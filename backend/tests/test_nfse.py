"""Fase 1 — NFS-e (ABRASF): parser tolerante + carga no MESMO canônico.

Sobe uma NFS-e de serviço (ISS não retido, sem INSS), confirma is_service e que
o upload auto-detecta NF-e vs NFS-e e dispara as regras de retenção.
"""

from __future__ import annotations

import contextlib

import pytest
from sqlalchemy import text

from app.connectors.upload.load import load_nfe_files
from app.connectors.upload.nfse import looks_like_nfse, parse_nfse
from app.core.db import tenant_session
from app.findings.service import list_findings
from app.rules.engine import run_all
from app.rules.retention_rules import register_retention_rules
from scripts.seed_synthetic import TENANT_ID, seed

# ABRASF com namespace e aninhamento típicos; IssRetido=2 (não retido), sem INSS.
NFSE = """<?xml version="1.0" encoding="UTF-8"?>
<ConsultarNfseResposta xmlns="http://www.abrasf.org.br/nfse.xsd">
 <ListaNfse><CompNfse><Nfse><InfNfse>
  <Numero>4321</Numero>
  <CodigoVerificacao>XK7P-22</CodigoVerificacao>
  <DataEmissao>2026-05-12T09:30:00</DataEmissao>
  <Servico>
    <Valores>
      <ValorServicos>12000.00</ValorServicos>
      <ValorIss>600.00</ValorIss>
      <IssRetido>2</IssRetido>
      <Aliquota>5.00</Aliquota>
    </Valores>
    <ItemListaServico>0701</ItemListaServico>
    <Discriminacao>Servico de engenharia consultiva</Discriminacao>
    <CodigoMunicipio>3550308</CodigoMunicipio>
  </Servico>
  <PrestadorServico>
    <IdentificacaoPrestador><Cnpj>14200166000187</Cnpj></IdentificacaoPrestador>
    <RazaoSocial>Engenharia Consultiva LTDA</RazaoSocial>
  </PrestadorServico>
 </InfNfse></Nfse></CompNfse></ListaNfse>
</ConsultarNfseResposta>"""


@pytest.fixture(scope="module", autouse=True)
def _register():
    with contextlib.suppress(ValueError):
        register_retention_rules()


@pytest.fixture
def seeded():
    return seed()


def test_parse_nfse_pure():
    d = parse_nfse(NFSE.encode())
    assert d["numero"] == "4321"
    assert d["chave"] == "4321-XK7P-22"
    assert d["emit_cnpj"] == "14200166000187"
    assert d["valor_total"] == "12000.00"
    assert d["retencoes"]["iss"] is None  # IssRetido=2 -> não retido
    assert d["itens"][0]["codigo"] == "0701"


def test_looks_like_nfse():
    assert looks_like_nfse(NFSE.encode()) is True
    assert looks_like_nfse(b"<nfeProc><infNFe/></nfeProc>") is False


def test_upload_autodetects_and_loads_nfse(seeded):
    summary = load_nfe_files(str(TENANT_ID), [("servico.xml", NFSE.encode())])
    assert summary["invoices"] == 1
    assert summary["dead_letters"] == 0
    with tenant_session(str(TENANT_ID)) as s:
        inv = s.execute(
            text("SELECT is_service, total_invoiced FROM invoice WHERE nfe_key = :k"),
            {"k": "4321-XK7P-22"},
        ).one()
        assert inv.is_service is True
        assert inv.total_invoiced == 12000


def test_nfse_triggers_retention_rules(seeded):
    load_nfe_files(str(TENANT_ID), [("servico.xml", NFSE.encode())])
    with tenant_session(str(TENANT_ID)) as s:
        run_all(s, str(TENANT_ID))
    with tenant_session(str(TENANT_ID)) as s:
        rules = {f.rule_id for f in list_findings(s, limit=1000)}
    assert "RET1" in rules  # INSS não retido
    assert "RET2" in rules  # ISS não retido
