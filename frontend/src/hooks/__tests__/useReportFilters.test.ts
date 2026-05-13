/**
 * Testes da extensao v4.0 do `useReportFilters` (Wave 5 v4.0 / C16).
 *
 * Cobre:
 *  - `parseRota` aceita os 6 valores de `Rota` (4 v4.0 + 2 legacy).
 *  - `parseStatus` aceita os 17 valores de `StatusProva` (10 v3 + 7 v4).
 *  - `parseRotaCategoria` aceita matriz/filial; rejeita outros.
 *  - URL com rota invalida retorna null (sem erro).
 *
 * Wave 5 v4.0 / C16 fix AUD-W5C16-006 (2026-05-13): testes agora importam
 * diretamente de `_useReportFilters.parsers` (modulo extraido), exercendo
 * as funcoes REAIS que o hook consome. Antes da extracao, este arquivo
 * re-implementava parsers identicos localmente — risco de drift silencioso
 * caso alguem mudasse o hook sem atualizar a copia aqui.
 */
import { describe, expect, it } from "vitest";

import { ROTA_OPTIONS, STATUS_OPTIONS } from "@/lib/types/prova";
import type { Rota, StatusProva } from "@/lib/types/prova";
import {
  parseRota,
  parseRotaCategoria,
  parseStatus,
} from "../_useReportFilters.parsers";

// ─── parseRota ────────────────────────────────────────────────────────

describe("parseRota — aceita 6 rotas (4 v4.0 + 2 legacy)", () => {
  const v4Rotas: Rota[] = ["MATRIZ", "LAM_MATRIZ", "FILIAL", "LAM_FILIAL"];
  const legacyRotas: Rota[] = ["PADRAO", "DIRETA"];

  it.each(v4Rotas)("aceita rota v4.0 %s", (rota) => {
    expect(parseRota(rota)).toBe(rota);
  });

  it.each(legacyRotas)("aceita rota legacy %s", (rota) => {
    expect(parseRota(rota)).toBe(rota);
  });

  it("rejeita rota invalida (string aleatoria)", () => {
    expect(parseRota("FOOBAR")).toBeNull();
  });

  it("rejeita rota lowercase", () => {
    expect(parseRota("matriz")).toBeNull();
  });

  it("rejeita string vazia", () => {
    expect(parseRota("")).toBeNull();
  });

  it("rejeita null", () => {
    expect(parseRota(null)).toBeNull();
  });

  it("aceita todos os valores de ROTA_OPTIONS (paridade)", () => {
    for (const rota of ROTA_OPTIONS) {
      expect(parseRota(rota)).toBe(rota);
    }
  });
});

// ─── parseStatus ──────────────────────────────────────────────────────

describe("parseStatus — aceita 17 status (10 v3 + 7 v4)", () => {
  const v3Status: StatusProva[] = [
    "CRIADA",
    "RETIRADA_PELO_VENDEDOR",
    "APROVADA_PELO_VENDEDOR",
    "DE_VOLTA_3STUDIO",
    "COM_MOTORISTA",
    "ENVIADA_PARA_CLICHERIA",
    "ENCAMINHADA_A_CLICHERIA",
    "RECEBIDA_PELA_CLICHERIA",
    "REPROVADA_PELO_VENDEDOR",
    "CANCELADA",
  ];
  const v4Status: StatusProva[] = [
    "COM_MOTORISTA_IDA_LAMINACAO",
    "COM_MOTORISTA_VOLTA_LAMINACAO",
    "COM_MOTORISTA_ENTREGA_FINAL",
    "ENCAMINHADA_PARA_LAMINACAO",
    "LAMINACAO_CONCLUIDA",
    "DE_VOLTA_3STUDIO_POS_LAMINACAO",
    "ENCAMINHADA_PARA_O_VENDEDOR",
  ];

  it.each(v3Status)("aceita status legacy v3 %s", (status) => {
    expect(parseStatus(status)).toBe(status);
  });

  it.each(v4Status)("aceita status v4.0 %s", (status) => {
    expect(parseStatus(status)).toBe(status);
  });

  it("rejeita status invalido", () => {
    expect(parseStatus("FOOBAR")).toBeNull();
  });

  it("rejeita string vazia", () => {
    expect(parseStatus("")).toBeNull();
  });

  it("rejeita null", () => {
    expect(parseStatus(null)).toBeNull();
  });

  it("aceita todos os 17 valores de STATUS_OPTIONS (paridade)", () => {
    expect(STATUS_OPTIONS.length).toBe(17);
    for (const status of STATUS_OPTIONS) {
      expect(parseStatus(status)).toBe(status);
    }
  });
});

// ─── parseRotaCategoria ───────────────────────────────────────────────

describe("parseRotaCategoria — aceita matriz|filial", () => {
  it("aceita matriz", () => {
    expect(parseRotaCategoria("matriz")).toBe("matriz");
  });

  it("aceita filial", () => {
    expect(parseRotaCategoria("filial")).toBe("filial");
  });

  it("rejeita ambas (qualquer outro string)", () => {
    expect(parseRotaCategoria("ambas")).toBeNull();
  });

  it("rejeita Matriz uppercase", () => {
    expect(parseRotaCategoria("Matriz")).toBeNull();
  });

  it("rejeita MATRIZ uppercase", () => {
    expect(parseRotaCategoria("MATRIZ")).toBeNull();
  });

  it("rejeita string vazia", () => {
    expect(parseRotaCategoria("")).toBeNull();
  });

  it("rejeita null", () => {
    expect(parseRotaCategoria(null)).toBeNull();
  });

  it("rejeita indefinida", () => {
    expect(parseRotaCategoria("indefinida")).toBeNull();
  });
});

// ─── Anti-regressao Wave 5 v3 ─────────────────────────────────────────

describe("anti-regressao: pre-Wave 5 v4.0 hard-coded STATUS_VALORES eram 10", () => {
  it("STATUS_OPTIONS agora tem 17 (10 v3 + 7 v4)", () => {
    // Garante que a fonte canonica saltou de 10 para 17 com a Wave 3 v4.0 C11.
    expect(STATUS_OPTIONS.length).toBe(17);
  });

  it("ROTA_OPTIONS tem 6 (4 v4 + 2 legacy)", () => {
    expect(ROTA_OPTIONS.length).toBe(6);
  });
});
