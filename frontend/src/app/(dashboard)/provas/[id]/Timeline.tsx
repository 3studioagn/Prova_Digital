"use client";

/**
 * Timeline visual — Componente 12 (Wave 3 v4.0).
 *
 * Renderiza dentro do card preto (`.timelineCard` em detalhe.module.css).
 * Recebe `prova` + `movimentacoes` e delega a transformacao para o
 * builder puro em `@/lib/timeline-builder`. Este arquivo eh apenas a
 * camada de apresentacao.
 *
 * Decisoes do Gate 1 implementadas:
 *   D1 Vertical · D2 Mesmo layout + badge rota + bloco laminacao
 *   D3 Bloco visualmente separado · D4 Badge textual do motorista
 *   D5 Multiplos ciclos empilhados · D6 Dot amarelo + badge "Atual" + pulse
 *   D7 Cancelamento card vermelho + no cinza · D8 Check verde + "Concluida"
 *   D9 Estatica · D10 Densa
 *   D11.1 Labels PADRAO/DIRETA -> "Matriz"/"Filial" (em prova.ts)
 *   D11.2 Heuristica vendedor_localizacao para rota=NULL (em prova.ts)
 *
 * Animacoes: framer-motion ja eh dependencia do projeto (Wave 6 + C10
 * v4.0). RNF-010 respeitado via `useReducedMotion`.
 */
import { Fragment, type ReactNode } from "react";
import { motion, useReducedMotion } from "framer-motion";

import {
  buildTimeline,
  type BuiltTimeline,
  type CancellationInfo,
  type CycleGroup,
  type TimelineNode,
} from "@/lib/timeline-builder";
import {
  STATUS_LABELS,
  type ContextoMotorista,
  type MovimentacaoListResponse,
  type ProvaResponse,
  type Setor,
} from "@/lib/types/prova";

import styles from "./timeline.module.css";

// ─── Tabelas de display ──────────────────────────────────────────────────

const SETOR_LABELS: Record<Setor, string> = {
  STUDIO: "3Studio",
  VENDEDOR: "Vendedor",
  MOTORISTA: "Motorista",
  CLICHERIA: "Clicheria",
};

const CONTEXTO_BADGE_LABEL: Record<ContextoMotorista, string> = {
  ida_laminacao: "→ Laminação",
  volta_laminacao: "Laminação →",
  entrega_final: "→ Clicheria",
};

const CYCLE_PHASE_LABEL: Record<CycleGroup["phase"], string> = {
  atual: "Em andamento",
  "passed-reprovacao": "Reprovado",
  "passed-completo": "Concluído",
};

// ─── Formatacao ──────────────────────────────────────────────────────────

function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

// ─── Icones SVG inline (padrao do projeto — sem lucide-react) ────────────

function CheckCircleIcon({
  className,
  ariaHidden = true,
}: {
  className?: string;
  ariaHidden?: boolean;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.4}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden={ariaHidden}
    >
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <path d="M22 4 12 14.01l-3-3" />
    </svg>
  );
}

function AlertTriangleIcon({
  className,
  ariaHidden = true,
}: {
  className?: string;
  ariaHidden?: boolean;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden={ariaHidden}
    >
      <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function BanIcon({
  className,
  ariaHidden = true,
}: {
  className?: string;
  ariaHidden?: boolean;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden={ariaHidden}
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
    </svg>
  );
}

// ─── Subcomponentes ──────────────────────────────────────────────────────

interface TimelineHeaderProps {
  rotaLabel: string;
  isTerminalOk: boolean;
  isCancelled: boolean;
}

function TimelineHeader({
  rotaLabel,
  isTerminalOk,
  isCancelled,
}: TimelineHeaderProps) {
  return (
    <header className={styles.header}>
      <span className={styles.rotaBadge} aria-label={`Rota: ${rotaLabel}`}>
        {`Rota: ${rotaLabel}`}
      </span>
      {isTerminalOk && (
        <span
          className={`${styles.headerStatusBadge} ${styles.headerStatusBadgeOk}`}
        >
          <CheckCircleIcon />
          Concluída
        </span>
      )}
      {isCancelled && (
        <span
          className={`${styles.headerStatusBadge} ${styles.headerStatusBadgeCancelled}`}
        >
          <BanIcon />
          Cancelada
        </span>
      )}
    </header>
  );
}

interface CancellationCardProps {
  info: CancellationInfo;
}

function CancellationCard({ info }: CancellationCardProps) {
  const atorTexto = info.ator
    ? `${info.ator.nome} (${SETOR_LABELS[info.ator.setor]})`
    : null;
  return (
    <div className={styles.cancellationCard} role="alert">
      <AlertTriangleIcon className={styles.cancellationCardIcon} />
      <div className={styles.cancellationCardBody}>
        <p className={styles.cancellationCardTitle}>
          Esta prova foi cancelada
        </p>
        <p className={styles.cancellationCardMeta}>
          {atorTexto && (
            <>
              <strong>Por:</strong> {atorTexto}
              <br />
            </>
          )}
          {info.quandoIso && (
            <>
              <strong>Quando:</strong> {formatDateTime(info.quandoIso)}
              <br />
            </>
          )}
          {info.motivo && (
            <>
              <strong>Motivo:</strong> {info.motivo}
            </>
          )}
        </p>
      </div>
    </div>
  );
}

interface TimelineStepProps {
  node: TimelineNode;
  isLastInGroup: boolean;
  shouldPulse: boolean;
}

function TimelineStep({ node, isLastInGroup, shouldPulse }: TimelineStepProps) {
  const isPending = node.phase === "pending";
  const isCurrent = node.phase === "current";
  const isReprov = node.isReprovacao;
  const isCancel = node.isCancelamento;
  const isTerminalOk = node.isTerminal && !isCancel;

  const itemClass = [
    styles.node,
    isPending && styles.nodePending,
    isCurrent && styles.nodeCurrent,
    !isPending && !isCurrent && !isReprov && !isCancel && !isTerminalOk && styles.nodePassed,
    isReprov && styles.nodeReprovacao,
    isCancel && styles.nodeCancelamento,
    isTerminalOk && styles.nodeTerminalOk,
  ]
    .filter(Boolean)
    .join(" ");

  const ariaLabelParts: string[] = [STATUS_LABELS[node.status]];
  if (isPending) {
    ariaLabelParts.push("pendente");
  } else if (isCurrent) {
    ariaLabelParts.push("etapa atual");
    if (node.createdAt) {
      ariaLabelParts.push(`desde ${formatDateTime(node.createdAt)}`);
    }
    ariaLabelParts.push(
      `por ${node.usuarioNome} (${SETOR_LABELS[node.usuarioSetor]})`,
    );
  } else if (isTerminalOk) {
    ariaLabelParts.push("concluída");
    if (node.createdAt)
      ariaLabelParts.push(`em ${formatDateTime(node.createdAt)}`);
  } else if (isCancel) {
    ariaLabelParts.push("cancelada");
    if (node.createdAt)
      ariaLabelParts.push(`em ${formatDateTime(node.createdAt)}`);
  } else {
    ariaLabelParts.push("concluído");
    if (node.createdAt)
      ariaLabelParts.push(`em ${formatDateTime(node.createdAt)}`);
    ariaLabelParts.push(
      `por ${node.usuarioNome} (${SETOR_LABELS[node.usuarioSetor]})`,
    );
  }

  return (
    <li
      className={itemClass}
      aria-label={ariaLabelParts.join(" — ")}
      aria-current={isCurrent ? "step" : undefined}
    >
      <div className={styles.dotColumn} aria-hidden="true">
        <span className={styles.dot}>
          {isCurrent && shouldPulse && (
            <motion.span
              className={styles.dotPulse}
              animate={{ scale: [1, 1.9, 1], opacity: [0.5, 0, 0.5] }}
              transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
            />
          )}
        </span>
        {!isLastInGroup && (
          <span
            className={`${styles.connector}${
              isPending ? ` ${styles.connectorPending}` : ""
            }`}
          />
        )}
      </div>
      <div className={styles.nodeContent}>
        <div className={styles.nodeHeader}>
          <span className={styles.nodeStatus}>
            {STATUS_LABELS[node.status]}
          </span>
          {node.contexto && !isPending && (
            <span className={styles.motoristaBadge}>
              {CONTEXTO_BADGE_LABEL[node.contexto]}
            </span>
          )}
          {isCurrent && (
            <span className={styles.currentBadge}>Atual</span>
          )}
          {isTerminalOk && node.phase !== "pending" && (
            <span className={styles.terminalBadge}>
              <CheckCircleIcon />
              Concluída
            </span>
          )}
        </div>
        {!isPending && (
          <div className={styles.nodeMeta}>
            <span>{node.usuarioNome}</span>
            <span className={styles.metaDim}>
              {" · "}
              {SETOR_LABELS[node.usuarioSetor]}
            </span>
            {node.createdAt && (
              <span className={styles.metaDim}>
                {" · "}
                {formatDateTime(node.createdAt)}
              </span>
            )}
          </div>
        )}
        {isPending && (
          <div className={`${styles.nodeMeta} ${styles.metaDim}`}>
            Aguardando
          </div>
        )}
        {node.motivoReprovacao && (
          <div className={styles.nodeMotivo}>
            <strong>Motivo:</strong>
            {node.motivoReprovacao}
          </div>
        )}
      </div>
    </li>
  );
}

interface RenderNodesProps {
  nodes: TimelineNode[];
  shouldPulse: boolean;
}

/**
 * Agrupa nos consecutivos com `inLaminationBlock=true` em um wrapper
 * `<div class="laminationBlock">`. Decisao 3 do Gate 1: bloco
 * visualmente separado.
 */
function RenderNodes({ nodes, shouldPulse }: RenderNodesProps) {
  const result: ReactNode[] = [];
  let i = 0;

  while (i < nodes.length) {
    const node = nodes[i];
    if (node.inLaminationBlock) {
      // Coletar nos adjacentes do bloco
      const start = i;
      while (i < nodes.length && nodes[i].inLaminationBlock) {
        i += 1;
      }
      const slice = nodes.slice(start, i);
      result.push(
        <li key={`lam-${start}`} role="group" aria-label="Etapa de laminação">
          <div className={styles.laminationBlock}>
            <p className={styles.laminationBlockTitle}>Etapa de laminação</p>
            <ul className={styles.nodeList} role="list">
              {slice.map((n, sIdx) => (
                <TimelineStep
                  key={n.id}
                  node={n}
                  isLastInGroup={
                    // ultimo do bloco eh isLast SE for o ultimo absoluto da lista
                    start + sIdx === nodes.length - 1
                  }
                  shouldPulse={shouldPulse}
                />
              ))}
            </ul>
          </div>
        </li>,
      );
    } else {
      result.push(
        <TimelineStep
          key={node.id}
          node={node}
          isLastInGroup={i === nodes.length - 1}
          shouldPulse={shouldPulse}
        />,
      );
      i += 1;
    }
  }

  return <>{result}</>;
}

interface TimelineCycleProps {
  cycle: CycleGroup;
  showHeader: boolean;
  cancellationInfo: CancellationInfo | null;
  shouldPulse: boolean;
}

function TimelineCycleItem({
  cycle,
  showHeader,
  cancellationInfo,
  shouldPulse,
}: TimelineCycleProps) {
  const isPassed =
    cycle.phase === "passed-reprovacao" || cycle.phase === "passed-completo";
  const cycleClass = [styles.cycle, isPassed && styles.cyclePassed]
    .filter(Boolean)
    .join(" ");

  return (
    <li className={cycleClass}>
      {showHeader && (
        <div className={styles.cycleHeader}>
          <h3 className={styles.cycleHeaderTitle}>
            <strong>Ciclo {cycle.ciclo}</strong>
            {cycle.phase === "passed-reprovacao" && cycle.reprovadoEm && (
              <>
                {" · reprovado em "}
                {formatDateTime(cycle.reprovadoEm)}
              </>
            )}
          </h3>
          <span
            className={`${styles.cycleHeaderPhase}${
              cycle.phase === "atual"
                ? ` ${styles.cycleHeaderPhaseAtual}`
                : cycle.phase === "passed-reprovacao"
                  ? ` ${styles.cycleHeaderPhaseReprovacao}`
                  : ""
            }`}
          >
            {CYCLE_PHASE_LABEL[cycle.phase]}
          </span>
        </div>
      )}
      {cycle.motivoReprovacao && (
        <p className={styles.cycleHeaderMotivo}>
          <strong>Motivo da reprovação:</strong>
          {cycle.motivoReprovacao}
        </p>
      )}
      <ul className={styles.nodeList} role="list">
        <RenderNodes nodes={cycle.nodes} shouldPulse={shouldPulse} />
      </ul>
      {cycle.phase === "atual" && cancellationInfo && (
        <CancellationCard info={cancellationInfo} />
      )}
    </li>
  );
}

// ─── Componente principal ────────────────────────────────────────────────

interface TimelineProps {
  movimentacoes: MovimentacaoListResponse | null;
  prova: ProvaResponse;
}

export function Timeline({ movimentacoes, prova }: TimelineProps) {
  const reducedMotion = useReducedMotion();
  const shouldPulse = !reducedMotion;

  // Loading state
  if (!movimentacoes) {
    return (
      <div className={styles.fallback}>
        Nao foi possivel carregar o historico.
      </div>
    );
  }

  // Empty state — prova sem movimentacoes E sem rota definida
  if (movimentacoes.total === 0 && !prova.rota && !prova.vendedor_localizacao) {
    return (
      <div className={styles.empty}>
        <p>Esta prova ainda nao teve movimentacoes.</p>
        <p className={styles.emptyHint}>
          A timeline visual fica disponivel quando a prova for escaneada pela
          primeira vez.
        </p>
      </div>
    );
  }

  const built: BuiltTimeline = buildTimeline(prova, movimentacoes);

  if (built.cycles.length === 0) {
    return (
      <div className={styles.empty}>
        <p>Esta prova ainda nao teve movimentacoes.</p>
        <p className={styles.emptyHint}>
          A timeline visual fica disponivel quando a prova for escaneada pela
          primeira vez.
        </p>
      </div>
    );
  }

  return (
    <div
      className={styles.timeline}
      role="region"
      aria-label={`Histórico de movimentações da prova ${prova.nro_requerimento}`}
    >
      <TimelineHeader
        rotaLabel={built.rotaLabel}
        isTerminalOk={built.isTerminalOk}
        isCancelled={built.isCancelled}
      />
      <ol className={styles.cycles} role="list">
        {built.cycles.map((cycle, idx) => (
          <Fragment key={cycle.ciclo}>
            {idx > 0 && (
              <li
                className={styles.cycleSeparator}
                aria-hidden="true"
              >
                {"↻ reinício de ciclo"}
              </li>
            )}
            <TimelineCycleItem
              cycle={cycle}
              showHeader={built.hasMultipleCycles}
              cancellationInfo={built.cancellation}
              shouldPulse={shouldPulse}
            />
          </Fragment>
        ))}
      </ol>
    </div>
  );
}
