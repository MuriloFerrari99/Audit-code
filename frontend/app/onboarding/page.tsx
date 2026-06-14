"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { Button, Card, Field, Money, Spinner } from "@/components/ui";
import { RULE_NAMES } from "@/lib/types";

type Step = "connect" | "running" | "done";

export default function OnboardingPage() {
  const ready = useRequireAuth();
  const router = useRouter();
  const [step, setStep] = useState<Step>("connect");

  // conexão
  const [sub, setSub] = useState("");
  const [user, setUser] = useState("");
  const [pwd, setPwd] = useState("");
  const [testing, setTesting] = useState(false);
  const [test, setTest] = useState<{ ok: boolean; creditors?: number; orders?: number; reason?: string } | null>(null);
  const [busy, setBusy] = useState(false);

  // execução
  const [status, setStatus] = useState<{ state: string; step?: string; total_findings?: number; found?: Record<string, number>; reason?: string }>({ state: "nao_iniciado" });

  const runTest = useCallback(async () => {
    setTesting(true);
    setTest(null);
    try {
      setTest(await api.onbTest(sub.trim(), user.trim(), pwd));
    } catch {
      setTest({ ok: false, reason: "erro ao testar" });
    } finally {
      setTesting(false);
    }
  }, [sub, user, pwd]);

  async function connectAndRun() {
    setBusy(true);
    try {
      await api.onbConnect(sub.trim(), user.trim(), pwd);
      await api.onbRun();
      setStep("running");
    } finally {
      setBusy(false);
    }
  }

  // polling do status quando em execução
  useEffect(() => {
    if (step !== "running") return;
    const id = setInterval(async () => {
      const s = await api.onbStatus();
      setStatus(s);
      if (s.state === "pronto") {
        setStep("done");
        clearInterval(id);
      }
      if (s.state === "erro") clearInterval(id);
    }, 2000);
    return () => clearInterval(id);
  }, [step]);

  if (!ready) return null;

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <Stepper step={step} />
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {step === "connect" && (
            <Card className="p-6">
              <h2 className="text-lg font-semibold">Conecte seu Sienge</h2>
              <p className="mt-1 text-sm text-ink-soft">
                Use um <b>usuário de API somente leitura</b>. Não escrevemos nada no seu ERP.
              </p>
              <div className="mt-5 grid grid-cols-1 gap-4">
                <Field label="Subdomínio (ex.: suaempresa em suaempresa.sienge.com.br)">
                  <input value={sub} onChange={(e) => setSub(e.target.value)}
                    className="w-full rounded-lg border border-surface-line px-3 py-2 text-sm outline-none focus:border-brand" />
                </Field>
                <Field label="Usuário de API">
                  <input value={user} onChange={(e) => setUser(e.target.value)}
                    className="w-full rounded-lg border border-surface-line px-3 py-2 text-sm outline-none focus:border-brand" />
                </Field>
                <Field label="Senha de API">
                  <input type="password" value={pwd} onChange={(e) => setPwd(e.target.value)}
                    className="w-full rounded-lg border border-surface-line px-3 py-2 text-sm outline-none focus:border-brand" />
                </Field>
              </div>

              <div className="mt-4 flex items-center gap-3">
                <Button variant="secondary" onClick={runTest} disabled={testing || !sub || !user || !pwd}>
                  {testing ? "Testando…" : "Testar conexão"}
                </Button>
                {test?.ok && (
                  <span className="text-sm text-ok">
                    ✓ Conectado — {test.creditors?.toLocaleString("pt-BR")} fornecedores,{" "}
                    {test.orders?.toLocaleString("pt-BR")} pedidos
                  </span>
                )}
                {test && !test.ok && <span className="text-sm text-sev-critical">{test.reason}</span>}
              </div>

              <div className="mt-6 border-t border-surface-line pt-4">
                <Button onClick={connectAndRun} disabled={!test?.ok || busy}>
                  {busy ? "Iniciando…" : "Conectar e auditar →"}
                </Button>
                <p className="mt-2 text-xs text-ink-faint">
                  Sua credencial é guardada criptografada e isolada por empresa.
                </p>
              </div>
            </Card>
          )}

          {step === "running" && (
            <Card className="p-8">
              <h2 className="text-lg font-semibold">Auditando seus gastos…</h2>
              <div className="mt-4"><Spinner /></div>
              <ul className="mt-4 space-y-1 text-sm text-ink-soft">
                <li>✓ Conectado ao Sienge</li>
                <li>{["carregando", "auditando", "pronto"].includes(status.state) ? "✓" : "•"} Lendo pedidos, notas, títulos e orçamento</li>
                <li>{["auditando", "pronto"].includes(status.state) ? "✓" : "•"} Casando cotações e rodando as regras</li>
              </ul>
              <p className="mt-3 text-xs text-ink-faint">{status.step ?? "preparando…"}</p>
              {status.state === "erro" && (
                <p className="mt-3 text-sm text-sev-critical">Falha: {status.reason}</p>
              )}
            </Card>
          )}

          {step === "done" && (
            <Card className="p-8 text-center">
              <div className="text-sm text-ink-soft">Sua primeira auditoria está pronta</div>
              <div className="mt-2 text-4xl font-bold text-brand">{status.total_findings ?? 0} achados</div>
              <div className="mt-4 flex flex-wrap justify-center gap-2 text-sm">
                {Object.entries(status.found ?? {}).map(([rid, n]) => (
                  <span key={rid} className="rounded-full bg-surface-alt px-3 py-1">
                    {RULE_NAMES[rid] ?? rid}: <b>{n}</b>
                  </span>
                ))}
              </div>
              <div className="mt-6">
                <Button onClick={() => router.replace("/findings")}>Ver achados →</Button>
              </div>
            </Card>
          )}
        </div>

        <OnboardingAssistant />
      </div>
    </div>
  );
}

function Stepper({ step }: { step: Step }) {
  const items: [Step, string][] = [["connect", "Conectar"], ["running", "Auditando"], ["done", "Resultado"]];
  const order = ["connect", "running", "done"];
  return (
    <div className="flex items-center gap-2 text-sm">
      {items.map(([k, label], i) => {
        const active = order.indexOf(step) >= i;
        return (
          <div key={k} className="flex items-center gap-2">
            <span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${active ? "bg-brand text-brand-fg" : "bg-surface-line text-ink-faint"}`}>{i + 1}</span>
            <span className={active ? "text-ink" : "text-ink-faint"}>{label}</span>
            {i < 2 && <span className="mx-1 text-ink-faint">—</span>}
          </div>
        );
      })}
    </div>
  );
}

function OnboardingAssistant() {
  const [msgs, setMsgs] = useState<{ role: "user" | "bot"; text: string }[]>([
    { role: "bot", text: "Posso ajudar a conectar o Sienge. Pergunte: onde gero a chave de API? é seguro? o que vocês acessam?" },
  ]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), [msgs]);

  async function ask(question: string) {
    if (!question.trim()) return;
    setMsgs((m) => [...m, { role: "user", text: question }]);
    setQ("");
    setLoading(true);
    try {
      const r = await api.assistant(question);
      setMsgs((m) => [...m, { role: "bot", text: r.answer }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="flex h-[28rem] flex-col p-4">
      <div className="text-sm font-medium text-ink-soft">Assistente de onboarding</div>
      <div className="mt-3 flex-1 space-y-3 overflow-y-auto pr-1">
        {msgs.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : ""}>
            <span className={`inline-block whitespace-pre-wrap rounded-lg px-3 py-2 text-sm ${m.role === "user" ? "bg-brand text-brand-fg" : "bg-surface-alt text-ink"}`}>
              {m.text}
            </span>
          </div>
        ))}
        {loading && <div className="text-xs text-ink-faint">pensando…</div>}
        <div ref={endRef} />
      </div>
      <div className="mt-3 flex gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask(q)}
          placeholder="Tire sua dúvida…"
          className="flex-1 rounded-lg border border-surface-line px-3 py-2 text-sm outline-none focus:border-brand"
        />
        <Button onClick={() => ask(q)} disabled={loading}>Enviar</Button>
      </div>
    </Card>
  );
}
