"""AI chatbot. Works fully offline with an intent engine over live timetable data;
if OLLAMA_URL is set, unknown questions are answered by a local LLM grounded with a data summary."""
import re
from collections import Counter
from datetime import datetime
import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .. import models as m
from ..config import DAYS, SLOTS, OLLAMA_URL, OLLAMA_MODEL
from ..database import get_db
from ..engine import service
from ..engine.analytics import analyse
from ..engine.context import Ctx
from ..security import current_user

router = APIRouter(prefix="/api", tags=["chatbot"])
STOP = {"of", "and", "the", "&", "to", "in"}


class Msg(BaseModel):
    message: str


def acronym(name):
    return "".join(w[0] for w in re.findall(r"[A-Za-z]+", name) if w.lower() not in STOP).lower()


def find_subject(ctx, text):
    t = text.lower()
    best = None
    for s in ctx.subjects.values():
        keys = {s["code"].lower(), acronym(re.sub(r"\(.*?\)", "", s["name"])), s["name"].lower()}
        if any(re.search(rf"\b{re.escape(k)}\b", t) for k in keys if k) and not (best and s["is_lab"] and not re.search(r"lab", t)):
            if not best or (s["is_lab"] == bool(re.search(r"lab", t))):
                best = s
    return best


def find_section(ctx, text):
    t = text.lower()
    mt = re.search(r"\b([3-8])\s*(?:st|nd|rd|th)?\s*[- ]?\s*(?:sem(?:ester)?)?\s*[- ]?\s*(?:cse)?\s*[- ]?\s*([a-d])\b", t)
    if mt:
        for s in ctx.sections.values():
            if s["semester"] == int(mt.group(1)) and s["name"].lower() == mt.group(2):
                return s
    return None


def find_day(text):
    t = text.lower()
    now = datetime.now().weekday()
    if "tomorrow" in t: return min((now + 1) % 7, len(DAYS) - 1) if (now + 1) % 7 < len(DAYS) else 0
    for i, d in enumerate(DAYS):
        if re.search(rf"\b{d.lower()}[a-z]*\b", t): return i
    return now if now < len(DAYS) else 0


def find_time(text):
    mt = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", text.lower()) or re.search(r"\b(\d{1,2}):(\d{2})\b()", text)
    if not mt: return None
    h, mi, ap = int(mt.group(1)), int(mt.group(2) or 0), mt.group(3)
    if ap == "pm" and h < 12: h += 12
    if ap == "am" and h == 12: h = 0
    if not ap and 1 <= h <= 6: h += 12                      # "2:00" in college hours means 14:00
    hm = f"{h:02d}:{mi:02d}"
    return next((i for i, (a, b) in enumerate(SLOTS) if a <= hm < b), None)


@router.post("/chat")
def chat(body: Msg, db: Session = Depends(get_db), user=Depends(current_user)):
    q = body.message.strip()
    ql = q.lower()
    ctx = Ctx(db)
    tt = service.active_timetable(db)
    es = service.load_entries(db, tt.id) if tt else []
    if not es and "generate" not in ql:
        return dict(reply="No timetable exists yet. Ask an admin to generate one (or say 'generate a timetable').")

    # --- generate with constraints
    if "generate" in ql and ("timetable" in ql or "schedule" in ql):
        if user.role != "admin":
            return dict(reply="Only administrators can generate timetables.")
        blocked = []
        if "without" in ql or "no " in ql or "avoid" in ql:
            parts = ["morning" in ql, "afternoon" in ql]
            for i, d in enumerate(DAYS):
                if re.search(rf"\b{d.lower()}[a-z]*\b", ql):
                    slots = [3, 4] if parts[1] and not parts[0] else [0, 1, 2] if parts[0] and not parts[1] else list(range(len(SLOTS)))
                    blocked.append(dict(day=i, slots=slots))
                what = ", ".join(f"{DAYS[b['day']]} {'afternoon' if b['slots'] == [3, 4] else 'morning' if b['slots'] == [0, 1, 2] else 'all day'}" for b in blocked) or "no extra restrictions"
                return dict(reply=f"Started generating 5 candidate timetables ({what}). This runs in the background and takes a few minutes. When it finishes, open History to compare the candidates and activate the best one.", action=dict(type="generate", job_id=jid)) # type: ignore

    # --- who teaches X
    mt = re.search(r"who (?:teaches|is teaching|takes|handles)\s+(.+?)\??$", ql)
    if mt:
        s = find_subject(ctx, mt.group(1))
        if not s: return dict(reply=f"I couldn't find a subject matching '{mt.group(1)}'.")
        pairs = sorted({(ctx.sections[e["section_id"]]["label"], ctx.faculty[e["faculty_id"]]["name"]) for e in es if e["subject_id"] == s["id"]})
        return dict(reply=f"{s['name']} ({s['code']}) is taught by: " + "; ".join(f"{f} (section {sec})" for sec, f in pairs) if pairs else f"{s['name']} is not scheduled.", data=pairs)

    # --- empty classrooms / free faculty at a time
    slot = find_time(ql)
    if re.search(r"(empty|free|vacant|available)\s+(class)?room", ql) or "empty classroom" in ql:
        if slot is None: return dict(reply="Which time? e.g. 'Find an empty classroom at 2 PM'.")
        d = find_day(ql)
        busy = {e["room_id"] for e in es if e["day"] == d and e["slot"] == slot}
        free = [r["name"] for r in ctx.rooms.values() if r["id"] not in busy and (("lab" in ql) == r["is_lab"])]
        return dict(reply=f"Free {'labs' if 'lab' in ql else 'classrooms'} on {DAYS[d]} at {SLOTS[slot][0]}: " + (", ".join(free) or "none"), data=free)
    if re.search(r"(free|available)\s+(faculty|teacher|staff)", ql):
        if slot is None: return dict(reply="Which time? e.g. 'Which faculty are free at 11 am'.")
        d = find_day(ql)
        busy = {e["faculty_id"] for e in es if e["day"] == d and e["slot"] == slot}
        free = [f["name"] for f in ctx.faculty.values() if f["id"] not in busy]
        return dict(reply=f"{len(free)} faculty are free on {DAYS[d]} at {SLOTS[slot][0]}: " + ", ".join(free[:15]) + (" ..." if len(free) > 15 else ""), data=free)

    # --- workload
    if re.search(r"workload|overload|busiest|most (classes|periods)", ql):
        a = analyse(ctx, es)["faculty"]
        if "lowest" in ql or "least" in ql: top = [f for f in a if f["hours"] > 0][-3:]
        else: top = a[:3]
        return dict(reply="Highest workload: " + "; ".join(f"{f['name']} - {f['hours']}/{f['max']} periods" for f in top) if "lowest" not in ql and "least" not in ql
                    else "Lowest workload: " + "; ".join(f"{f['name']} - {f['hours']}/{f['max']}" for f in top), data=top)

    # --- timetable of a day for a section / my timetable
    if "timetable" in ql or "schedule" in ql or "classes" in ql or "class today" in ql:
        d = find_day(ql)
        sec = find_section(ctx, ql)
        who = None
        if sec: rows = [e for e in es if e["section_id"] == sec["id"] and e["day"] == d]; who = f"section {sec['label']}"
        elif user.role == "faculty" or "my" in ql and user.role == "faculty":
            rows = [e for e in es if e["faculty_id"] == user.faculty_id and e["day"] == d]; who = "you"
        elif user.role == "student":
            st = db.get(m.Student, user.student_id); rows = [e for e in es if e["section_id"] == st.section_id and e["day"] == d]; who = "your section"
        else:
            rows = [e for e in es if e["day"] == d]; who = "all CSE sections"
        rows.sort(key=lambda e: (e["section_id"], e["slot"]))
        lines = [f"{SLOTS[e['slot']][0]} {ctx.subjects[e['subject_id']]['code']} {ctx.subjects[e['subject_id']]['name']}"
                 f"{'' if sec else ' [' + ctx.sections[e['section_id']]['label'] + ']'} - {ctx.faculty[e['faculty_id']]['name']} - {ctx.rooms[e['room_id']]['name']}" for e in rows]
        return dict(reply=f"{DAYS[d]} timetable for {who}:\n" + ("\n".join(lines) if lines else "No classes."), data=lines)

    # --- utilisation
    if re.search(r"utili[sz]ation|lab usage|room usage", ql):
        r = analyse(ctx, es)["resource"]
        return dict(reply=f"Teacher utilization {r['teacher_utilization']}%, room utilization {r['room_utilization']}%, lab utilization {r['lab_utilization']}%, faculty balance {r['faculty_balance']}%.")
    if re.search(r"score|quality", ql) and tt:
        return dict(reply=f"Active timetable '{tt.name}' scores {tt.score.get('overall')}% overall (conflicts {tt.score.get('conflict')}%, teacher balance {tt.score.get('teacher_balance')}%, student comfort {tt.score.get('student_comfort')}%).")

    # --- LLM fallback
    if OLLAMA_URL:
        a = analyse(ctx, es)
        facts = f"Stats: {a['stats']}. Resource: {a['resource']}. Subjects: {[s['name'] for s in ctx.subjects.values()]}."
        try:
            r = httpx.post(f"{OLLAMA_URL}/api/generate", json=dict(model=OLLAMA_MODEL, stream=False,
                           prompt=f"You are a timetable assistant for GIET University CSE. Facts: {facts}\nQuestion: {q}\nAnswer briefly."), timeout=60)
            return dict(reply=r.json().get("response", "").strip())
        except Exception:
            pass
    return dict(reply="I can answer: 'Who teaches AI?', 'Show today's timetable for 5-B', 'Find an empty classroom at 2 PM', "
                      "'Which faculty has the highest workload?', 'Which faculty are free at 11 am on Monday?', "
                      "'Generate a timetable without Friday afternoon classes', 'Show utilization'.")
