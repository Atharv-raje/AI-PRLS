"""The agent team. Each function is one specialist; the orchestrator composes them."""
from __future__ import annotations

import json

from .. import db, llm, rag
from . import prompts


async def route(message: str, history: list[dict]) -> dict:
    """Classify the student's message. Falls back to 'chat' on any parse issue."""
    convo = history[-4:] + [{"role": "user", "content": message}]
    raw = await llm.chat("router", prompts.ROUTER, convo)
    try:
        result = llm.extract_json(raw)
        if result.get("route") in {"quiz", "explain", "progress", "chat"}:
            return result
    except (ValueError, json.JSONDecodeError):
        pass
    return {"route": "chat", "chapter": None, "topic": "general"}


async def make_question(study_id: str, chapter: int | None, topic: str) -> dict:
    """Generate one original NBCOT-style item, grounded in companion notes."""
    query = f"chapter {chapter} {topic}" if chapter else topic
    context = rag.context_block(query)
    recent = db.recent_topics(study_id)
    user_msg = (
        f"Requested chapter: {chapter or 'any'}\n"
        f"Requested topic: {topic}\n\n"
        f"Companion notes (the study team's own material):\n{context}\n\n"
        f"Topics of this student's recent questions (avoid repeating these "
        f"scenarios): {', '.join(recent) if recent else 'none yet'}\n\n"
        "Write one new question now. Vary the format: use the six-option "
        "'scenario' format roughly one time in three."
    )
    raw = await llm.chat("question", prompts.QUESTION_MAKER, [{"role": "user", "content": user_msg}])
    q = llm.extract_json(raw)
    _validate_question(q)
    return q


def _validate_question(q: dict) -> None:
    fmt = q.get("format")
    n_opts = len(q.get("options", []))
    n_correct = len(q.get("correct", []))
    ok = (fmt == "single" and n_opts == 4 and n_correct == 1) or (
        fmt == "scenario" and n_opts == 6 and n_correct == 3
    )
    if not ok:
        raise ValueError(f"Malformed question from model: format={fmt}, "
                         f"options={n_opts}, correct={n_correct}")
    if len(q.get("rationales", [])) != n_opts:
        q["rationales"] = ["(no rationale provided)"] * n_opts


async def coach(question: dict, selected: list[int], explanation: str) -> dict:
    """Grade + coach the student's answer and, above all, their reasoning."""
    correct = sorted(question["correct"])
    verdict_hint = (
        "correct" if sorted(selected) == correct
        else "partly" if set(selected) & set(correct) and question["format"] == "scenario"
        else "incorrect"
    )
    user_msg = (
        f"QUESTION JSON:\n{json.dumps(question, indent=2)}\n\n"
        f"STUDENT SELECTED (zero-based indices): {selected}\n"
        f"STUDENT'S EXPLANATION OF WHY: {explanation or '(none given)'}\n\n"
        f"Scoring computed by the system: {verdict_hint}. Use this verdict.\n"
        "Coach the reasoning now."
    )
    raw = await llm.chat("coach", prompts.REASONING_COACH, [{"role": "user", "content": user_msg}])
    try:
        result = llm.extract_json(raw)
        result["verdict"] = verdict_hint  # system scoring is authoritative
        return result
    except (ValueError, json.JSONDecodeError):
        return {
            "verdict": verdict_hint,
            "feedback": raw,
            "trap": None,
            "next_step": "Try another question when you're ready.",
            "textbook_pointer": question.get("textbook_pointer", ""),
        }


async def explain(message: str, topic: str, history: list[dict]) -> str:
    context = rag.context_block(topic)
    user_msg = (
        f"Companion notes (the study team's own material):\n{context}\n\n"
        f"The student asks: {message}"
    )
    convo = history[-4:] + [{"role": "user", "content": user_msg}]
    return await llm.chat("explain", prompts.EXPLAINER, convo)


async def progress_note(study_id: str) -> tuple[str, dict]:
    s = db.stats(study_id)
    if s["total_attempts"] == 0:
        return (
            "You haven't answered any practice questions yet, so there's nothing to "
            "chart. Try \"quiz me\" to get started — your progress will build here.",
            s,
        )
    raw = await llm.chat(
        "progress",
        prompts.PROGRESS,
        [{"role": "user", "content": f"Student statistics JSON:\n{json.dumps(s, indent=2)}"}],
    )
    return raw, s


async def small_talk(message: str, history: list[dict]) -> str:
    convo = history[-6:] + [{"role": "user", "content": message}]
    return await llm.chat("chat", prompts.CHAT, convo)
