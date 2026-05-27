"""AskMyDocs — RAG pipeline package.

Read these in order to learn how the pipeline works:

1. config.py   — tunable constants (chunk size, top-K, model names)
2. prompts.py  — LLM system prompts (the single biggest lever on output quality)
3. ingest.py   — PDF → pages → chunks (no AI yet, just text wrangling)
4. embed.py    — load embedding model, turn chunks into vectors, build FAISS index
5. retrieve.py — vector similarity search (single-query + multi-query with dedup)
6. router.py   — LLM call #1: classify intent + propose search queries
7. answer.py   — LLM call #2: write the final natural-language answer

app.py at the project root is the Streamlit UI. It imports from here.
"""
