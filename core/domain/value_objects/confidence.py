"""
Confidence Value Object

Represents the confidence level of data, predictions, or analysis.
Immutable and value-based equality.
"""

from dataclasses import dataclass
from typing import Any
from enum import Enum


class ConfidenceLevel(Enum):
    """Standard confidence levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Confidence:
    """
    Value object representing confidence in data or predictions.

    Confidence represents the certainty or reliability of information.
    Higher confidence indicates more trustworthy or verified data.

    Attributes:
        level: The confidence level enum
        score: Numerical confidence score (0-100)
        explanation: Optional explanation of confidence level
    """

    level: ConfidenceLevel
    score: int
    explanation: str | None = None

    def __post_init__(self) -> None:
        """Validate the Confidence value object."""
        if not 0 <= self.score <= 100:
            raise ValueError(f"Confidence score must be between 0 and 100, got: {self.score}")

    @classmethod
    def critical(cls, explanation: str | None = None) -> "Confidence":
        """Create a CRITICAL confidence level."""
        return cls(ConfidenceLevel.CRITICAL, 90, explanation or "Highly verified and reliable")

    @classmethod
    def high(cls, explanation: str | None = None) -> "Confidence":
        """Create a HIGH confidence level."""
        return cls(ConfidenceLevel.HIGH, 75, explanation or "Well-supported with evidence")

    @classmethod
    def medium(cls, explanation: str | None = None) -> "Confidence":
        """Create a MEDIUM confidence level."""
        return cls(ConfidenceLevel.MEDIUM, 50, explanation or "Moderately supported")

    @classmethod
    def low(cls, explanation: str | None = None) -> "Confidence":
        """Create a LOW confidence level."""
        return cls(ConfidenceLevel.LOW, 25, explanation or "Limited evidence or unverified")

    @classmethod
    def unknown(cls, explanation: str | None = None) -> "Confidence":
        """Create an UNKNOWN confidence level."""
        return cls(ConfidenceLevel.UNKNOWN, 0, explanation or "No confidence information")

    @classmethod
    def from_score(cls, score: int, explanation: str | None = None) -> "Confidence":
        """
        Create a Confidence from a numerical score.

        Maps score to appropriate level:
        - 80-100: CRITICAL
        - 60-79: HIGH
        - 40-59: MEDIUM
        - 20-39: LOW
        - 0-19: UNKNOWN
        """
        if score >= 80:
            level = ConfidenceLevel.CRITICAL
        elif score >= 60:
            level = ConfidenceLevel.HIGH
        elif score >= 40:
            level = ConfidenceLevel.MEDIUM
        elif score >= 20:
            level = ConfidenceLevel.LOW
        else:
            level = ConfidenceLevel.UNKNOWN
        return cls(level, score, explanation)

    @classmethod
    def from_level(cls, level: ConfidenceLevel, explanation: str | None = None) -> "Confidence":
        """Create a Confidence from a level with default score."""
        score_map = {
            ConfidenceLevel.CRITICAL: 90,
            ConfidenceLevel.HIGH: 75,
            ConfidenceLevel.MEDIUM: 50,
            ConfidenceLevel.LOW: 25,
            ConfidenceLevel.UNKNOWN: 0,
        }
        return cls(level, score_map[level], explanation)

    @property
    def is_high(self) -> bool:
        """Check if confidence is high or critical."""
        return self.level in {ConfidenceLevel.HIGH, ConfidenceLevel.CRITICAL}

    @property
    def is_low(self) -> bool:
        """Check if confidence is low or unknown."""
        return self.level in {ConfidenceLevel.LOW, ConfidenceLevel.UNKNOWN}

    @property
    def is_critical(self) -> bool:
        """Check if confidence is critical."""
        return self.level == ConfidenceLevel.CRITICAL

    @property
    def is_unknown(self) -> bool:
        """Check if confidence is unknown."""
        return self.level == ConfidenceLevel.UNKNOWN

    @property
    def percentage(self) -> str:
        """Format score as percentage."""
        return f"{self.score}%"

    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        return self.level.value.replace("_", " ").title()

    def combine(self, other: "Confidence") -> "Confidence":
        """
        Combine with another confidence using weighted average.

        The lower confidence reduces the overall more significantly.
        """
        # Weighted combination favoring lower confidence
        combined_score = (self.score + other.score) // 2

        # If both are high, keep higher
        if self.is_high and other.is_high:
            combined_score = max(self.score, other.score)
        # If one is low, significantly reduce
        elif self.is_low or other.is_low:
            combined_score = int(combined_score * 0.7)

        return Confidence.from_score(combined_score)

    def boost(self, factor: float = 1.1, max_score: int = 95) -> "Confidence":
        """Boost confidence by a factor, capped at max_score."""
        new_score = min(int(self.score * factor), max_score)
        return Confidence.from_score(new_score, self.explanation)

    def reduce(self, factor: float = 0.9, min_score: int = 5) -> "Confidence":
        """Reduce confidence by a factor, floored at min_score."""
        new_score = max(int(self.score * factor), min_score)
        return Confidence.from_score(new_score, self.explanation)

    def with_explanation(self, explanation: str) -> "Confidence":
        """Return a new Confidence with updated explanation."""
        return Confidence(self.level, self.score, explanation)

    def __str__(self) -> str:
        """String representation."""
        if self.explanation:
            return f"{self.display_name} ({self.percentage}) - {self.explanation}"
        return f"{self.display_name} ({self.percentage})"

    def __repr__(self) -> str:
        """Representation."""
        return f"Confidence({self.level}, {self.score})"

    def __eq__(self, other: Any) -> bool:
        """Value-based equality."""
        if not isinstance(other, Confidence):
            return False
        return self.level == other.level and self.score == other.score

    def __hash__(self) -> int:
        """Hash for use in sets and dict keys."""
        return hash((self.level, self.score))

    def __lt__(self, other: "Confidence") -> bool:
        """Less than operator (lower confidence)."""
        return self.score < other.score

    def __gt__(self, other: "Confidence") -> bool:
        """Greater than operator (higher confidence)."""
        return self.score > other.score

    def __le__(self, other: "Confidence") -> bool:
        """Less than or equal operator."""
        return self.score <= other.score

    def __ge__(self, other: "Confidence") -> bool:
        """Greater than or equal operator."""
        return self.score >= other.score


__all__ = ["Confidence", "ConfidenceLevel"]