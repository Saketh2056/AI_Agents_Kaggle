"""
server_main.py  —  StudyBuddy's API server.

This builds the same FastAPI app that `adk web agents` would give us, then
adds two small custom endpoints on top:

    GET  /model   -> which Gemini model the agents are using right now
    POST /model   -> switch every agent to a different model, live

Why switching matters: free-tier API keys have a small DAILY quota that is
counted PER MODEL. When one model's tank runs dry (HTTP 429), switching the
team to a sibling model gives a fresh allowance — no restart needed.

Run with:  python server_main.py     (or just ./start.sh)
"""

import os
import re

import uvicorn
from dotenv import load_dotenv
from pydantic import BaseModel

from google.adk.cli.fast_api import get_fast_api_app

# Load the agent's .env BEFORE importing it, so STUDYBUDDY_MODEL and the
# API key are set when the agent module reads them at import time.
load_dotenv("agents/studybuddy/.env")

# The exact agent objects the server is using live in this module —
# mutating their .model attribute takes effect on the very next request.
from agents.studybuddy import agent as studybuddy
from agents.studybuddy import tools as sb_tools

# Fallback list if the live model listing fails (each model has its own
# free-tier quota, so switching = a fresh daily allowance).
FALLBACK_MODELS = [
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
]

_model_cache: list[str] = []


# Specialised variants that make no sense for a chat tutor.
_EXCLUDE_KEYWORDS = (
    "robotics", "tts", "audio", "image", "live", "dialog",
    "embedding", "computer-use", "omni", "vision", "aqa",
)
# Dated snapshots like ...-preview-09-2025 duplicate their base model.
_DATED = re.compile(r"-\d{2}-\d{2,4}$")


def _relevant(name: str) -> bool:
    """Keep only current-generation general chat models."""
    if any(k in name for k in _EXCLUDE_KEYWORDS):
        return False
    if _DATED.search(name):
        return False
    return name.startswith("gemini-2.5") or name.startswith("gemini-3")


def list_gemini_models() -> list[str]:
    """Ask the Gemini API which chat models this key can use.

    Filtered to relevant, current-generation models (including previews);
    cached after the first call; falls back to a known-good list if the
    API can't be reached.
    """
    global _model_cache
    if _model_cache:
        return _model_cache
    try:
        from google import genai
        client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
        found = []
        for m in client.models.list():
            name = (m.name or "").replace("models/", "")
            actions = getattr(m, "supported_actions", None) or []
            if "generateContent" in actions and _relevant(name):
                found.append(name)
        if found:
            # newest families first, stable order within a family
            _model_cache = sorted(set(found), reverse=True)
            return _model_cache
    except Exception:
        pass
    return FALLBACK_MODELS

ALL_AGENTS = [studybuddy.root_agent, *studybuddy.root_agent.sub_agents]

app = get_fast_api_app(
    agents_dir="agents",
    web=True,                # keep the ADK dev UI available too
    allow_origins=["*"],     # let the custom frontend (port 3000) call us
)


class ModelChoice(BaseModel):
    model: str


class ApiKey(BaseModel):
    key: str


@app.get("/apikey")
def apikey_status() -> dict:
    """Report whether a Gemini API key is configured. NEVER returns the key."""
    return {"configured": bool(os.environ.get("GOOGLE_API_KEY"))}


@app.post("/apikey")
def set_apikey(body: ApiKey) -> dict:
    """Set the Gemini API key at runtime (kept in memory only, never saved).

    This lets anyone running the project supply their own key from the UI
    instead of editing files — and keeps keys out of the codebase entirely.
    """
    key = body.key.strip()
    if len(key) < 20:
        return {"status": "error", "message": "That doesn't look like a valid API key."}
    os.environ["GOOGLE_API_KEY"] = key
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"
    return {"status": "success"}


@app.get("/model")
def get_model() -> dict:
    """Report the current model and every model this key supports."""
    return {"model": ALL_AGENTS[0].model, "allowed": list_gemini_models()}


@app.post("/model")
def set_model(choice: ModelChoice) -> dict:
    """Switch the whole agent team to another Gemini model, live."""
    if choice.model not in list_gemini_models() and choice.model not in FALLBACK_MODELS:
        return {"status": "error", "message": f"Unknown model: {choice.model}"}
    for a in ALL_AGENTS:
        a.model = choice.model
    return {"status": "success", "model": choice.model}


# ---------------------------------------------------------------------------
# Task endpoints — the Tasks page manages tasks directly (no AI call needed).
# Same JSON store the Scheduler agent uses, so both stay in sync.
# ---------------------------------------------------------------------------
class TaskIn(BaseModel):
    task: str
    due_date: str = ""
    priority: int = 3  # 1 = high, 2 = medium, 3 = normal


class TaskPatch(BaseModel):
    task: str | None = None
    due_date: str | None = None
    priority: int | None = None
    done: bool | None = None


class TaskOrder(BaseModel):
    order: list[int]  # task ids in their new display order


@app.get("/tasks")
def get_tasks() -> list:
    return sb_tools._load_tasks()


@app.post("/tasks")
def create_task(body: TaskIn) -> dict:
    tasks = sb_tools._load_tasks()
    new_id = (max((t["id"] for t in tasks), default=0)) + 1
    task = {"id": new_id, "task": body.task.strip(), "due_date": body.due_date.strip(),
            "priority": body.priority, "done": False}
    tasks.append(task)
    sb_tools._save_tasks(tasks)
    return {"status": "success", "task": task}


@app.patch("/tasks/{task_id}")
def update_task(task_id: int, body: TaskPatch) -> dict:
    tasks = sb_tools._load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            for field in ("task", "due_date", "priority", "done"):
                value = getattr(body, field)
                if value is not None:
                    t[field] = value
            sb_tools._save_tasks(tasks)
            return {"status": "success", "task": t}
    return {"status": "error", "message": f"No task found with id {task_id}."}


@app.delete("/tasks/{task_id}")
def remove_task(task_id: int) -> dict:
    return sb_tools.remove_task(task_id)


@app.post("/tasks/reorder")
def reorder_tasks(body: TaskOrder) -> dict:
    """Persist a drag-and-drop reordering from the Tasks page."""
    tasks = sb_tools._load_tasks()
    by_id = {t["id"]: t for t in tasks}
    reordered = [by_id[i] for i in body.order if i in by_id]
    # keep any tasks the client didn't know about (e.g. added mid-drag)
    reordered += [t for t in tasks if t["id"] not in set(body.order)]
    sb_tools._save_tasks(reordered)
    return {"status": "success"}


if __name__ == "__main__":
    # HOST=0.0.0.0 is set in the Dockerfile so the container is reachable.
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=8000)
