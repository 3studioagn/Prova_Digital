"""Schemas Pydantic v2 para Relatorios Gerenciais (Wave 5, Componente 16).

Implementa RF-015 (relatorios com metricas agregadas) e US-014 (criterios de aceitacao).

Indicadores:
  - total_geral: total de provas no periodo
  - tempo_medio_aprovacao_horas: media de horas entre RETIRADA e APROVADA
  - total_atrasadas: count de provas ativas com atraso (RN-008)
  - distribuicao_por_rota: provas por rota (PADRAO/DIRETA/SEM_ROTA)
  - distribuicao_por_status: provas ativas por status (para grafico PieChart)
  - por_vendedor: metricas por vendedor (total, aprovadas, reprovadas, taxa, tempo medio)
  - atrasadas: lista de provas atrasadas com dias de atraso (US-014 criterio 2)
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PeriodoFiltro(BaseModel):
    """Filtro de periodo para relatorios. Default: ultimos 30 dias.

    Nota (L-04 auditoria Wave 5): o check `inicio <= fim` e feito no handler
    `get_relatorios` (provas.py:1244) antes de instanciar este modelo, para
    retornar 422 com mensagem em portugues amigavel. Nao duplicar o check
    aqui como `@model_validator` — mantem o handler como fonte unica da
    verdade sobre a regra de periodo.
    """
    model_config = ConfigDict(frozen=True)

    inicio: date
    fim: date


class VendedorRelatorio(BaseModel):
    """Metricas de um vendedor individual no relatorio (RF-015)."""
    model_config = ConfigDict(frozen=True)

    vendedor_id: UUID
    vendedor_nome: str
    vendedor_localizacao: str | None
    total_provas: int
    aprovadas: int
    reprovadas: int
    taxa_reprovacao_pct: float
    """(reprovadas / total_provas) * 100. 0.0 se total_provas = 0."""
    tempo_medio_aprovacao_horas: float | None
    """Media de horas entre a criacao da prova (prova.created_at) e cada
    movimentacao APROVADA. Provas re-aprovadas em novos ciclos contribuem
    multiplas vezes (ADR-095 decisao 3.1). None se nenhuma aprovacao.
    """


class ProvaAtrasada(BaseModel):
    """Prova com atraso — US-014 criterio 2: 'listadas com dias de atraso'."""
    model_config = ConfigDict(frozen=True)

    prova_id: UUID
    nome: str
    nro_requerimento: str
    cliente: str
    vendedor_nome: str
    status: str
    rota: str | None
    dias_atraso: float
    """Dias corridos desde a ultima movimentacao (ou created_at)."""
    ultima_movimentacao_em: datetime


class DistribuicaoRota(BaseModel):
    """Contagem de provas por tipo de rota."""
    model_config = ConfigDict(frozen=True)

    PADRAO: int = 0
    DIRETA: int = 0
    SEM_ROTA: int = 0


class StatusCount(BaseModel):
    """Contagem de provas por status — alimenta PieChart de provas ativas."""
    model_config = ConfigDict(frozen=True)

    status: str
    """Valor do enum (ex: RETIRADA_PELO_VENDEDOR)."""
    label: str
    """Label legivel (ex: Com vendedor)."""
    quantidade: int


class RelatorioResponse(BaseModel):
    """Resposta de GET /api/v1/provas/relatorios (RF-015, US-014)."""
    model_config = ConfigDict(frozen=True)

    periodo: PeriodoFiltro
    total_geral: int
    tempo_medio_aprovacao_horas: float | None
    taxa_reprovacao_geral_pct: float
    """L-10 (auditoria Wave 5 ronda 2): taxa de reprovacao agregada no
    periodo, calculada como (sum(por_vendedor.reprovadas) / total_geral) *
    100. Centralizada no backend para evitar drift com frontend. 0.0 se
    total_geral = 0.
    """
    total_atrasadas: int
    distribuicao_por_rota: DistribuicaoRota
    distribuicao_por_status: list[StatusCount]
    por_vendedor: list[VendedorRelatorio]
    atrasadas: list[ProvaAtrasada]
    atualizado_em: datetime
