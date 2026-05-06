import { describe, it, expect } from "vitest";

import { formatRota, ROTA_LABELS } from "@/lib/types/prova";

/**
 * Wave 2 v4.0 / C08 — AUD-W2C08-003.
 *
 * Cobertura de `formatRota` para os 6 valores de `rota_enum` + null:
 *   - 4 valores v4.0 (MATRIZ, LAM_MATRIZ, FILIAL, LAM_FILIAL)
 *   - 2 valores legacy v3.0 (PADRAO, DIRETA) — sem sufixo "(legada v3.0)"
 *     conforme ADR-126
 *   - null (provas legacy pre-Wave 7) — retorna em-dash literal "—"
 *     conforme ADR-126 + AUD-W2C08-011
 *
 * Esta suite valida o contrato visual da rota; quando a Wave 7
 * (Componente 21) fizer backfill, o cenario null deixa de ser comum mas
 * o teste continua valido (defesa contra reintroducao).
 */

describe("formatRota (lib/types/prova.ts)", () => {
  it("formata MATRIZ como 'Matriz'", () => {
    expect(formatRota("MATRIZ")).toBe("Matriz");
  });

  it("formata LAM_MATRIZ como 'Lam. Matriz'", () => {
    expect(formatRota("LAM_MATRIZ")).toBe("Lam. Matriz");
  });

  it("formata FILIAL como 'Filial'", () => {
    expect(formatRota("FILIAL")).toBe("Filial");
  });

  it("formata LAM_FILIAL como 'Lam. Filial'", () => {
    expect(formatRota("LAM_FILIAL")).toBe("Lam. Filial");
  });

  it("formata legacy PADRAO como 'Padrao' (sem sufixo)", () => {
    expect(formatRota("PADRAO")).toBe("Padrao");
  });

  it("formata legacy DIRETA como 'Direta' (sem sufixo)", () => {
    expect(formatRota("DIRETA")).toBe("Direta");
  });

  it("retorna em-dash para rota null (legacy pre-Wave 7)", () => {
    expect(formatRota(null)).toBe("—");
  });

  it("`ROTA_LABELS` cobre exaustivamente os 6 valores do enum (sanity)", () => {
    // Defesa contra adicao de novo valor a `Rota` sem atualizar
    // `ROTA_LABELS` — o TS ja forca via Record<Rota,string>, mas garantir
    // que nenhum cenario sumiu silenciosamente deste arquivo de teste.
    expect(Object.keys(ROTA_LABELS).sort()).toEqual([
      "DIRETA",
      "FILIAL",
      "LAM_FILIAL",
      "LAM_MATRIZ",
      "MATRIZ",
      "PADRAO",
    ]);
  });
});
