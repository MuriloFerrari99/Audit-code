"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { AppShell } from "@/components/shell";
import { Card, Spinner } from "@/components/ui";
import type { ReasoningLog } from "@/lib/types";

const AGENT_LABEL: Record<string, string> = {
  extractor: "Extrator",
  enricher: "Enriquecedor",
  auditor: "Auditor",
  executor: "Executor",
};

function StatusDot({ status }: { status: string }) {
  const cls =
    status === "ok" ? "bg-ok" : status === "skipped" ? "bg-sev-medium" : status === "failed" ? "bg-sev-critical" : "bg-ink-faint";
  return <span className={`inline-block h-2 w-2 rounded-full ${cls}`} />;
}

export default function AgentsPage() {
  const ready = useRequireAuth();
  const [logs, setLogs] = useState<ReasoningLog[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setLogs((await api.reasoning()).logs);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (ready) void load();
  }, [ready, load]);

  if (!ready) return null;

  // agrupa por run_id, preservando ordem (mais recente primeiro)
  const runs: { run_id: string; logs: ReasoningLog[] }[] = [];
  const idx = new Map<string, number>();
  for (const l of logs) {
    if (!idx.has(l.run_id)) {
      idx.set(l.run_id, runs.length);
      runs.push({ run_id: l.run_id, logs: [] });
    }
    runs[idx.get(l.run_id)!].logs.push(l);
  }

  return (
    <AppShell>
      <h1 className="text-xl font-semibold">Prontuário agêntico</h1>
      <p className="mt-1 text-sm text-ink-soft">
        Raciocínio passo a passo do squad (explicabilidade auditável), agrupado por execução.
      </p>

      {loading ? (
        <div className="mt-8"><Spinner /></div>
      ) : runs.length === 0 ? (
        <Card className="mt-6 p-5 text-sm text-ink-faint">
          Nenhuma execução ainda. Envie documentos para o squad auditar.
        </Card>
      ) : (
        <div className="mt-6 space-y-4">
          {runs.map((run) => (
            <Card key={run.run_id} className="p-5">
              <div className="mb-3 flex items-center justify-between">
                <span className="font-mono text-xs text-ink-faint">run {run.run_id.slice(0, 8)}</span>
                <span className="text-xs text-ink-faint">
                  {run.logs[run.logs.length - 1]?.created_at?.slice(0, 19).replace("T", " ")}
                </span>
              </div>
              <ol className="space-y-3">
                {[...run.logs].reverse().map((l) => (
                  <li key={l.id} className="border-l-2 border-surface-line pl-3">
                    <div className="flex items-center gap-2 text-sm">
                      <StatusDot status={l.status} />
                      <b>{AGENT_LABEL[l.agent_name] ?? l.agent_name}</b>
                      {l.confidence && (
                        <span className="text-xs text-ink-faint">conf. {Number(l.confidence).toFixed(2)}</span>
                      )}
                    </div>
                    {l.reasoning && <div className="mt-1 text-sm text-ink-soft">{l.reasoning}</div>}
                    {l.citations && l.citations.length > 0 && (
                      <ul className="mt-1 list-disc pl-5 text-xs text-ink-faint">
                        {l.citations.map((c, i) => <li key={i}>{c}</li>)}
                      </ul>
                    )}
                  </li>
                ))}
              </ol>
            </Card>
          ))}
        </div>
      )}
    </AppShell>
  );
}
