"""Higiene de Dados (sanitização do Sienge) — roda sobre o dado REAL, stdlib only.

Lista os lançamentos a checar/corrigir no Sienge, que (1) impedem auditoria e
(2) geram falso-positivo na origem. Read-only.

Uso: python3 scripts/quality_alumbra.py [max_pedidos]
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
E = {}
for ln in (ROOT / ".env").read_text().splitlines():
    if "=" in ln and not ln.strip().startswith("#"):
        k, v = ln.split("=", 1)
        E[k.strip()] = v.strip()
SUB, U, P = E["SIENGE_DEFAULT_SUBDOMAIN"], E["SIENGE_DEFAULT_USER"], E["SIENGE_DEFAULT_PASSWORD"]
A = base64.b64encode(f"{U}:{P}".encode()).decode()
V1 = f"https://api.sienge.com.br/{SUB}/public/api/v1"
BULK = f"https://api.sienge.com.br/{SUB}/public/api/bulk-data/v1"


def g(url):
    r = urllib.request.Request(url, headers={"Authorization": f"Basic {A}"})
    return json.loads(urllib.request.urlopen(r, timeout=40).read())


def rest(path, off, lim=200, extra=""):
    d = g(f"{V1}{path}?limit={lim}&offset={off}{extra}")
    return d.get("results", []) if isinstance(d, dict) else d


def bulk(path, extra=""):
    d = g(f"{BULK}{path}?{extra}".rstrip("?"))
    return d.get("data", []) if isinstance(d, dict) else d


def main():
    n_orders = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    print(f"== HIGIENE DE DADOS — Sienge/Alumbra (amostra {n_orders} pedidos) ==\n", flush=True)
    issues = defaultdict(lambda: {"n": 0, "ex": []})

    def add(code, msg):
        i = issues[code]
        i["n"] += 1
        if len(i["ex"]) < 5:
            i["ex"].append(msg)

    # ---- DQ6: fornecedor duplicado (mesmo CNPJ, ids diferentes) ----
    print("Lendo fornecedores...", flush=True)
    creditors, off = [], 0
    while True:
        page = rest("/creditors", off)
        if not page:
            break
        creditors += page
        off += 200
        if off > 6000:
            break
    by_cnpj = defaultdict(list)
    for c in creditors:
        cnpj = (c.get("cnpj") or "").strip()
        if cnpj:
            by_cnpj[cnpj].append(c.get("id"))
    for cnpj, ids in by_cnpj.items():
        if len(ids) > 1:
            add("DQ6 fornecedor duplicado", f"CNPJ {cnpj}: ids {ids}")

    # ---- DQ3: cotação com preço R$ 0 ----
    print("Lendo cotações...", flush=True)
    for q in bulk("/purchase-quotations", "startDate=2024-01-01&endDate=2026-06-13"):
        for s in q.get("purchaseQuotationSuppliers") or []:
            for ne in s.get("negotiations") or []:
                for ni in ne.get("negotiationItems") or []:
                    if (ni.get("unitPrice") or 0) <= 0:
                        add("DQ3 cotacao preco zero",
                            f"cotação {q.get('purchaseQuotationId')} produto {ni.get('productId')}")

    # ---- itens dos pedidos (DQ1 + DQ2) ----
    print("Lendo pedidos e itens...", flush=True)
    orders, off = [], 0
    while len(orders) < n_orders:
        page = rest("/purchase-orders", off)
        if not page:
            break
        orders += page
        off += 200
    orders = orders[:n_orders]
    by_res = defaultdict(list)

    def items_of(o):
        try:
            return o, g(f"{V1}/purchase-orders/{o['id']}/items").get("results", [])
        except Exception:
            return o, []

    with ThreadPoolExecutor(max_workers=6) as pool:
        for o, items in pool.map(items_of, orders):
            for it in items:
                rid, up = it.get("resourceId"), it.get("unitPrice")
                if not rid or up is None or up <= 0:
                    add("DQ1 item sem codigo/preco",
                        f"pedido {o['id']} '{(it.get('resourceDescription') or '')[:30]}'")
                if rid and up and up > 0:
                    by_res[rid].append((up, it.get("resourceDescription", "")))

    # DQ2: resourceId genérico (dispersão alta com amostra)
    for rid, obs in by_res.items():
        ps = [p for p, _ in obs]
        if len(ps) >= 5 and min(ps) > 0 and max(ps) / min(ps) > 12:
            add("DQ2 insumo generico (desmembrar)",
                f"resourceId {rid} '{obs[0][1][:28]}' varia {min(ps):.2f}–{max(ps):.2f} (n={len(ps)})")

    # ---- DQ5: orçamento sem medição em obra ativa ----
    print("Lendo orçamento...", flush=True)
    buildings = {o.get("buildingId") for o in orders if o.get("buildingId")}
    for b in list(buildings)[:25]:
        try:
            for bi in bulk("/building-cost-estimation-items", f"buildingId={b}"):
                if (bi.get("quantity") or 0) > 0 and bi.get("measuredQuantity") is None \
                   and bi.get("buildingStatus") == "IN_PROGRESS":
                    add("DQ5 orcamento sem medicao",
                        f"obra {b} '{(bi.get('description') or '')[:30]}' orçado {bi.get('quantity')}")
        except Exception:
            pass

    # ---- relatório ----
    print("\n" + "=" * 60)
    print("LANÇAMENTOS A CHECAR / CORRIGIR NO SIENGE:")
    total = 0
    for code in sorted(issues):
        i = issues[code]
        total += i["n"]
        print(f"\n  [{code}] — {i['n']} ocorrência(s)")
        for ex in i["ex"]:
            print(f"      · {ex}")
    print(f"\n  TOTAL: {total} lançamentos a higienizar (amostra parcial).")
    print("  Higienizar isto na origem reduz o ruído da auditoria e melhora a confiança dos achados.")


if __name__ == "__main__":
    main()
