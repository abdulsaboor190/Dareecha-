# Build Plan: From Zero to a Deployed AI Engineering Agent

Companion to `PROJECT_SPEC.md`. The spec says **what** to build. This plan says **what you need, in what order, and what to reuse instead of writing yourself.**

> **Zero-cost version.** This plan is designed to be built for **$0**. Every paid service is replaced with a free or open-source option (see Section 2 and Section 7), and the architecture is unchanged. Free-tier limits and offers change often, so check each provider's current terms before relying on them.

---

## 1. The Golden Rule: Build the Core, Reuse the Commodity

Your value to an employer is not rewriting a code editor. It is the parts that make the system *intelligent and reliable*. So:

| Build yourself (this is your project) | Reuse / customize (don't reinvent) |
|---|---|
| The agent loop, planning, self-correction | Code editor (Monaco) |
| Tool design and the permission layer | Terminal view (xterm.js) |
| Event schema and event stream | Diff viewer (Monaco DiffEditor) |
| The Explainer agent and its prompts | Code parsing (tree-sitter) |
| Retrieval pipeline (chunking, ranking, hybrid search) | Vector storage (pgvector) |
| Sandbox orchestration logic | Container runtime (Docker) |
| Eval harness and metrics | Model access (free providers through an OpenAI-compatible SDK) |
| Replay view and explanation UX | GitHub access (OAuth + REST API client library) |

**Avoid heavy agent frameworks (LangChain, etc.) for the core loop.** Write the loop yourself. It is about 100 lines, you will understand every failure, and it is exactly what interviewers ask about.

---

## 2. Decisions to Make on Day 1

| Decision | Recommendation | Why |
|---|---|---|
| Backend language | **Python (FastAPI)** | Best ecosystem for agents, tree-sitter, embeddings, evals. Pick TypeScript only if you are far stronger in it. |
| Frontend | **React + TypeScript + Vite + Tailwind** | Matches your web background, Monaco has first-class React support. |
| Database | **PostgreSQL + pgvector** | One database for everything. |
| Queue / events | **Redis** (lists/queues + Streams) | Job queue and event bus in one tool. |
| Model | **Free providers** (Gemini free tier, Groq, OpenRouter free models, or local Ollama) behind your own `LLMClient` that speaks the **OpenAI-compatible API** | Switching provider is just a base URL and model name. You can move to a stronger paid model later with no rewrite. Use a bigger model for the Worker and a small one for the Explainer. |
| Embeddings | **Local `sentence-transformers`** (e.g. `bge-small`, `all-MiniLM-L6-v2`) | Runs on CPU, no API, no cost. |
| Hosting | **None. Run locally**, plus a static replay site on GitHub Pages or Cloudflare Pages | No VPS or domain needed. |
| Local dev | **Docker Compose** | Postgres, Redis and the API start with one command. |
| Repo layout | **Monorepo** | One repo, easier for recruiters to read. |

Write these in a short `DECISIONS.md` and add to it whenever you change one. It becomes great blog material.

---

## 3. Prerequisites

### 3.1 Accounts and tools
- GitHub account (plus a **separate test repo** for the agent to work on, never your real repos)
- Free API keys from one or two providers (Gemini, Groq, OpenRouter) and optionally **Ollama** installed for local models. No credit card should be needed; check each provider's current free-tier limits.
- Docker Engine on Linux, or Docker Desktop (free for personal and educational use) with WSL2 on Windows
- Python 3.11+, Node 20+, Git
- VS Code (to build with)
- Optional: check whether you qualify for the GitHub Student Developer Pack (offers change, so verify what it includes now). Nothing in this plan requires it.

### 3.2 Skills to refresh *before or during* the phase that needs them
| Skill | Needed in | Quick way to learn |
|---|---|---|
| Python async basics (`asyncio`) | Phase 1 | Official docs + FastAPI tutorial |
| Tool use / function calling (OpenAI-compatible format) | Phase 1 | Docs of your chosen provider on function calling |
| Docker basics (images, containers, volumes, limits) | Phase 2 | Docker "get started", then docker SDK for Python |
| SQL and Postgres basics | Phase 1-3 | Build the tables yourself, don't rely on an ORM magic |
| Embeddings and cosine similarity | Phase 3 | One short tutorial, then experiment |
| WebSockets | Phase 4 | FastAPI WebSocket docs |
| OAuth flow | Phase 5 | GitHub OAuth docs |

### 3.3 Reading list (study, don't copy)
Open-source coding agents are the best teachers. Read their code and design docs, then write your own:
- **SWE-agent / mini-swe-agent** (small, readable agent loop)
- **OpenHands** (full agent platform with sandboxing and UI)
- **Aider** (how it builds a repo map and applies edits)
- **SWE-bench** (how coding agents are evaluated)

You will understand these far better *after* writing your own Phase 1 loop, so read them alongside building, not before.

---

## 4. Repository Structure

```
codesensei/
├── DECISIONS.md
├── PROJECT_SPEC.md
├── docker-compose.yml          # postgres, redis, api
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI entry
│   │   ├── api/                # routes: tasks, auth, repos, ws
│   │   ├── agent/
│   │   │   ├── loop.py         # plan → act → verify
│   │   │   ├── tools/          # read_file, edit_file, run_tests, ...
│   │   │   ├── llm.py          # LLMClient abstraction
│   │   │   └── prompts/
│   │   ├── events/             # schema, publisher, subscriber
│   │   ├── explainer/          # batching, prompts, validation
│   │   ├── sandbox/            # docker orchestration
│   │   ├── indexing/           # chunking, embeddings, search
│   │   ├── github/             # OAuth, branch, PR
│   │   └── db/                 # models, migrations
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/         # Editor, DiffView, ActivityFeed, ExplainPanel
│       ├── hooks/              # useTaskStream (WebSocket)
│       └── pages/
├── evals/
│   ├── tasks/                  # benchmark tasks
│   └── run_evals.py
└── docs/                       # architecture diagram, write-up
```

---

## 5. Phase-by-Phase Plan

Assumes roughly 10 to 12 hours per week. If you have less, stretch each phase, but keep the order.

### Phase 0: Setup (a few days)
**Goal:** a working skeleton so every later phase just plugs in.
- Create the monorepo, `docker-compose.yml` (Postgres with pgvector, Redis), FastAPI hello-world, Vite React hello-world.
- Create a throwaway **test target repo** on GitHub: a small project (e.g. a Python or Node app with tests and 5 to 10 planted bugs/feature requests). You will use this for the whole project.
- Set up linting, formatting and a GitHub Actions workflow that runs tests.

**Reuse:** project templates, Docker images for Postgres and Redis.
**Done when:** `docker compose up` starts everything and CI is green.

### Phase 1: Agent Core and Event Stream (Weeks 1-2)
**Goal:** a CLI agent that completes small tasks on a local folder and emits structured events.
- **Build:** `LLMClient` wrapper, the tool-use loop, 4 to 5 tools (`read_file`, `list_dir`, `edit_file`, `run_command`, `search_text`), step limit, error handling, and the **event publisher** from day one. Require every tool call to include a `reason` field.
- **Reuse:** the official `openai` Python SDK pointed at any OpenAI-compatible endpoint (Gemini, Groq, OpenRouter, Ollama). Pydantic for event schemas.
- **Build (free-model hardening):** retry with backoff on rate limits, a per-task token budget, a provider fallback chain, and an LLM response cache (see Section 7).
- **Customize later:** prompts (iterate a lot).
- **Done when:** `python run_agent.py "fix the failing test in /target"` works on your test repo, and every step appears as a JSON event in a log file.

> The event stream is the most important design choice in the project. The logs, the UI, the Explainer, the replay view and the eval harness all depend on it. Spend time here.

### Phase 2: Sandbox and Test Loop (Weeks 3-4)
**Goal:** run the agent's work in an isolated container and let it fix its own failures.
- **Build:** sandbox manager that creates a container, clones the repo, mounts a workspace, executes tools inside it, and destroys it afterward. Add CPU, memory and time limits, and disabled or restricted network. Add the verify step: run tests, feed failures back to the Worker, retry up to N times.
- **Reuse:** Docker SDK for Python, official language base images (`python`, `node`).
- **Done when:** a task runs end to end in a container, you can kill it safely, and the agent recovers from at least one failing test by itself.

### Phase 3: Code Indexing and Retrieval (Weeks 5-6)
**Goal:** the agent finds the right files in a repo it has never seen.
- **Build:** the chunking strategy (by function/class), the hybrid ranking logic, the `search_code` tool, and a small retrieval test set ("given this question, the right file should be in the top 5").
- **Reuse:** **tree-sitter** for parsing, **pgvector** for vector search, **Postgres full-text search** for the keyword side (no need for a separate search engine), a **local sentence-transformers embedding model** (free, CPU-friendly). Cache embeddings per file hash so unchanged files are never re-embedded.
- **Done when:** retrieval hit-rate is measured on your test set and the agent uses `search_code` instead of reading every file.

### Phase 4: Web IDE and Explainer v1 (Weeks 7-8)
**Goal:** the visible product. This is the **minimum strong version**.
- **Build:** WebSocket gateway that streams events, the activity feed, task creation page, diff review with accept/reject, and **Explainer v1**: subscribes to events, batches every few seconds, streams short narration to a side panel.
- **Reuse:** `@monaco-editor/react` (including its built-in diff editor), xterm.js if you want a terminal view, Tailwind, Redis Streams for the event bus.
- **Customize:** panel layout, click-to-highlight sync between explanation and diff.
- **Done when:** you can start a task in the browser, watch the live feed and narration, and review the final diff.

### Phase 5: GitHub Integration and Explainer v2 (Weeks 9-10)
**Goal:** real PRs and the full teaching experience.
- **Build:** GitHub login, repo selection, branch + commit + PR creation with a generated description, handling review comments. Explainer v2: depth levels, concept cards, Mermaid architecture diagrams, post-task summary, quiz mode.
- **Reuse:** GitHub OAuth (or GitHub App), a GitHub API client library, Mermaid.js for diagrams, the browser's built-in speech synthesis if you add voice.
- **Done when:** the agent opens a real PR on your test repo, and the Explanation Layer works at three depth levels.

### Phase 6: Evaluation, Observability, Deployment (Weeks 11-12)
**Goal:** proof, polish, and a public demo.
- **Build:** the eval runner (runs all tasks, records pass/fail, steps, cost, time), explanation faithfulness check, replay view, cost tracking per task, metrics dashboard (simple page is fine).
- **Reuse:** your own event store for replay. Optionally an open-source LLM observability tool instead of building dashboards. Start with a small custom task set; move to **SWE-bench Lite** subset only if time allows, since its harness is heavy.
- **Demo (free):** record a demo video, and export a few good runs (events, diffs, explanations) as JSON to a **static replay site** hosted on GitHub Pages or Cloudflare Pages. Visitors can step through a real narrated task with no backend. The README gives a one-command local setup (`docker compose up`) for anyone who wants the live version.
- **Optional later:** if you ever want a live hosted version, use a VPS or student credits, with rate limits and a spending cap. Not needed for this plan.
- **Done when:** the replay site is public, the README contains real numbers, and the demo video and write-up are published.

---

## 6. What to Customize vs. Fetch (Quick Reference)

| Component | Source | Your customization |
|---|---|---|
| Code editor | Monaco | Theme, decorations that highlight lines the agent touched |
| Diff viewer | Monaco DiffEditor | Per-hunk accept/reject, explanation badges on hunks |
| Terminal | xterm.js | Streamed read-only output from the sandbox |
| Diagrams | Mermaid.js | Auto-generated from changed files and imports |
| Parsing | tree-sitter grammars | Your chunking rules and symbol extraction |
| Vector search | pgvector | Your hybrid scoring and reranking |
| Sandbox | Docker + base images | Your limits, lifecycle, cleanup, and network rules |
| Agent loop | **Written by you** | Everything |
| Explainer | **Written by you** | Everything |
| Eval harness | **Written by you** (task format can follow SWE-bench style) | Metrics and reports |

---

## 7. Zero-Cost Stack, Cost Control and Safety

### 7.1 The free stack at a glance

| Need | Free option |
|---|---|
| LLM for Worker and Explainer | Gemini free tier, Groq, OpenRouter free models, or local Ollama (if your machine can run it) |
| Embeddings | Local sentence-transformers model |
| Database, queue | PostgreSQL + pgvector, Redis (open source, run in Docker) |
| Sandbox | Docker (free for personal and educational use; WSL2 on Windows) |
| Editor, diff, terminal, diagrams | Monaco, xterm.js, Mermaid.js (open source) |
| Parsing | tree-sitter (open source) |
| CI | GitHub Actions free tier (public repos) |
| Demo hosting | GitHub Pages or Cloudflare Pages (static replay site) |
| Observability | Your own event tables and replay view |

Free tiers change often. Re-check limits at the start of each phase.

### 7.2 Making free models work

1. **One client, many providers.** Implement `LLMClient` against the OpenAI-compatible format with a config like `{base_url, model, api_key}` per provider.
2. **Fallback chain.** If a provider returns a rate-limit or quota error, retry with exponential backoff, then fall through to the next provider in the list.
3. **Record and replay.** Cache every LLM request/response (keyed by a hash of the request) during development. Use the cache in tests so most debugging costs no quota.
4. **Hard budgets.** Cap steps, tokens and wall-clock time per task. Free quotas disappear fast if a loop runs away.
5. **Small model for the Explainer.** Narration is easy work for a small free or local model. Reserve the strongest available model for the Worker.
6. **Start with narrow tasks.** Free and small models are weaker at tool use. Begin with small repos and simple tasks, then widen. Lower absolute scores are fine: report the improvement from your changes (retrieval, prompts, retries).
7. **Keep prompts and tool schemas simple.** Fewer, clearer tools and short instructions work better with weaker models.

### 7.3 Safety housekeeping

- Cap steps and tokens per task in code.
- Use a small or local model while developing, and your best available model only for evals and demos.
- Cache embeddings by file hash so unchanged files are never re-embedded.
- Never run the agent against repos you care about during development.
- Keep secrets in environment variables, never in the repo, and never in model context.
- Treat issue text and repo contents as **untrusted input** (prompt injection).

---

## 8. Working Habits That Make the Project Hireable

1. **Commit small and often** with clear messages. Recruiters read the history.
2. **Write tests** for tools, retrieval and the event pipeline.
3. **Keep a `DECISIONS.md`** and a `FAILURES.md` (what didn't work and why). Both are interview gold.
4. **Record a short demo video at the end of every phase.** It forces you to keep things working and gives you content to post.
5. **Measure everything** from Phase 1 onward: steps, tokens, cost, pass rate.
6. **Ship vertically.** After each phase, the whole system should still run end to end, just with more capability.

---

## 9. If You Fall Behind

Cut in this order (last item first):
1. Voice narration, quiz mode
2. Architecture diagrams
3. Webhook-triggered tasks and review-comment handling
4. SWE-bench subset (keep your own small task set)
5. Depth levels beyond two (Beginner and Expert only)

**Never cut:** the event stream, the sandbox, the eval numbers, or the narrated timeline. Those are what make the project stand out.

---

## 10. Milestone Checklist

- [ ] Phase 0: skeleton, test repo, CI green
- [ ] Phase 1: CLI agent + structured events
- [ ] Phase 2: sandboxed runs + self-fix loop
- [ ] Phase 3: hybrid retrieval with measured hit-rate
- [ ] Phase 4: web IDE + narrated timeline (minimum strong version)
- [ ] Phase 5: real PRs + full Explanation Layer
- [ ] Phase 6: eval results, replay, public demo, write-up
