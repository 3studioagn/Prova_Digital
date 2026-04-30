"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { createClient } from "@/lib/supabase/client";
import { CheckIcon } from "@/components/icons";
import { useConfiguracoes } from "@/hooks/useConfiguracoes";
import { useAuthorization } from "@/lib/hooks/use-authorization";
import { Restricted } from "@/components/Restricted";
import {
  CHAVE_TEMPLATE_ETIQUETA,
  CHAVE_TEMPO_ATRASO,
  FORMATO_LABELS,
  FORMATOS_ETIQUETA,
  TEMPO_ATRASO_MAX_HORAS,
  TEMPO_ATRASO_MIN_HORAS,
  isTemplateEtiquetaValor,
  isTempoAtrasoValor,
  type FormatoEtiqueta,
  type TemplateEtiquetaValor,
} from "@/lib/types/configuracao";
import styles from "./configuracoes.module.css";

type SectionStatus = {
  saving: boolean;
  error: string | null;
  success: boolean;
};

const EMPTY_STATUS: SectionStatus = {
  saving: false,
  error: null,
  success: false,
};

export default function ConfiguracoesPage() {
  // Wave 1 v4.0 — guard via Matriz. Configuracoes = admin-only (RF-022).
  const auth = useAuthorization("configuracoes");

  const getToken = useCallback(async () => {
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  }, []);

  const { loading, error, configuracoes, updateConfiguracao } =
    useConfiguracoes(getToken);

  // ── Tempo de atraso ─────────────────────────────────────────────────
  const [tempoAtrasoLocal, setTempoAtrasoLocal] = useState<string>("");
  const [tempoAtrasoStatus, setTempoAtrasoStatus] = useState<SectionStatus>(
    EMPTY_STATUS,
  );

  // ── Template de etiqueta ────────────────────────────────────────────
  const [templateLocal, setTemplateLocal] = useState<TemplateEtiquetaValor>({
    nome: "padrao",
    formato: "A4",
    logo_enabled: true,
    mostrar_data_criacao: false,
  });
  const [templateStatus, setTemplateStatus] =
    useState<SectionStatus>(EMPTY_STATUS);

  // Sincroniza estado local quando as configuracoes chegam da API.
  useEffect(() => {
    const tempo = configuracoes[CHAVE_TEMPO_ATRASO]?.valor;
    if (isTempoAtrasoValor(tempo)) {
      setTempoAtrasoLocal(String(tempo));
    }
    const template = configuracoes[CHAVE_TEMPLATE_ETIQUETA]?.valor;
    if (isTemplateEtiquetaValor(template)) {
      setTemplateLocal(template);
    }
  }, [configuracoes]);

  // ── Submit tempo de atraso ──────────────────────────────────────────
  const handleSubmitTempoAtraso = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      setTempoAtrasoStatus({ saving: true, error: null, success: false });

      const parsed = Number(tempoAtrasoLocal);
      if (
        !Number.isInteger(parsed) ||
        parsed < TEMPO_ATRASO_MIN_HORAS ||
        parsed > TEMPO_ATRASO_MAX_HORAS
      ) {
        setTempoAtrasoStatus({
          saving: false,
          error: `Informe um numero inteiro entre ${TEMPO_ATRASO_MIN_HORAS} e ${TEMPO_ATRASO_MAX_HORAS} horas.`,
          success: false,
        });
        return;
      }

      const result = await updateConfiguracao(CHAVE_TEMPO_ATRASO, parsed);
      if (result.ok) {
        setTempoAtrasoStatus({ saving: false, error: null, success: true });
      } else {
        setTempoAtrasoStatus({
          saving: false,
          error: result.error,
          success: false,
        });
      }
    },
    [tempoAtrasoLocal, updateConfiguracao],
  );

  // ── Submit template ─────────────────────────────────────────────────
  const handleSubmitTemplate = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      setTemplateStatus({ saving: true, error: null, success: false });

      const result = await updateConfiguracao(
        CHAVE_TEMPLATE_ETIQUETA,
        templateLocal,
      );
      if (result.ok) {
        setTemplateStatus({ saving: false, error: null, success: true });
      } else {
        setTemplateStatus({
          saving: false,
          error: result.error,
          success: false,
        });
      }
    },
    [templateLocal, updateConfiguracao],
  );

  // ── Render ──────────────────────────────────────────────────────────

  if (!auth.loading && !auth.hasAccess) {
    return <Restricted ruleKey="configuracoes" profile={auth.profile} />;
  }

  return (
    <>
      <div className={styles.mobileNotice}>
        <p>Para acessar esse recurso, acesse a versao desktop.</p>
      </div>
      <div className={styles.desktopOnly}>
        <header className={styles.pageHeader}>
          <h1 className={styles.title}>Configuracoes do sistema</h1>
        </header>

        {loading && (
          <div className={styles.loadingBox}>Carregando configuracoes...</div>
        )}

        {error && !loading && <div className={styles.errorBox}>{error}</div>}

        {!loading && !error && (
          <>
            {/* ── Seccao 1: Tempo de atraso ──────────────────────────── */}
            <section className={styles.card}>
              <h2 className={styles.h2}>Tempo de atraso</h2>
              <p className={styles.description}>
                Uma prova digital sem movimentacao por mais que esse tempo
                e considerada atrasada.
              </p>

              <form
                onSubmit={handleSubmitTempoAtraso}
                className={styles.cardBody}
              >
                <div className={styles.cardFields}>
                  <div className={styles.field}>
                    <label htmlFor="tempo_atraso" className={styles.label}>
                      Tempo (horas uteis)
                    </label>
                    <input
                      id="tempo_atraso"
                      type="number"
                      min={TEMPO_ATRASO_MIN_HORAS}
                      max={TEMPO_ATRASO_MAX_HORAS}
                      step={1}
                      className={`${styles.input} ${styles.inputNumero}`}
                      value={tempoAtrasoLocal}
                      onChange={(e) => {
                        setTempoAtrasoLocal(e.target.value);
                        setTempoAtrasoStatus(EMPTY_STATUS);
                      }}
                      disabled={tempoAtrasoStatus.saving}
                      required
                    />
                  </div>

                  {tempoAtrasoStatus.error && (
                    <div className={styles.inlineError}>
                      {tempoAtrasoStatus.error}
                    </div>
                  )}
                  {tempoAtrasoStatus.success && (
                    <div className={styles.inlineSuccess}>
                      Configuracao salva.
                    </div>
                  )}
                </div>

                <button
                  type="submit"
                  className={styles.btnPrimary}
                  disabled={tempoAtrasoStatus.saving}
                >
                  {tempoAtrasoStatus.saving ? "Salvando..." : "Salvar"}
                </button>
              </form>
            </section>

            {/* ── Seccao 2: Template da etiqueta ─────────────────────── */}
            <section className={styles.card}>
              <h2 className={styles.h2}>Template da etiqueta</h2>
              <p className={styles.description}>
                Layout da etiqueta imprimivel gerada a cada prova digital
                (RN-011).
              </p>

              <form
                onSubmit={handleSubmitTemplate}
                className={styles.cardBody}
              >
                <div className={styles.cardFields}>
                  <div className={styles.grid}>
                    <div className={styles.field}>
                      <label htmlFor="template_nome" className={styles.label}>
                        Nome do template
                      </label>
                      <input
                        id="template_nome"
                        type="text"
                        className={styles.input}
                        value={templateLocal.nome}
                        readOnly
                        disabled
                        aria-disabled="true"
                      />
                      <span className={styles.fieldHint}>
                        Campo read-only na Wave 2 — edicao futura.
                      </span>
                    </div>

                    <div className={styles.field}>
                      <label
                        htmlFor="template_formato"
                        className={styles.label}
                      >
                        Formato
                      </label>
                      <select
                        id="template_formato"
                        className={styles.select}
                        value={templateLocal.formato}
                        onChange={(e) => {
                          setTemplateLocal({
                            ...templateLocal,
                            formato: e.target.value as FormatoEtiqueta,
                          });
                          setTemplateStatus(EMPTY_STATUS);
                        }}
                        disabled={templateStatus.saving}
                      >
                        {FORMATOS_ETIQUETA.map((f) => (
                          <option key={f} value={f}>
                            {FORMATO_LABELS[f]}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className={styles.checkboxGroup}>
                    <label className={styles.checkboxLabel}>
                      <input
                        type="checkbox"
                        className={styles.checkbox}
                        checked={templateLocal.logo_enabled}
                        onChange={(e) => {
                          setTemplateLocal({
                            ...templateLocal,
                            logo_enabled: e.target.checked,
                          });
                          setTemplateStatus(EMPTY_STATUS);
                        }}
                        disabled={templateStatus.saving}
                      />
                      <span className={styles.checkboxBox} aria-hidden="true">
                        <CheckIcon />
                      </span>
                      <span>Exibir logo 3Studio no cabecalho</span>
                    </label>

                    <label className={styles.checkboxLabel}>
                      <input
                        type="checkbox"
                        className={styles.checkbox}
                        checked={templateLocal.mostrar_data_criacao}
                        onChange={(e) => {
                          setTemplateLocal({
                            ...templateLocal,
                            mostrar_data_criacao: e.target.checked,
                          });
                          setTemplateStatus(EMPTY_STATUS);
                        }}
                        disabled={templateStatus.saving}
                      />
                      <span className={styles.checkboxBox} aria-hidden="true">
                        <CheckIcon />
                      </span>
                      <span>Exibir data de criacao da prova</span>
                    </label>
                  </div>

                  {templateStatus.error && (
                    <div className={styles.inlineError}>
                      {templateStatus.error}
                    </div>
                  )}
                  {templateStatus.success && (
                    <div className={styles.inlineSuccess}>Template salvo.</div>
                  )}
                </div>

                <button
                  type="submit"
                  className={styles.btnPrimary}
                  disabled={templateStatus.saving}
                >
                  {templateStatus.saving ? "Salvando..." : "Salvar"}
                </button>
              </form>
            </section>
          </>
        )}
      </div>
    </>
  );
}
