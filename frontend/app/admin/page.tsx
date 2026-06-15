"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { AppShell } from "@/components/shell";
import { Card, Money, Spinner } from "@/components/ui";
import type { AdminPlan, AdminTenant } from "@/lib/types";

export default function AdminPage() {
  const ready = useRequireAuth();
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [tenants, setTenants] = useState<AdminTenant[]>([]);
  const [plans, setPlans] = useState<AdminPlan[]>([]);
  const [period, setPeriod] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const me = await api.me();
      if (!me.is_platform_admin) {
        setAllowed(false);
        return;
      }
      setAllowed(true);
      const [t, p] = await Promise.all([api.adminTenants(), api.adminPlans()]);
      setTenants(t.tenants);
      setPeriod(t.period);
      setPlans(p.plans);
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "erro ao carregar");
      setAllowed(false);
    }
  }, []);

  useEffect(() => {
    if (ready) void load();
  }, [ready, load]);

  async function changePlan(tenantId: string, planCode: string) {
    setMsg(null);
    try {
      await api.adminSetPlan(tenantId, planCode);
      await load();
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "falha ao trocar plano");
    }
  }

  if (!ready) return null;
  if (allowed === null) return <AppShell><div className="mt-8"><Spinner /></div></AppShell>;
  if (!allowed)
    return (
      <AppShell>
        <h1 className="text-xl font-semibold">Admin</h1>
        <Card className="mt-6 p-5 text-sm text-ink-soft">Acesso restrito à equipe da plataforma.</Card>
      </AppShell>
    );

  return (
    <AppShell>
      <h1 className="text-xl font-semibold">Admin — plataforma</h1>
      <p className="mt-1 text-sm text-ink-soft">
        Tenants, plano, uso e fatura projetada do período {period}.
      </p>

      {msg && (
        <div className="mt-4 rounded-lg border border-sev-high/40 bg-sev-high/10 px-4 py-2 text-sm text-sev-high">
          {msg}
        </div>
      )}

      <Card className="mt-6 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-surface-alt text-left text-ink-soft">
            <tr>
              <th className="px-4 py-2 font-medium">Tenant</th>
              <th className="px-4 py-2 font-medium">Plano</th>
              <th className="px-4 py-2 font-medium">Assinatura</th>
              <th className="px-4 py-2 font-medium text-right">Notas</th>
              <th className="px-4 py-2 font-medium text-right">Fatura</th>
              <th className="px-4 py-2 font-medium">Trocar plano</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-line">
            {tenants.map((t) => {
              const over = t.invoice_limit != null && t.invoices_used > t.invoice_limit;
              return (
                <tr key={t.tenant_id} className="hover:bg-surface-alt">
                  <td className="px-4 py-3">{t.name}</td>
                  <td className="px-4 py-3 text-ink-soft">{t.plan_code ?? "—"}</td>
                  <td className="px-4 py-3 text-ink-soft">{t.subscription_status}</td>
                  <td className={`px-4 py-3 text-right tabular-nums ${over ? "text-sev-high font-medium" : ""}`}>
                    {t.invoices_used.toLocaleString("pt-BR")}
                    {t.invoice_limit != null && <span className="text-ink-faint"> / {t.invoice_limit.toLocaleString("pt-BR")}</span>}
                  </td>
                  <td className="px-4 py-3 text-right"><Money value={t.total} /></td>
                  <td className="px-4 py-3">
                    <select
                      defaultValue={t.plan_code ?? ""}
                      onChange={(e) => e.target.value && changePlan(t.tenant_id, e.target.value)}
                      className="rounded-lg border border-surface-line bg-surface px-2 py-1 text-sm"
                    >
                      <option value="">selecionar…</option>
                      {plans.map((p) => (
                        <option key={p.code} value={p.code}>{p.name}</option>
                      ))}
                    </select>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
    </AppShell>
  );
}
