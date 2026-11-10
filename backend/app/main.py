import psycopg
import redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(title="Dareecha API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Liveness check. Needs no external services (used in CI tests)."""
    return {"status": "ok"}


@app.get("/health/deps")
def health_deps():
    """Checks Postgres, pgvector and Redis are reachable."""
    result = {"postgres": False, "pgvector": False, "redis": False}

    try:
        with psycopg.connect(settings.database_url, connect_timeout=2) as conn:
            conn.execute("SELECT 1")
            result["postgres"] = True
            row = conn.execute(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            ).fetchone()
            result["pgvector"] = row is not None
    except Exception as exc:  # noqa: BLE001
        result["postgres_error"] = str(exc)

    try:
        result["redis"] = bool(redis.from_url(settings.redis_url).ping())
    except Exception as exc:  # noqa: BLE001
        result["redis_error"] = str(exc)

    return result
