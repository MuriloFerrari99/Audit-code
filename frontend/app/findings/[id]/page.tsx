"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { AppShell } from "@/components/shell";
import { Button, Card, Money, SeverityBadge, Spinner, StatusBadge } from "@/components/ui";
import { RULE_NAMES, type Finding } from "@/lib/types";

export default function FindingDetailPage() {
  const ready = useRequireAuth();
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [finding, setFinding] = useState<Finding | null>(null);
  const [dossier, setDossier] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const f = await api.getFinding(params.id);
      setFinding(f);
      api.dossier(params.id).then(setDossier).catch(() => setDossier(null));
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => {
    if (ready) void load();
  }, [ready, load]);

  async function review(decision: string) {
    setActing(true);
    try {
      const updated = await api.reviewFinding(params.id, decision);
      setFinding(updated);
    } finally {
      setActing(false);
    }
  }

  if (!ready) return null;

  return (
    <AppShell>
      <button onClick={() => router.back()} className="text-sm text-ink-soft hover:text-ink">
        ← voltar
      </button>

      {loading || !finding ? (
        <div className="mt-6">
          <Spinner />
        </div>
      ) : (
        <>
          <div className="mt-4 flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3">
                <SeverityBadge severity={finding.severity} />
                <StatusBadge status={finding.status} />
                <span className="text-xs text-ink-faint">{RULE_NAMES[finding.rule_id] ?? finding.rule_id}</span>
              </div>
              <h1 className="mt-2 text-xl font-semibold">{finding.title}</h1>
            </div>
            <div className="text-right">
              <div className="text-xs text-ink-soft">R$ exposto</div>
              <div className="text-2xl font-semibold">
                <Money value={finding.exposed_amount} />
              </div>
            </div>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2 space-y-6">
              <Card className="p-5">
                <h2 className="text-sm font-medium text-ink-soft">Evidência</h2>
                <ul className="mt-3 space-y-3">
                  {finding.evidence.map((e, i) => (
                    <li key={i} className="rounded-lg border border-surface-line p-3">
                      <div className="text-xs font-medium uppercase tracking-wide text-brand">{e.role}</div>
                      <div className="mt-1 text-sm text-ink">{e.snippet}</div>
                      <div className="mt-1 text-xs text-ink-faint">{e.entity_type}</div>
                    </li>
                  ))}
                  {finding.evidence.length === 0 && (
                    <li className="text-sm text-ink-faint">Sem evidência anexada.</li>
                  )}
                </ul>
              </Card>

              {dossier?.narrative ? (
                <Card className="p-5">
                  <h2 className="text-sm font-medium text-ink-soft">Análise (Investigador)</h2>
                  <p className="mt-2 whitespace-pre-wrap text-sm text-ink">{String(dossier.narrative)}</p>
                </Card>
              ) : null}
            </div>

            <div className="space-y-4">
              <Card className="p-5">
                <h2 className="text-sm font-medium text-ink-soft">Revisão</h2>
                <p className="mt-1 text-xs text-ink-faint">
                  Advisory — a decisão é sua. Aceitar registra o valor no ledger de gainshare.
                </p>
                <div className="mt-4 grid grid-cols-1 gap-2">
                  <Button onClick={() => review("accept")} disabled={acting}>
                    Aceitar
                  </Button>
                  <Button onClick={() => review("dismiss")} disabled={acting} variant="secondary">
                    Descartar
                  </Button>
                  <Button onClick={() => review("escalate")} disabled={acting} variant="ghost">
                    Escalar
                  </Button>
                </div>
              </Card>

              <Card className="p-5">
                <h2 className="text-sm font-medium text-ink-soft">Referência</h2>
                <pre className="mt-2 overflow-x-auto text-xs text-ink-soft">
                  {JSON.stringify((dossier?.finding as Record<string, unknown>)?.reference ?? {}, null, 2)}
                </pre>
              </Card>
            </div>
          </div>
        </>
      )}
    </AppShell>
  );
}
