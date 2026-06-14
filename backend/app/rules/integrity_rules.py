"""Regras da Dimensão 4 — Integridade de fornecedor (advisory reforçado).

Leem `counterparty` (populado por integrity.service.refresh_for_tenant — sem rede
na avaliação). Toda evidência cita a fonte + data. Nunca afirmam fraude; apontam
"sinal a investigar". `exposed_amount` = valor comprado do fornecedor (gasto sob
risco), para priorização — não é "perda".
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.money import Money
from app.core.timeutils import now_utc
from app.integrity.service import only_digits
from app.models.findings import Severity
from app.models.integrity import Counterparty
from app.models.sourcing import Creditor, PurchaseOrder
from app.rules.base import EvidenceDraft, FindingDraft, RuleContext, dedup_key, register

D = Decimal


def _creditors_with_cnpj(session: Session) -> list[Creditor]:
    return list(
        session.execute(
            select(Creditor).where(Creditor.cnpj_cpf.is_not(None), Creditor.cnpj_cpf != "")
        ).scalars()
    )


def _counterparties(session: Session, cnpjs: list[str]) -> dict[str, Counterparty]:
    if not cnpjs:
        return {}
    rows = session.execute(
        select(Counterparty).where(Counterparty.cnpj.in_(cnpjs))
    ).scalars()
    return {c.cnpj: c for c in rows}


def _spend_by_creditor(session: Session) -> dict[str, Decimal]:
    rows = session.execute(
        select(PurchaseOrder.creditor_id, func.coalesce(func.sum(PurchaseOrder.total), 0))
        .where(PurchaseOrder.creditor_id.is_not(None))
        .group_by(PurchaseOrder.creditor_id)
    ).all()
    return {str(cid): D(str(total)) for cid, total in rows}


def _source_snap(cp: Counterparty) -> dict:
    return {"source": cp.source or "brasilapi", "checked_at": str(cp.checked_at)}


# --------------------------------------------------------------------------- I1
class SanctionedSupplierRule:
    id = "I1"
    version = 1
    dimension = 4
    severity_default = Severity.CRITICAL
    default_params: dict = {}

    def evaluate(self, session: Session, ctx: RuleContext) -> list[FindingDraft]:
        drafts: list[FindingDraft] = []
        creditors = _creditors_with_cnpj(session)
        cps = _counterparties(session, [only_digits(c.cnpj_cpf) for c in creditors])
        spend = _spend_by_creditor(session)
        for c in creditors:
            cp = cps.get(only_digits(c.cnpj_cpf))
            if cp is None or not cp.sancoes:  # None/[] => não sancionado/não verificado
                continue
            tipos = ", ".join(
                f"{s.get('fonte')}:{s.get('tipo') or '?'}" for s in cp.sancoes[:3]
            )
            drafts.append(FindingDraft(
                rule_id=self.id, rule_version=self.version,
                dedup_key=dedup_key(self.id, c.id),
                severity=self.severity_default.value,
                exposed_amount=Money.of(spend.get(str(c.id), D(0))),
                title=f"Fornecedor com sanção ({tipos}): {c.name}",
                evidence=[EvidenceDraft("counterparty", "sancao", cp.cnpj,
                                        f"{c.name} — sanções: {cp.sancoes} (fonte {cp.source}, {cp.checked_at})")],
                reference_snapshot=_source_snap(cp),
            ))
        return drafts


# --------------------------------------------------------------------------- I2
class CnpjNotActiveRule:
    id = "I2"
    version = 1
    dimension = 4
    severity_default = Severity.HIGH
    default_params: dict = {}

    def evaluate(self, session: Session, ctx: RuleContext) -> list[FindingDraft]:
        drafts: list[FindingDraft] = []
        creditors = _creditors_with_cnpj(session)
        cps = _counterparties(session, [only_digits(c.cnpj_cpf) for c in creditors])
        spend = _spend_by_creditor(session)
        for c in creditors:
            cp = cps.get(only_digits(c.cnpj_cpf))
            if cp is None or cp.status != "ok" or not cp.situacao_cadastral:
                continue
            sit = cp.situacao_cadastral.upper()
            if sit in ("ATIVA", "NAO_ENCONTRADO"):
                continue
            exposed = spend.get(str(c.id), D(0))
            drafts.append(FindingDraft(
                rule_id=self.id, rule_version=self.version,
                dedup_key=dedup_key(self.id, c.id),
                severity=self.severity_default.value,
                exposed_amount=Money.of(exposed),
                title=f"Fornecedor com CNPJ {sit}: {c.name}",
                evidence=[EvidenceDraft("counterparty", "situacao_cadastral", cp.cnpj,
                                        f"{c.name} — situação {sit} (fonte {cp.source}, {cp.checked_at})")],
                reference_snapshot=_source_snap(cp),
            ))
        return drafts


# --------------------------------------------------------------------------- I3
class RecentHighValueSupplierRule:
    id = "I3"
    version = 1
    dimension = 4
    severity_default = Severity.MEDIUM
    default_params = {"max_age_months": 12, "min_spend": 50000}

    def evaluate(self, session: Session, ctx: RuleContext) -> list[FindingDraft]:
        months = int(ctx.params.get("max_age_months", 12))
        min_spend = D(str(ctx.params.get("min_spend", 50000)))
        cutoff = now_utc().replace(tzinfo=timezone.utc).timestamp() - months * 30 * 86400
        drafts: list[FindingDraft] = []
        creditors = _creditors_with_cnpj(session)
        cps = _counterparties(session, [only_digits(c.cnpj_cpf) for c in creditors])
        spend = _spend_by_creditor(session)
        for c in creditors:
            cp = cps.get(only_digits(c.cnpj_cpf))
            if cp is None or cp.status != "ok" or not cp.data_abertura:
                continue
            try:
                opened = datetime.fromisoformat(cp.data_abertura).replace(tzinfo=timezone.utc).timestamp()
            except ValueError:
                continue
            total = spend.get(str(c.id), D(0))
            if opened >= cutoff and total > min_spend:
                drafts.append(FindingDraft(
                    rule_id=self.id, rule_version=self.version,
                    dedup_key=dedup_key(self.id, c.id),
                    severity=self.severity_default.value,
                    exposed_amount=Money.of(total),
                    title=f"Empresa recém-aberta de alto valor: {c.name} (desde {cp.data_abertura})",
                    evidence=[EvidenceDraft("counterparty", "data_abertura", cp.cnpj,
                                            f"{c.name} aberta em {cp.data_abertura}; comprado {total}")],
                    reference_snapshot=_source_snap(cp),
                    config_snapshot={"max_age_months": months, "min_spend": str(min_spend)},
                ))
        return drafts


# --------------------------------------------------------------------------- I4
class CommonPartnerRule:
    id = "I4"
    version = 1
    dimension = 4
    severity_default = Severity.HIGH
    default_params: dict = {}

    def evaluate(self, session: Session, ctx: RuleContext) -> list[FindingDraft]:
        creditors = _creditors_with_cnpj(session)
        cps = _counterparties(session, [only_digits(c.cnpj_cpf) for c in creditors])
        # mapa doc-do-sócio -> conjunto de fornecedores
        by_socio: dict[str, list[Creditor]] = {}
        for c in creditors:
            cp = cps.get(only_digits(c.cnpj_cpf))
            if cp is None or cp.status != "ok" or not cp.qsa:
                continue
            for s in cp.qsa:
                doc = (s.get("doc") or "").strip()
                nome = (s.get("nome") or "").strip()
                key = doc or nome
                if key:
                    by_socio.setdefault(key, []).append(c)
        drafts: list[FindingDraft] = []
        seen: set[str] = set()
        for key, crs in by_socio.items():
            uniq = {str(c.id): c for c in crs}
            if len(uniq) < 2:
                continue
            ids = sorted(uniq)
            ddk = dedup_key(self.id, *ids)
            if ddk in seen:
                continue
            seen.add(ddk)
            names = ", ".join(c.name for c in uniq.values())
            drafts.append(FindingDraft(
                rule_id=self.id, rule_version=self.version, dedup_key=ddk,
                severity=self.severity_default.value, exposed_amount=None,
                title=f"Sócio em comum entre fornecedores: {names}",
                evidence=[EvidenceDraft("counterparty", "socio_comum", None,
                                        f"sócio em comum ({key}) entre: {names}")],
                reference_snapshot={"source": "brasilapi"},
            ))
        return drafts


# --------------------------------------------------------------------------- I5
class UnverifiedSupplierRule:
    id = "I5"
    version = 1
    dimension = 4
    severity_default = Severity.LOW
    default_params: dict = {}

    def evaluate(self, session: Session, ctx: RuleContext) -> list[FindingDraft]:
        drafts: list[FindingDraft] = []
        creditors = _creditors_with_cnpj(session)
        cps = _counterparties(session, [only_digits(c.cnpj_cpf) for c in creditors])
        spend = _spend_by_creditor(session)
        for c in creditors:
            cp = cps.get(only_digits(c.cnpj_cpf))
            if cp is not None and cp.status == "ok":
                continue  # verificado
            reason = "fonte indisponível" if cp else "ainda não consultado"
            drafts.append(FindingDraft(
                rule_id=self.id, rule_version=self.version,
                dedup_key=dedup_key(self.id, c.id),
                severity=self.severity_default.value,
                exposed_amount=Money.of(spend.get(str(c.id), D(0))),
                title=f"Fornecedor não verificado: {c.name}",
                evidence=[EvidenceDraft("creditor", "nao_verificado", str(c.id),
                                        f"{c.name}: integridade não confirmada ({reason}). NÃO assumir idôneo.")],
                reference_snapshot={"source": "integrity", "status": cp.status if cp else "ausente"},
            ))
        return drafts


def register_integrity_rules() -> None:
    for rule in (SanctionedSupplierRule(), CnpjNotActiveRule(),
                 RecentHighValueSupplierRule(), CommonPartnerRule(),
                 UnverifiedSupplierRule()):
        register(rule)
