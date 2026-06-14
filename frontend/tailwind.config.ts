import type { Config } from "tailwindcss";

// Design tokens — base do design system (sincronizável com Claude Design).
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#0f766e", // teal-700 — confiança/auditoria
          fg: "#ffffff",
          muted: "#ccfbf1",
        },
        ink: { DEFAULT: "#0f172a", soft: "#475569", faint: "#94a3b8" },
        surface: { DEFAULT: "#ffffff", alt: "#f8fafc", line: "#e2e8f0" },
        sev: {
          critical: "#b91c1c",
          high: "#ea580c",
          medium: "#ca8a04",
          low: "#0891b2",
        },
        ok: "#15803d",
      },
      borderRadius: { card: "12px" },
      boxShadow: { card: "0 1px 2px rgba(15,23,42,.06), 0 1px 3px rgba(15,23,42,.1)" },
    },
  },
  plugins: [],
};
export default config;
