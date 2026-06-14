"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { AppShell } from "@/components/shell";
import { Button, Card, Money, SeverityBadge, Spinner, Stat } from "@/components/ui";
import { RULE_NAMES, type Finding, type MonthlyReport } from "@/lib/types";

export default function DashboardPage() {
  const ready = useRequireAuth();
  const [report, setReport] = useState<MonthlyReport | null>(null);
  const [top, setTop] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [r, f] = await Promise.all([
        api.monthlyReport(),
        api.listFindings({ status: "open", limit: "5" }),
      ]);
      setReport(r);
      setTop(f);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (ready) void load();
  }, [ready, load]);

  async function runRules() {
    setRunning(true);
    try {
      await api.runRules();
      await load();
    } finally {
      setRunning(false);
    }
  }

  if (!ready) return null;

  return (
    <AppShell>
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Visão geral</h1>
        <Button onClick={runRules} disabled={running} variant="secondary">
          {running ? "Auditando…" : "Rodar auditoria agora"}
        </Button>
      </div>

      {loading ? (
        <div className="mt-8">
          <Spinner />
        </div>
      ) : (
        <>
          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Stat
              label="R$ exposto (aberto)"
              value={<Money value={report?.numbers.exposed_open ?? "0"} />}
              hint="potencial bruto em achados abertos"
            />
            <Stat
              label="R$ validado"
              value={<Money value={report?.numbers.validated ?? "0"} />}
              hint={`período ${report?.numbers.period ?? "—"}`}
            />
            <Stat label="Achados abertos" value={report?.numbers.open_findings ?? 0} />
          </div>

          <Card className="mt-6 p-5">
            <h2 className="text-sm font-medium text-ink-soft">Resumo executivo</h2>
            <p className="mt-2 text-ink">{report?.summary}</p>
          </Card>

          <div className="mt-6 flex items-center justify-between">
            <h2 className="font-medium">Prioridades</h2>
            <Link href="/findings" className="text-sm text-brand hover:underline">
              ver todos →
            </Link>
          </div>
          <Card className="mt-2 divide-y divide-surface-line">
            {top.length === 0 && <div className="p-5 text-sm text-ink-faint">Nenhum achado aberto.</div>}
            {top.map((f) => (
              <Link key={f.id} href={`/findings/${f.id}`} className="flex items-center justify-between p-4 hover:bg-surface-alt">
                <div className="flex items-center gap-3">
                  <SeverityBadge severity={f.severity} />
                  <div>
                    <div className="text-sm font-medium">{f.title ?? RULE_NAMES[f.rule_id] ?? f.rule_id}</div>
                    <div className="text-xs text-ink-faint">{RULE_NAMES[f.rule_id] ?? f.rule_id}</div>
                  </div>
                </div>
                <Money value={f.exposed_amount} />
              </Link>
            ))}
          </Card>
        </>
      )}
    </AppShell>
  );
}
