"""Cross-encoder reranking — second-stage relevance scoring.

After hybrid retrieval gives us ~20 candidate chunks, a cross-encoder model
re-scores each (query, chunk) pair jointly. Unlike a bi-encoder (which
embeds query and chunk separately), the cross-encoder sees them together, so
it captures nuance like "X happened to Y" vs "Y happened to X".

Typical gain over vector-only retrieval: 10-20% in recall@5 on QA benchmarks.
The trade-off is latency — but we only score 20 pairs, not the whole corpus,
so this stays under ~100ms on CPU.
"""

import streamlit as st
from langsmith import traceable
from sentence_transformers import CrossEncoder

CROSS_ENCODER_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@st.cache_resource(show_spinner="Loading reranker (one-time, ~10s)...")
def load_reranker() -> CrossEncoder:
    """~80MB cross-encoder fine-tuned on MS MARCO. Cached per session."""
    return CrossEncoder(CROSS_ENCODER_NAME)


@traceable(run_type="tool", name="cross_encoder_rerank", metadata={"model": CROSS_ENCODER_NAME})
def rerank(
    query: str,
    candidates: list[dict],
    reranker: CrossEncoder,
    k: int,
) -> list[dict]:
    """Score (query, candidate.text) pairs with the cross-encoder; return top-k."""
    if not candidates:
        return []
    pairs = [(query, c["text"]) for c in candidates]
    scores = reranker.predict(pairs, show_progress_bar=False)
    ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    return [{**c, "score": float(s), "rerank_score": float(s)} for c, s in ranked[:k]]
