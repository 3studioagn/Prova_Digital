import { describe, it, expect } from "vitest";

import {
  contextoMotorista,
  ESTADOS_LAMINACAO,
  formatRota,
  getRotaEtapas,
  getRotaLabel,
  isInLaminationBlock,
  LEGACY_ROTA_DIRETA,
  LEGACY_ROTA_PADRAO,
  ROTA_ETAPAS,
  ROTA_LABELS,
  STATUS_LABELS,
  STATUS_LABELS_SHORT,
  type ContextoMotorista,
  type StatusProva,
} from "@/lib/types/prova";

/**
 * Wave 2 v4.0 / C08 — AUD-W2C08-003 (formatRota + ROTA_LABELS).
 * Wave 3 v4.0 / C12 — Decisao 11.1 do Gate 1: PADRAO/DIRETA viram
 * "Matriz"/"Filial" (supersede ADR-126).
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

  it("formata legacy PADRAO como 'Matriz' (C12 Decisao 11.1 — supersede ADR-126)", () => {
    expect(formatRota("PADRAO")).toBe("Matriz");
  });

  it("formata legacy DIRETA como 'Filial' (C12 Decisao 11.1 — supersede ADR-126)", () => {
    expect(formatRota("DIRETA")).toBe("Filial");
  });

  it("retorna em-dash para rota null (legacy pre-Wave 7)", () => {
    expect(formatRota(null)).toBe("—");
  });

  it("`ROTA_LABELS` cobre exaustivamente os 6 valores do enum (sanity)", () => {
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

/**
 * Wave 3 v4.0 / C12 — contexto do motorista (Decisao 4 do Gate 1).
 * Espelho do helper Python `contexto_motorista` em
 * `backend/app/state_machine/v4/contextos.py`.
 */
describe("contextoMotorista (lib/types/prova.ts)", () => {
  it("COM_MOTORISTA_IDA_LAMINACAO -> 'ida_laminacao'", () => {
    expect(contextoMotorista("COM_MOTORISTA_IDA_LAMINACAO")).toBe(
      "ida_laminacao",
    );
  });

  it("COM_MOTORISTA_VOLTA_LAMINACAO -> 'volta_laminacao'", () => {
    expect(contextoMotorista("COM_MOTORISTA_VOLTA_LAMINACAO")).toBe(
      "volta_laminacao",
    );
  });

  it("COM_MOTORISTA_ENTREGA_FINAL -> 'entrega_final'", () => {
    expect(contextoMotorista("COM_MOTORISTA_ENTREGA_FINAL")).toBe(
      "entrega_final",
    );
  });

  it("COM_MOTORISTA legacy v3.0 -> 'entrega_final' (compat — ADR-148)", () => {
    expect(contextoMotorista("COM_MOTORISTA")).toBe("entrega_final");
  });

  it("CRIADA -> null (nao-motorista)", () => {
    expect(contextoMotorista("CRIADA")).toBe(null);
  });

  it("RECEBIDA_PELA_CLICHERIA -> null (terminal nao-motorista)", () => {
    expect(contextoMotorista("RECEBIDA_PELA_CLICHERIA")).toBe(null);
  });

  it("cobre os 3 contextos distintos da v4.0 (sanity exhaustivo)", () => {
    const contextos = new Set<ContextoMotorista>();
    contextos.add(contextoMotorista("COM_MOTORISTA_IDA_LAMINACAO")!);
    contextos.add(contextoMotorista("COM_MOTORISTA_VOLTA_LAMINACAO")!);
    contextos.add(contextoMotorista("COM_MOTORISTA_ENTREGA_FINAL")!);
    expect(contextos.size).toBe(3);
  });
});

/**
 * Wave 3 v4.0 / C12 — bloco visual de laminacao (Decisao 3 do Gate 1).
 */
describe("isInLaminationBlock + ESTADOS_LAMINACAO", () => {
  it("ESTADOS_LAMINACAO tem 5 estados (cobre Lam. Matriz inteira + subset Lam. Filial)", () => {
    expect(ESTADOS_LAMINACAO).toHaveLength(5);
  });

  it("ENCAMINHADA_PARA_LAMINACAO -> true", () => {
    expect(isInLaminationBlock("ENCAMINHADA_PARA_LAMINACAO")).toBe(true);
  });

  it("COM_MOTORISTA_IDA_LAMINACAO -> true", () => {
    expect(isInLaminationBlock("COM_MOTORISTA_IDA_LAMINACAO")).toBe(true);
  });

  it("LAMINACAO_CONCLUIDA -> true", () => {
    expect(isInLaminationBlock("LAMINACAO_CONCLUIDA")).toBe(true);
  });

  it("COM_MOTORISTA_VOLTA_LAMINACAO -> true (so Lam. Matriz)", () => {
    expect(isInLaminationBlock("COM_MOTORISTA_VOLTA_LAMINACAO")).toBe(true);
  });

  it("DE_VOLTA_3STUDIO_POS_LAMINACAO -> true (so Lam. Matriz)", () => {
    expect(isInLaminationBlock("DE_VOLTA_3STUDIO_POS_LAMINACAO")).toBe(true);
  });

  it("CRIADA -> false (fora do bloco)", () => {
    expect(isInLaminationBlock("CRIADA")).toBe(false);
  });

  it("APROVADA_PELO_VENDEDOR -> false (fora do bloco)", () => {
    expect(isInLaminationBlock("APROVADA_PELO_VENDEDOR")).toBe(false);
  });

  it("COM_MOTORISTA_ENTREGA_FINAL -> false (motorista pos-laminacao, fora do bloco)", () => {
    expect(isInLaminationBlock("COM_MOTORISTA_ENTREGA_FINAL")).toBe(false);
  });

  it("RECEBIDA_PELA_CLICHERIA -> false (terminal, fora do bloco)", () => {
    expect(isInLaminationBlock("RECEBIDA_PELA_CLICHERIA")).toBe(false);
  });
});

/**
 * Wave 3 v4.0 / C12 — ROTA_ETAPAS por rota v4.0 (Decisao 2 do Gate 1).
 * Tamanhos espelham as 4 rotas da Secao 5 do Requisitos v4.0:
 *   MATRIZ=6 (§5.2 — 5 transicoes + CRIADA inicial)
 *   LAM_MATRIZ=11 (§5.3 — 10 transicoes + CRIADA inicial)
 *   FILIAL=4 (§5.4 — 3 transicoes + CRIADA inicial)
 *   LAM_FILIAL=7 (§5.5 — 6 transicoes + CRIADA inicial)
 *
 * Reprovacao e cancelamento NAO entram (transversais — Decisao 7 do C12).
 */
describe("ROTA_ETAPAS + sequencias canonicas", () => {
  it("MATRIZ tem 6 estados em ordem canonica", () => {
    expect(ROTA_ETAPAS.MATRIZ).toEqual([
      "CRIADA",
      "RETIRADA_PELO_VENDEDOR",
      "APROVADA_PELO_VENDEDOR",
      "DE_VOLTA_3STUDIO",
      "COM_MOTORISTA_ENTREGA_FINAL",
      "RECEBIDA_PELA_CLICHERIA",
    ]);
  });

  it("LAM_MATRIZ tem 11 estados em ordem canonica", () => {
    expect(ROTA_ETAPAS.LAM_MATRIZ).toEqual([
      "CRIADA",
      "ENCAMINHADA_PARA_LAMINACAO",
      "COM_MOTORISTA_IDA_LAMINACAO",
      "LAMINACAO_CONCLUIDA",
      "COM_MOTORISTA_VOLTA_LAMINACAO",
      "DE_VOLTA_3STUDIO_POS_LAMINACAO",
      "RETIRADA_PELO_VENDEDOR",
      "APROVADA_PELO_VENDEDOR",
      "DE_VOLTA_3STUDIO",
      "COM_MOTORISTA_ENTREGA_FINAL",
      "RECEBIDA_PELA_CLICHERIA",
    ]);
  });

  it("FILIAL tem 4 estados em ordem canonica", () => {
    expect(ROTA_ETAPAS.FILIAL).toEqual([
      "CRIADA",
      "ENCAMINHADA_PARA_O_VENDEDOR",
      "APROVADA_PELO_VENDEDOR",
      "RECEBIDA_PELA_CLICHERIA",
    ]);
  });

  it("LAM_FILIAL tem 7 estados em ordem canonica", () => {
    expect(ROTA_ETAPAS.LAM_FILIAL).toEqual([
      "CRIADA",
      "ENCAMINHADA_PARA_LAMINACAO",
      "COM_MOTORISTA_IDA_LAMINACAO",
      "LAMINACAO_CONCLUIDA",
      "ENCAMINHADA_PARA_O_VENDEDOR",
      "APROVADA_PELO_VENDEDOR",
      "RECEBIDA_PELA_CLICHERIA",
    ]);
  });

  it("nenhuma rota v4.0 inclui REPROVADA nem CANCELADA (transversais)", () => {
    const rotas = ["MATRIZ", "LAM_MATRIZ", "FILIAL", "LAM_FILIAL"] as const;
    for (const rota of rotas) {
      const set = new Set<StatusProva>(ROTA_ETAPAS[rota]);
      expect(set.has("REPROVADA_PELO_VENDEDOR")).toBe(false);
      expect(set.has("CANCELADA")).toBe(false);
    }
  });

  it("LEGACY_ROTA_PADRAO tem 7 estados (inclui COM_MOTORISTA legacy + ENVIADA_PARA_CLICHERIA)", () => {
    expect(LEGACY_ROTA_PADRAO).toEqual([
      "CRIADA",
      "RETIRADA_PELO_VENDEDOR",
      "APROVADA_PELO_VENDEDOR",
      "DE_VOLTA_3STUDIO",
      "COM_MOTORISTA",
      "ENVIADA_PARA_CLICHERIA",
      "RECEBIDA_PELA_CLICHERIA",
    ]);
  });

  it("LEGACY_ROTA_DIRETA tem 5 estados (inclui ENCAMINHADA_A_CLICHERIA)", () => {
    expect(LEGACY_ROTA_DIRETA).toEqual([
      "CRIADA",
      "RETIRADA_PELO_VENDEDOR",
      "APROVADA_PELO_VENDEDOR",
      "ENCAMINHADA_A_CLICHERIA",
      "RECEBIDA_PELA_CLICHERIA",
    ]);
  });
});

/**
 * Wave 3 v4.0 / C12 — Decisao 11.2 do Gate 1: heuristica para rota=NULL
 * baseada em `vendedor_localizacao`.
 */
describe("getRotaEtapas (resolucao com heuristica)", () => {
  it("rota MATRIZ -> ROTA_ETAPAS.MATRIZ (ignora vendedor)", () => {
    expect(getRotaEtapas("MATRIZ", null)).toBe(ROTA_ETAPAS.MATRIZ);
    expect(getRotaEtapas("MATRIZ", "FILIAL")).toBe(ROTA_ETAPAS.MATRIZ);
  });

  it("rota LAM_MATRIZ -> ROTA_ETAPAS.LAM_MATRIZ", () => {
    expect(getRotaEtapas("LAM_MATRIZ", "MATRIZ")).toBe(ROTA_ETAPAS.LAM_MATRIZ);
  });

  it("rota FILIAL -> ROTA_ETAPAS.FILIAL", () => {
    expect(getRotaEtapas("FILIAL", null)).toBe(ROTA_ETAPAS.FILIAL);
  });

  it("rota LAM_FILIAL -> ROTA_ETAPAS.LAM_FILIAL", () => {
    expect(getRotaEtapas("LAM_FILIAL", "FILIAL")).toBe(ROTA_ETAPAS.LAM_FILIAL);
  });

  it("rota PADRAO -> LEGACY_ROTA_PADRAO", () => {
    expect(getRotaEtapas("PADRAO", null)).toBe(LEGACY_ROTA_PADRAO);
  });

  it("rota DIRETA -> LEGACY_ROTA_DIRETA", () => {
    expect(getRotaEtapas("DIRETA", null)).toBe(LEGACY_ROTA_DIRETA);
  });

  it("rota NULL + vendedor MATRIZ -> LEGACY_ROTA_PADRAO (heuristica)", () => {
    expect(getRotaEtapas(null, "MATRIZ")).toBe(LEGACY_ROTA_PADRAO);
  });

  it("rota NULL + vendedor FILIAL -> LEGACY_ROTA_DIRETA (heuristica — 11/11 provas em producao)", () => {
    expect(getRotaEtapas(null, "FILIAL")).toBe(LEGACY_ROTA_DIRETA);
  });

  it("rota NULL + vendedor NULL -> [] (fallback)", () => {
    expect(getRotaEtapas(null, null)).toEqual([]);
  });
});

/**
 * Wave 3 v4.0 / C12 — Decisoes 11.1 e 11.2 do Gate 1: label do header
 * da Timeline com heuristica para rota=NULL.
 */
describe("getRotaLabel (badge do header)", () => {
  it("rota MATRIZ -> 'Matriz'", () => {
    expect(getRotaLabel("MATRIZ", null)).toBe("Matriz");
  });

  it("rota LAM_MATRIZ -> 'Lam. Matriz'", () => {
    expect(getRotaLabel("LAM_MATRIZ", null)).toBe("Lam. Matriz");
  });

  it("rota FILIAL -> 'Filial'", () => {
    expect(getRotaLabel("FILIAL", null)).toBe("Filial");
  });

  it("rota LAM_FILIAL -> 'Lam. Filial'", () => {
    expect(getRotaLabel("LAM_FILIAL", null)).toBe("Lam. Filial");
  });

  it("rota PADRAO -> 'Matriz' (C12 Decisao 11.1)", () => {
    expect(getRotaLabel("PADRAO", null)).toBe("Matriz");
  });

  it("rota DIRETA -> 'Filial' (C12 Decisao 11.1)", () => {
    expect(getRotaLabel("DIRETA", null)).toBe("Filial");
  });

  it("rota NULL + vendedor MATRIZ -> 'Matriz' (heuristica)", () => {
    expect(getRotaLabel(null, "MATRIZ")).toBe("Matriz");
  });

  it("rota NULL + vendedor FILIAL -> 'Filial' (heuristica)", () => {
    expect(getRotaLabel(null, "FILIAL")).toBe("Filial");
  });

  it("rota NULL + vendedor NULL -> '—'", () => {
    expect(getRotaLabel(null, null)).toBe("—");
  });
});

/**
 * Sanity: STATUS_LABELS e STATUS_LABELS_SHORT cobrem os 17 valores
 * (Wave 3 v4.0 / C11 migration 013). A Timeline (C12) depende disto.
 */
describe("STATUS_LABELS + STATUS_LABELS_SHORT (sanity 17 valores)", () => {
  it("STATUS_LABELS tem 17 chaves", () => {
    expect(Object.keys(STATUS_LABELS)).toHaveLength(17);
  });

  it("STATUS_LABELS_SHORT tem 17 chaves", () => {
    expect(Object.keys(STATUS_LABELS_SHORT)).toHaveLength(17);
  });

  it("STATUS_LABELS e STATUS_LABELS_SHORT cobrem o mesmo dominio (sanity drift)", () => {
    expect(Object.keys(STATUS_LABELS).sort()).toEqual(
      Object.keys(STATUS_LABELS_SHORT).sort(),
    );
  });
});
