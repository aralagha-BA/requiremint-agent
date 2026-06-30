"""
Agent definitions using Google ADK (Agent Development Kit).

Each agent is a narrow specialist with its own system instruction and
(optionally) its own tools. The Orchestrator (see orchestrator.py) wires
them together into a pipeline with a feedback loop.

NOTE: This is a skeleton meant to be adapted to the exact ADK version
you install (`pip install google-adk`). Method names like `Agent`,
`LlmAgent`, `.run()` may differ slightly across ADK releases — check
the installed package's docs/examples and adjust imports accordingly.
"""

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import MCPToolset, StdioServerParameters
from schemas import ElicitationSession, Epic, UserStory

MODEL = "gemini-2.0-flash"  # swap for whichever Gemini model you have access to


# ---------------------------------------------------------------------------
# 1. Elicitation Agent
# ---------------------------------------------------------------------------
# Talks directly to the stakeholder. Its job is to ask good follow-up
# questions, not to write final stories -- keeps its output low-stakes
# and conversational.
elicitation_agent = LlmAgent(
    name="elicitation_agent",
    model=MODEL,
    instruction="""
You are a senior Business Analyst conducting requirements elicitation.
Your job is ONLY to interview the stakeholder -- never invent requirements.

Rules:
- Ask one focused question at a time.
- If an answer is vague (e.g. "make it easier to use"), ask a concrete
  follow-up: who is affected, what does success look like, what's the
  current pain point.
- Probe for: user roles, goals, constraints, success metrics, edge cases.
- When you believe you have enough detail on a topic, summarize it back
  to the stakeholder in 1-2 sentences and ask them to confirm.
- Keep a friendly, efficient tone -- this is a working session, not a survey.
""",
    description="Interviews a stakeholder to gather raw requirement notes.",
)


# ---------------------------------------------------------------------------
# 2. Synthesis Agent
# ---------------------------------------------------------------------------
# Takes the raw transcript (possibly from multiple stakeholders) and
# clusters it into candidate epics. Explicitly tasked with flagging
# disagreement between stakeholders rather than silently resolving it.
synthesis_agent = LlmAgent(
    name="synthesis_agent",
    model=MODEL,
    instruction="""
You receive raw stakeholder notes/transcripts (possibly from multiple
people). Cluster them into candidate EPICS -- coherent themes of related
functionality.

Rules:
- Group related needs under one epic; don't create an epic per sentence.
- If two stakeholders express conflicting needs on the same topic, do NOT
  silently pick one. Record both views in the epic's `conflicts` field.
- Each epic needs a short title and a 1-3 sentence summary.
- Output must conform to the Epic list schema you are given.
""",
    description="Clusters raw stakeholder input into candidate epics.",
    output_schema=list[Epic],
)


# ---------------------------------------------------------------------------
# 3. Story-Writing Agent
# ---------------------------------------------------------------------------
# Converts each epic into INVEST-style user stories with acceptance
# criteria. Strict structured output so downstream tooling (Jira/Sheets
# via MCP) can consume it directly.
story_writer_agent = LlmAgent(
    name="story_writer_agent",
    model=MODEL,
    instruction="""
For the given epic, write well-formed user stories.

Format: "As a <role>, I want <goal>, so that <benefit>."

Rules:
- Each story should be independently valuable and testable (INVEST).
- Include 2-5 acceptance criteria per story, written as
  Given/When/Then where practical.
- Assign a MoSCoW priority (must_have/should_have/could_have/wont_have)
  based on how the stakeholder described urgency/impact.
- If something is still ambiguous, do NOT guess -- add it to
  `open_questions` on the story instead of inventing details.
- Output must conform to the UserStory list schema.
""",
    description="Converts an epic into structured user stories with acceptance criteria.",
    output_schema=list[UserStory],
)


# ---------------------------------------------------------------------------
# 4. Critic / QA Agent
# ---------------------------------------------------------------------------
# Reviews the synthesized epics+stories for ambiguity, missing edge
# cases, duplicate/conflicting requirements. This is what creates the
# feedback loop back to the Elicitation Agent.
critic_agent = LlmAgent(
    name="critic_agent",
    model=MODEL,
    instruction="""
You are a skeptical QA reviewer for requirements. Given a full session
(epics + stories), find problems:

- Vague acceptance criteria (not testable).
- Missing edge cases (errors, empty states, permissions, scale).
- Internal contradictions between stories or epics.
- Stories that are too large (should be split) or trivially small
  (should be merged).

For each problem, produce a specific, answerable clarifying question
that the Elicitation Agent could ask the stakeholder. Do not just say
"this is unclear" -- ask the actual question.

If the session has no remaining problems, set status to "complete".
Otherwise set status to "needs_clarification" and populate
`pending_clarifications`.
""",
    description="QA reviews the synthesized backlog and raises targeted clarifying questions.",
    output_schema=ElicitationSession,
)


# ---------------------------------------------------------------------------
# MCP Tooling
# ---------------------------------------------------------------------------
# Connects agents to the custom MCP server (see mcp_server.py) which
# exposes tools for: checking the existing backlog for duplicates, and
# persisting final stories to storage (Sheet/Jira/local DB).
backlog_toolset = MCPToolset(
    connection_params=StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
    ),
)

# Give the synthesis and story-writing agents access to the backlog tools
# so they can check for duplicates before creating new epics/stories.
synthesis_agent.tools = [backlog_toolset]
story_writer_agent.tools = [backlog_toolset]
