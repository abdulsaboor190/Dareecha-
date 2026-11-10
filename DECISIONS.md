# Decisions

- Backend: Python + FastAPI (best agent/RAG ecosystem)
- Frontend: React + TypeScript + Vite + Tailwind
- DB: PostgreSQL + pgvector. Queue/events: Redis
- LLM: free providers through an OpenAI-compatible client, swappable
- Embeddings: local sentence-transformers
- Hosting: local only; static replay site for the public demo
