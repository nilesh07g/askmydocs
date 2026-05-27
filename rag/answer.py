"""LLM answer generation (the second of two LLM calls per user message).

Given the user's query + retrieved chunks + chat history, build the answerer
prompt and call Groq to produce the final natural-language reply.
"""

from groq import Groq

from .config import LLM_MODEL
from .prompts import ANSWERER_SYSTEM_TEMPLATE


def build_answer_messages(
    user_query: str,
    retrieved: list[dict],
    history: list[dict],
) -> list[dict]:
    """Assemble the messages list for the answerer LLM call.

    If retrieved is empty (greeting / off-topic), we tell the LLM there are no
    excerpts so it falls back to a conversational reply.
    """
    if retrieved:
        # Plain page-tagged passages. No special markup the model could mimic.
        # Each passage shows up like a footnote-style "(from page N)" trailer.
        context_block = "\n\n".join(
            f"{r['text']}\n(from page {r['page']})"
            for r in retrieved
        )
        source_section = context_block
    else:
        source_section = (
            "(No reference passages were retrieved — the user is greeting, "
            "chatting socially, or asking something off-topic.)"
        )

    system_msg = ANSWERER_SYSTEM_TEMPLATE.format(source_section=source_section)

    messages = [{"role": "system", "content": system_msg}]
    for turn in history[-6:]:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_query})
    return messages


def ask_groq(client: Groq, messages: list[dict], temperature: float = 0.1) -> str:
    """Call Groq and return the assistant's reply as a string.

    Low temperature (0.1) keeps the answerer deterministic and reduces the
    chance of the model improvising format leaks or hallucinated content.
    """
    completion = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=1024,
    )
    return completion.choices[0].message.content
