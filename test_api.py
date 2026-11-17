import os, time
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def client():
    if os.path.exists("test.db"): os.remove("test.db")
    with TestClient(app) as c:
        yield c
    os.remove("test.db")


def auth(c, u, p):
    r = c.post("/api/auth/login", json=dict(username=u, password=p))
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def test_seed_counts(client):
    h = auth(client, "admin", "admin123")
    assert len(client.get("/api/faculty", headers=h).json()) == 40
    assert len(client.get("/api/students", headers=h).json()) == 57
    assert client.post("/api/auth/login", json=dict(username="admin", password="x")).status_code == 401


def test_roles(client):
    s = auth(client, "24cse002", "24UG010069")
    assert client.post("/api/rooms", json=dict(name="X", capacity=10), headers=s).status_code == 403
    p = client.get("/api/me/proctor", headers=s).json()
    assert p["student"]["name"] == "Niranjan Nanda" and len(p["cycles"]) == 5


def test_generate_validate_dragdrop_exports(client):
    h = auth(client, "admin", "admin123")
    jid = client.post("/api/timetables/generate", json=dict(candidates=2, time_limit=4,
                      blocked=[dict(day=4, slots=[4, 5, 6])]), headers=h).json()["job_id"]
    for _ in range(120):
        j = client.get(f"/api/timetables/jobs/{jid}", headers=h).json()
        if j["status"] != "running": break
        time.sleep(1)
    assert j["status"] == "done", j
    tid = j["best_id"]
    d = client.get(f"/api/timetables/{tid}", headers=h).json()
    assert d["score"]["hard_violations"] == 0 and len(d["entries"]) == 112
    assert not any(e["day"] == 4 and e["slot"] >= 4 for e in d["entries"])      # constraint honoured
    client.post(f"/api/timetables/{tid}/activate", headers=h)
    # drag a class onto a time that clashes with the same section -> rejected with suggestions
    e0 = d["entries"][0]
    other = next(e for e in d["entries"] if e["section_id"] == e0["section_id"] and e["block_id"] != e0["block_id"] and not e["is_lab"])
    r = client.post(f"/api/timetables/{tid}/move", json=dict(block_id=e0["block_id"], day=other["day"], slot=other["slot"]), headers=h).json()
    assert r["ok"] is False and r["conflicts"]
    assert client.get(f"/api/timetables/{tid}/analytics", headers=h).json()["resource"]
    sec = e0["section_id"]
    assert client.get(f"/api/reports/timetable.pdf?section_id={sec}", headers=h).content[:4] == b"%PDF"
    assert client.get("/api/reports/faculty.pdf", headers=h).content[:4] == b"%PDF"
    assert b"BEGIN:VCALENDAR" in client.get(f"/api/export/ics?section_id={sec}", headers=h).content
    assert client.get("/api/export/xlsx", headers=h).content[:2] == b"PK"
    f = auth(client, "shibanisubhadarshini", "Giet@123")
    assert client.get("/api/me/timetable", headers=f).json()["entries"] is not None
    c = client.post("/api/chat", json=dict(message="Who teaches AI?"), headers=h).json()
    assert "Artificial Intelligence" in c["reply"]
    assert "Free classrooms" in client.post("/api/chat", json=dict(message="Find an empty classroom at 2 PM"), headers=h).json()["reply"]
