import { describe, it, expect } from "vitest";

import {
  MENSAGENS_ERRO_PADRAO,
  type CodigoErro,
} from "@/lib/services/identificacao-prova";
import { MENSAGENS_C19, mensagemFinal } from "@/lib/c19-mensagens";

/**
 * Wave 3 v4.0 / Componente 19 — testes da uniformizacao de mensagens.
 *
 * Roda em `environment: node` — modulo `c19-mensagens.ts` e puro
 * (sem React, sem DOM).
 *
 * Cobre:
 *   - Invariante critica anti-enumeracao (AUD-W3C19-003):
 *     `mensagemFinal("QR_INVALIDO")` retorna **byte-a-byte** o mesmo
 *     texto que `MENSAGENS_ERRO_PADRAO.PROVA_NAO_ENCONTRADA`.
 *     Quebrar isso reintroduz vetor de enumeracao DAT §8.2.
 *   - Fallback para `mensagemPara(codigo)` quando nao ha override do C19.
 *   - Escopo controlado do `MENSAGENS_C19` (somente `QR_INVALIDO`
 *     sobrescrito; demais codigos seguem o padrao do C10).
 *   - Cobertura zero de regressao em `page.tsx` (resolve AUD-W3C19-008
 *     que era "mensagemFinal sem teste").
 */

describe("AUD-W3C19-003 — uniformizacao de mensagens", () => {
  it("mensagemFinal('QR_INVALIDO') retorna byte-a-byte 'Prova nao encontrada.'", () => {
    expect(mensagemFinal("QR_INVALIDO")).toBe("Prova nao encontrada.");
  });

  it("mensagemFinal('QR_INVALIDO') === MENSAGENS_ERRO_PADRAO.PROVA_NAO_ENCONTRADA (invariante critica)", () => {
    // **Anti-enumeracao em camada UI:** texto exibido no banner para
    // QR_INVALIDO (client OR backend 422) precisa ser identico ao
    // texto exibido para PROVA_NAO_ENCONTRADA (backend 404). Se isso
    // quebrar, atacante pode distinguir "formato errado" de "fora do
    // scope" — DAT v3.0 §8.2 quebrado.
    expect(mensagemFinal("QR_INVALIDO")).toBe(
      MENSAGENS_ERRO_PADRAO.PROVA_NAO_ENCONTRADA,
    );
  });

  it("mensagemFinal('PROVA_NAO_ENCONTRADA') usa fallback do C10 padrao", () => {
    expect(mensagemFinal("PROVA_NAO_ENCONTRADA")).toBe(
      MENSAGENS_ERRO_PADRAO.PROVA_NAO_ENCONTRADA,
    );
  });

  it("mensagemFinal('ERRO_REDE') usa fallback do C10 padrao", () => {
    expect(mensagemFinal("ERRO_REDE")).toBe(MENSAGENS_ERRO_PADRAO.ERRO_REDE);
  });

  it("mensagemFinal('SESSAO_EXPIRADA') usa fallback do C10 padrao", () => {
    expect(mensagemFinal("SESSAO_EXPIRADA")).toBe(
      MENSAGENS_ERRO_PADRAO.SESSAO_EXPIRADA,
    );
  });

  it("mensagemFinal('DISPOSITIVO_SEM_CAMERA') usa fallback do C10 padrao (nao aplicavel ao C19 mas precisa funcionar)", () => {
    // O codigo nao e disparado no caminho Manual mas a uniao TS exige
    // tratamento — fallback retorna a mensagem padrao do C10 sem
    // erro/explosao.
    expect(mensagemFinal("DISPOSITIVO_SEM_CAMERA")).toBe(
      MENSAGENS_ERRO_PADRAO.DISPOSITIVO_SEM_CAMERA,
    );
  });

  it("MENSAGENS_C19 sobrescreve SOMENTE QR_INVALIDO", () => {
    // Defensivo contra regressao: caso alguem adicione nova override,
    // o teste alerta. Reduzir o escopo para apenas QR_INVALIDO foi
    // decisao deliberada (ADR-143).
    expect(Object.keys(MENSAGENS_C19)).toEqual(["QR_INVALIDO"]);
  });

  it("MENSAGENS_C19.QR_INVALIDO usa diretamente MENSAGENS_ERRO_PADRAO.PROVA_NAO_ENCONTRADA (sem duplicacao de string)", () => {
    // Refactor pos-auditoria: em vez de hardcoded "Prova nao
    // encontrada.", a override usa a propria constante do C10. Isso
    // garante que qualquer alteracao futura no texto de
    // PROVA_NAO_ENCONTRADA se propaga automaticamente — drift
    // impossivel.
    expect(MENSAGENS_C19.QR_INVALIDO).toBe(
      MENSAGENS_ERRO_PADRAO.PROVA_NAO_ENCONTRADA,
    );
  });

  it("retorna string para todos os 5 codigos de erro (cobertura exhaustiva)", () => {
    const codigos: CodigoErro[] = [
      "QR_INVALIDO",
      "PROVA_NAO_ENCONTRADA",
      "DISPOSITIVO_SEM_CAMERA",
      "ERRO_REDE",
      "SESSAO_EXPIRADA",
    ];
    for (const c of codigos) {
      const m = mensagemFinal(c);
      expect(typeof m).toBe("string");
      expect(m.length).toBeGreaterThan(0);
    }
  });
});
