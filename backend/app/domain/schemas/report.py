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
    """Distribuicao de provas por rota (legacy — PADRAO vs DIRETA + NULL).

    Wave 5 v3 — schema preservado para compat. Frontend v4.0 consome
    `distribuicao_rota_v4` para detalhamento por 6 valores + categoria
    legacy.
    """

    model_config = ConfigDict(frozen=True)

    rota: RotaEnum | None
    """`None` representa provas com rota nao definida (status pre-aprovacao)."""
    quantidade: int


# ─── v4.0 (Wave 5 v4.0 / Componente 16) — distribuicao expandida ───────────


RotaCategoria = Literal["matriz", "filial"]
"""Categoria consolidada de rota — agrupa rotas v4.0 e legacy.

- `matriz`: provas com `rota IN {MATRIZ, LAM_MATRIZ, PADRAO}` + provas
  legacy `rota=NULL` cujo vendedor esta em `localizacao=MATRIZ`.
- `filial`: provas com `rota IN {FILIAL, LAM_FILIAL, DIRETA}` + provas
  legacy `rota=NULL` cujo vendedor esta em `localizacao=FILIAL`.

Wave 5 v4.0 (Componente 16): usado por `?rota_categoria=...` na API e
pelo card ROTA do `ReportGeral`. Frontend exibe 2 categorias visualmente
identicas ao v3 (apenas a semantica interna foi expandida).
"""

DistRotaV4Categoria = Literal[
    "v4_matriz",
    "v4_lam_matriz",
    "v4_filial",
    "v4_lam_filial",
    "legacy_padrao",
    "legacy_direta",
    "legacy_null_matriz",
    "legacy_null_filial",
    "legacy_null_indefinida",
]
"""Categoria detalhada de uma entrada de `distribuicao_rota_v4`.

- `v4_*`: rota v4.0 explicita (Wave 2 v4.0).
- `legacy_padrao` / `legacy_direta`: rota legacy v3.0 explicita.
- `legacy_null_*`: rota=NULL com inferencia via `vendedor_localizacao`
  (heuristica do C12 — Decisao 11.2).
- `legacy_null_indefinida`: rota=NULL + sem localizacao (improvavel mas
  defendido).

Frontend agrupa todas as 9 categorias em apenas 2 (matriz/filial) para o
card ROTA atual; expoe o detalhamento completo apenas no CSV summary
(Wave 5 v4.0).
"""


class DistRotaV4(BaseModel):
    """Distribuicao detalhada de provas por rota v4.0 + legacy.

    Wave 5 v4.0 (Componente 16): substituicao funcional do schema `DistRota`
    para a v4.0. `DistRota` (v3) permanece no payload por compat.
    """

    model_config = ConfigDict(frozen=True)

    categoria: DistRotaV4Categoria
    """Categoria detalhada — ver `DistRotaV4Categoria`."""

    rota: RotaEnum | None
    """Rota subjacente (None para legacy NULL inferidas via localizacao)."""

    quantidade: int


class ConsolidacaoRota(BaseModel):
    """Consolidacao da distribuicao por rota em 2 categorias (matriz/filial).

    Wave 5 v4.0 (Componente 16): usado pelo card ROTA do `ReportGeral` para
    preservar o layout v3 (2 dots: Matriz + Filial) ao mesmo tempo em que
    cobre os 6 valores de `rota_enum` + provas legacy NULL.

    Mapeamento:
      - `matriz` = COUNT(rota IN {MATRIZ, LAM_MATRIZ, PADRAO})
                 + COUNT(rota IS NULL AND vendedor.localizacao = MATRIZ)
      - `filial` = COUNT(rota IN {FILIAL, LAM_FILIAL, DIRETA})
                 + COUNT(rota IS NULL AND vendedor.localizacao = FILIAL)
      - `indefinida` = COUNT(rota IS NULL AND vendedor.localizacao IS NULL)
        (improvavel — apenas para integridade matematica do total).
    """

    model_config = ConfigDict(frozen=True)

    matriz: int
    filial: int
    indefinida: int = 0


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
    """Distribuicao de provas recebidas pela clicheria por origem de rota.

    Wave 5 v3 + v4.0 (Componente 16) — semantica expandida em v4.0:
      - `via_padrao`: chegada via motorista. Legacy: `COM_MOTORISTA →
        ENVIADA_PARA_CLICHERIA`. v4.0: `COM_MOTORISTA_ENTREGA_FINAL` (Matriz,
        Lam. Matriz). UI exibe o mesmo card "Via PADRAO (motorista)".
      - `via_direta`: chegada direto do vendedor da filial. Legacy:
        `ENCAMINHADA_A_CLICHERIA`. v4.0: `APROVADA_PELO_VENDEDOR` quando
        a rota e FILIAL ou LAM_FILIAL (sem motorista intermediario).
    """

    model_config = ConfigDict(frozen=True)

    via_padrao: int
    """Chegada via motorista (legacy + v4.0 consolidado)."""

    via_direta: int
    """Chegada direto da filial (legacy + v4.0 consolidado)."""


# ─── v4.0 (Wave 5 v4.0 / Componente 16) — contexto do motorista ────────────


DistContextoMotoristaKey = Literal[
    "ida_laminacao",
    "volta_laminacao",
    "entrega_final",
]
"""3 contextos canonicos do Motorista (US-006 v4.0). Espelha
`ContextoMotorista` do backend Python e do frontend TypeScript."""


class DistContextoMotorista(BaseModel):
    """Distribuicao de provas com motorista por contexto v4.0.

    Wave 5 v4.0 (Componente 16): conta provas atualmente com status de
    motorista (legacy `COM_MOTORISTA` mapeada para `entrega_final` por
    paridade com `contexto_motorista()`). Frontend nao expoe visualmente
    nesta sessao (preserva layout v3); valor disponivel para CSV +
    consumo programatico via API.
    """

    model_config = ConfigDict(frozen=True)

    contexto: DistContextoMotoristaKey
    quantidade: int


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
    """Resposta de GET /api/v1/reports?scope=geral.

    Wave 5 v4.0 (Componente 16): adicionados campos
    `distribuicao_rota_v4` e `consolidacao_rota` (aditivos — clientes
    antigos ignoram). Campo `distribuicao_rota` v3 preservado por compat
    (sera removido na Wave 7 / Componente 21 quando o backfill final
    eliminar `rota IS NULL`).
    """

    model_config = ConfigDict(frozen=True)

    scope: Literal["geral"] = "geral"
    periodo: PeriodoMeta
    indicadores: IndicadoresGeral
    serie_temporal: list[PontoSerie]
    """Provas criadas por dia (00:00 UTC do bucket)."""

    distribuicao_status: list[DistStatus]
    """Provas criadas no periodo agrupadas pelo status atual.

    Cobre os 17 valores de `StatusProvaEnum` (10 v3.0 + 7 v4.0 da Wave 3
    v4.0 / C11). Frontend exibe apenas estados nao-terminais via
    `STATUS_ATIVOS_SET` no donut de provas ativas; CSV summary inclui
    todos os com `quantidade > 0`."""

    distribuicao_rota: list[DistRota]
    """[LEGACY v3] Provas criadas no periodo agrupadas pela rota
    (apenas PADRAO/DIRETA/NULL contam visualmente — provas v4.0 ficam
    como `quantidade=0` neste campo). Preservado para compat."""

    distribuicao_rota_v4: list[DistRotaV4] = []
    """[v4.0] Distribuicao detalhada cobrindo as 9 categorias possiveis
    (4 rotas v4.0 + 2 legacy + 3 sub-buckets para `rota=NULL`). Campo
    aditivo — clientes antigos ignoram. Default lista vazia para nao
    quebrar deserializacao de payloads antigos cached."""

    consolidacao_rota: ConsolidacaoRota = ConsolidacaoRota(
        matriz=0, filial=0, indefinida=0
    )
    """[v4.0] Consolidacao em 2 categorias (matriz/filial) usada pelo card
    ROTA do `ReportGeral`. Preserva layout v3 com semantica v4.0."""

    contexto_motorista_dist: list[DistContextoMotorista] = []
    """[v4.0] Distribuicao de provas atualmente com motorista pelos 3
    contextos canonicos. Snapshot (nao filtrado por periodo). Campo
    aditivo — UI v3 nao consome; CSV expoe."""

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

    serie_temporal: list[PontoSerie]
    """Provas criadas por dia (00:00 UTC do bucket). Mesma fonte do
    scope=geral — `provas_criadas` deste scope agrega exatamente os
    mesmos registros, entao a serie diaria coincide. Usado pelo
    sparkline do card 'PROVAS CRIADAS' no frontend (Wave 5)."""

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
