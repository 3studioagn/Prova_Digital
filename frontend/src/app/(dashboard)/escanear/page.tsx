"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from "react";
import type SignatureCanvas from "react-signature-canvas";
import SigCanvas from "react-signature-canvas";

import { createClient } from "@/lib/supabase/client";
import { ScanIcon } from "@/components/icons";
import { useScanProva } from "@/hooks/useScanProva";
import { useExecutarTransicao } from "@/hooks/useExecutarTransicao";
import { useScanner } from "@/hooks/useScanner";
import {
  ASSINATURA_BASE64_MAX_BYTES,
  ROTA_LABELS,
  STATUS_LABELS,
  type ScanResponse,
  type StatusProva,
} from "@/lib/types/prova";
import styles from "./escanear.module.css";

/* ──────────────────────────────────────────────────────────────────────
 * Maquina de estados da pagina
 * ──────────────────────────────────────────────────────────────────── */

type PageState =
  | { kind: "idle" }
  | { kind: "scanning" }
  | { kind: "scan-loading"; payload: string }
  | { kind: "scan-ready"; scan: ScanResponse }
  | {
      kind: "signing";
      scan: ScanResponse;
      statusNovo: StatusProva;
      precisaMotivo: boolean;
    }
  | {
      kind: "submitting";
      scan: ScanResponse;
      statusNovo: StatusProva;
      precisaMotivo: boolean;
    }
  | {
      kind: "done";
      scan: ScanResponse;
      statusAplicado: StatusProva;
    }
  | { kind: "scan-error"; message: string };

/* ──────────────────────────────────────────────────────────────────────
 * Labels de botao por transicao (pt-BR).
 * Se nao houver entrada, fallback usa STATUS_LABELS[destino].
 * ──────────────────────────────────────────────────────────────────── */

const ACTION_LABELS: Partial<Record<StatusProva, string>> = {
  RETIRADA_PELO_VENDEDOR: "Retirar prova",
  APROVADA_PELO_VENDEDOR: "Aprovar",
  REPROVADA_PELO_VENDEDOR: "Reprovar",
  DE_VOLTA_3STUDIO: "Devolver a 3Studio",
  ENCAMINHADA_A_CLICHERIA: "Encaminhar a clicheria",
  COM_MOTORISTA: "Enviar ao motorista",
  ENVIADA_PARA_CLICHERIA: "Confirmar transporte",
  RECEBIDA_PELA_CLICHERIA: "Confirmar recebimento",
};

function labelParaTransicao(destino: StatusProva): string {
  return ACTION_LABELS[destino] ?? STATUS_LABELS[destino];
}

/* ──────────────────────────────────────────────────────────────────────
 * Pagina principal
 * ──────────────────────────────────────────────────────────────────── */

export default function EscanearPage() {
  const [state, setState] = useState<PageState>({ kind: "idle" });

  const getToken = useCallback(async () => {
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  }, []);

  const scanHook = useScanProva(getToken);
  const transicaoHook = useExecutarTransicao(getToken);

  // ── Scanner: ativo apenas no estado "scanning" ─────────────────────
  const handleDetect = useCallback(
    (payload: string) => {
      setState({ kind: "scan-loading", payload });
    },
    [],
  );

  const scanner = useScanner({
    enabled: state.kind === "scanning",
    onDetect: handleDetect,
  });

  // ── Handler: quando `scan-loading` entra, chama o backend ──────────
  useEffect(() => {
    if (state.kind !== "scan-loading") return;
    let cancelled = false;
    (async () => {
      const { data, error } = await scanHook.escanear(state.payload);
      if (cancelled) return;
      if (!data) {
        setState({
          kind: "scan-error",
          message: error ?? "Nao foi possivel resolver o QR Code.",
        });
        return;
      }
      setState({ kind: "scan-ready", scan: data });
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.kind]);

  // ── Handlers de transicao ──────────────────────────────────────────
  const comecarScan = useCallback(() => {
    scanHook.reset();
    transicaoHook.reset();
    setState({ kind: "scanning" });
  }, [scanHook, transicaoHook]);

  const resetar = useCallback(() => {
    scanHook.reset();
    transicaoHook.reset();
    setState({ kind: "idle" });
  }, [scanHook, transicaoHook]);

  const escolherTransicao = useCallback(
    (destino: StatusProva) => {
      if (state.kind !== "scan-ready") return;
      const precisaMotivo = state.scan.motivo_obrigatorio_em.includes(destino);
      setState({
        kind: "signing",
        scan: state.scan,
        statusNovo: destino,
        precisaMotivo,
      });
    },
    [state],
  );

  const cancelarAssinatura = useCallback(() => {
    if (state.kind === "signing") {
      setState({ kind: "scan-ready", scan: state.scan });
      transicaoHook.reset();
    }
  }, [state, transicaoHook]);

  const submeterTransicao = useCallback(
    async (assinaturaBase64: string, motivo: string | null) => {
      if (state.kind !== "signing") return;
      const provaId = state.scan.prova.id;
      const statusNovo = state.statusNovo;

      setState({
        kind: "submitting",
        scan: state.scan,
        statusNovo,
        precisaMotivo: state.precisaMotivo,
      });
      const { data, error, isConflict } = await transicaoHook.executar({
        provaId,
        statusNovo,
        assinaturaBase64,
        motivoReprovacao: motivo,
      });

      if (!data) {
        if (isConflict) {
          // B-03: 409 = status mudou. Volta ao inicio para re-escanear.
          setState({
            kind: "scan-error",
            message:
              error ?? "O status da prova mudou. Escaneie novamente.",
          });
          return;
        }
        // Volta para `signing` para o usuario poder retentar
        setState({
          kind: "signing",
          scan: state.scan,
          statusNovo,
          precisaMotivo: state.precisaMotivo,
        });
        return;
      }

      setState({
        kind: "done",
        scan: {
          ...state.scan,
          prova: data.prova,
        },
        statusAplicado: statusNovo,
      });
    },
    [state, transicaoHook],
  );

  return (
    <div className={styles.pageWrapper}>
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.title}>Escanear prova</h1>
          <p className={styles.subtitle}>
            Leia o QR Code da etiqueta e confirme a movimentacao.
          </p>
        </div>
      </div>

      {state.kind === "idle" && (
        <IdleView
          onStart={comecarScan}
          onManualSubmit={(payload) => {
            scanHook.reset();
            transicaoHook.reset();
            setState({ kind: "scan-loading", payload });
          }}
        />
      )}

      {state.kind === "scanning" && (
        <ScanningView
          divId={scanner.divId}
          ready={scanner.ready}
          error={scanner.error}
          onCancel={resetar}
        />
      )}

      {state.kind === "scan-loading" && (
        <div className={styles.scannerWrapper}>
          <p className={styles.scannerStatus}>Verificando QR Code...</p>
        </div>
      )}

      {state.kind === "scan-ready" && (
        <ScanReadyView
          scan={state.scan}
          onEscolher={escolherTransicao}
          onCancelar={resetar}
        />
      )}

      {(state.kind === "signing" || state.kind === "submitting") && (
        <>
          <ScanReadyView
            scan={state.scan}
            onEscolher={() => {
              /* opaco — modal esta aberto */
            }}
            onCancelar={resetar}
            readOnly
          />
          <AssinaturaModal
            statusAtual={state.scan.prova.status}
            statusNovo={state.statusNovo}
            precisaMotivo={state.precisaMotivo}
            loading={state.kind === "submitting"}
            error={transicaoHook.error}
            onCancelar={cancelarAssinatura}
            onConfirmar={submeterTransicao}
          />
        </>
      )}

      {state.kind === "done" && (
        <DoneView
          scan={state.scan}
          statusAplicado={state.statusAplicado}
          onNovaLeitura={comecarScan}
        />
      )}

      {state.kind === "scan-error" && (
        <ErrorView message={state.message} onTentarNovamente={comecarScan} />
      )}
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────────
 * Sub-componentes de estado
 * ──────────────────────────────────────────────────────────────────── */

function IdleView({
  onStart,
  onManualSubmit,
}: {
  onStart: () => void;
  onManualSubmit: (payload: string) => void;
}) {
  const [codigoManual, setCodigoManual] = useState("");

  const handleManual = useCallback(
    (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      const v = codigoManual.trim();
      if (v) onManualSubmit(v);
    },
    [codigoManual, onManualSubmit],
  );

  return (
    <div className={styles.idleCard}>
      <div className={styles.idleIcon} aria-hidden="true">
        <ScanIcon width={28} height={28} />
      </div>
      <h2 className={styles.idleTitle}>Pronto para escanear</h2>
      <p className={styles.idleDescription}>
        Ative a camera para ler o QR Code, ou digite o codigo da prova
        manualmente.
      </p>
      <button
        type="button"
        className={styles.primaryButton}
        onClick={onStart}
      >
        Abrir camera
      </button>

      <div className={styles.divider}>
        <span>ou</span>
      </div>

      <form className={styles.manualInputWrapper} onSubmit={handleManual}>
        <input
          type="text"
          className={styles.manualInput}
          placeholder="Ex: 3SD|REQ-001|a1b2c3d4e5f67890"
          value={codigoManual}
          onChange={(e) => setCodigoManual(e.target.value)}
        />
        <button
          type="submit"
          className={styles.secondaryButton}
          disabled={!codigoManual.trim()}
        >
          Buscar prova
        </button>
      </form>
    </div>
  );
}

function ScanningView({
  divId,
  ready,
  error,
  onCancel,
}: {
  divId: string;
  ready: boolean;
  error: string | null;
  onCancel: () => void;
}) {
  return (
    <div className={styles.scannerWrapper}>
      <div className={styles.scannerContainer} id={divId} />
      <p className={styles.scannerStatus}>
        {error
          ? ""
          : ready
          ? "Aponte a camera para o QR Code da prova."
          : "Iniciando camera..."}
      </p>
      {error && (
        <div className={styles.scannerError} role="alert">
          {error}
        </div>
      )}
      <button
        type="button"
        className={styles.secondaryButton}
        onClick={onCancel}
      >
        Cancelar
      </button>
    </div>
  );
}

function ScanReadyView({
  scan,
  onEscolher,
  onCancelar,
  readOnly = false,
}: {
  scan: ScanResponse;
  onEscolher: (destino: StatusProva) => void;
  onCancelar: () => void;
  readOnly?: boolean;
}) {
  const { prova, transicoes_permitidas } = scan;
  return (
    <>
      <div className={styles.provaCard}>
        <div className={styles.provaCardHeader}>
          <div>
            <div className={styles.provaNome}>{prova.nome}</div>
            <div className={styles.provaNroReq}>{prova.nro_requerimento}</div>
          </div>
          <span className={styles.statusBadge}>
            {STATUS_LABELS[prova.status]}
          </span>
        </div>
        <div className={styles.provaInfoGrid}>
          <div>
            <div className={styles.provaInfoLabel}>Cliente</div>
            <div className={styles.provaInfoValue}>{prova.cliente}</div>
          </div>
          <div>
            <div className={styles.provaInfoLabel}>Vendedor</div>
            <div className={styles.provaInfoValue}>{prova.vendedor_nome}</div>
          </div>
          {prova.rota && (
            <div>
              <div className={styles.provaInfoLabel}>Rota</div>
              <div className={styles.provaInfoValue}>
                {ROTA_LABELS[prova.rota]}
              </div>
            </div>
          )}
          <div>
            <div className={styles.provaInfoLabel}>Ciclo</div>
            <div className={styles.provaInfoValue}>{prova.ciclo_atual}</div>
          </div>
        </div>
      </div>

      <div className={styles.actionsWrapper}>
        <div className={styles.actionsTitle}>Acoes disponiveis</div>
        {transicoes_permitidas.length === 0 ? (
          <p className={styles.noActions}>
            {prova.status === "CANCELADA" || prova.status === "RECEBIDA_PELA_CLICHERIA"
              ? `Esta prova ja foi finalizada (${STATUS_LABELS[prova.status]}).`
              : "Voce nao tem permissao para movimentar esta prova no estado atual."}
          </p>
        ) : (
          <>
            <p className={styles.actionsHint}>
              Escolha uma acao abaixo e assine para confirmar.
            </p>
            <div className={styles.actionsList}>
              {transicoes_permitidas.map((destino) => {
                const reprovar = destino === "REPROVADA_PELO_VENDEDOR";
                const cls = reprovar
                  ? styles.dangerButton
                  : styles.primaryButton;
                return (
                  <button
                    key={destino}
                    type="button"
                    className={cls}
                    disabled={readOnly}
                    onClick={() => onEscolher(destino)}
                  >
                    {labelParaTransicao(destino)}
                  </button>
                );
              })}
            </div>
          </>
        )}
        <div style={{ marginTop: "1rem" }}>
          <button
            type="button"
            className={styles.secondaryButton}
            onClick={onCancelar}
            disabled={readOnly}
          >
            Escanear outra
          </button>
        </div>
      </div>
    </>
  );
}

/* ──────────────────────────────────────────────────────────────────────
 * Modal de assinatura
 * ──────────────────────────────────────────────────────────────────── */

function AssinaturaModal({
  statusAtual,
  statusNovo,
  precisaMotivo,
  loading,
  error,
  onCancelar,
  onConfirmar,
}: {
  statusAtual: StatusProva;
  statusNovo: StatusProva;
  precisaMotivo: boolean;
  loading: boolean;
  error: string | null;
  onCancelar: () => void;
  onConfirmar: (assinaturaBase64: string, motivo: string | null) => void;
}) {
  const sigRef = useRef<SignatureCanvas | null>(null);
  const canvasContainerRef = useRef<HTMLDivElement>(null);
  const [canvasWidth, setCanvasWidth] = useState(0);
  const [motivo, setMotivo] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  // B-02: Dimensionar canvas pela largura real do container (mobile-first).
  useEffect(() => {
    const el = canvasContainerRef.current;
    if (!el) return;
    const update = () => {
      const w = el.clientWidth;
      if (w > 0) setCanvasWidth(w);
    };
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // D-04: Fechar modal com Escape (WAI-ARIA).
  useEffect(() => {
    if (loading) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancelar();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [loading, onCancelar]);

  const label = labelParaTransicao(statusNovo);
  const isReprovar = statusNovo === "REPROVADA_PELO_VENDEDOR";
  const titulo = isReprovar ? "Reprovar prova" : `Confirmar: ${label}`;
  const descricao = isReprovar
    ? "Descreva o motivo da reprovacao e assine para confirmar."
    : "Assine no quadro abaixo para confirmar a movimentacao.";
  const transicaoLabel = `${STATUS_LABELS[statusAtual]} \u2192 ${STATUS_LABELS[statusNovo]}`;

  const handleLimpar = useCallback(() => {
    sigRef.current?.clear();
    setLocalError(null);
  }, []);

  const handleSubmit = useCallback(
    (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      setLocalError(null);

      const canvas = sigRef.current;
      if (!canvas || canvas.isEmpty()) {
        setLocalError("Assinatura e obrigatoria.");
        return;
      }
      if (precisaMotivo && !motivo.trim()) {
        setLocalError("Motivo da reprovacao e obrigatorio.");
        return;
      }

      // Exporta como dataURL e remove o prefixo `data:image/png;base64,`.
      // `getTrimmedCanvas()` e mais cara (tira bounding box) mas gera PNG
      // menor — vale ao custo para poupar banda/armazenamento.
      const dataUrl = canvas.getCanvas().toDataURL("image/png");
      const base64 = dataUrl.split(",")[1] ?? "";

      if (base64.length > ASSINATURA_BASE64_MAX_BYTES) {
        setLocalError(
          "Assinatura muito complexa. Tente um traco mais simples.",
        );
        return;
      }

      onConfirmar(base64, precisaMotivo ? motivo.trim() : null);
    },
    [precisaMotivo, motivo, onConfirmar],
  );

  const displayError = error ?? localError;

  return (
    <div
      className={styles.modalBackdrop}
      role="dialog"
      aria-modal="true"
      aria-labelledby="assinatura-modal-title"
    >
      <form className={styles.modalCard} onSubmit={handleSubmit}>
        <h2 id="assinatura-modal-title" className={styles.modalTitle}>
          {titulo}
        </h2>
        <p className={styles.modalDescription}>{descricao}</p>
        <p className={styles.modalTransicao}>{transicaoLabel}</p>

        {precisaMotivo && (
          <div className={styles.modalField}>
            <label className={styles.modalLabel} htmlFor="motivo-reprovacao">
              Motivo da reprovacao
            </label>
            <textarea
              id="motivo-reprovacao"
              className={styles.modalTextarea}
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              maxLength={1000}
              placeholder="Ex: Cor do logo errada"
              required
            />
          </div>
        )}

        <div className={styles.signatureWrapper}>
          <label className={styles.modalLabel}>Assinatura</label>
          <div ref={canvasContainerRef}>
            {canvasWidth > 0 && (
              <SigCanvas
                ref={sigRef}
                penColor="#000000"
                backgroundColor="#ffffff"
                canvasProps={{
                  className: styles.signatureCanvas,
                  width: canvasWidth,
                  height: 200,
                }}
              />
            )}
          </div>
          <div className={styles.signatureActions}>
            <span className={styles.signatureHint}>
              Assine com o dedo ou mouse no quadro acima.
            </span>
            <button
              type="button"
              className={styles.clearButton}
              onClick={handleLimpar}
            >
              Limpar
            </button>
          </div>
        </div>

        {displayError && (
          <div className={styles.modalError} role="alert">
            {displayError}
          </div>
        )}

        <div className={styles.modalFooter}>
          <button
            type="button"
            className={styles.secondaryButton}
            onClick={onCancelar}
            disabled={loading}
          >
            Cancelar
          </button>
          <button
            type="submit"
            className={isReprovar ? styles.dangerButton : styles.primaryButton}
            disabled={loading}
          >
            {loading ? "Enviando..." : "Confirmar"}
          </button>
        </div>
      </form>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────────
 * Done / Error views
 * ──────────────────────────────────────────────────────────────────── */

function DoneView({
  scan,
  statusAplicado,
  onNovaLeitura,
}: {
  scan: ScanResponse;
  statusAplicado: StatusProva;
  onNovaLeitura: () => void;
}) {
  const mensagem = useMemo(() => {
    const labelAcao = ACTION_LABELS[statusAplicado] ?? STATUS_LABELS[statusAplicado];
    return `${labelAcao} — movimentacao registrada.`;
  }, [statusAplicado]);

  return (
    <div className={styles.successCard}>
      <div className={styles.successIcon} aria-hidden="true">
        ✓
      </div>
      <div className={styles.successTitle}>Tudo certo!</div>
      <p className={styles.successMessage}>
        <strong>{scan.prova.nome}</strong> — {mensagem}
      </p>
      <span className={styles.statusBadge}>
        {STATUS_LABELS[scan.prova.status]}
      </span>
      <button
        type="button"
        className={styles.primaryButton}
        onClick={onNovaLeitura}
      >
        Escanear proxima
      </button>
    </div>
  );
}

function ErrorView({
  message,
  onTentarNovamente,
}: {
  message: string;
  onTentarNovamente: () => void;
}) {
  return (
    <div className={styles.errorCard}>
      <div className={styles.errorTitle}>Nao foi possivel escanear</div>
      <p className={styles.errorMessage}>{message}</p>
      <button
        type="button"
        className={styles.primaryButton}
        onClick={onTentarNovamente}
      >
        Tentar novamente
      </button>
    </div>
  );
}
