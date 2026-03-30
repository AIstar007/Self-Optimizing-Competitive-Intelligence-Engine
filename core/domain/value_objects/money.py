"""
Money Value Object

Represents monetary values with currency.
Immutable and value-based equality.
"""

from dataclasses import dataclass
from typing import Any
from decimal import Decimal, ROUND_HALF_UP


@dataclass(frozen=True, slots=True)
class Money:
    """
    Value object representing a monetary amount with currency.

    Money objects are immutable and have value-based equality.
    They handle decimal arithmetic for financial precision.

    Attributes:
        amount: The monetary amount as a Decimal
        currency: ISO 4217 currency code (e.g., "USD", "EUR")
    """

    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        """Validate the Money value object."""
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")
        if not self.currency:
            raise ValueError("Currency code cannot be empty")
        if len(self.currency) != 3:
            raise ValueError(f"Currency code must be 3 characters (ISO 4217), got: {self.currency}")

    @classmethod
    def usd(cls, amount: float | int | str) -> "Money":
        """Create USD money from a numeric value."""
        return cls(Decimal(str(amount)), "USD")

    @classmethod
    def eur(cls, amount: float | int | str) -> "Money":
        """Create EUR money from a numeric value."""
        return cls(Decimal(str(amount)), "EUR")

    @classmethod
    def gbp(cls, amount: float | int | str) -> "Money":
        """Create GBP money from a numeric value."""
        return cls(Decimal(str(amount)), "GBP")

    @classmethod
    def zero(cls, currency: str = "USD") -> "Money":
        """Create zero money for a given currency."""
        return cls(Decimal("0"), currency)

    @classmethod
    def from_cents(cls, cents: int, currency: str = "USD") -> "Money":
        """Create Money from cents/lowest denomination."""
        return cls(Decimal(cents) / Decimal("100"), currency)

    @classmethod
    def from_cents(cls, cents: int, currency: str = "USD") -> "Money":
        """Create Money from cents/lowest denomination."""
        return cls(Decimal(cents) / Decimal("100"), currency)

    @property
    def in_cents(self) -> int:
        """Get the amount in the smallest currency unit (e.g., cents)."""
        return int((self.amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    @property
    def in_millions(self) -> Decimal:
        """Get the amount in millions."""
        return self.amount / Decimal("1000000")

    @property
    def in_billions(self) -> Decimal:
        """Get the amount in billions."""
        return self.amount / Decimal("1000000000")

    def is_zero(self) -> bool:
        """Check if the amount is zero."""
        return self.amount == Decimal("0")

    def is_positive(self) -> bool:
        """Check if the amount is positive."""
        return self.amount > Decimal("0")

    def add(self, other: "Money") -> "Money":
        """Add another Money value. Must be same currency."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot add different currencies: {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: "Money") -> "Money":
        """Subtract another Money value. Must be same currency."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract different currencies: {self.currency} and {other.currency}")
        if self.amount < other.amount:
            raise ValueError("Cannot subtract to create negative money")
        return Money(self.amount - other.amount, self.currency)

    def multiply(self, factor: float | int | Decimal) -> "Money":
        """Multiply by a factor."""
        factor_decimal = Decimal(str(factor))
        if factor_decimal < 0:
            raise ValueError("Cannot multiply by negative factor")
        return Money(self.amount * factor_decimal, self.currency)

    def divide(self, divisor: float | int | Decimal) -> "Money":
        """Divide by a divisor."""
        if divisor == 0:
            raise ValueError("Cannot divide by zero")
        divisor_decimal = Decimal(str(divisor))
        if divisor_decimal < 0:
            raise ValueError("Cannot divide by negative divisor")
        return Money(self.amount / divisor_decimal, self.currency)

    def is_greater_than(self, other: "Money") -> bool:
        """Check if this amount is greater than another."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies: {self.currency} and {other.currency}")
        return self.amount > other.amount

    def is_less_than(self, other: "Money") -> bool:
        """Check if this amount is less than another."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies: {self.currency} and {other.currency}")
        return self.amount < other.amount

    def format(self, include_currency: bool = True) -> str:
        """Format as a string with appropriate currency formatting."""
        formatted = f"${self.amount:,.2f}" if self.currency == "USD" else f"{self.amount:,.2f} {self.currency}"
        if not include_currency and self.currency == "USD":
            return formatted.replace(" USD", "")
        return formatted

    def format_short(self) -> str:
        """Format with short notation (K, M, B)."""
        abs_amount = abs(self.amount)
        suffix = ""

        if abs_amount >= 1_000_000_000:
            amount = self.amount / 1_000_000_000
            suffix = "B"
        elif abs_amount >= 1_000_000:
            amount = self.amount / 1_000_000
            suffix = "M"
        elif abs_amount >= 1_000:
            amount = self.amount / 1_000
            suffix = "K"
        else:
            amount = self.amount

        currency_symbol = "$" if self.currency == "USD" else self.currency + " "
        return f"{currency_symbol}{amount:.1f}{suffix}"

    def __str__(self) -> str:
        """String representation."""
        return self.format()

    def __repr__(self) -> str:
        """Representation."""
        return f"Money({self.amount}, {self.currency})"

    def __eq__(self, other: Any) -> bool:
        """Value-based equality."""
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency == other.currency

    def __hash__(self) -> int:
        """Hash for use in sets and dict keys."""
        return hash((self.amount, self.currency))

    def __add__(self, other: "Money") -> "Money":
        """Add operator."""
        return self.add(other)

    def __sub__(self, other: "Money") -> "Money":
        """Subtract operator."""
        return self.subtract(other)

    def __mul__(self, factor: float | int | Decimal) -> "Money":
        """Multiply operator."""
        return self.multiply(factor)

    def __truediv__(self, divisor: float | int | Decimal) -> "Money":
        """Divide operator."""
        return self.divide(divisor)

    def __gt__(self, other: "Money") -> bool:
        """Greater than operator."""
        return self.is_greater_than(other)

    def __lt__(self, other: "Money") -> bool:
        """Less than operator."""
        return self.is_less_than(other)

    def __ge__(self, other: "Money") -> bool:
        """Greater than or equal operator."""
        return not self.is_less_than(other)

    def __le__(self, other: "Money") -> bool:
        """Less than or equal operator."""
        return not self.is_greater_than(other)


__all__ = ["Money"]