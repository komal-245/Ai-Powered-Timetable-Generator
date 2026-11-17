import os

_db = os.getenv("DATABASE_URL", "sqlite:///./timetable.db")
if _db.startswith("postgres://"):               # Render/Heroku style URL
    _db = _db.replace("postgres://", "postgresql://", 1)
DATABASE_URL = _db
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
TOKEN_MINUTES = int(os.getenv("TOKEN_MINUTES", "720"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "data"))

# Optional LLM for the chatbot (e.g. a local Ollama: http://localhost:11434)
OLLAMA_URL = os.getenv("OLLAMA_URL", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

# ---- Time grid ------------------------------------------------------------
DAYS = os.getenv("DAYS", "Mon,Tue,Wed,Thu,Fri").split(",")
SLOTS = [("08:00", "09:00"), ("09:00", "10:00"),      # tea break 10:50-11:05
         ("10:20", "11:20"), ("11:20", "12:20"),      # lunch 12:55-13:45
         ("12:20", "13:20")]
BREAK_AFTER = {1, 2}      # a physical break follows these slot indexes
LUNCH_AFTER = 3
MORNING = range(0, 2)
AFTERNOON = range(2,5)
