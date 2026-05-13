/**
 * Timeline builder — transformacao pura de `ProvaResponse` +
 * `MovimentacaoListResponse` em estrutura renderizavel pela `<Timeline>`.
 *
 * Wave 3 v4.0 / Componente 12. Modulo puro, testavel em
 * `vitest --environment node` (sem DOM). Helpers consumidos pelos
 * subcomponentes da Timeline.
 *
 * Decisoes de design (Gate 1 do C12):
 * - D1 vertical · D2 mesmo layout + bloco laminacao · D3 bloco visualmente
 *   separado · D4 badge textual do motorista · D5 multiplos ciclos
 *   empilhados · D7 cancelamento como card transversal + no cinza
 *   terminal · D8 check verde no terminal · D11 heuristica para rota=NULL.
 *
 * Tudo aqui e puro: zero side effects, zero DOM, zero React.
 */
import {
  type ContextoMotorista,
  type MovimentacaoListResponse,
  type MovimentacaoResponse,
  type ProvaResponse,
  type Rota,
  type Setor,
  type StatusProva,
  contextoMotorista,
  getRotaEtapas,
  getRotaLabel,
  isInLaminationBlock,
} from "@/lib/types/prova";

// ─── Tipos publicos ───────────────────────────────────────────────────────

/** Fase de cada step na timeline (Decisao 6 do Gate 1 do C12). */
export type StepPhase = "passed" | "current" | "pending";

/** No renderizavel — uma etapa concreta (ou implicita CRIADA). */
export interface TimelineNode {
  id: string;
  status: StatusProva;
  usuarioNome: string;
  usuarioSetor: Setor;
  createdAt: string | null; // null em pendentes
  ciclo: number;
  rotaNoMomento: Rota | null;
  motivoReprovacao: string | null;
  phase: StepPhase;
  isReprovacao: boolean;
  isCancelamento: boolean;
  isTerminal: boolean;
  isRoteamento: boolean;
  inLaminationBlock: boolean;
  contexto: ContextoMotorista | null;
}

/** Fase do ciclo. */
export type CyclePhase =
  | "atual" // o ciclo vigente (prova.ciclo_atual)
  | "passed-reprovacao" // ciclo anterior encerrado em REPROVADA
  | "passed-completo"; // ciclo anterior fechado por outro motivo (raro)

/** Agrupamento de um ciclo. */
export interface CycleGroup {
  ciclo: number;
  phase: CyclePhase;
  nodes: TimelineNode[];
  motivoReprovacao: string | null;
  reprovadoEm: string | null;
  reprovadoPor: { nome: string; setor: Setor } | null;
}

/** Card transversal de cancelamento (Decisao 7 do Gate 1). */
export interface CancellationInfo {
  motivo: string | null;
  ator: { nome: string; setor: Setor } | null;
  quandoIso: string | null;
}

/** Estrutura completa renderizada pela `<Timeline>`. */
export interface BuiltTimeline {
  cycles: CycleGroup[];
  rotaLabel: string;
  hasMultipleCycles: boolean;
  isTerminalOk: boolean;
  isCancelled: boolean;
  cancellation: CancellationInfo | null;
}

// ─── Implementacao ────────────────────────────────────────────────────────

/**
 * Gera nodos concretos a partir das movimentacoes brutas + prova.
 *
 * Logica:
 *   1. Adiciona um no implicito "Criada" para o ciclo 1 (antes de
 *      qualquer movimentacao) usando `prova.created_at`.
 *   2. Cada movimentacao gera um no concreto para seu `status_novo`.
 *   3. O ultimo no recebe phase=`current` se nao-terminal e
 *      nao-cancelado; senao `passed`.
 *   4. Flags + contexto + inLaminationBlock derivados.
 *
 * NAO inclui etapas pendentes — essas sao calculadas separadamente em
 * `derivePendingNodes`.
 */
function buildConcreteNodes(
  prova: ProvaResponse,
  movimentacoes: readonly MovimentacaoResponse[],
): TimelineNode[] {
  const nodes: TimelineNode[] = [];
  const hasMovs = movimentacoes.length > 0;
  const provaStatus = prova.status;
  const provaInTerminal =
    provaStatus === "RECEBIDA_PELA_CLICHERIA" || provaStatus === "CANCELADA";

  // No implicito CRIADA (ciclo 1, ator implicito 3Studio).
  nodes.push({
    id: "initial-criada",
    status: "CRIADA",
    usuarioNome: "3Studio",
    usuarioSetor: "STUDIO",
    createdAt: prova.created_at,
    ciclo: 1,
    rotaNoMomento: null,
    motivoReprovacao: null,
    phase: hasMovs ? "passed" : provaInTerminal ? "passed" : "current",
    isReprovacao: false,
    isCancelamento: false,
    isTerminal: false,
    isRoteamento: false,
    inLaminationBlock: false,
    contexto: null,
  });

  for (let i = 0; i < movimentacoes.length; i++) {
    const m = movimentacoes[i];
    const isLast = i === movimentacoes.length - 1;
    const sNovo = m.status_novo;
    const isReprov = sNovo === "REPROVADA_PELO_VENDEDOR";
    const isCancel = sNovo === "CANCELADA";
    const isTerminal = sNovo === "RECEBIDA_PELA_CLICHERIA";

    nodes.push({
      id: m.id,
      status: sNovo,
      usuarioNome: m.usuario_nome,
      usuarioSetor: m.usuario_setor,
      createdAt: m.created_at,
      ciclo: m.ciclo,
      rotaNoMomento: m.rota_no_momento,
      motivoReprovacao: m.motivo_reprovacao,
      // Ultimo no real: current se nao-terminal e nao-cancelado; senao passed.
      phase: isLast && !isTerminal && !isCancel ? "current" : "passed",
      isReprovacao: isReprov,
      isCancelamento: isCancel,
      isTerminal,
      isRoteamento: sNovo === "APROVADA_PELO_VENDEDOR",
      inLaminationBlock: isInLaminationBlock(sNovo),
      contexto: contextoMotorista(sNovo),
    });
  }

  return nodes;
}

/**
 * Detecta as etapas pendentes do ciclo ATUAL — aquelas que ainda nao
 * apareceram em `concreteNodes`. Usa `getRotaEtapas` para derivar a
 * sequencia canonica (incluindo heuristica Decisao 11.2 para rota=NULL).
 *
 * NAO renderiza pendentes para:
 *   - Provas em terminal sucesso (RECEBIDA_PELA_CLICHERIA)
 *   - Provas canceladas
 *   - Provas reprovadas no ciclo atual (esta esperando reinicio)
 *   - Ciclos passados (`ciclo !== prova.ciclo_atual`)
 *
 * Devolve nos com `phase=pending`, `usuarioNome="—"`, `createdAt=null`
 * etc. — sao stubs para visualizar o futuro.
 */
function derivePendingNodes(
  prova: ProvaResponse,
  concreteNodesAtualCiclo: TimelineNode[],
): TimelineNode[] {
  if (
    prova.status === "RECEBIDA_PELA_CLICHERIA" ||
    prova.status === "CANCELADA" ||
    prova.status === "REPROVADA_PELO_VENDEDOR"
  ) {
    return [];
  }

  const etapas = getRotaEtapas(prova.rota, prova.vendedor_localizacao);
  if (etapas.length === 0) {
    return [];
  }

  // Conjunto de status ja atingidos no ciclo atual.
  const visitados = new Set<StatusProva>();
  for (const node of concreteNodesAtualCiclo) {
    visitados.add(node.status);
  }

  const pendingStatuses: StatusProva[] = [];
  let encontrouAtual = false;
  for (const status of etapas) {
    if (!encontrouAtual && status === prova.status) {
      encontrouAtual = true;
      continue;
    }
    if (encontrouAtual && !visitados.has(status)) {
      pendingStatuses.push(status);
    }
  }

  return pendingStatuses.map((status, idx) => ({
    id: `pending-${prova.ciclo_atual}-${idx}-${status}`,
    status,
    usuarioNome: "—",
    usuarioSetor: "STUDIO", // placeholder; nao usado em pendente
    createdAt: null,
    ciclo: prova.ciclo_atual,
    rotaNoMomento: null,
    motivoReprovacao: null,
    phase: "pending",
    isReprovacao: false,
    isCancelamento: false,
    isTerminal: status === "RECEBIDA_PELA_CLICHERIA",
    isRoteamento: false,
    inLaminationBlock: isInLaminationBlock(status),
    contexto: contextoMotorista(status),
  }));
}

/**
 * Agrupa nos por ciclo + anexa metadata (motivo de reprovacao, ator e
 * timestamp do final do ciclo, fase do ciclo).
 *
 * Cada ciclo anterior (`ciclo < prova.ciclo_atual`) termina com uma
 * movimentacao para REPROVADA — extrai o motivo e quem reprovou.
 * O ciclo atual fica com `phase=atual`.
 */
function groupCyclesWithMetadata(
  nodes: TimelineNode[],
  prova: ProvaResponse,
): CycleGroup[] {
  const groups: CycleGroup[] = [];
  let current: CycleGroup | null = null;

  for (const node of nodes) {
    if (!current || current.ciclo !== node.ciclo) {
      current = {
        ciclo: node.ciclo,
        phase: node.ciclo === prova.ciclo_atual ? "atual" : "passed-completo",
        nodes: [],
        motivoReprovacao: null,
        reprovadoEm: null,
        reprovadoPor: null,
      };
      groups.push(current);
    }
    current.nodes.push(node);

    if (node.isReprovacao) {
      current.phase = "passed-reprovacao";
      current.motivoReprovacao = node.motivoReprovacao;
      current.reprovadoEm = node.createdAt;
      current.reprovadoPor = {
        nome: node.usuarioNome,
        setor: node.usuarioSetor,
      };
    }
  }

  return groups;
}

/**
 * Extrai info do cancelamento (Decisao 7 do Gate 1).
 *
 * Procura a movimentacao com `status_novo === "CANCELADA"` no ciclo
 * atual. Usa `prova.motivo_cancelamento` como fonte do motivo (a
 * movimentacao nao guarda motivo — RN-005 + audit_log).
 */
function extractCancellationInfo(
  prova: ProvaResponse,
  movimentacoes: readonly MovimentacaoResponse[],
): CancellationInfo | null {
  if (prova.status !== "CANCELADA") return null;
  const movCancelamento = movimentacoes.find(
    (m) => m.status_novo === "CANCELADA",
  );
  return {
    motivo: prova.motivo_cancelamento,
    ator: movCancelamento
      ? { nome: movCancelamento.usuario_nome, setor: movCancelamento.usuario_setor }
      : null,
    quandoIso: movCancelamento ? movCancelamento.created_at : null,
  };
}

/**
 * Pipeline principal — composicao dos helpers acima. Recebe o que o
 * `useProvaDetail` ja entrega e produz a estrutura renderizavel.
 *
 * Pode receber `movimentacoes=null` (loading) — devolve uma
 * `BuiltTimeline` vazia com rotaLabel resolvido.
 */
export function buildTimeline(
  prova: ProvaResponse,
  movimentacoes: MovimentacaoListResponse | null,
): BuiltTimeline {
  const rotaLabel = getRotaLabel(prova.rota, prova.vendedor_localizacao);
  const isTerminalOk = prova.status === "RECEBIDA_PELA_CLICHERIA";
  const isCancelled = prova.status === "CANCELADA";

  if (!movimentacoes) {
    return {
      cycles: [],
      rotaLabel,
      hasMultipleCycles: false,
      isTerminalOk,
      isCancelled,
      cancellation: null,
    };
  }

  const concreteNodes = buildConcreteNodes(prova, movimentacoes.items);

  // Pendentes so para o ciclo ATUAL — pega os nos do ciclo_atual
  // antes de adicionar pendentes.
  const concretosCicloAtual = concreteNodes.filter(
    (n) => n.ciclo === prova.ciclo_atual,
  );
  const pendingNodes = derivePendingNodes(prova, concretosCicloAtual);

  const allNodes = [...concreteNodes, ...pendingNodes];
  const cycles = groupCyclesWithMetadata(allNodes, prova);

  return {
    cycles,
    rotaLabel,
    hasMultipleCycles: cycles.length > 1,
    isTerminalOk,
    isCancelled,
    cancellation: extractCancellationInfo(prova, movimentacoes.items),
  };
}

// ─── Helpers exportados para testes ───────────────────────────────────────

export const __internals = {
  buildConcreteNodes,
  derivePendingNodes,
  groupCyclesWithMetadata,
  extractCancellationInfo,
};
