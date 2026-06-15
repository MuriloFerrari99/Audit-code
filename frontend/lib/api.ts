"use client";

import type { Finding, MonthlyReport, TokenResponse } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "audit_access_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers ?? {}),
    },
  });
  if (res.status === 401) {
    setToken(null);
    throw new ApiError(401, "não autenticado");
  }
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, detail.detail ?? "erro");
  }
  return (await res.json()) as T;
}

async function upload<T>(path: string, form: FormData): Promise<T> {
  const token = getToken();
  // NÃO setar Content-Type: o browser define o boundary do multipart.
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (res.status === 401) {
    setToken(null);
    throw new ApiError(401, "não autenticado");
  }
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, detail.detail ?? "erro no upload");
  }
  return (await res.json()) as T;
}

export const api = {
  async login(email: string, password: string, tenantId?: string): Promise<TokenResponse> {
    const body = JSON.stringify({ email, password, tenant_id: tenantId ?? null });
    const res = await fetch(`${BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    if (!res.ok) {
      const d = await res.json().catch(() => ({ detail: "falha no login" }));
      throw new ApiError(res.status, d.detail);
    }
    return (await res.json()) as TokenResponse;
  },
  async signup(email: string, password: string, companyName: string): Promise<TokenResponse> {
    const res = await fetch(`${BASE}/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, company_name: companyName }),
    });
    if (!res.ok) {
      const d = await res.json().catch(() => ({ detail: "falha no cadastro" }));
      throw new ApiError(res.status, d.detail);
    }
    return (await res.json()) as TokenResponse;
  },
  // onboarding
  onbTest: (subdomain: string, user: string, password: string) =>
    request<{ ok: boolean; creditors?: number; orders?: number; reason?: string }>(
      "/onboarding/test",
      { method: "POST", body: JSON.stringify({ subdomain, user, password }) },
    ),
  onbConnect: (subdomain: string, user: string, password: string) =>
    request<{ ok: boolean }>("/onboarding/connect", {
      method: "POST",
      body: JSON.stringify({ subdomain, user, password }),
    }),
  onbRun: () => request<{ state: string }>("/onboarding/run", { method: "POST" }),
  onbStatus: () =>
    request<{ state: string; step?: string; found?: Record<string, number>; total_findings?: number; reason?: string }>(
      "/onboarding/status",
    ),
  assistant: (question: string) =>
    fetch(`${BASE}/onboarding/assistant`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }).then((r) => r.json() as Promise<{ answer: string }>),
  uploadNfe: (files: File[]) => {
    const form = new FormData();
    for (const f of files) form.append("files", f);
    return upload<import("./types").NfeUploadSummary>("/upload/nfe", form);
  },
  uploadPlanilha: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return upload<import("./types").PlanilhaUploadSummary>("/upload/planilha", form);
  },
  runRules: () => request<{ found: Record<string, number> }>("/rules/run", { method: "POST" }),
  listFindings: (params: Record<string, string> = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request<Finding[]>(`/findings${qs ? `?${qs}` : ""}`);
  },
  getFinding: (id: string) => request<Finding>(`/findings/${id}`),
  reviewFinding: (id: string, decision: string, reason?: string) =>
    request<Finding>(`/findings/${id}/review`, {
      method: "POST",
      body: JSON.stringify({ decision, reason: reason ?? null }),
    }),
  billing: () => request<import("./types").BillingSummary>("/billing/me"),
  statement: () => request<import("./types").Statement>("/billing/statement"),
  monthlyReport: () => request<MonthlyReport>("/reports/monthly"),
  dossier: (id: string) => request<Record<string, unknown>>(`/findings/${id}/dossier`),
  quality: () =>
    request<{ total: number; by_code: Record<string, number>; issues: import("./types").QualityIssue[] }>(
      "/quality",
    ),
  calibration: () =>
    request<{ stats: import("./types").CalibrationStat[]; suggestions: string[] }>("/calibration"),
  calibrationRecompute: () =>
    request<{ stats: import("./types").CalibrationStat[]; suggestions: string[] }>(
      "/calibration/recompute",
      { method: "POST" },
    ),
};

export { ApiError };
