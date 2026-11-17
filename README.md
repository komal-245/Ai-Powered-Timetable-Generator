# AI-Powered Timetable Generator — GIET University, CSE

Full-stack project: **React + Tailwind + Chart.js** frontend, **FastAPI + SQLAlchemy** backend,
**Google OR-Tools CP-SAT** scheduling engine, JWT auth, PDF/Excel/ICS exports, chatbot, Docker + CI.

## Your data (loaded automatically on first start)
| File | Becomes |
|---|---|
| `data/Supervisor_List.xlsx` | 40 faculty (duplicate Debasis/Debasish Pradhan merged) + login accounts |
| `data/CSE-B_Proctor_cycle.xlsx` | 57 students of 5th Sem CSE-B, proctor Ms. Shibani Subhadarshini, 5 proctor-cycle dates each |

**Sample data (no source was provided; edit in Master Data):** subjects (3rd & 5th sem CSE), sections 3-A, 3-B, 5-A, 5-C,
rooms (6 classrooms + 3 labs), the teacher-subject "can teach" mapping, a few demo teacher preferences, the academic calendar.
Faculty max hours: Professor 12, Assoc. 14, Asst. 16, Lecturer 18, HOD 8.

## Logins
| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Faculty | email prefix, e.g. `shibanisubhadarshini` | `Giet@123` |
| Student | roll no, e.g. `24cse002` | registration no, e.g. `24UG010069` |

## Run locally
```bash
# backend  (http://localhost:8000, Swagger at /api/docs)
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
# frontend (http://localhost:5173, proxies /api)
cd frontend && npm install && npm run dev
```
Log in as admin -> **AI Generator** -> Generate (about 15-40 s per candidate) -> Activate.

## Docker (PostgreSQL)
`docker compose up --build` -> app at http://localhost:8080, API at :8000. Set `SECRET_KEY` first.
Render: `render.yaml` blueprint (set `VITE_API_URL`). CI: `.github/workflows/ci.yml`.

## AI engine (`backend/app/engine/`)
1. Faculty assignment: load-balanced, randomised per candidate.
2. CP-SAT time placement: hard constraints (no teacher/section/room/lab overlap, required hours, continuous labs never across breaks,
   availability, daily caps) + weighted soft goals (teacher preferences, idle gaps, long theory runs, workload and day balance).
3. CP-SAT room assignment: capacity, no clashes, minimal wastage, a "home" classroom per section.
4. 5-10 candidates are scored, ranked, explained in plain English; the best is flagged.
5. Conflict resolution (`validator.py`, `suggest.py`): drag-and-drop is validated instantly and conflicts come with concrete move suggestions.

## Tests
`cd backend && PYTHONPATH=. pytest -q`

## Notes
* Time grid lives in `backend/app/config.py` (`DAYS=Mon,Tue,Wed,Thu,Fri,Sat` env adds Saturday).
* Labs are 2-period blocks with one teacher; exam timetable is a future enhancement.
* Generation runs in a background thread; use a task queue for multi-worker production.
* Frontend was compile-checked (`vite build`) but not browser-tested; backend is covered by tests.
