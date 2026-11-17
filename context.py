"""Plain-python snapshot of the master data, shared by solver / validator / analytics / chatbot."""
from collections import defaultdict
from sqlalchemy.orm import Session
from .. import models as m
from ..config import DAYS, SLOTS


class Ctx:
    def __init__(self, db: Session):
        self.D, self.T = len(DAYS), len(SLOTS)
        self.sections = {s.id: dict(id=s.id, label=f"{s.semester}-{s.name}", name=s.name, semester=s.semester,
                                    strength=s.strength, dept=s.department_id, proctor_id=s.proctor_id)
                         for s in db.query(m.Section)}
        self.subjects = {s.id: dict(id=s.id, code=s.code, name=s.name, semester=s.semester, dept=s.department_id,
                                    hours=s.hours_per_week, is_lab=s.is_lab, credits=s.credits)
                         for s in db.query(m.Subject)}
        self.faculty = {f.id: dict(id=f.id, name=f.name, designation=f.designation, email=f.email, phone=f.phone,
                                   max_hours=f.max_hours_week, dept=f.department_id, active=f.active)
                        for f in db.query(m.Faculty)}
        self.rooms = {r.id: dict(id=r.id, name=r.name, capacity=r.capacity, is_lab=r.is_lab, building=r.building)
                      for r in db.query(m.Room)}
        self.unavail = {(u.faculty_id, u.day, u.slot) for u in db.query(m.FacultyUnavailability)}
        self.prefs = {p.faculty_id: dict(shift=p.shift, no_days=p.no_days or [], max_per_day=p.max_per_day,
                                         free_slots=[tuple(x) for x in (p.free_slots or [])])
                      for p in db.query(m.FacultyPreference)}
        self.eligible = defaultdict(list)
        for fs in db.query(m.FacultySubject):
            if fs.faculty_id in self.faculty and self.faculty[fs.faculty_id]["active"]:
                self.eligible[fs.subject_id].append(fs.faculty_id)

    def section_subjects(self, sid):
        s = self.sections[sid]
        return [x for x in self.subjects.values() if x["semester"] == s["semester"] and x["dept"] == s["dept"]]

    def requirements(self):
        """{(section_id, subject_id): periods_required}"""
        return {(sid, x["id"]): x["hours"] for sid in self.sections for x in self.section_subjects(sid)}

    def label(self, e):
        return f'{self.subjects[e["subject_id"]]["code"]}'


def entry_dict(e: m.TimetableEntry) -> dict:
    return dict(id=e.id, block_id=e.block_id, section_id=e.section_id, subject_id=e.subject_id,
                faculty_id=e.faculty_id, room_id=e.room_id, day=e.day, slot=e.slot, is_lab=e.is_lab)


def blocks_of(entries):
    """Group per-slot entries into sessions: {block_id: [entries sorted by slot]}"""
    b = defaultdict(list)
    for e in entries:
        b[e["block_id"]].append(e)
    for v in b.values():
        v.sort(key=lambda e: e["slot"])
    return b
