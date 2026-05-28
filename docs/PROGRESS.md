# AskMyDocs — Progress & Plan

> **Purpose:** Snapshot of where the build stands and what's next. Paste this into a new Claude / Claude Code session and you can resume without losing context.

**Last updated:** 2026-05-28
**Current status:** 🚀 **v1 DEPLOYED.** Live at https://askmydocs-nilesh.streamlit.app/ · Repo at https://github.com/nilesh07g/askmydocs

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

### ⚙️ Tier 1 — High resume ROI (~4–6 hrs total) — **DO THIS NEXT**

Do these in order. Each is a clear bullet on the resume.

- [ ] **Right-size models: 8B router + 70B answerer** (~15 min): Use `llama-3.1-8b-instant` for the router, keep `llama-3.3-70b-versatile` for the answerer. ~3x daily token budget on free tier, faster routing, reads as a real engineering decision. (Quick win — do first.)
- [ ] **Streaming responses** (~30 min): Use Groq `stream=True` + `st.write_stream`. Tokens appear live like ChatGPT. Big UX upgrade.
- [ ] **Hybrid retrieval — BM25 + vector + RRF** (~1 hr): Add `rank_bm25`, run BM25 keyword search alongside FAISS, fuse with Reciprocal Rank Fusion. Industry standard. Talk-worthy in interviews.
- [ ] **Cross-encoder reranking** (~30 min): Add `cross-encoder/ms-marco-MiniLM-L-6-v2`. Retrieve top-20 with FAISS, rerank to top-5. Typical 10–20% accuracy lift.
- [ ] **Embedding cache to disk** (~30 min): Pickle `chunks + vectors` keyed by PDF hash. Re-uploading same PDF is instant. Shows production thinking.
- [ ] **RAGAS evaluation** (~1.5 hrs): Add `ragas` lib to `eval.py`. Compute `faithfulness`, `answer_relevancy`, `context_precision`, `context_recall`. Recruiters grep resumes for "RAGAS".

**Resume bullet after Tier 1:**
> Built a production-style RAG pipeline with hybrid retrieval (BM25 + dense), cross-encoder reranking, and RAGAS evaluation (faithfulness 0.XX, answer relevancy 0.XX on a 20-Q golden set).

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
