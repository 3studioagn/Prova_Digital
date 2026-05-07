import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

import {
  criarErro,
  identificarProvaPorCodigo,
  identificarProvaPorPayload,
  type ResultadoIdentificacao,
} from "@/lib/services/identificacao-prova";

/**
 * Wave 3 v4.0 / Componente 10 — testes da camada de servico desacoplada.
 *
 * Roda em `environment: node` (sem JSDOM) — qualquer regressao de
 * acoplamento com DOM/camera quebra `npx vitest run` imediatamente.
 *
 * Cobre:
 *   - Caminho payload (camera) — happy path + 4 codigos de erro
 *   - Caminho codigo (manual / C19) — happy path + 4 codigos de erro
 *   - getToken null/throw → SESSAO_EXPIRADA
 *   - Body enviado tem o campo certo (XOR)
 *   - Mensagens em pt-BR sao corretas
 *   - `criarErro` helper
 */

const TOKEN_VALIDO = "fake-jwt-token";

const MOCK_PROVA = {
  id: "00000000-0000-0000-0000-000000000001",
  nome: "Prova Teste",
  nro_requerimento: "REQ-001",
  codigo_publico: "PRV-2026-05-K3T9XB",
  cliente: "Cliente",
  vendedor_id: "00000000-0000-0000-0000-000000000002",
  vendedor_nome: "Mario",
  vendedor_localizacao: "MATRIZ",
  vendedor_setor: "VENDEDOR",
  imagem_url: "provas/2026/05/abc/arte.jpg",
  qr_code_hash: "x".repeat(64),
  status: "CRIADA",
  rota: "MATRIZ",
  ciclo_atual: 1,
  motivo_cancelamento: null,
  created_at: "2026-05-06T00:00:00Z",
  updated_at: "2026-05-06T00:00:00Z",
};

const MOCK_SCAN_RESPONSE = {
  prova: MOCK_PROVA,
  transicoes_permitidas: ["RETIRADA_PELO_VENDEDOR"],
  motivo_obrigatorio_em: [],
};

// Mock global do fetch — Vitest aceita stub via vi.stubGlobal.
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

describe("identificarProvaPorPayload (camera)", () => {
  it("retorna sucesso com payload v4.0 (codigo_publico embutido)", async () => {
    mockResposta(200, MOCK_SCAN_RESPONSE);
    const r = await identificarProvaPorPayload(
      "3SD|PRV-2026-05-K3T9XB|abcd1234567890ef",
      { getToken },
    );
    expect(r.tipo).toBe("sucesso");
    if (r.tipo === "sucesso") {
      expect(r.prova.prova.codigo_publico).toBe("PRV-2026-05-K3T9XB");
    }
  });

  it("envia o campo `payload` no body, nao o `codigo`", async () => {
    mockResposta(200, MOCK_SCAN_RESPONSE);
    await identificarProvaPorPayload("3SD|REQ-001|aaaaaaaaaaaaaaaa", {
      getToken,
    });
    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    const body = JSON.parse(init.body as string);
    expect(body.payload).toBe("3SD|REQ-001|aaaaaaaaaaaaaaaa");
    expect(body.codigo).toBeUndefined();
  });

  it("mapeia 422 do backend → QR_INVALIDO", async () => {
    mockResposta(422, { detail: "QR Code mal formado" });
    const r = await identificarProvaPorPayload("3SD|x|y", { getToken });
    expect(r.tipo).toBe("erro");
    if (r.tipo === "erro") {
      expect(r.codigo).toBe("QR_INVALIDO");
      expect(r.mensagem).toContain("QR Code");
    }
  });

  it("mapeia 404 → PROVA_NAO_ENCONTRADA com mensagem generica", async () => {
    mockResposta(404, { detail: "Prova nao encontrada" });
    const r = await identificarProvaPorPayload("3SD|x|y", { getToken });
    expect(r).toEqual<ResultadoIdentificacao>({
      tipo: "erro",
      codigo: "PROVA_NAO_ENCONTRADA",
      mensagem: "Prova nao encontrada.",
    });
  });

  it("mapeia 502 → ERRO_REDE", async () => {
    mockResposta(502, { detail: "DB indisponivel" });
    const r = await identificarProvaPorPayload("3SD|x|y", { getToken });
    expect(r.tipo).toBe("erro");
    if (r.tipo === "erro") {
      expect(r.codigo).toBe("ERRO_REDE");
    }
  });

  it("mapeia 401 → SESSAO_EXPIRADA", async () => {
    mockResposta(401, { detail: "Unauthorized" });
    const r = await identificarProvaPorPayload("3SD|x|y", { getToken });
    expect(r.tipo).toBe("erro");
    if (r.tipo === "erro") {
      expect(r.codigo).toBe("SESSAO_EXPIRADA");
    }
  });
});

describe("identificarProvaPorCodigo (manual / C19)", () => {
  it("retorna sucesso com codigo PRV valido", async () => {
    mockResposta(200, MOCK_SCAN_RESPONSE);
    const r = await identificarProvaPorCodigo("PRV-2026-05-K3T9XB", {
      getToken,
    });
    expect(r.tipo).toBe("sucesso");
  });

  it("envia o campo `codigo` no body, nao o `payload`", async () => {
    mockResposta(200, MOCK_SCAN_RESPONSE);
    await identificarProvaPorCodigo("PRV-2026-05-K3T9XB", { getToken });
    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    const body = JSON.parse(init.body as string);
    expect(body.codigo).toBe("PRV-2026-05-K3T9XB");
    expect(body.payload).toBeUndefined();
  });

  it("mapeia 404 generico para codigo formato invalido", async () => {
    mockResposta(404, { detail: "Prova nao encontrada" });
    const r = await identificarProvaPorCodigo("formato-invalido", {
      getToken,
    });
    expect(r.tipo).toBe("erro");
    if (r.tipo === "erro") {
      expect(r.codigo).toBe("PROVA_NAO_ENCONTRADA");
      // Mensagem identica a "fora do scope" — DAT §8.2 protecao contra
      // enumeracao.
      expect(r.mensagem).toBe("Prova nao encontrada.");
    }
  });

  it("mapeia 404 generico para codigo fora do scope (mesma mensagem)", async () => {
    mockResposta(404, { detail: "Prova nao encontrada" });
    const r = await identificarProvaPorCodigo("PRV-2026-05-OUTRO9", {
      getToken,
    });
    expect(r.tipo).toBe("erro");
    if (r.tipo === "erro") {
      expect(r.codigo).toBe("PROVA_NAO_ENCONTRADA");
    }
  });
});

describe("autenticacao", () => {
  it("getToken retorna null → SESSAO_EXPIRADA sem chamar fetch", async () => {
    const r = await identificarProvaPorCodigo("PRV-2026-05-K3T9XB", {
      getToken: async () => null,
    });
    expect(r.tipo).toBe("erro");
    if (r.tipo === "erro") {
      expect(r.codigo).toBe("SESSAO_EXPIRADA");
    }
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("getToken throws → SESSAO_EXPIRADA sem chamar fetch", async () => {
    const r = await identificarProvaPorCodigo("PRV-2026-05-K3T9XB", {
      getToken: async () => {
        throw new Error("storage corrupted");
      },
    });
    expect(r.tipo).toBe("erro");
    if (r.tipo === "erro") {
      expect(r.codigo).toBe("SESSAO_EXPIRADA");
    }
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("envia Authorization Bearer no header", async () => {
    mockResposta(200, MOCK_SCAN_RESPONSE);
    await identificarProvaPorCodigo("PRV-2026-05-K3T9XB", { getToken });
    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBe(`Bearer ${TOKEN_VALIDO}`);
  });
});

describe("erros de rede", () => {
  it("fetch throws → ERRO_REDE", async () => {
    fetchSpy.mockRejectedValueOnce(new TypeError("network error"));
    const r = await identificarProvaPorCodigo("PRV-2026-05-K3T9XB", {
      getToken,
    });
    expect(r.tipo).toBe("erro");
    if (r.tipo === "erro") {
      expect(r.codigo).toBe("ERRO_REDE");
    }
  });
});

describe("criarErro helper", () => {
  it("constroi ResultadoIdentificacao para cada CodigoErro", () => {
    expect(criarErro("DISPOSITIVO_SEM_CAMERA")).toEqual({
      tipo: "erro",
      codigo: "DISPOSITIVO_SEM_CAMERA",
      mensagem: "Camera indisponivel. Use a digitacao manual.",
    });
    // narrowing necessario porque ResultadoIdentificacao e tagged union.
    const r1 = criarErro("QR_INVALIDO");
    if (r1.tipo === "erro") expect(r1.mensagem).toContain("QR Code");
    const r2 = criarErro("PROVA_NAO_ENCONTRADA");
    if (r2.tipo === "erro") expect(r2.mensagem).toBe("Prova nao encontrada.");
    const r3 = criarErro("ERRO_REDE");
    if (r3.tipo === "erro") expect(r3.mensagem).toContain("conexao");
    const r4 = criarErro("SESSAO_EXPIRADA");
    if (r4.tipo === "erro") expect(r4.mensagem).toContain("sessao");
  });
});

describe("desacoplamento (regra-chave da Wave 3 v4.0)", () => {
  it("modulo nao referencia DOM, navigator, html5-qrcode etc.", async () => {
    // Importa o modulo crua e inspeciona o source. Se algum dia
    // alguem importar 'html5-qrcode' ou 'navigator', o regex pega.
    const fs = await import("node:fs/promises");
    const path = await import("node:path");
    const file = path.resolve(
      __dirname,
      "..",
      "identificacao-prova.ts",
    );
    const src = await fs.readFile(file, "utf-8");
    // Linha que importa 'html5-qrcode' OU usa 'navigator.' OU 'document.'
    // OU 'window.' indicaria acoplamento.
    expect(src).not.toMatch(/import .*html5-qrcode/);
    expect(src).not.toMatch(/\bnavigator\.|\bdocument\.|\bwindow\./);
  });
});
