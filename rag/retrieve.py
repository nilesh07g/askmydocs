"""Vector retrieval — single query, and multi-query with dedup.

Given a query string and the FAISS index built in embed.py, return the chunks
most likely to contain the answer.
"""

import faiss


def retrieve(query: str, embedder, index, chunks: list[dict], k: int) -> list[dict]:
    """Return the top-k chunks most similar to the query.

    Each result has the original chunk's {"page", "text"} plus:
      - "score": cosine similarity in [0, 1]
      - "_idx":  chunk's position in the original list (used to dedupe in retrieve_multi)
    """
    q_vec = embedder.encode([query], convert_to_numpy=True).astype("float32")
    faiss.normalize_L2(q_vec)
    scores, idxs = index.search(q_vec, k)

    results = []
    for score, i in zip(scores[0], idxs[0]):
        if i == -1:
            continue
        results.append({**chunks[int(i)], "score": float(score), "_idx": int(i)})
    return results


def retrieve_multi(
    queries: list[str],
    embedder,
    index,
    chunks: list[dict],
    k_per_query: int,
    k_total: int,
) -> list[dict]:
    """Run several queries, dedupe by chunk index, return the top k_total by score.

    Used for global questions where the router LLM has generated multiple
    diverse queries (e.g. ["introduction", "main themes", "conclusion"]) to
    pull broad coverage of the document.
    """
    seen = set()
    pooled = []
    for q in queries:
        for r in retrieve(q, embedder, index, chunks, k=k_per_query):
            if r["_idx"] in seen:
                continue
            seen.add(r["_idx"])
            pooled.append(r)
    pooled.sort(key=lambda x: x["score"], reverse=True)
    return pooled[:k_total]
