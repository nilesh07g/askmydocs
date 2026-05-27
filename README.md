# 📄 AskMyDocs — Chat With Any PDF

A Retrieval-Augmented Generation (RAG) chatbot that lets you upload any PDF and ask questions about it in natural language. Answers include exact page-number citations, so you can verify every claim.

**Live demo:** _Add Streamlit Cloud URL after deploying_
**Tech:** Python · Streamlit · LangChain concepts · Groq (Llama 3.3 70B) · FAISS · sentence-transformers · pdfplumber

---

## ✨ What it does

- Upload any text-based PDF (textbook, research paper, brochure, contract...)
- Ask questions like *"What's the main argument in chapter 3?"* or *"What does the author say about X?"*
- Get answers grounded **only** in the document, with **page-number citations** on every claim
- Multi-turn chat — follow-up questions work
- Source viewer shows the exact chunks the LLM used (with similarity scores)

## 🧠 How the RAG pipeline works

```
PDF upload
   │
   ▼
[pdfplumber] extract text per page
   │
   ▼
[chunker] 800-char chunks, 150-char overlap, page numbers preserved
   │
   ▼
[sentence-transformers all-MiniLM-L6-v2] → 384-dim vectors
   │
   ▼
[FAISS IndexFlatIP] in-memory cosine similarity index
   │
   ▼
User question ─► embed ─► retrieve top-4 chunks
   │
   ▼
[Groq · Llama 3.3 70B] answers using only those chunks, cites pages
```

## 🚀 Run locally

```bash
# 1. Clone
git clone https://github.com/nilesh07g/askmydocs.git
cd askmydocs

# 2. Create venv (Windows PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install deps
pip install -r requirements.txt

# 4. Add your Groq API key
copy .env.example .env
# Open .env and paste your key from https://console.groq.com

# 5. Run
streamlit run app.py
```

App opens at `http://localhost:8501`.

## 📊 Evaluation

A 10-question golden set in `eval.py` measures retrieval accuracy + answer keyword hits on a test document.

```bash
python eval.py path/to/test.pdf
```

Output:
```
Retrieval accuracy : 8/10 (80%)
Answer keyword hit : 7/10 (70%)
```

_(Edit the `GOLDEN_SET` list in `eval.py` to match your specific test PDF.)_

## ☁️ Deploy free

1. Push this repo to GitHub
2. Go to https://share.streamlit.io → **New app**
3. Pick the repo, main branch, `app.py`
4. **Advanced settings → Secrets** — add:
   ```
   GROQ_API_KEY = "gsk_..."
   ```
5. Deploy. Done.

## 🛠️ Design choices (FAQ for interviewers)

**Why chunk size 800 / overlap 150?**
~800 chars is roughly one paragraph — small enough that retrieval is precise, large enough to keep semantic context. The 150-char overlap prevents answers from being cut off at chunk boundaries.

**Why `all-MiniLM-L6-v2` embeddings?**
80MB, runs on CPU, 384-dim — fast enough to embed a 200-page PDF in under a minute on a laptop, while quality is good enough for short-form Q&A. Trade-off: a larger model like `bge-large-en` would improve recall ~5–10% but is overkill here.

**Why FAISS over Pinecone/Chroma/Qdrant?**
Single-PDF use case fits entirely in RAM. No DB to install, no network hop, zero infra cost. For multi-tenant / persistent / 100k-doc scale I'd reach for Qdrant or pgvector.

**Why Groq?**
Free tier + sub-second Llama 3.3 70B inference. Latency is the demo's wow-factor; Groq's LPU makes the answer appear faster than ChatGPT does.

**Why top-K = 4?**
Empirically the best precision/recall trade-off for this prompt size. K=2 misses context; K=8 dilutes the prompt with weakly-relevant chunks and degrades the answer.

## 🗺️ Roadmap

- [ ] OCR support for scanned PDFs (Tesseract)
- [ ] Persistent vector store (swap FAISS → Chroma) so the same PDF doesn't re-embed
- [ ] Multi-document chat
- [ ] Streaming token output
- [ ] Better eval: LLM-judge for answer correctness

## 📝 License

MIT
