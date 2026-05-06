import { describe, it, expect } from "vitest";

import { isPathActive } from "@/lib/path-active";

/**
 * Wave 2 v4.0 / C08 — AUD-W2C08-003 + AUD-W2C08-012.
 *
 * Cobertura dos 5 casos do contrato de `isPathActive`, conforme ADR-128:
 *   1. exact match
 *   2. prefix match com separador `/`
 *   3. prefix com trailing slash no pathname (`/provas/[id]/` se existir)
 *   4. false-positive defendido (`/provas-other` NAO ativa `/provas`)
 *   5. href undefined retorna false
 *
 * Esta suite roda em `vitest.config.ts:environment=node` (sem DOM).
 */

describe("isPathActive (lib/path-active.ts)", () => {
  it("retorna true quando pathname === href (exact)", () => {
    expect(isPathActive("/provas", "/provas")).toBe(true);
  });

  it("retorna true quando pathname e subpath de href via /", () => {
    expect(isPathActive("/provas/abc-uuid", "/provas")).toBe(true);
  });

  it("retorna true quando pathname tem trailing slash apos o subpath", () => {
    // Caso defensivo: rotas Next.js normalmente nao tem trailing slash,
    // mas a normalizacao do middleware ja atende essa variacao.
    expect(isPathActive("/provas/abc-uuid/", "/provas")).toBe(true);
  });

  it("retorna false em prefix sem separador / (defende /provas-other)", () => {
    expect(isPathActive("/provas-other", "/provas")).toBe(false);
  });

  it("retorna false quando href e undefined", () => {
    expect(isPathActive("/provas", undefined)).toBe(false);
  });
});
