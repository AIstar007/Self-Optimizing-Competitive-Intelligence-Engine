"""
Planner Agent

Decomposes user goals into tasks. Example: "Analyze OpenAI competitors"
becomes a task graph with tasks for identifying competitors,
researching companies, extracting signals, analyzing strategies,
and generating reports.
"""

from .planner_agent import PlannerAgent

__all__ = ["PlannerAgent"]