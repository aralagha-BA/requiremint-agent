"""
Orchestrator: wires the four specialist agents into a pipeline with a
feedback loop, and is the single entry point the UI (app.py) calls.

Flow:
    stakeholder <-> elicitation_agent          (repeats until enough info)
                         |
                         v
                  synthesis_agent  --------> epics (with conflicts flagged)
                         |
                         v
                story_writer_agent ---------> stories per epic
                         |
                         v
                   critic_agent ----+--> status=complete -> DONE
                         |          |
                         |          +--> status=needs_clarification
                         v
            pending_clarifications --------> fed back to elicitation_agent
            (loop, capped at MAX_CLARIFICATION_ROUNDS)
"""

import uuid
from google.adk.runners import InMemoryRunner  # adjust import per installed ADK version
from agents import (
    elicitation_agent,
    synthesis_agent,
    story_writer_agent,
    critic_agent,
)
from schemas import ElicitationSession

MAX_CLARIFICATION_ROUNDS = 3


class RequirementsOrchestrator:
    def __init__(self):
        self.session = ElicitationSession(session_id=str(uuid.uuid4()))
        # One runner per agent keeps state isolated; swap for a single
        # SequentialAgent/ParallelAgent composition if your ADK version
        # supports declarative pipelines instead of manual orchestration.
        self._elicitation_runner = InMemoryRunner(elicitation_agent)
        self._synthesis_runner = InMemoryRunner(synthesis_agent)
        self._story_runner = InMemoryRunner(story_writer_agent)
        self._critic_runner = InMemoryRunner(critic_agent)

    # ------------------------------------------------------------------
    # Step 1: interview turn (called once per stakeholder chat message)
    # ------------------------------------------------------------------
    def interview_turn(self, stakeholder_message: str) -> str:
        self.session.transcript.append(
            {"role": "stakeholder", "content": stakeholder_message}
        )
        reply = self._elicitation_runner.run(
            input=stakeholder_message,
            context={"transcript": self.session.transcript},
        )
        self.session.transcript.append({"role": "agent", "content": reply.text})
        return reply.text

    # ------------------------------------------------------------------
    # Step 2-4: run synthesis -> story writing -> critic, looping on
    # clarifications up to MAX_CLARIFICATION_ROUNDS.
    # ------------------------------------------------------------------
    def build_backlog(self) -> ElicitationSession:
        notes = "\n".join(
            f"{t['role']}: {t['content']}" for t in self.session.transcript
        )

        for round_num in range(MAX_CLARIFICATION_ROUNDS):
            epics_result = self._synthesis_runner.run(input=notes)
            self.session.epics = epics_result.output  # list[Epic]

            for epic in self.session.epics:
                stories_result = self._story_runner.run(
                    input=epic.summary, context={"epic": epic.model_dump()}
                )
                epic.stories = stories_result.output  # list[UserStory]

            critic_result = self._critic_runner.run(
                input="review", context={"session": self.session.model_dump()}
            )
            reviewed: ElicitationSession = critic_result.output
            self.session.status = reviewed.status
            self.session.pending_clarifications = reviewed.pending_clarifications

            if self.session.status == "complete":
                break

            # Feed clarifications back into the notes for the next round
            # instead of re-asking the live stakeholder synchronously --
            # in app.py these are surfaced to the user as follow-up
            # questions before the next build_backlog() call.
            notes += "\n\nOPEN QUESTIONS TO RESOLVE:\n" + "\n".join(
                self.session.pending_clarifications
            )

        return self.session

    # ------------------------------------------------------------------
    # Step 5: persist to backlog via the MCP toolset (writes happen
    # inside story_writer_agent's tool calls; this is a manual fallback)
    # ------------------------------------------------------------------
    def export(self) -> dict:
        return self.session.model_dump()
