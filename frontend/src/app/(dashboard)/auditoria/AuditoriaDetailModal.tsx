"use client";

import { useEffect } from "react";
import Link from "next/link";
import { CloseIcon } from "@/components/icons";
import { useAuditoriaDetail } from "@/hooks/useAuditoriaDetail";
import styles from "./auditoria.module.css";
import { useFocusTrap } from "@/hooks/useFocusTrap";

interface Props {
  /** UUID do log selecionado, ou `null` para modal fechado. */
  logId: string | null;
  onClose: () => void;
  getToken: () => Promise<string | null>;
}

/**
 * Modal de detalhes de um audit log (Wave 6, Componente 18).
 *
 * Design seguindo o padrao do `VisualizarEtiquetaModal`:
 *  - Focus trap via `useFocusTrap`.
 *  - ESC fecha.
 *  - Body scroll lock.
 *  - Click no overlay fecha.
 *  - `role="dialog"` + `aria-modal` + `aria-labelledby`.
 *
 * Conteudo:
 *  - Header: titulo com `tipo_evento_label` + "quando" + botao close.
 *  - Body: grid com "Quem", "Prova", "IP/UA", e `detalhes_json` pretty.
 *  - Footer: link "Abrir prova" (quando aplicavel) + botao Fechar.
 *
 * `logId=null` fecha o modal — sem render, sem fetch. Trocar para UUID
 * dispara o fetch automatico via `useAuditoriaDetail`.
 */
export function AuditoriaDetailModal({ logId, onClose, getToken }: Props) {
  const isOpen = logId !== null;
  const focusTrapRef = useFocusTrap<HTMLDivElement>(isOpen);
  const { loading, error, data } = useAuditoriaDetail(getToken, logId);

  // ESC fecha o modal.
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, onClose]);

  // Body scroll lock enquanto aberto.
  useEffect(() => {
    if (!isOpen) return;
    const original = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = original;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className={styles.modalOverlay}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="auditoria-modal-title"
      ref={focusTrapRef}
    >
      <div className={styles.modalContent}>
        <header className={styles.modalHeader}>
          <div className={styles.modalTitleWrap}>
            <h2 id="auditoria-modal-title" className={styles.modalTitle}>
              {data ? data.tipo_evento_label : "Detalhe do evento"}
            </h2>
            {data && (
              <span className={styles.modalSubtitle}>
                {formatFullWhen(data.created_at)}
              </span>
            )}
          </div>
          <button
            type="button"
            className={styles.modalCloseBtn}
            onClick={onClose}
            aria-label="Fechar modal"
          >
            <CloseIcon width={24} height={24} />
          </button>
        </header>

        <div className={styles.modalBody}>
          {loading && (
            <div className={styles.modalLoading}>
              Carregando detalhes...
            </div>
          )}
          {error && !loading && (
            <div className={styles.modalError}>{error}</div>
          )}
          {!loading && !error && data && (
            <div className={styles.modalGrid}>
              {/* Quem */}
              <section className={styles.modalSection}>
                <h3 className={styles.modalSectionTitle}>Quem</h3>
                <dl className={styles.kvList}>
                  <div className={styles.kvRow}>
                    <dt>Nome</dt>
                    <dd>{data.usuario.nome}</dd>
                  </div>
                  <div className={styles.kvRow}>
                    <dt>Setor</dt>
                    <dd>{data.usuario.setor}</dd>
                  </div>
                  <div className={styles.kvRow}>
                    <dt>Admin</dt>
                    <dd>{data.usuario.is_admin ? "Sim" : "Nao"}</dd>
                  </div>
                </dl>
              </section>

              {/* Prova */}
              <section className={styles.modalSection}>
                <h3 className={styles.modalSectionTitle}>Prova</h3>
                {data.prova ? (
                  <dl className={styles.kvList}>
                    <div className={styles.kvRow}>
                      <dt>Requerimento</dt>
                      <dd>{data.prova.nro_requerimento}</dd>
                    </div>
                    <div className={styles.kvRow}>
                      <dt>Nome</dt>
                      <dd>{data.prova.nome}</dd>
                    </div>
                  </dl>
                ) : (
                  <p className={styles.modalMuted}>
                    Sem prova associada (ex: alteracao de configuracao).
                  </p>
                )}
              </section>

              {/* Acao crua + Tipo derivado */}
              <section className={styles.modalSection}>
                <h3 className={styles.modalSectionTitle}>Evento</h3>
                <dl className={styles.kvList}>
                  <div className={styles.kvRow}>
                    <dt>Tipo</dt>
                    <dd>
                      <span
                        className={`${styles.chip} ${
                          styles[`chip_${data.tipo_evento}`] ?? ""
                        }`}
                      >
                        {data.tipo_evento_label}
                      </span>
                    </dd>
                  </div>
                  <div className={styles.kvRow}>
                    <dt>Acao crua</dt>
                    <dd>
                      <code className={styles.kvCode}>{data.acao}</code>
                    </dd>
                  </div>
                </dl>
              </section>

              {/* Origem: IP + UA */}
              <section className={styles.modalSection}>
                <h3 className={styles.modalSectionTitle}>Origem</h3>
                <dl className={styles.kvList}>
                  <div className={styles.kvRow}>
                    <dt>IP</dt>
                    <dd>
                      <code className={styles.kvCode}>
                        {data.ip_address || "—"}
                      </code>
                    </dd>
                  </div>
                  <div className={styles.kvRow}>
                    <dt>User-Agent</dt>
                    <dd className={styles.kvUa}>{data.user_agent || "—"}</dd>
                  </div>
                </dl>
              </section>

              {/* detalhes_json */}
              <section className={`${styles.modalSection} ${styles.modalSectionFull}`}>
                <h3 className={styles.modalSectionTitle}>
                  Detalhes (JSON)
                </h3>
                <pre className={styles.jsonBox}>
                  {data.detalhes_json
                    ? JSON.stringify(data.detalhes_json, null, 2)
                    : "(sem detalhes)"}
                </pre>
              </section>
            </div>
          )}
        </div>

        <footer className={styles.modalFooter}>
          {data && data.prova && (
            <Link
              href={`/provas/${data.prova.id}`}
              className={styles.btnSecondary}
            >
              Abrir prova
            </Link>
          )}
          <button
            type="button"
            className={styles.btnPrimary}
            onClick={onClose}
          >
            Fechar
          </button>
        </footer>
      </div>
    </div>
  );
}

function formatFullWhen(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString("pt-BR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso;
  }
}
