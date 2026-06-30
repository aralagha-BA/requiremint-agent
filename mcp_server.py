"""
A minimal custom MCP server exposing two tools to the agents:

  1. check_duplicate_epic(title, summary) -> finds similar existing epics
  2. save_story(epic_id, story_json) -> persists a finished story

For the hackathon submission this stores to a local JSON file so the
demo is self-contained and needs no external accounts/API keys. Swap
`BACKLOG_PATH` writes for a Jira/Notion/Google Sheets API call if you
want a "real" integration -- keep credentials in environment variables
only, never hardcoded (see .env.example).

Run standalone for local testing:
    python mcp_server.py
"""

import json
import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP  # pip install mcp

BACKLOG_PATH = Path(os.environ.get("BACKLOG_PATH", "backlog.json"))

mcp = FastMCP("ba-backlog-server")


def _load_backlog() -> list[dict]:
    if not BACKLOG_PATH.exists():
        return []
    return json.loads(BACKLOG_PATH.read_text())


def _save_backlog(items: list[dict]) -> None:
    BACKLOG_PATH.write_text(json.dumps(items, indent=2))


@mcp.tool()
def check_duplicate_epic(title: str, summary: str) -> dict:
    """
    Check whether a similar epic already exists in the backlog.
    Simple keyword-overlap heuristic for the demo -- swap for an
    embedding-similarity search in a production version.
    """
    backlog = _load_backlog()
    title_words = set(title.lower().split())
    matches = []
    for item in backlog:
        existing_words = set(item.get("title", "").lower().split())
        overlap = title_words & existing_words
        if len(overlap) >= 2:
            matches.append(item)
    return {"duplicates_found": len(matches), "matches": matches}


@mcp.tool()
def save_story(epic_id: str, story: dict) -> dict:
    """Persist a finished, reviewed user story to the backlog store."""
    backlog = _load_backlog()
    backlog.append({"epic_id": epic_id, **story})
    _save_backlog(backlog)
    return {"saved": True, "total_items": len(backlog)}


@mcp.tool()
def list_backlog() -> list[dict]:
    """Return the full current backlog -- useful for the UI's export view."""
    return _load_backlog()


if __name__ == "__main__":
    mcp.run(transport="stdio")
