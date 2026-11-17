"""Independent hard/soft constraint checker. Used for scoring, drag & drop and conflict resolution."""
from collections import defaultdict
from ..config import BREAK_AFTER
from .context import Ctx, blocks_of


def validate(ctx: Ctx, entries: list[dict], blocked: set | None = None, check_hours: bool = True) -> list[dict]:
    blocked = blocked or set()
    V = []

    def add(kind, sev, msg, blocks):
        V.append(dict(type=kind, severity=sev, message=msg, block_ids=sorted(set(blocks))))

    sec, fac, room = defaultdict(list), defaultdict(list), defaultdict(list)
    for e in entries:
        k = (e["day"], e["slot"])
        sec[(e["section_id"],) + k].append(e)
        fac[(e["faculty_id"],) + k].append(e)
        room[(e["room_id"],) + k].append(e)
    from ..config import DAYS, SLOTS
    tl = lambda d, t: f"{DAYS[d]} P{t + 1} ({SLOTS[t][0]})"
    for (s, d, t), es in sec.items():
        if len({e["block_id"] for e in es}) > 1:
            add("section_overlap", "hard", f"Section {ctx.sections[s]['label']} has two classes at {tl(d, t)}", [e["block_id"] for e in es])
    for (f, d, t), es in fac.items():
        if len({e["block_id"] for e in es}) > 1:
            add("teacher_overlap", "hard", f"{ctx.faculty[f]['name']} is double-booked at {tl(d, t)}", [e["block_id"] for e in es])
        if (f, d, t) in ctx.unavail:
            add("faculty_unavailable", "hard", f"{ctx.faculty[f]['name']} is unavailable at {tl(d, t)}", [e["block_id"] for e in es])
    for (r, d, t), es in room.items():
        if len({e["block_id"] for e in es}) > 1:
            add("room_overlap", "hard", f"Room {ctx.rooms[r]['name']} is double-booked at {tl(d, t)}", [e["block_id"] for e in es])
    for e in entries:
        if (e["day"], e["slot"]) in blocked:
            add("blocked_slot", "hard", f"Class placed in a blocked period {tl(e['day'], e['slot'])}", [e["block_id"]])

    bl = blocks_of(entries)
    for bid, es in bl.items():
        e0 = es[0]
        slots = [e["slot"] for e in es]
        if len({e["day"] for e in es}) > 1 or slots != list(range(slots[0], slots[0] + len(slots))) or \
                any(b in BREAK_AFTER for b in range(slots[0], slots[-1])):
            add("not_continuous", "hard", f"{ctx.subjects[e0['subject_id']]['name']} session is not continuous / crosses a break", [bid])
        rm = ctx.rooms[e0["room_id"]]
        if rm["is_lab"] != e0["is_lab"]:
            add("room_type", "hard", f"{ctx.subjects[e0['subject_id']]['name']} needs a {'lab' if e0['is_lab'] else 'classroom'}, got {rm['name']}", [bid])
        elif rm["capacity"] < ctx.sections[e0["section_id"]]["strength"]:
            add("capacity", "hard", f"Room {rm['name']} (cap {rm['capacity']}) too small for {ctx.sections[e0['section_id']]['label']}", [bid])

    if check_hours:
        have = defaultdict(int)
        for e in entries:
            have[(e["section_id"], e["subject_id"])] += 1
        for key, need in ctx.requirements().items():
            if have.get(key, 0) != need:
                add("hours", "hard", f"{ctx.subjects[key[1]]['code']} for {ctx.sections[key[0]]['label']}: {have.get(key, 0)}/{need} periods scheduled", [])

    wk = defaultdict(int)
    for e in entries:
        wk[e["faculty_id"]] += 1
    for f, h in wk.items():
        if h > ctx.faculty[f]["max_hours"]:
            add("overload", "soft", f"{ctx.faculty[f]['name']} has {h} periods (max {ctx.faculty[f]['max_hours']})", [])
    return V
