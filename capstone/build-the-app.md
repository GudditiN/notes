---
description: "Write the FastAPI service and package it as a non-root container image."
icon: code
---

# 1. Build and containerize the app

## Step 1 — The application

{% code title="app/main.py" %}
```python
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
```
{% endcode %}

{% code title="app/requirements.txt" %}
```text
fastapi==0.115.0
uvicorn[standard]==0.30.6
psycopg[binary]==3.2.3
psycopg-pool==3.2.3
prometheus-client==0.21.0
```
{% endcode %}

## Step 2 — Containerize it

{% code title="app/Dockerfile" %}
```docker
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY main.py .

RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin appuser
USER 10001

EXPOSE 8000
# exec form: uvicorn is PID 1 and receives SIGTERM directly for graceful shutdown
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
```
{% endcode %}

{% code title="app/.dockerignore" %}
```text
__pycache__/
*.pyc
.venv/
.env
```
{% endcode %}

```bash
cd app
docker build -t notes-api:1.0.0 .
# quick local sanity check (fails readiness without a DB, but / and /healthz respond)
docker run --rm -p 8000:8000 -e DB_HOST=x -e DB_NAME=x -e DB_USER=x -e DB_PASSWORD=x notes-api:1.0.0
curl localhost:8000/healthz
```
