"""Parser de NF-e contra XML 4.00 (estrutura real). Puro; XML defused (XXE-safe)."""

from __future__ import annotations

from app.connectors.upload.nfe import parse_nfe

NFE = """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
 <NFe><infNFe Id="NFe35200114200166000187550010000000071000000071" versao="4.00">
  <ide><nNF>7</nNF><serie>1</serie><dhEmi>2026-06-10T10:00:00-03:00</dhEmi><natOp>VENDA</natOp></ide>
  <emit><CNPJ>14200166000187</CNPJ><xNome>FORNECEDOR ABC LTDA</xNome></emit>
  <dest><CNPJ>11111111000111</CNPJ><xNome>CONSTRUTORA ZERO</xNome></dest>
  <det nItem="1"><prod><cProd>555</cProd><xProd>CIMENTO CP-II 50KG</xProd><NCM>25232910</NCM>
    <CFOP>5102</CFOP><uCom>SC</uCom><qCom>100.0000</qCom><vUnCom>40.0000</vUnCom><vProd>4000.00</vProd></prod></det>
  <det nItem="2"><prod><cProd>777</cProd><xProd>ACO CA-50 10MM</xProd><uCom>KG</uCom>
    <qCom>200.0000</qCom><vUnCom>6.0000</vUnCom><vProd>1200.00</vProd></prod></det>
  <total><ICMSTot><vProd>5200.00</vProd><vICMS>624.00</vICMS><vIPI>0.00</vIPI><vNF>5200.00</vNF></ICMSTot>
    <retTrib><vRetPrev>572.00</vRetPrev><vRetPIS>34.00</vRetPIS></retTrib></total>
 </infNFe></NFe></nfeProc>"""


def test_parse_nfe():
    d = parse_nfe(NFE)
    assert d["chave"] == "35200114200166000187550010000000071000000071"
    assert d["numero"] == "7" and d["serie"] == "1"
    assert d["emit_cnpj"] == "14200166000187"
    assert d["valor_total"] == "5200.00" and d["valor_produtos"] == "5200.00"
    assert d["retencoes"]["inss"] == "572.00"  # retenção previdenciária
    assert len(d["itens"]) == 2
    assert d["itens"][0]["codigo"] == "555" and d["itens"][0]["valor_total"] == "4000.00"


def test_parse_nfe_rejeita_xml_invalido():
    import pytest

    with pytest.raises(ValueError):
        parse_nfe("<x><y/></x>")
