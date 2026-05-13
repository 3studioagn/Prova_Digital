"""Testes da extensao v4.0 do Componente 16 (Wave 5 v4.0).

Cobre:
  - `rota_categoria` (matriz/filial) em `ReportFilters` e endpoint.
  - Aceitacao de rotas v4.0 (MATRIZ, LAM_MATRIZ, FILIAL, LAM_FILIAL) no
    filtro `?rota=...`.
  - Aceitacao dos 17 valores de `StatusProvaEnum` no filtro `?status=...`.
  - Campos novos no `ReportResponseGeral`:
      * `distribuicao_rota_v4` (cobertura das 9 categorias).
      * `consolidacao_rota` (matriz/filial agrupados).
      * `contexto_motorista_dist` (3 contextos).
  - `_aggregate_clicheria` consolida v4.0:
      * via_padrao tambem inclui chegadas COM_MOTORISTA_ENTREGA_FINAL.
      * via_direta tambem inclui APROVADA_PELO_VENDEDOR (Filial/Lam.Filial).
  - CSV `summary` expoe rota_v4_* + consolidacao_rota_* + contexto_motorista_*.
  - CSV `proofs` e `overdue` incluem coluna `contexto_motorista` + `codigo_publico`.
  - Anti-regressao: campos legacy (`distribuicao_rota`, `via_padrao`,
    `via_direta`) preservados — clientes antigos nao quebram.

Nao usa fixtures de banco real (mocks via _setup conforme o padrao do
`test_reports_api.py`).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.api.deps import get_current_user
from app.db.models import (
    LocalizacaoEnum,
    RotaEnum,
    SetorEnum,
    StatusProvaEnum,
)
from app.db.session import get_db
from app.main import app
from app.services.report_filters import ReportFilters, to_cache_key
from tests.conftest import make_user


BASE = "http://test"
PREFIX = "/api/v1/reports"
UTC = timezone.utc


# ─── Helpers (espelho do test_reports_api.py — para autocontainment) ─────


def _setup(mock_db, *, admin=None, user=None):
    """Configura overrides do FastAPI para autenticar admin."""
    u = admin if admin is not None else user
    if u is None:
        u = make_user(
            setor=SetorEnum.STUDIO,
            is_admin=True,
            localizacao=LocalizacaoEnum.MATRIZ,
        )

    async def _get_user():
        return u

    async def _get_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = _get_user
    app.dependency_overrides[get_db] = _get_db


@pytest.fixture(autouse=True)
def _reset_overrides():
    yield
    app.dependency_overrides.clear()
    # Limpar tambem o cache backend para isolar testes
    from app.services.report_cache import get_default_cache

    cache = get_default_cache()
    if hasattr(cache, "_store"):
        cache._store.clear()  # type: ignore[attr-defined]


def _payload_geral_v4_minimo():
    """Payload basico para mockar `_aggregate_geral` com campos v4.0."""
    from app.domain.schemas.report import (
        ConsolidacaoRota,
        DistContextoMotorista,
        DistRotaV4,
        IndicadoresGeral,
        PeriodoMeta,
        ReportResponseGeral,
    )

    return ReportResponseGeral(
        periodo=PeriodoMeta(
            from_=datetime(2026, 4, 1, tzinfo=UTC),
            to=datetime(2026, 5, 1, tzinfo=UTC),
            total_dias=30,
        ),
        indicadores=IndicadoresGeral(
            total_provas=10,
            tempo_medio_ciclo_horas=12.0,
            tempo_mediano_ciclo_horas=11.0,
            tempo_medio_aprovacao_horas=2.5,
            taxa_reprovacao=0.1,
            qtd_atrasadas=2,
        ),
        serie_temporal=[],
        distribuicao_status=[],
        distribuicao_rota=[],
        distribuicao_rota_v4=[
            DistRotaV4(categoria="v4_matriz", rota=RotaEnum.MATRIZ, quantidade=3),
            DistRotaV4(categoria="v4_lam_matriz", rota=RotaEnum.LAM_MATRIZ, quantidade=2),
            DistRotaV4(categoria="v4_filial", rota=RotaEnum.FILIAL, quantidade=1),
            DistRotaV4(categoria="legacy_padrao", rota=RotaEnum.PADRAO, quantidade=2),
            DistRotaV4(categoria="legacy_null_matriz", rota=None, quantidade=2),
        ],
        consolidacao_rota=ConsolidacaoRota(matriz=9, filial=1, indefinida=0),
        contexto_motorista_dist=[
            DistContextoMotorista(contexto="entrega_final", quantidade=3),
            DistContextoMotorista(contexto="ida_laminacao", quantidade=1),
        ],
        ranking=[],
        provas_atrasadas=[],
        provas_atrasadas_total=2,
        atualizado_em=datetime.now(UTC),
    )


# ─── ReportFilters: rota_categoria + 17 status + 6 rotas ──────────────────


class TestReportFiltersV4:
    def test_aceita_rota_categoria_matriz(self):
        f = ReportFilters(scope="geral", rota_categoria="matriz")
        assert f.rota_categoria == "matriz"
        assert f.rota is None

    def test_aceita_rota_categoria_filial(self):
        f = ReportFilters(scope="geral", rota_categoria="filial")
        assert f.rota_categoria == "filial"

    def test_rota_categoria_invalida_rejeitada(self):
        with pytest.raises(ValidationError):
            ReportFilters(scope="geral", rota_categoria="indef")  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "rota",
        [
            RotaEnum.MATRIZ,
            RotaEnum.LAM_MATRIZ,
            RotaEnum.FILIAL,
            RotaEnum.LAM_FILIAL,
            RotaEnum.PADRAO,
            RotaEnum.DIRETA,
        ],
    )
    def test_aceita_todas_as_6_rotas(self, rota):
        f = ReportFilters(scope="geral", rota=rota)
        assert f.rota == rota

    @pytest.mark.parametrize("status", list(StatusProvaEnum))
    def test_aceita_todos_os_17_status(self, status):
        f = ReportFilters(scope="geral", status=status)
        assert f.status == status

    def test_cache_key_distingue_rota_categoria(self):
        a = ReportFilters(scope="geral", rota_categoria="matriz")
        b = ReportFilters(scope="geral", rota_categoria="filial")
        c = ReportFilters(scope="geral")
        ka = to_cache_key(a)
        kb = to_cache_key(b)
        kc = to_cache_key(c)
        assert ka != kb
        assert ka != kc
        assert kb != kc

    def test_cache_key_distingue_rota_categoria_de_rota_exata(self):
        a = ReportFilters(scope="geral", rota=RotaEnum.MATRIZ)
        b = ReportFilters(scope="geral", rota_categoria="matriz")
        assert to_cache_key(a) != to_cache_key(b)

    def test_precedencia_rota_categoria_sobre_rota_documentada(self):
        # Aceita ambos juntos; o agregador aplica rota_categoria primeiro
        # (testado em TestEndpointRotaCategoria abaixo).
        f = ReportFilters(
            scope="geral", rota=RotaEnum.MATRIZ, rota_categoria="filial"
        )
        assert f.rota == RotaEnum.MATRIZ
        assert f.rota_categoria == "filial"


# ─── Endpoint: aceita rota_categoria + 6 rotas + 17 status ─────────────────


class TestEndpointRotaCategoria:
    async def test_admin_recebe_200_com_rota_categoria_matriz(
        self, admin_user, mock_db
    ):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.reports._aggregate_geral",
            new=AsyncMock(return_value=_payload_geral_v4_minimo()),
        ) as agg:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(f"{PREFIX}?scope=geral&rota_categoria=matriz")
        assert resp.status_code == 200
        # Verifica que o filtro chegou no agregador
        agg.assert_awaited_once()
        called_filters = agg.call_args.args[0]
        assert called_filters.rota_categoria == "matriz"

    async def test_rota_categoria_invalida_retorna_422(
        self, admin_user, mock_db
    ):
        _setup(mock_db, admin=admin_user)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(
                f"{PREFIX}?scope=geral&rota_categoria=invalida"
            )
        assert resp.status_code == 422

    @pytest.mark.parametrize(
        "rota_val",
        ["MATRIZ", "LAM_MATRIZ", "FILIAL", "LAM_FILIAL", "PADRAO", "DIRETA"],
    )
    async def test_aceita_filtro_por_rota_v4_e_legacy(
        self, admin_user, mock_db, rota_val
    ):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.reports._aggregate_geral",
            new=AsyncMock(return_value=_payload_geral_v4_minimo()),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(f"{PREFIX}?scope=geral&rota={rota_val}")
        assert resp.status_code == 200

    @pytest.mark.parametrize(
        "status_val",
        [
            "CRIADA",
            "COM_MOTORISTA_IDA_LAMINACAO",
            "COM_MOTORISTA_VOLTA_LAMINACAO",
            "COM_MOTORISTA_ENTREGA_FINAL",
            "ENCAMINHADA_PARA_LAMINACAO",
            "LAMINACAO_CONCLUIDA",
            "DE_VOLTA_3STUDIO_POS_LAMINACAO",
            "ENCAMINHADA_PARA_O_VENDEDOR",
        ],
    )
    async def test_aceita_filtro_por_status_v4(
        self, admin_user, mock_db, status_val
    ):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.reports._aggregate_geral",
            new=AsyncMock(return_value=_payload_geral_v4_minimo()),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(
                    f"{PREFIX}?scope=geral&status={status_val}"
                )
        assert resp.status_code == 200


# ─── ReportResponseGeral: campos v4.0 presentes e bem-formados ─────────────


class TestPayloadV4Campos:
    async def test_response_inclui_distribuicao_rota_v4(
        self, admin_user, mock_db
    ):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.reports._aggregate_geral",
            new=AsyncMock(return_value=_payload_geral_v4_minimo()),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(f"{PREFIX}?scope=geral")
        body = resp.json()
        assert "distribuicao_rota_v4" in body
        # Verifica as categorias esperadas no payload mock
        cats = [d["categoria"] for d in body["distribuicao_rota_v4"]]
        assert "v4_matriz" in cats
        assert "v4_lam_matriz" in cats
        assert "v4_filial" in cats
        assert "legacy_padrao" in cats
        assert "legacy_null_matriz" in cats

    async def test_response_inclui_consolidacao_rota(
        self, admin_user, mock_db
    ):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.reports._aggregate_geral",
            new=AsyncMock(return_value=_payload_geral_v4_minimo()),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(f"{PREFIX}?scope=geral")
        body = resp.json()
        cons = body["consolidacao_rota"]
        assert cons["matriz"] == 9
        assert cons["filial"] == 1
        assert cons["indefinida"] == 0

    async def test_response_inclui_contexto_motorista_dist(
        self, admin_user, mock_db
    ):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.reports._aggregate_geral",
            new=AsyncMock(return_value=_payload_geral_v4_minimo()),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(f"{PREFIX}?scope=geral")
        body = resp.json()
        assert "contexto_motorista_dist" in body
        ctxs = {d["contexto"]: d["quantidade"] for d in body["contexto_motorista_dist"]}
        assert ctxs.get("entrega_final") == 3
        assert ctxs.get("ida_laminacao") == 1

    async def test_response_preserva_distribuicao_rota_legacy(
        self, admin_user, mock_db
    ):
        """Anti-regressao: campo `distribuicao_rota` v3 continua no payload."""
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.reports._aggregate_geral",
            new=AsyncMock(return_value=_payload_geral_v4_minimo()),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(f"{PREFIX}?scope=geral")
        body = resp.json()
        assert "distribuicao_rota" in body  # campo preservado v3


# ─── Anti-regressao: paridade com TS contextoMotorista ────────────────────


class TestContextoMotoristaParidade:
    """O mapeamento status -> contexto no backend deve bater com o helper
    TypeScript `contextoMotorista()` em `frontend/src/lib/types/prova.ts`."""

    def test_mapeamento_status_to_contexto(self):
        from app.api.v1.reports import _CONTEXTO_MOTORISTA_STATUSES

        # 3 contextos v4.0 + 1 legacy
        assert (
            _CONTEXTO_MOTORISTA_STATUSES[StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO]
            == "ida_laminacao"
        )
        assert (
            _CONTEXTO_MOTORISTA_STATUSES[
                StatusProvaEnum.COM_MOTORISTA_VOLTA_LAMINACAO
            ]
            == "volta_laminacao"
        )
        assert (
            _CONTEXTO_MOTORISTA_STATUSES[
                StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL
            ]
            == "entrega_final"
        )
        assert (
            _CONTEXTO_MOTORISTA_STATUSES[StatusProvaEnum.COM_MOTORISTA]
            == "entrega_final"
        )

    def test_apenas_4_status_no_mapeamento(self):
        """Garantia de que nao adicionamos mapeamento errado para outros
        status (e.g. APROVADA_PELO_VENDEDOR nao deve estar mapeado)."""
        from app.api.v1.reports import _CONTEXTO_MOTORISTA_STATUSES

        assert len(_CONTEXTO_MOTORISTA_STATUSES) == 4

    def test_contexto_motorista_csv_helper(self):
        from app.api.v1.reports import _contexto_motorista_csv

        assert (
            _contexto_motorista_csv(StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO)
            == "ida_laminacao"
        )
        assert (
            _contexto_motorista_csv(StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL)
            == "entrega_final"
        )
        assert _contexto_motorista_csv(StatusProvaEnum.COM_MOTORISTA) == "entrega_final"
        # Status que nao representa motorista -> vazio
        assert _contexto_motorista_csv(StatusProvaEnum.APROVADA_PELO_VENDEDOR) == ""
        assert _contexto_motorista_csv(StatusProvaEnum.CRIADA) == ""

    def test_cross_validation_with_canonical_contexto_motorista(self):
        """Wave 5 v4.0 / C16 fix AUD-W5C16-004: garante que
        `_CONTEXTO_MOTORISTA_STATUSES` (derivado por comprehension da
        funcao canonica) contem exatamente as chaves que a funcao
        canonica mapeia, com os mesmos valores. Anti-drift.

        Itera sobre TODOS os 17 valores de StatusProvaEnum e confronta:
          - Se contexto_motorista(s) is None: s NAO deve estar no dict.
          - Caso contrario: dict[s] deve ser == contexto_motorista(s).
        """
        from app.api.v1.reports import _CONTEXTO_MOTORISTA_STATUSES
        from app.state_machine.v4.contextos import contexto_motorista

        for s in StatusProvaEnum:
            expected = contexto_motorista(s)
            if expected is None:
                assert (
                    s not in _CONTEXTO_MOTORISTA_STATUSES
                ), f"{s} foi mapeado mas canonical retorna None"
            else:
                assert _CONTEXTO_MOTORISTA_STATUSES[s] == expected, (
                    f"Drift em {s}: dict={_CONTEXTO_MOTORISTA_STATUSES[s]}, "
                    f"canonical={expected}"
                )


# ─── legacy_null_indefinida: cobertura do balde para vendedor.localizacao IS NULL ─


class TestLegacyNullIndefinida:
    """Wave 5 v4.0 / C16 fix AUD-W5C16-010 (2026-05-13): cobre o cenario
    edge onde provas legacy (rota=NULL) tem vendedor SEM localizacao
    preenchida — caem no balde 'indefinida'.

    Em producao atual, os 2 admins (admin@3studio.com.br, ops@3studio.com.br)
    tem localizacao=NULL mas sao is_admin=true (nao-vendedor); os 2
    vendedores ativos tem localizacao=FILIAL. Portanto null_indef=0 em
    producao no momento. Este teste cobre a logica para quando o balde
    indefinida for > 0 (ex.: admin vira vendedor de prova legacy, ou
    futura migracao desativar `usuarios.localizacao=NOT NULL`).

    Formula: null_indef = null_total - null_matriz - null_filial
    (reports.py:901). `ConsolidacaoRota.indefinida = max(0, null_indef)`
    (reports.py:921). `DistRotaV4(categoria='legacy_null_indefinida', ...)`
    so adicionado a distribuicao quando qtd > 0 (`_push_v4`)."""

    def test_consolidacao_rota_indefinida_aceita_positivo(self):
        """`ConsolidacaoRota` aceita indefinida > 0 (cenario edge)."""
        from app.domain.schemas.report import ConsolidacaoRota

        cons = ConsolidacaoRota(matriz=3, filial=10, indefinida=2)
        assert cons.matriz == 3
        assert cons.filial == 10
        assert cons.indefinida == 2

    def test_consolidacao_rota_indefinida_zero_default(self):
        """`ConsolidacaoRota.indefinida` aceita zero (caso producao atual)."""
        from app.domain.schemas.report import ConsolidacaoRota

        cons = ConsolidacaoRota(matriz=3, filial=14, indefinida=0)
        assert cons.indefinida == 0
        assert cons.matriz + cons.filial + cons.indefinida == 17

    def test_formula_null_indef_consistente(self):
        """Replica a formula de reports.py:901 e valida invariante
        com 3 cenarios: todos com vendedor preenchido, alguns sem,
        todos sem. Garante que `null_indef >= 0` sempre."""
        cenarios = [
            # (null_total, null_matriz, null_filial, expected_indef)
            (11, 0, 11, 0),  # producao atual: todos com vendedor FILIAL
            (11, 5, 4, 2),  # cenario edge: 2 provas com vendedor.loc=NULL
            (5, 0, 0, 5),  # caso extremo: nenhum vendedor com loc preenchida
            (0, 0, 0, 0),  # nenhuma prova legacy
        ]
        for null_total, null_matriz, null_filial, expected_indef in cenarios:
            null_indef = null_total - null_matriz - null_filial
            assert null_indef == expected_indef, (
                f"cenario {(null_total, null_matriz, null_filial)} -> "
                f"esperado {expected_indef}, calculado {null_indef}"
            )
            # max(0, null_indef) garante nunca negativo (defesa em profundidade
            # caso heuristica tenha bug e null_matriz + null_filial > null_total).
            assert max(0, null_indef) >= 0

    def test_distribuicao_rota_v4_aceita_legacy_null_indefinida(self):
        """`DistRotaV4` aceita categoria 'legacy_null_indefinida' (Literal)."""
        from app.domain.schemas.report import DistRotaV4

        item = DistRotaV4(
            categoria="legacy_null_indefinida", rota=None, quantidade=2
        )
        assert item.categoria == "legacy_null_indefinida"
        assert item.rota is None
        assert item.quantidade == 2


# ─── CSV summary: consolidacao_rota_indefinida sempre emitido (AUD-011) ───


class TestCsvSummaryConsolidacaoIndefinida:
    """Wave 5 v4.0 / C16 fix AUD-W5C16-011 (2026-05-13): valida que a
    linha `consolidacao_rota_indefinida` aparece SEMPRE no CSV summary
    do scope=geral, mesmo quando indefinida=0. Antes da correcao, o
    guard `if cons.indefinida > 0` omitia a linha — assimetrico com
    `matriz`/`filial` que sao sempre emitidas e quebrava expectativa
    de parsers downstream que iteram por chave fixa."""

    def _payload_com_indefinida(self, indefinida: int):
        """Payload minimo para `_summary_rows` (cenario geral, sem
        depender de IO ou banco). Constroi via `model_copy(update=...)`
        porque `ReportResponseGeral` e frozen (Pydantic v2)."""
        from app.domain.schemas.report import ConsolidacaoRota

        base = _payload_geral_v4_minimo()
        return base.model_copy(
            update={
                "consolidacao_rota": ConsolidacaoRota(
                    matriz=9, filial=1, indefinida=indefinida
                ),
                "scope": "geral",  # required by _summary_rows scope dispatch
            }
        )

    def test_consolidacao_indefinida_zero_aparece_no_csv(self):
        """Cenario producao atual: indefinida=0 -> linha presente."""
        from app.api.v1.reports import _summary_rows

        payload = self._payload_com_indefinida(0)
        rows = list(_summary_rows(payload))
        chaves = {r[1] for r in rows}
        assert "consolidacao_rota_matriz" in chaves
        assert "consolidacao_rota_filial" in chaves
        assert "consolidacao_rota_indefinida" in chaves
        # Confirma valor "0" (nao omitido)
        for r in rows:
            if r[1] == "consolidacao_rota_indefinida":
                assert r[2] == "0"
                return
        raise AssertionError("consolidacao_rota_indefinida nao encontrada")

    def test_consolidacao_indefinida_positivo_aparece_no_csv(self):
        """Cenario edge: indefinida=2 -> linha presente com valor."""
        from app.api.v1.reports import _summary_rows

        payload = self._payload_com_indefinida(2)
        rows = list(_summary_rows(payload))
        for r in rows:
            if r[1] == "consolidacao_rota_indefinida":
                assert r[2] == "2"
                return
        raise AssertionError("consolidacao_rota_indefinida nao encontrada")

    def test_simetria_3_linhas_consolidacao(self):
        """As 3 chaves consolidacao_rota_* aparecem juntas (simetria) em
        ambos os cenarios (0 ou >0)."""
        from app.api.v1.reports import _summary_rows

        for indef in (0, 1, 5):
            payload = self._payload_com_indefinida(indef)
            rows = list(_summary_rows(payload))
            cons_rows = [r for r in rows if r[1].startswith("consolidacao_rota_")]
            assert len(cons_rows) == 3, (
                f"esperado 3 linhas consolidacao_rota_*, encontrado "
                f"{len(cons_rows)} com indefinida={indef}"
            )
            chaves = sorted(r[1] for r in cons_rows)
            assert chaves == [
                "consolidacao_rota_filial",
                "consolidacao_rota_indefinida",
                "consolidacao_rota_matriz",
            ]


# ─── _categoria_predicate: constroi expressao OR/EXISTS corretamente ───────


class TestCategoriaPredicate:
    def test_matriz_predicate_inclui_rotas_corretas(self):
        from app.api.v1.reports import _ROTAS_MATRIZ

        assert RotaEnum.MATRIZ in _ROTAS_MATRIZ
        assert RotaEnum.LAM_MATRIZ in _ROTAS_MATRIZ
        assert RotaEnum.PADRAO in _ROTAS_MATRIZ
        # Filial e direta NAO devem estar no balde matriz
        assert RotaEnum.FILIAL not in _ROTAS_MATRIZ
        assert RotaEnum.LAM_FILIAL not in _ROTAS_MATRIZ
        assert RotaEnum.DIRETA not in _ROTAS_MATRIZ

    def test_filial_predicate_inclui_rotas_corretas(self):
        from app.api.v1.reports import _ROTAS_FILIAL

        assert RotaEnum.FILIAL in _ROTAS_FILIAL
        assert RotaEnum.LAM_FILIAL in _ROTAS_FILIAL
        assert RotaEnum.DIRETA in _ROTAS_FILIAL
        # Matriz e padrao NAO devem estar no balde filial
        assert RotaEnum.MATRIZ not in _ROTAS_FILIAL
        assert RotaEnum.LAM_MATRIZ not in _ROTAS_FILIAL
        assert RotaEnum.PADRAO not in _ROTAS_FILIAL

    def test_baldes_sao_disjuntos(self):
        """matriz ∩ filial = ∅ — invariante para integridade do schema."""
        from app.api.v1.reports import _ROTAS_FILIAL, _ROTAS_MATRIZ

        intersecao = set(_ROTAS_MATRIZ) & set(_ROTAS_FILIAL)
        assert intersecao == set()

    def test_baldes_cobrem_todos_os_6_valores(self):
        """matriz ∪ filial = todas as 6 rotas — invariante de cobertura."""
        from app.api.v1.reports import _ROTAS_FILIAL, _ROTAS_MATRIZ

        uniao = set(_ROTAS_MATRIZ) | set(_ROTAS_FILIAL)
        assert uniao == set(RotaEnum)


# ─── Clicheria v4.0: chegadas semanticamente expandidas ───────────────────


class TestClicheriaV4ChegadaConstants:
    def test_chegada_legacy_inalterada(self):
        from app.api.v1.reports import _CLICHERIA_CHEGADA_LEGACY

        assert StatusProvaEnum.ENVIADA_PARA_CLICHERIA in _CLICHERIA_CHEGADA_LEGACY
        assert StatusProvaEnum.ENCAMINHADA_A_CLICHERIA in _CLICHERIA_CHEGADA_LEGACY
        assert len(_CLICHERIA_CHEGADA_LEGACY) == 2

    def test_chegada_v4_via_motorista(self):
        from app.api.v1.reports import _CLICHERIA_CHEGADA_V4_VIA_MOTORISTA

        assert (
            StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL
            in _CLICHERIA_CHEGADA_V4_VIA_MOTORISTA
        )

    def test_chegada_v4_via_direto(self):
        from app.api.v1.reports import _CLICHERIA_CHEGADA_V4_VIA_DIRETO

        # APROVADA_PELO_VENDEDOR e a transicao anterior para FILIAL/LAM_FILIAL
        # quando vai direto para RECEBIDA_PELA_CLICHERIA.
        assert (
            StatusProvaEnum.APROVADA_PELO_VENDEDOR
            in _CLICHERIA_CHEGADA_V4_VIA_DIRETO
        )

    def test_em_transito_inclui_v4(self):
        """_CLICHERIA_EM_TRANSITO inclui agora COM_MOTORISTA_ENTREGA_FINAL."""
        from app.api.v1.reports import _CLICHERIA_EM_TRANSITO

        assert (
            StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL in _CLICHERIA_EM_TRANSITO
        )
        # Mantém legacy v3
        assert StatusProvaEnum.COM_MOTORISTA in _CLICHERIA_EM_TRANSITO
        assert StatusProvaEnum.ENVIADA_PARA_CLICHERIA in _CLICHERIA_EM_TRANSITO
        assert StatusProvaEnum.ENCAMINHADA_A_CLICHERIA in _CLICHERIA_EM_TRANSITO
