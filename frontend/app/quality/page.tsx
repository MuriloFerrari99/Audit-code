"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { AppShell } from "@/components/shell";
import { Card, Spinner } from "@/components/ui";
import type { QualityIssue } from "@/lib/types";

const CODE_LABEL: Record<string, string> = {
  DQ1: "Item sem código/preço",
  DQ2: "Insumo genérico (desmembrar)",
  DQ3: "Cotação com preço R$ 0",
  DQ5: "Orçamento sem medição",
  DQ6: "Fornecedor duplicado",
};

export default function QualityPage() {
  const ready = useRequireAuth();
  const [data, setData] = useState<{ total: number; by_code: Record<string, number>; issues: QualityIssue[] } | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await api.quality());
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
      <h1 className="text-xl font-semibold">Higiene de Dados</h1>
      <p className="mt-1 text-sm text-ink-soft">
        Lançamentos a checar/corrigir no Sienge — corrigir na origem reduz o ruído da auditoria.
      </p>

      {loading ? (
        <div className="mt-8"><Spinner /></div>
      ) : !data ? (
        <div className="mt-8 text-sm text-ink-faint">Sem dados.</div>
      ) : (
        <>
          <div className="mt-5 flex flex-wrap gap-2">
            {Object.entries(data.by_code).map(([code, n]) => (
              <span key={code} className="rounded-full bg-surface-alt px-3 py-1 text-sm">
                {CODE_LABEL[code] ?? code}: <b>{n}</b>
              </span>
            ))}
            <span className="rounded-full bg-brand-muted px-3 py-1 text-sm text-brand">
              Total: <b>{data.total}</b>
            </span>
          </div>

          <Card className="mt-5 overflow-hidden">
            {data.issues.length === 0 ? (
              <div className="p-5 text-sm text-ink-faint">Nenhum problema de dado encontrado. 🎉</div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-surface-alt text-left text-ink-soft">
                  <tr>
                    <th className="px-4 py-2 font-medium">Tipo</th>
                    <th className="px-4 py-2 font-medium">Lançamento</th>
                    <th className="px-4 py-2 font-medium">Ação recomendada</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-line">
                  {data.issues.map((i, idx) => (
                    <tr key={idx} className="hover:bg-surface-alt">
                      <td className="px-4 py-3 text-ink-soft">{CODE_LABEL[i.code] ?? i.code}</td>
                      <td className="px-4 py-3">{i.message}</td>
                      <td className="px-4 py-3 text-ink-soft">{i.action}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </>
      )}
    </AppShell>
  );
}
