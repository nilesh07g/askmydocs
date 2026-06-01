"""LLM-based query router (the first of two LLM calls per user message).

Given the user's message + recent chat history, ask Llama to:
  1. Classify intent (greeting / specific_question / global_question / off_topic)
  2. Generate the search queries we should run against the FAISS index

This replaces hardcoded keyword matching with a small, fast LLM call that
generalizes to any phrasing or language.
"""

import json

from groq import Groq
from langsmith import traceable

from .config import LLM_MODEL_ROUTER
from .prompts import ROUTER_SYSTEM

VALID_INTENTS = {"greeting", "specific_question", "global_question", "off_topic"}


@traceable(run_type="llm", name="router", metadata={"model": LLM_MODEL_ROUTER})
def route_query(client: Groq, user_query: str, history: list[dict]) -> dict:
    """Classify intent + propose search queries.

    Returns {"intent": str, "search_queries": list[str]}.
    Falls back to ("specific_question", [user_query]) if the LLM call fails.
    """
    messages = [{"role": "system", "content": ROUTER_SYSTEM}]
    # Brief history so follow-ups like "and the next chapter?" route correctly
    for turn in history[-2:]:
        messages.append({"role": turn["role"], "content": turn["content"][:300]})
    messages.append({"role": "user", "content": user_query})

    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL_ROUTER,
            messages=messages,
            temperature=0.0,
            max_tokens=256,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content)
        intent = data.get("intent", "specific_question")
        queries = data.get("search_queries", []) or []
        if intent not in VALID_INTENTS:
            intent = "specific_question"
        return {"intent": intent, "search_queries": queries}
    except Exception:
        # Safe fallback so a router failure never breaks the chat
        return {"intent": "specific_question", "search_queries": [user_query]}
