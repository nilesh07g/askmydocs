"""Embedding model + FAISS index.

Turn each chunk of text into a 384-dim vector, then build an in-memory FAISS
index that lets us find the most similar chunks to any query in milliseconds.
"""

import faiss
import streamlit as st
from sentence_transformers import SentenceTransformer

from .config import EMBED_MODEL_NAME


@st.cache_resource(show_spinner="Loading embedding model (one-time, ~30s)...")
def load_embedder() -> SentenceTransformer:
    """Load the sentence-transformer once per session.

    @st.cache_resource keeps the model in memory across Streamlit reruns so we
    don't reload 80MB every time the user types.
    """
    return SentenceTransformer(EMBED_MODEL_NAME)


def build_faiss_index(chunks: list[dict], embedder: SentenceTransformer):
    """Embed every chunk and build a cosine-similarity FAISS index.

    We L2-normalize the vectors and use IndexFlatIP (inner product). On
    normalized vectors, inner product == cosine similarity.
    """
    texts = [c["text"] for c in chunks]
    vectors = embedder.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
    ).astype("float32")

    faiss.normalize_L2(vectors)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    return index, vectors
