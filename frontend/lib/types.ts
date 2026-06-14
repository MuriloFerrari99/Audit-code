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
  R1: "Sobrepreço",
  R2: "Cotação perdida",
  R3: "Fracionamento",
  R4: "Estouro de quantidade",
  R5: "Divergência pedido→pagamento",
  R6: "Sem concorrência",
};
