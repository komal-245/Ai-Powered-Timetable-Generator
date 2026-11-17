from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from .config import CORS_ORIGINS
from .routers import auth, master, timetable, portal, reports, chat
from .seed import init_db


@asynccontextmanager
async def lifespan(app):
    init_db()                       # create tables + seed from the GIET spreadsheets on first start
    yield


app = FastAPI(title="AI-Powered Timetable Generator", version="1.0.0", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None,
              description="GIET University CSE - OR-Tools CP-SAT timetable engine with REST API")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
for r in (auth, master, timetable, portal, reports, chat):
    app.include_router(r.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
