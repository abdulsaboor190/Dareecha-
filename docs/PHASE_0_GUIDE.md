# Phase 0 Guide: Project Setup (about 3 days)

**Goal:** a working skeleton where `docker compose up` starts the database and Redis, the API answers `/health`, the React app talks to the API, a separate test repo exists for the agent to practice on, and CI is green.

**Cost: $0.** Everything here is free and open source.

---

## Day 1: Tools, Repo, Infrastructure

### 1.1 Check your tools

Run each command. You need these versions or newer:

```bash
git --version          # any recent version
python3 --version      # 3.11+
node --version         # 20+
docker --version
docker compose version
```

- **Windows:** use **WSL2** (Ubuntu) and do all work inside it. Install Docker Desktop with the WSL2 backend (free for personal and educational use).
- **Linux:** install Docker Engine and add yourself to the `docker` group.

### 1.2 Create the monorepo

```bash
mkdir codesensei && cd codesensei
git init
mkdir -p backend/app/api backend/app/agent backend/app/events backend/app/sandbox \
         backend/app/indexing backend/app/explainer backend/app/github backend/app/db \
         backend/tests frontend infra evals/tasks docs
touch backend/app/__init__.py
```

Copy `PROJECT_SPEC.md` and `BUILD_PLAN.md` into the repo root and create `DECISIONS.md`:

```markdown
# Decisions
- Backend: Python + FastAPI (best agent/RAG ecosystem)
- Frontend: React + TypeScript + Vite + Tailwind
- DB: PostgreSQL + pgvector. Queue/events: Redis
- LLM: free providers through an OpenAI-compatible client, swappable
- Embeddings: local sentence-transformers
- Hosting: local only; static replay site for the public demo
```

### 1.3 `.gitignore` (repo root)

```gitignore
# Python
__pycache__/
*.pyc
.venv/
.pytest_cache/
.ruff_cache/

# Node
node_modules/
dist/

# Secrets and local data
.env
*.log
.cache/
llm_cache/
```

### 1.4 `.env.example` (repo root)

Commit this file. Copy it to `.env` (never commit `.env`).

```bash
DATABASE_URL=postgresql://codesensei:codesensei@localhost:5432/codesensei
REDIS_URL=redis://localhost:6379/0

# Fill in later (Phase 1). Free keys only.
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
```

### 1.5 `docker-compose.yml` (repo root)

Only the infrastructure runs in Docker. You run the API and frontend directly on your machine, which gives faster reloads while developing.

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: codesensei
      POSTGRES_PASSWORD: codesensei
      POSTGRES_DB: codesensei
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./infra/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U codesensei"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  pgdata:
```

`infra/init.sql`:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Start and verify:

```bash
docker compose up -d
docker compose ps        # both services should show "healthy"
```

Commit:

```bash
git add . && git commit -m "chore: repo skeleton, docker compose for postgres+redis"
```

---

## Day 2: Backend and Frontend Skeletons

### 2.1 Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows (non-WSL): .venv\Scripts\activate
pip install fastapi "uvicorn[standard]" pydantic-settings "psycopg[binary]" redis \
            openai pytest httpx ruff
pip freeze > requirements.txt
```

`backend/app/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://codesensei:codesensei@localhost:5432/codesensei"
    redis_url: str = "redis://localhost:6379/0"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")


settings = Settings()
```

`backend/app/main.py`:

```python
import psycopg
import redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(title="CodeSensei API")

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
    except Exception as exc:
        result["postgres_error"] = str(exc)

    try:
        result["redis"] = bool(redis.from_url(settings.redis_url).ping())
    except Exception as exc:
        result["redis_error"] = str(exc)

    return result
```

`backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

Run it:

```bash
# from the backend/ folder
pytest
uvicorn app.main:app --reload --port 8000
# in another terminal:
curl http://localhost:8000/health
curl http://localhost:8000/health/deps     # expect all true with docker compose running
```

Add a `backend/pyproject.toml` so pytest finds the `app` package and ruff has settings:

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
```

### 2.2 Frontend setup

From the repo root:

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install tailwindcss @tailwindcss/vite
```

> Tailwind's setup steps change between major versions. If anything below doesn't match, follow the current Tailwind + Vite instructions on tailwindcss.com.

`frontend/vite.config.ts`:

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
```

Replace the contents of `frontend/src/index.css` with:

```css
@import "tailwindcss";
```

Replace `frontend/src/App.tsx`:

```tsx
import { useEffect, useState } from "react";

type Deps = { postgres: boolean; pgvector: boolean; redis: boolean };

export default function App() {
  const [api, setApi] = useState<string>("checking...");
  const [deps, setDeps] = useState<Deps | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((d) => setApi(d.status))
      .catch(() => setApi("unreachable"));

    fetch("/api/health/deps")
      .then((r) => r.json())
      .then(setDeps)
      .catch(() => setDeps(null));
  }, []);

  return (
    <main className="min-h-screen bg-slate-900 text-slate-100 p-8">
      <h1 className="text-3xl font-bold">CodeSensei</h1>
      <p className="mt-2 text-slate-400">Phase 0 skeleton</p>

      <ul className="mt-6 space-y-1">
        <li>API: {api}</li>
        <li>Postgres: {deps ? String(deps.postgres) : "unknown"}</li>
        <li>pgvector: {deps ? String(deps.pgvector) : "unknown"}</li>
        <li>Redis: {deps ? String(deps.redis) : "unknown"}</li>
      </ul>
    </main>
  );
}
```

Run:

```bash
npm run dev      # open http://localhost:5173
```

You should see API `ok` and all three dependencies `true`.

Commit:

```bash
git add . && git commit -m "feat: FastAPI health endpoints and React skeleton wired through Vite proxy"
```

---

## Day 3: Test Target Repo and CI

### 3.1 Create the test target repo

This is a **separate GitHub repo** the agent will practice on for the whole project. Never point the agent at repos you care about.

Create a public repo named `agent-target-shop` and add this structure:

```
agent-target-shop/
├── shop/
│   ├── __init__.py
│   ├── cart.py
│   └── discounts.py
├── tests/
│   ├── test_cart.py
│   └── test_discounts.py
├── requirements.txt      # contains: pytest
└── README.md
```

`shop/cart.py` (contains **two planted bugs**):

```python
class Cart:
    def __init__(self):
        self.items = {}  # name -> (price, qty)

    def add(self, name, price, qty=1):
        if qty < 0:  # BUG 1: should be <= 0
            raise ValueError("qty must be positive")
        if name in self.items:
            _, old_qty = self.items[name]
            self.items[name] = (price, old_qty + qty)
        else:
            self.items[name] = (price, qty)

    def remove(self, name):
        del self.items[name]

    def total(self):
        return sum(price for price, qty in self.items.values())  # BUG 2: ignores qty
```

`shop/discounts.py` (contains **one planted bug**):

```python
COUPONS = {"SAVE10": 10, "SAVE20": 20}


def apply_percent(total, percent):
    """Return the total after applying a percentage discount (0-100)."""
    if not 0 <= percent <= 100:
        raise ValueError("percent must be between 0 and 100")
    return round(total * (percent / 100), 2)  # BUG 3: returns the discount, not the new total


def apply_coupon(total, code):
    if code not in COUPONS:
        return total
    return apply_percent(total, COUPONS[code])
```

`tests/test_cart.py`:

```python
import pytest

from shop.cart import Cart


def test_total_uses_quantity():
    cart = Cart()
    cart.add("pen", 2.0, qty=3)
    assert cart.total() == 6.0


def test_add_rejects_zero_quantity():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add("pen", 1.0, qty=0)


def test_add_same_item_increases_quantity():
    cart = Cart()
    cart.add("pen", 1.0, qty=1)
    cart.add("pen", 1.0, qty=2)
    assert cart.items["pen"] == (1.0, 3)
```

`tests/test_discounts.py`:

```python
import pytest

from shop.discounts import apply_coupon, apply_percent


def test_percent_discount():
    assert apply_percent(100, 10) == 90


def test_invalid_percent():
    with pytest.raises(ValueError):
        apply_percent(100, 150)


def test_unknown_coupon_changes_nothing():
    assert apply_coupon(50, "NOPE") == 50


def test_known_coupon():
    assert apply_coupon(200, "SAVE20") == 160
```

Verify the planted bugs:

```bash
pip install pytest
pytest      # expect 4 failing tests (total_uses_quantity, zero_quantity, percent_discount, known_coupon)
```

Commit and push this broken state. Tag it so you can always reset to it:

```bash
git add . && git commit -m "initial: shop library with planted bugs"
git tag baseline-v1 && git push --tags origin main
```

Then open **GitHub Issues** on the target repo describing the work the agent will do later, for example:

1. "Fix: total() ignores item quantity"
2. "Fix: adding an item with quantity 0 should raise ValueError"
3. "Fix: apply_percent returns the discount instead of the discounted total"
4. "Feature: add `Cart.clear()`"
5. "Feature: `remove()` should raise a clear `KeyError` message when the item doesn't exist"
6. "Feature: add a `SAVE30` coupon and tests"

These issues become your first benchmark tasks in Phase 6. Save each one later as a file in `evals/tasks/` (issue text, repo URL, test command, expected passing tests).

### 3.2 CI with GitHub Actions

In the main project repo, create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: ruff check .
      - run: pytest

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm ci
      - run: npm run build
```

Create a GitHub repo for the project, push, and confirm both CI jobs go green. Fix any lint errors `ruff` reports (`ruff check . --fix` handles many).

---

## Phase 0 Done-When Checklist

- [ ] `docker compose up -d` starts Postgres (with pgvector) and Redis, both healthy
- [ ] `uvicorn` serves `/health` and `/health/deps` (all `true`)
- [ ] React app shows API, Postgres, pgvector and Redis status
- [ ] `agent-target-shop` repo exists with 4 failing tests, a `baseline-v1` tag, and 6 issues
- [ ] CI is green on the main project repo (backend lint + tests, frontend build)
- [ ] `DECISIONS.md` exists and everything is committed with clear messages

## Common Problems

| Problem | Fix |
|---|---|
| Port 5432 or 6379 already in use | Stop the local service using it, or change the left side of the port mapping (e.g. `"5433:5432"`) and update `DATABASE_URL` |
| `/health/deps` shows `pgvector: false` | `init.sql` only runs on first creation. Run `docker compose down -v` (deletes data) and `up -d` again |
| Frontend can't reach the API | Check the API runs on port 8000 and the Vite proxy is set; fetch `/api/health`, not `/health` |
| Docker permission denied (Linux) | Add your user to the `docker` group and log in again |
| Tests can't import `app` | Run `pytest` from the `backend/` folder and make sure `pyproject.toml` has `pythonpath = ["."]` |

## Next: Phase 1

Phase 1 builds the `LLMClient` (OpenAI-compatible, with retry, fallback and caching), the tool-use loop, five tools, and the structured event stream, and the first real test is getting your agent to fix the three planted bugs in `agent-target-shop`.
