"""Hybrid retrieval — combine BM25 keyword search with dense vector search.

Why hybrid?
- Vector search is great at semantic match ("the ache of moving on" ↔ "heartbreak")
  but can miss exact keyword hits (proper nouns, numbers, code identifiers).
- BM25 is the opposite: precise on rare tokens, blind to synonyms.
- Reciprocal Rank Fusion (RRF) merges the two ranked lists without needing
  to calibrate scales — it only uses ranks. Industry-standard fusion technique.
"""

import re

import numpy as np
from rank_bm25 import BM25Okapi


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


class BM25Searcher:
    """Pre-tokenized BM25 over the chunk list. Built once per PDF."""

    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self._tokenized = [_tokenize(c["text"]) for c in chunks]
        self._bm25 = BM25Okapi(self._tokenized)

    def search(self, query: str, k: int) -> list[dict]:
        scores = self._bm25.get_scores(_tokenize(query))
        top_idxs = np.argsort(scores)[::-1][:k]
        return [
            {**self.chunks[int(i)], "score": float(scores[int(i)]), "_idx": int(i)}
            for i in top_idxs
            if scores[int(i)] > 0
        ]


def reciprocal_rank_fusion(
    ranked_lists: list[list[dict]], k: int = 60
) -> list[dict]:
    """Merge ranked lists using RRF: score(d) = Σ 1 / (k + rank_r(d)).

    k=60 is the standard hyperparameter from the original RRF paper.
    """
    rrf_scores: dict[int, float] = {}
    chunk_map: dict[int, dict] = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked):
            idx = item["_idx"]
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + 1.0 / (k + rank)
            chunk_map[idx] = item

    ordered = sorted(rrf_scores.keys(), key=lambda i: rrf_scores[i], reverse=True)
    return [{**chunk_map[i], "score": rrf_scores[i], "_idx": i} for i in ordered]


def retrieve_hybrid(
    queries: list[str],
    embedder,
    index,
    chunks: list[dict],
    bm25: BM25Searcher,
    k_per_query: int,
    k_total: int,
) -> list[dict]:
    """For each query: vector search + BM25 search → RRF fuse → top k_total."""
    from .retrieve import retrieve

    all_rankings: list[list[dict]] = []
    for q in queries:
        all_rankings.append(retrieve(q, embedder, index, chunks, k=k_per_query))
        all_rankings.append(bm25.search(q, k=k_per_query))

    return reciprocal_rank_fusion(all_rankings)[:k_total]
