"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, setToken } from "@/lib/api";
import { Button, Card, Field } from "@/components/ui";

export default function SignupPage() {
  const router = useRouter();
  const [company, setCompany] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await api.signup(email, password, company);
      setToken(res.access_token);
      router.replace("/onboarding");
    } catch (err) {
      setError(err instanceof Error ? err.message : "falha no cadastro");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-sm p-8">
        <h1 className="text-lg font-semibold text-brand">Comece sua auditoria</h1>
        <p className="mt-1 text-sm text-ink-soft">
          Crie a conta e conecte o Sienge — primeiros achados em minutos.
        </p>
        <form onSubmit={submit} className="mt-6 space-y-4">
          <Field label="Empresa">
            <input value={company} onChange={(e) => setCompany(e.target.value)} required
              className="w-full rounded-lg border border-surface-line px-3 py-2 text-sm outline-none focus:border-brand" />
          </Field>
          <Field label="E-mail">
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required
              className="w-full rounded-lg border border-surface-line px-3 py-2 text-sm outline-none focus:border-brand" />
          </Field>
          <Field label="Senha (mín. 8)">
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8}
              className="w-full rounded-lg border border-surface-line px-3 py-2 text-sm outline-none focus:border-brand" />
          </Field>
          {error && <p className="text-sm text-sev-critical">{error}</p>}
          <Button type="submit" disabled={loading} className="w-full">
            {loading ? "Criando…" : "Criar conta"}
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-ink-soft">
          Já tem conta? <Link href="/login" className="text-brand hover:underline">Entrar</Link>
        </p>
      </Card>
    </div>
  );
}
