"""Métricas Prometheus (E16, ADR-18)."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

rule_runs_total = Counter(
    "audit_rule_runs_total", "Execuções do motor de regras", ["tenant"]
)
findings_emitted_total = Counter(
    "audit_findings_emitted_total", "Achados emitidos por regra", ["rule_id"]
)
sync_duration_seconds = Histogram(
    "audit_sync_duration_seconds", "Duração do sync incremental por fonte", ["source"]
)
llm_tokens_total = Counter(
    "audit_llm_tokens_total", "Tokens de LLM consumidos por tenant", ["tenant"]
)
