/**
 * Testes dos helpers puros do fluxo de assinatura — Wave 8 v5.0 / C22.
 *
 * Cobre a logica testavel em isolamento (Decisao D11 — Opcao B: Vitest
 * para logica pura + smoke E2E manual para componente/hook). Roda em
 * `environment: node` (sem JSDOM) — os helpers nao tocam DOM.
 */
import { describe, it, expect } from "vitest";
import type {
  ProvaResponse,
  ScanResponse,
  StatusProva,
} from "@/lib/types/prova";
import { STATUS_OPTIONS } from "@/lib/types/prova";
import {
  ACTION_LABELS,
  badgeContextoMotorista,
  descricaoTransicao,
  deveAbrirAssinatura,
  exigeMotivo,
  isReprovacao,
  labelParaTransicao,
  tituloAssinatura,
} from "../helpers";

function fakeProva(over: Partial<ProvaResponse> = {}): ProvaResponse {
  return {
    id: "prova-1",
    nome: "Prova Teste",
    nro_requerimento: "REQ-001",
    codigo_publico: "PRV-2026-05-ABC234",
    cliente: "Cliente X",
    vendedor_id: "vend-1",
    vendedor_nome: "Vendedor Y",
    vendedor_localizacao: "MATRIZ",
    imagem_url: "https://example.test/img.png",
    qr_code_hash: "abcdef0123456789",
    status: "CRIADA",
    rota: "MATRIZ",
    ciclo_atual: 1,
    motivo_cancelamento: null,
    created_at: "2026-05-22T10:00:00Z",
    updated_at: "2026-05-22T10:00:00Z",
    ...over,
  };
}

function fakeScan(
  transicoes: StatusProva[],
  motivoEm: StatusProva[] = [],
  provaOver: Partial<ProvaResponse> = {},
): ScanResponse {
  return {
    prova: fakeProva(provaOver),
    transicoes_permitidas: transicoes,
    motivo_obrigatorio_em: motivoEm,
  };
}

describe("ACTION_LABELS", () => {
  it("cobre os 17 estados (exaustividade do Record)", () => {
    for (const s of STATUS_OPTIONS) {
      expect(ACTION_LABELS[s]).toBeTruthy();
    }
    expect(Object.keys(ACTION_LABELS)).toHaveLength(17);
  });

  it("estende o vocabulario v3.0 para os estados v4.0 de laminacao", () => {
    expect(ACTION_LABELS.ENCAMINHADA_PARA_LAMINACAO).toBe(
      "Encaminhar para laminacao",
    );
    expect(ACTION_LABELS.LAMINACAO_CONCLUIDA).toBe(
      "Confirmar laminacao concluida",
    );
    expect(ACTION_LABELS.COM_MOTORISTA_IDA_LAMINACAO).toContain("travessia");
    expect(ACTION_LABELS.ENCAMINHADA_PARA_O_VENDEDOR).toContain("vendedor");
  });
});

describe("labelParaTransicao", () => {
  it("retorna o verbo de acao do destino", () => {
    expect(labelParaTransicao("APROVADA_PELO_VENDEDOR")).toBe("Aprovar");
    expect(labelParaTransicao("REPROVADA_PELO_VENDEDOR")).toBe("Reprovar");
    expect(labelParaTransicao("RECEBIDA_PELA_CLICHERIA")).toBe(
      "Confirmar recebimento final",
    );
  });
});

describe("isReprovacao", () => {
  it("verdadeiro apenas para REPROVADA_PELO_VENDEDOR", () => {
    expect(isReprovacao("REPROVADA_PELO_VENDEDOR")).toBe(true);
    expect(isReprovacao("APROVADA_PELO_VENDEDOR")).toBe(false);
    expect(isReprovacao("COM_MOTORISTA_ENTREGA_FINAL")).toBe(false);
    expect(isReprovacao("CANCELADA")).toBe(false);
  });
});

describe("deveAbrirAssinatura (Decisao D6 — regra central do C22)", () => {
  it("verdadeiro com 1 transicao permitida (motorista/clicheria/3Studio)", () => {
    expect(deveAbrirAssinatura(fakeScan(["COM_MOTORISTA_IDA_LAMINACAO"]))).toBe(
      true,
    );
  });

  it("verdadeiro com 2 transicoes (vendedor — Aprovar + Reprovar)", () => {
    expect(
      deveAbrirAssinatura(
        fakeScan(["APROVADA_PELO_VENDEDOR", "REPROVADA_PELO_VENDEDOR"]),
      ),
    ).toBe(true);
  });

  it("falso quando transicoes_permitidas e vazio (ator errado in-scope)", () => {
    expect(deveAbrirAssinatura(fakeScan([]))).toBe(false);
  });

  it("falso para prova terminal sem transicoes (RECEBIDA_PELA_CLICHERIA)", () => {
    expect(
      deveAbrirAssinatura(
        fakeScan([], [], { status: "RECEBIDA_PELA_CLICHERIA" }),
      ),
    ).toBe(false);
  });

  it("falso para prova terminal CANCELADA", () => {
    expect(
      deveAbrirAssinatura(fakeScan([], [], { status: "CANCELADA" })),
    ).toBe(false);
  });
});

describe("exigeMotivo", () => {
  it("verdadeiro quando o destino consta em motivo_obrigatorio_em", () => {
    const scan = fakeScan(
      ["APROVADA_PELO_VENDEDOR", "REPROVADA_PELO_VENDEDOR"],
      ["REPROVADA_PELO_VENDEDOR"],
    );
    expect(exigeMotivo(scan, "REPROVADA_PELO_VENDEDOR")).toBe(true);
    expect(exigeMotivo(scan, "APROVADA_PELO_VENDEDOR")).toBe(false);
  });

  it("falso quando motivo_obrigatorio_em e vazio", () => {
    const scan = fakeScan(["COM_MOTORISTA_IDA_LAMINACAO"]);
    expect(exigeMotivo(scan, "COM_MOTORISTA_IDA_LAMINACAO")).toBe(false);
  });
});

describe("badgeContextoMotorista", () => {
  it("mapeia os 3 contextos do motorista v4.0", () => {
    expect(badgeContextoMotorista("COM_MOTORISTA_IDA_LAMINACAO")).toContain(
      "ida",
    );
    expect(badgeContextoMotorista("COM_MOTORISTA_VOLTA_LAMINACAO")).toContain(
      "volta",
    );
    expect(badgeContextoMotorista("COM_MOTORISTA_ENTREGA_FINAL")).toContain(
      "entrega",
    );
  });

  it("mapeia COM_MOTORISTA legacy v3.0 como entrega final (compat)", () => {
    expect(badgeContextoMotorista("COM_MOTORISTA")).toContain("entrega");
  });

  it("retorna null para transicoes que nao sao de motorista", () => {
    expect(badgeContextoMotorista("APROVADA_PELO_VENDEDOR")).toBeNull();
    expect(badgeContextoMotorista("RECEBIDA_PELA_CLICHERIA")).toBeNull();
    expect(badgeContextoMotorista("ENCAMINHADA_PARA_LAMINACAO")).toBeNull();
    expect(badgeContextoMotorista("CRIADA")).toBeNull();
  });
});

describe("descricaoTransicao", () => {
  it("formata 'estado atual -> estado destino' com labels pt-BR", () => {
    expect(descricaoTransicao("CRIADA", "RETIRADA_PELO_VENDEDOR")).toBe(
      "Aguardando vendedor → Retirada pelo vendedor",
    );
    expect(
      descricaoTransicao(
        "DE_VOLTA_3STUDIO",
        "COM_MOTORISTA_ENTREGA_FINAL",
      ),
    ).toBe("De volta a 3Studio → Com motorista (entrega final)");
  });
});

describe("tituloAssinatura", () => {
  it("titulo proprio para reprovacao e aprovacao", () => {
    expect(tituloAssinatura("REPROVADA_PELO_VENDEDOR")).toBe("Reprovar prova");
    expect(tituloAssinatura("APROVADA_PELO_VENDEDOR")).toBe("Aprovar prova");
  });

  it("titulo generico para as demais transicoes (sem duplicar 'Confirmar')", () => {
    expect(tituloAssinatura("COM_MOTORISTA_IDA_LAMINACAO")).toBe(
      "Confirmar movimentacao",
    );
    expect(tituloAssinatura("RECEBIDA_PELA_CLICHERIA")).toBe(
      "Confirmar movimentacao",
    );
    expect(tituloAssinatura("ENCAMINHADA_PARA_LAMINACAO")).toBe(
      "Confirmar movimentacao",
    );
  });
});
