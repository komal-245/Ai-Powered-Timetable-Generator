from collections import Counter, defaultdict
from ..config import DAYS, SLOTS
from .context import Ctx
from .scoring import score
from .validator import validate


def analyse(ctx: Ctx, entries: list[dict]) -> dict:
    D, T = ctx.D, ctx.T
    wk = Counter(e["faculty_id"] for e in entries)
    room_used = Counter(e["room_id"] for e in entries)
    heat = [[0] * T for _ in range(D)]
    for e in entries:
        heat[e["day"]][e["slot"]] += 1
    daily = [sum(r) for r in heat]
    by_slot = [sum(heat[d][t] for d in range(D)) for t in range(T)]
    total_slots = D * T

    def room_row(r):
        return dict(id=r["id"], name=r["name"], is_lab=r["is_lab"], used=room_used.get(r["id"], 0),
                    pct=round(100 * room_used.get(r["id"], 0) / total_slots, 1))
    rooms = [room_row(r) for r in ctx.rooms.values()]
    cls = [r for r in rooms if not r["is_lab"]]
    labs = [r for r in rooms if r["is_lab"]]

    fac = [dict(id=f["id"], name=f["name"], hours=wk.get(f["id"], 0), max=f["max_hours"],
                pct=round(100 * wk.get(f["id"], 0) / f["max_hours"], 1)) for f in ctx.faculty.values()]
    subj = Counter(e["subject_id"] for e in entries)
    subjects = [dict(code=ctx.subjects[s]["code"], name=ctx.subjects[s]["name"], periods=c) for s, c in subj.most_common()]

    # free periods per section-day (days having classes)
    occ = defaultdict(lambda: defaultdict(set))
    for e in entries:
        occ[e["section_id"]][e["day"]].add(e["slot"])
    free = {sid: round(sum(T - len(s) for s in days.values()) / max(1, len(days)), 1) for sid, days in occ.items()}
    sections = [dict(id=sid, label=s["label"], periods=sum(len(v) for v in occ[sid].values()),
                     avg_free=free.get(sid, T)) for sid, s in ctx.sections.items()]

    sc = score(ctx, entries) if entries else {}
    teacher_cap = sum(f["max_hours"] for f in ctx.faculty.values() if wk.get(f["id"]))
    resource = dict(
        teacher_utilization=round(100 * sum(wk.values()) / teacher_cap, 1) if teacher_cap else 0,
        room_utilization=round(sum(r["pct"] for r in cls) / len(cls), 1) if cls else 0,
        lab_utilization=round(sum(r["pct"] for r in labs) / len(labs), 1) if labs else 0,
        faculty_balance=sc.get("teacher_balance", 0))
    active = [f for f in fac if f["hours"] > 0]
    stats = dict(
        peak_hour=f"P{by_slot.index(max(by_slot)) + 1} ({SLOTS[by_slot.index(max(by_slot))][0]})" if entries else "-",
        most_crowded_day=DAYS[daily.index(max(daily))] if entries else "-",
        least_occupied_room=min(rooms, key=lambda r: r["used"])["name"] if rooms else "-",
        faculty_utilization=resource["teacher_utilization"],
        avg_free_periods=round(sum(free.values()) / len(free), 1) if free else 0,
        optimization_score=sc.get("overall", 0), active_faculty=len(active))
    return dict(faculty=sorted(fac, key=lambda f: -f["hours"]), rooms=rooms, subjects=subjects, daily=daily,
                days=DAYS, heatmap=heat, slots=[s[0] for s in SLOTS], sections=sections, resource=resource,
                stats=stats, score=sc)


def smart_notifications(ctx: Ctx, entries: list[dict]) -> list[dict]:
    out, a = [], analyse(ctx, entries)
    for f in a["faculty"]:
        if f["hours"] > f["max"]:
            out.append(dict(level="warning", kind="overload", message=f"Teacher overloaded: {f['name']} has {f['hours']}/{f['max']} periods"))
    for r in a["rooms"]:
        if not r["is_lab"] and r["pct"] < 20:
            out.append(dict(level="info", kind="room_underused", message=f"Room underutilized: {r['name']} used only {r['pct']}% of the week"))
        if r["is_lab"] and r["used"] == 0:
            out.append(dict(level="warning", kind="lab_unused", message=f"Lab idle: {r['name']} has no sessions scheduled"))
    for v in validate(ctx, entries):
        if v["type"] == "hours":
            out.append(dict(level="danger", kind="hours", message=f"Subject hours incomplete - {v['message']}"))
        elif v["severity"] == "hard":
            out.append(dict(level="danger", kind=v["type"], message=v["message"]))
    if not entries:
        out.append(dict(level="info", kind="empty", message="No timetable generated yet"))
    return out


def room_status(ctx, entries, room_id, now_day, now_slot):
    mine = {(e["day"], e["slot"]): e for e in entries if e["room_id"] == room_id}
    sched = [dict(day=d, slot=t, **{"section": ctx.sections[e["section_id"]]["label"],
                                    "subject": ctx.subjects[e["subject_id"]]["name"],
                                    "faculty": ctx.faculty[e["faculty_id"]]["name"]})
             for (d, t), e in sorted(mine.items())]
    free = [dict(day=d, slot=t) for d in range(ctx.D) for t in range(ctx.T) if (d, t) not in mine]
    cur = mine.get((now_day, now_slot))
    upcoming = [s for s in sched if (s["day"], s["slot"]) > (now_day, now_slot)][:5]
    return dict(room=ctx.rooms[room_id], current=next((s for s in sched if (s["day"], s["slot"]) == (now_day, now_slot)), None),
                upcoming=upcoming, free_slots=free, schedule=sched,
                occupancy_pct=round(100 * len(mine) / (ctx.D * ctx.T), 1))
