from datetime import datetime, date
from sqlalchemy import String, Integer, Boolean, ForeignKey, JSON, Text, DateTime, Date, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(120))


class Section(Base):          # a Semester + Section pair, e.g. 5th Sem CSE-B
    __tablename__ = "sections"
    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    semester: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(10))
    batch: Mapped[str] = mapped_column(String(20), default="")
    strength: Mapped[int] = mapped_column(Integer, default=60)
    proctor_id: Mapped[int | None] = mapped_column(ForeignKey("faculty.id"), nullable=True)


class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    semester: Mapped[int] = mapped_column(Integer)
    credits: Mapped[int] = mapped_column(Integer, default=3)
    hours_per_week: Mapped[int] = mapped_column(Integer, default=3)
    is_lab: Mapped[bool] = mapped_column(Boolean, default=False)


class Faculty(Base):
    __tablename__ = "faculty"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    designation: Mapped[str] = mapped_column(String(40))
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), unique=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    max_hours_week: Mapped[int] = mapped_column(Integer, default=16)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class FacultySubject(Base):   # which subjects a teacher is able to teach
    __tablename__ = "faculty_subjects"
    __table_args__ = (UniqueConstraint("faculty_id", "subject_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))


class FacultyUnavailability(Base):
    __tablename__ = "faculty_unavailability"
    __table_args__ = (UniqueConstraint("faculty_id", "day", "slot"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id"))
    day: Mapped[int] = mapped_column(Integer)
    slot: Mapped[int] = mapped_column(Integer)


class FacultyPreference(Base):
    __tablename__ = "faculty_preferences"
    id: Mapped[int] = mapped_column(primary_key=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id"), unique=True)
    shift: Mapped[str] = mapped_column(String(10), default="any")      # morning | afternoon | any
    no_days: Mapped[list] = mapped_column(JSON, default=list)          # day indexes to avoid
    max_per_day: Mapped[int] = mapped_column(Integer, default=5)
    free_slots: Mapped[list] = mapped_column(JSON, default=list)       # [[day, slot], ...]


class Room(Base):
    __tablename__ = "rooms"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)
    building: Mapped[str] = mapped_column(String(40), default="")
    capacity: Mapped[int] = mapped_column(Integer, default=60)
    is_lab: Mapped[bool] = mapped_column(Boolean, default=False)


class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    roll_no: Mapped[str] = mapped_column(String(20), unique=True)
    reg_no: Mapped[str] = mapped_column(String(20), default="")
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20), default="")
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"))
    proctor_id: Mapped[int | None] = mapped_column(ForeignKey("faculty.id"), nullable=True)


class ProctorCycle(Base):
    __tablename__ = "proctor_cycles"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    cycle_no: Mapped[int] = mapped_column(Integer)
    meeting_date: Mapped[date] = mapped_column(Date)


class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(150))
    kind: Mapped[str] = mapped_column(String(30), default="event")  # semester_start|semester_end|holiday|exam|event
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(10))                      # admin|faculty|student
    full_name: Mapped[str] = mapped_column(String(120), default="")
    faculty_id: Mapped[int | None] = mapped_column(ForeignKey("faculty.id"), nullable=True)
    student_id: Mapped[int | None] = mapped_column(ForeignKey("students.id"), nullable=True)


class Timetable(Base):
    __tablename__ = "timetables"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    run_id: Mapped[str] = mapped_column(String(40), default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    rank: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(12), default="candidate")  # candidate|best|archived
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[dict] = mapped_column(JSON, default=dict)
    explanation: Mapped[str] = mapped_column(Text, default="")
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TimetableEntry(Base):
    __tablename__ = "timetable_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    timetable_id: Mapped[int] = mapped_column(ForeignKey("timetables.id", ondelete="CASCADE"), index=True)
    block_id: Mapped[int] = mapped_column(Integer)          # entries of one continuous session share block_id
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id"))
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    day: Mapped[int] = mapped_column(Integer)
    slot: Mapped[int] = mapped_column(Integer)
    is_lab: Mapped[bool] = mapped_column(Boolean, default=False)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)  # null = broadcast
    role: Mapped[str] = mapped_column(String(10), default="")                           # optional role target
    level: Mapped[str] = mapped_column(String(10), default="info")
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
