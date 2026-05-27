# AskMyDocs — Full Project Handoff Context

> **Purpose of this file:** Paste this entire file into a new Claude Code / ChatGPT / any-LLM session to give it full context. The next session can pick up exactly where we left off.

---

## 1. Who I Am (the user)

- **Name:** Ganja Nilesh
- **College:** IIIT Sricity, B.Tech (Aug 2022 – June 2026), CGPA 8.08
- **Current role:** AI Product Analyst Intern (1-year internship, Aug 11 2025 – 2026)
- **Career target:** AI Intern / AI Engineer roles after current internship ends
- **GitHub:** `nilesh07g` | **LeetCode:** `NileshGanja`
- **OS / Hardware:** Windows 11, AMD Ryzen 7 5700U, 16GB RAM, integrated Radeon graphics (no dedicated GPU)
- **Already installed:** Python 3.10.0, VS Code

### Important context about my skill level
- I built earlier projects (AI Brochure Generator with LLMs/FastAPI/React, Font Recognition CNN, MERN Book-Store) about **10 months ago and remember almost nothing**.
- Treat me as a **near-beginner**. Explain concepts only when we actively use them.
- Give me **ONE tiny step at a time**. Never dump a wall of instructions.
- Wait for me to paste output / errors before moving to the next step.

---

## 2. The Project: AskMyDocs

### What we're building (plain English)
A web app where you upload any PDF (textbook, research paper, brochure) and then **chat with it**. Ask questions in natural language. The app finds the relevant sections, sends them to an LLM, and returns an answer with the exact source page/chunk cited.

Same concept as ChatPDF / NotebookLM / Perplexity-but-for-your-docs.

### Why this specific project
- "RAG over documents" is the #1 most common AI use case in industry today
- Demonstrates ALL the core AI Intern skills: embeddings, vector search, RAG architecture, prompt engineering, evals, deployment
- Achievable in **4 weeks** on a basic laptop with **all free-tier tools**
- Demoable in 30 seconds for recruiters
- Solves a real problem I'll actually use

### Final resume bullet target
> **AskMyDocs — Chat-with-PDF App** | Python, Streamlit, LangChain, Groq, FAISS, sentence-transformers
> - Built and deployed a Retrieval-Augmented Generation (RAG) chatbot answering questions over any uploaded PDF with per-chunk source citations.
> - Implemented semantic chunking + FAISS vector retrieval using sentence-transformer embeddings; served Llama 3 70B inference via Groq API for sub-second response.
> - Built a 20-question golden eval set; achieved 85% retrieval accuracy on a 200-page test document.
> - Deployed via Streamlit Cloud with public live demo. [link] [github]

---

## 3. Tech Stack (deliberately simple, beginner-friendly, free-tier-only)

**Do NOT suggest upgrading to Next.js / Docker / Qdrant / Langfuse / LangGraph / Redis yet.** Those are explicitly deferred to "after the basic version works." We start simple.

| Layer | Tool | Why this choice | Cost |
|---|---|---|---|
| Language | Python 3.10 | Already installed | Free |
| UI | **Streamlit** | Pure Python, no React/HTML/CSS needed | Free |
| LLM API | **Groq** | Free tier, runs Llama 3 70B super fast | Free |
| Backup LLM | OpenAI (GPT-4o-mini) | Higher quality for final demo only | $5 free credit |
| RAG framework | **LangChain** (basic, not LangGraph) | Easiest first introduction to RAG | Free |
| Vector store | **FAISS** (in-memory) | No database to install, runs in Python | Free |
| Embeddings | **sentence-transformers** (HuggingFace) | Tiny model, runs on laptop CPU | Free |
| PDF reading | **pdfplumber** | Cleaner text extraction than pypdf | Free |
| Env management | `python-dotenv` + venv | Standard | Free |
| Hosting | **Streamlit Community Cloud** | 1-click deploy from GitHub | Free |
| Source control | GitHub (public repo) | Already have account | Free |

**Total project cost: $0.**

---

## 4. The 4-Week Plan

### Week 1 — Setup + Hello AI
- Create project folder + Python virtual environment
- Get free Groq API key
- Install Streamlit + Groq client
- Build a basic chat UI that talks to Llama 3 (no documents yet)
- **End-of-week deliverable:** A ChatGPT-clone running in browser via `streamlit run app.py`
- **Skills learned:** venv, env vars, calling an LLM API, Streamlit basics

### Week 2 — PDF Ingestion + Embeddings
- Add PDF upload widget in Streamlit
- Extract text with pdfplumber
- Split text into chunks (semantic chunking)
- Convert chunks → vectors using sentence-transformers
- Store in FAISS index (in-memory)
- **End-of-week deliverable:** App can ingest a PDF and "remember" it
- **Skills learned:** chunking strategies, embeddings (what they really are), vector similarity

### Week 3 — RAG Pipeline + Citations
- When user asks question → embed question → find top-K similar chunks → send to LLM with the chunks as context
- Show source page numbers in the answer
- Add chat history (multi-turn conversation)
- **End-of-week deliverable:** Working RAG chatbot — the "magic moment"
- **Skills learned:** RAG architecture, prompt engineering, context-window management

### Week 4 — Eval + Polish + Deploy
- Build a 20-question "golden set" with known correct answers
- Measure retrieval accuracy + answer quality
- Push code to GitHub
- Deploy to Streamlit Community Cloud → public URL
- Write a short LinkedIn / Medium post about what I built
- **End-of-week deliverable:** Live demo URL + GitHub repo + blog post
- **Skills learned:** Evals (the recruiter differentiator), deployment, technical writing

---

## 5. Where We Are RIGHT NOW

**Current step:** Week 1, Step 1 — Project setup.

**Completed:** Nothing yet. Just verified Python 3.10 + VS Code + 16GB RAM hardware.

**Next mini-steps in order (resume here):**
1. Create folder `C:\Users\smk\OneDrive\Desktop\AskMyDocs`
2. Open folder in VS Code
3. Open VS Code terminal — confirm prompt shows the AskMyDocs path
4. Create venv: `python -m venv venv`
5. Activate venv: `.\venv\Scripts\Activate.ps1` (may need `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` first)
6. Verify terminal prompt now shows `(venv)` prefix

**Then Week 1 Step 2:** Install Streamlit + Groq, get a free Groq API key, write a 10-line hello-AI chat app.

---

## 6. How To Coach Me (instructions for the next AI assistant)

- **One tiny step at a time.** Maximum 5 mini-actions per message. Then wait.
- **Always give the EXACT command to copy-paste.** No "now configure X" — show the literal lines.
- **Explain concepts only when we touch them.** Don't pre-teach embeddings before we use them.
- **After every command, ask me to paste the output back.** Especially errors.
- **No jargon without translation.** If you say "vectorize," immediately add "(turn text into a list of numbers that represents its meaning)."
- **No suggesting fancier tools yet.** Stick to the simple stack above until the basic version is working and deployed.
- **Build → understand → next.** Run the code first, explain it second. Momentum > theory.
- **When I get stuck, debug WITH me.** Don't just say "the error means X" — give the exact command to fix it.

---

## 7. Useful Links & Accounts Needed

- **Groq Console (free API key):** https://console.groq.com
- **Streamlit docs:** https://docs.streamlit.io
- **LangChain docs:** https://python.langchain.com
- **sentence-transformers:** https://www.sbert.net
- **Streamlit Cloud deploy:** https://share.streamlit.io
- **My GitHub:** https://github.com/nilesh07g

---

## 8. Things Explicitly OUT OF SCOPE (for now)

Do not introduce until basic 4-week project is shipped:
- LangGraph / agentic workflows
- Docker / containerization
- Self-hosted Qdrant, Weaviate, Pinecone
- Next.js / React frontend
- Langfuse / Arize observability
- Redis caching
- Fine-tuning / LoRA / QLoRA
- Multi-agent systems
- Multimodal (vision/audio) features

These come **after** the simple version is live on the internet and on my resume.

---

## 9. My Working Style

- I can give ~6-8 hours/week (have an ongoing 1-year internship in parallel)
- I learn by doing, not by reading textbooks
- I may forget concepts week-to-week — re-explain when needed without judgment
- I prefer copy-paste-runnable code over abstract explanations
- I want a working v1 fast, then iterate — not perfect-on-first-try
