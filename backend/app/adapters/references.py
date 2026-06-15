"""Adapter BR/Construção do ReferencePriceProvider (Port).

Envolve a cascata já existente (app/rules/references): SINAPI regional -> mediana
intra-tenant por código de insumo. Construído por execução com a sessão do tenant
ativa (RLS) e a UF da obra. Outros países/setores entram como novos adapters
(ex.: RSMeansProvider) sem tocar o Enriquecedor.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.ports.reference import PriceReference
from app.rules.references import _sinapi_reference, resolve_price_reference


class BrazilSinapiProvider:
    """ReferencePriceProvider para country=BR, industry=construction."""

    def __init__(self, session: Session, state: str | None = None) -> None:
        self.session = session
        self.state = state

    def resolve(self, *, code: str | None, description: str, country: str,
                industry: str) -> PriceReference | None:
        if country != "BR" or industry != "construction" or not code:
            return None
        # 1) SINAPI (código tratado como sinapi_code); 2) mediana intra-tenant por insumo
        ref = _sinapi_reference(self.session, code, self.state) or resolve_price_reference(
            self.session, catalog_item_id=None, state=self.state, resource_code=code
        )
        if ref is None:
            return None
        snap = ref.snapshot or {}
        return PriceReference(
            unit_price=ref.value,
            source=str(snap.get("source", ref.layer)),
            layer=snap.get("layer"),
            sample_size=snap.get("n"),
        )


class RSMeansProvider:
    """ReferencePriceProvider para country=US, industry=construction (RSMeans).

    Skeleton da expansão multi-país: prova que acoplar um novo país é só um novo
    adapter — Core/Enricher/Runner não mudam. A ingestão da base US entra depois;
    por ora resolve None (sem lastro), registrado no prontuário como 'skipped'.
    """

    def __init__(self, session: Session, state: str | None = None) -> None:
        self.session = session
        self.state = state

    def resolve(self, *, code: str | None, description: str, country: str,
                industry: str) -> PriceReference | None:
        return None  # base RSMeans ainda não ingerida (P6+)


def get_reference_provider(session: Session, country: str, industry: str,
                          state: str | None = None):
    """Seleciona o provider de preço por país/setor do tenant (hexágono).

    Acoplar um novo mercado = adicionar um ramo aqui; nada no Core muda.
    """
    if industry != "construction":
        return None
    if country == "BR":
        return BrazilSinapiProvider(session, state)
    if country == "US":
        return RSMeansProvider(session, state)
    return None
