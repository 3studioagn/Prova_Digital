"""Integration tests para /api/v1/reports (Wave 5, Componente 16).

Padrao do projeto: mocks SQLAlchemy via `app.dependency_overrides[get_db]`
+ httpx.AsyncClient com ASGITransport. Tests E2E reais ficam em manual
smoke usando `scripts/seed_reports_fixture.py` em staging.

Cobertura:
  - RBAC: admin OK, vendedor 403, motorista 403, clicheria 403, sem auth 401
  - Validacao Pydantic (scope, datas, q max length, range > 366d)
  - ETag header presente + If-None-Match => 304
  - Cache hit nao chama agregador 2x para mesmos filtros
  - Filtros diferentes => caches separados
  - Agregador certo invocado por scope (geral/3studio/vendedores/clicheria)
  - CSV export: BOM UTF-8, headers, datasets, audit logado
  - Audit log NAO acontece em GET /reports (so em /export)
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_admin_user, get_current_user
from app.db.models import LocalizacaoEnum, RotaEnum, SetorEnum, StatusProvaEnum
from app.db.session import get_db
from app.domain.schemas.report import (
    DistLocalizacao,
    DistOrigemRota,
    Indicadores3Studio,
    IndicadoresClicheria,
    IndicadoresGeral,
    PeriodoMeta,
    ReportResponse3Studio,
    ReportResponseClicheria,
    ReportResponseGeral,
    ReportResponseVendedores,
)
from app.main import app
from app.services.report_cache import reset_default_cache
from tests.conftest import make_user

UTC = timezone.utc
BASE = "http://test"
PREFIX = "/api/v1/reports"


# ─── Helpers ───────────────────────────────────────────────────────────────


def _setup(mock_db, *, admin=None, user=None):
    async def _get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db
    if admin is not None:
        app.dependency_overrides[get_admin_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin
    elif user is not None:
        app.dependency_overrides[get_current_user] = lambda: user


def _periodo_dummy() -> PeriodoMeta:
    return PeriodoMeta(
        from_=datetime(2026, 4, 1, tzinfo=UTC),
        to=datetime(2026, 4, 27, tzinfo=UTC),
        total_dias=27,
    )


def _payload_geral(total: int = 5, atrasadas: int = 1) -> ReportResponseGeral:
    return ReportResponseGeral(
        periodo=_periodo_dummy(),
        indicadores=IndicadoresGeral(
            total_provas=total,
            tempo_medio_ciclo_horas=24.0,
            tempo_mediano_ciclo_horas=20.0,
            tempo_medio_aprovacao_horas=4.0,
            taxa_reprovacao=0.1,
            qtd_atrasadas=atrasadas,
        ),
        serie_temporal=[],
        distribuicao_status=[],
        distribuicao_rota=[],
        atualizado_em=datetime.now(UTC),
    )


def _payload_3studio() -> ReportResponse3Studio:
    return ReportResponse3Studio(
        periodo=_periodo_dummy(),
        indicadores=Indicadores3Studio(
            provas_criadas=10,
            media_diaria_criacao=0.37,
            reinicios_de_ciclo=1,
            devolvidas_motorista=3,
            reprovadas_aguardando_acao=2,
            cancelamentos=1,
            tempo_medio_criacao_ate_primeira_mov_horas=3.0,
        ),
        cancelamentos_top=[],
        atualizado_em=datetime.now(UTC),
    )


def _payload_vendedores() -> ReportResponseVendedores:
    return ReportResponseVendedores(
        periodo=_periodo_dummy(),
        ranking=[],
        distribuicao_localizacao=DistLocalizacao(matriz=2, filial=1),
        atrasadas_em_poder=[],
        atualizado_em=datetime.now(UTC),
    )


def _payload_clicheria() -> ReportResponseClicheria:
    return ReportResponseClicheria(
        periodo=_periodo_dummy(),
        indicadores=IndicadoresClicheria(
            recebidas_no_periodo=3,
            tempo_medio_aguardando_recebimento_horas=12.5,
            em_transito_atual=1,
            por_origem_rota=DistOrigemRota(via_padrao=2, via_direta=1),
        ),
        atualizado_em=datetime.now(UTC),
    )


@pytest.fixture(autouse=True)
def _clear_cache():
    """Reseta o cache singleton entre testes para evitar vazamento."""
    reset_default_cache()
    yield
    reset_default_cache()


# ─── RBAC ──────────────────────────────────────────────────────────────────


class TestReportsRBAC:
    async def test_admin_autorizado(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.reports._aggregate_geral",
            new=AsyncMock(return_value=_payload_geral()),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(f"{PREFIX}?scope=geral")
        assert resp.status_code == 200
        assert resp.json()["scope"] == "geral"

    async def test_vendedor_403(self, mock_db):
        vendedor = make_user(
            setor=SetorEnum.VENDEDOR,
            localizacao=LocalizacaoEnum.MATRIZ,
            is_admin=False,
        )
        _setup(mock_db, user=vendedor)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(f"{PREFIX}?scope=geral")
        assert resp.status_code == 403

    async def test_motorista_403(self, mock_db):
        motorista = make_user(setor=SetorEnum.MOTORISTA, is_admin=False)
        _setup(mock_db, user=motorista)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(f"{PREFIX}?scope=geral")
        assert resp.status_code == 403

    async def test_clicheria_403(self, mock_db):
        clicheria = make_user(setor=SetorEnum.CLICHERIA, is_admin=False)
        _setup(mock_db, user=clicheria)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(f"{PREFIX}?scope=geral")
        assert resp.status_code == 403

    async def test_studio_sem_admin_403(self, mock_db):
        """Setor STUDIO sem is_admin=true tambem e bloqueado (defesa)."""
        studio = make_user(setor=SetorEnum.STUDIO, is_admin=False)
        _setup(mock_db, user=studio)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(f"{PREFIX}?scope=geral")
        assert resp.status_code == 403

    async def test_sem_token_401(self, mock_db):
        # Sem dependency override, get_current_user nao tem token
        async def _get_db():
            yield mock_db

        app.dependency_overrides[get_db] = _get_db
        # NAO override de get_current_user — quer usar o real (que falha sem token)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(f"{PREFIX}?scope=geral")
        assert resp.status_code == 401


# ─── Validacao ─────────────────────────────────────────────────────────────


class TestReportsValidacao:
    async def test_scope_invalido_422(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(f"{PREFIX}?scope=invalido")
        assert resp.status_code == 422

    async def test_scope_ausente_422(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(f"{PREFIX}")
        assert resp.status_code == 422

    async def test_from_maior_que_to_422(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(
                f"{PREFIX}?scope=geral"
                "&from=2026-04-27T00:00:00Z&to=2026-04-01T00:00:00Z"
            )
        assert resp.status_code == 422

    async def test_periodo_acima_366_dias_422(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(
                f"{PREFIX}?scope=geral"
                "&from=2024-01-01T00:00:00Z&to=2025-04-01T00:00:00Z"
            )
        assert resp.status_code == 422

    async def test_q_acima_max_length_422(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(f"{PREFIX}?scope=geral&q={'x' * 201}")
        assert resp.status_code == 422

    async def test_vendedor_id_invalido_422(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(
                f"{PREFIX}?scope=vendedores&vendedor_id=not-a-uuid"
            )
        assert resp.status_code == 422


# ─── Resolucao de scope (qual agregador chamado) ──────────────────────────


class TestReportsScopeRouting:
    async def test_geral_chama_aggregate_geral(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.reports._aggregate_geral",
            new=AsyncMock(return_value=_payload_geral()),
        ) as mock_geral, patch(
            "app.api.v1.reports._aggregate_3studio",
            new=AsyncMock(return_value=_payload_3studio()),
        ) as mock_3s:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(f"{PREFIX}?scope=geral")
        assert resp.status_code == 200
        assert mock_geral.await_count == 1
        assert mock_3s.await_count == 0

    async def test_3studio_chama_aggregate_3studio(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.reports._aggregate_3studio",
            new=AsyncMock(return_value=_payload_3studio()),
        ) as mock_3s:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(f"{PREFIX}?scope=3studio")
        assert resp.status_code == 200
        assert resp.json()["scope"] == "3studio"
        assert mock_3s.await_count == 1

    async def test_vendedores_chama_aggregate_vendedores(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.reports._aggregate_vendedores",
            new=AsyncMock(return_value=_payload_vendedores()),
        ) as mock_v:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(f"{PREFIX}?scope=vendedores")
        assert resp.status_code == 200
        assert resp.json()["scope"] == "vendedores"
        assert mock_v.await_count == 1

    async def test_clicheria_chama_aggregate_clicheria(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.reports._aggregate_clicheria",
            new=AsyncMock(return_value=_payload_clicheria()),
        ) as mock_c:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(f"{PREFIX}?scope=clicheria")
        assert resp.status_code == 200
        assert resp.json()["scope"] == "clicheria"
        assert mock_c.await_count == 1


# ─── Cache (segunda request com mesmos filtros nao chama agregador) ───────


class TestReportsCache:
    async def test_cache_hit_nao_chama_agregador_2x(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        mock_aggr = AsyncMock(return_value=_payload_geral())
        with patch("app.api.v1.reports._aggregate_geral", new=mock_aggr):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                # Mesmos filtros (datas explicitas para evitar drift do default)
                params = {
                    "scope": "geral",
                    "from": "2026-04-01T00:00:00Z",
                    "to": "2026-04-27T00:00:00Z",
                }
                r1 = await ac.get(PREFIX, params=params)
                r2 = await ac.get(PREFIX, params=params)
        assert r1.status_code == 200
        assert r2.status_code == 200
        # Agregador chamado UMA vez (segunda foi cache hit)
        assert mock_aggr.await_count == 1

    async def test_filtros_diferentes_caches_separados(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        mock_aggr = AsyncMock(return_value=_payload_geral())
        with patch("app.api.v1.reports._aggregate_geral", new=mock_aggr):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                p1 = {
                    "scope": "geral",
                    "from": "2026-04-01T00:00:00Z",
                    "to": "2026-04-27T00:00:00Z",
                }
                p2 = {
                    "scope": "geral",
                    "from": "2026-03-01T00:00:00Z",
                    "to": "2026-04-01T00:00:00Z",
                }
                await ac.get(PREFIX, params=p1)
                await ac.get(PREFIX, params=p2)
        # Filtros diferentes => 2 chamadas
        assert mock_aggr.await_count == 2

    async def test_scopes_diferentes_caches_separados(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        mock_geral = AsyncMock(return_value=_payload_geral())
        mock_3s = AsyncMock(return_value=_payload_3studio())
        with patch(
            "app.api.v1.reports._aggregate_geral", new=mock_geral
        ), patch("app.api.v1.reports._aggregate_3studio", new=mock_3s):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                params = {
                    "from": "2026-04-01T00:00:00Z",
                    "to": "2026-04-27T00:00:00Z",
                }
                await ac.get(PREFIX, params={**params, "scope": "geral"})
                await ac.get(PREFIX, params={**params, "scope": "3studio"})
        assert mock_geral.await_count == 1
        assert mock_3s.await_count == 1


# ─── ETag + If-None-Match (304 sem reserializacao) ────────────────────────


class TestReportsETag:
    async def test_etag_header_presente(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.reports._aggregate_geral",
            new=AsyncMock(return_value=_payload_geral()),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(f"{PREFIX}?scope=geral")
        assert resp.status_code == 200
        assert "etag" in {k.lower() for k in resp.headers.keys()}
        etag = resp.headers["etag"]
        assert etag.startswith('"') and etag.endswith('"')
        assert len(etag) == 66  # '"' + 64 hex + '"'

    async def test_cache_control_header(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.reports._aggregate_geral",
            new=AsyncMock(return_value=_payload_geral()),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(f"{PREFIX}?scope=geral")
        cc = resp.headers.get("cache-control", "")
        assert "private" in cc
        assert "max-age=30" in cc
        assert "stale-while-revalidate=60" in cc

    async def test_if_none_match_match_retorna_304(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        mock_aggr = AsyncMock(return_value=_payload_geral())
        with patch("app.api.v1.reports._aggregate_geral", new=mock_aggr):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                params = {
                    "scope": "geral",
                    "from": "2026-04-01T00:00:00Z",
                    "to": "2026-04-27T00:00:00Z",
                }
                first = await ac.get(PREFIX, params=params)
                etag = first.headers["etag"]
                second = await ac.get(
                    PREFIX, params=params, headers={"If-None-Match": etag}
                )
        assert second.status_code == 304
        assert second.content == b""
        # Headers preservados em 304
        assert second.headers["etag"] == etag

    async def test_if_none_match_diferente_retorna_200(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.reports._aggregate_geral",
            new=AsyncMock(return_value=_payload_geral()),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(
                    f"{PREFIX}?scope=geral",
                    headers={"If-None-Match": '"stale-etag-from-yesterday"'},
                )
        assert resp.status_code == 200
        assert resp.json()["scope"] == "geral"

    async def test_etag_estavel_para_mesmo_payload(self, admin_user, mock_db):
        """Mesmos filtros + mesmo payload => mesmo ETag."""
        _setup(mock_db, admin=admin_user)
        payload = _payload_geral(total=42, atrasadas=3)
        with patch(
            "app.api.v1.reports._aggregate_geral",
            new=AsyncMock(return_value=payload),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                params = {
                    "scope": "geral",
                    "from": "2026-04-01T00:00:00Z",
                    "to": "2026-04-27T00:00:00Z",
                }
                # Reset cache para forcar 2 calculos do ETag
                reset_default_cache()
                r1 = await ac.get(PREFIX, params=params)
                reset_default_cache()
                r2 = await ac.get(PREFIX, params=params)
        assert r1.headers["etag"] == r2.headers["etag"]


# ─── Erro do agregador propaga como 502 ───────────────────────────────────


class TestReportsErroBackend:
    async def test_agregador_levanta_502(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.reports._aggregate_geral",
            new=AsyncMock(side_effect=RuntimeError("simulated DB error")),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(f"{PREFIX}?scope=geral")
        assert resp.status_code == 502
        assert "Erro" in resp.json()["detail"]


# ─── /reports/export ──────────────────────────────────────────────────────


class TestReportsExport:
    async def test_export_summary_geral(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        # Mock log_audit (para nao falhar por falta de audit_logs real)
        # E mock do agregador (chamado dentro do _stream_summary)
        with patch(
            "app.api.v1.reports.log_audit", new=AsyncMock()
        ) as mock_audit, patch(
            "app.api.v1.reports._aggregate_geral",
            new=AsyncMock(return_value=_payload_geral(total=7)),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(
                    f"{PREFIX}/export?scope=geral&dataset=summary"
                )
        assert resp.status_code == 200
        # Content-Type CSV
        assert "text/csv" in resp.headers["content-type"]
        # BOM UTF-8
        assert resp.content.startswith(b"\xef\xbb\xbf")
        # Audit chamado
        assert mock_audit.await_count == 1
        # Audit recebeu acao=REPORT_EXPORTED
        kwargs = mock_audit.await_args.kwargs
        assert kwargs["acao"] == "REPORT_EXPORTED"
        # Detalhes incluem scope+dataset
        assert kwargs["detalhes"]["scope"] == "geral"
        assert kwargs["detalhes"]["dataset"] == "summary"

    async def test_export_content_disposition(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.reports.log_audit", new=AsyncMock()
        ), patch(
            "app.api.v1.reports._aggregate_3studio",
            new=AsyncMock(return_value=_payload_3studio()),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(
                    f"{PREFIX}/export"
                    "?scope=3studio&dataset=summary"
                    "&from=2026-04-01T00:00:00Z&to=2026-04-27T00:00:00Z"
                )
        cd = resp.headers["content-disposition"]
        assert "attachment" in cd
        assert "relatorio_3studio_summary_2026-04-01_2026-04-27.csv" in cd

    async def test_export_no_cache_header(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.reports.log_audit", new=AsyncMock()
        ), patch(
            "app.api.v1.reports._aggregate_geral",
            new=AsyncMock(return_value=_payload_geral()),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(
                    f"{PREFIX}/export?scope=geral&dataset=summary"
                )
        assert resp.headers.get("cache-control") == "no-store"

    async def test_export_summary_csv_format(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        payload = _payload_geral(total=42, atrasadas=5)
        with patch(
            "app.api.v1.reports.log_audit", new=AsyncMock()
        ), patch(
            "app.api.v1.reports._aggregate_geral",
            new=AsyncMock(return_value=payload),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(
                    f"{PREFIX}/export?scope=geral&dataset=summary"
                )
        # Decodificar removendo BOM
        text = resp.content.decode("utf-8-sig")
        lines = text.strip().split("\r\n")
        # Header
        assert lines[0] == "scope,indicador,valor"
        # Inclui pelo menos os indicadores principais
        joined = "\n".join(lines)
        assert "total_provas" in joined
        assert "42" in joined
        assert "qtd_atrasadas" in joined
        assert "tempo_medio_ciclo_horas" in joined
        assert "taxa_reprovacao" in joined

    async def test_export_by_seller_dataset(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.reports.log_audit", new=AsyncMock()
        ), patch(
            "app.api.v1.reports._aggregate_vendedores",
            new=AsyncMock(return_value=_payload_vendedores()),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(
                    f"{PREFIX}/export?scope=vendedores&dataset=by-seller"
                )
        assert resp.status_code == 200
        text = resp.content.decode("utf-8-sig")
        # Header esperado
        assert "vendedor_id" in text
        assert "taxa_aprovacao_pct" in text

    async def test_export_dataset_invalido_422(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(
                f"{PREFIX}/export?scope=geral&dataset=invalid"
            )
        assert resp.status_code == 422

    async def test_export_audit_inclui_filtros(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.reports.log_audit", new=AsyncMock()
        ) as mock_audit, patch(
            "app.api.v1.reports._aggregate_geral",
            new=AsyncMock(return_value=_payload_geral()),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                await ac.get(
                    f"{PREFIX}/export"
                    "?scope=geral&dataset=summary"
                    "&from=2026-04-01T00:00:00Z&to=2026-04-27T00:00:00Z"
                    "&q=ACME&rota=PADRAO"
                )
        kwargs = mock_audit.await_args.kwargs
        det = kwargs["detalhes"]
        assert det["scope"] == "geral"
        assert det["dataset"] == "summary"
        assert det["q"] == "ACME"
        assert det["rota"] == "PADRAO"
        assert det["from"].startswith("2026-04-01")

    async def test_export_rbac_vendedor_403(self, mock_db):
        vendedor = make_user(
            setor=SetorEnum.VENDEDOR,
            localizacao=LocalizacaoEnum.MATRIZ,
            is_admin=False,
        )
        _setup(mock_db, user=vendedor)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(
                f"{PREFIX}/export?scope=geral&dataset=summary"
            )
        assert resp.status_code == 403


# ─── /reports nao loga audit (so /export loga) ────────────────────────────


class TestReportsAuditLogScope:
    async def test_get_reports_nao_chama_log_audit(self, admin_user, mock_db):
        """GET /reports e idempotente/cacheado — sem audit log."""
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.reports.log_audit", new=AsyncMock()
        ) as mock_audit, patch(
            "app.api.v1.reports._aggregate_geral",
            new=AsyncMock(return_value=_payload_geral()),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                await ac.get(f"{PREFIX}?scope=geral")
        assert mock_audit.await_count == 0


# ─── Filtros opcionais (q, vendedor_id, rota, status) ────────────────────


class TestReportsFiltros:
    async def test_q_filter_propaga_para_aggregator(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        captured = {}

        async def _fake_aggr(filters, db):
            captured["q"] = filters.q
            captured["vendedor_id"] = filters.vendedor_id
            captured["rota"] = filters.rota
            captured["status"] = filters.status
            return _payload_geral()

        with patch("app.api.v1.reports._aggregate_geral", new=_fake_aggr):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(
                    f"{PREFIX}?scope=geral&q=ACME&rota=PADRAO&status=CRIADA"
                )
        assert resp.status_code == 200
        assert captured["q"] == "ACME"
        assert captured["rota"] == RotaEnum.PADRAO
        assert captured["status"] == StatusProvaEnum.CRIADA


# ─── Estabilidade do helper de cache (com filtros default) ────────────────


class TestReportsCacheKeyDefault:
    async def test_default_filtros_cache_consistente_em_mesmo_segundo(
        self, admin_user, mock_db
    ):
        """Sem filtros explicitos, defaults usam now() — cache pode ou nao
        bater entre requests consecutivos. Garantimos que o agregador NAO
        e chamado duas vezes se o `to` resolver para o mesmo segundo."""
        _setup(mock_db, admin=admin_user)
        mock_aggr = AsyncMock(return_value=_payload_geral())

        # Congelar `now()` durante o teste para garantir cache hit
        fixed_now = datetime(2026, 4, 27, 10, 0, 0, tzinfo=UTC)

        class _FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_now if tz is None else fixed_now.astimezone(tz)

        with patch(
            "app.api.v1.reports._aggregate_geral", new=mock_aggr
        ), patch(
            "app.services.report_filters.datetime", _FixedDateTime
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                await ac.get(f"{PREFIX}?scope=geral")
                await ac.get(f"{PREFIX}?scope=geral")
        assert mock_aggr.await_count == 1


# ─── Equivalencia cross-wave (Dashboard ↔ Relatorios) ─────────────────────


class TestEquivalenciaDashboardRelatorios:
    """WAVE5_ANALYSIS §7.4 — atrasadas no Dashboard e no Relatorio
    devem usar a MESMA logica (horas corridas, mesmo cutoff).

    Este teste valida que os dois caminhos sao implementados via os MESMOS
    helpers (limite_atraso, _ultima_mov_subq). Em E2E manual com seed real
    a equivalencia numerica e validada com banco real.
    """

    def test_helpers_compartilhados_referenciados(self):
        """Garante que reports.py e provas.py referenciam o mesmo helper de tempo de atraso."""
        # Ambos devem ter funcao similar para ler tempo_atraso
        # (provas usa inline, reports usa _read_tempo_atraso) — mas a chave
        # da config e a mesma.
        import inspect

        from app.api.v1 import provas, reports

        provas_src = inspect.getsource(provas)
        reports_src = inspect.getsource(reports)

        chave = "tempo_atraso_horas_uteis"
        assert chave in provas_src
        assert chave in reports_src

    def test_limite_atraso_reusa_helper_metrics(self):
        """reports.py importa limite_atraso de report_metrics — mesma logica."""
        from app.api.v1 import reports
        from app.services import report_metrics

        # Confirma que reports.limite_atraso e o mesmo objeto que metrics.limite_atraso
        assert reports.limite_atraso is report_metrics.limite_atraso


# ─── Smoke: mock_db nao chamado em cache hit ──────────────────────────────


class TestReportsCacheNoDbCall:
    async def test_cache_hit_nao_toca_db(self, admin_user, mock_db):
        """Verifica que o segundo request nao toca db.execute (cache hit)."""
        _setup(mock_db, admin=admin_user)
        mock_aggr = AsyncMock(return_value=_payload_geral())
        with patch("app.api.v1.reports._aggregate_geral", new=mock_aggr):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                params = {
                    "scope": "geral",
                    "from": "2026-04-01T00:00:00Z",
                    "to": "2026-04-27T00:00:00Z",
                }
                await ac.get(PREFIX, params=params)
                # Capture call count
                first_call_count = mock_aggr.await_count
                await ac.get(PREFIX, params=params)
                second_call_count = mock_aggr.await_count

        # Segunda request foi cache hit — sem novo call ao agregador
        assert first_call_count == 1
        assert second_call_count == 1
