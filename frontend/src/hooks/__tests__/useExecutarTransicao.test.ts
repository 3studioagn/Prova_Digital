import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

import {
  executarTransicaoRequest,
  type ExecutarTransicaoInput,
} from "@/hooks/useExecutarTransicao";

/**
 * Testes da camada pura do `useExecutarTransicao` — Wave 8 v5.0 / C22.
 *
 * Cobertura proposta no plano (AUD-W8C22-005):
 *   1. 201 sucesso
 *   2. 401 sessao expirada
 *   3. 404 prova nao encontrada
 *   4. 409 race condition (isConflict=true)
 *   5. 422 + texto que LISTA setores → mensagem generica (cobre AUD-003)
 *   6. 5xx (502/503) → mensagem de falha de conexao
 *   7. 403 (demais status) → mensagem generica (cobre branch else do AUD-003)
 *   8. fetch throws (rede caiu) → status=null + mensagem generica
 *   9. getToken null → SESSAO_EXPIRADA sem chamar fetch
 *  10. getToken throw → SESSAO_EXPIRADA sem chamar fetch
 *  11. envia Authorization Bearer no header
 *  12. envia o body com status_novo, assinatura_base64, motivo_reprovacao
 *
 * Roda em `environment: node` — extraida da funcao pura
 * `executarTransicaoRequest`, sem JSDOM nem `@testing-library/react`,
 * espelhando o padrao de `identificacao-prova.test.ts` (cultura D-13).
 */

const TOKEN_VALIDO = "fake-jwt-token";

const INPUT_OK: ExecutarTransicaoInput = {
  provaId: "00000000-0000-0000-0000-000000000001",
  statusNovo: "APROVADA_PELO_VENDEDOR",
  assinaturaBase64: "AAAA",
  motivoReprovacao: null,
};

const MOCK_TRANSICAO_RESPONSE = {
  prova: {
    id: "00000000-0000-0000-0000-000000000001",
    nome: "Prova Teste",
    nro_requerimento: "REQ-001",
    codigo_publico: "PRV-2026-05-K3T9XB",
    cliente: "Cliente",
    vendedor_id: "00000000-0000-0000-0000-000000000002",
    vendedor_nome: "Mario",
    vendedor_localizacao: "MATRIZ",
    imagem_url: "provas/2026/05/abc/arte.jpg",
    qr_code_hash: "x".repeat(64),
    status: "APROVADA_PELO_VENDEDOR",
    rota: "MATRIZ",
    ciclo_atual: 1,
    motivo_cancelamento: null,
    created_at: "2026-05-22T10:00:00Z",
    updated_at: "2026-05-22T10:00:00Z",
  },
  movimentacao: {
    id: "mov-1",
    status_anterior: "RETIRADA_PELO_VENDEDOR",
    status_novo: "APROVADA_PELO_VENDEDOR",
    ator_id: "00000000-0000-0000-0000-000000000002",
    ator_nome: "Mario",
    motivo_reprovacao: null,
    ciclo: 1,
    rota_no_momento: "MATRIZ",
    created_at: "2026-05-22T10:01:00Z",
  },
};

let fetchSpy: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchSpy = vi.fn();
  vi.stubGlobal("fetch", fetchSpy);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

const getToken = async () => TOKEN_VALIDO;

function mockResposta(status: number, body: unknown) {
  fetchSpy.mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response);
}

describe("executarTransicaoRequest — happy path", () => {
  it("retorna { data, status=201, isConflict=false, error=null } para 201", async () => {
    mockResposta(201, MOCK_TRANSICAO_RESPONSE);
    const r = await executarTransicaoRequest(INPUT_OK, { getToken });
    expect(r.data).toEqual(MOCK_TRANSICAO_RESPONSE);
    expect(r.status).toBe(201);
    expect(r.isConflict).toBe(false);
    expect(r.error).toBeNull();
  });
});

describe("executarTransicaoRequest — erros mapeados", () => {
  it("401 → status=401 + mensagem 'Sessao expirada...'", async () => {
    mockResposta(401, { detail: "Unauthorized" });
    const r = await executarTransicaoRequest(INPUT_OK, { getToken });
    expect(r.data).toBeNull();
    expect(r.status).toBe(401);
    expect(r.error).toBe("Sessao expirada. Faca login novamente.");
    expect(r.isConflict).toBe(false);
  });

  it("404 → status=404 + mensagem 'Prova nao encontrada.'", async () => {
    mockResposta(404, { detail: "Prova nao encontrada" });
    const r = await executarTransicaoRequest(INPUT_OK, { getToken });
    expect(r.status).toBe(404);
    expect(r.error).toBe("Prova nao encontrada.");
    expect(r.isConflict).toBe(false);
  });

  it("409 → status=409 + isConflict=true + mensagem 'O status da prova mudou...'", async () => {
    mockResposta(409, { detail: "Transicao invalida — status mudou" });
    const r = await executarTransicaoRequest(INPUT_OK, { getToken });
    expect(r.status).toBe(409);
    expect(r.isConflict).toBe(true);
    expect(r.error).toBe("O status da prova mudou. Escaneie novamente.");
  });

  it("502 → status=502 + mensagem 'Falha de conexao...'", async () => {
    mockResposta(502, { detail: "DB indisponivel" });
    const r = await executarTransicaoRequest(INPUT_OK, { getToken });
    expect(r.status).toBe(502);
    expect(r.error).toBe(
      "Falha de conexao. Tente novamente em instantes.",
    );
    expect(r.isConflict).toBe(false);
  });

  it("503 (>=500) tambem → 'Falha de conexao...'", async () => {
    mockResposta(503, { detail: "service unavailable" });
    const r = await executarTransicaoRequest(INPUT_OK, { getToken });
    expect(r.status).toBe(503);
    expect(r.error).toBe(
      "Falha de conexao. Tente novamente em instantes.",
    );
  });

  it("rede caiu (fetch throws) → status=null + mensagem padrao", async () => {
    fetchSpy.mockRejectedValueOnce(new TypeError("network error"));
    const r = await executarTransicaoRequest(INPUT_OK, { getToken });
    expect(r.data).toBeNull();
    expect(r.status).toBeNull();
    expect(r.isConflict).toBe(false);
    expect(r.error).toBe("Nao foi possivel executar a transicao.");
  });
});

describe("executarTransicaoRequest — AUD-W8C22-003 (anti-enumeracao 422 + outros)", () => {
  it("422 com texto que LISTA setores → mensagem GENERICA (nao vaza setor)", async () => {
    // Simula o pior caso: backend retorna `AtorNaoAutorizadoError` cuja
    // mensagem original LISTAVA setores permitidos.
    mockResposta(422, {
      detail:
        "Apenas usuarios do setor VENDEDOR ou MOTORISTA podem executar esta transicao",
    });
    const r = await executarTransicaoRequest(INPUT_OK, { getToken });
    expect(r.status).toBe(422);
    // Asserção que falha se o hook voltar a expor `err.message` cru.
    expect(r.error).not.toContain("setor");
    expect(r.error).not.toContain("VENDEDOR");
    expect(r.error).not.toContain("MOTORISTA");
    // Mensagem generica fixa esperada (paridade com plano AUD-003):
    expect(r.error).toBe("Nao foi possivel registrar a movimentacao.");
  });

  it("403 (e demais status nao-mapeados) → mensagem GENERICA padrao", async () => {
    mockResposta(403, { detail: "Forbidden — perfil X nao pode Y" });
    const r = await executarTransicaoRequest(INPUT_OK, { getToken });
    expect(r.status).toBe(403);
    // Mesma defesa do AUD-003: branch "else" tambem nao vaza err.message.
    expect(r.error).not.toContain("Forbidden");
    expect(r.error).not.toContain("perfil");
    expect(r.error).toBe("Nao foi possivel executar a transicao.");
  });
});

describe("executarTransicaoRequest — autenticacao", () => {
  it("getToken retorna null → status=401 sem chamar fetch", async () => {
    const r = await executarTransicaoRequest(INPUT_OK, {
      getToken: async () => null,
    });
    expect(r.status).toBe(401);
    expect(r.error).toBe("Sessao expirada. Faca login novamente.");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("getToken throws → status=401 sem chamar fetch", async () => {
    const r = await executarTransicaoRequest(INPUT_OK, {
      getToken: async () => {
        throw new Error("storage corrupted");
      },
    });
    expect(r.status).toBe(401);
    expect(r.error).toBe("Sessao expirada. Faca login novamente.");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("envia Authorization Bearer no header", async () => {
    mockResposta(201, MOCK_TRANSICAO_RESPONSE);
    await executarTransicaoRequest(INPUT_OK, { getToken });
    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBe(`Bearer ${TOKEN_VALIDO}`);
  });
});

describe("executarTransicaoRequest — body da requisicao", () => {
  it("envia status_novo, assinatura_base64 e motivo_reprovacao (string)", async () => {
    mockResposta(201, MOCK_TRANSICAO_RESPONSE);
    await executarTransicaoRequest(
      {
        ...INPUT_OK,
        statusNovo: "REPROVADA_PELO_VENDEDOR",
        motivoReprovacao: "Cor do logo errada",
      },
      { getToken },
    );
    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    const body = JSON.parse(init.body as string);
    expect(body.status_novo).toBe("REPROVADA_PELO_VENDEDOR");
    expect(body.assinatura_base64).toBe(INPUT_OK.assinaturaBase64);
    expect(body.motivo_reprovacao).toBe("Cor do logo errada");
  });

  it("envia motivo_reprovacao=null quando nao informado (undefined)", async () => {
    mockResposta(201, MOCK_TRANSICAO_RESPONSE);
    await executarTransicaoRequest(
      {
        provaId: INPUT_OK.provaId,
        statusNovo: "APROVADA_PELO_VENDEDOR",
        assinaturaBase64: INPUT_OK.assinaturaBase64,
        // motivoReprovacao omitido
      },
      { getToken },
    );
    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    const body = JSON.parse(init.body as string);
    expect(body.motivo_reprovacao).toBeNull();
  });

  it("chama o endpoint /api/v1/provas/{provaId}/transicoes", async () => {
    mockResposta(201, MOCK_TRANSICAO_RESPONSE);
    await executarTransicaoRequest(INPUT_OK, { getToken });
    const url = fetchSpy.mock.calls[0][0] as string;
    expect(url).toContain(`/api/v1/provas/${INPUT_OK.provaId}/transicoes`);
  });
});
