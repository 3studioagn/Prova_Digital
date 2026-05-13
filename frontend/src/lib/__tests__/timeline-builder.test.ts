/**
 * Testes do `lib/timeline-builder.ts` — pipeline puro consumido pela
 * Timeline (Componente 12 v4.0).
 *
 * Cobertura:
 *   - buildTimeline para cada rota v4.0 (MATRIZ, LAM_MATRIZ, FILIAL, LAM_FILIAL)
 *   - prova legacy (rota=NULL com heuristica por vendedor + rota=PADRAO/DIRETA)
 *   - multiplos ciclos (reprovacao + reinicio)
 *   - cancelamento mid-fluxo
 *   - terminal sucesso
 *   - 3 contextos do motorista
 *   - estados pendentes calculados corretamente
 *   - movimentacoes nulas (loading) — devolve BuiltTimeline vazia coerente
 *
 * Roda em `vitest --environment node` (sem JSDOM, alinhado com D-13).
 */
import { describe, it, expect } from "vitest";

import { buildTimeline } from "@/lib/timeline-builder";
import type {
  Localizacao,
  MovimentacaoListResponse,
  MovimentacaoResponse,
  ProvaResponse,
  Rota,
  Setor,
  StatusProva,
} from "@/lib/types/prova";

// ─── Fixtures ────────────────────────────────────────────────────────────

function mkProva(overrides: Partial<ProvaResponse>): ProvaResponse {
  return {
    id: "prova-test",
    nome: "Prova teste",
    nro_requerimento: "0001",
    codigo_publico: "PRV-2026-05-XXXXXX",
    cliente: "Cliente",
    vendedor_id: "vend-1",
    vendedor_nome: "Vendedor Teste",
    vendedor_localizacao: "MATRIZ" as Localizacao,
    imagem_url: "imagens/x.jpg",
    qr_code_hash: "abcdef0123456789",
    status: "CRIADA",
    rota: null,
    ciclo_atual: 1,
    motivo_cancelamento: null,
    created_at: "2026-05-10T12:00:00Z",
    updated_at: "2026-05-10T12:00:00Z",
    ...overrides,
  };
}

let movCounter = 0;
function mkMov(
  status_anterior: StatusProva,
  status_novo: StatusProva,
  overrides: Partial<MovimentacaoResponse> = {},
): MovimentacaoResponse {
  movCounter += 1;
  return {
    id: `mov-${movCounter}`,
    prova_id: "prova-test",
    usuario_id: "user-1",
    usuario_nome: "Fulano",
    usuario_setor: "VENDEDOR" as Setor,
    status_anterior,
    status_novo,
    motivo_reprovacao: null,
    ciclo: 1,
    rota_no_momento: null,
    created_at: "2026-05-10T13:00:00Z",
    ...overrides,
  };
}

function mkMovList(items: MovimentacaoResponse[]): MovimentacaoListResponse {
  return { items, total: items.length };
}

// ─── Cenarios v4.0 (4 rotas) ─────────────────────────────────────────────

describe("buildTimeline · rotas v4.0", () => {
  it("MATRIZ · em andamento (CRIADA, sem movimentacoes) — 1 ciclo, 1 no current + 5 pendentes", () => {
    const prova = mkProva({ rota: "MATRIZ" as Rota, status: "CRIADA" });
    const result = buildTimeline(prova, mkMovList([]));

    expect(result.rotaLabel).toBe("Matriz");
    expect(result.cycles).toHaveLength(1);
    expect(result.cycles[0].phase).toBe("atual");
    expect(result.cycles[0].nodes).toHaveLength(6); // 1 current + 5 pending

    expect(result.cycles[0].nodes[0].status).toBe("CRIADA");
    expect(result.cycles[0].nodes[0].phase).toBe("current");

    const pendentes = result.cycles[0].nodes.filter(
      (n) => n.phase === "pending",
    );
    expect(pendentes).toHaveLength(5);
    expect(pendentes.map((n) => n.status)).toEqual([
      "RETIRADA_PELO_VENDEDOR",
      "APROVADA_PELO_VENDEDOR",
      "DE_VOLTA_3STUDIO",
      "COM_MOTORISTA_ENTREGA_FINAL",
      "RECEBIDA_PELA_CLICHERIA",
    ]);
  });

  it("MATRIZ · terminal sucesso — 5 movs, todos passed, sem pendentes, isTerminalOk", () => {
    const prova = mkProva({
      rota: "MATRIZ" as Rota,
      status: "RECEBIDA_PELA_CLICHERIA",
    });
    const movs = [
      mkMov("CRIADA", "RETIRADA_PELO_VENDEDOR"),
      mkMov("RETIRADA_PELO_VENDEDOR", "APROVADA_PELO_VENDEDOR"),
      mkMov("APROVADA_PELO_VENDEDOR", "DE_VOLTA_3STUDIO", {
        usuario_setor: "STUDIO" as Setor,
      }),
      mkMov("DE_VOLTA_3STUDIO", "COM_MOTORISTA_ENTREGA_FINAL", {
        usuario_setor: "MOTORISTA" as Setor,
      }),
      mkMov("COM_MOTORISTA_ENTREGA_FINAL", "RECEBIDA_PELA_CLICHERIA", {
        usuario_setor: "CLICHERIA" as Setor,
      }),
    ];
    const result = buildTimeline(prova, mkMovList(movs));

    expect(result.isTerminalOk).toBe(true);
    expect(result.isCancelled).toBe(false);
    expect(result.cycles).toHaveLength(1);

    const cycle = result.cycles[0];
    expect(cycle.nodes).toHaveLength(6); // 1 implicita + 5 reais
    expect(cycle.nodes.filter((n) => n.phase === "pending")).toHaveLength(0);
    expect(cycle.nodes.at(-1)?.isTerminal).toBe(true);
    expect(cycle.nodes.at(-1)?.status).toBe("RECEBIDA_PELA_CLICHERIA");
  });

  it("LAM_MATRIZ · em andamento na LAMINACAO_CONCLUIDA — 4 reais + 7 pendentes, bloco de laminacao marcado", () => {
    const prova = mkProva({
      rota: "LAM_MATRIZ" as Rota,
      status: "LAMINACAO_CONCLUIDA",
    });
    const movs = [
      mkMov("CRIADA", "ENCAMINHADA_PARA_LAMINACAO", {
        usuario_setor: "STUDIO" as Setor,
      }),
      mkMov("ENCAMINHADA_PARA_LAMINACAO", "COM_MOTORISTA_IDA_LAMINACAO", {
        usuario_setor: "MOTORISTA" as Setor,
      }),
      mkMov("COM_MOTORISTA_IDA_LAMINACAO", "LAMINACAO_CONCLUIDA", {
        usuario_setor: "CLICHERIA" as Setor,
      }),
    ];
    const result = buildTimeline(prova, mkMovList(movs));

    expect(result.rotaLabel).toBe("Lam. Matriz");
    expect(result.cycles).toHaveLength(1);

    const cycle = result.cycles[0];
    // 1 implicita CRIADA + 3 reais + 7 pendentes = 11 totais (estados_da_rota LAM_MATRIZ)
    expect(cycle.nodes).toHaveLength(11);

    const atualNode = cycle.nodes.find((n) => n.phase === "current");
    expect(atualNode?.status).toBe("LAMINACAO_CONCLUIDA");
    expect(atualNode?.inLaminationBlock).toBe(true);

    // Pendentes: VOLTA -> POS -> RETIRADA -> APROVADA -> DE_VOLTA -> ENTREGA -> RECEBIDA
    const pendentes = cycle.nodes.filter((n) => n.phase === "pending");
    expect(pendentes.map((n) => n.status)).toEqual([
      "COM_MOTORISTA_VOLTA_LAMINACAO",
      "DE_VOLTA_3STUDIO_POS_LAMINACAO",
      "RETIRADA_PELO_VENDEDOR",
      "APROVADA_PELO_VENDEDOR",
      "DE_VOLTA_3STUDIO",
      "COM_MOTORISTA_ENTREGA_FINAL",
      "RECEBIDA_PELA_CLICHERIA",
    ]);

    // Bloco de laminacao: 5 nos consecutivos marcados (ENCAMINHADA_PARA_LAMINACAO,
    // IDA, LAMINACAO_CONCLUIDA, VOLTA, POS — todos com inLaminationBlock=true).
    const inBloco = cycle.nodes.filter((n) => n.inLaminationBlock);
    expect(inBloco).toHaveLength(5);
  });

  it("FILIAL · em andamento (APROVADA) — 3 reais + 1 pendente", () => {
    const prova = mkProva({
      rota: "FILIAL" as Rota,
      status: "APROVADA_PELO_VENDEDOR",
      vendedor_localizacao: "FILIAL" as Localizacao,
    });
    const movs = [
      mkMov("CRIADA", "ENCAMINHADA_PARA_O_VENDEDOR", {
        usuario_setor: "VENDEDOR" as Setor,
      }),
      mkMov("ENCAMINHADA_PARA_O_VENDEDOR", "APROVADA_PELO_VENDEDOR"),
    ];
    const result = buildTimeline(prova, mkMovList(movs));

    expect(result.rotaLabel).toBe("Filial");
    expect(result.cycles[0].nodes).toHaveLength(4); // 1 implicita + 2 reais + 1 pendente

    const atualNode = result.cycles[0].nodes.find((n) => n.phase === "current");
    expect(atualNode?.status).toBe("APROVADA_PELO_VENDEDOR");

    const pendentes = result.cycles[0].nodes.filter(
      (n) => n.phase === "pending",
    );
    expect(pendentes.map((n) => n.status)).toEqual(["RECEBIDA_PELA_CLICHERIA"]);
  });

  it("LAM_FILIAL · em andamento (LAMINACAO_CONCLUIDA) — bloco de laminacao com 3 nos", () => {
    const prova = mkProva({
      rota: "LAM_FILIAL" as Rota,
      status: "LAMINACAO_CONCLUIDA",
      vendedor_localizacao: "FILIAL" as Localizacao,
    });
    const movs = [
      mkMov("CRIADA", "ENCAMINHADA_PARA_LAMINACAO", {
        usuario_setor: "STUDIO" as Setor,
      }),
      mkMov("ENCAMINHADA_PARA_LAMINACAO", "COM_MOTORISTA_IDA_LAMINACAO", {
        usuario_setor: "MOTORISTA" as Setor,
      }),
      mkMov("COM_MOTORISTA_IDA_LAMINACAO", "LAMINACAO_CONCLUIDA", {
        usuario_setor: "CLICHERIA" as Setor,
      }),
    ];
    const result = buildTimeline(prova, mkMovList(movs));

    expect(result.rotaLabel).toBe("Lam. Filial");
    // 1 implicita + 3 reais + 3 pendentes (ENC_VENDEDOR, APROVADA, RECEBIDA)
    expect(result.cycles[0].nodes).toHaveLength(7);

    // Bloco de laminacao na Lam. Filial: 3 nos (ENC_LAM + IDA + CONCLUIDA);
    // sem VOLTA/POS (sao so da LAM_MATRIZ).
    const inBloco = result.cycles[0].nodes.filter((n) => n.inLaminationBlock);
    expect(inBloco).toHaveLength(3);
  });
});

// ─── Cenario: prova legacy ───────────────────────────────────────────────

describe("buildTimeline · provas legacy v3.0", () => {
  it("rota=PADRAO -> label 'Matriz' (Decisao 11.1) + sequencia LEGACY_ROTA_PADRAO", () => {
    const prova = mkProva({
      rota: "PADRAO" as Rota,
      status: "CRIADA",
      vendedor_localizacao: "MATRIZ" as Localizacao,
    });
    const result = buildTimeline(prova, mkMovList([]));

    expect(result.rotaLabel).toBe("Matriz");
    // 1 implicita CRIADA + 6 pendentes (RETIRADA, APROVADA, DE_VOLTA,
    // COM_MOTORISTA legacy, ENVIADA_PARA_CLICHERIA, RECEBIDA)
    expect(result.cycles[0].nodes).toHaveLength(7);

    const pendentes = result.cycles[0].nodes.filter(
      (n) => n.phase === "pending",
    );
    expect(pendentes.map((n) => n.status)).toEqual([
      "RETIRADA_PELO_VENDEDOR",
      "APROVADA_PELO_VENDEDOR",
      "DE_VOLTA_3STUDIO",
      "COM_MOTORISTA",
      "ENVIADA_PARA_CLICHERIA",
      "RECEBIDA_PELA_CLICHERIA",
    ]);

    // Nao tem bloco de laminacao em legacy.
    expect(result.cycles[0].nodes.every((n) => !n.inLaminationBlock)).toBe(
      true,
    );
  });

  it("rota=DIRETA -> label 'Filial' (Decisao 11.1) + sequencia LEGACY_ROTA_DIRETA", () => {
    const prova = mkProva({
      rota: "DIRETA" as Rota,
      status: "CRIADA",
      vendedor_localizacao: "FILIAL" as Localizacao,
    });
    const result = buildTimeline(prova, mkMovList([]));

    expect(result.rotaLabel).toBe("Filial");
    // 1 implicita + 4 pendentes (RETIRADA, APROVADA, ENCAMINHADA_A_CLICHERIA, RECEBIDA)
    expect(result.cycles[0].nodes).toHaveLength(5);
  });

  it("rota=NULL + vendedor FILIAL -> heuristica DIRETA (11 provas em producao)", () => {
    const prova = mkProva({
      rota: null,
      status: "CRIADA",
      vendedor_localizacao: "FILIAL" as Localizacao,
    });
    const result = buildTimeline(prova, mkMovList([]));

    expect(result.rotaLabel).toBe("Filial");
    expect(result.cycles[0].nodes).toHaveLength(5); // LEGACY_ROTA_DIRETA
  });

  it("rota=NULL + vendedor MATRIZ -> heuristica PADRAO", () => {
    const prova = mkProva({
      rota: null,
      status: "CRIADA",
      vendedor_localizacao: "MATRIZ" as Localizacao,
    });
    const result = buildTimeline(prova, mkMovList([]));

    expect(result.rotaLabel).toBe("Matriz");
    expect(result.cycles[0].nodes).toHaveLength(7); // LEGACY_ROTA_PADRAO
  });

  it("rota=NULL + vendedor=NULL -> label '—' + sem etapas pendentes (fallback)", () => {
    const prova = mkProva({
      rota: null,
      status: "CRIADA",
      vendedor_localizacao: null,
    });
    const result = buildTimeline(prova, mkMovList([]));

    expect(result.rotaLabel).toBe("—");
    expect(result.cycles[0].nodes).toHaveLength(1); // so a CRIADA implicita, sem pendentes
  });
});

// ─── Cenario: multiplos ciclos ───────────────────────────────────────────

describe("buildTimeline · multiplos ciclos (reprovacao + reinicio)", () => {
  it("ciclo 1 reprovado + ciclo 2 atual — 2 grupos, fase correta", () => {
    const prova = mkProva({
      rota: "MATRIZ" as Rota,
      status: "RETIRADA_PELO_VENDEDOR",
      ciclo_atual: 2,
    });
    const movs = [
      mkMov("CRIADA", "RETIRADA_PELO_VENDEDOR", {
        usuario_setor: "VENDEDOR" as Setor,
        ciclo: 1,
      }),
      mkMov("RETIRADA_PELO_VENDEDOR", "REPROVADA_PELO_VENDEDOR", {
        usuario_setor: "VENDEDOR" as Setor,
        usuario_nome: "Joao",
        motivo_reprovacao: "Cor errada",
        ciclo: 1,
        created_at: "2026-05-11T10:00:00Z",
      }),
      mkMov("REPROVADA_PELO_VENDEDOR", "CRIADA", {
        usuario_setor: "STUDIO" as Setor,
        ciclo: 2,
        created_at: "2026-05-11T14:00:00Z",
      }),
      mkMov("CRIADA", "RETIRADA_PELO_VENDEDOR", {
        usuario_setor: "VENDEDOR" as Setor,
        ciclo: 2,
        created_at: "2026-05-11T16:00:00Z",
      }),
    ];
    const result = buildTimeline(prova, mkMovList(movs));

    expect(result.hasMultipleCycles).toBe(true);
    expect(result.cycles).toHaveLength(2);

    // Ciclo 1: reprovado
    const c1 = result.cycles[0];
    expect(c1.ciclo).toBe(1);
    expect(c1.phase).toBe("passed-reprovacao");
    expect(c1.motivoReprovacao).toBe("Cor errada");
    expect(c1.reprovadoPor?.nome).toBe("Joao");
    expect(c1.reprovadoEm).toBe("2026-05-11T10:00:00Z");
    // ciclo 1 NAO tem pendentes
    expect(c1.nodes.every((n) => n.phase !== "pending")).toBe(true);

    // Ciclo 2: atual
    const c2 = result.cycles[1];
    expect(c2.ciclo).toBe(2);
    expect(c2.phase).toBe("atual");
    expect(c2.motivoReprovacao).toBe(null);
    // ciclo 2 tem pendentes (estamos em RETIRADA, faltam 4)
    const c2Pendentes = c2.nodes.filter((n) => n.phase === "pending");
    expect(c2Pendentes.map((n) => n.status)).toEqual([
      "APROVADA_PELO_VENDEDOR",
      "DE_VOLTA_3STUDIO",
      "COM_MOTORISTA_ENTREGA_FINAL",
      "RECEBIDA_PELA_CLICHERIA",
    ]);
  });

  it("prova reprovada (status atual REPROVADA) — sem pendentes, fica esperando reinicio", () => {
    const prova = mkProva({
      rota: "MATRIZ" as Rota,
      status: "REPROVADA_PELO_VENDEDOR",
      ciclo_atual: 1,
    });
    const movs = [
      mkMov("CRIADA", "RETIRADA_PELO_VENDEDOR", {
        usuario_setor: "VENDEDOR" as Setor,
      }),
      mkMov("RETIRADA_PELO_VENDEDOR", "REPROVADA_PELO_VENDEDOR", {
        usuario_setor: "VENDEDOR" as Setor,
        motivo_reprovacao: "Texto borrado",
      }),
    ];
    const result = buildTimeline(prova, mkMovList(movs));

    expect(result.cycles).toHaveLength(1);
    expect(result.cycles[0].phase).toBe("passed-reprovacao");
    expect(result.cycles[0].nodes.every((n) => n.phase !== "pending")).toBe(
      true,
    );
  });
});

// ─── Cenario: cancelamento ───────────────────────────────────────────────

describe("buildTimeline · cancelamento", () => {
  it("Matriz cancelada mid-ciclo — extractCancellationInfo preenchido + sem pendentes", () => {
    const prova = mkProva({
      rota: "MATRIZ" as Rota,
      status: "CANCELADA",
      motivo_cancelamento: "Cliente desistiu",
    });
    const movs = [
      mkMov("CRIADA", "RETIRADA_PELO_VENDEDOR", {
        usuario_setor: "VENDEDOR" as Setor,
      }),
      mkMov("RETIRADA_PELO_VENDEDOR", "CANCELADA", {
        usuario_setor: "STUDIO" as Setor,
        usuario_nome: "Maria Admin",
        created_at: "2026-05-12T15:00:00Z",
      }),
    ];
    const result = buildTimeline(prova, mkMovList(movs));

    expect(result.isCancelled).toBe(true);
    expect(result.cancellation).not.toBe(null);
    expect(result.cancellation?.motivo).toBe("Cliente desistiu");
    expect(result.cancellation?.ator?.nome).toBe("Maria Admin");
    expect(result.cancellation?.ator?.setor).toBe("STUDIO");
    expect(result.cancellation?.quandoIso).toBe("2026-05-12T15:00:00Z");

    expect(result.cycles[0].nodes.every((n) => n.phase !== "pending")).toBe(
      true,
    );
  });

  it("prova ativa (nao-cancelada) — cancellation eh null", () => {
    const prova = mkProva({ rota: "MATRIZ" as Rota, status: "CRIADA" });
    const result = buildTimeline(prova, mkMovList([]));
    expect(result.isCancelled).toBe(false);
    expect(result.cancellation).toBe(null);
  });
});

// ─── Cenario: contextos do motorista ─────────────────────────────────────

describe("buildTimeline · contextos do motorista", () => {
  it("LAM_MATRIZ · ida_laminacao corretamente derivado", () => {
    const prova = mkProva({
      rota: "LAM_MATRIZ" as Rota,
      status: "COM_MOTORISTA_IDA_LAMINACAO",
    });
    const movs = [
      mkMov("CRIADA", "ENCAMINHADA_PARA_LAMINACAO", {
        usuario_setor: "STUDIO" as Setor,
      }),
      mkMov("ENCAMINHADA_PARA_LAMINACAO", "COM_MOTORISTA_IDA_LAMINACAO", {
        usuario_setor: "MOTORISTA" as Setor,
      }),
    ];
    const result = buildTimeline(prova, mkMovList(movs));
    const motoristaNode = result.cycles[0].nodes.find(
      (n) => n.status === "COM_MOTORISTA_IDA_LAMINACAO",
    );
    expect(motoristaNode?.contexto).toBe("ida_laminacao");
  });

  it("LAM_MATRIZ · volta_laminacao corretamente derivado", () => {
    const prova = mkProva({
      rota: "LAM_MATRIZ" as Rota,
      status: "COM_MOTORISTA_VOLTA_LAMINACAO",
    });
    const movs = [
      mkMov("LAMINACAO_CONCLUIDA", "COM_MOTORISTA_VOLTA_LAMINACAO", {
        usuario_setor: "MOTORISTA" as Setor,
      }),
    ];
    const result = buildTimeline(prova, mkMovList(movs));
    const motoristaNode = result.cycles[0].nodes.find(
      (n) => n.status === "COM_MOTORISTA_VOLTA_LAMINACAO",
    );
    expect(motoristaNode?.contexto).toBe("volta_laminacao");
  });

  it("MATRIZ · entrega_final corretamente derivado", () => {
    const prova = mkProva({
      rota: "MATRIZ" as Rota,
      status: "COM_MOTORISTA_ENTREGA_FINAL",
    });
    const movs = [
      mkMov("DE_VOLTA_3STUDIO", "COM_MOTORISTA_ENTREGA_FINAL", {
        usuario_setor: "MOTORISTA" as Setor,
      }),
    ];
    const result = buildTimeline(prova, mkMovList(movs));
    const motoristaNode = result.cycles[0].nodes.find(
      (n) => n.status === "COM_MOTORISTA_ENTREGA_FINAL",
    );
    expect(motoristaNode?.contexto).toBe("entrega_final");
  });
});

// ─── Cenario: edge cases ─────────────────────────────────────────────────

describe("buildTimeline · edge cases", () => {
  it("movimentacoes=null (loading) -> BuiltTimeline vazia coerente", () => {
    const prova = mkProva({ rota: "MATRIZ" as Rota });
    const result = buildTimeline(prova, null);
    expect(result.cycles).toEqual([]);
    expect(result.rotaLabel).toBe("Matriz");
    expect(result.hasMultipleCycles).toBe(false);
    expect(result.isTerminalOk).toBe(false);
    expect(result.isCancelled).toBe(false);
    expect(result.cancellation).toBe(null);
  });

  it("sem movimentacoes mas com rota v4.0 -> CRIADA implicita atual + pendentes", () => {
    const prova = mkProva({ rota: "MATRIZ" as Rota, status: "CRIADA" });
    const result = buildTimeline(prova, mkMovList([]));
    expect(result.cycles).toHaveLength(1);
    expect(result.cycles[0].nodes[0].status).toBe("CRIADA");
    expect(result.cycles[0].nodes[0].phase).toBe("current");
  });

  it("sem rota nem vendedor_localizacao + status v3.0 -> renderiza so historico (sem pendentes)", () => {
    const prova = mkProva({
      rota: null,
      vendedor_localizacao: null,
      status: "RETIRADA_PELO_VENDEDOR",
    });
    const movs = [
      mkMov("CRIADA", "RETIRADA_PELO_VENDEDOR", {
        usuario_setor: "VENDEDOR" as Setor,
      }),
    ];
    const result = buildTimeline(prova, mkMovList(movs));
    expect(result.rotaLabel).toBe("—");
    expect(result.cycles[0].nodes.every((n) => n.phase !== "pending")).toBe(
      true,
    );
  });
});
