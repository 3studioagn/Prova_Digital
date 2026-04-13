"use client";

import { motion } from "framer-motion";
import type {
  MovimentacaoListResponse,
  MovimentacaoResponse,
  ProvaResponse,
  Rota,
  Setor,
  StatusProva,
} from "@/lib/types/prova";
import { ROTA_LABELS, STATUS_LABELS } from "@/lib/types/prova";
import styles from "./timeline.module.css";

// ─── Modelo de dados da timeline ────────────────────────────────────────

interface TimelineNode {
  id: string;
  status: StatusProva;
  usuarioNome: string;
  usuarioSetor: Setor;
  createdAt: string;
  ciclo: number;
  rotaNoMomento: Rota | null;
  motivoReprovacao: string | null;
  isCurrent: boolean;
  isReprovacao: boolean;
  isCancelamento: boolean;
  isTerminal: boolean;
  isRoteamento: boolean;
}

interface CycleGroup {
  ciclo: number;
  nodes: TimelineNode[];
}

// ─── Transformacao de dados ─────────────────────────────────────────────

/**
 * Transforma as movimentacoes brutas + dados da prova em nos renderizaveis.
 *
 * Logica:
 *   1. Adiciona um no implicito "Criada" para o ciclo 1 (antes de qualquer
 *      movimentacao), usando `prova.created_at`.
 *   2. Cada movimentacao gera um no para seu `status_novo`.
 *   3. O ultimo no recebe `isCurrent = true`.
 *   4. Flags booleanas de tipo de no sao derivadas do `status_novo`.
 */
function buildTimelineNodes(
  movimentacoes: MovimentacaoResponse[],
  prova: ProvaResponse,
): TimelineNode[] {
  const nodes: TimelineNode[] = [];
  const hasMovs = movimentacoes.length > 0;

  nodes.push({
    id: "initial-criada",
    status: "CRIADA",
    usuarioNome: "3Studio",
    usuarioSetor: "STUDIO",
    createdAt: prova.created_at,
    ciclo: 1,
    rotaNoMomento: null,
    motivoReprovacao: null,
    isCurrent: !hasMovs,
    isReprovacao: false,
    isCancelamento: false,
    isTerminal: false,
    isRoteamento: false,
  });

  for (let i = 0; i < movimentacoes.length; i++) {
    const m = movimentacoes[i];
    const isLast = i === movimentacoes.length - 1;
    const sNovo = m.status_novo as StatusProva;

    nodes.push({
      id: m.id,
      status: sNovo,
      usuarioNome: m.usuario_nome,
      usuarioSetor: m.usuario_setor,
      createdAt: m.created_at,
      ciclo: m.ciclo,
      rotaNoMomento: m.rota_no_momento,
      motivoReprovacao: m.motivo_reprovacao,
      isCurrent: isLast,
      isReprovacao: sNovo === "REPROVADA_PELO_VENDEDOR",
      isCancelamento: sNovo === "CANCELADA",
      isTerminal: sNovo === "RECEBIDA_PELA_CLICHERIA",
      isRoteamento: sNovo === "APROVADA_PELO_VENDEDOR",
    });
  }

  return nodes;
}

function groupByCycle(nodes: TimelineNode[]): CycleGroup[] {
  const groups: CycleGroup[] = [];
  let current: CycleGroup | null = null;

  for (const node of nodes) {
    if (!current || current.ciclo !== node.ciclo) {
      current = { ciclo: node.ciclo, nodes: [] };
      groups.push(current);
    }
    current.nodes.push(node);
  }

  return groups;
}

// ─── Formatacao ─────────────────────────────────────────────────────────

function formatDateTime(iso: string): string {
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

const SETOR_LABELS: Record<Setor, string> = {
  STUDIO: "3Studio",
  VENDEDOR: "Vendedor",
  MOTORISTA: "Motorista",
  CLICHERIA: "Clicheria",
};

// ─── Framer Motion variants ─────────────────────────────────────────────

const nodeVariants = {
  hidden: { opacity: 0, x: -16 },
  visible: (i: number) => ({
    opacity: 1,
    x: 0,
    transition: { delay: i * 0.07, duration: 0.3, ease: "easeOut" as const },
  }),
};

// ─── Componente ─────────────────────────────────────────────────────────

interface TimelineProps {
  movimentacoes: MovimentacaoListResponse | null;
  prova: ProvaResponse;
}

export function Timeline({ movimentacoes, prova }: TimelineProps) {
  if (!movimentacoes) {
    return (
      <div className={styles.fallback}>
        Nao foi possivel carregar o historico.
      </div>
    );
  }

  if (movimentacoes.total === 0) {
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

  const nodes = buildTimelineNodes(movimentacoes.items, prova);
  const cycles = groupByCycle(nodes);
  const hasMultipleCycles = cycles.length > 1;

  let globalIdx = 0;

  return (
    <div className={styles.timeline}>
      {cycles.map((cycle) => (
        <div key={cycle.ciclo} className={styles.cycleGroup}>
          {hasMultipleCycles && (
            <div className={styles.cycleLabel}>Ciclo {cycle.ciclo}</div>
          )}
          <div className={styles.nodeList}>
            {cycle.nodes.map((node, localIdx) => {
              const animIdx = globalIdx++;
              const isLastInCycle = localIdx === cycle.nodes.length - 1;

              const nodeClass = [
                styles.node,
                node.isCurrent && styles.nodeCurrent,
                node.isReprovacao && styles.nodeReprovacao,
                node.isCancelamento && styles.nodeCancelamento,
                node.isTerminal && !node.isCancelamento && styles.nodeTerminal,
              ]
                .filter(Boolean)
                .join(" ");

              return (
                <motion.div
                  key={node.id}
                  className={nodeClass}
                  custom={animIdx}
                  initial="hidden"
                  animate="visible"
                  variants={nodeVariants}
                >
                  {/* Coluna do ponto + conector vertical */}
                  <div className={styles.dotColumn}>
                    <div className={styles.dot}>
                      {node.isCurrent && (
                        <motion.div
                          className={styles.dotPulse}
                          animate={{
                            scale: [1, 1.9, 1],
                            opacity: [0.5, 0, 0.5],
                          }}
                          transition={{
                            duration: 2,
                            repeat: Infinity,
                            ease: "easeInOut",
                          }}
                        />
                      )}
                    </div>
                    {!isLastInCycle && <div className={styles.connector} />}
                  </div>

                  {/* Conteudo do no */}
                  <div className={styles.nodeContent}>
                    <div className={styles.nodeHeader}>
                      <span className={styles.nodeStatus}>
                        {STATUS_LABELS[node.status]}
                      </span>
                      {node.isRoteamento && node.rotaNoMomento && (
                        <span className={styles.rotaBadge}>
                          {ROTA_LABELS[node.rotaNoMomento]}
                        </span>
                      )}
                      {node.isCurrent && !node.isTerminal && !node.isCancelamento && (
                        <span className={styles.currentBadge}>Atual</span>
                      )}
                    </div>
                    <div className={styles.nodeMeta}>
                      <span>{node.usuarioNome}</span>
                      <span className={styles.metaDim}>
                        {" \u00b7 "}
                        {SETOR_LABELS[node.usuarioSetor]}
                      </span>
                      <span className={styles.metaDim}>
                        {" \u00b7 "}
                        {formatDateTime(node.createdAt)}
                      </span>
                    </div>
                    {node.motivoReprovacao && (
                      <div className={styles.nodeMotivo}>
                        Motivo: {node.motivoReprovacao}
                      </div>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
