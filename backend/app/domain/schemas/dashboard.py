"""Schemas Pydantic v2 para o Dashboard em Tempo Real (Wave 4, Componente 15).

Implementa RF-014 (contadores em tempo real) e RN-008 (calculo de atraso).

Os contadores sao derivados por query sobre provas_digitais e movimentacoes.
O layout do Figma define quais contadores sao exibidos no frontend.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DashboardContadores(BaseModel):
    """Contadores agregados do dashboard (RF-014).

    Todos os contadores possiveis sao calculados pelo backend. O frontend
    consome apenas os que o design Figma especifica.
    """
    model_config = ConfigDict(frozen=True)

    criadas_hoje: int
    """Provas criadas hoje (created_at >= 00:00 BRT), qualquer status."""

    com_vendedor: int
    """Provas em status RETIRADA_PELO_VENDEDOR."""

    aprovadas: int
    """Provas em status APROVADA_PELO_VENDEDOR."""

    reprovadas: int
    """Provas em status REPROVADA_PELO_VENDEDOR."""

    aguardando_envio: int
    """Provas em status DE_VOLTA_3STUDIO (aguardando motorista)."""

    com_motorista: int
    """Provas em status COM_MOTORISTA."""

    na_clicheria: int
    """Provas em ENVIADA_PARA_CLICHERIA + ENCAMINHADA_A_CLICHERIA."""

    concluidas: int
    """Provas em status RECEBIDA_PELA_CLICHERIA."""

    atrasadas: int
    """Provas nao-terminais cuja ultima atividade excede tempo_atraso_horas (RN-008)."""


class AtrasadaPorVendedor(BaseModel):
    """Item do breakdown de atrasadas por vendedor (Figma: lista no card Atrasadas)."""
    model_config = ConfigDict(frozen=True)

    vendedor_nome: str
    quantidade: int


class DashboardResponse(BaseModel):
    """Resposta de GET /api/v1/provas/dashboard."""
    model_config = ConfigDict(frozen=True)

    contadores: DashboardContadores
    total_ativas: int
    """Total de provas em status nao-terminal (exclui RECEBIDA e CANCELADA)."""

    tempo_atraso_horas: int
    """Valor atual de tempo_atraso_horas_uteis da configuracao (RN-008)."""

    atrasadas_por_vendedor: list[AtrasadaPorVendedor]
    """Breakdown de atrasadas agrupado por vendedor (top 10, ordenado DESC)."""

    atualizado_em: datetime
    """Timestamp UTC do momento em que os contadores foram calculados."""
