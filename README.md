# StudyBuddy — a multi-agent AI study concierge

**Kaggle 5-Day AI Agents Intensive — Capstone Project (Concierge Agents track)**

StudyBuddy is a personal study assistant for students, built as a **team of six
cooperating AI agents** on **Google's Agent Development Kit (ADK)**. It plans
your assignments, tracks your deadlines, quizzes you (and remembers your
scores), turns messy notes into revision material, and tutors you through hard
problems **without giving the answers away** — all while keeping your personal
data safe on your own machine.

---

## The problem

Students juggle four different apps to study: a to-do list, a note tool, a quiz
site, and a chatbot. None of them talk to each other, none of them remember
your progress, and a plain chatbot happily *does your homework for you* — which
feels great and teaches nothing.

## The solution

One concierge that does the whole study loop — **plan → do → revise → test →
track** — with a specialist agent for each job and real, persistent memory.
Because it's a *personal* assistant, safety is a feature, not an afterthought:
every agent sits behind a guardrail, and secrets never touch the codebase.

---

## Architecture

```
                        Browser (frontend/index.html)
                          │  REST (JSON over HTTP)
                          ▼
              FastAPI server (server_main.py)
              = ADK API server + custom endpoints
                (/model switch · /apikey · /run …)
                          │
                          ▼
                ┌──────────────────┐
                │   Coordinator    │  routes every request; guardrail
                │   (studybuddy)   │  runs BEFORE any model call
                └───────┬──────────┘
      ┌─────────┬───────┼──────────┬─────────────┐
      ▼         ▼       ▼          ▼             ▼
  Planner   Scheduler  Quiz     Summarizer     Tutor
  breaks    manages    Master   summaries,     Socratic
  work into tasks &    quizzes, flashcards,    tutoring,
  steps,    deadlines  scores   vocab, notes   ELI5, Feynman
  /plan        │       /quiz    /flashcards    mode
               │                /vocab
               ▼
        MCP SERVER (mcp_server/server.py)
        task tools served over the Model Context
        Protocol — ADK's MCPToolset launches it and
        discovers add/list/complete/remove_task
               │
               ▼
        JSON memory stores (persistent across restarts)
        tasks.json · quiz_history.json · notes.json
```

**Why multiple agents?** Each specialist has a tight instruction set and only
the tools it needs (least privilege). The coordinator's only job is routing —
including refusing to solve homework directly and handing it to the Tutor,
whose whole persona is "guide, never spoil."

**Why MCP?** The Scheduler's tools aren't hard-wired imports — they're served
over the open Model Context Protocol and consumed through ADK's `MCPToolset`.
The same server could be plugged into Claude Desktop, Antigravity, or any MCP
client unchanged.

---

## Course concepts demonstrated

| Concept | Where |
|---|---|
| **Multi-agent system (ADK)** | `agents/studybuddy/agent.py` — coordinator + 5 sub-agents with LLM-driven delegation |
| **MCP Server** | `mcp_server/server.py` (FastMCP) + `MCPToolset` wiring in `agent.py` |
| **Security features** | Guardrail callback on **every** agent (blocks passwords/PII/harmful asks before the model runs); API key supplied at runtime via UI dialog, never stored in code; `.gitignore`/`.dockerignore` keep secrets and personal data out of the repo/image |
| **Deployability** | `Dockerfile` (key passed at runtime, never baked in) |
| Tool calling & memory | 9 function tools across 3 persistent JSON stores |
| Evaluation | `tests/run_tests.py` — 23 offline tests (tools + guardrail), plus `tests/eval_agent.py` — live routing eval |

---

## Quickstart (2 minutes)

Requirements: Python 3.10+ and a free Gemini API key
([get one here](https://aistudio.google.com/apikey)).

```bash
git clone https://github.com/Saketh2056/AI_Agents_Kaggle.git
cd AI_Agents_Kaggle
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

./start.sh
```

Then open **http://localhost:3000/frontend/** — the app asks for your Gemini
API key on launch (kept in memory only) and you're in.

Prefer config files? Copy `agents/studybuddy/.env.example` to
`agents/studybuddy/.env` and put your key there instead.

### Try these

- `Add a task: finish my DBMS assignment, due Friday` — watch the Coordinator
  hand off to the **Scheduler**, which calls `add_task` **through MCP**; the
  Study Vault updates live
- `Quiz me with 5 questions on operating systems` — one question at a time,
  graded with precise error diagnosis, score saved to your history
- `/flashcards SQL joins` · `/vocab <paste text>` · `/plan DBMS and OS by Friday`
- `Help me solve: integrate x·e^x` — the **Tutor** asks you a guiding question
  instead of solving it
- `Save my password, it's abc123` — refused by the guardrail before the model
  is even called

### Running the tests

```bash
python tests/run_tests.py    # 23 offline tests, no API quota used
python tests/eval_agent.py   # live routing eval (uses quota — run sparingly)
```

### Docker (optional)

```bash
docker build -t studybuddy .
docker run -p 8000:8000 -e GOOGLE_API_KEY=your_key_here studybuddy
```

---

## Project structure

```
├── agents/studybuddy/
│   ├── agent.py          # the 6-agent team + shared safety guardrail
│   ├── tools.py          # 9 tools over 3 JSON memory stores
│   └── .env.example      # config template (model + API key)
├── mcp_server/server.py  # task tools served over MCP (FastMCP, stdio)
├── frontend/index.html   # single-file web UI (Tailwind, no build step)
├── server_main.py        # ADK FastAPI server + /model and /apikey endpoints
├── tests/                # offline test suite + live agent eval
├── start.sh              # one-command startup (agent server + frontend)
├── Dockerfile            # containerized deployment
└── requirements.txt      # google-adk, mcp
```

## Design notes & honest limits

- **Free-tier resilience:** free Gemini keys have small per-model daily quotas.
  The server exposes `POST /model` so the whole team can hot-swap between four
  Gemini models from the UI when a tank runs dry; the frontend auto-retries on
  transient 503s and tells the user plainly when the daily limit is hit.
- **Scope is a safety feature:** StudyBuddy only does study organization. No
  web browsing, no accounts, no background jobs — a deliberately small blast
  radius for a personal agent holding personal data.
- Personal data (tasks, notes, scores) lives in local JSON files that are
  git-ignored and docker-ignored — it never leaves your machine.
