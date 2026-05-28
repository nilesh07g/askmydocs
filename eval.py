"""AskMyDocs evaluation harness — RAGAS metrics on a golden set.

Computes four industry-standard RAG metrics for each question:
  - faithfulness        : does the answer match the retrieved context (no hallucination)?
  - answer_relevancy    : does the answer address the question asked?
  - context_precision   : are the retrieved chunks relevant?
  - context_recall      : did we retrieve enough to fully answer (vs ground_truth)?

Usage:
    python eval.py path/to/test_document.pdf

Edit the GOLDEN_SET below to match your test PDF. Each entry needs:
  - q              : the question
  - ground_truth   : the correct answer (used by context_recall + answer_relevancy)
  - expected_pages : optional; for the cheap retrieval-page check we also still run
"""

import os
import sys
import json
import time
from pathlib import Path

# Disable LangSmith tracing inside RAGAS (otherwise ragas tries to ship every
# judge call to api.smith.langchain.com — noisy and 403s without an API key).
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGSMITH_TRACING", "false")
os.environ.pop("LANGSMITH_API_KEY", None)
os.environ.pop("LANGCHAIN_API_KEY", None)

from dotenv import load_dotenv
from groq import Groq

from rag.config import (
    LLM_MODEL_ANSWERER,
    LLM_MODEL_ROUTER,
    TOP_K_INITIAL,
    TOP_K_SPECIFIC,
    TOP_K_GLOBAL,
    EMBED_MODEL_NAME,
)
from rag.ingest import extract_pages, chunk_pages
from rag.embed import load_embedder, embed_chunks, build_index_from_vectors
from rag.hybrid import BM25Searcher, retrieve_hybrid
from rag.rerank import load_reranker, rerank
from rag.router import route_query
from rag.answer import build_answer_messages, ask_groq

load_dotenv()


# ---- Golden set for docs/test.pdf (I Don't Love You Anymore by Rithvik Singh) ----
# Each ground_truth was hand-written from directly reading the cited pages.
# Question-type mix: factual lookup, thematic, multi-hop, quote, out-of-scope.
GOLDEN_SET = [
    # === Direct factual lookups ===
    {
        "q": "Who is the author of this book?",
        "ground_truth": "Rithvik Singh.",
        "expected_pages": [3, 146],
    },
    {
        "q": "What other book has this author written?",
        "ground_truth": "Warmth, published in 2021.",
        "expected_pages": [145, 146],
    },
    {
        "q": "Who is this book dedicated to?",
        "ground_truth": "The author's mother. The dedication thanks her for being the only person who always loves him, even at his worst.",
        "expected_pages": [4],
    },

    # === Thematic / global questions ===
    {
        "q": "What is the central theme of this book?",
        "ground_truth": "Love, heartbreak, and emotional healing. The book is a collection of short poems and reflections about the pain of losing love, longing, friendship loss, and learning to value oneself enough to walk away from relationships that hurt.",
        "expected_pages": [],
    },
    {
        "q": "What kind of writing style does the author use?",
        "ground_truth": "Short, poetic prose and free-verse poems with an introspective, emotional tone. Many pages contain only a few lines. The writing uses imagery drawn from nature — flowers, rain, the sky, the sun, and the ocean — to express feelings of love and loss.",
        "expected_pages": [],
    },

    # === Multi-hop / synthesis ===
    {
        "q": "Does the author believe love should require fighting for someone's attention?",
        "ground_truth": "No. The author argues that love should not feel like a tug of war, a race, or a fight. Love is not a trophy you have to fight for, but a gift someone wants to give you every day without you having to ask. If you have to constantly struggle to make space in someone's heart, they do not deserve to be with you.",
        "expected_pages": [60],
    },

    # === Specific quote / passage ===
    {
        "q": "What does the author compare life with a former lover to in a 'half sun-lit room'?",
        "ground_truth": "Life with that person, where their love brought darkness in equal measure to light, and the pain never fully left, so the author chose to leave.",
        "expected_pages": [100],
    },
    {
        "q": "What does the author say about losing friends over time?",
        "ground_truth": "You lose friends without noticing — only realizing it later when you see an old photograph and the people you were once closest to are no longer in your life. Even childhood friends, the ones you sat next to in school or invited to your birthday parties, can quietly slip away.",
        "expected_pages": [125],
    },

    # === Out-of-scope / negative (tests honest 'I don't know' behavior) ===
    {
        "q": "What university did the author attend?",
        "ground_truth": "The book does not state where the author studied or which university he attended.",
        "expected_pages": [],
    },

    # === Reader engagement / closing ===
    {
        "q": "How can readers contact the author?",
        "ground_truth": "Through Instagram at @wordsofrithvik. The book invites readers to write to him there if they enjoyed the book.",
        "expected_pages": [145, 146],
    },
]


def run_pipeline(client, user_query, embedder, index, chunks, bm25, reranker):
    """Same agentic flow as app.py — no Streamlit UI, returns full result dict."""
    route_info = route_query(client, user_query, history=[])
    intent = route_info["intent"]
    queries = route_info["search_queries"]

    if intent in ("greeting", "off_topic") or not queries:
        retrieved = []
    else:
        final_k = TOP_K_GLOBAL if intent == "global_question" else TOP_K_SPECIFIC
        candidates = retrieve_hybrid(
            queries or [user_query], embedder, index, chunks, bm25,
            k_per_query=6, k_total=TOP_K_INITIAL,
        )
        retrieved = rerank(user_query, candidates, reranker, k=final_k)

    messages = build_answer_messages(user_query, retrieved, history=[])
    answer = ask_groq(client, messages)
    return {"answer": answer, "retrieved": retrieved, "route_info": route_info}


def run_ragas(items: list[dict]):
    """Score the (question, answer, contexts, ground_truth) items with RAGAS."""
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    )
    from langchain_groq import ChatGroq
    from langchain_huggingface import HuggingFaceEmbeddings

    api_key = os.getenv("GROQ_API_KEY")
    # Judge runs on 8B (LLM_MODEL_ROUTER) instead of 70B — the 70B free tier
    # caps at 100k tokens/day and a full RAGAS pass blows through it. The 8B
    # has ~1M TPD and is still a reliable judge for these metrics on portfolio
    # eval scale (note the model in any resume claim about the scores).
    judge_llm = ChatGroq(model=LLM_MODEL_ROUTER, api_key=api_key, temperature=0.0)
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL_NAME)

    dataset = Dataset.from_dict({
        "question": [it["q"] for it in items],
        "answer": [it["answer"] for it in items],
        "contexts": [[c["text"] for c in it["retrieved"]] for it in items],
        "ground_truth": [it.get("ground_truth", "") for it in items],
    })

    return evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=judge_llm,
        embeddings=embeddings,
    )


def evaluate_pdf(pdf_path: str):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: Set GROQ_API_KEY in your .env file first.")
        sys.exit(1)

    print(f"\n[1/4] Loading PDF: {pdf_path}")
    with open(pdf_path, "rb") as f:
        pages = extract_pages(f)
    print(f"      Extracted {len(pages)} pages")

    print("[2/4] Chunking + embedding + indexing...")
    chunks = chunk_pages(pages)
    embedder = load_embedder()
    vectors = embed_chunks(chunks, embedder)
    index = build_index_from_vectors(vectors)
    bm25 = BM25Searcher(chunks)
    reranker = load_reranker()
    print(f"      Built index with {len(chunks)} chunks")

    print(f"[3/4] Running pipeline on {len(GOLDEN_SET)} questions...\n")
    client = Groq(api_key=api_key)

    items = []
    page_hits = 0
    questions_with_expected_pages = 0
    for i, q in enumerate(GOLDEN_SET, 1):
        print(f"  Q{i}: {q['q']}")
        out = run_pipeline(client, q["q"], embedder, index, chunks, bm25, reranker)
        retrieved_pages = sorted({r["page"] for r in out["retrieved"]})

        expected = set(q.get("expected_pages") or [])
        if expected:
            questions_with_expected_pages += 1
            if expected & set(retrieved_pages):
                page_hits += 1

        items.append({
            "q": q["q"],
            "ground_truth": q.get("ground_truth", ""),
            "answer": out["answer"],
            "retrieved": out["retrieved"],
            "intent": out["route_info"]["intent"],
            "retrieved_pages": retrieved_pages,
        })
        print(f"      intent={out['route_info']['intent']}  pages={retrieved_pages}")
        print(f"      answer: {out['answer'][:120].strip()}{'...' if len(out['answer']) > 120 else ''}\n")
        time.sleep(0.5)

    print("[4/4] Computing RAGAS metrics (this calls Groq several times, ~30-60s)...")
    ragas_dict = None
    try:
        ragas_result = run_ragas(items)
        # ragas 0.4.x: EvaluationResult exposes per-row scores via to_pandas().
        # Metric names are the non-input columns. Average across rows for the summary.
        df = ragas_result.to_pandas()
        input_cols = {
            "user_input", "response", "retrieved_contexts", "reference",
            "question", "answer", "contexts", "ground_truth",
        }
        metric_cols = [c for c in df.columns if c not in input_cols]
        ragas_dict = {col: float(df[col].mean(skipna=True)) for col in metric_cols}

        print("\n=========== RAGAS SCORES ===========")
        for metric, score in ragas_dict.items():
            score_str = "NaN (judge calls failed)" if score != score else f"{score:.3f}"
            print(f"  {metric:25s} : {score_str}")
        print("====================================")
    except Exception as e:
        print(f"\n  [WARN] RAGAS evaluation failed: {e}")
        print("        (Falling back to keyword/page eval only.)")

    if questions_with_expected_pages:
        acc = page_hits / questions_with_expected_pages * 100
        print(f"\n  Cheap retrieval check (any expected page hit): "
              f"{page_hits}/{questions_with_expected_pages} ({acc:.0f}%)")

    # Persist results for later comparison
    output = {
        "ragas": ragas_dict,
        "page_hit_rate": page_hits / questions_with_expected_pages
            if questions_with_expected_pages else None,
        "items": [
            {
                "q": it["q"],
                "ground_truth": it["ground_truth"],
                "answer": it["answer"],
                "intent": it["intent"],
                "retrieved_pages": it["retrieved_pages"],
            }
            for it in items
        ],
    }
    out_path = Path("eval_results.json")
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\nFull results written to {out_path.resolve()}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python eval.py path/to/test.pdf")
        sys.exit(1)
    evaluate_pdf(sys.argv[1])
