"""
Shared data models for the Requirements Elicitation Agent.

Using Pydantic gives us structured, validated output from the LLM
(via ADK's structured-output / JSON-schema support) instead of parsing
free text — this matters because downstream agents (Critic, MCP writer)
depend on a stable schema.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class Priority(str, Enum):
    MUST = "must_have"
    SHOULD = "should_have"
    COULD = "could_have"
    WONT = "wont_have"  # MoSCoW


class UserStory(BaseModel):
    id: str = Field(description="Short stable id, e.g. US-001")
    role: str = Field(description="The 'as a <role>' persona")
    goal: str = Field(description="The 'I want <goal>' clause")
    benefit: str = Field(description="The 'so that <benefit>' clause")
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="Given/When/Then or plain bullet acceptance criteria",
    )
    priority: Priority = Priority.SHOULD
    open_questions: List[str] = Field(
        default_factory=list,
        description="Ambiguities the Critic agent still wants resolved",
    )
    source_stakeholder: Optional[str] = None


class Epic(BaseModel):
    id: str = Field(description="Short stable id, e.g. EP-01")
    title: str
    summary: str
    stories: List[UserStory] = Field(default_factory=list)
    conflicts: List[str] = Field(
        default_factory=list,
        description="Notes when two stakeholders disagree on this epic",
    )


class ElicitationSession(BaseModel):
    """The full working state passed between agents in the pipeline."""
    session_id: str
    stakeholder_notes: List[str] = Field(default_factory=list)
    transcript: List[dict] = Field(
        default_factory=list, description="[{role, content}, ...] chat turns"
    )
    epics: List[Epic] = Field(default_factory=list)
    pending_clarifications: List[str] = Field(default_factory=list)
    status: str = "in_progress"  # in_progress | needs_clarification | complete
