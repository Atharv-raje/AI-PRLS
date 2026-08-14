"""The Tutor Manager: receives a student message, routes it, runs the right
specialist, logs everything for research, and returns a payload the frontend
can render (plain text, a question card, or a progress card)."""
from __future__ import annotations

import json

from . import agents, db

# One pending question per student, held server-side between /chat and /answer
_pending: dict[str, dict] = {}


async def handle_chat(study_id: str, message: str) -> dict:
    db.log_message(study_id, "student", message)
    history = db.recent_messages(study_id)

    decision = await agents.route(message, history)
    route = decision["route"]

    if route == "quiz":
        try:
            q = await agents.make_question(
                study_id, decision.get("chapter"), decision.get("topic") or "general"
            )
        except Exception:
            text = ("I had trouble writing a well-formed question just now — "
                    "please ask me again in a moment.")
            mid = db.log_message(study_id, "assistant", text, route)
            return {"type": "text", "text": text, "message_id": mid, "route": route}
        _pending[study_id] = q
        student_view = {k: q[k] for k in
                        ("format", "stem", "options", "chapter", "domain", "topic", "bloom_level")}
        mid = db.log_message(study_id, "assistant", json.dumps(student_view), route)
        instruction = (
            "Choose the ONE best answer, then briefly tell me why you chose it."
            if q["format"] == "single"
            else "Choose the THREE best responses, then briefly tell me why."
        )
        return {
            "type": "question",
            "question": student_view,
            "instruction": instruction,
            "message_id": mid,
            "route": route,
        }

    if route == "progress":
        note, stats = await agents.progress_note(study_id)
        mid = db.log_message(study_id, "assistant", note, route)
        return {"type": "progress", "text": note, "stats": stats,
                "message_id": mid, "route": route}

    if route == "explain":
        text = await agents.explain(message, decision.get("topic") or message, history)
    else:
        text = await agents.small_talk(message, history)
    mid = db.log_message(study_id, "assistant", text, route)
    return {"type": "text", "text": text, "message_id": mid, "route": route}


async def handle_answer(study_id: str, selected: list[int], explanation: str) -> dict:
    q = _pending.get(study_id)
    if not q:
        text = "I don't have an open question for you — say \"quiz me\" to get one."
        mid = db.log_message(study_id, "assistant", text, "coach")
        return {"type": "text", "text": text, "message_id": mid, "route": "coach"}

    db.log_message(
        study_id, "student",
        json.dumps({"selected": selected, "explanation": explanation}),
    )
    result = await agents.coach(q, selected, explanation)
    db.log_attempt(study_id, q, selected, explanation, result["verdict"], result.get("bloom_level"))
    _pending.pop(study_id, None)

    result["correct_options"] = q["correct"]
    result["rationales"] = q.get("rationales", [])
    mid = db.log_message(study_id, "assistant", json.dumps(result), "coach")
    return {"type": "coaching", **result, "message_id": mid, "route": "coach"}
