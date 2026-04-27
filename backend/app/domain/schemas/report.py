"""Schemas Pydantic v2 para Relatorios Gerenciais (Wave 5, Componente 16).

Implementa RF-015 e US-014 com discriminated union por `scope`:
  - geral      : visao consolidada da operacao
  - 3studio    : visao interna (criacao, retrabalho, cancelamentos)
  - vendedores : visao comercial / responsabilizacao
  - clicheria  : visao produtiva da clicheria

Decisoes registradas:
  - ADR-091 + ADR-099: tempos calculados em HORAS CORRIDAS (consistencia
    com Dashboard da Wave 4; desvio explicito do RN-008 literal).
  - ADR-101 (a registrar no Bloco 5.6): taxa de reprovacao calculada sobre
    CICLOS (RN-006), nao provas. Provas com ciclos reiniciados sao contadas
    multiplas vezes — uma por ciclo.
  - ADR-096 (Bloco 5.2): endpoint unico discriminado por `scope` em vez de
    4-5 endpoints separados. Reduz superficie e numero de roundtrips.

Todos os schemas sao `frozen=True` (imutaveis) — protecao contra mutacao
acidental apos cache hit (camada do report_cache.ReportCache).
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import LocalizacaoEnum, RotaEnum, StatusProvaEnum

# ─── Sub-schemas comuns ────────────────────────────────────────────────────


class PeriodoMeta(BaseModel):
    """Metadados temporais do relatorio (janela aplicada)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    from_: datetime = Field(..., alias="from", serialization_alias="from")
    """Limite inferior (inclusive) do periodo, em UTC."""

    to: datetime
    """Limite superior (exclusive) do periodo, em UTC."""

    total_dias: int
    """Numero de dias na janela (arredondamento up). Min 1."""


class DistStatus(BaseModel):
    """Distribuicao de provas por status (snapshot final do periodo)."""

    model_config = ConfigDict(frozen=True)

    status: StatusProvaEnum
    quantidade: int


class DistRota(BaseModel):
    """Distribuicao de provas por rota (PADRAO vs DIRETA).

    Provas com `rota=NULL` (status pre-aprovacao) sao agrupadas em `nao_definida`
    no schema acumulador (ver `IndicadoresGeral.distribuicao_rota`).
    """

    model_config = ConfigDict(frozen=True)

    rota: RotaEnum | None
    """`None` representa provas com rota nao definida (status pre-aprovacao)."""
    quantidade: int


class PontoSerie(BaseModel):
    """Ponto de serie temporal — usado em 'criadas por dia'."""

    model_config = ConfigDict(frozen=True)

    data: datetime
    """Inicio do bucket (00:00 UTC do dia)."""

    quantidade: int


class CancelamentoTop(BaseModel):
    """Top motivos de cancelamento (3studio scope)."""

    model_config = ConfigDict(frozen=True)

    motivo: str
    """Texto livre fornecido no cancelamento (RN-005)."""

    quantidade: int


class DistLocalizacao(BaseModel):
    """Distribuicao de provas processadas por localizacao do vendedor."""

    model_config = ConfigDict(frozen=True)

    matriz: int
    filial: int


class DistOrigemRota(BaseModel):
    """Distribuicao de provas recebidas pela clicheria por origem de rota."""

    model_config = ConfigDict(frozen=True)

    via_padrao: int
    """Provas que vieram de COM_MOTORISTA → ENVIADA_PARA_CLICHERIA → RECEBIDA."""

    via_direta: int
    """Provas que vieram de ENCAMINHADA_A_CLICHERIA → RECEBIDA (vendedor Filial)."""


# ─── Indicadores por scope ─────────────────────────────────────────────────


class IndicadoresGeral(BaseModel):
    """Indicadores da perspectiva 'geral'."""

    model_config = ConfigDict(frozen=True)

    total_provas: int
    """Provas criadas no periodo."""

    tempo_medio_ciclo_horas: float | None
    """Media de horas (corridas) entre criacao e conclusao (RECEBIDA_PELA_CLICHERIA).
    None se nenhuma prova foi concluida no periodo."""

    tempo_mediano_ciclo_horas: float | None
    """Mediana de horas (corridas) entre criacao e conclusao."""

    tempo_medio_aprovacao_horas: float | None
    """Media de horas entre criacao e primeira decisao do vendedor
    (APROVADA_PELO_VENDEDOR ou REPROVADA_PELO_VENDEDOR).
    None se nenhum ciclo decidiu no periodo."""

    taxa_reprovacao: float
    """Reprovacoes / (aprovacoes + reprovacoes) sobre CICLOS (ADR-101).
    0.0 se denominador for zero. Faixa: 0.0 a 1.0."""

    qtd_atrasadas: int
    """Provas nao-terminais cuja ultima atividade excede tempo_atraso_horas
    (ADR-099 — horas corridas). Snapshot do momento da query, nao filtrado por periodo."""


class Indicadores3Studio(BaseModel):
    """Indicadores da perspectiva '3studio' (operacao interna)."""

    model_config = ConfigDict(frozen=True)

    provas_criadas: int
    """Provas criadas no periodo."""

    media_diaria_criacao: float
    """provas_criadas / total_dias do periodo. Float com 2 casas."""

    reinicios_de_ciclo: int
    """Movimentacoes com status_anterior=REPROVADA, status_novo=CRIADA — RN-006.
    Indica retrabalho."""

    devolvidas_motorista: int
    """Provas que entraram em status COM_MOTORISTA no periodo (transitions count)."""

    reprovadas_aguardando_acao: int
    """Snapshot atual: provas com status REPROVADA_PELO_VENDEDOR (sem reinicio)."""

    cancelamentos: int
    """Movimentacoes com status_novo=CANCELADA no periodo."""

    tempo_medio_criacao_ate_primeira_mov_horas: float | None
    """Media de horas entre criacao da prova e primeira movimentacao registrada
    (responsividade do vendedor para retirar). None se sem movimentacoes."""


class VendedorMetrica(BaseModel):
    """Metricas agregadas de um vendedor no periodo."""

    model_config = ConfigDict(frozen=True)

    vendedor_id: UUID
    vendedor_nome: str
    localizacao: LocalizacaoEnum

    volume: int
    """Provas processadas pelo vendedor no periodo."""

    aprovacoes: int
    """Numero absoluto de aprovacoes do vendedor no periodo (count sobre ciclos)."""

    reprovacoes: int
    """Numero absoluto de reprovacoes do vendedor no periodo (count sobre ciclos)."""

    taxa_aprovacao: float
    """Aprovacoes / (aprovacoes + reprovacoes) sobre ciclos. 0.0 se denominador zero."""

    taxa_reprovacao: float
    """Reprovacoes / (aprovacoes + reprovacoes) sobre ciclos. 0.0 se denominador zero."""

    tempo_medio_retirada_a_decisao_horas: float | None
    """Media de horas entre RETIRADA_PELO_VENDEDOR e (APROVADA|REPROVADA)_PELO_VENDEDOR.
    None se vendedor nao decidiu nenhuma prova no periodo."""

    provas_atrasadas_em_poder: int
    """Snapshot: provas em status RETIRADA ou APROVADA atualmente em poder do
    vendedor que excedem o tempo de atraso (ADR-099)."""


class VendedorAtrasoAtual(BaseModel):
    """Item da lista 'atrasadas em poder' (vendedores com provas vencidas)."""

    model_config = ConfigDict(frozen=True)

    vendedor_id: UUID
    vendedor_nome: str
    localizacao: LocalizacaoEnum
    qtd_atrasadas: int


class ProvaAtrasadaItem(BaseModel):
    """Item da lista de provas atrasadas (visao Geral, top 20).

    Detalha individualmente cada prova nao-terminal cuja ultima
    movimentacao excede o tempo de atraso (ADR-099 — horas corridas).
    Snapshot do momento da query, nao filtrado por periodo.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID
    nome: str
    nro_requerimento: str
    cliente: str
    vendedor_nome: str
    status: StatusProvaEnum
    horas_atrasada: float
    """Horas corridas alem do tempo limite de atraso configurado."""
    ultima_movimentacao_at: datetime
    """Timestamp da ultima movimentacao (ou created_at se nao houver mov)."""


class IndicadoresClicheria(BaseModel):
    """Indicadores da perspectiva 'clicheria'."""

    model_config = ConfigDict(frozen=True)

    recebidas_no_periodo: int
    """Provas que entraram em RECEBIDA_PELA_CLICHERIA no periodo."""

    tempo_medio_aguardando_recebimento_horas: float | None
    """Media de horas entre (ENVIADA|ENCAMINHADA)_A_CLICHERIA e RECEBIDA.
    None se nenhuma prova foi recebida no periodo."""

    em_transito_atual: int
    """Snapshot: COM_MOTORISTA + ENVIADA_PARA_CLICHERIA + ENCAMINHADA_A_CLICHERIA."""

    por_origem_rota: DistOrigemRota
    """Breakdown das recebidas_no_periodo por rota PADRAO vs DIRETA."""


# ─── Respostas tipadas (discriminated union) ───────────────────────────────


class ReportResponseGeral(BaseModel):
    """Resposta de GET /api/v1/reports?scope=geral."""

    model_config = ConfigDict(frozen=True)

    scope: Literal["geral"] = "geral"
    periodo: PeriodoMeta
    indicadores: IndicadoresGeral
    serie_temporal: list[PontoSerie]
    """Provas criadas por dia (00:00 UTC do bucket)."""

    distribuicao_status: list[DistStatus]
    """Provas criadas no periodo agrupadas pelo status atual."""

    distribuicao_rota: list[DistRota]
    """Provas criadas no periodo agrupadas pela rota."""

    ranking: list[VendedorMetrica]
    """Top vendedores por volume no periodo. Reusa o mesmo schema do
    scope=vendedores. Limit hard 200 (mesmo do scope vendedores)."""

    provas_atrasadas: list[ProvaAtrasadaItem]
    """Top 20 provas atualmente atrasadas (snapshot, ordenado por
    `ultima_movimentacao_at` ASC — mais antigas primeiro)."""

    provas_atrasadas_total: int
    """Contagem total de provas atrasadas (sem cap). Permite UI exibir
    'Provas Atrasadas (N)' mesmo quando a lista esta capada em 20."""

    atualizado_em: datetime
    """Timestamp UTC do calculo dos indicadores."""


class ReportResponse3Studio(BaseModel):
    """Resposta de GET /api/v1/reports?scope=3studio."""

    model_config = ConfigDict(frozen=True)

    scope: Literal["3studio"] = "3studio"
    periodo: PeriodoMeta
    indicadores: Indicadores3Studio
    cancelamentos_top: list[CancelamentoTop]
    """Top motivos de cancelamento no periodo (max 10, ordenado DESC)."""

    atualizado_em: datetime


class ReportResponseVendedores(BaseModel):
    """Resposta de GET /api/v1/reports?scope=vendedores."""

    model_config = ConfigDict(frozen=True)

    scope: Literal["vendedores"] = "vendedores"
    periodo: PeriodoMeta
    ranking: list[VendedorMetrica]
    """Vendedores ordenados por `volume` DESC (max 200, default top 50)."""

    distribuicao_localizacao: DistLocalizacao
    """Total de provas por localizacao do vendedor responsavel."""

    atrasadas_em_poder: list[VendedorAtrasoAtual]
    """Vendedores com provas atualmente em RETIRADA/APROVADA estourando RN-008.
    Max 10, ordenado por qtd_atrasadas DESC."""

    atualizado_em: datetime


class ReportResponseClicheria(BaseModel):
    """Resposta de GET /api/v1/reports?scope=clicheria."""

    model_config = ConfigDict(frozen=True)

    scope: Literal["clicheria"] = "clicheria"
    periodo: PeriodoMeta
    indicadores: IndicadoresClicheria
    atualizado_em: datetime


# ─── Discriminated union ───────────────────────────────────────────────────


ReportResponse = Annotated[
    ReportResponseGeral
    | ReportResponse3Studio
    | ReportResponseVendedores
    | ReportResponseClicheria,
    Field(discriminator="scope"),
]
"""Tipo de resposta unificado de /api/v1/reports.

Pydantic resolve qual sub-modelo deserializar via o campo `scope` (literal).
TypeScript no frontend recebe a discriminated union espelhada e usa
narrowing exaustivo via switch/case (sem `if/else` sobre campos opcionais).
"""
