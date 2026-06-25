"""Pydantic schemas for plan representation and validation.

These models are the building blocks for the optional LLM-based planner.
Currently used for validation only; the actual plan is still built by the
rule-based planner in ``planner.py``.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """A single tool invocation within a plan."""

    name: str = Field(..., description="Tool name, must match a key in TOOL_REGISTRY")
    description: str = Field(default="", description="Human-readable purpose of this step")


class StepPlan(BaseModel):
    """An ordered sequence of tool calls that constitutes a video analysis plan."""

    tools: list[ToolCall] = Field(default_factory=list, description="Ordered tool chain")
    reasoning: str = Field(default="", description="Why this plan was chosen")


class PlanValidationResult(BaseModel):
    """Result of validating a plan against tool registry and dependency rules."""

    valid: bool = Field(default=False, description="Whether the plan passes all checks")
    errors: list[str] = Field(default_factory=list, description="Validation error messages")
