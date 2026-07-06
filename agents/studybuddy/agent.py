"""
agent.py  —  The "brain(s)" of StudyBuddy.

This file builds a MULTI-AGENT system using Google's Agent Development Kit (ADK).
Instead of one giant agent that does everything, we use a small TEAM of agents,
each with one job. A "coordinator" agent reads what you ask and hands the work
to the right teammate:

    StudyBuddy (coordinator)
        ├── Planner    -> breaks big assignments into small steps; /plan
        ├── Scheduler  -> saves / lists / completes / removes tasks (uses tools)
        ├── Quiz Master-> runs interactive quizzes and records scores; /quiz
        ├── Summarizer -> revision notes, /flashcards, /vocab (uses tools)
        └── Tutor      -> Socratic tutoring, error diagnosis, ELI5, Feynman mode

Concepts demonstrated:
  1. MULTI-AGENT SYSTEM (ADK)  -> the coordinator + four sub-agents below
  2. TOOL CALLING              -> Scheduler, Quiz Master and Summarizer use tools.py
  3. MEMORY                    -> tasks.json, quiz_history.json, notes.json
  4. SECURITY / GUARDRAILS     -> a safety gate enforced on EVERY agent
"""

import os
import sys
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams
from google.genai import types
from mcp import StdioServerParameters

from .tools import (
    record_quiz_result, get_quiz_history,
    save_note, list_notes, get_note,
)

# Path to our MCP server script (see mcp_server/server.py for what MCP is).
MCP_SERVER = Path(__file__).resolve().parents[2] / "mcp_server" / "server.py"

# Which Gemini model powers the agents' "thinking".
# Configurable via .env (STUDYBUDDY_MODEL) without touching code — handy
# because free-tier API keys have small per-model daily quotas, and every
# user message triggers several model calls (coordinator + sub-agent).
MODEL = os.getenv("STUDYBUDDY_MODEL", "gemini-2.5-flash")


# ---------------------------------------------------------------------------
# SECURITY / GUARDRAIL
# ---------------------------------------------------------------------------
# A guardrail is a safety gate. This function runs BEFORE the agent's brain is
# asked to respond. If the user's message looks unsafe or off-topic, we stop
# right here and return a polite refusal — the AI model is never even called.
# This is how we keep a personal assistant safe (a core goal of the Concierge
# track): it stays in its lane and refuses harmful requests.
BLOCKED_TOPICS = [
    "password", "credit card", "social security", "hack", "weapon", "bomb",
]


def safety_guardrail(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> LlmResponse | None:
    """Inspect the latest user message and block anything unsafe or sensitive.

    Returning an LlmResponse here short-circuits the agent: the model is skipped
    and our refusal is shown instead. Returning None lets the request proceed
    normally.
    """
    # Grab the text of the most recent user message.
    last_text = ""
    if llm_request.contents:
        for part in llm_request.contents[-1].parts or []:
            if part.text:
                last_text += part.text.lower()

    # If the message mentions a blocked/sensitive topic, refuse politely.
    for word in BLOCKED_TOPICS:
        if word in last_text:
            refusal = (
                "I'm sorry, but I can't help with that. To keep your data safe, "
                "StudyBuddy only helps with study planning and task management, "
                "and never handles passwords or other sensitive personal info."
            )
            return LlmResponse(
                content=types.Content(
                    role="model", parts=[types.Part(text=refusal)]
                )
            )
    # Nothing blocked — let the agent continue as normal.
    return None


# A shared rulebook injected into every agent that works with the student's
# own material. This is what keeps answers grounded instead of hallucinated.
GROUNDING_RULES = (
    "\nGROUNDING RULES: when the student pastes notes or uploads a document, "
    "answer STRICTLY from that material. Quote short snippets to back up "
    "answers (e.g. your notes say: \"...\"). If the material does not cover "
    "something, say so plainly instead of inventing an answer."
)


# ---------------------------------------------------------------------------
# SUB-AGENT 1: THE PLANNER
# ---------------------------------------------------------------------------
# This teammate has no tools. Its only job is to think: take a big, scary
# assignment and break it into a short, ordered list of small steps.
planner_agent = LlmAgent(
    name="planner",
    model=MODEL,
    description="Breaks big assignments into steps and builds backward study plans (/plan).",
    instruction=(
        "You are a study planning expert.\n"
        "- Given an assignment or goal: break it into 3-6 clear, ordered, "
        "bite-sized steps. Keep each step short and actionable.\n"
        "- /plan [topics] by [date] (or any 'exam on <date>' request): work "
        "BACKWARD from the exam date to today. Spread the topics into a "
        "day-by-day checklist — each day gets a date heading and 2-3 small "
        "items. Reserve the final day before the exam for revision and a "
        "self-test. Keep daily loads realistic.\n"
        "Do not manage the to-do list yourself — just produce the plan. "
        "If the request is not planning, transfer back to the coordinator."
    ),
)


# ---------------------------------------------------------------------------
# SUB-AGENT 2: THE SCHEDULER  (tools served over MCP!)
# ---------------------------------------------------------------------------
# This teammate's tools don't come from a direct import — they arrive through
# the Model Context Protocol. ADK's MCPToolset launches our MCP server
# (mcp_server/server.py) as a subprocess and discovers its tools over the
# standard protocol. The same server could be plugged into Claude Desktop,
# Antigravity, or any other MCP client — that's the point of the standard.
scheduler_agent = LlmAgent(
    name="scheduler",
    model=MODEL,
    description="Adds, lists, completes, and removes study tasks and deadlines.",
    instruction=(
        "You manage the student's to-do list. Use your tools to add, list, "
        "complete, or remove tasks. Always confirm what you did in a friendly, "
        "brief way. When showing tasks, present them as a simple readable list."
    ),
    tools=[
        MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    # sys.executable = this venv's python, so the MCP server
                    # runs with the same installed packages as the agent.
                    command=sys.executable,
                    args=[str(MCP_SERVER)],
                ),
            ),
        )
    ],
)


# ---------------------------------------------------------------------------
# SUB-AGENT 3: THE QUIZ MASTER
# ---------------------------------------------------------------------------
# Runs interactive quizzes: one question at a time, waits for the answer,
# grades it, and records the final score so progress builds up over time.
quizmaster_agent = LlmAgent(
    name="quizmaster",
    model=MODEL,
    description="Runs interactive quizzes (/quiz) on any topic or provided notes; records scores.",
    instruction=(
        "You are an encouraging quiz master for a university student.\n"
        "When asked for a quiz (or the student types /quiz [topic or notes]):\n"
        "1. Default to 5 multiple-choice questions A/B/C/D (or the number and "
        "style the student asks for).\n"
        "2. Ask ONE question at a time, numbered, then WAIT for the answer.\n"
        "3. Grade each answer. If WRONG, do precision error diagnosis: name "
        "the exact concept or step the student mixed up (e.g. 'you confused "
        "a deadlock with a livelock — the processes here are still running'), "
        "give the correct answer with a one-line explanation, then continue.\n"
        "4. If the quiz is based on notes or an uploaded document, draw every "
        "question STRICTLY from that material and quote the relevant line "
        "when explaining an answer.\n"
        "5. After the last question, give the final score with a short, "
        "encouraging note on what to revise, and ALWAYS call "
        "record_quiz_result to save the result.\n"
        "If asked about past performance, use get_quiz_history.\n"
        "If the student wants something that is not a quiz, transfer back to "
        "the coordinator."
        + GROUNDING_RULES
    ),
    tools=[record_quiz_result, get_quiz_history],
)


# ---------------------------------------------------------------------------
# SUB-AGENT 4: THE SUMMARIZER
# ---------------------------------------------------------------------------
# Turns pasted lecture notes (or any topic) into clean revision notes, and can
# save them to a personal notebook (notes.json) for later revision.
summarizer_agent = LlmAgent(
    name="summarizer",
    model=MODEL,
    description=(
        "Summarizes notes or topics into revision notes, flashcards "
        "(/flashcards) and vocab tables (/vocab); saves notes."
    ),
    instruction=(
        "You turn study material into excellent revision aids.\n"
        "- Summaries: short bullet points with key terms in **bold**, plus "
        "definitions worth memorizing. Works from pasted text, an uploaded "
        "file, or a named topic.\n"
        "- /flashcards [topic or notes]: produce 5-10 flashcards as a "
        "numbered list, each formatted exactly as:\n"
        "  **Q:** question\n"
        "  **A:** answer\n"
        "- /vocab [text or topic]: extract the key terms and return ONLY a "
        "markdown table with columns | Term | Plain-English Definition | "
        "Example | — one row per term, no extra prose before the table.\n"
        "- End every summary or study aid by offering to save it; if the "
        "student agrees (or asked upfront), call save_note with a short title.\n"
        "- Use list_notes and get_note when the student wants their saved notes.\n"
        "If the request is not about summaries, flashcards, vocab, or notes, "
        "transfer back to the coordinator."
        + GROUNDING_RULES
    ),
    tools=[save_note, list_notes, get_note],
)


# ---------------------------------------------------------------------------
# SUB-AGENT 5: THE TUTOR
# ---------------------------------------------------------------------------
# The teaching specialist. No tools — pure pedagogy. Four behaviors:
# Socratic scaffolding, precision error diagnosis, ELI5 analogies, and
# Feynman mode (the student teaches, the tutor plays curious beginner).
tutor_agent = LlmAgent(
    name="tutor",
    model=MODEL,
    description=(
        "Patient tutor: guides through problems step by step (never just "
        "gives answers), diagnoses mistakes, explains simply, Feynman mode."
    ),
    instruction=(
        "You are a patient, warm tutor. Four core behaviors:\n"
        "1. SOCRATIC SCAFFOLDING — for homework, math, or any complex "
        "problem, NEVER hand over the final answer up front. Break the "
        "solution into steps and ask ONE guiding question at a time, then "
        "WAIT for the student's reply before continuing. Only reveal a full "
        "solution if the student has genuinely tried and explicitly asks.\n"
        "2. PRECISION ERROR DIAGNOSIS — when the student gets something "
        "wrong, never just say 'incorrect'. Isolate the EXACT step or "
        "concept where their logic broke (e.g. 'everything was right until "
        "you moved -3x across the equals sign — the sign has to flip'), "
        "then guide them from that point.\n"
        "3. ELI5 MODE — if the student asks you to simplify, or seems stuck "
        "or frustrated, drop ALL jargon and re-explain using one relatable "
        "everyday analogy, then bridge back to the technical terms.\n"
        "4. FEYNMAN MODE — if the student wants to practice explaining "
        "(says 'Feynman mode', 'let me teach you', 'can I explain it to "
        "you'), flip roles: you are now a curious beginner who knows "
        "nothing. Ask them to teach you the concept. Ask gentle follow-up "
        "questions that probe for gaps ('wait — why does that happen?'). "
        "At the end, tell them what they explained well and where their "
        "explanation got fuzzy.\n"
        "If the request is about tasks, schedules, quizzes, or making notes, "
        "transfer back to the coordinator."
        + GROUNDING_RULES
    ),
)


# ---------------------------------------------------------------------------
# THE COORDINATOR (ROOT AGENT)
# ---------------------------------------------------------------------------
# This is the "front desk" the student talks to. It reads each message and
# decides which teammate should handle it, then hands off (delegates) to them.
# ADK looks for a variable named exactly `root_agent` to start the app.
root_agent = LlmAgent(
    name="studybuddy",
    model=MODEL,
    description="A friendly personal study assistant for students.",
    instruction=(
        "You are StudyBuddy, a warm and encouraging study assistant. "
        "Greet the student and help them stay organized.\n"
        "ROUTING:\n"
        "- Breaking down / planning an assignment, or /plan -> 'planner'.\n"
        "- Add, view, complete, delete tasks and deadlines -> 'scheduler'.\n"
        "- Quizzes, being tested, /quiz, or quiz scores -> 'quizmaster'.\n"
        "- Summaries, revision notes, /flashcards, /vocab, or managing saved "
        "notes -> 'summarizer'.\n"
        "- Homework help, 'help me solve/understand X', explaining concepts, "
        "'I don't get it', or Feynman mode ('let me teach you') -> 'tutor'. "
        "NEVER solve homework problems yourself — the tutor guides step by "
        "step instead of giving answers away.\n"
        "- Uploaded files (lecture notes, textbook page, PDF, whiteboard "
        "photo): 'summarizer' to digest it — unless they ask to be quizzed "
        "on it ('quizmaster') or taught from it ('tutor').\n"
        "- Simple greetings or small questions: answer directly and kindly.\n"
        "SLASH COMMANDS the student may type: /flashcards, /quiz, /vocab, "
        "/plan — route them as above; the text after the command is the "
        "topic or material.\n"
        "Never ask for or store sensitive personal data like passwords."
    ),
    # The team of sub-agents this coordinator can delegate to:
    sub_agents=[
        planner_agent, scheduler_agent, quizmaster_agent,
        summarizer_agent, tutor_agent,
    ],
    # The safety gate runs before every response from the coordinator:
    before_model_callback=safety_guardrail,
)

# ---------------------------------------------------------------------------
# Enforce the safety gate on EVERY agent, not just the front desk.
# After a handoff, the student talks directly to the sub-agent — so each
# teammate needs the same protection. Defense in depth.
# ---------------------------------------------------------------------------
for _agent in (
    planner_agent, scheduler_agent, quizmaster_agent,
    summarizer_agent, tutor_agent,
):
    _agent.before_model_callback = safety_guardrail
