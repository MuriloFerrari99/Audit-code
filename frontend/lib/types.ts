export type Severity = "low" | "medium" | "high" | "critical";
export type FindingStatus =
  | "open"
  | "accepted"
  | "dismissed"
  | "escalated"
  | "resolved"
  | "superseded";

export interface Evidence {
  entity_type: string;
  role: string;
  snippet: string | null;
  value: Record<string, unknown> | null;
}

export interface Finding {
  id: string;
  rule_id: string;
  severity: Severity;
  status: FindingStatus;
  exposed_amount: string | null;
  confidence: string | null;
  title: string | null;
  project_id: string | null;
  created_at: string;
  evidence: Evidence[];
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  tenant_id: string | null;
  role: string | null;
}

export interface MonthlyReport {
  numbers: {
    period: string;
    exposed_open: string;
    validated: string;
    open_findings: number;
    by_rule: Record<string, number>;
  };
  summary: string;
}

export const RULE_NAMES: Record<string, string> = {
  // Dimensão 1 — Preço/governança
  R1: "Sobrepreço",
  R2: "Cotação perdida",
  R3: "Fracionamento",
  R4: "Estouro de quantidade",
  R5: "Divergência pedido→pagamento",
  R6: "Sem concorrência",
  // Dimensão 2 — Fiscal
  F1: "Nota acima do pedido",
  F2: "Nota inconsistente",
  F3: "Pagamento acima da nota",
  // Dimensão 3 — Pagamento
  P1: "Pagamento duplicado",
  P2: "Pagamento sem lastro",
  // Dimensão 4 — Integridade do fornecedor
  I1: "Fornecedor sancionado",
  I2: "CNPJ não-ativo",
  I3: "Empresa recém-aberta de alto valor",
  I4: "Sócio em comum",
  I5: "Fornecedor não verificado",
};

export const RULE_DIMENSION: Record<string, number> = {
  R1: 1, R2: 1, R3: 1, R4: 1, R6: 1,
  F1: 2, F2: 2, F3: 2,
  R5: 3, P1: 3, P2: 3,
  I1: 4, I2: 4, I3: 4, I4: 4, I5: 4,
};

export const DIMENSION_LABELS: Record<number, string> = {
  1: "Preço & Governança",
  2: "Fiscal",
  3: "Pagamento",
  4: "Integridade",
};

export interface CalibrationStat {
  rule_id: string;
  samples: number;
  accepted: number;
  dismissed: number;
  acceptance_rate: number | null;
  confidence_factor: number;
}

export interface QualityIssue {
  code: string;
  severity: string;
  entity_type: string;
  entity_id: string | null;
  message: string;
  action: string;
}

export interface NfeUploadSummary {
  invoices: number;
  items: number;
  dead_letters: number;
}

export interface PlanilhaUploadSummary {
  bills: number;
  dead_letters: number;
  mapping: Record<string, string>;
}

export interface BillingSummary {
  period: string;
  plan: { code: string; name: string } | null;
  invoices_used: number;
  invoice_limit: number | null;
  overage_units: number;
  base_price: string;
  overage_price: string;
  overage_amount: string;
  total: string;
  subscription_status: string;
}
