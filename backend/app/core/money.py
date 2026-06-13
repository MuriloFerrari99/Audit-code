"""Padrão de dinheiro (T-023, ADR-04).

Dinheiro é SEMPRE Decimal + currency. Float é proibido em qualquer caminho de
valor. Persistência em NUMERIC(18,4). Apresentação em 2 casas, ROUND_HALF_UP.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, getcontext

getcontext().prec = 28

CENTS = Decimal("0.01")
STORAGE = Decimal("0.0001")  # 4 casas, casa com NUMERIC(18,4)


def to_decimal(value: str | int | Decimal) -> Decimal:
    """Converte para Decimal de forma segura. float é recusado de propósito."""
    if isinstance(value, float):  # pragma: no cover - guarda explícita
        raise TypeError("float é proibido em valores monetários; use str/Decimal")
    return Decimal(value)


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "BRL"

    @classmethod
    def of(cls, value: str | int | Decimal, currency: str = "BRL") -> Money:
        return cls(to_decimal(value).quantize(STORAGE), currency)

    def _check(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError(f"moedas diferentes: {self.currency} vs {other.currency}")

    def __add__(self, other: Money) -> Money:
        self._check(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._check(other)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, qty: Decimal | int) -> Money:
        if isinstance(qty, float):
            raise TypeError("multiplicação por float é proibida; use Decimal")
        return Money((self.amount * Decimal(qty)).quantize(STORAGE), self.currency)

    def rounded(self) -> Decimal:
        """Valor para apresentação (2 casas)."""
        return self.amount.quantize(CENTS, rounding=ROUND_HALF_UP)

    def __str__(self) -> str:
        return f"{self.currency} {self.rounded()}"
