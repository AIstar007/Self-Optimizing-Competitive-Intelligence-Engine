"""
Critique Agent

Reviews the output of other agents, detects hallucinations,
verifies evidence, improves reasoning, and suggests corrections.
Enables agent self-reflection loops.
"""

from .critique_agent import CritiqueAgent

__all__ = ["CritiqueAgent"]