"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { setToken } from "@/lib/api";

const NAV = [
  { href: "/", label: "Visão geral" },
  { href: "/findings", label: "Achados" },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  function logout() {
    setToken(null);
    router.replace("/login");
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-surface-line bg-surface">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-8">
            <span className="font-semibold text-brand">Auditoria de Gastos</span>
            <nav className="flex gap-1">
              {NAV.map((item) => {
                const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`rounded-lg px-3 py-1.5 text-sm ${active ? "bg-brand-muted text-brand" : "text-ink-soft hover:bg-surface-alt"}`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>
          <button onClick={logout} className="text-sm text-ink-soft hover:text-ink">
            Sair
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
