"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { AppShell } from "@/components/shell";
import { Card, Money, Spinner, Stat } from "@/components/ui";
import type { BillingSummary } from "@/lib/types";

export default function BillingPage() {
  const ready = useRequireAuth();
  const [data, setData] = useState<BillingSummary | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await api.billing());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (ready) void load();
  }, [ready, load]);

  if (!ready) return null;

  const used = data?.invoices_used ?? 0;
  const limit = data?.invoice_limit ?? 0;
  const pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0;
  const over = (data?.overage_units ?? 0) > 0;

  return (
    <AppShell>
      <h1 className="text-xl font-semibold">Cobrança</h1>
      <p className="mt-1 text-sm text-ink-soft">
        Fatura do período calculada pelo uso real: mensalidade base + excedente por nota acima do
        limite do plano.
      </p>

      {loading ? (
        <div className="mt-8"><Spinner /></div>
      ) : !data ? (
        <div className="mt-8 text-sm text-ink-faint">Sem dados de cobrança.</div>
      ) : !data.plan ? (
        <Card className="mt-6 p-5 text-sm text-ink-soft">
          Nenhum plano ativo. Fale com o administrador para ativar uma assinatura.
        </Card>
      ) : (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <Stat label="Plano" value={data.plan.name} hint={`período ${data.period}`} />
            <Stat
              label="Notas no período"
              value={`${used.toLocaleString("pt-BR")} / ${limit.toLocaleString("pt-BR")}`}
              hint={over ? `${data.overage_units.toLocaleString("pt-BR")} acima do limite` : "dentro do limite"}
            />
            <Stat label="Fatura projetada" value={<Money value={data.total} />} hint="estimativa do mês" />
          </div>

          {/* barra de uso */}
          <Card className="mt-4 p-5">
            <div className="flex items-center justify-between text-sm text-ink-soft">
              <span>Consumo de notas</span>
              <span>{pct}%</span>
            </div>
            <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-surface-alt">
              <div
                className={`h-full ${over ? "bg-sev-high" : "bg-brand"}`}
                style={{ width: `${over ? 100 : pct}%` }}
              />
            </div>
          </Card>

          {/* memória de cálculo */}
          <Card className="mt-4 overflow-hidden">
            <table className="w-full text-sm">
              <tbody className="divide-y divide-surface-line">
                <tr>
                  <td className="px-4 py-3 text-ink-soft">Mensalidade base</td>
                  <td className="px-4 py-3 text-right"><Money value={data.base_price} /></td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-ink-soft">
                    Excedente: {data.overage_units.toLocaleString("pt-BR")} nota(s) × <Money value={data.overage_price} />
                  </td>
                  <td className="px-4 py-3 text-right"><Money value={data.overage_amount} /></td>
                </tr>
                <tr className="bg-surface-alt font-semibold">
                  <td className="px-4 py-3">Total do período</td>
                  <td className="px-4 py-3 text-right"><Money value={data.total} /></td>
                </tr>
              </tbody>
            </table>
          </Card>
        </>
      )}
    </AppShell>
  );
}
