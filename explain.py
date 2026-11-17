from collections import Counter
from .context import Ctx


def explain(ctx: Ctx, entries, sc, profile="balanced", violations=None) -> str:
    wk = Counter(e["faculty_id"] for e in entries)
    busiest = max(wk, key=wk.get) if wk else None
    parts = []
    if sc["hard_violations"] == 0:
        parts.append("All mandatory constraints are satisfied: no teacher, classroom or laboratory overlaps, "
                     "every subject receives its required hours, labs are continuous and rooms fit their sections.")
    else:
        parts.append(f"{sc['hard_violations']} mandatory constraint(s) still need attention - see the conflict list.")
    parts.append(f"Teaching load is spread across {len(wk)} faculty members"
                 + (f" (highest: {ctx.faculty[busiest]['name']} with {wk[busiest]} periods)" if busiest else "")
                 + f", giving a teacher-balance score of {sc['teacher_balance']}%.")
    parts.append(f"Classrooms are matched to section strength (room usage {sc['room_usage']}%), "
                 f"students have {sc['idle_periods']} idle period(s) in the week and {sc['long_theory_runs']} long theory run(s) "
                 f"(comfort {sc['student_comfort']}%). Faculty preferences are {sc['preference']}% satisfied.")
    parts.append(f"Candidate was optimised with the '{profile}' objective profile.")
    return " ".join(parts)
