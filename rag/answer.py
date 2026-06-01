"""LLM answer generation (the second of two LLM calls per user message).

Given the user's query + retrieved chunks + chat history, build the answerer
prompt and call Groq to produce the final natural-language reply.
"""

from groq import Groq

from .config import LLM_MODEL_ANSWERER
from .prompts import ANSWERER_SYSTEM


def _format_user_turn(user_query: str, retrieved: list[dict]) -> str:
    """Wrap the user's question with the reference passages for this turn.

    Putting passages in the USER message (not the system message) makes the
    model treat them as references for THIS question, not as a document to
    extend. Big drop in hallucination vs. embedding passages in the system role.
    """
    if not retrieved:
        return user_query

    passages = "\n\n".join(
        f"Passage {i+1} — page {r['page']}:\n{r['text']}"
        for i, r in enumerate(retrieved)
    )
    return (
        "Reference passages (use ONLY these to answer; do not draw on any "
        "outside knowledge):\n\n"
        f"{passages}\n\n"
        "---\n\n"
        f"Question: {user_query}"
    )


def build_answer_messages(
    user_query: str,
    retrieved: list[dict],
    history: list[dict],
) -> list[dict]:
    """Assemble the messages list for the answerer LLM call.

    Layout:
      system   = identity + behavior rules (static; no chunks)
      history  = last few turns of plain Q/A (no chunks repeated)
      user     = THIS turn's chunks + THIS turn's question
    """
    messages = [{"role": "system", "content": ANSWERER_SYSTEM}]
    for turn in history[-6:]:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": _format_user_turn(user_query, retrieved)})
    return messages


def ask_groq(client: Groq, messages: list[dict], temperature: float = 0.0) -> str:
    """Call Groq and return the assistant's reply as a single string (non-streaming).

    Temperature 0.0 (greedy decoding) maximises faithfulness — the LLM is least
    likely to drift into parametric knowledge when forced to take the highest-
    probability token at every step. Trade-off: slightly less varied phrasing.
    """
    completion = client.chat.completions.create(
        model=LLM_MODEL_ANSWERER,
        messages=messages,
        temperature=temperature,
        max_tokens=1024,
    )
    return completion.choices[0].message.content


def stream_groq(client: Groq, messages: list[dict], temperature: float = 0.0):
    """Yield tokens as they arrive from Groq. Used with st.write_stream in the UI.

    Temperature kept at 0.0 to match ask_groq — so RAGAS eval scores reflect
    actual production behavior, not a slightly different (warmer) regime.
    """
    stream = client.chat.completions.create(
        model=LLM_MODEL_ANSWERER,
        messages=messages,
        temperature=temperature,
        max_tokens=1024,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
