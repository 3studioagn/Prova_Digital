/** Tipos TypeScript para Relatorios Gerenciais (Wave 5, Componente 16). */

export interface VendedorRelatorio {
  vendedor_id: string;
  vendedor_nome: string;
  vendedor_localizacao: string | null;
  total_provas: number;
  aprovadas: number;
  reprovadas: number;
  taxa_reprovacao_pct: number;
  tempo_medio_aprovacao_horas: number | null;
}

export interface ProvaAtrasada {
  prova_id: string;
  nome: string;
  nro_requerimento: string;
  cliente: string;
  vendedor_nome: string;
  status: string;
  rota: string | null;
  dias_atraso: number;
  ultima_movimentacao_em: string;
}

export interface DistribuicaoRota {
  PADRAO: number;
  DIRETA: number;
  SEM_ROTA: number;
}

export interface StatusCount {
  status: string;
  label: string;
  quantidade: number;
}

export interface RelatorioResponse {
  periodo: { inicio: string; fim: string };
  total_geral: number;
  tempo_medio_aprovacao_horas: number | null;
  /** L-10 (auditoria Wave 5 ronda 2): taxa de reprovacao agregada no periodo,
   * calculada no backend como (sum(por_vendedor.reprovadas) / total_geral) * 100.
   * Centralizado para evitar drift com o frontend. */
  taxa_reprovacao_geral_pct: number;
  total_atrasadas: number;
  distribuicao_por_rota: DistribuicaoRota;
  distribuicao_por_status: StatusCount[];
  por_vendedor: VendedorRelatorio[];
  atrasadas: ProvaAtrasada[];
  atualizado_em: string;
}
