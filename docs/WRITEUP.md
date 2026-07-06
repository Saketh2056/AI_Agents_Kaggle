# KAGGLE WRITEUP — paste into kaggle.com "New Writeup"
# Title:    StudyBuddy — a multi-agent AI study concierge
# Subtitle: Six cooperating ADK agents that plan, quiz, tutor and organize a
#           student's studying — with MCP tools, guardrails on every agent,
#           and zero secrets in the code.
# Track:    Concierge Agents
# (~1,400 words — under the 2,500 limit)
# ---------------------------------------------------------------------------

## The problem

Ask any engineering student how they study and you'll hear the same four-app
story: a to-do list for deadlines, a notes app for revision, a quiz website
for practice, and an AI chatbot for questions. None of these tools talk to
each other. None of them remember what you studied last week or how you scored
on your last practice test. And the chatbot has a darker flaw: ask it your
homework question and it will happily hand you the finished answer — great for
tonight's deadline, terrible for actually learning.

I wanted one assistant that closes the whole study loop — **plan → do →
revise → test → track** — and that treats *teaching* as different from
*answering*. And because a study assistant inevitably holds personal
information (what you're studying, where you're falling behind, your
deadlines), it had to be built like a proper concierge: safe by default, with
personal data that never leaves your machine.

## Why agents?

A single prompt can't hold all of these jobs at once. A planner should think
in steps and dates; a quiz master should withhold answers until you commit to
one; a tutor should refuse to reveal solutions; a scheduler needs write-access
to your task list. Those are *different personas with different privileges* —
exactly what a multi-agent system expresses naturally. Splitting the work also
enforces least privilege: only the Scheduler can touch tasks, only the
Summarizer can write to the notebook, and the Tutor has no tools at all — it
can only teach.

## The solution

StudyBuddy is a team of **six agents** built on **Google's Agent Development
Kit (ADK)**, running behind a clean web workspace:

- **Coordinator** — the front desk. Reads every message and delegates using
  ADK's LLM-driven `transfer_to_agent`. It is explicitly instructed never to
  solve homework itself.
- **Planner** — breaks assignments into steps; `/plan topics by date` builds a
  backward day-by-day study checklist from an exam date.
- **Scheduler** — the only agent with task-write powers: add, list, complete,
  remove — with every tool call travelling over **MCP** (more below).
- **Quiz Master** — `/quiz <topic>` runs an interactive quiz, one question at
  a time. Wrong answers get *precision error diagnosis* ("you confused a
  deadlock with a livelock — these processes are still running"), and every
  final score is persisted to a quiz history.
- **Summarizer** — turns pasted notes, uploaded files, or topics into revision
  notes, `/flashcards`, and `/vocab` term tables, and saves them to a personal
  notebook.
- **Tutor** — the pedagogy specialist: Socratic scaffolding (one guiding
  question at a time, never the final answer up front), ELI5 analogies on
  request, and a role-reversal **Feynman mode** where the student teaches and
  the agent plays a curious beginner probing for gaps.

Three JSON memory stores (`tasks.json`, `quiz_history.json`, `notes.json`)
persist across restarts, so the assistant genuinely *remembers* — your task
list, your notebook, and your quiz average survive a reboot.

## Architecture

Browser → FastAPI server → Coordinator → five specialists → tools → memory:

- The **frontend** is a single-file web app (Tailwind, no build step) with a
  dashboard, a chat stream that visibly shows agent hand-offs, and a live
  "Study Vault" panel that re-renders tasks, scores and notes as the agents
  change them.
- The **server** (`server_main.py`) is ADK's FastAPI app extended with two
  custom endpoints: `POST /model` hot-swaps the whole team between four Gemini
  models at runtime, and `POST /apikey` lets anyone supply their own key from
  the UI — the key lives in process memory only.
- The **MCP server** (`mcp_server/server.py`, FastMCP over stdio) serves the
  four task tools. The Scheduler consumes them through ADK's `MCPToolset`,
  which launches the server as a subprocess and discovers its tools over the
  open protocol — the same server would plug into Claude Desktop or
  Antigravity unchanged. This was a deliberate design statement: tools as a
  *service*, not as private imports.

## Security & guardrails

Concierge agents hold personal data, so safety is a first-class feature:

1. **A guardrail on every agent, not just the front door.** ADK's
   `before_model_callback` runs a safety check before each model call. After a
   hand-off the student talks directly to the sub-agent, so the same guardrail
   is attached to all six — defense in depth. It blocks password/credit-card
   storage and harmful requests *before* any tokens are spent, returning a
   polite refusal.
2. **No secrets in the repo, ever.** The API key arrives either from a
   git-ignored `.env` or from the launch dialog at runtime; an automated sweep
   confirms no key material in any committed file.
3. **Personal data stays local** — the memory stores are git-ignored and
   docker-ignored.
4. **Scope as a safety property**: no browsing, no accounts, no background
   actions. A personal agent should have a small blast radius.

## Evaluation

Two-part test suite. `tests/run_tests.py` runs **23 deterministic tests**
covering every tool (task lifecycle, quiz math edge cases like zero-question
quizzes, notebook round-trips) and the guardrail (blocks the bad, passes the
good, case-insensitive) — offline, in milliseconds, costing zero quota.
`tests/eval_agent.py` exercises the live system end-to-end: scripted messages
asserting that task requests route to the Scheduler and fire `add_task`, that
planning reaches the Planner, quizzing reaches the Quiz Master, and that an
unsafe request is refused with no tool touched.

## The journey (what I'd tell another student)

The hardest engineering wasn't the agents — it was **operating on the free
tier**. Free Gemini keys have small per-model daily quotas, and a multi-agent
system burns 2–3 model calls per user message (the router thinks, then the
specialist thinks). I hit 429s mid-build and treated it as a design input
instead of bad luck: the model became a config value, then a live-switchable
server endpoint, and the UI grew honest failure states — automatic retries on
transient 503s, an amber "limit reached — switch model" status, and a plain-
language explanation instead of a silent error. Production agents need to
fail gracefully; the free tier just made me practice that early.

The second lesson was **guardrail placement**. My first guardrail sat only on
the coordinator — but after a transfer, messages flow straight to the
sub-agent, bypassing it. Realizing this and attaching the callback to every
agent was a one-line loop and a big conceptual click about how delegation
actually works in ADK.

## Limits and next steps

StudyBuddy is deliberately narrow: no calendar integration, no accounts, one
user. Next steps would be ADK's persistent session service for long-term
conversational memory, a session-aware eval harness scoring tutoring quality
(does the Tutor *never* leak answers?), and deploying the container to Cloud
Run / Agent Engine.

## Build notes

Built solo with Python 3.14, google-adk 2.3, FastMCP, Gemini (2.5/3 flash
family), and a vibe-coding workflow with an AI pair assistant. All code, setup
instructions, tests, and the Dockerfile are in the repo linked on this page.

# ---------------------------------------------------------------------------
# ATTACH BEFORE SUBMITTING:
#   1. Cover image  (screenshot of the dashboard — see VIDEO_SCRIPT.md)
#   2. YouTube video (≤5 min)
#   3. Project link  (your public GitHub repo URL)
# Select track: Concierge Agents  →  Save  →  SUBMIT (not draft!)
# ---------------------------------------------------------------------------
