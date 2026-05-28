"""Tunable constants for the RAG pipeline.

Change a number here and the whole app picks it up — useful when experimenting
with chunk sizes, retrieval depth, or swapping models.
"""

# ---- Embedding model ----
# Small (80MB), CPU-friendly, 384-dim vectors. Good default for short-form Q&A.
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

# ---- Chunking ----
# We split each page into overlapping windows so retrieval is precise but
# answers aren't cut off at chunk boundaries.
CHUNK_SIZE = 800       # characters per chunk (~1 paragraph)
CHUNK_OVERLAP = 150    # overlap between consecutive chunks

# ---- Retrieval ----
# Two-stage retrieval:
#   1. Hybrid (BM25 + vector + RRF) fetches a wide pool of TOP_K_INITIAL candidates
#   2. Cross-encoder reranker scores each candidate against the query
#   3. We keep TOP_K_SPECIFIC or TOP_K_GLOBAL after rerank — these go to the LLM.
TOP_K_INITIAL = 20     # how many candidates hybrid retrieval pulls before reranking
TOP_K_SPECIFIC = 5     # final chunks sent to the answerer for focused questions
TOP_K_GLOBAL = 12      # final chunks sent for summary / theme / overview questions

# ---- LLM ----
# Two models, right-sized for the task:
#   - Router: small, fast — intent classification + 3-4 search queries is easy.
#   - Answerer: larger, capable — natural prose synthesis needs reasoning.
# Bonus: the 8B has ~10x the daily free-tier limit, so we burn through fewer
# tokens on every chat message.
LLM_MODEL_ROUTER = "llama-3.1-8b-instant"
LLM_MODEL_ANSWERER = "llama-3.3-70b-versatile"

# Kept so any old `from rag.config import LLM_MODEL` import keeps working.
LLM_MODEL = LLM_MODEL_ANSWERER
