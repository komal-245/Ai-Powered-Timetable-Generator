"""Quality score of a timetable (0-100 per dimension)."""
import statistics as st
from collections import defaultdict
from ..config import LUNCH_AFTER, MORNING, AFTERNOON
from .context import Ctx, blocks_of
from .validator import validate


def _clip(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))


def idle_and_runs(ctx, entries):
    """per section: idle gaps and 3-in-a-row theory windows; per section-day load"""
    occ = defaultdict(lambda: defaultdict(set))       # section -> day -> slots
    th = defaultdict(lambda: defaultdict(set))
    for e in entries:
        occ[e["section_id"]][e["day"]].add(e["slot"])
        if not e["is_lab"]:
            th[e["section_id"]][e["day"]].add(e["slot"])
    idle = runs = 0
    for s, days in occ.items():
        for d, sl in days.items():
            idle += (max(sl) - min(sl) + 1) - len(sl)
            for t in range(ctx.T - 2):
                if all(x in th[s][d] for x in (t, t + 1, t + 2)) and not (t <= LUNCH_AFTER < t + 2):
                    runs += 1
    return idle, runs, occ


def score(ctx: Ctx, entries: list[dict], violations: list | None = None, blocked=None) -> dict:
    V = violations if violations is not None else validate(ctx, entries, blocked)
    hard = [v for v in V if v["severity"] == "hard"]
    conflict = _clip(100 - 12 * len(hard))

    # --- teacher balance: weekly load CV relative to capacity + daily peak
    wk, daily = defaultdict(int), defaultdict(lambda: defaultdict(int))
    for e in entries:
        wk[e["faculty_id"]] += 1
        daily[e["faculty_id"]][e["day"]] += 1
    rel = [h / ctx.faculty[f]["max_hours"] for f, h in wk.items()]
    cv = (st.pstdev(rel) / st.mean(rel)) if len(rel) > 1 and st.mean(rel) else 0
    peak = st.mean([max(d.values()) - (sum(d.values()) / ctx.D) for d in daily.values()]) if daily else 0
    over = sum(1 for f, h in wk.items() if h > ctx.faculty[f]["max_hours"])
    teacher = _clip(100 - 45 * cv - 8 * peak - 10 * over)

    # --- room usage: fit of strength/capacity + home-room consistency
    fits, home = [], defaultdict(lambda: defaultdict(int))
    for bl in blocks_of(entries).values():
        e = bl[0]
        if not e["is_lab"]:
            fits.append(min(1, ctx.sections[e["section_id"]]["strength"] / ctx.rooms[e["room_id"]]["capacity"]))
            home[e["section_id"]][e["room_id"]] += len(bl)
    consist = [max(v.values()) / sum(v.values()) for v in home.values()] or [1]
    room = _clip(100 * (0.7 * min(1, (st.mean(fits) if fits else 1) / 0.9) + 0.3 * st.mean(consist)))

    # --- student comfort
    idle, runs, occ = idle_and_runs(ctx, entries)
    n = max(1, len(ctx.sections))
    spread = []
    for s, days in occ.items():
        cnt = [len(days.get(d, ())) for d in range(ctx.D)]
        spread.append(st.pstdev(cnt))
    comfort = _clip(100 - (4 * idle + 3 * runs) / n - 6 * (st.mean(spread) if spread else 0))

    # --- teacher preference satisfaction
    tot = bad = 0
    for e in entries:
        p = ctx.prefs.get(e["faculty_id"])
        tot += 1
        if not p:
            continue
        if (p["shift"] == "morning" and e["slot"] not in MORNING) or (p["shift"] == "afternoon" and e["slot"] not in AFTERNOON):
            bad += 1
        elif e["day"] in p["no_days"] or (e["day"], e["slot"]) in p["free_slots"]:
            bad += 1
    for f, dd in daily.items():
        p = ctx.prefs.get(f)
        if p:
            bad += sum(max(0, c - p["max_per_day"]) for c in dd.values())
    pref = _clip(100 * (1 - bad / tot)) if tot else 100

    overall = 0.30 * conflict + 0.20 * teacher + 0.15 * room + 0.25 * comfort + 0.10 * pref
    if hard:
        overall = min(overall, conflict)
    r = lambda x: round(x, 1)
    return dict(overall=r(overall), conflict=r(conflict), teacher_balance=r(teacher), room_usage=r(room),
                student_comfort=r(comfort), preference=r(pref), idle_periods=idle, long_theory_runs=runs,
                hard_violations=len(hard), soft_warnings=len(V) - len(hard))
