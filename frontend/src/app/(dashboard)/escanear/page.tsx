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
 * Estrategia desta entrega (analysis.md §1):
 *   - Apenas IDENTIFICACAO: scan + lookup → redireciona para /provas/[id].
 *   - O fluxo de assinatura/transicao NAO esta mais aqui — migra para a
 *     pagina de detalhe na proxima entrega da wave (C11 v4.0).
 *
 * UI fiel ao Figma:
 *   - Header com h1 "Escanear prova" + subtitulo.
 *   - Toggle pill "Camera" / "Manual" (ambos os tabs funcionalmente
 *     clicaveis — modo Manual e o contrato pronto para o C19).
 *   - Card grande cinza claro com:
 *       · Lado esquerdo: subcard branco com preview do QR / camera live.
 *       · Lado direito: titulo + descricao + CTA "Abrir camera".
 *   - Card central (modo Manual): titulo + descricao + input PRV +
 *     botao "Buscar prova →".
 *   - Footer placeholder: "Ultima leitura ha — | Ver historico"
 *     (OUT OF SCOPE Wave 3 v4.0 / C10 — aprovado pelo Mario na Q3 do
 *     pre-Gate-2).
 *
 * RBAC (Wave 1 v4.0 / Componente 05):
 *   - rule key = "scanner", path = "/escanear", match = prefix.
 *   - Os 4 perfis tem `acesso = full`. Anonimo bloqueado pelo middleware.
 *   - Defesa proativa abaixo via `useAuthorization` segue o padrao das
 *     outras pages (M-1 fix da Wave 1 v4.0 Audit Fixes — `loading=true`
 *     evita flash de UI proibida).
 *
 * Atalho global `g s` em `useGlobalShortcuts` continua apontando para
 * esta rota — sem mudanca.
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

  // ── Camera lifecycle ─────────────────────────────────────────────
  const handleDetect = useCallback((payload: string) => {
    setCameraState({ kind: "identifying", payload });
  }, []);

  const scanner = useScanner({
    enabled: cameraState.kind === "scanning",
    onDetect: handleDetect,
  });

  // Erro de hardware/permissao reportado pelo useScanner: traduz em
  // erro tipado e oferece o tab Manual como alternativa.
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

  // ── Identificacao — caminho camera ───────────────────────────────
  useEffect(() => {
    if (cameraState.kind !== "identifying") return;
    let cancelled = false;
    (async () => {
      const result = await identificarProvaPorPayload(cameraState.payload, {
        getToken,
      });
      if (cancelled) return;
      _aplicarResultadoCamera(result);
    })();
    return () => {
      cancelled = true;
    };

    function _aplicarResultadoCamera(result: ResultadoIdentificacao) {
      if (result.tipo === "sucesso") {
        // Sucesso → navega para /provas/[id]. Animacao de feedback CSS
        // pode ser observada brevemente antes do replace via fade.
        router.push(`/provas/${result.prova.prova.id}`);
        return;
      }
      setCameraState({
        kind: "error",
        codigo: result.codigo,
        mensagem: result.mensagem,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cameraState.kind]);

  // ── Identificacao — caminho manual (C19 contract) ────────────────
  const handleManualSubmit = useCallback(
    async (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      const codigo = codigoManual.trim();
      if (!codigo) return;
      setManualState({ kind: "identifying", codigo });
      const result = await identificarProvaPorCodigo(codigo, { getToken });
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

  // ── Defesa proativa RBAC (M-1 fix Wave 1 v4.0) ───────────────────
  if (auth.loading) return null;
  if (!auth.hasAccess) {
    return <Restricted ruleKey="scanner" profile={auth.profile} />;
  }

  return (
    <div className={styles.pageWrapper}>
      <div className={styles.pageHeader}>
        <h1 className={styles.title}>Escanear prova</h1>
        <p className={styles.subtitle}>
          Leia o QR Code da etiqueta com a camera ou insira o codigo
          manualmente para confirmar a proxima movimentacao.
        </p>
      </div>

      <ScannerTabs
        tab={tab}
        onCamera={trocarParaCamera}
        onManual={trocarParaManual}
      />

      <div className={styles.card}>
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
        <CardFooter />
      </div>
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
    <div className={styles.tabs} role="tablist" aria-label="Modo de leitura">
      <button
        type="button"
        role="tab"
        aria-selected={tab === "camera"}
        className={`${styles.tab} ${tab === "camera" ? styles.tabActive : ""}`}
        onClick={onCamera}
      >
        <CameraIcon width={18} height={18} aria-hidden="true" />
        <span>Camera</span>
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={tab === "manual"}
        className={`${styles.tab} ${tab === "manual" ? styles.tabActive : ""}`}
        onClick={onManual}
      >
        <KeyIcon width={18} height={18} aria-hidden="true" />
        <span>Manual</span>
      </button>
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
      <div className={styles.previewSlot}>
        {state.kind === "scanning" ? (
          <CameraLive divId={scanner.divId} ready={scanner.ready} />
        ) : (
          <QRMockPreview />
        )}
        <p className={styles.previewHint}>
          {state.kind === "scanning"
            ? "Centralize o QR Code no quadro"
            : "Centralize o QR Code no quadro"}
        </p>
      </div>

      <div className={styles.cameraSidebar}>
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
          className={styles.primaryButton}
          onClick={ctaHandler}
          disabled={ctaDisabled}
        >
          <CameraIcon width={18} height={18} aria-hidden="true" />
          <span>{ctaLabel}</span>
        </button>
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

function CameraLive({ divId, ready }: { divId: string; ready: boolean }) {
  return (
    <div className={styles.cameraLiveWrapper}>
      <div className={styles.cameraLive} id={divId} />
      <div className={styles.cameraOverlay} aria-hidden="true">
        <span className={styles.bracketTopLeft} />
        <span className={styles.bracketTopRight} />
        <span className={styles.bracketBottomLeft} />
        <span className={styles.bracketBottomRight} />
      </div>
      {!ready && (
        <p className={styles.cameraStatus}>Iniciando camera...</p>
      )}
    </div>
  );
}

function QRMockPreview() {
  // Preview estatico do estado idle — quadrado central com brackets,
  // alinhado a Imagem 1 do Figma.
  return (
    <div className={styles.qrMock} aria-hidden="true">
      <div className={styles.qrMockOverlay}>
        <span className={styles.bracketTopLeft} />
        <span className={styles.bracketTopRight} />
        <span className={styles.bracketBottomLeft} />
        <span className={styles.bracketBottomRight} />
      </div>
      <div className={styles.qrMockSquare}>
        <div className={styles.qrMockYellowStripe} />
        {/* Padrao de "QR" simulado — apenas decorativo. */}
        <div className={styles.qrMockGrid}>
          {Array.from({ length: 49 }, (_, i) => (
            <span
              key={i}
              className={
                _qrMockCell(i)
                  ? styles.qrMockCellOn
                  : styles.qrMockCellOff
              }
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// Padrao deterministico para o mock do QR — apenas decorativo, sem
// significado funcional.
function _qrMockCell(i: number): boolean {
  // Alguns padroes "tipo QR": cantos cheios + quadrados centrais.
  const row = Math.floor(i / 7);
  const col = i % 7;
  // Finder patterns nos cantos
  const tl = row < 3 && col < 3;
  const tr = row < 3 && col > 3;
  const bl = row > 3 && col < 3;
  if (tl || tr || bl) {
    // borda + centro do finder
    if (row === 0 || row === 2 || col === 0 || col === 2) return true;
    if (row === 1 && col === 1) return true;
    return tr && (row === 1 || col === 5);
  }
  // Centro com pseudo-padrao
  return (i * 7 + 3) % 5 < 2;
}

interface ManualPanelProps {
  state: ManualState;
  codigo: string;
  onChange: (v: string) => void;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
}

function ManualPanel({ state, codigo, onChange, onSubmit }: ManualPanelProps) {
  // Wave 3 v4.0 (C10 v4.0): este painel e o **shell visual** + chamada
  // a camada de servico. Nao tem mascara de digitacao avancada nem
  // validacao em tempo real (`validar_formato_codigo_publico` no
  // backend ja rejeita formato invalido com 404 generico). Isso fica
  // para o Componente 19 (Wave 3 v4.0).
  const isLoading = state.kind === "identifying";
  const isError = state.kind === "error";
  const trimmed = codigo.trim();
  const submitDisabled = isLoading || trimmed.length === 0;

  return (
    <form className={styles.manualPanel} onSubmit={onSubmit}>
      <h2 className={styles.panelTitleCenter}>Inserir codigo manualmente</h2>
      <p className={styles.panelDescriptionCenter}>
        Digite o codigo da etiqueta no formato{" "}
        <code className={styles.codigoFormat}>PRV-AAAA-MM-NNNNNN</code>. A
        movimentacao sera registrada apos a confirmacao.
      </p>

      <div className={styles.manualInputWrapper}>
        <label htmlFor="codigo-manual" className={styles.srOnly}>
          Codigo da prova
        </label>
        <input
          id="codigo-manual"
          type="text"
          className={styles.manualInput}
          value={codigo}
          onChange={(e) => onChange(e.target.value)}
          placeholder="PRV-AAAA-MM-NNNNNN"
          autoComplete="off"
          autoCapitalize="characters"
          spellCheck={false}
          aria-invalid={isError ? "true" : "false"}
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
        className={styles.primaryButton}
        disabled={submitDisabled}
      >
        <span>{isLoading ? "Buscando..." : "Buscar prova"}</span>
        {!isLoading && (
          <ArrowRightIcon width={16} height={16} aria-hidden="true" />
        )}
      </button>
    </form>
  );
}

function CardFooter() {
  // Wave 3 v4.0 (C10): footer renderizado como **placeholder visual**.
  // "Ultima leitura" e "Ver historico" requerem endpoint de query do
  // audit_log por usuario — fora do escopo desta entrega (aprovado pelo
  // Mario na Q3 do pre-Gate-2). C18 (Auditoria, Wave 6 v3.0) ja entrega
  // os dados; uma futura wave plugara aqui.
  return (
    <div className={styles.cardFooter}>
      <span className={styles.cardFooterLabel}>Ultima leitura ha —</span>
      <span
        className={styles.cardFooterLinkDisabled}
        aria-disabled="true"
        title="Disponivel em breve"
      >
        Ver historico →
      </span>
    </div>
  );
}
