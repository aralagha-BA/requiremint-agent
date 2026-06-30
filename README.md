# Requirements Elicitation Agent

**Track:** Agents for Business

## Problem

Business analysts spend significant time interviewing stakeholders, untangling
vague or conflicting input, and manually translating it into well-formed
epics and user stories. Mistakes here are expensive: vague acceptance
criteria and unresolved conflicts surface late, during sprints, as rework.

## Solution

A multi-agent pipeline that interviews a stakeholder conversationally, then
synthesizes the conversation into epics and INVEST-style user stories with
acceptance criteria, while explicitly flagging ambiguity and stakeholder
conflicts instead of guessing.

## Architecture

```
 Stakeholder
     |
     v
[Elicitation Agent] <-----------------+
     |  (raw notes/transcript)        |
     v                                |
[Synthesis Agent] -- MCP tool: --> check_duplicate_epic
     |  (epics, conflicts flagged)    |
     v                                |
[Story Writer Agent] -- MCP tool: --> save_story
     |  (epics + stories)             |
     v                                |
[Critic / QA Agent] ---- pending_clarifications --+
     |
     v (status == complete)
  Final backlog (epics + stories), exportable as JSON
```

- **Orchestrator** (`orchestrator.py`): runs the pipeline, loops the Critic's
  clarifications back into synthesis up to `MAX_CLARIFICATION_ROUNDS`.
- **Agents** (`agents.py`): four ADK `LlmAgent`s, each with a narrow
  instruction and structured (Pydantic) output schema.
- **MCP Server** (`mcp_server.py`): custom tool server exposing
  `check_duplicate_epic`, `save_story`, `list_backlog`. Demo storage is a
  local JSON file; swap for Jira/Notion/Sheets in production.
- **UI** (`app.py`): Streamlit chat + backlog viewer, used for the demo.

## Key concepts demonstrated

| Concept | Where |
|---|---|
| Agent / Multi-agent system (ADK) | `agents.py`, `orchestrator.py` |
| MCP Server | `mcp_server.py`, wired into agents via `MCPToolset` |
| Security features | input length capping in `app.py`, no hardcoded secrets, `.env.example` pattern |
| Deployability | Streamlit app, runnable locally or on Cloud Run |
| Agent skills | narrow per-agent instructions act as composable skills; story schema enforces a reusable "write_user_story" behavior |

## Setup

```bash
git clone <your-repo-url>
cd ba_agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GOOGLE_API_KEY
streamlit run app.py
```

The MCP server is launched automatically by the agent toolset
(`StdioServerParameters` in `agents.py`); you don't need to run
`mcp_server.py` separately unless testing it in isolation.

## Notes on adapting this skeleton

- ADK's exact API (`LlmAgent`, `InMemoryRunner`, structured `output_schema`)
  may differ slightly by installed version -- check `google-adk`'s docs and
  adjust imports/method names as needed.
- `mcp_server.py`'s duplicate-check is a simple keyword-overlap heuristic for
  demo purposes; swap for embedding similarity for production quality.
- No API keys or secrets are committed; `.env` is gitignored.
