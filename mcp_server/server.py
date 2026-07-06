"""
server.py  —  StudyBuddy's MCP server.

WHAT IS MCP?
The Model Context Protocol is an open standard — a universal "plug socket"
for AI tools. Instead of wiring tools directly into one agent, you serve
them over MCP, and then ANY MCP-compatible client can use them:
our own StudyBuddy agent, Claude Desktop, Google Antigravity, and so on.

WHAT THIS SERVER DOES
It exposes StudyBuddy's task-management tools (the same functions in
agents/studybuddy/tools.py) over MCP via stdio. Our ADK Scheduler agent
connects to this server through ADK's MCPToolset — so the agent's "hands"
are now reached through a standard protocol instead of a private wire.

Concept demonstrated: MCP SERVER
Run standalone with:  python mcp_server/server.py
(Our agent starts it automatically — see agents/studybuddy/agent.py.)
"""

import sys
from pathlib import Path

# Make the repo root importable so we can reuse the same tool functions
# the agent package defines (single source of truth for task logic).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp.server.fastmcp import FastMCP

from agents.studybuddy import tools as t

# The server announces itself to clients under this name.
mcp = FastMCP("studybuddy-tasks")


@mcp.tool()
def add_task(task: str, due_date: str) -> dict:
    """Add a new study task or assignment to the to-do list.

    Args:
        task: A short description of the task, e.g. "Finish math homework".
        due_date: When it is due, e.g. "2026-07-10" or "next Friday".
    """
    return t.add_task(task, due_date)


@mcp.tool()
def list_tasks() -> dict:
    """List all study tasks that have been saved, both done and not done."""
    return t.list_tasks()


@mcp.tool()
def complete_task(task_id: int) -> dict:
    """Mark a task as finished (done).

    Args:
        task_id: The id number of the task to mark complete (see list_tasks).
    """
    return t.complete_task(task_id)


@mcp.tool()
def remove_task(task_id: int) -> dict:
    """Delete a task from the list entirely.

    Args:
        task_id: The id number of the task to delete (see list_tasks).
    """
    return t.remove_task(task_id)


if __name__ == "__main__":
    # stdio transport: the client starts this process and talks to it
    # over stdin/stdout — no network, no ports, works everywhere.
    mcp.run()
