"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, setToken } from "@/lib/api";
import { Button, Card, Field } from "@/components/ui";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await api.login(email, password);
      setToken(res.access_token);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "falha no login");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-sm p-8">
        <h1 className="text-lg font-semibold text-brand">Auditoria de Gastos</h1>
        <p className="mt-1 text-sm text-ink-soft">Entre para revisar os achados.</p>
        <form onSubmit={submit} className="mt-6 space-y-4">
          <Field label="E-mail">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-lg border border-surface-line px-3 py-2 text-sm outline-none focus:border-brand"
            />
          </Field>
          <Field label="Senha">
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full rounded-lg border border-surface-line px-3 py-2 text-sm outline-none focus:border-brand"
            />
          </Field>
          {error && <p className="text-sm text-sev-critical">{error}</p>}
          <Button type="submit" disabled={loading} className="w-full">
            {loading ? "Entrando…" : "Entrar"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
