# AskMyDocs — Progress & Plan

> **Purpose:** Snapshot of where the build stands and what's next. Paste this into a new Claude / Claude Code session and you can resume without losing context.

**Last updated:** 2026-06-03
**Current status:** ✅ **Bio-hallucination bug fixed in production. Gemini 2.5 Flash answerer is live.**
Live at https://askmydocs-nilesh.streamlit.app/ · Repo at https://github.com/nilesh07g/askmydocs

## 🟢 Latest shipped (merge commit `3f11f3d`, 2026-06-03)

The two-day bio-hallucination saga is closed. Three layered fixes on branch `fix/history-poisoning` (now merged + deleted):

1. **History poisoning** — answerer no longer receives prior chat turns (router still handles conversational context). Confirmed via LangSmith trace that bad outputs no longer cascade across questions.
2. **Stop sequences** — Groq `stop=['</context>', '<context>', '</question>', '<question>']` prevents the model from inventing fake follow-up Q&A blocks in XML format.
3. **Answerer model swap** — Groq Llama-3.3-70B → Google Gemini 2.5 Flash. Llama exhibited parametric drift on biographical queries that prompt engineering could not fix; Gemini grounds correctly on identical inputs.

The Groq Llama-3.1-8B router stays (cheap intent classification). Only the answerer call moved providers.

### Production observability
- **Local dev traces** flow to LangSmith project `askmydocs-dev`
- **Production traces** flow to LangSmith project `askmydocs-prod` (separated for clean signal — recruiter clicks don't pollute development metrics)
- All `@traceable` decorators fire: `router`, `hybrid_retrieval`, `cross_encoder_rerank`, `answerer_stream`, `askmydocs_pipeline` (parent)

### Verified end-to-end on live URL
- "who is the author?" → "The author is Rithvik Singh ... Warmth ... (p. 146)" — grounded, cited, no hallucination
- "what does the author say about losing friends?" → real page 125 paraphrase
- LangSmith `askmydocs-prod` project receiving traces from prod users in real time

## ⏭️ Next session — Tier-2 polish (no urgency, app is solid)

1. **Prompts in LangSmith Hub** — push `ANSWERER_SYSTEM` + `ROUTER_SYSTEM` to LangSmith Hub. Replace hardcoded strings in `rag/prompts.py` with `pull_prompt()` calls. Tag versions per env (`:dev` / `:prod`). Outcome: edit prompts in LangSmith web UI without code redeploy. Est. 30–45 min on a fresh branch.
2. **Complete RAGAS rerun on Gemini** — once daily quota resets, full 10-question eval. Expected faithfulness jump 0.32 → 0.85+. Update README/PROGRESS.md with the new numbers.
3. **eval.py incremental persistence** — write `eval_results.json` after each question instead of at the end, so a mid-run crash doesn't waste the work.

---

## 🟢 Done so far

### Setup
- Project folder: `C:\Users\smk\OneDrive\Desktop\NILESH-RESUME\`
- Python 3.10 venv at `./venv/`
- All deps installed via `requirements.txt`
- Groq API key loaded from `.env` (server-side only — never in UI)

### RAG pipeline (working end-to-end)
- **Ingest** (`rag/ingest.py`): pdfplumber → per-page text → 800-char sliding-window chunks with 150-char overlap, page numbers preserved
- **Embed** (`rag/embed.py`): `sentence-transformers/all-MiniLM-L6-v2` → 384-dim vectors → FAISS `IndexFlatIP` (cosine sim via normalized inner product)
- **Retrieve** (`rag/retrieve.py`): single-query + multi-query with dedup
- **Router** (`rag/router.py`): Groq Llama 3.3 70B with `response_format=json_object` → returns `{"intent": "greeting|specific_question|global_question|off_topic", "search_queries": [...]}`
- **Answer** (`rag/answer.py`): Groq Llama 3.3 70B at temperature 0.1, natural prose output with `(p. N)` citations

### UI (`app.py`)
- Streamlit, ~200 lines
- Sidebar: PDF upload, current-doc info, Clear Chat, Developer Mode toggle, "How it works" expander
- Main: chat history, source expander under each assistant turn
- Dev Mode: shows routing JSON + similarity scores (off by default)

### Architecture decisions (locked in)
- **Two-call agentic flow** (router → answerer) instead of single-call + hardcoded keyword detection
- **Server-side secrets only** — no API-key field in the UI (caught by user as a security risk; lesson in memory)
- **Plain text chunk format** for the answerer prompt (`text\n(from page N)`) — proved that LLMs mirror input shape, so the input format must match the desired output to avoid markup leakage
- **JSON-mode for the router** (deterministic intent + queries)
- **Modular `rag/` package** (one concept per file, easy to read in order)

### Bugs squashed
| Bug | Fix |
|---|---|
| `Client.__init__() got an unexpected keyword argument 'proxies'` | Upgraded `groq` SDK to >=0.11 |
| `Connection error` masking model_decommissioned | Switched from `llama3-70b-8192` → `llama-3.3-70b-versatile` |
| API key visible in sidebar | Removed UI field; read from `.env` / `st.secrets` only |
| `[Source N \| Page X]` leaking into answers | Changed chunk format twice → settled on `text\n(from page N)` |
| "No secrets files found" red banner on local dev | `get_api_key()` probes for `secrets.toml` existence before touching `st.secrets` |
| Hardcoded greeting/global keyword lists (rejected before merge) | Replaced with LLM router |
| Mid-build summary answers were poor quality | Prompt now includes explicit GOOD vs BAD output examples; temperature lowered 0.3 → 0.1 |

### Project hygiene
- Folder structure refactored into `rag/` package + `docs/` folder
- `.gitignore` covers venv, .env, *.pkl, screenshots
- README.md simplified (no FAQ/roadmap clutter — just description, setup, eval, license)
- `eval.py` runs the same pipeline as `app.py` (no duplication of logic)
- Git history kept clean: no AI co-author trailers (preference saved to memory)

### 🚀 Tier 0 — Deploy ✅ DONE

- [x] GitHub repo created at https://github.com/nilesh07g/askmydocs
- [x] `git init`, initial commit, force-pushed to rewrite history without AI attribution
- [x] Push to GitHub via Git Credential Manager (browser OAuth)
- [x] Streamlit Cloud account + GitHub authorization
- [x] App deployed: https://askmydocs-nilesh.streamlit.app/
- [x] `GROQ_API_KEY` added to Streamlit Secrets (rotated once after IDE accidentally exposed the original)
- [x] Live URL added to README and pushed
- [x] Build fixed: pinned `runtime.txt = python-3.11` + relaxed `requirements.txt` pins (Cloud's default Python 3.13 lacks wheels for `faiss-cpu` and `sentence-transformers`)

### Deploy-time issues hit and resolved
| Symptom | Root cause | Fix |
|---|---|---|
| `installer returned a non-zero exit code` on Streamlit Cloud | Cloud uses Python 3.13 by default; `faiss-cpu==1.8.0` + `sentence-transformers==2.7.0` have no 3.13 wheels yet | Added `runtime.txt` with `python-3.11`, loosened version pins so resolver had room |
| `Error 401 Invalid API Key` on the live app | Stale/typo'd key in Streamlit Secrets after rotation | Re-pasted new key with correct TOML format `GROQ_API_KEY = "gsk_..."`, rebooted app from Manage app menu |
| `Error 429 Rate limit reached` after a few queries | Free tier cap of 100k tokens/day on `llama-3.3-70b-versatile` | None needed for now — resets in ~1h. Future fix documented: split into 8B router + 70B answerer to ~3x daily capacity |

---

## 🟡 Pending (in priority order)

### ⚙️ Tier 1 — High resume ROI ✅ DONE (merged to main 2026-05-28)

- [x] **Right-size models: 8B router + 70B answerer** — `LLM_MODEL_ROUTER = llama-3.1-8b-instant`, `LLM_MODEL_ANSWERER = llama-3.3-70b-versatile`. Faster routing, ~3x daily token budget.
- [x] **Streaming responses** — Groq `stream=True` + `st.write_stream`. Tokens appear live.
- [x] **Hybrid retrieval — BM25 + vector + RRF** — `rag/hybrid.py`. BM25 + dense fused via Reciprocal Rank Fusion (k=60).
- [x] **Cross-encoder reranking** — `rag/rerank.py`. `cross-encoder/ms-marco-MiniLM-L-6-v2`. Retrieves top-20 → reranks to top-5/12.
- [x] **Embedding cache to disk** — `rag/cache.py`. Re-uploading the same PDF is instant.
- [x] **RAGAS evaluation harness** — `eval.py` with real 10-question golden set for `docs/test.pdf` (gitignored). Judge runs on 8B (free tier budget).
- [x] **Ran RAGAS, recorded scores, surfaced a real bug.** See findings below.

### 📊 RAGAS findings on `docs/test.pdf` (10-Q golden set, 2026-06-02)

| Metric | Score | Interpretation |
|---|---|---|
| Context recall | **1.00** | Retrieval pulled every ground-truth fact into the top-K |
| Context precision | **0.67** | 2/3 of retrieved chunks are directly useful per question |
| Page-hit rate | **86%** | 6/7 fact-checkable questions retrieved the cited page |
| Faithfulness | 0.32 | ⚠️ Half the LLM's claims are not grounded in passages |
| Answer relevancy | 0.32 | ⚠️ Answerer drifts off-topic on biographical questions |

**The story the numbers tell:** the retrieval pipeline (hybrid BM25+vector → RRF → cross-encoder rerank) works very well — almost all relevant content makes it to the LLM. The answerer LLM (Llama 3.3 70B at temp 0.0) is the weak link: it grounds factual questions like "what does the author say about losing friends?" perfectly, but on biographical questions ("who is the author?", "what other book?") it generates plausible-sounding parametric content like "2 million Instagram followers" that does not appear in the document.

**Five prompt designs were tested over two days.** Each surfaced a different prompt-engineering pitfall (documented in feedback memory):
1. Original with literal "GOOD output" few-shot → the model copied the example verbatim
2. Universal system prompt with chunks in system message → the model treated chunks as a document to continue writing
3. Chunks in user message + `Passage N — page X:` numbered labels → the model invented Passage 6, 7, 8 with hallucinated content
4. XML-tagged `<context>...</context>` + `<question>...</question>` framing → reduced format leakage on first message but bio hallucination persisted
5. **Current (shipped):** XML-tagged framing + industry-grade structure (role / input format / reasoning / output rules / prohibitions / failure mode) — same Llama-3.3 70B parametric drift on biographical queries

**Verdict:** The bio hallucination is a **Llama 3.3 70B model limitation**, not a prompt bug. The model has strong parametric priors about "Instagram author" templates (millions of followers, bestselling books, podcasts, etc.) and interpolates them into responses for any document where the author is described as an Instagram writer — regardless of prompt structure. This was verified by reproducing the same hallucination in LangSmith Playground with hand-crafted reference passages.

### 🔭 LangSmith observability — DONE (2026-06-02)
- [x] **LangSmith tracing** for `router`, `hybrid_retrieval`, `cross_encoder_rerank`, `answerer`, plus parent `askmydocs_pipeline` trace
- [x] **Project:** `askmydocs-dev` at https://smith.langchain.com/o/fc5e30e2-ac74-4b14-b6a8-0246364862d0
- [x] **Trace-driven debugging proved the diagnosis** — saw the exact prompts, exact retrieved chunks, exact LLM output side-by-side. Confirmed retrieval is great, answerer is the weak link.

### ⏭️ Tier-2 follow-up: switch answerer model
- [ ] **Swap answerer LLM to Claude Haiku 3.5 or GPT-4o-mini.** Llama 3.3 70B's parametric drift on bio queries is the bottleneck. Stronger instruction-following models (Anthropic / OpenAI) should grounded RAG much better. Estimated ~30 min code change + free trial credit covers it.

**Resume bullet (honest, defensible in interviews):**
> Built a production-grade RAG pipeline (hybrid retrieval BM25+dense via RRF, cross-encoder reranking, agentic 8B/70B routing, token streaming, embedding cache) and instrumented it end-to-end with **LangSmith observability**. Evaluated with **RAGAS** on a 10-question golden set: **context recall 1.00, context precision 0.67, page-hit rate 86%**. Trace-driven analysis surfaced a Llama-3.3 70B grounding limitation on biographical queries; documented as a Tier-2 model-swap follow-up. Five prompt redesigns and a structured analysis of LLM input-shape-mirroring behaviors recorded as engineering artifacts.

### 🥈 Tier 2 — Strong differentiators (~6–8 hrs, pick 1–2)

- [ ] **Multi-document support**: Upload N PDFs, chat across all, citations include `(file.pdf, p. 3)`. Demonstrates product thinking. **(most demo-able)**
- [ ] **PDF page preview with highlight**: Click a source citation → opens that PDF page in-app with the chunk highlighted.
- [ ] **Conversation memory + summarization**: Long chats compress old turns. Shows you understand context-window economics.
- [ ] **LLM-as-judge eval**: Llama grades each answer 1–5 vs. expected. More rigorous than keyword matching.
- [ ] **Citation verifier**: After answer generation, check every `(p. X)` actually exists in retrieved chunks. Catches hallucination.

### 🥉 Tier 3 — Advanced (defer)

- [ ] **Agentic RAG with tool calling** (LangGraph territory): LLM picks between `vector_search`, `get_page(n)`, `find_quote`. Strong signal for "AI Engineer" roles.
- [ ] **Self-correcting RAG (CRAG)**: Low-confidence retrieval → reformulate → re-search → fall back to web.
- [ ] **Persistent vector store** (ChromaDB drop-in for FAISS): Survives restarts. Shows DB knowledge.
- [ ] **Streamlit auth + per-user collections**: Multi-tenant story.
- [ ] **Observability dashboard**: JSONL log of every query → metrics page (latency, top queries, retrieval scores).

---

## 🧠 Key learnings captured

These are saved in `~/.claude/projects/.../memory/` for future projects:

1. **Server-side secrets only** — never put API keys in user-facing UI fields, even with `type=password`.
2. **LLM-native over heuristics** — use a small LLM call for intent/routing decisions, not hardcoded keyword lists.
3. **Prompt shape mirroring** — LLMs copy the structure of their input. Fix format leakage by changing input format, not by adding "don't copy" rules. Lower temperature reinforces.
4. **No AI co-author trailers in commits** — keep git history showing solo authorship; recruiters reading commits should see consistent personal authorship.

---

## 🗺️ How to resume in a new session

Paste this prompt into a fresh Claude Code session:

> I'm continuing the AskMyDocs project at `C:\Users\smk\OneDrive\Desktop\NILESH-RESUME\`. Read `docs/PROGRESS.md` to see what's done and what's pending. We were about to **[next step from the pending list]**.

The auto-memory system will also re-inject the user profile, project context, and the three feedback memories listed above.

---

## 📦 Current file inventory

```
NILESH-RESUME/
├── app.py                  ← Streamlit UI (~200 lines)
├── eval.py                 ← 10-Q golden set eval harness
├── rag/                    ← all RAG logic, one concept per file
│   ├── __init__.py         ← guided tour
│   ├── config.py           ← constants
│   ├── prompts.py          ← system prompts (biggest lever on quality)
│   ├── ingest.py           ← PDF → chunks
│   ├── embed.py            ← embedding + FAISS
│   ├── retrieve.py         ← vector search
│   ├── router.py           ← LLM intent classifier
│   └── answer.py           ← LLM answer generator
├── docs/
│   ├── ASKMYDOCS_PROJECT_CONTEXT.md   ← original brief
│   ├── PROGRESS.md                    ← this file (v1 status)
│   └── PROGRESS_v2_PRODUCTION.md      ← production roadmap (LangSmith, CI/CD, RAGAS)
├── requirements.txt       (loosened pins for Streamlit Cloud compat)
├── runtime.txt            ← pins Python 3.11 on Streamlit Cloud
├── README.md
├── .gitignore
├── .env.example
├── .env                   ← gitignored, contains GROQ_API_KEY
└── venv/                  ← gitignored
```
