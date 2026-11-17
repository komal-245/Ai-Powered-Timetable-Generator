"""AI scheduling engine - Google OR-Tools CP-SAT.

Stage 0  faculty assignment (load-balanced, randomised per candidate)
Stage 1  CP-SAT places every session (day, start period)   -> hard + soft constraints
Stage 2  CP-SAT assigns rooms (capacity, no clash, home-room preference, minimal wastage)
Several candidates are produced with different seeds / objective profiles, scored and ranked.
"""
import math
import os
import random
from collections import defaultdict
from ortools.sat.python import cp_model
from ..config import BREAK_AFTER, LUNCH_AFTER, MORNING, AFTERNOON
from .context import Ctx

PROFILES = {   # weight multipliers for the soft objective
    "balanced": dict(pref=1, idle_sec=1, idle_fac=1, consec=1, load=1, sec_bal=1),
    "teacher-friendly": dict(pref=3, idle_sec=1, idle_fac=2, consec=1, load=2, sec_bal=1),
    "student-friendly": dict(pref=1, idle_sec=3, idle_fac=1, consec=3, load=1, sec_bal=3),
    "compact": dict(pref=1, idle_sec=3, idle_fac=3, consec=1, load=1, sec_bal=1),
    "workload-balanced": dict(pref=1, idle_sec=1, idle_fac=1, consec=1, load=4, sec_bal=2),
}


class SchedulingError(Exception):
    pass


def valid_starts(T, L):
    return [t for t in range(T - L + 1) if not any(b in BREAK_AFTER for b in range(t, t + L - 1))]


def assign_faculty(ctx: Ctx, rng: random.Random):
    """Pick one teacher per (section, subject); balance load relative to each teacher's maximum."""
    jobs = [(sid, x) for sid in ctx.sections for x in ctx.section_subjects(sid)]
    jobs.sort(key=lambda j: (-j[1]["hours"], rng.random()))
    load, out = defaultdict(int), {}
    for sid, sub in jobs:
        cands = ctx.eligible.get(sub["id"]) or [f for f in ctx.faculty if ctx.faculty[f]["active"]]
        fits = [f for f in cands if load[f] + sub["hours"] <= ctx.faculty[f]["max_hours"]] or cands
        f = min(fits, key=lambda f: (load[f] + sub["hours"]) / ctx.faculty[f]["max_hours"] + rng.random() * 0.2)
        out[(sid, sub["id"])] = f
        load[f] += sub["hours"]
    return out


def build_sessions(ctx, assign):
    sess, uid = [], 0
    for (sid, subj_id), f in assign.items():
        sub = ctx.subjects[subj_id]
        if sub["is_lab"]:
            for _ in range(max(1, sub["hours"] // 2)):
                sess.append(dict(uid=uid, sec=sid, subj=subj_id, fac=f, L=2, lab=True)); uid += 1
        else:
            for _ in range(sub["hours"]):
                sess.append(dict(uid=uid, sec=sid, subj=subj_id, fac=f, L=1, lab=False)); uid += 1
    return sess


def solve_times(ctx, sess, blocked, profile, seed, time_limit, workers):
    D, T = ctx.D, ctx.T
    W = PROFILES[profile]
    rng = random.Random(seed)
    M = cp_model.CpModel()
    x, terms = {}, []
    sec_occ, fac_occ = defaultdict(list), defaultdict(list)
    room_cnt, lab_cnt, sec_th = defaultdict(list), defaultdict(list), defaultdict(list)
    subj_day = defaultdict(list)
    n_cls = sum(1 for r in ctx.rooms.values() if not r["is_lab"])
    n_lab = sum(1 for r in ctx.rooms.values() if r["is_lab"])

    for s in sess:
        opts = []
        p = ctx.prefs.get(s["fac"])
        for d in range(D):
            for t in valid_starts(T, s["L"]):
                occ = range(t, t + s["L"])
                if any((d, k) in blocked or (s["fac"], d, k) in ctx.unavail for k in occ):
                    continue
                v = M.NewBoolVar(f"x{s['uid']}_{d}_{t}")
                x[(s["uid"], d, t)] = v
                opts.append(v)
                cost = rng.randint(0, 2)                           # tie-break noise -> candidate diversity
                for k in occ:
                    sec_occ[(s["sec"], d, k)].append(v)
                    fac_occ[(s["fac"], d, k)].append(v)
                    (lab_cnt if s["lab"] else room_cnt)[(d, k)].append(v)
                    if not s["lab"]:
                        sec_th[(s["sec"], d, k)].append(v)
                    if p:
                        if (p["shift"] == "morning" and k not in MORNING) or (p["shift"] == "afternoon" and k not in AFTERNOON):
                            cost += 2 * W["pref"]
                        if d in p["no_days"]:
                            cost += 8 * W["pref"]
                        if (d, k) in p["free_slots"]:
                            cost += 4 * W["pref"]
                if cost:
                    terms.append((cost, v))
                subj_day[(s["sec"], s["subj"], d)].append((s["uid"], v))
        if not opts:
            raise SchedulingError(f"No feasible period for {ctx.subjects[s['subj']]['name']} "
                                  f"(teacher {ctx.faculty[s['fac']]['name']}) - check availability/blocked periods")
        M.AddExactlyOne(opts)

    for key, vs in sec_occ.items():  M.AddAtMostOne(vs)
    for key, vs in fac_occ.items():  M.AddAtMostOne(vs)
    for d in range(D):
        for t in range(T):
            if lab_cnt[(d, t)]:  M.Add(sum(lab_cnt[(d, t)]) <= n_lab)
            if room_cnt[(d, t)]: M.Add(sum(room_cnt[(d, t)]) <= n_cls)
    # a subject appears at most ceil(n/D) times a day for a section
    n_per = defaultdict(int)
    for s in sess: n_per[(s["sec"], s["subj"])] += 1
    for (sec, subj, d), lst in subj_day.items():
        M.Add(sum(v for _, v in lst) <= math.ceil(n_per[(sec, subj)] / D))

    Z = M.NewConstant(0)

    def act_of(vs):
        if not vs: return Z
        a = M.NewBoolVar("")
        M.Add(a == sum(vs))
        return a

    def gaps(acts, w):
        before = [M.NewBoolVar("") for _ in range(T)]
        after = [M.NewBoolVar("") for _ in range(T)]
        for t in range(T):
            if t > 0:
                M.Add(before[t] >= acts[t - 1]); M.Add(before[t] >= before[t - 1])
            if t < T - 1:
                M.Add(after[t] >= acts[t + 1]); M.Add(after[t] >= after[t + 1])
            h = M.NewBoolVar("")
            M.Add(h >= before[t] + after[t] - acts[t] - 1)
            terms.append((w, h))

    # hard: daily caps ; soft: idle gaps, consecutive theory
    for sid in ctx.sections:
        for d in range(D):
            acts = [act_of(sec_occ[(sid, d, t)]) for t in range(T)]
            M.Add(sum(acts) <= 6)
            gaps(acts, 6 * W["idle_sec"])
            ths = [act_of(sec_th[(sid, d, t)]) for t in range(T)]
            for t in range(T - 2):
                if t <= LUNCH_AFTER < t + 2:
                    continue
                r = M.NewBoolVar("")
                M.Add(r >= ths[t] + ths[t + 1] + ths[t + 2] - 2)
                terms.append((4 * W["consec"], r))
    for sid in ctx.sections:                      # balance the days of a section
        pk = M.NewIntVar(0, T, "")
        for d in range(D):
            M.Add(pk >= sum(v for t in range(T) for v in sec_occ[(sid, d, t)]))
        terms.append((3 * W["sec_bal"], pk))

    used_f = {s["fac"] for s in sess}
    for f in used_f:
        p = ctx.prefs.get(f, {})
        mpd = p.get("max_per_day", 6)
        peak = M.NewIntVar(0, T, "")
        for d in range(D):
            acts = [act_of(fac_occ[(f, d, t)]) for t in range(T)]
            M.Add(sum(acts) <= 6)
            M.Add(peak >= sum(acts))
            ex = M.NewIntVar(0, T, "")
            M.Add(ex >= sum(acts) - mpd)
            terms.append((5 * W["pref"], ex))
            gaps(acts, 2 * W["idle_fac"])
        terms.append((2 * W["load"], peak))

    # phase 1: find any feasible timetable fast (hard constraints only) and use it as a hint
    S1 = cp_model.CpSolver()
    S1.parameters.max_time_in_seconds = max(20, time_limit * 2)
    S1.parameters.num_workers = workers
    S1.parameters.random_seed = seed
    S1.parameters.stop_after_first_solution = True
    st1 = S1.Solve(M)
    if st1 == cp_model.INFEASIBLE:
        raise SchedulingError("No feasible timetable under the hard constraints "
                              "(too many hours for the available teachers/rooms or too many blocked periods).")
    if st1 in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for v in x.values():
            M.AddHint(v, S1.Value(v))
    # phase 2: improve the soft objective within the time limit
    M.Minimize(sum(c * v for c, v in terms))
    S = cp_model.CpSolver()
    S.parameters.max_time_in_seconds = time_limit
    S.parameters.num_workers = workers
    S.parameters.random_seed = seed
    st = S.Solve(M)
    if st == cp_model.INFEASIBLE:
        raise SchedulingError("No feasible timetable under the hard constraints "
                              "(too many hours for the available teachers/rooms or too many blocked periods).")
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise SchedulingError(f"No solution found within {time_limit}s - increase the time limit per candidate.")
    placed = []
    for s in sess:
        for d in range(D):
            for t in valid_starts(T, s["L"]):
                v = x.get((s["uid"], d, t))
                if v is not None and S.Value(v):
                    placed.append({**s, "day": d, "start": t})
    return placed, S.ObjectiveValue()


def assign_rooms(ctx, placed, seed, time_limit=10):
    M = cp_model.CpModel()
    z, occ, cost = {}, defaultdict(list), []
    secs = {p["sec"] for p in placed}
    home = {(s, r): M.NewBoolVar("") for s in secs for r, rm in ctx.rooms.items() if not rm["is_lab"]}
    for s in secs:
        M.AddExactlyOne([home[(s, r)] for r, rm in ctx.rooms.items() if not rm["is_lab"]])
    warn = False
    for p in placed:
        strength = ctx.sections[p["sec"]]["strength"]
        pool = [r for r, rm in ctx.rooms.items() if rm["is_lab"] == p["lab"] and rm["capacity"] >= strength]
        if not pool:
            warn = True
            pool = [r for r, rm in ctx.rooms.items() if rm["is_lab"] == p["lab"]]
        if not pool:
            raise SchedulingError("No rooms of the required type exist")
        vs = []
        for r in pool:
            v = M.NewBoolVar(""); z[(p["uid"], r)] = v; vs.append(v)
            for k in range(p["start"], p["start"] + p["L"]):
                occ[(r, p["day"], k)].append(v)
            cost.append(max(0, ctx.rooms[r]["capacity"] - strength) // 4 * v)
            if not p["lab"]:
                w = M.NewBoolVar(""); M.Add(w <= v); M.Add(w <= home[(p["sec"], r)])
                cost.append(-5 * w)
        M.AddExactlyOne(vs)
    for vs in occ.values():
        M.AddAtMostOne(vs)
    M.Minimize(sum(cost))
    S = cp_model.CpSolver()
    S.parameters.max_time_in_seconds = time_limit
    S.parameters.num_workers = 4
    S.parameters.random_seed = seed
    if S.Solve(M) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise SchedulingError("Room assignment failed - not enough rooms of suitable capacity")
    for p in placed:
        p["room"] = next(r for (u, r), v in z.items() if u == p["uid"] and S.Value(v))
    return placed


def to_entries(placed):
    out = []
    for p in placed:
        for k in range(p["L"]):
            out.append(dict(block_id=p["uid"], section_id=p["sec"], subject_id=p["subj"], faculty_id=p["fac"],
                            room_id=p["room"], day=p["day"], slot=p["start"] + k, is_lab=p["lab"]))
    return out


def generate_candidate(ctx, index, blocked=None, time_limit=10, workers=None):
    workers = workers or min(8, os.cpu_count() or 4)
    names = list(PROFILES)
    profile = names[index % len(names)]
    seed = 1000 + 37 * index
    rng = random.Random(seed)
    assign = assign_faculty(ctx, rng)
    sess = build_sessions(ctx, assign)
    placed, obj = solve_times(ctx, sess, blocked or set(), profile, seed, time_limit, workers)
    placed = assign_rooms(ctx, placed, seed)
    return dict(entries=to_entries(placed), profile=profile, seed=seed, objective=obj)
