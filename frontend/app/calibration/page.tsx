"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { AppShell } from "@/components/shell";
import { Button, Card, Spinner } from "@/components/ui";
import { RULE_NAMES, type CalibrationStat } from "@/lib/types";

export default function CalibrationPage() {
  const ready = useRequireAuth();
  const [data, setData] = useState<{ stats: CalibrationStat[]; suggestions: string[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await api.calibration());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (ready) void load();
  }, [ready, load]);

  async function recompute() {
    setRunning(true);
    try {
      setData(await api.calibrationRecompute());
    } finally {
      setRunning(false);
    }
  }

  if (!ready) return null;

  const pct = (n: number | null) => (n == null ? "—" : `${Math.round(n * 100)}%`);

  return (
    <AppShell>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Aprendizado por empresa</h1>
          <p className="mt-1 text-sm text-ink-soft">
            O sistema ajusta a confiança de cada regra conforme você aceita/descarta — para não te
            mostrar ruído. Sugestões de ajuste exigem sua aprovação.
          </p>
        </div>
        <Button onClick={recompute} disabled={running} variant="secondary">
          {running ? "Recalculando…" : "Recalcular"}
        </Button>
      </div>

      {loading ? (
        <div className="mt-8"><Spinner /></div>
      ) : !data ? (
        <div className="mt-8 text-sm text-ink-faint">Sem dados.</div>
      ) : (
        <>
          {data.suggestions.length > 0 && (
            <Card className="mt-5 p-5">
              <h2 className="text-sm font-medium text-ink-soft">Sugestões (você decide)</h2>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
                {data.suggestions.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </Card>
          )}

          <Card className="mt-5 overflow-hidden">
            {data.stats.length === 0 ? (
              <div className="p-5 text-sm text-ink-faint">
                Ainda sem revisões suficientes. Aceite/descarte achados para o sistema aprender.
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-surface-alt text-left text-ink-soft">
                  <tr>
                    <th className="px-4 py-2 font-medium">Regra</th>
                    <th className="px-4 py-2 font-medium">Revisões</th>
                    <th className="px-4 py-2 font-medium">Aceitos</th>
                    <th className="px-4 py-2 font-medium">Descartados</th>
                    <th className="px-4 py-2 font-medium">Taxa de aceite</th>
                    <th className="px-4 py-2 font-medium">Fator de confiança</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-line">
                  {data.stats.map((s) => (
                    <tr key={s.rule_id} className="hover:bg-surface-alt">
                      <td className="px-4 py-3">{RULE_NAMES[s.rule_id] ?? s.rule_id}</td>
                      <td className="px-4 py-3">{s.samples}</td>
                      <td className="px-4 py-3 text-ok">{s.accepted}</td>
                      <td className="px-4 py-3 text-ink-soft">{s.dismissed}</td>
                      <td className="px-4 py-3">{pct(s.acceptance_rate)}</td>
                      <td className="px-4 py-3 tabular-nums">{s.confidence_factor.toFixed(2)}×</td>
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
