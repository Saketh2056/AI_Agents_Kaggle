"""
tools.py  —  The "hands" of StudyBuddy.

An AI agent's brain (the language model) can only *think* and *talk*.
To actually DO things, it calls "tools" — plain Python functions like the ones
below. StudyBuddy uses these to remember things in small files on disk.

Concept demonstrated: TOOL CALLING + MEMORY
Three memory files, all persistent across restarts:
  tasks.json        -> the to-do list (Scheduler's memory)
  quiz_history.json -> every quiz taken, with scores (Quiz Master's memory)
  notes.json        -> saved revision notes (Summarizer's memory)
"""

import json
from datetime import date
from pathlib import Path

# The files where we store memory. They sit next to this code file.
TASKS_FILE = Path(__file__).parent / "tasks.json"
QUIZ_FILE = Path(__file__).parent / "quiz_history.json"
NOTES_FILE = Path(__file__).parent / "notes.json"


def _load_tasks() -> list[dict]:
    """Read the saved tasks from disk. Returns an empty list if none exist yet."""
    if TASKS_FILE.exists():
        return json.loads(TASKS_FILE.read_text())
    return []


def _save_tasks(tasks: list[dict]) -> None:
    """Write the tasks back to disk so they are remembered next time."""
    TASKS_FILE.write_text(json.dumps(tasks, indent=2))


def add_task(task: str, due_date: str) -> dict:
    """Add a new study task or assignment to the to-do list.

    Args:
        task: A short description of the task, e.g. "Finish math homework".
        due_date: When it is due, e.g. "2026-07-10" or "next Friday".

    Returns:
        A dictionary confirming the task that was added, including its new id.
    """
    tasks = _load_tasks()
    # Give each task a simple numeric id: 1, 2, 3, ...
    new_id = (max((t["id"] for t in tasks), default=0)) + 1
    # priority: 1 = high, 2 = medium, 3 = normal (editable on the Tasks page)
    new_task = {"id": new_id, "task": task, "due_date": due_date,
                "priority": 3, "done": False}
    tasks.append(new_task)
    _save_tasks(tasks)
    return {"status": "success", "added": new_task}


def list_tasks() -> dict:
    """List all study tasks that have been saved, both done and not done.

    Returns:
        A dictionary containing the full list of tasks.
    """
    tasks = _load_tasks()
    if not tasks:
        return {"status": "success", "tasks": [], "message": "You have no tasks yet."}
    return {"status": "success", "tasks": tasks}


def complete_task(task_id: int) -> dict:
    """Mark a task as finished (done).

    Args:
        task_id: The id number of the task to mark complete (see list_tasks).

    Returns:
        A dictionary confirming the change, or an error if the id was not found.
    """
    tasks = _load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            t["done"] = True
            _save_tasks(tasks)
            return {"status": "success", "completed": t}
    return {"status": "error", "message": f"No task found with id {task_id}."}


def remove_task(task_id: int) -> dict:
    """Delete a task from the list entirely.

    Args:
        task_id: The id number of the task to delete (see list_tasks).

    Returns:
        A dictionary confirming the deletion, or an error if the id was not found.
    """
    tasks = _load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            tasks.remove(t)
            _save_tasks(tasks)
            return {"status": "success", "removed": t}
    return {"status": "error", "message": f"No task found with id {task_id}."}


# ---------------------------------------------------------------------------
# QUIZ MASTER's tools — remember every quiz so progress is visible over time
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> list[dict]:
    """Read a JSON list from disk, or an empty list if the file doesn't exist."""
    if path.exists():
        return json.loads(path.read_text())
    return []


def record_quiz_result(topic: str, score: int, total: int) -> dict:
    """Save the result of a finished quiz so progress can be tracked over time.

    Args:
        topic: What the quiz was about, e.g. "operating systems".
        score: How many questions the student answered correctly.
        total: How many questions the quiz had.

    Returns:
        A confirmation with the stored record.
    """
    history = _load_json(QUIZ_FILE)
    record = {
        "topic": topic,
        "score": score,
        "total": total,
        "percent": round(100 * score / max(total, 1)),
        "date": date.today().isoformat(),
    }
    history.append(record)
    QUIZ_FILE.write_text(json.dumps(history, indent=2))
    return {"status": "success", "recorded": record}


def get_quiz_history() -> dict:
    """Show all past quiz results and the overall average score.

    Returns:
        Every stored quiz result plus an average percentage across them.
    """
    history = _load_json(QUIZ_FILE)
    if not history:
        return {"status": "success", "history": [], "message": "No quizzes taken yet."}
    avg = round(sum(h["percent"] for h in history) / len(history))
    return {"status": "success", "history": history, "average_percent": avg}


# ---------------------------------------------------------------------------
# SUMMARIZER's tools — a personal notebook of saved revision notes
# ---------------------------------------------------------------------------

def save_note(title: str, content: str) -> dict:
    """Save a revision note (e.g. a summary just written) to the notebook.

    Args:
        title: A short name for the note, e.g. "SQL joins".
        content: The full text of the note in markdown.

    Returns:
        A confirmation with the new note's id.
    """
    notes = _load_json(NOTES_FILE)
    new_id = (max((n["id"] for n in notes), default=0)) + 1
    note = {"id": new_id, "title": title, "content": content, "date": date.today().isoformat()}
    notes.append(note)
    NOTES_FILE.write_text(json.dumps(notes, indent=2))
    return {"status": "success", "saved": {"id": new_id, "title": title}}


def list_notes() -> dict:
    """List the titles of all saved revision notes.

    Returns:
        The id, title and date of every saved note (not the full text).
    """
    notes = _load_json(NOTES_FILE)
    if not notes:
        return {"status": "success", "notes": [], "message": "No notes saved yet."}
    return {
        "status": "success",
        "notes": [{"id": n["id"], "title": n["title"], "date": n["date"]} for n in notes],
    }


def get_note(note_id: int) -> dict:
    """Fetch the full text of one saved note by its id.

    Args:
        note_id: The id of the note to read (see list_notes).

    Returns:
        The complete note, or an error if the id was not found.
    """
    notes = _load_json(NOTES_FILE)
    for n in notes:
        if n["id"] == note_id:
            return {"status": "success", "note": n}
    return {"status": "error", "message": f"No note found with id {note_id}."}
