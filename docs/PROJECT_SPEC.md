# CodeSensei: An AI Engineering Agent That Builds and Teaches

> Working title. An open-source "Issue-to-PR" AI software engineer with a browser IDE, plus a live **Explanation Layer** that teaches you what the agent is doing while it works.

---

## 1. One-Line Pitch

Connect a GitHub repo, give the agent a task. It plans, edits code in a sandbox, runs tests, fixes its own failures and opens a pull request, while a second agent narrates and teaches every step in real time so you understand and trust the result.

## 2. The Problem

1. **Dead time.** When an AI agent works, the developer just watches a raw log scroll by.
2. **Trust gap.** Developers hesitate to merge changes they don't understand. Reviewing a diff without knowing the reasoning is slow and risky.
3. **Black-box tools.** Most agents show *what* they did (actions), not *why* (reasoning) or *what it means* (concepts).
4. **Learning gap.** Junior developers and students use AI to produce code but learn little from it.

## 3. The Solution

Two cooperating agents sharing one event stream:

| Agent | Role |
|---|---|
| **Worker Agent** | Does the engineering: plan, search, edit, run tests, fix, open PR. |
| **Explainer Agent** | Watches the worker's events and turns them into plain-language, level-appropriate explanations, diagrams, concept cards and quizzes. |

The Explainer never blocks or controls the Worker. It only reads.

## 4. Target Users

- **Students and junior developers** who want to learn on a real codebase.
- **Solo developers and small teams** who want to delegate small issues and review safely.
- **Reviewers and tech leads** who need to understand AI-made changes fast.

## 5. Core Features

### 5.1 Agent Core (Worker)
- Plan, act, verify loop with a step limit and retry policy.
- Tool use: `read_file`, `search_code`, `edit_file`, `list_dir`, `run_tests`, `run_command`, `git_*`, plus MCP tools.
- Self-correction: reads failing test output and revises its patch.
- Every action carries a **stated reason** (structured field), which feeds the Explainer.
- Provider abstraction so models are swappable (Claude, OpenAI, Gemini, local via Ollama).

### 5.2 Sandboxed Execution
- Every task runs in a fresh Docker container with the repo cloned.
- Resource limits (CPU, memory, time), restricted network, no host access.
- Optional hardening later: gVisor or Firecracker.

### 5.3 Code Intelligence (Indexing and Retrieval)
- **tree-sitter** parsing to chunk code by function, class and module.
- **Hybrid search**: embeddings (pgvector) plus keyword/BM25 plus symbol lookup.
- Dependency and call-graph hints so the agent finds related files.
- Incremental re-indexing when files change.

### 5.4 Web IDE
- React + Monaco editor, file tree, integrated terminal view.
- **Live activity feed** of agent steps.
- **Diff viewer** with accept, reject and comment per hunk.
- Human feedback loop: "change this part" sends the agent back to work.

### 5.5 GitHub Integration
- OAuth login, repo selection, issue import.
- Creates branches, commits and pull requests with a generated description.
- Responds to PR review comments and iterates.
- Webhook support (new issue labeled `ai-agent` triggers a task).

### 5.6 The Explanation Layer (Signature Feature)
- **Live narrated timeline**: short, plain-language updates synced to the activity feed.
- **Depth levels**: Beginner, Intermediate, Expert. Same event, different explanation.
- **Concept cards**: pop-ups when a new idea appears (JWT, migration, race condition, index).
- **Live architecture diagrams**: Mermaid diagrams that update as files change.
- **Click-through sync**: clicking an explanation highlights the related file, line or diff hunk.
- **Post-task review**: a summary of "what changed, why, and what to watch for".
- **Quiz mode**: "Why did the agent add this check?" to reinforce learning.
- **Optional voice narration** (text-to-speech).
- **Mute and collapse controls** to avoid information overload.

### 5.7 Evaluation Harness
- Benchmark of 20 to 50 tasks (small real repos, SWE-bench Lite style problems).
- Metrics: pass rate, steps per task, cost per task, time per task.
- Explainer metrics: **faithfulness** (does the explanation match the actual diff and reason?) and **usefulness** (user ratings).
- Regression tracking: compare prompt, retrieval or model changes over time.

### 5.8 Observability
- Structured logs for every step, token and cost tracking per task.
- **Replay view**: step through a finished run with its explanations.
- Dashboard: success rate, failure categories, average cost.

### 5.9 Safety and Security
- Approval gates for risky commands (deletes, network, installs).
- Network egress limits inside the sandbox.
- **Prompt-injection defense**: treat repo content, issues and web pages as untrusted data, never as instructions.
- Secrets never enter the model context or logs.
- Per-user isolation, rate limits and audit log.

## 6. What Makes It Novel

1. **Dual-agent architecture.** A separate Explainer consumes the Worker's event stream. Most tools only have one agent and a raw log.
2. **Reason-grounded explanations.** The Worker emits its own stated reason with every action and the Explainer paraphrases it instead of guessing motives, which reduces hallucinated explanations.
3. **Teaching mode on a real codebase.** Not a toy tutorial. The user learns from changes made to their own project.
4. **Adaptive depth.** One event, multiple explanation levels.
5. **Measured explanation quality.** Explanation faithfulness is part of the eval harness. Few projects evaluate the explanation, only the code.
6. **Replayable runs.** Every task can be replayed with its narration, useful for onboarding and code review.

## 7. System Architecture

```
┌────────────────────────────────────────────────────────────┐
│  React + Monaco UI                                         │
│  Editor | Diff Viewer | Activity Feed | Explanation Panel  │
└───────────────▲────────────────────────────────────────────┘
                │ WebSocket (events + explanations)
┌───────────────┴────────────────────────────────────────────┐
│  API Server (FastAPI or Node/TS)                           │
│  Auth | Task API | GitHub OAuth | Webhooks | WS gateway    │
└───┬───────────────┬──────────────────┬─────────────────────┘
    │               │                  │
    ▼               ▼                  ▼
┌─────────┐   ┌─────────────┐   ┌───────────────┐
│ Worker  │   │ Event Bus   │   │ Code Index    │
│ Agent   │──▶│ (Redis      │   │ pgvector +    │
│ (plan → │   │  Streams)   │   │ BM25 + symbols│
│ act →   │   └──────┬──────┘   └───────────────┘
│ verify) │          │
└────┬────┘          ▼
     │         ┌───────────────┐
     │         │ Explainer     │
     │         │ Agent (small, │
     │         │ fast model)   │
     │         └───────────────┘
     ▼
┌─────────────────────────────┐        ┌──────────────┐
│ Sandbox Workers (Docker)    │───────▶│ GitHub API   │
│ clone | edit | test | git   │        │ branch | PR  │
└─────────────────────────────┘        └──────────────┘

Storage: PostgreSQL (tasks, events, users, explanations, evals)
Queue:   Redis (jobs + event streams)
```

### 7.1 Data Flow
1. User submits a task (or an issue webhook fires).
2. API enqueues a job, and a sandbox worker spins up a container with the repo.
3. Worker Agent loops: retrieve context, plan, call tools, observe results.
4. Each step is published as a **structured event** to the event bus.
5. The Explainer subscribes, batches events every few seconds and produces explanations.
6. Events and explanations stream to the UI over WebSocket and are stored for replay.
7. When tests pass, the Worker opens a PR. The user reviews the diff with explanations and approves or gives feedback.

### 7.2 Event Schema (draft)

```json
{
  "task_id": "t_123",
  "seq": 42,
  "timestamp": "2026-11-10T12:00:00Z",
  "type": "tool_call | tool_result | plan | edit | test_run | error | retry | pr_opened",
  "tool": "edit_file",
  "target": "src/auth/login.ts",
  "summary": "Added input validation to login handler",
  "reason": "Tests showed empty passwords were accepted",
  "payload": { "diff": "...", "exit_code": 0 },
  "tokens": { "in": 1200, "out": 300 }
}
```

### 7.3 Explainer Design
- **Input:** batched events, project summary, user depth level, recent explanations (to avoid repetition).
- **Output:** short narration (1 to 3 sentences), optional concept card, optional diagram update.
- **Rules:** explain only what has happened or is happening, never predict. Paraphrase the stated `reason`, do not invent one. Flag uncertainty.
- **Model:** a cheaper, faster model than the Worker. Runs asynchronously and never blocks the Worker.
- **Validation:** a lightweight check compares each explanation against the event payload (file names, symbols, outcome) to catch contradictions.

## 8. Technology Stack

| Layer | Choice | Notes |
|---|---|---|
| Frontend | React, TypeScript, Tailwind, Monaco Editor | Mermaid.js for diagrams |
| Realtime | WebSockets (or SSE) | Event and explanation streaming |
| Backend | FastAPI (Python) or Node + TypeScript | Choose the one you are stronger in |
| Database | PostgreSQL + pgvector | One database for relational and vector data |
| Queue / Events | Redis (queues, Streams) | Job queue plus event bus |
| Execution | Docker, optional gVisor | Per-task sandbox containers |
| Code parsing | tree-sitter | Language-aware chunking |
| Models | Claude API (primary), swappable | Larger model for Worker, smaller for Explainer |
| Integrations | GitHub API and webhooks, MCP | OAuth app or GitHub App |
| Auth | GitHub OAuth, JWT sessions | |
| Observability | OpenTelemetry or structured logs, Grafana (optional) | Cost and latency tracking |
| Testing | pytest or Vitest, Playwright | Plus the eval harness |
| Deployment | Docker Compose locally, Fly.io or a VPS for the demo | CI with GitHub Actions |

## 9. Data Model (core tables)

- `users`: id, github_id, tokens (encrypted), created_at
- `repos`: id, user_id, full_name, index_status, last_indexed_at
- `tasks`: id, repo_id, prompt, status, branch, pr_url, cost, started_at, finished_at
- `events`: id, task_id, seq, type, payload (JSONB), created_at
- `explanations`: id, task_id, event_range, level, text, concept_tags, faithfulness_score
- `code_chunks`: id, repo_id, path, symbol, content, embedding (vector), tsv
- `eval_runs` / `eval_results`: id, version, task_id, passed, steps, cost, notes

## 10. Roadmap (10 to 12 weeks, part-time)

| Weeks | Milestone | Deliverable |
|---|---|---|
| 1-2 | Agent core + **event stream** | Local agent with tools, emitting structured events |
| 3-4 | Docker sandbox + test running | Isolated runs, self-fix loop on failing tests |
| 5-6 | Indexing and retrieval | tree-sitter chunking, hybrid search, retrieval tests |
| 7-8 | Web IDE + **Explainer v1** | Monaco UI, live feed, diff review, narrated timeline |
| 9-10 | GitHub integration + Explainer v2 | OAuth, PR creation, depth levels, concept cards, diagrams |
| 11-12 | Eval, observability, deploy | Benchmark results, replay view, public demo, write-up |

**Minimum strong version:** ship through week 8 (agent + sandbox + retrieval + IDE + narrated timeline). That is already a standout project.

## 11. Evaluation Plan

**Agent quality**
- Pass rate on 20 to 50 tasks, steps per task, cost per task, wall-clock time.
- Ablations: with vs. without retrieval, with vs. without self-correction.

**Explanation quality**
- **Faithfulness:** automated check plus manual sampling of explanations against diffs.
- **Usefulness:** user study with a few classmates (rating, comprehension quiz scores, review time with and without explanations).
- **Cost overhead:** extra tokens and latency added by the Explainer.

Report results in the README, for example: "Pass rate 22% to 38% after hybrid retrieval. Reviewers understood diffs X% faster with the Explanation Layer."

## 12. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Explainer hallucinates reasoning | Worker emits stated reasons, Explainer paraphrases, add validation check |
| Information overload | Batching, short outputs, mute and collapse, depth levels |
| Extra cost and latency | Small model, batched calls, async, never blocks Worker |
| Narrating wrong predictions | Narrate only past and present, never future |
| Sandbox escape or abuse | Container limits, no host mounts, network restrictions, gVisor later |
| Prompt injection from repo or issues | Treat as untrusted data, tool permission gates, approval for risky actions |
| Scope creep | Fixed milestones, ship through week 8 first |
| Weak agent results | Start with small repos and narrow task types, measure and iterate |

## 13. Career Value

**Skills demonstrated**
- Agent engineering: tool use, planning, self-correction, multi-agent design
- RAG and search: chunking, embeddings, hybrid retrieval
- Infrastructure: containers, sandboxing, queues, event-driven design
- Full-stack: React, WebSockets, auth, PostgreSQL
- Integrations: GitHub API, webhooks, MCP
- Rigor: evaluation, observability, safety, cost tracking
- Product thinking: a differentiated teaching UX

**Resume bullet examples**
- Built an open-source AI software engineering agent that converts GitHub issues into tested pull requests using sandboxed execution and hybrid code retrieval.
- Designed a dual-agent architecture where an Explainer agent consumes the Worker's event stream to deliver real-time, level-adaptive explanations, with faithfulness evaluation.
- Created an evaluation harness over N tasks, improving pass rate from X% to Y% through retrieval and prompt iteration.

**Portfolio package**
- Live demo that opens a real PR on a real repo
- Open-source repo with a clean README, architecture diagram and numbers
- A 2 to 3 minute demo video
- A blog post on design decisions and failures

## 14. Future Extensions

- AI code reviewer mode (comment on PRs automatically)
- CI failure triage agent
- Team mode with shared task history and review queues
- Support for more languages and frameworks
- Local or self-hosted models for privacy
- VS Code extension front end
- Learning paths generated from a repo ("understand this codebase in 5 lessons")

## 15. Definition of Done

- [ ] Agent resolves a set of benchmark tasks end to end in a sandbox
- [ ] Retrieval works on repos with 500+ files
- [ ] Web IDE shows live activity, diffs, and narrated explanations
- [ ] PRs are created on GitHub with generated descriptions
- [ ] Depth levels, concept cards and replay work
- [ ] Eval results documented with numbers
- [ ] Public deployment and demo video
- [ ] README, architecture doc and blog post published
