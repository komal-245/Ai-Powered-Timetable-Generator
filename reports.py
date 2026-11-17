"""PDF (ReportLab), Excel (pandas/openpyxl), ICS and Google-Calendar exports."""
import io
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from urllib.parse import quote
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from sqlalchemy.orm import Session
from .. import models as m
from ..config import DAYS, SLOTS
from ..database import get_db
from ..engine import service
from ..engine.analytics import analyse
from ..engine.context import Ctx, blocks_of
from ..security import current_user, require

router = APIRouter(prefix="/api", tags=["reports"])
styles = getSampleStyleSheet()
NAVY = colors.HexColor("#1e3a8a")


def pick(db, tid):
    t = db.get(m.Timetable, tid) if tid else service.active_timetable(db)
    if not t:
        raise HTTPException(404, "No timetable available - generate one first")
    return t


def filt(es, section_id, faculty_id, room_id):
    if section_id: es = [e for e in es if e["section_id"] == section_id]
    if faculty_id: es = [e for e in es if e["faculty_id"] == faculty_id]
    if room_id: es = [e for e in es if e["room_id"] == room_id]
    return es


def pdf_response(story, name, landscape_mode=True):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4) if landscape_mode else A4, leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm, title=name)
    doc.build(story)
    return Response(buf.getvalue(), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{name}.pdf"'})


def table(data, widths=None, header=True):
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")), ("FONTSIZE", (0, 0), (-1, -1), 8),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
               ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")])]
    t.setStyle(TableStyle(st))
    return t


def title_block(text, sub=""):
    s = [Paragraph(f"<b>GIET University, Gunupur - Department of CSE</b>", styles["Title"]), Paragraph(text, styles["Heading2"])]
    if sub: s.append(Paragraph(sub, styles["Normal"]))
    return s + [Spacer(1, 4 * mm)]


def grid_table(ctx, es, mode):
    T = ctx.T
    head = ["Day"] + [f"P{t + 1}\n{SLOTS[t][0]}-{SLOTS[t][1]}" for t in range(T)]
    cells = [[""] * T for _ in DAYS]
    spans = []
    for bl in blocks_of(es).values():
        e = bl[0]
        txt = f"{ctx.subjects[e['subject_id']]['code']}\n"
        txt += {"section": ctx.faculty[e["faculty_id"]]["name"].split(". ")[-1][:18],
                "faculty": ctx.sections[e["section_id"]]["label"], "room": ctx.sections[e["section_id"]]["label"]}[mode]
        txt += f"\n{ctx.rooms[e['room_id']]['name']}" if mode != "room" else f"\n{ctx.faculty[e['faculty_id']]['name'].split('. ')[-1][:14]}"
        cells[e["day"]][bl[0]["slot"]] = txt
        if len(bl) > 1:
            spans.append(("SPAN", (bl[0]["slot"] + 1, e["day"] + 1), (bl[-1]["slot"] + 1, e["day"] + 1)))
    data = [head] + [[DAYS[d]] + cells[d] for d in range(len(DAYS))]
    t = table(data, [18 * mm] + [37 * mm] * T)
    t.setStyle(TableStyle(spans + [("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white]), ("FONTSIZE", (0, 1), (-1, -1), 7),
                                   ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#dbeafe"))]))
    return t


@router.get("/reports/timetable.pdf")
def timetable_pdf(tid: int | None = None, section_id: int | None = None, faculty_id: int | None = None,
                  room_id: int | None = None, db: Session = Depends(get_db), _=Depends(current_user)):
    t, ctx = pick(db, tid), Ctx(db)
    es = service.load_entries(db, t.id)
    if section_id: who, mode = f"Section {ctx.sections[section_id]['label']}", "section"
    elif faculty_id: who, mode = ctx.faculty[faculty_id]["name"], "faculty"
    elif room_id: who, mode = f"Room {ctx.rooms[room_id]['name']}", "room"
    else: raise HTTPException(400, "Give section_id, faculty_id or room_id")
    es = filt(es, section_id, faculty_id, room_id)
    story = title_block(f"Timetable - {who}", f"{t.name}  |  generated {t.created_at:%d %b %Y}") + [grid_table(ctx, es, mode)]
    subs = Counter((e["subject_id"], e["faculty_id"]) for e in es if True)
    rows = [["Code", "Subject", "Faculty", "Periods/week"]] + \
           [[ctx.subjects[s]["code"], ctx.subjects[s]["name"], ctx.faculty[f]["name"], c] for (s, f), c in sorted(subs.items())]
    story += [Spacer(1, 6 * mm), table(rows, [25 * mm, 90 * mm, 70 * mm, 30 * mm])]
    return pdf_response(story, f"timetable_{who.replace(' ', '_')}")


@router.get("/reports/{kind}.pdf")
def report_pdf(kind: str, tid: int | None = None, db: Session = Depends(get_db), _=Depends(require("admin", "faculty"))):
    t, ctx = pick(db, tid), Ctx(db)
    es = service.load_entries(db, t.id)
    a = analyse(ctx, es)
    sub = f"{t.name}  |  overall score {t.score.get('overall')}%"
    if kind == "faculty":
        rows = [["Faculty", "Designation", "Periods", "Max", "Utilization %"]] + \
               [[f["name"], ctx.faculty[f["id"]]["designation"], f["hours"], f["max"], f["pct"]] for f in a["faculty"]]
        story = title_block("Faculty Workload Report", sub) + [table(rows, [70 * mm, 55 * mm, 25 * mm, 25 * mm, 35 * mm])]
    elif kind == "classroom":
        rows = [["Room", "Type", "Capacity", "Periods used", "Occupancy %"]] + \
               [[r["name"], "Lab" if r["is_lab"] else "Classroom", ctx.rooms[r["id"]]["capacity"], r["used"], r["pct"]] for r in a["rooms"]]
        story = title_block("Classroom & Laboratory Report", sub) + [table(rows)]
    elif kind == "utilization":
        r = a["resource"]
        rows = [["Metric", "Value"], ["Teacher utilization", f"{r['teacher_utilization']}%"], ["Room utilization", f"{r['room_utilization']}%"],
                ["Lab utilization", f"{r['lab_utilization']}%"], ["Faculty balance", f"{r['faculty_balance']}%"]] + \
               [[k.replace("_", " ").title(), v] for k, v in t.score.items()]
        story = title_block("Resource Utilization Report", sub) + [table(rows, [90 * mm, 50 * mm])]
    elif kind == "department":
        rows = [["Section", "Students", "Periods/week", "Avg free periods/day"]] + \
               [[s["label"], ctx.sections[s["id"]]["strength"], s["periods"], s["avg_free"]] for s in a["sections"]]
        story = title_block("Department Report - CSE", sub) + [table(rows)]
    elif kind == "analytics":
        s = a["stats"]
        rows = [["Statistic", "Value"]] + [[k.replace("_", " ").title(), v] for k, v in s.items()]
        rows2 = [["Day"] + a["days"], ["Periods"] + a["daily"]]
        rows3 = [["Subject", "Periods"]] + [[x["name"], x["periods"]] for x in a["subjects"]]
        story = title_block("Analytics Report", sub) + [table(rows, [90 * mm, 50 * mm]), Spacer(1, 5 * mm),
                                                          table(rows2), Spacer(1, 5 * mm), table(rows3, [100 * mm, 30 * mm])]
    else:
        raise HTTPException(404, "Unknown report")
    return pdf_response(story, f"{kind}_report", landscape_mode=False)


@router.get("/export/xlsx")
def export_xlsx(tid: int | None = None, db: Session = Depends(get_db), _=Depends(current_user)):
    t, ctx = pick(db, tid), Ctx(db)
    es = service.load_entries(db, t.id)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for sid, s in ctx.sections.items():
            grid = {f"P{k + 1} {SLOTS[k][0]}": [""] * len(DAYS) for k in range(ctx.T)}
            for e in es:
                if e["section_id"] == sid:
                    grid[f"P{e['slot'] + 1} {SLOTS[e['slot']][0]}"][e["day"]] = \
                        f"{ctx.subjects[e['subject_id']]['code']} | {ctx.faculty[e['faculty_id']]['name']} | {ctx.rooms[e['room_id']]['name']}"
            pd.DataFrame(grid, index=DAYS).to_excel(xw, sheet_name=f"Sem{s['label']}")
        a = analyse(ctx, es)
        pd.DataFrame(a["faculty"]).to_excel(xw, sheet_name="Faculty workload", index=False)
        pd.DataFrame(a["rooms"]).to_excel(xw, sheet_name="Rooms", index=False)
    return Response(buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="timetable.xlsx"'})


# ---------------------------------------------------------------------------- calendar export
def term_dates(db):
    start = db.query(m.CalendarEvent).filter_by(kind="semester_start").first()
    end = db.query(m.CalendarEvent).filter_by(kind="semester_end").first()
    s = start.start_date if start else date.today()
    s += timedelta(days=(7 - s.weekday()) % 7)                # first Monday on/after
    e = end.start_date if end else s + timedelta(weeks=16)
    return s, e


def occurrences(ctx, es, db):
    s, e = term_dates(db)
    out = []
    for bl in blocks_of(es).values():
        x = bl[0]
        day = s + timedelta(days=x["day"])
        h1, m1 = map(int, SLOTS[bl[0]["slot"]][0].split(":"))
        h2, m2 = map(int, SLOTS[bl[-1]["slot"]][1].split(":"))
        out.append(dict(start=datetime(day.year, day.month, day.day, h1, m1), end=datetime(day.year, day.month, day.day, h2, m2),
                        title=f"{ctx.subjects[x['subject_id']]['name']} ({ctx.sections[x['section_id']]['label']})",
                        desc=f"Faculty: {ctx.faculty[x['faculty_id']]['name']}", loc=ctx.rooms[x["room_id"]]["name"], until=e))
    return out


@router.get("/export/ics")
def export_ics(tid: int | None = None, section_id: int | None = None, faculty_id: int | None = None,
               room_id: int | None = None, db: Session = Depends(get_db), _=Depends(current_user)):
    t, ctx = pick(db, tid), Ctx(db)
    es = filt(service.load_entries(db, t.id), section_id, faculty_id, room_id)
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//AI Timetable Generator//EN", "CALSCALE:GREGORIAN", "X-WR-TIMEZONE:Asia/Kolkata"]
    for i, o in enumerate(occurrences(ctx, es, db)):
        L += ["BEGIN:VEVENT", f"UID:tt{t.id}-{i}@timetable.local", f"DTSTAMP:{datetime.utcnow():%Y%m%dT%H%M%SZ}",
              f"DTSTART;TZID=Asia/Kolkata:{o['start']:%Y%m%dT%H%M%S}", f"DTEND;TZID=Asia/Kolkata:{o['end']:%Y%m%dT%H%M%S}",
              f"RRULE:FREQ=WEEKLY;UNTIL={o['until']:%Y%m%d}T235959Z", f"SUMMARY:{o['title']}", f"DESCRIPTION:{o['desc']}",
              f"LOCATION:{o['loc']}", "END:VEVENT"]
    L.append("END:VCALENDAR")
    return Response("\r\n".join(L), media_type="text/calendar", headers={"Content-Disposition": 'attachment; filename="timetable.ics"'})


@router.get("/export/gcal-links")
def gcal_links(tid: int | None = None, section_id: int | None = None, faculty_id: int | None = None,
               room_id: int | None = None, db: Session = Depends(get_db), _=Depends(current_user)):
    """One-click 'Add to Google Calendar' links (weekly recurring). For everything at once, import the .ics file."""
    t, ctx = pick(db, tid), Ctx(db)
    es = filt(service.load_entries(db, t.id), section_id, faculty_id, room_id)
    out = []
    for o in occurrences(ctx, es, db):
        recur = quote(f"RRULE:FREQ=WEEKLY;UNTIL={o['until']:%Y%m%d}T235959Z", safe="")
        url = ("https://calendar.google.com/calendar/render?action=TEMPLATE&text=" + quote(o["title"]) +
               f"&dates={o['start']:%Y%m%dT%H%M%S}/{o['end']:%Y%m%dT%H%M%S}&ctz=Asia/Kolkata&recur={recur}"
               f"&details={quote(o['desc'])}&location={quote(o['loc'])}")
        out.append(dict(title=o["title"], when=f"{DAYS[o['start'].weekday()]} {o['start']:%H:%M}-{o['end']:%H:%M}", url=url))
    return out
