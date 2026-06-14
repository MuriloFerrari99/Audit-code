"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { AppShell } from "@/components/shell";
import { Card, ConfidenceBadge, Money, SeverityBadge, Spinner, StatusBadge } from "@/components/ui";
import { DIMENSION_LABELS, RULE_DIMENSION, RULE_NAMES, type Finding } from "@/lib/types";

const STATUS_OPTS = ["open", "accepted", "dismissed", "escalated", "resolved"];

export default function FindingsPage() {
  const ready = useRequireAuth();
  const [items, setItems] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState("open");
  const [rule, setRule] = useState("");
  const [dim, setDim] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = { limit: "200" };
      if (status) params.status = status;
      if (rule) params.rule_id = rule;
      setItems(await api.listFindings(params));
    } finally {
      setLoading(false);
    }
  }, [status, rule]);

  useEffect(() => {
    if (ready) void load();
  }, [ready, load]);

  if (!ready) return null;

  return (
    <AppShell>
      <h1 className="text-xl font-semibold">Achados</h1>

      <div className="mt-4 flex flex-wrap gap-3">
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="rounded-lg border border-surface-line bg-surface px-3 py-2 text-sm"
        >
          <option value="">Todos os status</option>
          {STATUS_OPTS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select
          value={dim}
          onChange={(e) => setDim(e.target.value)}
          className="rounded-lg border border-surface-line bg-surface px-3 py-2 text-sm"
        >
          <option value="">Todas as dimensões</option>
          {Object.entries(DIMENSION_LABELS).map(([id, name]) => (
            <option key={id} value={id}>
              {name}
            </option>
          ))}
        </select>
        <select
          value={rule}
          onChange={(e) => setRule(e.target.value)}
          className="rounded-lg border border-surface-line bg-surface px-3 py-2 text-sm"
        >
          <option value="">Todas as regras</option>
          {Object.entries(RULE_NAMES).map(([id, name]) => (
            <option key={id} value={id}>
              {id} — {name}
            </option>
          ))}
        </select>
      </div>

      <Card className="mt-4 overflow-hidden">
        {loading ? (
          <div className="p-5">
            <Spinner />
          </div>
        ) : (() => {
          const shown = dim ? items.filter((f) => String(RULE_DIMENSION[f.rule_id]) === dim) : items;
          return shown.length === 0 ? (
            <div className="p-5 text-sm text-ink-faint">Nenhum achado com esses filtros.</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-surface-alt text-left text-ink-soft">
                <tr>
                  <th className="px-4 py-2 font-medium">Severidade</th>
                  <th className="px-4 py-2 font-medium">Achado</th>
                  <th className="px-4 py-2 font-medium">Regra</th>
                  <th className="px-4 py-2 font-medium">Confiança</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                  <th className="px-4 py-2 text-right font-medium">R$ exposto</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-line">
                {shown.map((f) => (
                  <tr key={f.id} className="hover:bg-surface-alt">
                    <td className="px-4 py-3">
                      <SeverityBadge severity={f.severity} />
                    </td>
                    <td className="px-4 py-3">
                      <Link href={`/findings/${f.id}`} className="text-brand hover:underline">
                        {f.title ?? "(sem título)"}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-ink-soft">{RULE_NAMES[f.rule_id] ?? f.rule_id}</td>
                    <td className="px-4 py-3"><ConfidenceBadge value={f.confidence} /></td>
                    <td className="px-4 py-3">
                      <StatusBadge status={f.status} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Money value={f.exposed_amount} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          );
        })()}
      </Card>
    </AppShell>
  );
}
