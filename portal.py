"""Faculty / Student / Classroom portals, dashboard, search, notifications."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from .. import models as m
from ..config import DAYS, SLOTS
from ..database import get_db
from ..engine import service
from ..engine.analytics import analyse, smart_notifications, room_status
from ..engine.context import Ctx
from ..security import current_user, require
from .timetable import enrich

router = APIRouter(prefix="/api", tags=["portals"])


def current_entries(db):
    t = service.active_timetable(db)
    return t, (service.load_entries(db, t.id) if t else [])


def now_cell():
    n = datetime.now()
    d = min(n.weekday(), len(DAYS) - 1) if n.weekday() < len(DAYS) else 0
    hm = n.strftime("%H:%M")
    slot = next((i for i, (a, b) in enumerate(SLOTS) if a <= hm < b), 0)
    return d, slot


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _=Depends(require("admin"))):
    ctx = Ctx(db)
    t, es = current_entries(db)
    a = analyse(ctx, es)
    cards = dict(total_faculty=db.query(m.Faculty).count(), total_students=db.query(m.Student).count(),
                 total_departments=db.query(m.Department).count(), total_rooms=sum(1 for r in ctx.rooms.values() if not r["is_lab"]),
                 total_labs=sum(1 for r in ctx.rooms.values() if r["is_lab"]),
                 timetables_generated=db.query(m.Timetable).count(), active_faculty=a["stats"]["active_faculty"],
                 ai_score=a["stats"]["optimization_score"])
    dept = []
    for d in db.query(m.Department):
        secs = [s for s in ctx.sections.values() if s["dept"] == d.id]
        sid = {s["id"] for s in secs}
        dept.append(dict(name=d.code, sections=len(secs), periods=sum(1 for e in es if e["section_id"] in sid),
                         faculty=sum(1 for f in ctx.faculty.values() if f["dept"] == d.id)))
    return dict(cards=cards, analytics=a, departments=dept, active=t.name if t else None,
                notifications=smart_notifications(ctx, es))


@router.get("/me/timetable")
def my_timetable(db: Session = Depends(get_db), u=Depends(current_user)):
    ctx, (t, es) = Ctx(db), current_entries(db)
    if u.role == "faculty":
        es = [e for e in es if e["faculty_id"] == u.faculty_id]
    elif u.role == "student":
        st = db.get(m.Student, u.student_id)
        es = [e for e in es if e["section_id"] == st.section_id]
    return dict(timetable=t.name if t else None, entries=enrich(ctx, es))


@router.get("/me/workload")
def my_workload(db: Session = Depends(get_db), u=Depends(require("faculty"))):
    ctx, (t, es) = Ctx(db), current_entries(db)
    mine = [e for e in es if e["faculty_id"] == u.faculty_id]
    f = ctx.faculty[u.faculty_id]
    per_day = [sum(1 for e in mine if e["day"] == d) for d in range(len(DAYS))]
    subj = {}
    for e in mine:
        k = (e["subject_id"], e["section_id"])
        subj[k] = subj.get(k, 0) + 1
    return dict(faculty=f, hours=len(mine), per_day=per_day, days=DAYS,
                subjects=[dict(code=ctx.subjects[s]["code"], name=ctx.subjects[s]["name"],
                               section=ctx.sections[sec]["label"], periods=c) for (s, sec), c in subj.items()])


@router.get("/me/preferences")
def get_pref(db: Session = Depends(get_db), u=Depends(require("faculty"))):
    p = db.query(m.FacultyPreference).filter_by(faculty_id=u.faculty_id).first()
    un = [[x.day, x.slot] for x in db.query(m.FacultyUnavailability).filter_by(faculty_id=u.faculty_id)]
    return dict(shift=p.shift if p else "any", no_days=p.no_days if p else [], max_per_day=p.max_per_day if p else 5,
                free_slots=p.free_slots if p else [], unavailable=un)


@router.put("/me/preferences")
def put_pref(body: dict, db: Session = Depends(get_db), u=Depends(require("faculty"))):
    p = db.query(m.FacultyPreference).filter_by(faculty_id=u.faculty_id).first()
    if not p:
        p = m.FacultyPreference(faculty_id=u.faculty_id); db.add(p)
    p.shift = body.get("shift", "any") if body.get("shift") in ("any", "morning", "afternoon") else "any"
    p.no_days = [int(d) for d in body.get("no_days", [])]
    p.max_per_day = max(1, min(7, int(body.get("max_per_day", 5))))
    p.free_slots = [[int(a), int(b)] for a, b in body.get("free_slots", [])]
    db.query(m.FacultyUnavailability).filter_by(faculty_id=u.faculty_id).delete()
    db.add_all([m.FacultyUnavailability(faculty_id=u.faculty_id, day=d, slot=s)
                for d, s in {(int(a), int(b)) for a, b in body.get("unavailable", [])}])
    db.commit()
    return {"ok": True}


@router.get("/me/proctor")
def my_proctor(db: Session = Depends(get_db), u=Depends(require("student"))):
    st = db.get(m.Student, u.student_id)
    pr = db.get(m.Faculty, st.proctor_id) if st.proctor_id else None
    cyc = db.query(m.ProctorCycle).filter_by(student_id=st.id).order_by(m.ProctorCycle.cycle_no)
    sec = db.get(m.Section, st.section_id)
    return dict(student=dict(roll_no=st.roll_no, reg_no=st.reg_no, name=st.name, phone=st.phone,
                             section=f"{sec.semester}-{sec.name}", batch=sec.batch),
                proctor=dict(name=pr.name, email=pr.email, phone=pr.phone) if pr else None,
                cycles=[dict(cycle=c.cycle_no, date=c.meeting_date.isoformat()) for c in cyc])


@router.get("/notifications")
def notifications(db: Session = Depends(get_db), u=Depends(current_user)):
    qs = db.query(m.Notification).filter(or_(m.Notification.user_id == u.id, m.Notification.user_id.is_(None))) \
        .filter(or_(m.Notification.role == "", m.Notification.role == u.role)).order_by(m.Notification.id.desc()).limit(30)
    out = [dict(level=n.level, message=n.message, created_at=n.created_at.isoformat()) for n in qs]
    if u.role in ("admin", "faculty"):
        ctx, (t, es) = Ctx(db), current_entries(db)
        for n in smart_notifications(ctx, es):
            if u.role == "admin" or (u.faculty_id and ctx.faculty[u.faculty_id]["name"] in n["message"]):
                out.insert(0, dict(level=n["level"], message=n["message"], created_at=datetime.utcnow().isoformat()))
    return out


@router.get("/faculty-directory")
def directory(db: Session = Depends(get_db), _=Depends(current_user)):
    ctx, (t, es) = Ctx(db), current_entries(db)
    teaches = {}
    for e in es:
        teaches.setdefault(e["faculty_id"], set()).add(ctx.subjects[e["subject_id"]]["name"])
    return [dict(id=f["id"], name=f["name"], designation=f["designation"], email=f["email"], phone=f["phone"],
                 subjects=sorted(teaches.get(f["id"], []))) for f in ctx.faculty.values()]


@router.get("/rooms/{rid}/status")
def room_info(rid: int, db: Session = Depends(get_db), _=Depends(current_user)):
    ctx, (t, es) = Ctx(db), current_entries(db)
    if rid not in ctx.rooms:
        raise HTTPException(404, "Room not found")
    d, s = now_cell()
    return dict(**room_status(ctx, es, rid, d, s), now=dict(day=d, slot=s), days=DAYS, slots=[x[0] for x in SLOTS])


@router.get("/search")
def search(q: str, db: Session = Depends(get_db), _=Depends(current_user)):
    like = f"%{q}%"
    ctx, (t, es) = Ctx(db), current_entries(db)
    res = dict(
        faculty=[dict(id=f.id, name=f.name, designation=f.designation, email=f.email) for f in db.query(m.Faculty).filter(m.Faculty.name.ilike(like)).limit(10)],
        subjects=[dict(id=s.id, code=s.code, name=s.name, semester=s.semester) for s in db.query(m.Subject).filter(or_(m.Subject.name.ilike(like), m.Subject.code.ilike(like))).limit(10)],
        rooms=[dict(id=r.id, name=r.name, capacity=r.capacity, is_lab=r.is_lab) for r in db.query(m.Room).filter(m.Room.name.ilike(like)).limit(10)],
        departments=[dict(id=d.id, code=d.code, name=d.name) for d in db.query(m.Department).filter(or_(m.Department.name.ilike(like), m.Department.code.ilike(like))).limit(10)],
        sections=[dict(id=s["id"], label=s["label"], semester=s["semester"]) for s in ctx.sections.values()
                  if q.lower() in s["label"].lower() or q.lower() in f"sem {s['semester']}"],
    )
    return res
