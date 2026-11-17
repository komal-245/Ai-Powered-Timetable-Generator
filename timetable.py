from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from .. import models as m
from ..database import get_db
from ..engine import service
from ..engine.analytics import analyse, smart_notifications
from ..engine.context import Ctx, blocks_of
from ..engine.explain import explain
from ..engine.scoring import score
from ..engine.suggest import apply_move, suggest_moves
from ..engine.validator import validate
from ..security import current_user, require

router = APIRouter(prefix="/api/timetables", tags=["timetables"])


def tt_dict(t: m.Timetable, full=False):
    d = dict(id=t.id, name=t.name, run_id=t.run_id, version=t.version, rank=t.rank, status=t.status,
             is_active=t.is_active, score=t.score, created_at=t.created_at.isoformat(), params=t.params)
    if full:
        d["explanation"] = t.explanation
    return d


def enrich(ctx: Ctx, entries):
    out = []
    for e in entries:
        out.append({**e, "section": ctx.sections[e["section_id"]]["label"],
                    "subject": ctx.subjects[e["subject_id"]]["name"], "code": ctx.subjects[e["subject_id"]]["code"],
                    "faculty": ctx.faculty[e["faculty_id"]]["name"], "room": ctx.rooms[e["room_id"]]["name"]})
    return out


def get_tt(db, tid) -> m.Timetable:
    t = db.get(m.Timetable, tid)
    if not t:
        raise HTTPException(404, "Timetable not found")
    return t


class GenParams(BaseModel):
    candidates: int = Field(5, ge=1, le=10)
    time_limit: int = Field(10, ge=2, le=60, description="seconds per candidate")
    blocked: list[dict] = []        # [{"day": 4, "slots": [4,5,6]}]  e.g. no Friday afternoon


@router.post("/generate", status_code=202)
def generate(p: GenParams, _=Depends(require("admin"))):
    jid = service.start_job(p.candidates, p.time_limit, dict(blocked=p.blocked, candidates=p.candidates))
    return dict(job_id=jid)


@router.get("/jobs/{jid}")
def job(jid: str, _=Depends(require("admin"))):
    j = service.JOBS.get(jid)
    if not j:
        raise HTTPException(404, "Unknown job")
    return j


@router.get("")
def history(db: Session = Depends(get_db), _=Depends(current_user)):
    return [tt_dict(t) for t in db.query(m.Timetable).order_by(m.Timetable.id.desc())]


@router.get("/active")
def active(db: Session = Depends(get_db), _=Depends(current_user)):
    t = service.active_timetable(db)
    return tt_dict(t, True) if t else None


@router.get("/compare")
def compare(a: int, b: int, db: Session = Depends(get_db), _=Depends(current_user)):
    ta, tb = get_tt(db, a), get_tt(db, b)
    key = lambda e: (e["section_id"], e["subject_id"], e["faculty_id"], e["day"], e["slot"])
    ea, eb = {key(e) for e in service.load_entries(db, a)}, {key(e) for e in service.load_entries(db, b)}
    keys = ["overall", "conflict", "teacher_balance", "room_usage", "student_comfort", "preference", "idle_periods"]
    return dict(a=tt_dict(ta, True), b=tt_dict(tb, True), changed_periods=len(ea - eb),
                diff=[dict(metric=k, a=ta.score.get(k), b=tb.score.get(k),
                           delta=round((tb.score.get(k) or 0) - (ta.score.get(k) or 0), 1)) for k in keys])


@router.get("/{tid}")
def detail(tid: int, db: Session = Depends(get_db), _=Depends(current_user)):
    t, ctx = get_tt(db, tid), Ctx(db)
    return dict(**tt_dict(t, True), entries=enrich(ctx, service.load_entries(db, tid)))


@router.get("/{tid}/view")
def view(tid: int, section_id: int | None = None, faculty_id: int | None = None, room_id: int | None = None,
         db: Session = Depends(get_db), _=Depends(current_user)):
    ctx = Ctx(db)
    es = service.load_entries(db, tid)
    if section_id: es = [e for e in es if e["section_id"] == section_id]
    if faculty_id: es = [e for e in es if e["faculty_id"] == faculty_id]
    if room_id: es = [e for e in es if e["room_id"] == room_id]
    return enrich(ctx, es)


@router.get("/{tid}/conflicts")
def conflicts(tid: int, db: Session = Depends(get_db), _=Depends(current_user)):
    ctx, es = Ctx(db), service.load_entries(db, tid)
    V = validate(ctx, es, service.blocked_set(get_tt(db, tid).params))
    for v in V:           # AI conflict resolution: attach concrete suggestions
        v["suggestions"] = suggest_moves(ctx, es, v["block_ids"][0], limit=2) if v["block_ids"] and v["severity"] == "hard" else []
    return V


@router.get("/{tid}/analytics")
def tt_analytics(tid: int, db: Session = Depends(get_db), _=Depends(current_user)):
    ctx, es = Ctx(db), service.load_entries(db, tid)
    return dict(**analyse(ctx, es), notifications=smart_notifications(ctx, es))


class Move(BaseModel):
    block_id: int
    day: int
    slot: int
    commit: bool = True


@router.post("/{tid}/move")
def move(tid: int, body: Move, db: Session = Depends(get_db), _=Depends(require("admin"))):
    """Drag & drop: validate teacher / room / lab / time clashes instantly, apply only if clean."""
    t, ctx = get_tt(db, tid), Ctx(db)
    es = service.load_entries(db, tid)
    bl = blocks_of(es)
    if body.block_id not in bl:
        raise HTTPException(404, "Session not found")
    if not (0 <= body.day < ctx.D and 0 <= body.slot < ctx.T):
        raise HTTPException(400, "Invalid period")
    blocked = service.blocked_set(t.params)
    new, err = apply_move(ctx, es, body.block_id, body.day, body.slot)
    conflicts = []
    if err:
        conflicts.append(dict(type="room_overlap", severity="hard", message=err, block_ids=[body.block_id]))
    else:
        conflicts = [v for v in validate(ctx, new, blocked) if v["severity"] == "hard" and body.block_id in v["block_ids"]]
    if conflicts:
        return dict(ok=False, conflicts=conflicts, suggestions=suggest_moves(ctx, es, body.block_id, blocked))
    if body.commit:
        by_old = {(e["day"], e["slot"]): e for e in bl[body.block_id]}
        rows = {r.id: r for r in db.query(m.TimetableEntry).filter_by(timetable_id=tid, block_id=body.block_id)}
        first = bl[body.block_id][0]["slot"]
        new_room = next(e["room_id"] for e in new if e["block_id"] == body.block_id)
        for r in rows.values():
            r.day, r.slot, r.room_id = body.day, body.slot + (r.slot - first), new_room
        sc = score(ctx, new, None, blocked)
        t.score = sc
        t.explanation = explain(ctx, new, sc, t.params.get("profile", "manual"))
        db.commit()
        return dict(ok=True, score=sc)
    return dict(ok=True, conflicts=[])


@router.post("/{tid}/activate")
def activate(tid: int, db: Session = Depends(get_db), _=Depends(require("admin"))):
    get_tt(db, tid)
    return tt_dict(service.activate(db, tid))


@router.post("/{tid}/restore")
def restore(tid: int, db: Session = Depends(get_db), _=Depends(require("admin"))):
    """Clone an older version as a brand-new version and make it active."""
    src, ctx = get_tt(db, tid), Ctx(db)
    es = service.load_entries(db, tid)
    for e in es: e.pop("id", None)
    tt = service.save_timetable(db, ctx, es, f"Restored from {src.name}", src.run_id, service.next_version(db), 1,
                                src.params.get("profile", "restored"), src.params, service.blocked_set(src.params))
    db.commit()
    return tt_dict(service.activate(db, tt.id))


@router.delete("/{tid}")
def delete(tid: int, db: Session = Depends(get_db), _=Depends(require("admin"))):
    t = get_tt(db, tid)
    db.query(m.TimetableEntry).filter_by(timetable_id=tid).delete()
    db.delete(t); db.commit()
    return {"ok": True}
