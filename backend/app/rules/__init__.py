"""Motor de regras determinístico (E9). Ver docs/regras.md e ADR-03/07."""

from app.rules.base import EvidenceDraft, FindingDraft, Rule, RuleContext, registry

__all__ = ["Rule", "RuleContext", "FindingDraft", "EvidenceDraft", "registry"]
