# AI-PRLS Progress Report

**Project:** AI-Supported Professional Reasoning and Learning Success (AI-PRLS)  
**Component:** Version 1 prototype — Fishbowl learning environment  
**Author:** Atharv Raje  
**Date:** August 2026  
**Status:** Demo-ready (mock mode); pilot prep in progress

---

## Demo link

**Live demo (click to open):**  
https://guiding-silenced-raffle.ngrok-free.dev

**How to try it:**
1. Open the link (click **Visit Site** if ngrok shows a warning page).
2. Enter any study ID (e.g. `demo01`).
3. Check the consent box → **Enter**.
4. Try: `quiz me on chapter 1`, `I don't understand splinting`, `how am I doing?`

**Note:** Demo runs on craft-1 in tmux (app + ngrok). Free ngrok URLs may change if the tunnel is restarted — check with the server admin for the current link.

**Code repository:** https://github.com/Atharv-raje/AI-PRLS

---

## Executive summary

The Version 1 prototype delivers the three core student flows defined in the simple plan: **Practice**, **Ask**, and **Check progress**. The chat interface, multi-agent backend, research logging, and responsible-use guardrails are implemented and tested. The system is deployed on the shared server (`craft-1`) and exposed via ngrok for team review.

The app currently runs in **mock mode** (canned AI responses). Connecting the real local LLM (Qwen2.5-14B via vLLM on GPUs) and expanding companion documents for 2–3 pilot chapters are the main remaining technical steps before a student pilot.

---

## Update — 2026-08-14: Bloom's-taxonomy Socratic scaffolding

Responding directly to the collaborator's review of the tutor instructions
(feedback + Bloom's Taxonomy question-stem chart): questions and coaching
now explicitly use Socratic prompting tied to Bloom's cognitive levels
(Knowledge → Comprehension → Application → Analysis → Synthesis →
Evaluation).

- New companion doc `companion_docs/02_blooms_taxonomy_ladder.md` grounds the
  ladder and question stems in the team's own material.
- **Question Maker** now tags each generated item with a `bloom_level` and
  varies level (mostly Application/Analysis, occasional Knowledge/
  Comprehension or Synthesis/Evaluation), shown on the question card.
- **Reasoning Coach** now diagnoses the Bloom's level a student's explanation
  demonstrates and ends with one targeted Socratic question aimed at the
  next level up, instead of a generic "try another question" line.
- **Explainer** ("I don't get it") now aims its opening guiding question at
  the level just above the student's apparent confusion, and closes with one
  Socratic follow-up question one level higher than the explanation given.
- Practice attempts now log `bloom_level`; the progress view shows an
  accuracy-by-cognitive-level chart alongside chapter/domain.
- Scope note: this pass is single-shot (one Socratic nudge per response),
  not a persistent multi-turn ladder state machine — a decision made to keep
  this shippable before the pilot; flagged as a possible V2 deepening.

## Alignment with the prototype plan

### Three ground rules

| Rule | Status | Implementation |
|------|--------|----------------|
| 1. The textbook stays the textbook | Done | Shared agent prompts forbid reproduction; tutor refers to chapters/sections only |
| 2. Teach reasoning, not memorization | Done | Reasoning Coach asks for "why" and feedback on thinking, not just correctness |
| 3. Pedagogy is permanent; model is replaceable | Done | Prompts in `backend/agents/prompts.py`; RAG over team's companion docs |

### Version 1 student activities (simple plan)

| Activity | Plan requirement | Status |
|----------|------------------|--------|
| **Practice** — quiz + reasoning feedback | Core V1 | Done |
| **Ask** — Socratic explanations | Core V1 | Done |
| **Check progress** — stats + summary | Core V1 | Done |
| Study plan builder | Deferred (later V) | Not built |
| Timed strategy drills | Deferred (later V) | Not built |

### Multi-agent backend

| Agent / role | Status |
|--------------|--------|
| Tutor Manager (Router) | Done — routes to quiz / explain / progress / chat |
| Question Maker | Done — single-answer and 6-option scenario formats |
| Reasoning Coach | Done — verdict + feedback on stated reasoning |
| Explainer | Done — Socratic explanations with textbook pointers |
| Progress narrator | Done — plain-language summary from logged stats |
| Study Planner | Not in V1 scope | — |

### Pilot & research requirements

| Requirement | Status |
|-------------|--------|
| Consent gate + anonymous study ID | Done |
| Log all messages | Done (SQLite) |
| Log question attempts + student reasoning | Done |
| Thumbs up/down feedback | Done |
| Baseline / end quizzes & surveys | Not built (team + IRB decision) |
| Faculty question review workflow | Not built (process TBD at kickoff) |

### Responsible-use guardrails

| Guardrail | Status |
|-----------|--------|
| Disclosure (study tool, can make mistakes, not NBCOT) | Done — login screen + prompts |
| Copyright (decline to reproduce textbook) | Done — in every agent prompt |
| Privacy (study IDs only) | Done — SQLite keyed by study ID |
| Academic honesty (no graded coursework) | Done — in shared prompt rules |

---

## What was completed

### Development
- Multi-agent FastAPI backend with router, question maker, reasoning coach, explainer, and progress agents
- Plain academic chat UI (login, sidebar shortcuts, question cards, coaching feedback, progress bars)
- RAG over companion documents with offline keyword fallback
- Mock mode for demos without GPUs (`AIPRLS_MOCK_LLM=1`)
- Smoke test suite (`scripts/smoke_test.sh`) — all tests pass
- Bug fix: RAG graceful fallback when embedding model unavailable offline

### Deployment
- Code pushed to GitHub: `Atharv-raje/AI-PRLS`
- Cloned to server: `/home/atharv/AI-PRLS` on `craft-1`
- App running in tmux session: `aiprls`
- Public demo via ngrok in tmux session: `ngrok-aiprls`
- End-to-end tests verified through public URL (login, quiz, answer/coaching, progress)

### Documentation
- README with local setup (conda/venv), mock mode, configuration, project layout
- Two example companion docs (`00_nbcot_exam_structure.md`, `01_chapter_map_certification.md`)

---

## Gaps and next steps

### High priority (before student pilot)

1. **Connect real LLM** — Start vLLM with `scripts/start_llm.sh` on GPU hardware; run app without mock mode.
2. **Expand companion docs** — Team adds chapter maps and NBCOT/ACOTE crosswalks for 2–3 chosen chapters; rebuild index.
3. **Kickoff decisions** — Which chapters, outcome measures, pilot duration, study ID administration (see plan §8).
4. **Stable public URL** — Coordinate with server admin for persistent ngrok domain or reverse proxy.

### Medium priority (pilot support)

5. **Baseline / end instruments** — Pre/post quizzes and surveys (may live outside the chat app per IRB).
6. **Faculty review process** — How AI-generated questions are checked before or during pilot.
7. **README server deploy section** — Document tmux + ngrok setup on craft-1.

### Out of scope for Version 1 (per simple plan)

- Study plan builder (Activity C)
- Timed test-taking strategy coaching (Activity D)
- Dedicated Study Planner agent

---

## Test results (demo link)

Verified on public URL:

| Test | Result |
|------|--------|
| Frontend loads | Pass |
| Login + consent | Pass |
| Chat / small talk | Pass |
| Quiz → question card | Pass |
| Answer → coaching + verdict | Pass |
| Progress view | Pass |
| No answer leak to client | Pass |

---

## Server setup reference

```bash
# SSH
ssh atharv-ngrok

# App (tmux session: aiprls)
cd /home/atharv/AI-PRLS
. .venv/bin/activate
AIPRLS_MOCK_LLM=1 python3 app.py

# Public link (tmux session: ngrok-aiprls)
NGROK_CONFIG=/home/atharv/.config/ngrok/ngrok.yml /usr/local/bin/ngrok http 8000

# Reattach to check on running sessions
tmux attach -t aiprls
tmux attach -t ngrok-aiprls

# Detach without stopping: Ctrl+b, then d
```

---

## References

- Prototype Plan v1 (team discussion draft, July 2026)
- AI-PRLS Simple Plan (Version 1 scope)
- Repository README: `README.md`

---

*Research prototype for the AI-PRLS Educational Design Research project. Not for clinical use.*
