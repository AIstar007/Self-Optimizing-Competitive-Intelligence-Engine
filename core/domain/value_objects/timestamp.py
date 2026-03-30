"""
Timestamp Value Object

Represents a point in time with timezone awareness.
Immutable and value-based equality.
"""

from dataclasses import dataclass
from typing import Any, Union
from datetime import datetime, timezone, timedelta
from enum import Enum


class TimestampPrecision(Enum):
    """Precision level for timestamps."""
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


@dataclass(frozen=True, slots=True)
class Timestamp:
    """
    Value object representing a timestamp.

    Timestamps are always in UTC timezone to ensure consistency
    across the system. They provide convenient methods for
    date/time manipulation.

    Attributes:
        value: The underlying datetime object (always UTC)
    """

    value: datetime

    def __post_init__(self) -> None:
        """Validate the Timestamp value object."""
        # Ensure timezone is set to UTC
        if self.value.tzinfo is None:
            object.__setattr__(self, "value", self.value.replace(tzinfo=timezone.utc))
        elif self.value.tzinfo != timezone.utc:
            # Convert to UTC if different timezone
            object.__setattr__(self, "value", self.value.astimezone(timezone.utc))

    @classmethod
    def now(cls) -> "Timestamp":
        """Create a Timestamp for the current time (UTC)."""
        return cls(datetime.now(timezone.utc))

    @classmethod
    def from_datetime(cls, dt: datetime) -> "Timestamp":
        """Create a Timestamp from a datetime object."""
        return cls(dt)

    @classmethod
    def from_iso(cls, iso_string: str) -> "Timestamp":
        """Create a Timestamp from an ISO 8601 string."""
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return cls(dt)

    @classmethod
    def from_timestamp(cls, ts: float) -> "Timestamp":
        """Create a Timestamp from a Unix timestamp."""
        return cls(datetime.fromtimestamp(ts, tz=timezone.utc))

    @classmethod
    def from_date(cls, year: int, month: int, day: int,
                  hour: int = 0, minute: int = 0, second: int = 0,
                  microsecond: int = 0) -> "Timestamp":
        """Create a Timestamp from date components."""
        return cls(datetime(year, month, day, hour, minute, second, microsecond, tzinfo=timezone.utc))

    @classmethod
    def utc_start_of_day(cls) -> "Timestamp":
        """Get the start of the current day in UTC."""
        now = datetime.now(timezone.utc)
        return cls(datetime(now.year, now.month, now.day, 0, 0, 0, 0, tzinfo=timezone.utc))

    @classmethod
    def utc_start_of_week(cls) -> "Timestamp":
        """Get the start of the current week (Monday) in UTC."""
        now = datetime.now(timezone.utc)
        days_since_monday = now.weekday()
        start_of_week = now - timedelta(days=days_since_monday)
        return cls(datetime(start_of_week.year, start_of_week.month, start_of_week.day, 0, 0, 0, 0, tzinfo=timezone.utc))

    @classmethod
    def utc_start_of_month(cls) -> "Timestamp":
        """Get the start of the current month in UTC."""
        now = datetime.now(timezone.utc)
        return cls(datetime(now.year, now.month, 1, 0, 0, 0, 0, tzinfo=timezone.utc))

    @classmethod
    def utc_start_of_year(cls) -> "Timestamp":
        """Get the start of the current year in UTC."""
        now = datetime.now(timezone.utc)
        return cls(datetime(now.year, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc))

    @property
    def year(self) -> int:
        """Get the year."""
        return self.value.year

    @property
    def month(self) -> int:
        """Get the month (1-12)."""
        return self.value.month

    @property
    def day(self) -> int:
        """Get the day of month (1-31)."""
        return self.value.day

    @property
    def hour(self) -> int:
        """Get the hour (0-23)."""
        return self.value.hour

    @property
    def minute(self) -> int:
        """Get the minute (0-59)."""
        return self.value.minute

    @property
    def second(self) -> int:
        """Get the second (0-59)."""
        return self.value.second

    @property
    def weekday(self) -> int:
        """Get the weekday (0=Monday, 6=Sunday)."""
        return self.value.weekday()

    @property
    def date_only(self) -> "Timestamp":
        """Get timestamp with time set to midnight (start of day)."""
        return Timestamp(datetime(self.year, self.month, self.day, 0, 0, 0, 0, tzinfo=timezone.utc))

    @property
    def end_of_day(self) -> "Timestamp":
        """Get timestamp with time set to end of day (23:59:59.999999)."""
        return Timestamp(datetime(self.year, self.month, self.day, 23, 59, 59, 999999, tzinfo=timezone.utc))

    @property
    def unix(self) -> float:
        """Get Unix timestamp."""
        return self.value.timestamp()

    @property
    def iso(self) -> str:
        """Get ISO 8601 string representation."""
        return self.value.isoformat()

    def is_future(self) -> bool:
        """Check if this timestamp is in the future."""
        return self.value > datetime.now(timezone.utc)

    def is_past(self) -> bool:
        """Check if this timestamp is in the past."""
        return self.value < datetime.now(timezone.utc)

    def is_today(self) -> bool:
        """Check if this timestamp is today."""
        now = datetime.now(timezone.utc)
        return (self.year, self.month, self.day) == (now.year, now.month, now.day)

    def is_yesterday(self) -> bool:
        """Check if this timestamp was yesterday."""
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        return (self.year, self.month, self.day) == (yesterday.year, yesterday.month, yesterday.day)

    def is_this_week(self) -> bool:
        """Check if this timestamp is in the current week."""
        now = datetime.now(timezone.utc)
        start_of_week = now - timedelta(days=now.weekday())
        end_of_week = start_of_week + timedelta(days=7)
        return start_of_week <= self.value < end_of_week

    def is_this_month(self) -> bool:
        """Check if this timestamp is in the current month."""
        now = datetime.now(timezone.utc)
        return self.year == now.year and self.month == now.month

    def days_until(self) -> int:
        """Get days until this timestamp (positive for future, negative for past)."""
        return (self.value - datetime.now(timezone.utc)).days

    def days_since(self) -> int:
        """Get days since this timestamp (negative for future, positive for past)."""
        return -self.days_until()

    def add(self, **kwargs) -> "Timestamp":
        """
        Add time components to this timestamp.

        Args:
            years: Years to add
            months: Months to add
            weeks: Weeks to add
            days: Days to add
            hours: Hours to add
            minutes: Minutes to add
            seconds: Seconds to add
        """
        delta = timedelta(
            weeks=kwargs.get("weeks", 0),
            days=kwargs.get("days", 0),
            hours=kwargs.get("hours", 0),
            minutes=kwargs.get("minutes", 0),
            seconds=kwargs.get("seconds", 0),
        )

        # Handle months and years separately (they're not fixed durations)
        dt = self.value + delta

        if "years" in kwargs:
            dt = dt.replace(year=dt.year + kwargs["years"])
        if "months" in kwargs:
            new_month = dt.month + kwargs["months"]
            year_offset, new_month = divmod(new_month - 1, 12)
            dt = dt.replace(year=dt.year + year_offset, month=new_month + 1)

        return Timestamp(dt)

    def subtract(self, **kwargs) -> "Timestamp":
        """Subtract time components from this timestamp."""
        negative_kwargs = {k: -v for k, v in kwargs.items()}
        return self.add(**negative_kwargs)

    def diff(self, other: "Timestamp") -> timedelta:
        """Get the time difference between this and another timestamp."""
        return self.value - other.value

    def is_before(self, other: "Timestamp") -> bool:
        """Check if this timestamp is before another."""
        return self.value < other.value

    def is_after(self, other: "Timestamp") -> bool:
        """Check if this timestamp is after another."""
        return self.value > other.value

    def format(self, fmt: str = "%Y-%m-%d %H:%M:%S UTC") -> str:
        """Format the timestamp as a string."""
        return self.value.strftime(fmt)

    def format_date(self) -> str:
        """Format as date only (YYYY-MM-DD)."""
        return self.value.strftime("%Y-%m-%d")

    def format_relative(self) -> str:
        """Format as relative time (e.g., '2 hours ago', 'in 3 days')."""
        now = datetime.now(timezone.utc)
        delta = self.value - now
        total_seconds = int(delta.total_seconds())
        abs_seconds = abs(total_seconds)

        if abs_seconds < 60:
            unit = "second" if abs_seconds == 1 else "seconds"
            return f"{abs_seconds} {unit} {'from now' if total_seconds > 0 else 'ago'}"

        if abs_seconds < 3600:
            minutes = abs_seconds // 60
            unit = "minute" if minutes == 1 else "minutes"
            return f"{minutes} {unit} {'from now' if total_seconds > 0 else 'ago'}"

        if abs_seconds < 86400:
            hours = abs_seconds // 3600
            unit = "hour" if hours == 1 else "hours"
            return f"{hours} {unit} {'from now' if total_seconds > 0 else 'ago'}"

        if abs_seconds < 604800:  # 7 days
            days = abs_seconds // 86400
            unit = "day" if days == 1 else "days"
            return f"{days} {unit} {'from now' if total_seconds > 0 else 'ago'}"

        if abs_seconds < 2592000:  # 30 days
            weeks = abs_seconds // 604800
            unit = "week" if weeks == 1 else "weeks"
            return f"{weeks} {unit} {'from now' if total_seconds > 0 else 'ago'}"

        months = abs_seconds // 2592000
        unit = "month" if months == 1 else "months"
        return f"{months} {unit} {'from now' if total_seconds > 0 else 'ago'}"

    @property
    def to_datetime(self) -> datetime:
        """Get the underlying datetime object."""
        return self.value

    def __str__(self) -> str:
        """String representation (ISO format)."""
        return self.iso

    def __repr__(self) -> str:
        """Representation."""
        return f"Timestamp({self.iso})"

    def __eq__(self, other: Any) -> bool:
        """Value-based equality."""
        if not isinstance(other, Timestamp):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        """Hash for use in sets and dict keys."""
        return hash(self.value)

    def __lt__(self, other: "Timestamp") -> bool:
        """Less than operator."""
        return self.value < other.value

    def __gt__(self, other: "Timestamp") -> bool:
        """Greater than operator."""
        return self.value > other.value

    def __le__(self, other: "Timestamp") -> bool:
        """Less than or equal operator."""
        return self.value <= other.value

    def __ge__(self, other: "Timestamp") -> bool:
        """Greater than or equal operator."""
        return self.value >= other.value

    def __sub__(self, other: Union["Timestamp", timedelta]) -> Union[timedelta, "Timestamp"]:
        """Subtract operator."""
        if isinstance(other, Timestamp):
            return self.value - other.value
        return Timestamp(self.value - other)

    def __add__(self, delta: timedelta) -> "Timestamp":
        """Add operator for timedelta."""
        return Timestamp(self.value + delta)


__all__ = ["Timestamp", "TimestampPrecision"]