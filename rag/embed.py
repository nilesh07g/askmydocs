"""Embedding model + FAISS index.

Turn each chunk of text into a 384-dim vector, then build an in-memory FAISS
index that lets us find the most similar chunks to any query in milliseconds.
"""

import faiss
import numpy as np
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


def embed_chunks(chunks: list[dict], embedder: SentenceTransformer) -> np.ndarray:
    """Embed every chunk and return L2-normalized vectors (float32)."""
    texts = [c["text"] for c in chunks]
    vectors = embedder.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
    ).astype("float32")
    faiss.normalize_L2(vectors)
    return vectors


def build_index_from_vectors(vectors: np.ndarray):
    """Build a cosine-similarity FAISS index from already-normalized vectors.

    IndexFlatIP + L2-normalized vectors == cosine similarity.
    """
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    return index


def build_faiss_index(chunks: list[dict], embedder: SentenceTransformer):
    """Convenience: embed chunks + build the index in one call."""
    vectors = embed_chunks(chunks, embedder)
    return build_index_from_vectors(vectors), vectors
