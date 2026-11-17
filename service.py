"""Orchestration: background generation jobs, persistence of candidates, loading timetables."""
import threading
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from .. import models as m
from ..database import SessionLocal
from .context import Ctx, entry_dict
from .explain import explain
from .scoring import score
from .solver import generate_candidate, SchedulingError
from .validator import validate

JOBS: dict[str, dict] = {}


def blocked_set(params):
    b = set()
    for item in (params or {}).get("blocked", []):
        for s in item.get("slots", []):
            b.add((item["day"], s))
    return b


def save_timetable(db, ctx, entries, name, run_id, version, rank, profile, params, blocked=None):
    V = validate(ctx, entries, blocked)
    sc = score(ctx, entries, V, blocked)
    tt = m.Timetable(name=name, run_id=run_id, version=version, rank=rank, status="candidate", score=sc,
                     explanation=explain(ctx, entries, sc, profile, V), params={**params, "profile": profile})
    db.add(tt); db.flush()
    db.add_all([m.TimetableEntry(timetable_id=tt.id, **e) for e in entries])
    return tt


def next_version(db):
    last = db.query(m.Timetable).order_by(m.Timetable.version.desc()).first()
    return (last.version if last else 0) + 1


def run_generation(job_id, n, time_limit, params):
    job = JOBS[job_id]
    try:
        with SessionLocal() as db:
            ctx = Ctx(db)
            blocked = blocked_set(params)
            results = []
            for i in range(n):
                job.update(progress=i, message=f"Solving candidate {i + 1} of {n}...")
                try:
                    results.append(generate_candidate(ctx, i, blocked, time_limit))
                except SchedulingError as e:
                    if blocked and i == 0:   # retry once without the user's extra blocked periods
                        job["warnings"].append(f"Constraints could not be met ({e}); relaxing blocked periods.")
                        blocked = set()
                        results.append(generate_candidate(ctx, i, blocked, time_limit))
                    else:
                        job["warnings"].append(str(e))
            if not results:
                raise SchedulingError("; ".join(job["warnings"]) or "No candidate could be generated")
            scored = []
            for r in results:
                V = validate(ctx, r["entries"], blocked)
                scored.append((score(ctx, r["entries"], V, blocked)["overall"], r))
            scored.sort(key=lambda x: -x[0])
            ver = next_version(db)
            stamp = datetime.now().strftime("%d %b %H:%M")
            ids = []
            for rank, (_, r) in enumerate(scored, 1):
                tt = save_timetable(db, ctx, r["entries"], f"v{ver} {stamp} - candidate {rank}", job_id, ver, rank,
                                    r["profile"], params, blocked)
                tt.status = "best" if rank == 1 else "candidate"
                ids.append(tt.id)
            db.commit()
            job.update(status="done", progress=n, message="Finished", timetable_ids=ids, best_id=ids[0])
    except Exception as e:           # noqa
        job.update(status="error", message=str(e))


def start_job(n, time_limit, params):
    jid = uuid.uuid4().hex[:12]
    JOBS[jid] = dict(id=jid, status="running", progress=0, total=n, message="Starting", warnings=[], timetable_ids=[])
    threading.Thread(target=run_generation, args=(jid, n, time_limit, params), daemon=True).start()
    return jid


def load_entries(db: Session, tid: int):
    return [entry_dict(e) for e in db.query(m.TimetableEntry).filter_by(timetable_id=tid)]


def activate(db: Session, tid: int):
    db.query(m.Timetable).update({m.Timetable.is_active: False})
    tt = db.get(m.Timetable, tid)
    tt.is_active = True
    db.add(m.Notification(role="", level="info", message=f"Timetable '{tt.name}' is now active. Please review your schedule."))
    db.commit()
    return tt


def active_timetable(db: Session):
    return db.query(m.Timetable).filter_by(is_active=True).first() or \
        db.query(m.Timetable).order_by(m.Timetable.id.desc()).first()
