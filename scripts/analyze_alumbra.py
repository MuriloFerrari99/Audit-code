"""Analisador standalone (stdlib only) — roda as regras sobre o dado REAL do
Sienge da Alumbra sem Docker/Postgres/deps. Read-only.

Prova de valor: aplica a lógica de R1/R4/R5/R6/R2 em memória e imprime achados
com R$ e evidência. NÃO substitui o pipeline conteinerizado (que persiste,
versiona, rastreia) — é um dry-run para ver número real já.

Uso: python3 scripts/analyze_alumbra.py [max_pedidos]
"""

from __future__ import annotations

import base64
import json
import statistics
import sys
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = {}
for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        ENV[k.strip()] = v.strip()

SUB = ENV["SIENGE_DEFAULT_SUBDOMAIN"]
USER = ENV["SIENGE_DEFAULT_USER"]
PWD = ENV["SIENGE_DEFAULT_PASSWORD"]
HOST = "https://api.sienge.com.br"
V1 = f"{HOST}/{SUB}/public/api/v1"
BULK = f"{HOST}/{SUB}/public/api/bulk-data/v1"
AUTH = base64.b64encode(f"{USER}:{PWD}".encode()).decode()

BRL = lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Insumos que NÃO passam por cotação de material (serviço/mão de obra/etc.) —
# reduzem falso-positivo de R1/R6. Heurística por descrição (acento-insensível).
NON_MATERIAL = (
    "mao de obra", "m.o", "servico", "empreitada", "locacao", "aluguel",
    "alimentacao", "frete", "taxa", "imposto", "medicao", "terceiriz",
    "consultoria", "honorario", "comissao", "mensalidade", "manutencao",
    "transporte", "diaria", "hospedagem",
)
DISPERSION_MAX = 12  # se max/min do insumo > isto, é heterogêneo → mediana inválida


def _norm(s: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", (s or "").lower())
                   if not unicodedata.combining(c))


def is_non_material(desc: str) -> bool:
    n = _norm(desc)
    return any(k in n for k in NON_MATERIAL)


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {AUTH}"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode())


def rest_page(path: str, offset: int, limit: int = 200, extra: str = "") -> list:
    d = get(f"{V1}{path}?limit={limit}&offset={offset}{extra}")
    return d.get("results", []) if isinstance(d, dict) else d


def bulk_all(path: str, extra: str = "") -> list:
    d = get(f"{BULK}{path}?{extra}".rstrip("?"))
    return d.get("data", []) if isinstance(d, dict) else d


def main() -> None:
    max_orders = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    print(f"== Analisador Alumbra (dado real, read-only) — até {max_orders} pedidos ==\n")

    # ---- pedidos + itens ----
    print("Puxando pedidos e itens...", flush=True)
    orders = []
    off = 0
    while len(orders) < max_orders:
        page = rest_page("/purchase-orders", off)
        if not page:
            break
        orders.extend(page)
        off += 200
    orders = orders[:max_orders]

    by_resource = defaultdict(list)   # resourceId -> [(unitPrice, order, item)]
    order_items = {}                  # orderId -> [items]

    def fetch_items(o):
        try:
            return o, get(f"{V1}/purchase-orders/{o['id']}/items").get("results", [])
        except Exception:
            return o, []

    done = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        for o, items in pool.map(fetch_items, orders):
            order_items[o["id"]] = items
            for it in items:
                up = it.get("unitPrice")
                rid = it.get("resourceId")
                if up and rid:
                    by_resource[rid].append((up, o, it))
            done += 1
            if done % 200 == 0:
                print(f"  ...{done}/{len(orders)} pedidos", flush=True)

    findings = []

    # ---- R1 sobrepreço: preço > 10% acima da mediana do mesmo insumo (n>=3) ----
    for rid, obs in by_resource.items():
        prices = [p for p, _, _ in obs]
        if len(prices) < 3:
            continue
        med = statistics.median(prices)
        if med <= 0:
            continue
        # guarda de heterogeneidade: resourceId que mistura coisas diferentes
        # (preço varia ordens de grandeza) torna a mediana sem sentido -> pula.
        lo = min(p for p in prices if p > 0) if any(p > 0 for p in prices) else 0
        if lo > 0 and max(prices) / lo > DISPERSION_MAX:
            continue
        for up, o, it in obs:
            if is_non_material(it.get("resourceDescription", "")):
                continue
            if up > med * 1.10:
                qty = it.get("quantity") or 1
                exposed = (up - med) * qty
                if exposed >= 100:
                    findings.append(("R1 sobrepreço", exposed,
                                     f"pedido {o['id']} '{it.get('resourceDescription','')[:40]}' "
                                     f"pago {BRL(up)}/un vs mediana {BRL(med)} (n={len(prices)})"))

    # ---- R4 estouro de quantidade: medido > orçado (orçamento) ----
    print("Puxando orçamento (building-cost-estimation-items)...", flush=True)
    buildings = {o.get("buildingId") for o in orders if o.get("buildingId")}
    budget = []
    for b in list(buildings)[:40]:
        try:
            budget.extend(bulk_all("/building-cost-estimation-items", f"buildingId={b}"))
        except Exception:
            pass
    for bi in budget:
        q = bi.get("quantity")
        m = bi.get("measuredQuantity")
        up = bi.get("unitPrice") or 0
        if q and m and q > 0 and m > q * 1.05:
            exposed = (m - q) * up
            if exposed >= 100:
                findings.append(("R4 estouro qty", exposed,
                                 f"obra {bi.get('buildingId')} '{bi.get('description','')[:40]}' "
                                 f"medido {m} vs orçado {q}"))

    # ---- R5 divergência pedido->pagamento: título > pedido (via forecastBillId) ----
    print("Puxando títulos...", flush=True)
    bills = {}
    boff = 0
    while True:
        page = rest_page("/bills", boff, extra="&startDate=2024-01-01&endDate=2026-06-13")
        if not page:
            break
        for b in page:
            bills[b["id"]] = b
        boff += 200
        if boff > 12000:
            break
    for o in orders:
        fb = o.get("forecastBillId")
        tot = o.get("totalAmount")
        if fb and tot and fb in bills:
            paid = bills[fb].get("totalInvoiceAmount")
            if paid and paid > tot * 1.02:
                findings.append(("R5 divergência", paid - tot,
                                 f"pedido {o['id']} {BRL(tot)} vs título {fb} {BRL(paid)}"))

    # ---- R6 sem concorrência: pedido > 50k com <2 fornecedores cotando seus insumos ----
    print("Puxando cotações...", flush=True)
    quote_suppliers = defaultdict(set)  # productId -> {supplierId}
    quote_min_price = {}                 # productId -> menor unitPrice cotado
    quotes = bulk_all("/purchase-quotations", "startDate=2024-01-01&endDate=2026-06-13")
    for q in quotes:
        for sup in q.get("purchaseQuotationSuppliers") or []:
            sid = sup.get("supplierId")
            for neg in sup.get("negotiations") or []:
                for ni in neg.get("negotiationItems") or []:
                    pid = ni.get("productId")
                    up = ni.get("unitPrice")
                    if pid:
                        quote_suppliers[pid].add(sid)
                        if up and up > 0:  # ignora cotação placeholder R$ 0,00
                            quote_min_price[pid] = min(quote_min_price.get(pid, up), up)

    # ---- R2 cotação perdida: item do pedido pago acima da cotação mais barata ----
    for o in orders:
        for it in order_items.get(o["id"], []):
            rid = it.get("resourceId")
            up = it.get("unitPrice")
            best = quote_min_price.get(rid)
            if not (rid and up and best and best > 0 and up > best):
                continue
            if is_non_material(it.get("resourceDescription", "")):
                continue
            if up / best > 30:  # ratio absurdo = produto/unidade diferente, não sobrepreço
                continue
            qty = it.get("quantity") or 1
            exposed = (up - best) * qty
            if exposed >= 100:
                findings.append(("R2 cotação perdida", exposed,
                                 f"pedido {o['id']} '{it.get('resourceDescription','')[:38]}' "
                                 f"pago {BRL(up)}/un vs cotação {BRL(best)}"))
    for o in orders:
        if (o.get("totalAmount") or 0) <= 50000:
            continue
        items = order_items.get(o["id"], [])
        material = [it for it in items if not is_non_material(it.get("resourceDescription", ""))]
        if not material:
            continue  # pedido só de serviço/mão de obra/empreitada → não é "sem concorrência"
        rids = {it.get("resourceId") for it in material if it.get("resourceId")}
        suppliers = set()
        for rid in rids:
            suppliers |= quote_suppliers.get(rid, set())
        if len(suppliers) < 2:
            findings.append(("R6 sem concorrência", o.get("totalAmount", 0),
                             f"pedido {o['id']} {BRL(o['totalAmount'])} (material) com "
                             f"{len(suppliers)} fornecedor(es) cotando"))

    # ---- resumo ----
    print("\n" + "=" * 60)
    by_rule = defaultdict(lambda: [0, 0.0])
    for rule, exposed, _ in findings:
        by_rule[rule][0] += 1
        by_rule[rule][1] += exposed
    print("ACHADOS POR REGRA (amostra de", len(orders), "pedidos):")
    total = 0.0
    for rule, (n, val) in sorted(by_rule.items()):
        print(f"  {rule:22} {n:4} achados   {BRL(val)} exposto")
        total += val
    print(f"  {'TOTAL':22} {len(findings):4} achados   {BRL(total)} exposto")
    print("\nTOP 12 por R$ exposto:")
    for rule, exposed, ev in sorted(findings, key=lambda x: -x[1])[:12]:
        print(f"  [{rule.split()[0]}] {BRL(exposed):>16}  {ev}")
    print("\n(amostra parcial; quotações/datas em janela. Validação plena = pipeline conteinerizado.)")


if __name__ == "__main__":
    main()
