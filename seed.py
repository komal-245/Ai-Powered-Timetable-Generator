import os
import re
from datetime import date, datetime
import pandas as pd
from sqlalchemy.orm import Session
from . import models as m
from .config import DATA_DIR
from .database import Base, engine, SessionLocal
from .security import hash_password

DEFAULT_FACULTY_PASSWORD = "Giet@123"
ADMIN_USER, ADMIN_PASS = "admin", "admin123"

# (code, name, hours/week, is_lab)  - sample curriculum
SUBJECTS = {
    3: [("CS301", "Data Structures & Algorithms", 4, False), ("CS302", "Discrete Mathematics", 3, False),
        ("CS303", "Digital Logic Design", 3, False), ("CS304", "Object Oriented Programming (Java)", 3, False),
        ("CS305", "Computer Organization & Architecture", 3, False),
        ("CS391", "Data Structures Lab", 2, True), ("CS392", "OOP Lab", 2, True)],
    5: [("CS501", "Database Management Systems", 4, False), ("CS502", "Operating Systems", 4, False),
        ("CS503", "Computer Networks", 3, False), ("CS504", "Software Engineering", 3, False),
        ("CS505", "Artificial Intelligence", 3, False), ("CS506", "Formal Languages & Automata Theory", 3, False),
        ("CS591", "DBMS Lab", 2, True), ("CS592", "Operating Systems Lab", 2, True)],
}
SECTIONS = [(3, "A", "2025-2029", 60), (3, "B", "2025-2029", 60),
            (5, "A", "2024-2028", 60), (5, "B", "2024-2028", None), (5, "C", "2024-2028", 60)]
ROOMS = [("LH-101", "Main Block", 70, False), ("LH-102", "Main Block", 70, False), ("LH-103", "Main Block", 70, False),
         ("LH-201", "Main Block", 80, False), ("LH-202", "Main Block", 80, False), ("LH-203", "Main Block", 66, False),
         ("LAB-A1", "CSE Lab Block", 70, True), ("LAB-A2", "CSE Lab Block", 70, True), ("LAB-B1", "CSE Lab Block", 70, True)]
MAX_HOURS = {"professor": 12, "assoc": 14, "asst": 16, "lecturer": 18}


def _designation(raw: str) -> str:
    r = raw.lower().replace(".", "").replace(" ", "")
    if r.startswith("prof"): return "Professor"
    if r.startswith("assoc"): return "Associate Professor"
    if r.startswith("asst") or r.startswith("assist"): return "Assistant Professor"
    return "Lecturer"


def _max_hours(desig: str, name: str) -> int:
    if "Murali Gopal" in name: return 8                  # Head of Department
    return MAX_HOURS[{"Professor": "professor", "Associate Professor": "assoc",
                      "Assistant Professor": "asst"}.get(desig, "lecturer")]


def _clean_phone(p) -> str:
    return re.sub(r"\D", "", str(p or ""))[-10:]


def load_faculty_rows():
    df = pd.read_excel(os.path.join(DATA_DIR, "Supervisor_List.xlsx"), header=None, dtype=str)
    rows, seen = [], set()
    for _, r in df.iterrows():
        sl = str(r[0]).strip()
        if not sl.isdigit() or pd.isna(r[1]):
            continue
        email = str(r[4]).strip().lower()
        if email in seen or "@" not in email:
            continue                                      # duplicate (e.g. Debasis/Debasish Pradhan)
        seen.add(email)
        name = re.sub(r"\s+", " ", str(r[1]).strip())
        name = re.sub(r"^(Dr|Mr|Mrs|Ms)\.?(?=[A-Za-z(])", r"\1. ", name)
        name = re.sub(r"(?<=\b[A-Z])\.(?=[A-Za-z]{2})", ". ", name)
        rows.append(dict(name=name, designation=_designation(str(r[2])), phone=_clean_phone(r[3]), email=email))
    return rows


def load_students():
    df = pd.read_excel(os.path.join(DATA_DIR, "CSE-B_Proctor_cycle.xlsx"), header=None)
    proctor = "Shibani Subhadarshini"
    for v in df.iloc[1].tolist():
        if isinstance(v, str) and "PROCTOR" in v.upper():
            proctor = v.split("-", 1)[-1].strip().title().replace("Ms.", "").strip()
    out = []
    for _, r in df.iloc[3:].iterrows():
        if not isinstance(r[0], str) or not r[0].upper().startswith("24CSE"):
            continue
        cycles = [(i + 1, pd.Timestamp(r[4 + i]).date()) for i in range(5) if pd.notna(r[4 + i])]
        out.append(dict(roll_no=r[0].strip(), reg_no=str(r[1]).strip(), name=str(r[2]).strip().title(),
                        phone=_clean_phone(r[3]), cycles=cycles))
    return proctor, out


def seed(db: Session, force: bool = False):
    if db.query(m.User).count() and not force:
        return False
    cse = m.Department(code="CSE", name="Computer Science & Engineering")
    db.add(cse); db.flush()

    # ---- faculty -----------------------------------------------------------------------
    fac = []
    for r in load_faculty_rows():
        f = m.Faculty(department_id=cse.id, max_hours_week=_max_hours(r["designation"], r["name"]), **r)
        db.add(f); fac.append(f)
    db.flush()

    # ---- subjects ----------------------------------------------------------------------
    subs = []
    for sem, lst in SUBJECTS.items():
        for code, name, hrs, lab in lst:
            s = m.Subject(code=code, name=name, department_id=cse.id, semester=sem,
                          credits=1 if lab else (4 if hrs == 4 else 3), hours_per_week=hrs, is_lab=lab)
            db.add(s); subs.append(s)
    db.flush()
    # sample "can teach" mapping: 9 eligible teachers per subject, spread over seniority (editable)
    n = len(fac)
    for i, s in enumerate(subs):
        picks, k = [], 0
        while len(picks) < 9:
            idx = (i * 7 + k * 4) % n
            if fac[idx].id not in picks:
                picks.append(fac[idx].id)
            k += 1
        for fid in picks:
            db.add(m.FacultySubject(faculty_id=fid, subject_id=s.id))

    # ---- rooms -------------------------------------------------------------------------
    for name, b, cap, lab in ROOMS:
        db.add(m.Room(name=name, building=b, capacity=cap, is_lab=lab))

    # ---- students + proctor (real data) -------------------------------------------------
    proctor_name, students = load_students()
    proctor = next((f for f in fac if re.sub(r"\W", "", f.name.lower()).endswith(re.sub(r"\W", "", proctor_name.lower()))), None)
    secs = {}
    for sem, name, batch, strength in SECTIONS:
        sec = m.Section(department_id=cse.id, semester=sem, name=name, batch=batch,
                        strength=strength or len(students))
        if (sem, name) == (5, "B") and proctor:
            sec.proctor_id = proctor.id
        db.add(sec); secs[(sem, name)] = sec
    db.flush()
    sec_b = secs[(5, "B")]
    users = [m.User(username=ADMIN_USER, password_hash=hash_password(ADMIN_PASS), role="admin", full_name="Administrator")]
    for st in students:
        s = m.Student(roll_no=st["roll_no"], reg_no=st["reg_no"], name=st["name"], phone=st["phone"],
                      section_id=sec_b.id, proctor_id=proctor.id if proctor else None)
        db.add(s); db.flush()
        for no, d in st["cycles"]:
            db.add(m.ProctorCycle(student_id=s.id, cycle_no=no, meeting_date=d))
        users.append(m.User(username=st["roll_no"].lower(), password_hash=hash_password(st["reg_no"]),
                            role="student", full_name=s.name, student_id=s.id))
    fh = hash_password(DEFAULT_FACULTY_PASSWORD)
    for f in fac:
        users.append(m.User(username=f.email.split("@")[0], password_hash=fh, role="faculty",
                            full_name=f.name, faculty_id=f.id))
    db.add_all(users)

    # ---- demo preferences (teachers can change these from the Faculty portal) -------------
    for i, f in enumerate(fac[:12]):
        pref = [dict(shift="morning"), dict(no_days=[4]), dict(shift="afternoon", max_per_day=4), dict()][i % 4]
        db.add(m.FacultyPreference(faculty_id=f.id, **{"max_per_day": 5, **pref}))

    # ---- sample academic calendar -----------------------------------------------------------
    for title, kind, a, b in [("Odd semester begins", "semester_start", date(2026, 7, 6), None),
                              ("Mid-semester examinations (sample)", "exam", date(2026, 9, 14), date(2026, 9, 19)),
                              ("Puja vacation (sample)", "holiday", date(2026, 10, 17), date(2026, 10, 21)),
                              ("End-semester examinations (sample)", "exam", date(2026, 11, 30), date(2026, 12, 12)),
                              ("Odd semester teaching ends", "semester_end", date(2026, 11, 27), None)]:
        db.add(m.CalendarEvent(title=title, kind=kind, start_date=a, end_date=b))
    db.add(m.Notification(role="", level="info", message="Welcome to the AI Timetable Generator."))
    db.commit()
    return True


def init_db(force=False):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        return seed(db, force)


if __name__ == "__main__":
    print("seeded" if init_db() else "already seeded")
