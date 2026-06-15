"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { AppShell } from "@/components/shell";
import { Button, Card, Money, Spinner, Stat } from "@/components/ui";
import { ApiError } from "@/lib/api";
import type { BillingSummary, GainshareSummary } from "@/lib/types";

export default function BillingPage() {
  const ready = useRequireAuth();
  const [data, setData] = useState<BillingSummary | null>(null);
  const [gs, setGs] = useState<GainshareSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState<string | null>(null);

  async function activate(planCode: string) {
    setMsg(null);
    try {
      const { url } = await api.checkout(planCode);
      window.location.href = url;
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "não foi possível iniciar a assinatura");
    }
  }

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [me, st] = await Promise.all([api.billing(), api.statement()]);
      setData(me);
      setGs(st.gainshare);
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
          {msg && (
            <div className="mt-4 rounded-lg border border-sev-high/40 bg-sev-high/10 px-4 py-2 text-sm text-sev-high">
              {msg}
            </div>
          )}

          <div className="mt-4 flex items-center justify-between">
            <span className="text-sm text-ink-soft">
              Assinatura: <b>{data.subscription_status}</b>
            </span>
            {data.subscription_status !== "active" && (
              <Button variant="secondary" onClick={() => activate(data.plan!.code)}>
                Ativar assinatura
              </Button>
            )}
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-3">
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

          {/* gainshare — economia validada elegível (hard savings + cost avoidance) */}
          {gs && (
            <Card className="mt-6 p-5">
              <div className="flex items-center justify-between">
                <h2 className="font-medium">Gainshare — economia validada</h2>
                <span className="text-xs text-ink-faint">
                  regras elegíveis: {gs.eligible_rules.join(", ")}
                </span>
              </div>
              <p className="mt-1 text-xs text-ink-soft">
                Soma dos achados aceitos elegíveis (governança fica fora da fatura).
              </p>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <Stat label="Base de gainshare (aceito)" value={<Money value={gs.base} />} />
                <Stat
                  label="Gainshare a faturar"
                  value={
                    gs.gainshare_amount != null ? <Money value={gs.gainshare_amount} /> : "% a definir"
                  }
                  hint={gs.gainshare_pct != null ? `${(Number(gs.gainshare_pct) * 100).toFixed(1)}% da base` : "defina o % do plano"}
                />
              </div>
              {Object.keys(gs.by_rule).length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {Object.entries(gs.by_rule).map(([rule, amt]) => (
                    <span key={rule} className="rounded-full bg-surface-alt px-3 py-1 text-xs text-ink-soft">
                      {rule}: <Money value={amt} />
                    </span>
                  ))}
                </div>
              )}
            </Card>
          )}
        </>
      )}
    </AppShell>
  );
}
