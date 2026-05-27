# AskMyDocs — Production Edition Plan (v2)

> **Difference from `PROGRESS.md` (v1):** v1 ships a working RAG chatbot. v2 makes it look like a project a real AI team would ship — with observability, prompt versioning, env separation, CI/CD, and structured eval. The goal is to differentiate from the ~10,000 "RAG tutorial clones" on GitHub and signal real engineering judgment to recruiters.

**Last updated:** 2026-05-27
**Status:** Plan only — none of this section is built yet. v1 must be deployed first.

---

## 🎯 Vision

Build a project that, in a code-review interview, lets you say:

> "Here's the LangSmith trace for that exact query — you can see the router's intent classification, the retrieved chunks with their similarity scores, the answerer's prompt and token usage, and the total latency. The prompt is pulled from LangSmith Hub at runtime so I can A/B test versions without redeploying. Dev and prod use separate LangSmith projects so eval runs don't pollute prod traces."

That's the gap between "tutorial RAG" and "AI app a company would actually run".

---

## 🟢 Foundation already in place (from v1)

Don't re-do these — v1 already nailed:
- Two-call agentic flow (router + answerer)
- Modular `rag/` package — easy to add tracing decorators
- `.env` based config — easy to extend to multi-env
- Pure-function helpers — easy to unit test
- One source of truth for prompts (`rag/prompts.py`) — easy to push to LangSmith Hub
- Eval harness (`eval.py`) — easy to wire into CI

---

## 🏗️ Production pillars

### Pillar 1 — LangSmith observability (highest signal, ~3 hrs)

**What it gives you:** Every LLM call (router + answerer) appears in LangSmith with full input/output, latency, token usage, and custom metadata. You can replay traces, compare runs, and debug live issues.

**Build steps:**
- [ ] Create LangSmith account at https://smith.langchain.com (free tier: 5k traces/month)
- [ ] Add to `requirements.txt`: `langsmith>=0.1.0`
- [ ] Add to `.env.example`:
  ```
  LANGSMITH_API_KEY=lsv2_...
  LANGSMITH_PROJECT=askmydocs-dev
  LANGSMITH_TRACING=true
  ```
- [ ] In `rag/router.py` and `rag/answer.py`, wrap the Groq client with `@traceable` from `langsmith`:
  ```python
  from langsmith import traceable

  @traceable(run_type="llm", name="router")
  def route_query(...): ...

  @traceable(run_type="llm", name="answerer")
  def ask_groq(...): ...
  ```
- [ ] Add custom metadata to traces: `intent`, `num_chunks_retrieved`, `top_similarity_score`, `pdf_name`
- [ ] Create a wrapper in `rag/observability.py` that tags every run with a session-level `trace_id` so you can find related traces

**Resume signal:**
> Instrumented the RAG pipeline with LangSmith — every router decision, retrieval, and answer is traced with custom metadata (intent, retrieval scores, latency, token cost). Used traces to debug a prompt-leakage regression in <10 minutes.

### Pillar 2 — Prompt versioning via LangSmith Hub (~2 hrs)

**What it gives you:** Prompts live in LangSmith, not in code. Iterate on prompts without redeploying. A/B test by serving different versions to different users. Roll back instantly if a new prompt regresses.

**Build steps:**
- [ ] Push current prompts (`ROUTER_SYSTEM`, `ANSWERER_SYSTEM_TEMPLATE`) to LangSmith Hub as named prompts (`askmydocs/router`, `askmydocs/answerer`)
- [ ] Tag them with semantic versions (`v1.0.0`, `v1.0.1`)
- [ ] Replace hardcoded strings in `rag/prompts.py` with a `load_prompt(name, version)` helper:
  ```python
  from langsmith import Client
  ls = Client()
  prompt = ls.pull_prompt("askmydocs/router", include_model=False)
  ```
- [ ] Cache pulled prompts in-memory for the session
- [ ] Add a config flag `PROMPT_VERSION` (`prod` or `dev` or a specific tag) so dev can test new prompts while prod stays stable
- [ ] Document the prompt-change workflow in README

**Resume signal:**
> Centralized prompts in LangSmith Hub with semantic versioning — enabled A/B testing prompt variants in production without code redeploys and instant rollback on regressions.

### Pillar 3 — Dev / staging / prod env separation (~1.5 hrs)

**What it gives you:** Three isolated environments. Dev traces don't pollute prod. Staging eval can run against the prod-shaped data. Recruiter sees you understand "promote-through-environments" workflow.

**Build steps:**
- [ ] Add `pydantic-settings` to deps
- [ ] Create `rag/settings.py` with a typed `Settings` class:
  ```python
  class Settings(BaseSettings):
      env: Literal["dev", "staging", "prod"] = "dev"
      groq_api_key: str
      langsmith_api_key: str | None = None
      langsmith_project: str = "askmydocs-dev"
      prompt_version: str = "dev"
      embed_cache_dir: Path = Path(".cache/embeddings")
      # ...
      class Config:
          env_file = ".env"
  ```
- [ ] Three env files: `.env.dev`, `.env.staging`, `.env.prod` (all gitignored, .env.example tracked)
- [ ] `ENV=prod streamlit run app.py` loads `.env.prod`
- [ ] Streamlit Cloud uses `.env.prod` values via Streamlit Secrets
- [ ] Banner in UI when `env != "prod"` so you never confuse dev with prod

**Resume signal:**
> Built three-environment promotion pipeline (dev → staging → prod) with isolated LangSmith projects and typed configuration via `pydantic-settings` — prevented dev experiments from polluting production observability.

### Pillar 4 — CI/CD with automated eval (~2 hrs)

**What it gives you:** Every PR runs lint + tests + RAGAS eval. Streamlit Cloud auto-deploys main. Recruiters can see green CI badges on your GitHub.

**Build steps:**
- [ ] Add `.github/workflows/ci.yml`:
  - Job 1: `ruff check` + `mypy rag/`
  - Job 2: `pytest tests/`
  - Job 3: `python eval.py docs/test.pdf` (uses a small test PDF committed to the repo)
- [ ] Add GitHub Secrets: `GROQ_API_KEY`, `LANGSMITH_API_KEY` (staging keys, not prod)
- [ ] Fail CI if RAGAS faithfulness drops below a threshold
- [ ] Streamlit Cloud → enable auto-deploy from main
- [ ] Add status badges to README

**Resume signal:**
> CI pipeline (GitHub Actions) lints, type-checks, runs unit tests, and gates merges on RAGAS evaluation thresholds — caught two prompt regressions before they reached prod.

### Pillar 5 — RAGAS + LangSmith datasets (~2 hrs)

**What it gives you:** Industry-standard eval metrics (faithfulness, answer_relevancy, context_precision, context_recall). Datasets in LangSmith for regression testing. Visible numbers to put on resume.

**Build steps:**
- [ ] Add `ragas` + `datasets` to deps
- [ ] Convert `GOLDEN_SET` in `eval.py` from a list of dicts → a LangSmith Dataset (upload once, version it)
- [ ] Use `ragas.evaluate()` to compute all four metrics
- [ ] Persist results: write to `eval_results.json` + push to LangSmith run
- [ ] Make eval idempotent — same input → same trace ID for comparison

**Resume signal:**
> RAGAS evaluation harness (faithfulness 0.XX, answer_relevancy 0.YY, context_precision 0.ZZ) wired into CI and LangSmith datasets — every prompt change shows up as a deltable metric.

### Pillar 6 — Tests (~1.5 hrs)

**What it gives you:** Confidence to refactor. Green ✅ on GitHub. Demonstrates basic engineering hygiene.

**Build steps:**
- [ ] Add `pytest` + `pytest-asyncio` to dev deps
- [ ] Create `tests/` folder:
  - [ ] `tests/test_ingest.py` — chunking edge cases (empty page, single-char text, exact-chunk-size boundary)
  - [ ] `tests/test_retrieve.py` — dedup, score ordering, k-limit
  - [ ] `tests/test_router.py` — mocked Groq client, asserts valid JSON shape + intent validation
  - [ ] `tests/test_answer.py` — mocked client, asserts citation format in output
- [ ] Aim for ~70% line coverage in `rag/` — not chasing 100%, just covering the non-trivial logic

### Pillar 7 — Structured logging + cost tracking (~1.5 hrs)

**What it gives you:** Every request logged as JSON for grep-ability. Token costs tracked per session. LangSmith already covers traces, but local JSON logs let you tail without hitting the dashboard.

**Build steps:**
- [ ] Add `loguru` (one-liner setup, beats `logging` module)
- [ ] In `app.py`, log per request: `{request_id, query, intent, num_chunks, latency_ms, prompt_tokens, completion_tokens, cost_usd}`
- [ ] Show running session cost in sidebar (cents-level precision)
- [ ] Log to both stdout (Streamlit Cloud captures) AND `logs/askmydocs.jsonl` locally

### Pillar 8 — Production hardening (defer until after first 7) (~3 hrs)

- [ ] **Embedding cache to disk** (~30 min) — hash PDF → reload chunks/vectors instantly
- [ ] **Rate limiting** (~30 min) — `slowapi`-style limiter on `app.py` (per-IP soft limit for Streamlit Cloud)
- [ ] **Sentry error tracking** (~30 min) — free tier, catches exceptions in prod
- [ ] **Health check endpoint** (~30 min) — `/_health` returns Groq + embedding-model + FAISS-load status
- [ ] **Pre-commit hooks** (~30 min) — ruff + mypy + check-toml. Block bad code before it's committed.

---

## 📅 Recommended sequence (~12–15 hrs total)

| Order | Pillar | Hours | Why this order |
|---|---|---|---|
| 0 | **Deploy v1** (from PROGRESS.md) | 0.5 | Need live baseline first |
| 1 | LangSmith observability | 3 | Biggest wow factor; unblocks everything else |
| 2 | Env separation | 1.5 | Needed before adding more envs/secrets |
| 3 | Prompt versioning | 2 | LangSmith Hub auto-shows in traces |
| 4 | Tests | 1.5 | Foundation for safe CI |
| 5 | CI/CD | 2 | Surfaces everything as PR checks |
| 6 | RAGAS + datasets | 2 | Now you have CI to gate on |
| 7 | Logging + cost tracking | 1.5 | Polish; resume number |
| 8 | Hardening (pick 2) | ~1.5 | Stop when it looks "real" |

---

## 🎯 Resume bullet (target after v2)

> **AskMyDocs — Production-grade RAG chatbot** | Python, Streamlit, LangChain, LangSmith, Groq, FAISS, RAGAS
> - Built and deployed a chat-with-PDF app with two-call agentic LLM routing (intent classifier + answerer), achieving 0.XX RAGAS faithfulness and 0.YY answer relevancy on a 20-question golden set.
> - Instrumented the pipeline with LangSmith observability — every router decision, retrieval, and LLM call is traced with custom metadata; prompts are versioned in LangSmith Hub and pulled at runtime for A/B testing without redeploy.
> - Three-environment promotion (dev/staging/prod) with isolated LangSmith projects, GitHub Actions CI gating merges on RAGAS thresholds, and structured JSON logging.
> - Live demo: [URL] · GitHub: [URL]

---

## 🧠 Thinking style for v2

When building each pillar, ask:
1. "Could a senior engineer reviewing this say *'this person understands how AI apps actually run in production'*?"
2. "If someone broke this in a PR, would the CI catch it before it shipped?"
3. "If a user reported a bad answer in prod, could I find the trace in <2 minutes?"
4. "Is the prompt change a code change, or a config change?" (Should be config.)

These questions are also great interview prep — recruiters ask exactly these.

---

## 🚫 What's deliberately OUT of v2

To stay in scope:
- **Docker / Kubernetes** — overkill for a Streamlit Cloud app
- **Real database / Postgres** — FAISS in-memory is correct for single-PDF
- **Auth / multi-tenant** — single-tenant demo is fine for portfolio
- **Microservices / FastAPI split** — Streamlit handles UI; can split later if needed
- **Self-hosted LLM (Ollama/vLLM)** — Groq's free tier is the win
- **Mobile / native apps** — web demo is enough

The Tier 3 list in PROGRESS.md (agentic RAG with LangGraph, self-correcting RAG, ChromaDB) is also deferred until v2's seven pillars are done. Don't add MORE features; make the existing features look production-grade first.

---

## 🗺️ How to resume in a new session

Paste this prompt into a fresh Claude Code session:

> I'm continuing the AskMyDocs project at `C:\Users\smk\OneDrive\Desktop\NILESH-RESUME\`. Read `docs/PROGRESS.md` for v1 status and `docs/PROGRESS_v2_PRODUCTION.md` for the production roadmap. We just finished **[last pillar]** and are about to start **[next pillar]**.

The auto-memory will also reload your profile + the three feedback memories.
