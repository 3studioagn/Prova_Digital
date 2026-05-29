"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";

// Easing canonico do projeto (espelha ENTER_EASE da /nova-prova).
const ENTER_EASE = [0.32, 0.72, 0, 1] as const;

import { createClient } from "@/lib/supabase/client";
import { CameraIcon, KeyIcon, ArrowRightIcon } from "@/components/icons";
import { useScanner } from "@/hooks/useScanner";
import { useCodigoPrvInput } from "@/hooks/useCodigoPrvInput";
import { useAuthorization } from "@/lib/hooks/use-authorization";
import { Restricted } from "@/components/Restricted";
import {
  identificarProvaPorCodigo,
  type CodigoErro,
  type ResultadoIdentificacao,
  identificarProvaPorPayload,
} from "@/lib/services/identificacao-prova";
// Wave 3 v4.0 / C19 — mensagens customizadas (override do C10 com
// anti-enumeracao em camada UI). Extraidas para modulo standalone em
// 2026-05-11 pos-auditoria (AUD-W3C19-003) para permitir teste de
// integracao da uniformizacao byte-a-byte. Ver `lib/c19-mensagens.ts`
// para a invariante critica e seu teste Vitest (8 cenarios).
import { mensagemFinal } from "@/lib/c19-mensagens";
// Wave 8 v5.0 / C22 — reativacao da tela de assinatura no fluxo de scan.
import { AssinaturaModal } from "@/components/assinatura/AssinaturaModal";
import { deveAbrirAssinatura } from "@/lib/assinatura/helpers";
import type { ScanResponse } from "@/lib/types/prova";
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

  // Wave 8 v5.0 / C22 — ScanResponse da prova identificada cujo ator e o
  // proximo habilitado. Enquanto != null, o modal de assinatura fica aberto.
  const [assinatura, setAssinatura] = useState<ScanResponse | null>(null);

  // Wave 3 v4.0 / C19 — hook que conecta o input do <ManualPanel> aos
  // utilitarios puros de lib/codigo-publico (mascara, auto-uppercase,
  // bloqueio rigido por posicao, validacao de formato).
  const codigoInput = useCodigoPrvInput();

  const getToken = useCallback(async () => {
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  }, []);

  // Wave 8 v5.0 / C22 — destino comum dos dois caminhos de identificacao
  // (camera e digitacao manual). Regra unica confirmada pelo Mario:
  //   - usuario E o proximo ator (transicoes_permitidas nao-vazio) ->
  //     abre o modal de assinatura automaticamente (RF-028);
  //   - caso contrario (nao e a vez dele OU prova terminal) -> abre
  //     /provas/[id] normal, como ja acontecia (Decisao D6).
  // O sub-caso ator-errado FORA do escopo RLS nao chega aqui: o /scan ja
  // retornou 404 e a pagina exibiu o erro generico (anti-enumeracao).
  const handleIdentificada = useCallback(
    (scan: ScanResponse) => {
      if (deveAbrirAssinatura(scan)) {
        setAssinatura(scan);
      } else {
        router.push(`/provas/${scan.prova.id}`);
      }
    },
    [router],
  );

  const handleDetect = useCallback((payload: string) => {
    // AUD-W3C10-004 (race fix): html5-qrcode pode disparar onDetect
    // multiplas vezes em sequencia (frame rate ~10 FPS) ate o cleanup
    // tomar efeito. Sem este guard, o segundo onDetect substituiria o
    // payload do primeiro DEPOIS do effect ja ter comecado a identificar
    // — usuario apontaria para QR A, acabaria em /provas/B.
    // So aceita transicao a partir de "scanning"; demais estados sao
    // no-op (incluindo "identifying", "error" e "idle").
    setCameraState((prev) =>
      prev.kind === "scanning" ? { kind: "identifying", payload } : prev,
    );
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
    // AUD-W3C10-004 + AUD-W3C10-018: deps completas (cameraState, getToken,
    // handleIdentificada) — sem eslint-disable. O early-return barra recomputacoes
    // quando kind != "identifying"; o flag `cancelled` previne side-effects
    // duplicados se um novo payload chegar antes do anterior resolver
    // (combinado com o guard de handleDetect, essa situacao agora exige
    // uma volta explicita por "scanning", entao na pratica nao ocorre).
    if (cameraState.kind !== "identifying") return;
    let cancelled = false;
    (async () => {
      const result = await identificarProvaPorPayload(cameraState.payload, {
        getToken,
      });
      if (cancelled) return;
      if (result.tipo === "sucesso") {
        handleIdentificada(result.prova);
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
  }, [cameraState, getToken, handleIdentificada]);

  const handleManualSubmit = useCallback(
    async (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      const codigo = codigoInput.codigoCompleto;
      if (!codigo) return;
      // Validacao client-side ANTES de chamar o backend (D7 — anti-enumeracao
      // uniformizada via mensagemFinal mapeia QR_INVALIDO -> "Prova nao encontrada").
      // Reduz disparos desnecessarios mas ainda blinda contra timing differential
      // — mensagem retornada e identica ao 404 generico do backend.
      if (!codigoInput.isFormatValid) {
        setManualState({
          kind: "error",
          codigo: "QR_INVALIDO",
          mensagem: mensagemFinal("QR_INVALIDO"),
        });
        return;
      }
      setManualState({ kind: "identifying", codigo });
      const result: ResultadoIdentificacao = await identificarProvaPorCodigo(
        codigo,
        { getToken },
      );
      if (result.tipo === "sucesso") {
        handleIdentificada(result.prova);
        return;
      }
      setManualState({
        kind: "error",
        codigo: result.codigo,
        mensagem: mensagemFinal(result.codigo),
      });
    },
    [
      codigoInput.codigoCompleto,
      codigoInput.isFormatValid,
      getToken,
      handleIdentificada,
    ],
  );

  // D8 — reset do banner de erro quando usuario comeca a editar de novo.
  // O hook esta no container, entao envolvemos `setFromInput` para zerar
  // o estado de erro junto. Sem isso o banner persiste ate o proximo submit.
  const handleManualChange = useCallback(
    (raw: string) => {
      codigoInput.setFromInput(raw);
      if (manualState.kind === "error") {
        setManualState({ kind: "idle" });
      }
    },
    [codigoInput, manualState.kind],
  );

  const trocarParaManual = useCallback(() => {
    setTab("manual");
    setCameraState({ kind: "idle" });
  }, []);

  const trocarParaCamera = useCallback(() => {
    setTab("camera");
    setManualState({ kind: "idle" });
    // codigoInput preservado intencionalmente (R-9): usuario que digitou
    // parcialmente nao perde o trabalho ao olhar a camera por um momento.
  }, []);

  // R-10 — botao "Tentar novamente" no estado de erro de rede: limpa o
  // banner sem mexer no codigo digitado. Usuario clica "Buscar prova"
  // novamente apos restabelecer conexao.
  const tentarNovamenteManual = useCallback(() => {
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
          {/* Iteracao 9 (pos-Mario pedir): crossfade animado entre os
              panels Camera/Manual. AnimatePresence mode="wait" garante
              que o panel atual sai antes do novo entrar (evita
              sobreposicao). Combina fade leve (opacity) + escala
              imperceptivel (0.98 → 1) para suavizar a troca.
              `initial={false}` evita animacao no render inicial. */}
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={tab}
              className={styles.panelMotion}
              initial={{ opacity: 0, scale: 0.985, y: 6 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.985, y: -6 }}
              transition={{ duration: 0.26, ease: ENTER_EASE }}
            >
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
                  display={codigoInput.display}
                  isFormatValid={codigoInput.isFormatValid}
                  onChange={handleManualChange}
                  onSubmit={handleManualSubmit}
                  onTentarNovamente={tentarNovamenteManual}
                />
              )}
            </motion.div>
          </AnimatePresence>
        </div>
      </section>

      {/* Wave 8 v5.0 / C22 — modal de assinatura. Abre automaticamente
          (RF-028) quando a prova identificada tem o usuario logado como
          proximo ator. TODA saida (sucesso, cancelamento, conflito,
          sessao) navega para /provas/[id]. */}
      {assinatura && (
        <AssinaturaModal
          scan={assinatura}
          getToken={getToken}
          onFechar={() => router.push(`/provas/${assinatura.prova.id}`)}
        />
      )}
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
          {/* Wave 3 v4.0 (C10) iteracao 5 — Mario pediu mesma animacao
              do `.segmentBtn` da /nova-prova: pill preto desliza entre
              os tabs via framer-motion `layoutId`. */}
          {tab === "camera" && (
            <motion.span
              layoutId="scanner-tab-pill"
              className={styles.tabPill}
              transition={{ type: "spring", bounce: 0.2, duration: 0.35 }}
              aria-hidden="true"
            />
          )}
          <span className={styles.tabLabel}>
            <CameraIcon width={20} height={20} aria-hidden="true" />
            <span>Camera</span>
          </span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "manual"}
          className={`${styles.tab} ${tab === "manual" ? styles.tabActive : ""}`}
          onClick={onManual}
        >
          {tab === "manual" && (
            <motion.span
              layoutId="scanner-tab-pill"
              className={styles.tabPill}
              transition={{ type: "spring", bounce: 0.2, duration: 0.35 }}
              aria-hidden="true"
            />
          )}
          <span className={styles.tabLabel}>
            <KeyIcon width={20} height={20} aria-hidden="true" />
            <span>Manual</span>
          </span>
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
  /** Texto exibido no <input> apos a mascara, sem o prefixo "PRV-". */
  display: string;
  /** True quando montarCodigoCompleto(display) casa o regex canonico. */
  isFormatValid: boolean;
  /** Recebe valor cru do <input> antes da remascara. */
  onChange: (v: string) => void;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
  /** Limpa o banner de erro sem mexer no display (acionado pelo botao
   *  "Tentar novamente" no estado ERRO_REDE). */
  onTentarNovamente: () => void;
}

function ManualPanel({
  state,
  display,
  isFormatValid,
  onChange,
  onSubmit,
  onTentarNovamente,
}: ManualPanelProps) {
  // Wave 3 v4.0 (C19): valida formato client-side, foco automatico, label
  // estendida e hint sr-only adicional. Visual identico ao shell do C10
  // (JetBrains Mono, cores #9a9a9a/#757575, bg #fafafa) — nada de redesign.
  const isLoading = state.kind === "identifying";
  const isError = state.kind === "error";
  const isErroRede = isError && state.codigo === "ERRO_REDE";

  // Botao habilita SOMENTE quando o formato esta completo e valido.
  // Reforco UX: usuario nao consegue submeter um display parcial. (D5 +
  // anti-enumeracao client-side via mensagem uniformizada.)
  const submitDisabled = isLoading || !isFormatValid;

  // R-8 — foco automatico no mount. Tab "Manual" e remontada cada vez que
  // o usuario alterna (AnimatePresence mode="wait" desmonta o panel
  // anterior antes do novo entrar) — o efeito dispara em cada entrada.
  // Sem dependencias: roda apenas no mount, nao em mudancas posteriores.
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  return (
    <form className={styles.manualPanel} onSubmit={onSubmit}>
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
            Codigo da prova no formato PRV-AAAA-MM-NNNNNN
          </label>
          <input
            ref={inputRef}
            id="codigo-manual"
            type="text"
            // Wave 8 v5.0 / C23 (Decisao 9): teclado nativo mobile otimizado.
            // inputMode="text" — codigo e alfanumerico (PRV-AAAA-MM-NNNNNN);
            // "numeric" excluiria as letras do sufixo. enterKeyHint="search"
            // rotula a tecla de acao como "buscar". font-size do input ja e
            // 16px (escanear.module.css), evitando o auto-zoom do iOS.
            inputMode="text"
            enterKeyHint="search"
            className={styles.manualInput}
            value={display}
            onChange={(e) => onChange(e.target.value)}
            placeholder="AAAA-MM-NNNNNN"
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
            // D10 — aria-describedby aponta para o banner de erro quando
            // ha erro; para o hint estatico caso contrario. Garante que
            // leitores de tela tem orientacao em ambos os modos.
            aria-describedby={isError ? "manual-error" : "manual-hint"}
            // AUD-W3C19-004 — aria-invalid no <input> (alem do wrapper).
            // Leitores de tela esperam o atributo no campo de entrada
            // para anunciar "invalido" quando focado. O wrapper mantem
            // o aria-invalid tambem porque a regra CSS
            // `.manualInputWrapper[aria-invalid="true"]` (escanear.module.css:581)
            // depende do seletor de atributo no contexto pai — mover
            // exigiria tocar o CSS, vetado pelo escopo da sessao.
            aria-invalid={isError ? "true" : "false"}
            disabled={isLoading}
            // Limite hard que espelha backend ScanRequest.codigo max_length=32
            // (AUD-W3C10-012). O codigo final tem 18 chars; aqui usamos
            // 14 (display sem prefixo) — folga ate 32 e do backend.
            maxLength={14}
          />
        </div>

        {/* Hint sr-only — D10. Apenas para leitores de tela. */}
        <span id="manual-hint" className={styles.srOnly}>
          Digite 4 digitos para o ano, 2 digitos para o mes e 6 caracteres
          alfanumericos do alfabeto sem chars ambiguos (sem zero, O, um, I
          ou L). Hifens sao inseridos automaticamente.
        </span>

        {isError && (
          <div id="manual-error" className={styles.errorBanner} role="alert">
            <strong>{state.mensagem}</strong>
            {isErroRede && (
              <button
                type="button"
                className={styles.linkButton}
                onClick={onTentarNovamente}
              >
                Tentar novamente
              </button>
            )}
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
