# 📄 AskMyDocs — Chat With Any PDF

A chat-with-PDF app built on RAG (Retrieval-Augmented Generation). Upload any PDF, ask questions in natural language, get answers with exact page-number citations.

**Live demo:** https://askmydocs-nilesh.streamlit.app/

**Stack:** Python · Streamlit · Groq (Llama 3.1 8B router) · Google Gemini 2.5 Flash (answerer) · FAISS · BM25 · sentence-transformers · cross-encoder reranker · LangSmith · RAGAS · pdfplumber

---

## ✨ Features

- Upload any text-based PDF (textbook, research paper, contract, ...)
- Chat with natural-language questions; every answer cites the page numbers it used
- **Hybrid retrieval** — BM25 keyword search + dense vector search, fused via Reciprocal Rank Fusion
- **Cross-encoder reranking** of top-20 candidates down to the most relevant 5–12
- **Agentic two-call LLM pipeline** — a small 8B router decides intent + search queries, then a stronger answerer LLM writes the reply. Greetings skip retrieval; summaries get broader doc coverage
- **Streaming responses** — tokens appear live like ChatGPT
- **End-to-end LangSmith observability** — every router decision, retrieval, rerank, and LLM call is traced with metadata
- **Embedding cache** — re-uploading the same PDF is instant
- Source viewer shows the exact chunks behind each answer (with rerank scores in Developer Mode)

## 🚀 Run locally

```powershell
# 1. Clone
git clone https://github.com/nilesh07g/askmydocs.git
cd askmydocs

# 2. Create + activate a Python 3.10 venv (Windows PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Get two free API keys, paste both into .env
#    - Groq      : https://console.groq.com           (for the 8B router LLM)
#    - Gemini    : https://aistudio.google.com/apikey (for the answerer LLM — free tier)
copy .env.example .env
# then open .env and paste both keys

# 5. (Optional) LangSmith tracing — sign up free at https://smith.langchain.com,
#    add LANGSMITH_API_KEY + LANGSMITH_PROJECT + LANGSMITH_TRACING=true to .env

# 6. Run
streamlit run app.py
```

App opens at `http://localhost:8501`.

## 📊 Evaluation

The eval harness uses [RAGAS](https://docs.ragas.io) to compute industry-standard RAG metrics — faithfulness, answer relevancy, context precision, context recall — against a 10-question golden set.

```bash
# Install eval-only dependencies (kept separate from the main app deps)
pip install -r requirements-eval.txt

# Run
python eval.py path/to/test.pdf
```

Edit `GOLDEN_SET` in `eval.py` to match your test document.

## 📁 Project structure

```
app.py              # Streamlit UI (~200 lines)
eval.py             # RAGAS evaluation harness
rag/
  config.py         # Tunable constants (chunk size, top-K, model names)
  prompts.py        # System prompts (router + answerer)
  ingest.py         # PDF → page-tagged chunks
  embed.py          # Embedding model + FAISS index
  retrieve.py       # Vector retrieval (single + multi-query)
  hybrid.py         # BM25 + dense fusion via RRF
  rerank.py         # Cross-encoder reranking
  router.py         # LLM intent classifier (Groq Llama-3.1-8B)
  answer.py         # LLM answer generator (Gemini 2.5 Flash)
  cache.py          # On-disk embedding cache
docs/PROGRESS.md    # Build journal — what's done, what's pending, design decisions
```

## 📝 License

MIT
