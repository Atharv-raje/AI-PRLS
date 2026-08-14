"""Thin client for the local vLLM server (OpenAI-compatible chat API).

Includes a MOCK mode (AIPRLS_MOCK_LLM=1) that returns canned responses so the
frontend and database can be tested on a laptop with no GPUs.
"""
from __future__ import annotations

import json
import re

import httpx

from . import config


def _strip_fences(text: str) -> str:
    """Remove ```json ... ``` fences if the model added them."""
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else text.strip()


def extract_json(text: str) -> dict:
    """Best-effort extraction of a single JSON object from model output."""
    text = _strip_fences(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # fall back to the outermost {...}
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError(f"No JSON object found in model output: {text[:200]}")


# ---------------------------------------------------------------------------

_MOCK_RESPONSES = {
    "router": '{"route": "explain", "chapter": null, "topic": "general"}',
    "question": json.dumps(
        {
            "format": "single",
            "domain": 3,
            "chapter": 1,
            "topic": "exam pacing",
            "bloom_level": "application",
            "stem": "MOCK MODE — the LLM server is not connected. This is a placeholder "
            "question. An OT student has 90 items left and 60 minutes remaining on a "
            "computer-based certification exam. What is the MOST effective next step?",
            "options": [
                "Answer every remaining item with detailed re-reading of each stem",
                "Mark a consistent answer choice for all remaining items, then revisit "
                "as time allows",
                "Leave the remaining items blank to avoid penalty",
                "Restart the exam tutorial to reduce anxiety",
            ],
            "correct": [1],
            "rationales": [
                "Too slow given the time remaining.",
                "Correct — guessing carries no penalty and preserves review time.",
                "Blank answers score zero; unanswered items waste the guessing odds.",
                "The tutorial cannot be reopened and would consume exam time.",
            ],
            "textbook_pointer": "Review the time-management strategies in Chapter 1 "
            "of your TherapyEd book.",
        }
    ),
    "coach": json.dumps(
        {
            "verdict": "correct",
            "bloom_level": "application",
            "feedback": "MOCK MODE — placeholder coaching. Your answer is correct, and "
            "your explanation shows you weighed the time constraint. One habit to keep: "
            "you named the rule (no penalty for guessing) before choosing — that is "
            "exactly the reasoning the exam rewards.",
            "trap": None,
            "next_step": "MOCK MODE — example Socratic follow-up. Now think about a "
            "client whose pacing struggles come from test anxiety rather than a skill "
            "gap — what is the underlying cause you'd need to identify before choosing "
            "a strategy for them?",
            "textbook_pointer": "See the test-taking strategy tables in Chapter 1 of "
            "your TherapyEd book.",
        }
    ),
    "explain": "MOCK MODE — the LLM server is not connected, so this is a placeholder "
    "explanation. When the model is running, I would first ask you one guiding question "
    "aimed at where your understanding seems to be on the Bloom's ladder, then give a "
    "plain-language explanation with a short clinical example, then close with one "
    "Socratic follow-up question one level up (for example, asking you to apply the "
    "idea to a new client) before pointing you to the right chapter of your TherapyEd "
    "book.",
    "progress": "MOCK MODE — placeholder summary. With the model connected, this would "
    "be a short plain-language note about what is getting stronger and what to practice "
    "next, based on your logged attempts.",
    "chat": "MOCK MODE — hello! The LLM server is not connected. Start it with "
    "scripts/start_llm.sh, or keep exploring the interface: try the Practice and Ask "
    "buttons on the left.",
}


def _mock_route(messages: list[dict]) -> str:
    """Keyword routing so every flow can be demoed without a GPU."""
    last = messages[-1]["content"].lower() if messages else ""
    if any(w in last for w in ("quiz", "question", "practice", "test me", "drill")):
        return '{"route": "quiz", "chapter": 1, "topic": "certification"}'
    if any(w in last for w in ("progress", "how am i doing", "stats", "study next")):
        return '{"route": "progress", "chapter": null, "topic": "general"}'
    if any(w in last for w in ("hello", "hi", "hey", "thanks", "what can you")):
        return '{"route": "chat", "chapter": null, "topic": "general"}'
    return '{"route": "explain", "chapter": null, "topic": "general"}'


async def chat(role: str, system: str, messages: list[dict]) -> str:
    """Send a chat completion request. `role` picks generation settings."""
    if config.MOCK_LLM:
        if role == "router":
            return _mock_route(messages)
        return _MOCK_RESPONSES.get(role, _MOCK_RESPONSES["chat"])

    gen = config.GEN.get(role, config.GEN["chat"])
    payload = {
        "model": config.LLM_MODEL,
        "messages": [{"role": "system", "content": system}] + messages,
        "temperature": gen["temperature"],
        "max_tokens": gen["max_tokens"],
    }
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(
            f"{config.LLM_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {config.LLM_API_KEY}"},
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
