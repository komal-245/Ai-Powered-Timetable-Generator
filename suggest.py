"""AI conflict resolution: propose concrete moves instead of just reporting a conflict."""
from ..config import DAYS, SLOTS
from .context import Ctx, blocks_of
from .scoring import score
from .validator import validate
from .solver import valid_starts


def free_room(ctx, entries, bid, day, start, L, prefer=None):
    sec = next(e for e in entries if e["block_id"] == bid)
    lab = sec["is_lab"]
    strength = ctx.sections[sec["section_id"]]["strength"]
    busy = {(e["room_id"], e["day"], e["slot"]) for e in entries if e["block_id"] != bid}
    pool = [r for r, rm in ctx.rooms.items() if rm["is_lab"] == lab and rm["capacity"] >= strength
            and all((r, day, k) not in busy for k in range(start, start + L))]
    if not pool:
        return None
    if prefer in pool:
        return prefer
    return min(pool, key=lambda r: ctx.rooms[r]["capacity"])


def apply_move(ctx, entries, bid, day, start):
    """Return (new_entries, error). Room is kept when free, otherwise a free room is picked."""
    bl = blocks_of(entries)[bid]
    L = len(bl)
    room = free_room(ctx, entries, bid, day, start, L, prefer=bl[0]["room_id"])
    if room is None:
        return None, "No free room of the right type/capacity at that time"
    new = []
    for e in entries:
        if e["block_id"] == bid:
            k = e["slot"] - bl[0]["slot"]
            e = {**e, "day": day, "slot": start + k, "room_id": room}
        new.append(e)
    return new, None


def label(ctx, e0):
    return f"{ctx.subjects[e0['subject_id']]['name']} ({ctx.sections[e0['section_id']]['label']})"


def suggest_moves(ctx, entries, bid, blocked=None, limit=3, ignore=()):
    bl = blocks_of(entries)[bid]
    L, e0 = len(bl), bl[0]
    out = []
    for d in range(ctx.D):
        for t in valid_starts(ctx.T, L):
            if (d, t) == (e0["day"], e0["slot"]):
                continue
            new, err = apply_move(ctx, entries, bid, d, t)
            if err:
                continue
            V = [v for v in validate(ctx, new, blocked, check_hours=False) if v["severity"] == "hard"]
            if V:
                continue
            out.append((score(ctx, new, [], blocked)["overall"], d, t))
    out.sort(reverse=True)
    return [dict(block_id=bid, subject=label(ctx, e0),
                 from_=f"{DAYS[e0['day']]} P{e0['slot'] + 1} {SLOTS[e0['slot']][0]}",
                 to=f"{DAYS[d]} P{t + 1} {SLOTS[t][0]}", day=d, slot=t, resulting_score=sc,
                 text=f"Move {label(ctx, e0)}: {DAYS[e0['day']]} {SLOTS[e0['slot']][0]} -> {DAYS[d]} {SLOTS[t][0]}")
            for sc, d, t in out[:limit]]
