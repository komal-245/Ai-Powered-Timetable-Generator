"""Generic CRUD for the master-data tables (admin writes, any logged-in user reads)."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import inspect as sa_inspect
from .. import models as m
from ..config import DAYS, SLOTS, BREAK_AFTER
from ..database import get_db
from ..security import current_user, require

router = APIRouter(prefix="/api", tags=["master-data"])

RESOURCES = {
    "departments": m.Department, "sections": m.Section, "subjects": m.Subject, "faculty": m.Faculty,
    "rooms": m.Room, "students": m.Student, "calendar": m.CalendarEvent,
}
READONLY = {"id"}


def to_dict(o):
    out = {}
    for c in sa_inspect(o.__class__).columns:
        v = getattr(o, c.key)
        out[c.key] = v.isoformat() if isinstance(v, date) else v
    return out


def clean(model, data):
    cols = {c.key: c for c in sa_inspect(model).columns}
    out = {}
    for k, v in data.items():
        if k in cols and k not in READONLY:
            if isinstance(v, str) and "Date" in str(cols[k].type):
                v = date.fromisoformat(v) if v else None
            out[k] = v
    return out


@router.get("/meta")
def meta():
    return dict(days=DAYS, break_after=sorted(BREAK_AFTER), slots=[dict(index=i, start=s, end=e) for i, (s, e) in enumerate(SLOTS)])


def make(name, model):
    @router.get(f"/{name}", name=f"list_{name}")
    def list_(q: str | None = None, skip: int = 0, limit: int = 500, db: Session = Depends(get_db), _=Depends(current_user)):
        qs = db.query(model)
        if q:
            for col in ("name", "title", "code", "roll_no", "email"):
                if hasattr(model, col):
                    qs = qs.filter(getattr(model, col).ilike(f"%{q}%")); break
        return [to_dict(o) for o in qs.order_by(model.id).offset(skip).limit(limit)]

    @router.post(f"/{name}", status_code=201, name=f"create_{name}")
    def create(data: dict, db: Session = Depends(get_db), _=Depends(require("admin"))):
        o = model(**clean(model, data)); db.add(o)
        try:
            db.commit()
        except Exception as e:
            db.rollback(); raise HTTPException(400, f"Could not save: {e.__class__.__name__}")
        return to_dict(o)

    @router.put(f"/{name}/{{oid}}", name=f"update_{name}")
    def update(oid: int, data: dict, db: Session = Depends(get_db), _=Depends(require("admin"))):
        o = db.get(model, oid)
        if not o: raise HTTPException(404, "Not found")
        for k, v in clean(model, data).items(): setattr(o, k, v)
        db.commit()
        return to_dict(o)

    @router.delete(f"/{name}/{{oid}}", name=f"delete_{name}")
    def delete(oid: int, db: Session = Depends(get_db), _=Depends(require("admin"))):
        o = db.get(model, oid)
        if not o: raise HTTPException(404, "Not found")
        try:
            db.delete(o); db.commit()
        except Exception:
            db.rollback(); raise HTTPException(409, "Cannot delete: record is referenced by other data")
        return {"ok": True}


for _n, _m in RESOURCES.items():
    make(_n, _m)


# ---- teacher <-> subject mapping and availability ---------------------------------------
@router.get("/faculty/{fid}/subjects")
def fac_subjects(fid: int, db: Session = Depends(get_db), _=Depends(current_user)):
    return [r.subject_id for r in db.query(m.FacultySubject).filter_by(faculty_id=fid)]


@router.put("/faculty/{fid}/subjects")
def set_fac_subjects(fid: int, ids: list[int], db: Session = Depends(get_db), _=Depends(require("admin"))):
    db.query(m.FacultySubject).filter_by(faculty_id=fid).delete()
    db.add_all([m.FacultySubject(faculty_id=fid, subject_id=i) for i in set(ids)])
    db.commit()
    return {"ok": True}


@router.get("/faculty/{fid}/unavailability")
def unavail(fid: int, db: Session = Depends(get_db), _=Depends(current_user)):
    return [[u.day, u.slot] for u in db.query(m.FacultyUnavailability).filter_by(faculty_id=fid)]


@router.put("/faculty/{fid}/unavailability")
def set_unavail(fid: int, cells: list[list[int]], db: Session = Depends(get_db), user=Depends(current_user)):
    if user.role != "admin" and user.faculty_id != fid:
        raise HTTPException(403, "Not allowed")
    db.query(m.FacultyUnavailability).filter_by(faculty_id=fid).delete()
    db.add_all([m.FacultyUnavailability(faculty_id=fid, day=d, slot=s) for d, s in {tuple(c) for c in cells}])
    db.commit()
    return {"ok": True}
