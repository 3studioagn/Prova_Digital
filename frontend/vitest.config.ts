import { defineConfig } from "vitest/config";
import path from "node:path";

/**
 * Wave 1 v4.0 — Audit Round 2 (AUD-W1V4-005).
 *
 * Configuracao minima do Vitest para cobrir o middleware RBAC. Roda em
 * environment Node (sem jsdom) — middleware nao toca DOM. Apenas o
 * caminho de teste atual e `src/lib/supabase/__tests__/middleware.test.ts`;
 * estende quando criarmos novos modulos com testes.
 *
 * Nao inclui coverage v8 nem testing-library para minimizar superficie
 * instalada (vide §3.5 do fix-plan: "Mudanca limitada a devDependency").
 */
export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts", "src/**/__tests__/*.test.ts"],
    globals: false,
  },
});
