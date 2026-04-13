"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { buildQrPayload } from "@/lib/types/prova";
import { CloseIcon } from "@/components/icons";
import styles from "./detalhe.module.css";

interface Props {
  provaId: string;
  nroRequerimento: string;
  qrCodeHash: string;
  isOpen: boolean;
  onClose: () => void;
  getToken: () => Promise<string | null>;
}

interface BlobState {
  pdfUrl: string | null;
  qrUrl: string | null;
  loading: boolean;
  error: string | null;
}

const INITIAL_BLOB: BlobState = {
  pdfUrl: null,
  qrUrl: null,
  loading: false,
  error: null,
};

/**
 * Busca `/etiqueta.pdf` e `/qr-code.png` em paralelo, converte para Blob
 * URLs e exibe em um modal com 2 colunas. Revoga as object URLs no unmount.
 *
 * Nao usamos `apiFetch` aqui porque ele tenta fazer `response.json()` — os
 * 2 endpoints retornam binarios. Fetch puro com Authorization manual e
 * conversao para Blob via `response.blob()`.
 */
export function VisualizarEtiquetaModal({
  provaId,
  nroRequerimento,
  qrCodeHash,
  isOpen,
  onClose,
  getToken,
}: Props) {
  const [state, setState] = useState<BlobState>(INITIAL_BLOB);
  const [copied, setCopied] = useState(false);

  const qrPayload = buildQrPayload(nroRequerimento, qrCodeHash);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(qrPayload);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback para browsers sem Clipboard API
      const input = document.createElement("input");
      input.value = qrPayload;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [qrPayload]);

  // Carrega PDF + QR quando o modal abre.
  //
  // Cleanup sem race: usamos uma ref mutavel que acumula as blob URLs criadas
  // durante esta execucao do effect. O cleanup le a ref no momento de rodar,
  // cobrindo tanto o cenario "URLs criadas antes do cleanup" quanto o
  // "criadas depois do re-check de aborted". Qualquer coisa que entrar em
  // `createdRef.current` eventualmente sera revogada.
  useEffect(() => {
    if (!isOpen) return;

    const createdUrls: string[] = [];
    let aborted = false;

    async function load() {
      setState({ ...INITIAL_BLOB, loading: true });
      const token = await getToken();
      if (!token) {
        if (!aborted) {
          setState({
            ...INITIAL_BLOB,
            error: "Sessao expirada. Faca login novamente.",
          });
        }
        return;
      }

      const apiBase =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

      try {
        const [pdfResp, qrResp] = await Promise.all([
          fetch(`${apiBase}/api/v1/provas/${provaId}/etiqueta.pdf`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch(`${apiBase}/api/v1/provas/${provaId}/qr-code.png`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ]);

        if (!pdfResp.ok) {
          throw new ApiError(
            `Falha ao carregar PDF (${pdfResp.status})`,
            pdfResp.status,
          );
        }
        if (!qrResp.ok) {
          throw new ApiError(
            `Falha ao carregar QR code (${qrResp.status})`,
            qrResp.status,
          );
        }

        const [pdfBlob, qrBlob] = await Promise.all([
          pdfResp.blob(),
          qrResp.blob(),
        ]);

        // Cria as 2 URLs atomicamente e registra na lista antes de checar
        // `aborted` — garante que cleanup sempre ve tudo que foi criado.
        const pdfUrl = URL.createObjectURL(pdfBlob);
        createdUrls.push(pdfUrl);
        const qrUrl = URL.createObjectURL(qrBlob);
        createdUrls.push(qrUrl);

        if (aborted) {
          // Cleanup ja rodou ou esta pra rodar — revoga imediato.
          URL.revokeObjectURL(pdfUrl);
          URL.revokeObjectURL(qrUrl);
          return;
        }

        setState({ loading: false, error: null, pdfUrl, qrUrl });
      } catch (err) {
        if (aborted) return;
        const msg =
          err instanceof ApiError
            ? err.message
            : "Nao foi possivel carregar a etiqueta.";
        setState({ ...INITIAL_BLOB, error: msg });
      }
    }

    load();

    return () => {
      aborted = true;
      // Revoga qualquer URL ja acumulada. Se o load() estiver a meio caminho,
      // a checagem `if (aborted)` dentro dele vai cuidar das URLs criadas
      // DEPOIS desta cleanup rodar.
      for (const url of createdUrls) {
        URL.revokeObjectURL(url);
      }
      createdUrls.length = 0;
    };
  }, [isOpen, provaId, getToken]);

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

  const handleDownload = useCallback(() => {
    if (!state.pdfUrl) return;
    const a = document.createElement("a");
    a.href = state.pdfUrl;
    a.download = `etiqueta-${nroRequerimento}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }, [state.pdfUrl, nroRequerimento]);

  if (!isOpen) return null;

  return (
    <div
      className={styles.modalOverlay}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="etiqueta-modal-title"
    >
      <div className={styles.modalContent}>
        <header className={styles.modalHeader}>
          <h2 id="etiqueta-modal-title" className={styles.modalTitle}>
            Etiqueta — {nroRequerimento}
          </h2>
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
          {state.loading && (
            <div className={styles.modalLoading}>Carregando etiqueta...</div>
          )}
          {state.error && !state.loading && (
            <div className={styles.modalError}>{state.error}</div>
          )}
          {!state.loading &&
            !state.error &&
            state.pdfUrl &&
            state.qrUrl && (
              <div className={styles.modalGrid}>
                <div className={styles.modalPdfWrap}>
                  <iframe
                    title="Preview da etiqueta"
                    src={state.pdfUrl}
                    className={styles.modalPdfFrame}
                  />
                </div>
                <div className={styles.modalQrWrap}>
                  <h3 className={styles.modalQrTitle}>QR Code</h3>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={state.qrUrl}
                    alt="QR Code da prova"
                    className={styles.modalQrImg}
                  />
                  <p className={styles.modalQrHint}>
                    Escaneie com a camera do sistema para movimentar a prova
                  </p>
                  <div className={styles.qrPayloadBox}>
                    <label className={styles.qrPayloadLabel}>
                      Codigo do QR
                    </label>
                    <div className={styles.qrPayloadRow}>
                      <input
                        type="text"
                        readOnly
                        value={qrPayload}
                        className={styles.qrPayloadInput}
                        onClick={(e) =>
                          (e.target as HTMLInputElement).select()
                        }
                      />
                      <button
                        type="button"
                        className={styles.qrPayloadCopyBtn}
                        onClick={handleCopy}
                      >
                        {copied ? "Copiado!" : "Copiar"}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
        </div>

        <footer className={styles.modalFooter}>
          <button
            type="button"
            className={styles.btnSecondary}
            onClick={handleDownload}
            disabled={!state.pdfUrl}
          >
            Baixar PDF
          </button>
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
