"use client";

import type { ReactNode } from "react";
import type { FindingStatus, Severity } from "@/lib/types";

// --- Design system base (sincronizável com Claude Design) -------------------

export function Button({
  children,
  variant = "primary",
  ...props
}: {
  children: ReactNode;
  variant?: "primary" | "secondary" | "ghost" | "danger";
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const styles: Record<string, string> = {
    primary: "bg-brand text-brand-fg hover:opacity-90",
    secondary: "bg-surface border border-surface-line text-ink hover:bg-surface-alt",
    ghost: "text-brand hover:bg-brand-muted",
    danger: "bg-sev-critical text-white hover:opacity-90",
  };
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium transition disabled:opacity-50 ${styles[variant]} ${props.className ?? ""}`}
    >
      {children}
    </button>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-card bg-surface shadow-card border border-surface-line ${className}`}>
      {children}
    </div>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <Card className="p-5">
      <div className="text-sm text-ink-soft">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-ink">{value}</div>
      {hint && <div className="mt-1 text-xs text-ink-faint">{hint}</div>}
    </Card>
  );
}

const SEV_LABEL: Record<Severity, string> = {
  critical: "Crítica",
  high: "Alta",
  medium: "Média",
  low: "Baixa",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  const color: Record<Severity, string> = {
    critical: "bg-sev-critical",
    high: "bg-sev-high",
    medium: "bg-sev-medium",
    low: "bg-sev-low",
  };
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium text-white ${color[severity]}`}>
      {SEV_LABEL[severity]}
    </span>
  );
}

const STATUS_LABEL: Record<FindingStatus, string> = {
  open: "Aberto",
  accepted: "Aceito",
  dismissed: "Descartado",
  escalated: "Escalado",
  resolved: "Resolvido",
  superseded: "Substituído",
};

export function StatusBadge({ status }: { status: FindingStatus }) {
  return (
    <span className="inline-block rounded-full border border-surface-line bg-surface-alt px-2.5 py-0.5 text-xs text-ink-soft">
      {STATUS_LABEL[status]}
    </span>
  );
}

export function Money({ value }: { value: string | null }) {
  if (value == null) return <span className="text-ink-faint">—</span>;
  const n = Number(value);
  const fmt = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(n);
  return <span className="font-medium tabular-nums">{fmt}</span>;
}

export function Spinner() {
  return (
    <div className="flex items-center gap-2 text-ink-soft">
      <span className="h-3 w-3 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      carregando…
    </div>
  );
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-ink-soft">{label}</span>
      {children}
    </label>
  );
}
