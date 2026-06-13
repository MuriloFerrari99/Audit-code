"""Testes puros (sem DB): normalização de insumo e priorização do Triador."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.agents.triador import prioritize, priority_score
from app.ml.normalize import normalize_description


def test_normalize_synonyms_and_units():
    assert "aco ca-50" in normalize_description("Vergalhão 10.0mm")
    assert "10mm" in normalize_description("Aço CA-50 Ø10")


def test_triador_orders_by_materiality_and_severity():
    f_low = SimpleNamespace(exposed_amount=Decimal("5000"), severity="low")
    f_high = SimpleNamespace(exposed_amount=Decimal("2000"), severity="critical")
    f_mid = SimpleNamespace(exposed_amount=Decimal("3000"), severity="high")
    ordered = prioritize([f_low, f_high, f_mid])
    # critical*2000=8000 > high*3000=9000? high=3*3000=9000 > crit=4*2000=8000 > low=1*5000=5000
    assert priority_score(ordered[0]) >= priority_score(ordered[1]) >= priority_score(ordered[2])
    assert ordered[0] is f_mid  # maior score
