"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";
import { useRouter } from "next/navigation";

import { createClient } from "@/lib/supabase/client";
import { CameraIcon, KeyIcon, ArrowRightIcon } from "@/components/icons";
import { useScanner } from "@/hooks/useScanner";
import { useAuthorization } from "@/lib/hooks/use-authorization";
import { Restricted } from "@/components/Restricted";
import {
  identificarProvaPorCodigo,
  identificarProvaPorPayload,
  type CodigoErro,
  type ResultadoIdentificacao,
} from "@/lib/services/identificacao-prova";
import styles from "./escanear.module.css";

/* ──────────────────────────────────────────────────────────────────────
 * Pagina /escanear — Wave 3 v4.0, Componente 10 (atualizacao v4.0).
 *
 * Iteracao 3 (pos-Mario fornecer link do Figma + extracao via MCP).
 * Specs canonicos extraidos de:
 *   - file kqOrPgP07y6y1SV7BUlEBs
 *   - frame Camera node 206:87
 *   - frame Manual node 240:6448
 *
 * Estrategia desta entrega:
 *   - Apenas IDENTIFICACAO: scan/digitacao → /provas/[id].
 *   - Tab Manual usa formato real PRV-AAAA-MM-NNNNNN (Q4 do Mario)
 *     com estilizacao 100% Figma (JetBrains Mono, cores #9a9a9a/#757575,
 *     bg #fafafa, border #e3e3e3, rounded 12px).
 *
 * RBAC (Wave 1 v4.0): rule key "scanner", todos os 4 perfis = full.
 * ──────────────────────────────────────────────────────────────────── */

type Tab = "camera" | "manual";

type CameraState =
  | { kind: "idle" }
  | { kind: "scanning" }
  | { kind: "identifying"; payload: string }
  | { kind: "error"; codigo: CodigoErro; mensagem: string };

type ManualState =
  | { kind: "idle" }
  | { kind: "identifying"; codigo: string }
  | { kind: "error"; codigo: CodigoErro; mensagem: string };

export default function EscanearPage() {
  const router = useRouter();
  const auth = useAuthorization("scanner");

  const [tab, setTab] = useState<Tab>("camera");
  const [cameraState, setCameraState] = useState<CameraState>({ kind: "idle" });
  const [manualState, setManualState] = useState<ManualState>({ kind: "idle" });
  const [codigoManual, setCodigoManual] = useState("");

  const getToken = useCallback(async () => {
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  }, []);

  const handleDetect = useCallback((payload: string) => {
    setCameraState({ kind: "identifying", payload });
  }, []);

  const scanner = useScanner({
    enabled: cameraState.kind === "scanning",
    onDetect: handleDetect,
  });

  useEffect(() => {
    if (
      cameraState.kind === "scanning" &&
      scanner.errorCode === "DISPOSITIVO_SEM_CAMERA"
    ) {
      setCameraState({
        kind: "error",
        codigo: "DISPOSITIVO_SEM_CAMERA",
        mensagem: "Camera indisponivel. Use a digitacao manual.",
      });
    }
  }, [cameraState.kind, scanner.errorCode]);

  useEffect(() => {
    if (cameraState.kind !== "identifying") return;
    let cancelled = false;
    (async () => {
      const result = await identificarProvaPorPayload(cameraState.payload, {
        getToken,
      });
      if (cancelled) return;
      if (result.tipo === "sucesso") {
        router.push(`/provas/${result.prova.prova.id}`);
        return;
      }
      setCameraState({
        kind: "error",
        codigo: result.codigo,
        mensagem: result.mensagem,
      });
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cameraState.kind]);

  const handleManualSubmit = useCallback(
    async (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      const codigo = codigoManual.trim();
      if (!codigo) return;
      setManualState({ kind: "identifying", codigo });
      const result: ResultadoIdentificacao = await identificarProvaPorCodigo(
        codigo,
        { getToken },
      );
      if (result.tipo === "sucesso") {
        router.push(`/provas/${result.prova.prova.id}`);
        return;
      }
      setManualState({
        kind: "error",
        codigo: result.codigo,
        mensagem: result.mensagem,
      });
    },
    [codigoManual, getToken, router],
  );

  const trocarParaManual = useCallback(() => {
    setTab("manual");
    setCameraState({ kind: "idle" });
  }, []);

  const trocarParaCamera = useCallback(() => {
    setTab("camera");
    setManualState({ kind: "idle" });
  }, []);

  const abrirCamera = useCallback(() => {
    setCameraState({ kind: "scanning" });
  }, []);

  const cancelarCamera = useCallback(() => {
    setCameraState({ kind: "idle" });
  }, []);

  const tentarNovamenteCamera = useCallback(() => {
    setCameraState({ kind: "idle" });
  }, []);

  if (auth.loading) return null;
  if (!auth.hasAccess) {
    return <Restricted ruleKey="scanner" profile={auth.profile} />;
  }

  return (
    <div className={styles.pageWrapper}>
      <section className={styles.wrapper}>
        <header className={styles.header}>
          <h1 className={styles.title}>Escanear prova</h1>
          <p className={styles.subtitle}>
            Leia o QR Code da etiqueta com a camera ou insira o codigo
            manualmente para confirmar a proxima movimentacao.
          </p>
        </header>

        <ScannerTabs
          tab={tab}
          onCamera={trocarParaCamera}
          onManual={trocarParaManual}
        />

        <div className={styles.innerCard}>
          {tab === "camera" ? (
            <CameraPanel
              state={cameraState}
              scanner={scanner}
              onAbrir={abrirCamera}
              onCancelar={cancelarCamera}
              onTentarNovamente={tentarNovamenteCamera}
              onTrocarParaManual={trocarParaManual}
            />
          ) : (
            <ManualPanel
              state={manualState}
              codigo={codigoManual}
              onChange={setCodigoManual}
              onSubmit={handleManualSubmit}
            />
          )}
        </div>
      </section>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────── */
/* Sub-componentes                                                      */
/* ──────────────────────────────────────────────────────────────────── */

function ScannerTabs({
  tab,
  onCamera,
  onManual,
}: {
  tab: Tab;
  onCamera: () => void;
  onManual: () => void;
}) {
  return (
    <div className={styles.tabsRow}>
      <div className={styles.tabs} role="tablist" aria-label="Modo de leitura">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "camera"}
          className={`${styles.tab} ${tab === "camera" ? styles.tabActive : ""}`}
          onClick={onCamera}
        >
          <CameraIcon width={20} height={20} aria-hidden="true" />
          <span>Camera</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "manual"}
          className={`${styles.tab} ${tab === "manual" ? styles.tabActive : ""}`}
          onClick={onManual}
        >
          <KeyIcon width={20} height={20} aria-hidden="true" />
          <span>Manual</span>
        </button>
      </div>
    </div>
  );
}

interface CameraPanelProps {
  state: CameraState;
  scanner: ReturnType<typeof useScanner>;
  onAbrir: () => void;
  onCancelar: () => void;
  onTentarNovamente: () => void;
  onTrocarParaManual: () => void;
}

function CameraPanel({
  state,
  scanner,
  onAbrir,
  onCancelar,
  onTentarNovamente,
  onTrocarParaManual,
}: CameraPanelProps) {
  const { titulo, descricao, ctaLabel, ctaHandler, ctaDisabled } = useMemo(
    () => _resolverTextoCamera(state, onAbrir, onCancelar, onTentarNovamente),
    [state, onAbrir, onCancelar, onTentarNovamente],
  );

  return (
    <div className={styles.cameraPanel}>
      {/* Lado esquerdo: previewSlot com gradient + brackets amarelos
          envolvendo o mini-card branco com QR mock (estado idle) ou a
          camera live (estado scanning). */}
      <div className={styles.previewSlot}>
        {state.kind === "scanning" ? (
          <div className={styles.qrMockBox}>
            <CameraLive divId={scanner.divId} ready={scanner.ready} />
            <Brackets />
          </div>
        ) : (
          <div className={styles.qrMockBox}>
            <QRMockCard />
            <Brackets />
          </div>
        )}
        <p className={styles.previewHint}>Centralize o QR Code no quadro</p>
      </div>

      {/* Lado direito: bloco superior (titulo + descricao + CTA) +
          bloco inferior (footer com divisor + Ultima leitura + Ver
          historico). justify-content: space-between separa os dois.
          Specs Figma: footer no node 240:6339+6336+6300 fica em
          left[1258], w[554] — alinhado com a coluna direita,
          NAO com a largura total do innerCard. */}
      <div className={styles.cameraSidebar}>
        <div className={styles.cameraSidebarTop}>
          <h2 className={styles.panelTitle}>{titulo}</h2>
          <p className={styles.panelDescription}>{descricao}</p>

          {state.kind === "error" && (
            <div className={styles.errorBanner} role="alert">
              <strong>{state.mensagem}</strong>
              {state.codigo === "DISPOSITIVO_SEM_CAMERA" && (
                <button
                  type="button"
                  className={styles.linkButton}
                  onClick={onTrocarParaManual}
                >
                  Ir para digitacao manual →
                </button>
              )}
            </div>
          )}

          <button
            type="button"
            className={styles.cameraCta}
            onClick={ctaHandler}
            disabled={ctaDisabled}
          >
            <CameraIcon width={20} height={20} aria-hidden="true" />
            <span>{ctaLabel}</span>
          </button>
        </div>

        <InnerFooter />
      </div>
    </div>
  );
}

function _resolverTextoCamera(
  state: CameraState,
  onAbrir: () => void,
  onCancelar: () => void,
  onTentarNovamente: () => void,
): {
  titulo: string;
  descricao: string;
  ctaLabel: string;
  ctaHandler: () => void;
  ctaDisabled: boolean;
} {
  switch (state.kind) {
    case "idle":
      return {
        titulo: "Pronto para escanear",
        descricao:
          "Aponte a camera para o QR Code da etiqueta. A leitura e instantanea e a movimentacao e registrada com horario e usuario.",
        ctaLabel: "Abrir camera",
        ctaHandler: onAbrir,
        ctaDisabled: false,
      };
    case "scanning":
      return {
        titulo: "Aponte para o QR Code",
        descricao:
          "A camera ja esta ativa. Centralize o codigo no quadro para identificar a prova.",
        ctaLabel: "Cancelar",
        ctaHandler: onCancelar,
        ctaDisabled: false,
      };
    case "identifying":
      return {
        titulo: "Verificando QR Code",
        descricao: "Estamos identificando a prova. Isso leva menos de 2 segundos.",
        ctaLabel: "Aguarde...",
        ctaHandler: () => {},
        ctaDisabled: true,
      };
    case "error":
      return {
        titulo: "Nao foi possivel escanear",
        descricao:
          state.codigo === "DISPOSITIVO_SEM_CAMERA"
            ? "Sem acesso a camera. Use a digitacao manual ou tente novamente apos liberar a permissao."
            : "Tente novamente ou troque para a digitacao manual.",
        ctaLabel: "Tentar novamente",
        ctaHandler: onTentarNovamente,
        ctaDisabled: false,
      };
  }
}

/** 4 brackets amarelos (#f5c518) com inset -10px do parent.
 * Posicionados absolutamente; o parent precisa de position relative. */
function Brackets() {
  return (
    <>
      <span className={styles.bracketTopLeft} aria-hidden="true" />
      <span className={styles.bracketTopRight} aria-hidden="true" />
      <span className={styles.bracketBottomLeft} aria-hidden="true" />
      <span className={styles.bracketBottomRight} aria-hidden="true" />
    </>
  );
}

function CameraLive({ divId, ready }: { divId: string; ready: boolean }) {
  return (
    <div className={styles.cameraLiveWrapper}>
      <div className={styles.cameraLive} id={divId} />
      {!ready && <p className={styles.cameraStatus}>Iniciando camera...</p>}
    </div>
  );
}

/** Mini-card branco com sombra + faixa amarela superior + SVG QR 120x120
 * centralizado. Specs Figma: 300x300, border 1px #ececec, rounded 16px,
 * shadow `0 12px 36px -12px rgba(0,0,0,0.18)`. */
function QRMockCard() {
  return (
    <div className={styles.qrMockCard} aria-hidden="true">
      <div className={styles.qrMockYellowBar} />
      <QRIconSvg className={styles.qrMockSvg} />
    </div>
  );
}

/** Icone SVG do QR Code — replica decorativa do Figma (120x120).
 * Black blocks + 1 quadrado amarelo central. Apenas decorativo. */
function QRIconSvg({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 120 120"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role="presentation"
    >
      {/* Finder pattern top-left (3 squares) */}
      <rect x="0" y="0" width="35" height="35" fill="#000" />
      <rect x="5" y="5" width="25" height="25" fill="#fff" />
      <rect x="10" y="10" width="15" height="15" fill="#000" />

      {/* Finder pattern top-right */}
      <rect x="85" y="0" width="35" height="35" fill="#000" />
      <rect x="90" y="5" width="25" height="25" fill="#fff" />
      <rect x="95" y="10" width="15" height="15" fill="#000" />

      {/* Finder pattern bottom-left */}
      <rect x="0" y="85" width="35" height="35" fill="#000" />
      <rect x="5" y="90" width="25" height="25" fill="#fff" />
      <rect x="10" y="95" width="15" height="15" fill="#000" />

      {/* Center yellow square — destaque do Figma */}
      <rect x="50" y="50" width="20" height="20" fill="#f5c518" />

      {/* Random data dots — visual filler. */}
      <rect x="40" y="5" width="5" height="5" fill="#000" />
      <rect x="50" y="5" width="5" height="5" fill="#000" />
      <rect x="65" y="5" width="5" height="5" fill="#000" />
      <rect x="75" y="5" width="5" height="5" fill="#000" />
      <rect x="40" y="15" width="5" height="5" fill="#000" />
      <rect x="55" y="15" width="5" height="5" fill="#000" />
      <rect x="75" y="15" width="5" height="5" fill="#000" />
      <rect x="45" y="25" width="5" height="5" fill="#000" />
      <rect x="60" y="25" width="5" height="5" fill="#000" />
      <rect x="70" y="25" width="5" height="5" fill="#000" />

      <rect x="5" y="40" width="5" height="5" fill="#000" />
      <rect x="20" y="40" width="5" height="5" fill="#000" />
      <rect x="30" y="40" width="5" height="5" fill="#000" />
      <rect x="40" y="40" width="5" height="5" fill="#000" />
      <rect x="80" y="40" width="5" height="5" fill="#000" />
      <rect x="90" y="40" width="5" height="5" fill="#000" />
      <rect x="100" y="40" width="5" height="5" fill="#000" />
      <rect x="115" y="40" width="5" height="5" fill="#000" />

      <rect x="10" y="50" width="5" height="5" fill="#000" />
      <rect x="25" y="50" width="5" height="5" fill="#000" />
      <rect x="40" y="50" width="5" height="5" fill="#000" />
      <rect x="80" y="50" width="5" height="5" fill="#000" />
      <rect x="95" y="50" width="5" height="5" fill="#000" />
      <rect x="115" y="50" width="5" height="5" fill="#000" />

      <rect x="0" y="60" width="5" height="5" fill="#000" />
      <rect x="15" y="60" width="5" height="5" fill="#000" />
      <rect x="30" y="60" width="5" height="5" fill="#000" />
      <rect x="40" y="60" width="5" height="5" fill="#000" />
      <rect x="80" y="60" width="5" height="5" fill="#000" />
      <rect x="100" y="60" width="5" height="5" fill="#000" />
      <rect x="110" y="60" width="5" height="5" fill="#000" />

      <rect x="5" y="70" width="5" height="5" fill="#000" />
      <rect x="20" y="70" width="5" height="5" fill="#000" />
      <rect x="40" y="70" width="5" height="5" fill="#000" />
      <rect x="80" y="70" width="5" height="5" fill="#000" />
      <rect x="90" y="70" width="5" height="5" fill="#000" />
      <rect x="105" y="70" width="5" height="5" fill="#000" />

      <rect x="40" y="85" width="5" height="5" fill="#000" />
      <rect x="55" y="85" width="5" height="5" fill="#000" />
      <rect x="70" y="85" width="5" height="5" fill="#000" />
      <rect x="80" y="85" width="5" height="5" fill="#000" />
      <rect x="100" y="85" width="5" height="5" fill="#000" />
      <rect x="115" y="85" width="5" height="5" fill="#000" />

      <rect x="45" y="95" width="5" height="5" fill="#000" />
      <rect x="60" y="95" width="5" height="5" fill="#000" />
      <rect x="80" y="95" width="5" height="5" fill="#000" />
      <rect x="95" y="95" width="5" height="5" fill="#000" />
      <rect x="110" y="95" width="5" height="5" fill="#000" />

      <rect x="40" y="105" width="5" height="5" fill="#000" />
      <rect x="50" y="105" width="5" height="5" fill="#000" />
      <rect x="75" y="105" width="5" height="5" fill="#000" />
      <rect x="85" y="105" width="5" height="5" fill="#000" />
      <rect x="100" y="105" width="5" height="5" fill="#000" />
      <rect x="115" y="105" width="5" height="5" fill="#000" />

      <rect x="45" y="115" width="5" height="5" fill="#000" />
      <rect x="65" y="115" width="5" height="5" fill="#000" />
      <rect x="80" y="115" width="5" height="5" fill="#000" />
      <rect x="95" y="115" width="5" height="5" fill="#000" />
    </svg>
  );
}

interface ManualPanelProps {
  state: ManualState;
  codigo: string;
  onChange: (v: string) => void;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
}

function ManualPanel({ state, codigo, onChange, onSubmit }: ManualPanelProps) {
  // Wave 3 v4.0 (C10): formato real PRV-AAAA-MM-NNNNNN com estilizacao
  // 100% Figma (JetBrains Mono, cores #9a9a9a/#757575, bg #fafafa).
  const isLoading = state.kind === "identifying";
  const isError = state.kind === "error";
  const trimmed = codigo.trim();
  const submitDisabled = isLoading || trimmed.length === 0;

  return (
    <form className={styles.manualPanel} onSubmit={onSubmit}>
      {/* Bloco superior (conteudo centralizado vertical) + bloco
          inferior (footer com divisor). justify-content: space-between
          replica o layout do Figma node 240:6611 (divisor w[554])
          + 240:6605/6609 (textos do footer). */}
      <div className={styles.manualPanelTop}>
        <h2 className={styles.panelTitleManual}>Inserir codigo manualmente</h2>
        <p className={styles.panelDescriptionManual}>
          Digite o codigo da etiqueta no formato PRV-AAAA-MM-NNNNNN. A
          movimentacao sera registrada apos a confirmacao.
        </p>

        <div
          className={styles.manualInputWrapper}
          aria-invalid={isError ? "true" : "false"}
        >
          <span className={styles.manualInputPrefix} aria-hidden="true">
            PRV-
          </span>
          <label htmlFor="codigo-manual" className={styles.srOnly}>
            Codigo da prova
          </label>
          <input
            id="codigo-manual"
            type="text"
            className={styles.manualInput}
            value={codigo}
            onChange={(e) => onChange(e.target.value)}
            placeholder="AAAA-MM-NNNNNN"
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
            aria-describedby={isError ? "manual-error" : undefined}
            disabled={isLoading}
          />
        </div>

        {isError && (
          <div id="manual-error" className={styles.errorBanner} role="alert">
            {state.mensagem}
          </div>
        )}

        <button
          type="submit"
          className={styles.manualCta}
          disabled={submitDisabled}
        >
          <span>{isLoading ? "Buscando..." : "Buscar prova"}</span>
          {!isLoading && (
            <ArrowRightIcon width={11} height={11} aria-hidden="true" />
          )}
        </button>
      </div>

      <InnerFooter />
    </form>
  );
}

/** Footer dentro do innerCard branco — placeholder visual.
 * Q3 do Mario: "Ultima leitura ha —" + "Ver historico" desabilitado.
 * Texto 11px #7a7a7a, divisor 1px #e9e9e9 (specs Figma). */
function InnerFooter() {
  return (
    <div className={styles.innerFooter}>
      <span className={styles.innerFooterLabel}>Ultima leitura ha —</span>
      <span
        className={styles.innerFooterLinkDisabled}
        aria-disabled="true"
        title="Disponivel em breve"
      >
        Ver historico
        <ArrowRightIcon width={11} height={11} aria-hidden="true" />
      </span>
    </div>
  );
}
