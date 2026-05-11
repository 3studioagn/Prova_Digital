import { describe, it, expect } from "vitest";

import {
  ALFABETO_SUFIXO,
  CODIGO_PUBLICO_REGEX,
  CODIGO_PUBLICO_TOTAL_LEN,
  DISPLAY_TOTAL_LEN,
  aplicarMascara,
  isCharValidoEmPosicaoSemHifen,
  isDisplayCompleto,
  montarCodigoCompleto,
  validarFormatoCodigoPublico,
} from "@/lib/codigo-publico";

/**
 * Wave 3 v4.0 / Componente 19 — testes do util de codigo publico.
 *
 * Roda em `environment: node` (vitest.config.ts) — modulo e puro.
 *
 * Cobre:
 *   - Paridade com regex backend (`validar_formato_codigo_publico`)
 *   - Mascara incremental (paste, parcial, completo)
 *   - Bloqueio rigido por posicao (alfabeto do sufixo nao se aplica ao ano/mes)
 *   - Idempotencia de aplicarMascara
 *   - Strip do prefixo "PRV-" em paste
 *   - Concatenacao final em montarCodigoCompleto
 */

describe("constants", () => {
  it("alfabeto do sufixo tem 31 chars sem ambiguos (DAT §8.3)", () => {
    expect(ALFABETO_SUFIXO).toBe("ABCDEFGHJKMNPQRSTUVWXYZ23456789");
    expect(ALFABETO_SUFIXO.length).toBe(31);
    // Sem 0/O/1/I/L
    expect(ALFABETO_SUFIXO).not.toMatch(/[0OIL1]/);
  });

  it("tamanhos canonicos batem com o backend", () => {
    expect(CODIGO_PUBLICO_TOTAL_LEN).toBe(18);
    expect(DISPLAY_TOTAL_LEN).toBe(14);
  });
});

describe("validarFormatoCodigoPublico (paridade com backend)", () => {
  // ─── Casos validos canonicos ───────────────────────────────────────
  it.each([
    "PRV-2026-05-K3T9XB",
    "PRV-2026-04-9PQYW2",
    "PRV-2024-01-AAAAAA",
    "PRV-2099-12-Z9Z9Z9",
    "PRV-2026-09-23456789".slice(0, 18), // sanity: trunca para 6 sufixo
  ])("aceita codigo canonico: %s", (codigo) => {
    expect(validarFormatoCodigoPublico(codigo)).toBe(true);
  });

  // ─── Casos invalidos: prefixo ──────────────────────────────────────
  it("rejeita prefixo errado", () => {
    expect(validarFormatoCodigoPublico("PRX-2026-05-K3T9XB")).toBe(false);
    expect(validarFormatoCodigoPublico("prv-2026-05-K3T9XB")).toBe(false);
    expect(validarFormatoCodigoPublico("PRV-2026-05_K3T9XB")).toBe(false);
  });

  // ─── Casos invalidos: ano/mes ──────────────────────────────────────
  it("rejeita ano nao-digito", () => {
    expect(validarFormatoCodigoPublico("PRV-A026-05-K3T9XB")).toBe(false);
    expect(validarFormatoCodigoPublico("PRV-202B-05-K3T9XB")).toBe(false);
  });

  it("rejeita mes fora de 01-12", () => {
    expect(validarFormatoCodigoPublico("PRV-2026-00-K3T9XB")).toBe(false);
    expect(validarFormatoCodigoPublico("PRV-2026-13-K3T9XB")).toBe(false);
    expect(validarFormatoCodigoPublico("PRV-2026-99-K3T9XB")).toBe(false);
  });

  // ─── Casos invalidos: sufixo ───────────────────────────────────────
  it("rejeita sufixo com chars ambiguos (0, O, 1, I, L)", () => {
    expect(validarFormatoCodigoPublico("PRV-2026-05-0AAAAA")).toBe(false);
    expect(validarFormatoCodigoPublico("PRV-2026-05-OAAAAA")).toBe(false);
    expect(validarFormatoCodigoPublico("PRV-2026-05-1AAAAA")).toBe(false);
    expect(validarFormatoCodigoPublico("PRV-2026-05-IAAAAA")).toBe(false);
    expect(validarFormatoCodigoPublico("PRV-2026-05-LAAAAA")).toBe(false);
  });

  it("rejeita sufixo com tamanho incorreto", () => {
    expect(validarFormatoCodigoPublico("PRV-2026-05-AAAAA")).toBe(false); // 5
    expect(validarFormatoCodigoPublico("PRV-2026-05-AAAAAAA")).toBe(false); // 7
  });

  // ─── Casos invalidos: tipo / vazio ─────────────────────────────────
  it("rejeita strings vazia / casos limite", () => {
    expect(validarFormatoCodigoPublico("")).toBe(false);
    expect(validarFormatoCodigoPublico("PRV-")).toBe(false);
    // @ts-expect-error testa tipagem em runtime
    expect(validarFormatoCodigoPublico(null)).toBe(false);
    // @ts-expect-error testa tipagem em runtime
    expect(validarFormatoCodigoPublico(undefined)).toBe(false);
    // @ts-expect-error testa tipagem em runtime
    expect(validarFormatoCodigoPublico(12345)).toBe(false);
  });

  it("CODIGO_PUBLICO_REGEX bate com a funcao", () => {
    const samples = [
      "PRV-2026-05-K3T9XB",
      "PRV-2026-13-K3T9XB",
      "PRV-2026-05-0AAAAA",
    ];
    for (const s of samples) {
      expect(validarFormatoCodigoPublico(s)).toBe(CODIGO_PUBLICO_REGEX.test(s));
    }
  });
});

describe("isCharValidoEmPosicaoSemHifen", () => {
  it("ano (pos 0-3): aceita digitos 0-9", () => {
    for (const c of "0123456789") {
      expect(isCharValidoEmPosicaoSemHifen(c, 0)).toBe(true);
      expect(isCharValidoEmPosicaoSemHifen(c, 3)).toBe(true);
    }
  });

  it("ano (pos 0-3): rejeita letras", () => {
    expect(isCharValidoEmPosicaoSemHifen("A", 0)).toBe(false);
    expect(isCharValidoEmPosicaoSemHifen("Z", 3)).toBe(false);
  });

  it("mes (pos 4-5): aceita digitos 0-9 (validacao de range 01-12 e do regex final)", () => {
    expect(isCharValidoEmPosicaoSemHifen("0", 4)).toBe(true);
    expect(isCharValidoEmPosicaoSemHifen("9", 5)).toBe(true);
  });

  it("mes (pos 4-5): rejeita letras", () => {
    expect(isCharValidoEmPosicaoSemHifen("A", 4)).toBe(false);
  });

  it("sufixo (pos 6-11): aceita chars do alfabeto", () => {
    for (const c of ALFABETO_SUFIXO) {
      expect(isCharValidoEmPosicaoSemHifen(c, 6)).toBe(true);
      expect(isCharValidoEmPosicaoSemHifen(c, 11)).toBe(true);
    }
  });

  it("sufixo (pos 6-11): rejeita chars ambiguos", () => {
    for (const c of "0OIL1") {
      expect(isCharValidoEmPosicaoSemHifen(c, 6)).toBe(false);
    }
  });

  it("pos >= 12: rejeita qualquer char", () => {
    expect(isCharValidoEmPosicaoSemHifen("A", 12)).toBe(false);
    expect(isCharValidoEmPosicaoSemHifen("9", 99)).toBe(false);
  });

  it("rejeita strings de tamanho != 1", () => {
    expect(isCharValidoEmPosicaoSemHifen("AB", 0)).toBe(false);
    expect(isCharValidoEmPosicaoSemHifen("", 0)).toBe(false);
  });
});

describe("aplicarMascara — comportamento incremental", () => {
  it("vazio retorna vazio", () => {
    expect(aplicarMascara("")).toBe("");
  });

  it("digita ano parcial", () => {
    expect(aplicarMascara("20")).toBe("20");
    expect(aplicarMascara("202")).toBe("202");
    expect(aplicarMascara("2026")).toBe("2026");
  });

  it("insere hifen automatico apos ano completo", () => {
    expect(aplicarMascara("20265")).toBe("2026-5");
    expect(aplicarMascara("202605")).toBe("2026-05");
  });

  it("insere hifen automatico apos mes completo", () => {
    expect(aplicarMascara("2026059")).toBe("2026-05-9");
    expect(aplicarMascara("20260509")).toBe("2026-05-9"); // 0 no sufixo bloqueado
  });

  it("constroi codigo completo (display = 14 chars)", () => {
    const r = aplicarMascara("202605K3T9XB");
    expect(r).toBe("2026-05-K3T9XB");
    expect(r.length).toBe(DISPLAY_TOTAL_LEN);
  });

  it("auto-uppercase", () => {
    expect(aplicarMascara("2026-05-k3t9xb")).toBe("2026-05-K3T9XB");
    expect(aplicarMascara("2026-05-k3t9xb".toLowerCase())).toBe(
      "2026-05-K3T9XB",
    );
  });

  it("strip do prefixo PRV- (paste-friendly)", () => {
    expect(aplicarMascara("PRV-2026-05-K3T9XB")).toBe("2026-05-K3T9XB");
    expect(aplicarMascara("prv-2026-05-k3t9xb")).toBe("2026-05-K3T9XB");
    expect(aplicarMascara("PRV2026-05-K3T9XB")).toBe("2026-05-K3T9XB");
  });

  it("bloqueia letra no ano (D5 bloqueio rigido por posicao)", () => {
    expect(aplicarMascara("A2026")).toBe("2026"); // A descartado, 2026 ocupa pos 0-3
    expect(aplicarMascara("2A26")).toBe("226"); // A descartado entre 2 e 26
  });

  it("bloqueia char ambiguo no sufixo", () => {
    // 2026-05- + sufixo com 0 ou O ou I ou L ou 1: descartados
    expect(aplicarMascara("202605K0T9XB")).toBe("2026-05-KT9XB"); // 0 descartado
    expect(aplicarMascara("202605KOT9XB")).toBe("2026-05-KT9XB"); // O descartado
    expect(aplicarMascara("202605K1T9XB")).toBe("2026-05-KT9XB"); // 1 descartado
    expect(aplicarMascara("202605KIT9XB")).toBe("2026-05-KT9XB"); // I descartado
    expect(aplicarMascara("202605KLT9XB")).toBe("2026-05-KT9XB"); // L descartado
  });

  it("trunca em 14 chars (display) — chars extras descartados", () => {
    expect(aplicarMascara("2026-05-K3T9XBABCDEF")).toBe("2026-05-K3T9XB");
  });

  it("ignora espacos e caracteres aleatorios", () => {
    expect(aplicarMascara("2026 05 K3 T9 XB")).toBe("2026-05-K3T9XB");
    expect(aplicarMascara("2026.05.K3T9XB")).toBe("2026-05-K3T9XB");
    expect(aplicarMascara("@#$2026!05$K3T9XB&*")).toBe("2026-05-K3T9XB");
  });

  it("idempotencia: aplicarMascara(aplicarMascara(x)) === aplicarMascara(x)", () => {
    const samples = [
      "",
      "2026",
      "2026-05",
      "2026-05-K3T9XB",
      "PRV-2026-05-K3T9XB",
      "prv-2026-05-k3t9xb",
      "2026 05 K3 T9 XB",
    ];
    for (const s of samples) {
      const once = aplicarMascara(s);
      const twice = aplicarMascara(once);
      expect(twice).toBe(once);
    }
  });

  it("rejeita tipos nao-string em runtime", () => {
    // @ts-expect-error testa tipagem
    expect(aplicarMascara(null)).toBe("");
    // @ts-expect-error testa tipagem
    expect(aplicarMascara(undefined)).toBe("");
    // @ts-expect-error testa tipagem
    expect(aplicarMascara(123)).toBe("");
  });
});

describe("montarCodigoCompleto", () => {
  it("concatena PRV- a um display completo", () => {
    expect(montarCodigoCompleto("2026-05-K3T9XB")).toBe("PRV-2026-05-K3T9XB");
  });

  it("retorna vazio se display vazio", () => {
    expect(montarCodigoCompleto("")).toBe("");
  });

  it("concatena mesmo se display parcial (chamador decide validar)", () => {
    expect(montarCodigoCompleto("2026")).toBe("PRV-2026");
  });
});

describe("isDisplayCompleto", () => {
  it("true quando display tem 14 chars", () => {
    expect(isDisplayCompleto("2026-05-K3T9XB")).toBe(true);
  });

  it("false quando display tem outro tamanho", () => {
    expect(isDisplayCompleto("")).toBe(false);
    expect(isDisplayCompleto("2026")).toBe(false);
    expect(isDisplayCompleto("2026-05-K3T9XB-XX")).toBe(false);
  });
});

describe("integracao mascara → validacao", () => {
  it("display completo passa por aplicarMascara → montarCodigoCompleto → validarFormatoCodigoPublico", () => {
    const display = aplicarMascara("2026-05-K3T9XB");
    expect(isDisplayCompleto(display)).toBe(true);
    const completo = montarCodigoCompleto(display);
    expect(validarFormatoCodigoPublico(completo)).toBe(true);
  });

  it("display parcial nao passa na validacao", () => {
    const display = aplicarMascara("2026-05-K3T9X");
    const completo = montarCodigoCompleto(display);
    expect(validarFormatoCodigoPublico(completo)).toBe(false);
  });

  it("paste com prefixo PRV- normaliza para mesma forma", () => {
    const display1 = aplicarMascara("2026-05-K3T9XB");
    const display2 = aplicarMascara("PRV-2026-05-K3T9XB");
    expect(display1).toBe(display2);
    expect(montarCodigoCompleto(display1)).toBe("PRV-2026-05-K3T9XB");
  });
});
