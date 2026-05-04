import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest, NextResponse } from "next/server";

/**
 * Wave 1 v4.0 — Audit Round 2 (AUD-W1V4-005).
 *
 * Suite de testes do middleware RBAC. Cobre os caminhos de decisao do
 * `updateSession` para validar a defesa em profundidade na camada
 * superior (Next middleware) — anteriormente sem teste unitario,
 * apenas smoke preview anonimo.
 *
 * Cenarios cobertos:
 *  - Funcoes puras de access-matrix (getRuleForPath com/sem trailing
 *    slash; isPublicPath via comportamento observado).
 *  - updateSession com perfis distintos (admin/vendedor/anonimo) e
 *    validacao de side-effects (redirect URL, cookie auth-toast com
 *    flag Secure conforme NODE_ENV — H-2; rejeicao de user com
 *    ativo=false — H-1; injecao de header x-rbac-scope em PARCIAL).
 *  - Comportamento do cache LRU (PROFILE_CACHE TTL 30s) entre 2
 *    chamadas consecutivas para o mesmo auth_uid.
 *
 * Mocks:
 *  - `@supabase/ssr.createServerClient` retorna client com `auth.getUser`
 *    e `from(...).select(...).eq(...).maybeSingle()` controlados via
 *    `vi.fn()`.
 *  - `NextRequest`/`NextResponse` sao usados de verdade (next/server
 *    funciona em ambiente node do Vitest).
 */

// ── Mocks ─────────────────────────────────────────────────────────────

const mockGetUser = vi.fn();
const mockMaybeSingle = vi.fn();

vi.mock("@supabase/ssr", () => ({
  createServerClient: vi.fn(() => ({
    auth: {
      getUser: mockGetUser,
    },
    from: () => ({
      select: () => ({
        eq: () => ({
          maybeSingle: mockMaybeSingle,
        }),
      }),
    }),
  })),
}));

// Importar APOS vi.mock para que o middleware veja o mock.
import { updateSession } from "../middleware";
import { getRuleForPath, getRuleByKey, evaluateRule } from "../../access-matrix";

// ── Helpers ───────────────────────────────────────────────────────────

function makeRequest(pathname: string): NextRequest {
  const url = new URL(`http://localhost${pathname}`);
  // NextRequest precisa de objeto com a interface Request; o construtor
  // aceita uma string URL.
  return new NextRequest(url);
}

const ADMIN_USER = { id: "admin-uid-001" };
const VENDEDOR_USER = { id: "vendedor-uid-002" };

const ADMIN_PROFILE = {
  id: "admin-id-001",
  setor: "STUDIO",
  is_admin: true,
  ativo: true,
};
const VENDEDOR_PROFILE = {
  id: "vendedor-id-002",
  setor: "VENDEDOR",
  is_admin: false,
  ativo: true,
};
const VENDEDOR_INATIVO_PROFILE = {
  id: "vendedor-id-002",
  setor: "VENDEDOR",
  is_admin: false,
  ativo: false,
};

beforeEach(() => {
  vi.clearAllMocks();
  // Limpar cache LRU em memoria entre testes — o middleware mantem um
  // Map module-level. Como nao ha API publica para clear, usamos TTL=0
  // implicito via clearAllMocks + delay artificial nao se aplica. Ao
  // inves disso, cada teste usa um auth_uid unico para evitar colisao.
});

// ── Funcoes puras (access-matrix) ─────────────────────────────────────

describe("getRuleForPath (pure)", () => {
  it("resolve /auditoria via prefix match", () => {
    const rule = getRuleForPath("/auditoria");
    expect(rule).not.toBeNull();
    expect(rule!.key).toBe("auditoria");
  });

  it("normaliza trailing slash (M-4): /auditoria/ deve bater igual /auditoria", () => {
    const ruleWithSlash = getRuleForPath("/auditoria/");
    const ruleNoSlash = getRuleForPath("/auditoria");
    expect(ruleWithSlash).not.toBeNull();
    expect(ruleWithSlash!.key).toBe(ruleNoSlash!.key);
  });

  it("retorna null para path nao mapeado (pass-through defensivo — AUD-W1V4-102)", () => {
    expect(getRuleForPath("/rota-inexistente-xyz")).toBeNull();
  });

  it("/provas/[id] via dynamic match", () => {
    const rule = getRuleForPath("/provas/abc-123-uuid");
    expect(rule).not.toBeNull();
    expect(rule!.key).toBe("provas.detail");
  });

  it("evaluateRule: vendedor em /auditoria deve ser NEGADO", () => {
    const rule = getRuleByKey("auditoria")!;
    const decision = evaluateRule(rule, {
      setor: "VENDEDOR",
      is_admin: false,
    });
    expect(decision.acesso).toBe("negado");
  });

  it("evaluateRule: vendedor em /provas (list) deve ser PARCIAL self_vendedor", () => {
    const rule = getRuleByKey("provas.list")!;
    const decision = evaluateRule(rule, {
      setor: "VENDEDOR",
      is_admin: false,
    });
    expect(decision.acesso).toBe("parcial");
    expect(decision.scope).toBe("self_vendedor");
  });
});

// ── updateSession (orquestrador) ──────────────────────────────────────

describe("updateSession — anonimo", () => {
  it("redireciona para /login em rota nao-publica sem user", async () => {
    mockGetUser.mockResolvedValue({ data: { user: null } });

    const req = makeRequest("/dashboard");
    const res = await updateSession(req);

    // NextResponse.redirect retorna status 307 ou 302; checa via location
    expect(res.headers.get("location")).toContain("/login");
  });

  it("permite pass-through em rota publica (/login) sem user", async () => {
    mockGetUser.mockResolvedValue({ data: { user: null } });

    const req = makeRequest("/login");
    const res = await updateSession(req);

    // Pass-through: nao redireciona
    expect(res.headers.get("location")).toBeNull();
  });
});

describe("updateSession — admin (full em todas)", () => {
  it("permite pass-through em /auditoria (admin only, full)", async () => {
    mockGetUser.mockResolvedValue({
      data: { user: { id: "admin-pass-001" } },
    });
    mockMaybeSingle.mockResolvedValue({
      data: { ...ADMIN_PROFILE, id: "admin-pass-001" },
      error: null,
    });

    const req = makeRequest("/auditoria");
    const res = await updateSession(req);

    expect(res.headers.get("location")).toBeNull(); // sem redirect
    expect(res.headers.get("x-rbac-scope")).toBeNull(); // admin = full, sem header
  });
});

describe("updateSession — vendedor", () => {
  it("redireciona /auditoria -> homeForProfile com cookie auth-toast (rota_negada)", async () => {
    mockGetUser.mockResolvedValue({
      data: { user: { id: "vend-deny-001" } },
    });
    mockMaybeSingle.mockResolvedValue({
      data: { ...VENDEDOR_PROFILE, id: "vend-deny-001" },
      error: null,
    });

    const req = makeRequest("/auditoria");
    const res = await updateSession(req);

    // Vendedor: home = /dashboard
    expect(res.headers.get("location")).toContain("/dashboard");
    // Cookie auth-toast setado
    const setCookieHeader = res.headers.get("set-cookie") || "";
    expect(setCookieHeader).toContain("auth-toast");
    expect(setCookieHeader).toContain("rota_negada");
  });

  it("PARCIAL em /provas: pass-through + header x-rbac-scope com self_vendedor", async () => {
    mockGetUser.mockResolvedValue({
      data: { user: { id: "vend-parcial-002" } },
    });
    mockMaybeSingle.mockResolvedValue({
      data: { ...VENDEDOR_PROFILE, id: "vend-parcial-002" },
      error: null,
    });

    const req = makeRequest("/provas");
    const res = await updateSession(req);

    expect(res.headers.get("location")).toBeNull(); // pass-through
    const xrbac = res.headers.get("x-rbac-scope");
    expect(xrbac).not.toBeNull();
    expect(xrbac).toContain("self_vendedor");
    expect(xrbac).toContain("vend-parcial-002");
  });
});

describe("updateSession — defesa H-1 (ativo=false)", () => {
  it("user com ativo=false e tratado como perfil ausente -> /login + cookie", async () => {
    mockGetUser.mockResolvedValue({
      data: { user: { id: "vend-inativo-003" } },
    });
    mockMaybeSingle.mockResolvedValue({
      data: { ...VENDEDOR_INATIVO_PROFILE, id: "vend-inativo-003" },
      error: null,
    });

    const req = makeRequest("/auditoria");
    const res = await updateSession(req);

    expect(res.headers.get("location")).toContain("/login");
    const setCookieHeader = res.headers.get("set-cookie") || "";
    expect(setCookieHeader).toContain("perfil_ausente");
  });
});

describe("updateSession — defesa H-2 (cookie Secure por NODE_ENV)", () => {
  const originalNodeEnv = process.env.NODE_ENV;

  it("em production, cookie auth-toast tem flag Secure", async () => {
    // @ts-expect-error: NODE_ENV e readonly em algumas tipagens
    process.env.NODE_ENV = "production";

    mockGetUser.mockResolvedValue({
      data: { user: { id: "vend-h2-prod-004" } },
    });
    mockMaybeSingle.mockResolvedValue({
      data: { ...VENDEDOR_PROFILE, id: "vend-h2-prod-004" },
      error: null,
    });

    const req = makeRequest("/auditoria");
    const res = await updateSession(req);

    const setCookieHeader = res.headers.get("set-cookie") || "";
    expect(setCookieHeader.toLowerCase()).toContain("secure");

    // @ts-expect-error: restaurar
    process.env.NODE_ENV = originalNodeEnv;
  });

  it("em development, cookie auth-toast NAO tem flag Secure", async () => {
    // @ts-expect-error: idem
    process.env.NODE_ENV = "development";

    mockGetUser.mockResolvedValue({
      data: { user: { id: "vend-h2-dev-005" } },
    });
    mockMaybeSingle.mockResolvedValue({
      data: { ...VENDEDOR_PROFILE, id: "vend-h2-dev-005" },
      error: null,
    });

    const req = makeRequest("/auditoria");
    const res = await updateSession(req);

    const setCookieHeader = res.headers.get("set-cookie") || "";
    expect(setCookieHeader.toLowerCase()).not.toContain("secure");

    // @ts-expect-error: restaurar
    process.env.NODE_ENV = originalNodeEnv;
  });
});

describe("updateSession — cache LRU (PROFILE_TTL_MS = 30s)", () => {
  it("segunda chamada para mesmo auth_uid nao dispara nova query SQL", async () => {
    mockGetUser.mockResolvedValue({
      data: { user: { id: "vend-cache-006" } },
    });
    mockMaybeSingle.mockResolvedValue({
      data: { ...VENDEDOR_PROFILE, id: "vend-cache-006" },
      error: null,
    });

    // Chamada 1: cache miss
    await updateSession(makeRequest("/provas"));
    expect(mockMaybeSingle).toHaveBeenCalledTimes(1);

    // Chamada 2: mesmo auth_uid, dentro do TTL (cache hit)
    await updateSession(makeRequest("/provas"));
    expect(mockMaybeSingle).toHaveBeenCalledTimes(1); // nao incrementou
  });
});
