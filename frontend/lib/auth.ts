"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "./api";

/** Garante sessão; redireciona para /login se não houver token. */
export function useRequireAuth(): boolean {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
    } else {
      setReady(true);
    }
  }, [router]);
  return ready;
}
