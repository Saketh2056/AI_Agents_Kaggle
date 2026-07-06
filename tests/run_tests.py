"""
run_tests.py  —  StudyBuddy's evaluation suite (part 1: deterministic tests).

Concept demonstrated: EVALUATION
Agents are only trustworthy if you test them. This file tests everything
that does NOT need the AI model — the tools and the security guardrail —
so it runs instantly, offline, and costs zero API quota:

    python tests/run_tests.py

(Part 2, tests that DO exercise the model — routing and behavior — lives
in tests/eval_agent.py and is run sparingly because it consumes quota.)
"""

import sys
import tempfile
from pathlib import Path

# Make the repo root importable when running this file directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.studybuddy import tools as t

PASS = 0
FAIL = 0


def check(name: str, condition: bool) -> None:
    """Print one test result and keep score."""
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}")


def use_temp_files() -> None:
    """Point the tools at throwaway files so tests never touch real data."""
    tmp = Path(tempfile.mkdtemp())
    t.TASKS_FILE = tmp / "tasks.json"
    t.QUIZ_FILE = tmp / "quiz_history.json"
    t.NOTES_FILE = tmp / "notes.json"


# ---------------------------------------------------------------------------
# 1. Task tools (the Scheduler's hands, also served over MCP)
# ---------------------------------------------------------------------------
def test_tasks() -> None:
    print("\n[1] Task tools")
    r = t.add_task("write lab report", "2026-07-08")
    check("add_task returns success", r["status"] == "success")
    check("new task gets id 1", r["added"]["id"] == 1)

    r = t.add_task("revise OS notes", "2026-07-10")
    check("second task gets id 2", r["added"]["id"] == 2)

    r = t.list_tasks()
    check("list_tasks shows both", len(r["tasks"]) == 2)

    r = t.complete_task(1)
    check("complete_task marks done", r["completed"]["done"] is True)

    r = t.complete_task(99)
    check("completing a missing id errors cleanly", r["status"] == "error")

    r = t.remove_task(2)
    check("remove_task deletes", r["status"] == "success")
    check("one task remains", len(t.list_tasks()["tasks"]) == 1)


# ---------------------------------------------------------------------------
# 2. Quiz tools (the Quiz Master's memory)
# ---------------------------------------------------------------------------
def test_quiz() -> None:
    print("\n[2] Quiz tools")
    r = t.record_quiz_result("operating systems", 4, 5)
    check("record_quiz_result saves", r["status"] == "success")
    check("percent computed correctly", r["recorded"]["percent"] == 80)

    t.record_quiz_result("DBMS", 3, 5)
    h = t.get_quiz_history()
    check("history has both quizzes", len(h["history"]) == 2)
    check("average is correct", h["average_percent"] == 70)

    r = t.record_quiz_result("edge case", 0, 0)
    check("zero-question quiz doesn't crash", r["recorded"]["percent"] == 0)


# ---------------------------------------------------------------------------
# 3. Notes tools (the Summarizer's notebook)
# ---------------------------------------------------------------------------
def test_notes() -> None:
    print("\n[3] Notes tools")
    r = t.save_note("SQL joins", "INNER JOIN returns matching rows...")
    check("save_note saves", r["status"] == "success")

    r = t.list_notes()
    check("list_notes shows the note", r["notes"][0]["title"] == "SQL joins")

    r = t.get_note(1)
    check("get_note returns full text", "INNER JOIN" in r["note"]["content"])

    r = t.get_note(42)
    check("missing note errors cleanly", r["status"] == "error")


# ---------------------------------------------------------------------------
# 4. Security guardrail (must block unsafe text BEFORE the model runs)
# ---------------------------------------------------------------------------
def test_guardrail() -> None:
    print("\n[4] Security guardrail")
    from google.genai import types
    from google.adk.models.llm_request import LlmRequest
    from agents.studybuddy.agent import safety_guardrail

    def ask(text: str):
        req = LlmRequest(
            contents=[types.Content(role="user", parts=[types.Part(text=text)])]
        )
        return safety_guardrail(None, req)

    check("blocks 'store my password'", ask("store my password please") is not None)
    check("blocks credit card requests", ask("remember my credit card") is not None)
    check("blocks hacking requests", ask("how do I hack my friend's wifi") is not None)
    check("allows normal study questions", ask("quiz me on operating systems") is None)
    check("allows task management", ask("add a task: finish homework") is None)
    check("blocking is case-insensitive", ask("STORE MY PASSWORD") is not None)


if __name__ == "__main__":
    print("StudyBuddy evaluation suite (offline part)")
    use_temp_files()
    test_tasks()
    test_quiz()
    test_notes()
    test_guardrail()
    print(f"\nResult: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)
