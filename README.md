# 📄 AskMyDocs — Chat With Any PDF

A chat-with-PDF app built on RAG (Retrieval-Augmented Generation). Upload any PDF, ask questions in natural language, get answers with exact page-number citations.

**Live demo:** _Add Streamlit Cloud URL here after deploying_
**Stack:** Python · Streamlit · Groq (Llama 3.3 70B) · FAISS · sentence-transformers · pdfplumber

---

## ✨ Features

- Upload any text-based PDF (textbook, research paper, contract, ...)
- Chat with multi-turn follow-ups
- Every answer cites the page numbers it used — verifiable
- Agentic two-call LLM pipeline (intent router → answerer), so greetings skip retrieval and summaries get broader doc coverage
- Source viewer shows the exact chunks behind each answer

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

# 4. Add your Groq API key (free at https://console.groq.com)
copy .env.example .env
# then open .env and paste your key

# 5. Run
streamlit run app.py
```

App opens at `http://localhost:8501`.

## 📊 Evaluation

```bash
python eval.py path/to/test.pdf
```

Runs a golden-set evaluation against the PDF — reports retrieval accuracy and answer keyword hits. Edit `GOLDEN_SET` in `eval.py` to match your test document.

## 📝 License

MIT
