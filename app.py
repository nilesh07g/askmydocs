"""AskMyDocs — Streamlit UI.

This file is intentionally thin. All RAG logic lives in the `rag/` package:
  rag/ingest.py   — PDF → chunks
  rag/embed.py    — chunks → FAISS vector index
  rag/retrieve.py — query → top-k chunks
  rag/router.py   — LLM intent classifier
  rag/answer.py   — LLM answer generator

Read `rag/__init__.py` for a guided tour.
"""

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from groq import Groq

from rag.config import TOP_K_SPECIFIC, TOP_K_GLOBAL
from rag.ingest import extract_pages, chunk_pages
from rag.embed import load_embedder, embed_chunks, build_index_from_vectors
from rag.router import route_query
from rag.answer import build_answer_messages, ask_groq
from rag.hybrid import BM25Searcher, retrieve_hybrid
from rag import cache as embed_cache

load_dotenv()


# -------------------- Page config --------------------
st.set_page_config(
    page_title="AskMyDocs - Chat with your PDF",
    page_icon="📄",
    layout="wide",
)


# -------------------- API key resolution --------------------
def get_api_key() -> str:
    """Resolve GROQ_API_KEY from local .env first, then Streamlit Cloud secrets.

    We probe for a secrets.toml file before touching st.secrets to avoid the
    "No secrets files found" warning on local dev where only .env is used.
    """
    key = os.getenv("GROQ_API_KEY", "")
    if key:
        return key

    secrets_paths = [
        Path(".streamlit") / "secrets.toml",
        Path.home() / ".streamlit" / "secrets.toml",
    ]
    if any(p.exists() for p in secrets_paths):
        try:
            return st.secrets.get("GROQ_API_KEY", "")
        except Exception:
            return ""
    return ""


api_key = get_api_key()


# -------------------- Session state --------------------
for key, default in {
    "chunks": None,
    "index": None,
    "bm25": None,
    "pdf_name": None,
    "num_pages": 0,
    "num_chunks": 0,
    "history": [],
}.items():
    st.session_state.setdefault(key, default)


# -------------------- Header --------------------
st.title("📄 AskMyDocs")
st.caption("Upload a PDF and chat with it. Answers cite the exact source pages.")


# -------------------- Sidebar --------------------
with st.sidebar:
    st.header("📎 Upload PDF")
    pdf_file = st.file_uploader("Choose a PDF", type=["pdf"])

    if pdf_file is not None and pdf_file.name != st.session_state.pdf_name:
        # Hash file bytes to look up the embedding cache
        pdf_bytes = pdf_file.getvalue()
        file_hash = embed_cache.pdf_hash(pdf_bytes)
        cached = embed_cache.load(file_hash)

        if cached is not None:
            with st.spinner("Loading cached embeddings (instant)..."):
                chunks = cached["chunks"]
                vectors = cached["vectors"]
                index = build_index_from_vectors(vectors)
                bm25 = BM25Searcher(chunks)
                # Re-extract pages just for the page count display
                pdf_file.seek(0)
                pages = extract_pages(pdf_file)
            st.success(
                f"Ready (from cache)! {len(pages)} pages, {len(chunks)} chunks."
            )
        else:
            pdf_file.seek(0)
            with st.spinner("Reading PDF..."):
                pages = extract_pages(pdf_file)
            if not pages:
                st.error("Couldn't extract any text. Is this a scanned PDF?")
                pages = []

            if pages:
                with st.spinner("Chunking + embedding (first time may take ~30s)..."):
                    chunks = chunk_pages(pages)
                    embedder = load_embedder()
                    vectors = embed_chunks(chunks, embedder)
                    index = build_index_from_vectors(vectors)
                    bm25 = BM25Searcher(chunks)
                    embed_cache.save(file_hash, chunks, vectors)
                st.success(f"Ready! {len(pages)} pages, {len(chunks)} chunks indexed.")

        if pages:
            st.session_state.chunks = chunks
            st.session_state.index = index
            st.session_state.bm25 = bm25
            st.session_state.pdf_name = pdf_file.name
            st.session_state.num_pages = len(pages)
            st.session_state.num_chunks = len(chunks)
            st.session_state.history = []

    if st.session_state.pdf_name:
        st.divider()
        st.markdown(
            f"**Current doc:** `{st.session_state.pdf_name}`\n\n"
            f"**Pages:** {st.session_state.num_pages}  \n"
            f"**Chunks:** {st.session_state.num_chunks}"
        )
        if st.button("🗑️ Clear chat", use_container_width=True):
            st.session_state.history = []
            st.rerun()

    st.divider()
    dev_mode = st.toggle(
        "🛠️ Developer mode",
        value=False,
        help="Show routing decisions, search queries, and similarity scores.",
    )

    with st.expander("ℹ️ How it works"):
        st.markdown(
            "1. PDF → ~800-char chunks (150-char overlap), embedded with "
            "`all-MiniLM-L6-v2` → FAISS index\n"
            "2. **Router LLM** classifies each message (greeting / specific / summary "
            "/ off-topic) and proposes the search queries — no hardcoded keywords\n"
            "3. Retrieve top chunks per query, dedupe across queries\n"
            "4. **Answerer LLM** (Llama 3.3 70B via Groq) writes a natural answer "
            "with `(p. X)` citations\n"
            "5. Greetings & off-topic messages skip retrieval entirely"
        )


# -------------------- Helpers --------------------
def render_sources(retrieved: list[dict], show_scores: bool):
    """Source expander shown under every answer that used retrieval."""
    if not retrieved:
        return
    with st.expander(f"📚 Sources ({len(retrieved)} chunks)"):
        for i, src in enumerate(retrieved, 1):
            score_text = f" _(similarity: {src['score']:.2f})_" if show_scores else ""
            st.markdown(f"**Source {i} — Page {src['page']}**{score_text}")
            preview = src["text"][:500] + ("..." if len(src["text"]) > 500 else "")
            st.text(preview)
            st.divider()


def run_pipeline(client: Groq, user_query: str, embedder, dev: bool):
    """Two-LLM-call agentic pipeline: route → hybrid retrieve → answer."""
    with st.spinner("Routing..."):
        route_info = route_query(client, user_query, st.session_state.history)

    intent = route_info["intent"]
    queries = route_info["search_queries"]

    if intent in ("greeting", "off_topic") or not queries:
        retrieved = []
    elif intent == "global_question":
        with st.spinner("Searching across the document..."):
            retrieved = retrieve_hybrid(
                queries,
                embedder,
                st.session_state.index,
                st.session_state.chunks,
                st.session_state.bm25,
                k_per_query=4,
                k_total=TOP_K_GLOBAL,
            )
    else:
        with st.spinner("Searching..."):
            retrieved = retrieve_hybrid(
                queries or [user_query],
                embedder,
                st.session_state.index,
                st.session_state.chunks,
                st.session_state.bm25,
                k_per_query=TOP_K_SPECIFIC,
                k_total=TOP_K_SPECIFIC,
            )

    messages = build_answer_messages(user_query, retrieved, st.session_state.history)
    with st.spinner("Thinking..."):
        answer = ask_groq(client, messages)
    return answer, retrieved, route_info


# -------------------- Main chat area --------------------
if not api_key:
    st.error(
        "⚠️ `GROQ_API_KEY` not configured on the server.\n\n"
        "• Local dev: add it to your `.env` file\n"
        "• Streamlit Cloud: add it in **App settings → Secrets**"
    )
elif st.session_state.index is None:
    st.info("👈 Upload a PDF in the sidebar to start chatting with it.")
else:
    # Replay history
    for turn in st.session_state.history:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"])
            if turn["role"] == "assistant" and turn.get("sources"):
                render_sources(turn["sources"], show_scores=dev_mode)

    # Chat input
    user_query = st.chat_input("Ask anything about your PDF...")
    if user_query:
        with st.chat_message("user"):
            st.markdown(user_query)

        embedder = load_embedder()
        client = Groq(api_key=api_key)

        with st.chat_message("assistant"):
            try:
                answer, retrieved, route_info = run_pipeline(
                    client, user_query, embedder, dev_mode
                )
                st.markdown(answer)

                if dev_mode:
                    with st.expander(
                        f"🧭 Routing: **{route_info['intent']}** · "
                        f"{len(retrieved)} chunks used"
                    ):
                        st.json(route_info)

                render_sources(retrieved, show_scores=dev_mode)
            except Exception as e:
                st.error(f"Error: {e}")
                answer = f"_Error: {e}_"
                retrieved = []

        st.session_state.history.append({"role": "user", "content": user_query})
        st.session_state.history.append(
            {"role": "assistant", "content": answer, "sources": retrieved}
        )
