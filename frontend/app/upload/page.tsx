"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { AppShell } from "@/components/shell";
import { Button, Card, Spinner } from "@/components/ui";
import type { NfeUploadSummary, PlanilhaUploadSummary } from "@/lib/types";

const MAP_LABEL: Record<string, string> = {
  fornecedor: "Fornecedor",
  cnpj: "CNPJ",
  documento: "Documento/Nota",
  valor: "Valor",
  data: "Data/Vencimento",
  pedido: "Pedido",
};

function DropZone({
  accept,
  multiple,
  hint,
  onPick,
}: {
  accept: string;
  multiple?: boolean;
  hint: string;
  onPick: (files: File[]) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        onPick(Array.from(e.dataTransfer.files));
      }}
      onClick={() => inputRef.current?.click()}
      className={`cursor-pointer rounded-card border-2 border-dashed p-8 text-center transition ${
        over ? "border-brand bg-brand-muted" : "border-surface-line hover:bg-surface-alt"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        className="hidden"
        onChange={(e) => onPick(Array.from(e.target.files ?? []))}
      />
      <div className="text-sm text-ink-soft">Arraste aqui ou clique para escolher</div>
      <div className="mt-1 text-xs text-ink-faint">{hint}</div>
    </div>
  );
}

export default function UploadPage() {
  const ready = useRequireAuth();
  const [busy, setBusy] = useState<null | "nfe" | "planilha" | "rules">(null);
  const [error, setError] = useState<string | null>(null);
  const [nfe, setNfe] = useState<NfeUploadSummary | null>(null);
  const [planilha, setPlanilha] = useState<PlanilhaUploadSummary | null>(null);
  const [ran, setRan] = useState<Record<string, number> | null>(null);

  if (!ready) return null;

  async function sendNfe(files: File[]) {
    const xmls = files.filter((f) => f.name.toLowerCase().endsWith(".xml"));
    if (xmls.length === 0) {
      setError("Selecione um ou mais arquivos .xml de NF-e.");
      return;
    }
    setError(null);
    setBusy("nfe");
    try {
      setNfe(await api.uploadNfe(xmls));
      setRan(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "falha no upload de NF-e");
    } finally {
      setBusy(null);
    }
  }

  async function sendPlanilha(files: File[]) {
    const file = files[0];
    if (!file) return;
    setError(null);
    setBusy("planilha");
    try {
      setPlanilha(await api.uploadPlanilha(file));
      setRan(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "falha no upload da planilha");
    } finally {
      setBusy(null);
    }
  }

  async function runRules() {
    setError(null);
    setBusy("rules");
    try {
      const r = await api.runRules();
      setRan(r.found);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "falha ao rodar a auditoria");
    } finally {
      setBusy(null);
    }
  }

  const hasData = (nfe && nfe.invoices > 0) || (planilha && planilha.bills > 0);

  return (
    <AppShell>
      <h1 className="text-xl font-semibold">Enviar documentos</h1>
      <p className="mt-1 text-sm text-ink-soft">
        Suba notas fiscais (XML) e a planilha de lançamentos. Auditamos sobre o mesmo modelo —
        não precisa de integração com o ERP.
      </p>

      {error && (
        <div className="mt-4 rounded-lg border border-sev-high/40 bg-sev-high/10 px-4 py-2 text-sm text-sev-high">
          {error}
        </div>
      )}

      <div className="mt-6 grid gap-5 md:grid-cols-2">
        {/* NF-e */}
        <Card className="p-5">
          <h2 className="font-medium">Notas fiscais (NF-e / NFS-e)</h2>
          <p className="mt-1 text-xs text-ink-soft">Um ou vários arquivos .xml (produto ou serviço).</p>
          <div className="mt-4">
            <DropZone accept=".xml" multiple hint="arquivos .xml de NF-e ou NFS-e" onPick={sendNfe} />
          </div>
          {busy === "nfe" && <div className="mt-4"><Spinner /></div>}
          {nfe && (
            <div className="mt-4 space-y-1 text-sm">
              <div>Notas carregadas: <b>{nfe.invoices}</b></div>
              <div>Itens: <b>{nfe.items}</b></div>
              {nfe.dead_letters > 0 && (
                <div className="text-sev-high">XMLs inválidos (revisar): <b>{nfe.dead_letters}</b></div>
              )}
            </div>
          )}
        </Card>

        {/* Planilha */}
        <Card className="p-5">
          <h2 className="font-medium">Planilha de lançamentos</h2>
          <p className="mt-1 text-xs text-ink-soft">CSV ou XLSX. As colunas são detectadas sozinhas.</p>
          <div className="mt-4">
            <DropZone accept=".csv,.xlsx,.xlsm" hint="arquivo .csv ou .xlsx" onPick={sendPlanilha} />
          </div>
          {busy === "planilha" && <div className="mt-4"><Spinner /></div>}
          {planilha && (
            <div className="mt-4 space-y-2 text-sm">
              <div>Lançamentos carregados: <b>{planilha.bills}</b></div>
              {planilha.dead_letters > 0 && (
                <div className="text-sev-high">Linhas sem valor (revisar): <b>{planilha.dead_letters}</b></div>
              )}
              <div className="flex flex-wrap gap-1.5 pt-1">
                {Object.entries(planilha.mapping).map(([field, col]) => (
                  <span key={field} className="rounded-full bg-surface-alt px-2.5 py-0.5 text-xs text-ink-soft">
                    {MAP_LABEL[field] ?? field}: <b>{col}</b>
                  </span>
                ))}
                {Object.keys(planilha.mapping).length === 0 && (
                  <span className="text-xs text-ink-faint">Nenhuma coluna reconhecida — confira os cabeçalhos.</span>
                )}
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* Auditar */}
      <Card className="mt-6 flex flex-wrap items-center justify-between gap-3 p-5">
        <div className="text-sm text-ink-soft">
          {hasData ? "Documentos prontos. Rode a auditoria para gerar os achados." : "Suba ao menos uma nota ou planilha para auditar."}
        </div>
        <div className="flex items-center gap-3">
          {busy === "rules" && <Spinner />}
          <Button onClick={runRules} disabled={!hasData || busy !== null}>
            Rodar auditoria
          </Button>
        </div>
      </Card>

      {ran && (
        <Card className="mt-4 p-5">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="text-ink-soft">Achados por regra:</span>
            {Object.entries(ran).length === 0 ? (
              <span className="text-ink-faint">nenhum achado nesta rodada.</span>
            ) : (
              Object.entries(ran).map(([rule, n]) => (
                <span key={rule} className="rounded-full bg-brand-muted px-3 py-1 text-brand">
                  {rule}: <b>{n}</b>
                </span>
              ))
            )}
          </div>
          <Link href="/findings" className="mt-3 inline-block text-sm text-brand hover:underline">
            Ver achados →
          </Link>
        </Card>
      )}
    </AppShell>
  );
}
