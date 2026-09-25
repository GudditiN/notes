import os
import socket
import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field
from psycopg_pool import ConnectionPool
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("notes")

CONNINFO = (
    f"host={os.environ['DB_HOST']} port={os.getenv('DB_PORT', '5432')} "
    f"dbname={os.environ['DB_NAME']} user={os.environ['DB_USER']} "
    f"password={os.environ['DB_PASSWORD']} connect_timeout=3"
)
pool = ConnectionPool(CONNINFO, min_size=1, max_size=int(os.getenv("DB_POOL_MAX", "5")), open=False)
schema_ready = False

def ensure_schema() -> None:
    """Create the table once. Safe to call repeatedly."""
    global schema_ready
    if schema_ready:
        return
    with pool.connection(timeout=3) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS notes ("
            " id SERIAL PRIMARY KEY,"
            " text TEXT NOT NULL,"
            " created_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
    schema_ready = True
    log.info("schema ready")

@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open(wait=False)
    try:
        ensure_schema()
    except Exception as exc:  # DB may still be starting; readiness will retry
        log.warning("database not ready at startup: %s", exc)
    yield
    log.info("shutting down, closing pool")
    pool.close()

app = FastAPI(title="notes-api", lifespan=lifespan)

REQUESTS = Counter("http_requests_total", "Total HTTP requests", ["method", "route", "status"])
LATENCY = Histogram("http_request_duration_seconds", "Request latency in seconds", ["method", "route"])

@app.middleware("http")
async def observe(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    path = route.path if route else "unmatched"
    if path != "/metrics":
        REQUESTS.labels(request.method, path, str(response.status_code)).inc()
        LATENCY.labels(request.method, path).observe(time.perf_counter() - start)
    return response

class NoteIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)

@app.get("/")
def root():
    return {
        "app": "notes-api",
        "env": os.getenv("APP_ENV", "dev"),
        "greeting": os.getenv("GREETING", "hello"),
        "pod": socket.gethostname(),
    }

@app.get("/healthz")
def healthz():
    # Liveness: only proves the process responds. Never checks the DB.
    return {"status": "ok"}

@app.get("/ready")
def ready():
    # Readiness: can we serve real requests right now?
    try:
        ensure_schema()
        with pool.connection(timeout=2) as conn:
            conn.execute("SELECT 1")
        return {"status": "ready"}
    except Exception as exc:
        log.warning("readiness failed: %s", exc)
        raise HTTPException(status_code=503, detail="database unavailable")

@app.get("/notes")
def list_notes():
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT id, text, created_at FROM notes ORDER BY id DESC LIMIT 100"
        ).fetchall()
    return [{"id": r[0], "text": r[1], "created_at": r[2].isoformat()} for r in rows]

@app.post("/notes", status_code=201)
def create_note(note: NoteIn):
    with pool.connection() as conn:
        row = conn.execute(
            "INSERT INTO notes (text) VALUES (%s) RETURNING id", (note.text,)
        ).fetchone()
    return {"id": row[0], "text": note.text}

@app.get("/burn")
def burn(ms: int = 200):
    # Burns CPU so you can watch the HPA react.
    ms = max(1, min(ms, 2000))
    end = time.perf_counter() + ms / 1000
    n = 0
    while time.perf_counter() < end:
        n += 1
    return {"burned_ms": ms, "pod": socket.gethostname()}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
