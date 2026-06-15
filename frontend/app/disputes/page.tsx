"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { AppShell } from "@/components/shell";
import { Card, Spinner } from "@/components/ui";
import type { DisputeRow } from "@/lib/types";

const STATUS_LABEL: Record<string, string> = {
  draft: "Rascunho",
  erp_blocked: "Pagamento bloqueado",
  email_sent: "Contestação enviada",
  resolved: "Resolvida",
  rejected: "Rejeitada",
  failed: "Falhou",
};

function badge(status: string) {
  const cls =
    status === "erp_blocked" || status === "email_sent"
      ? "bg-ok/10 text-ok"
      : status === "failed" || status === "rejected"
        ? "bg-sev-critical/10 text-sev-critical"
        : "bg-surface-alt text-ink-soft";
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs ${cls}`}>
      {STATUS_LABEL[status] ?? status}
    </span>
  );
}

export default function DisputesPage() {
  const ready = useRequireAuth();
  const [rows, setRows] = useState<DisputeRow[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows((await api.disputesList()).disputes);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (ready) void load();
  }, [ready, load]);

  if (!ready) return null;

  return (
    <AppShell>
      <h1 className="text-xl font-semibold">Disputas</h1>
      <p className="mt-1 text-sm text-ink-soft">
        Ações de mitigação do Agente Executor (bloqueio no ERP / contestação). Ação externa só
        com opt-in do tenant; senão fica em rascunho.
      </p>

      {loading ? (
        <div className="mt-8"><Spinner /></div>
      ) : rows.length === 0 ? (
        <Card className="mt-6 p-5 text-sm text-ink-faint">Nenhuma disputa registrada.</Card>
      ) : (
        <Card className="mt-6 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-surface-alt text-left text-ink-soft">
              <tr>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Canal</th>
                <th className="px-4 py-2 font-medium">Ação</th>
                <th className="px-4 py-2 font-medium">Referência</th>
                <th className="px-4 py-2 font-medium">Achado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-line">
              {rows.map((d) => (
                <tr key={d.id} className="hover:bg-surface-alt">
                  <td className="px-4 py-3">{badge(d.status)}</td>
                  <td className="px-4 py-3 text-ink-soft">{d.channel ?? "—"}</td>
                  <td className="px-4 py-3 text-ink-soft">{d.erp_action ?? "—"}</td>
                  <td className="px-4 py-3 font-mono text-xs text-ink-faint">{d.erp_ref ?? d.recipient ?? "—"}</td>
                  <td className="px-4 py-3 font-mono text-xs text-ink-faint">
                    {d.finding_id ? d.finding_id.slice(0, 8) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </AppShell>
  );
}
