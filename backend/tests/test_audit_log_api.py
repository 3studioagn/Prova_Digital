"""Testes integrados para /api/v1/audit-log (Wave 6, Componente 18).

Padrao: dependency_overrides para get_db + get_admin_user/get_current_user;
mock do service via patch para isolar a camada API. Testes do service real
(queries SQL, JOINs) ficam em manual smoke / E2E em staging.

Cobertura:
  - RBAC: admin OK, vendedor/motorista/clicheria 403, anonimo 401
  - Validacao Pydantic: page<1, page_size>200, sort invalido, datas
    invertidas, range > 366d, q com control chars, q com >200 chars,
    UUID mal formado em path => 404
  - Endpoints: list, detail (com/sem movimentacao_relacionada),
    by-prova (com prova existente, com 404 em prova inexistente)
  - Imutabilidade: POST/PUT/PATCH/DELETE => 405 Method Not Allowed
  - Header anti-cache: Cache-Control: no-store em todas as respostas
"""
from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_admin_user, get_current_user
from app.db.models import RotaEnum, SetorEnum, StatusProvaEnum, LocalizacaoEnum
from app.db.session import get_db
from app.domain.schemas.audit_log import (
    AuditLogDetailResponse,
    AuditLogItemResponse,
    AuditLogListResponse,
    MovimentacaoSnapshot,
)
from app.main import app
from tests.conftest import make_user

UTC = timezone.utc
BASE = "http://test"
PREFIX = "/api/v1/audit-log"


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


def _make_item(**overrides) -> AuditLogItemResponse:
    """Helper que monta um AuditLogItemResponse com defaults razoaveis."""
    base = {
        "id": _uuid.uuid4(),
        "acao": "criar_prova",
        "prova_id": _uuid.uuid4(),
        "prova_nro_requerimento": "REQ-001",
        "usuario_id": _uuid.uuid4(),
        "usuario_nome": "Admin Teste",
        "usuario_setor": SetorEnum.STUDIO,
        "detalhes_json": {"cliente": "Test Co", "vendedor_nome": "Vendedor X"},
        "ip_address": "127.0.0.1",
        "user_agent": "Mozilla/5.0",
        "created_at": datetime.now(UTC),
    }
    base.update(overrides)
    return AuditLogItemResponse(**base)


def _make_list_response(n: int = 3, total: int | None = None) -> AuditLogListResponse:
    return AuditLogListResponse(
        items=[_make_item() for _ in range(n)],
        total=total if total is not None else n,
        page=1,
        page_size=50,
    )


# ─── RBAC ──────────────────────────────────────────────────────────────────


class TestAuditLogRBAC:
    async def test_admin_autorizado(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.audit_log.listar_audit_logs",
            new=AsyncMock(return_value=_make_list_response()),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(PREFIX)
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body

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
            resp = await ac.get(PREFIX)
        assert resp.status_code == 403

    async def test_motorista_403(self, mock_db):
        motorista = make_user(setor=SetorEnum.MOTORISTA, is_admin=False)
        _setup(mock_db, user=motorista)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(PREFIX)
        assert resp.status_code == 403

    async def test_clicheria_403(self, mock_db):
        clicheria = make_user(setor=SetorEnum.CLICHERIA, is_admin=False)
        _setup(mock_db, user=clicheria)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(PREFIX)
        assert resp.status_code == 403

    async def test_studio_sem_admin_403(self, mock_db):
        """STUDIO sem is_admin=true tambem e bloqueado — defesa em
        profundidade, igual ao /reports da Wave 5."""
        studio = make_user(setor=SetorEnum.STUDIO, is_admin=False)
        _setup(mock_db, user=studio)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(PREFIX)
        assert resp.status_code == 403

    async def test_sem_token_401(self, mock_db):
        async def _get_db():
            yield mock_db

        app.dependency_overrides[get_db] = _get_db
        # NAO override de get_current_user — quer usar o real (sem token => 401)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(PREFIX)
        assert resp.status_code == 401

    async def test_detail_vendedor_403(self, mock_db):
        vendedor = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
        _setup(mock_db, user=vendedor)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(f"{PREFIX}/{_uuid.uuid4()}")
        assert resp.status_code == 403

    async def test_by_prova_vendedor_403(self, mock_db):
        vendedor = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
        _setup(mock_db, user=vendedor)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(f"{PREFIX}/by-prova/{_uuid.uuid4()}")
        assert resp.status_code == 403


# ─── Validacao ─────────────────────────────────────────────────────────────


class TestAuditLogValidacao:
    async def test_page_zero_422(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(f"{PREFIX}?page=0")
        assert resp.status_code == 422

    async def test_page_size_acima_max_422(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(f"{PREFIX}?page_size=201")
        assert resp.status_code == 422

    async def test_sort_invalido_422(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(f"{PREFIX}?sort=lateral")
        assert resp.status_code == 422

    async def test_datas_invertidas_422(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(
                f"{PREFIX}?from=2026-04-29T00:00:00Z&to=2026-04-01T00:00:00Z"
            )
        assert resp.status_code == 422

    async def test_intervalo_acima_366_dias_422(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(
                f"{PREFIX}?from=2024-01-01T00:00:00Z&to=2026-01-01T00:00:00Z"
            )
        assert resp.status_code == 422

    async def test_q_acima_200_chars_422(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        big_q = "x" * 201
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(f"{PREFIX}?q={big_q}")
        assert resp.status_code == 422

    async def test_acao_acima_100_chars_422(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        big_acao = "x" * 101
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(f"{PREFIX}?acao={big_acao}")
        assert resp.status_code == 422

    async def test_uuid_invalido_em_detail_404(self, admin_user, mock_db):
        """Path com string nao-UUID retorna 404 (parse_audit_id), nao 422."""
        _setup(mock_db, admin=admin_user)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(f"{PREFIX}/abc-nao-uuid")
        assert resp.status_code == 404

    async def test_uuid_invalido_em_by_prova_404(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(f"{PREFIX}/by-prova/nao-uuid")
        assert resp.status_code == 404


# ─── Endpoints: listagem ──────────────────────────────────────────────────


class TestAuditLogList:
    async def test_listagem_default_devolve_items_e_total(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.audit_log.listar_audit_logs",
            new=AsyncMock(return_value=_make_list_response(n=3, total=3)),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(PREFIX)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 3
        assert body["total"] == 3
        assert body["page"] == 1
        assert body["page_size"] == 50

    async def test_listagem_passa_filtros_para_service(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        captured = {}

        async def fake_listar(db, query):
            captured["query"] = query
            return _make_list_response(n=0, total=0)

        with patch(
            "app.api.v1.audit_log.listar_audit_logs",
            new=AsyncMock(side_effect=fake_listar),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(
                    f"{PREFIX}?page=2&page_size=10&sort=asc"
                    f"&acao=transitar_status&q=cor%20errada"
                )
        assert resp.status_code == 200
        q = captured["query"]
        assert q.page == 2
        assert q.page_size == 10
        assert q.sort == "asc"
        assert q.acao == "transitar_status"
        assert q.q == "cor errada"

    async def test_listagem_no_store_header(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.audit_log.listar_audit_logs",
            new=AsyncMock(return_value=_make_list_response()),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(PREFIX)
        assert resp.headers.get("cache-control") == "no-store"
        assert resp.headers.get("pragma") == "no-cache"

    async def test_listagem_assinatura_digital_nao_retorna_no_payload(
        self, admin_user, mock_db
    ):
        """Garantia de privacidade: BYTEA nunca aparece no JSON."""
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.audit_log.listar_audit_logs",
            new=AsyncMock(return_value=_make_list_response()),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(PREFIX)
        body = resp.text
        assert "assinatura_digital" not in body


# ─── Endpoints: detalhe ───────────────────────────────────────────────────


class TestAuditLogDetail:
    async def test_detail_existente_devolve_200(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        item = _make_item()
        detail = AuditLogDetailResponse(
            **item.model_dump(),
            movimentacao_relacionada=None,
        )
        with patch(
            "app.api.v1.audit_log.buscar_audit_log_detalhe",
            new=AsyncMock(return_value=detail),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(f"{PREFIX}/{item.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(item.id)
        assert body["movimentacao_relacionada"] is None

    async def test_detail_inexistente_404(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.audit_log.buscar_audit_log_detalhe",
            new=AsyncMock(return_value=None),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(f"{PREFIX}/{_uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_detail_com_movimentacao_relacionada(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        item = _make_item(
            acao="transitar_status",
            detalhes_json={"de": "CRIADA", "para": "RETIRADA_PELO_VENDEDOR", "ciclo": 1},
        )
        mov_snap = MovimentacaoSnapshot(
            id=_uuid.uuid4(),
            status_anterior=StatusProvaEnum.CRIADA,
            status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
            motivo_reprovacao=None,
            ciclo=1,
            rota_no_momento=None,
            assinatura_digital_presente=True,
            created_at=datetime.now(UTC),
        )
        detail = AuditLogDetailResponse(
            **item.model_dump(),
            movimentacao_relacionada=mov_snap,
        )
        with patch(
            "app.api.v1.audit_log.buscar_audit_log_detalhe",
            new=AsyncMock(return_value=detail),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(f"{PREFIX}/{item.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["movimentacao_relacionada"] is not None
        # BYTEA nao expoe — apenas o boolean
        assert body["movimentacao_relacionada"]["assinatura_digital_presente"] is True
        assert "assinatura_digital" not in body["movimentacao_relacionada"]


# ─── Endpoints: by-prova ──────────────────────────────────────────────────


class TestAuditLogByProva:
    async def test_by_prova_existente_200(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        prova_id = _uuid.uuid4()
        with patch(
            "app.api.v1.audit_log.prova_existe",
            new=AsyncMock(return_value=True),
        ), patch(
            "app.api.v1.audit_log.listar_audit_logs_por_prova",
            new=AsyncMock(return_value=_make_list_response(n=5, total=5)),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(f"{PREFIX}/by-prova/{prova_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 5

    async def test_by_prova_inexistente_404(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        with patch(
            "app.api.v1.audit_log.prova_existe",
            new=AsyncMock(return_value=False),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(f"{PREFIX}/by-prova/{_uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_by_prova_default_sort_asc(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        captured = {}

        async def fake_listar(db, prova_id, sort):
            captured["sort"] = sort
            return _make_list_response(n=2, total=2)

        with patch(
            "app.api.v1.audit_log.prova_existe",
            new=AsyncMock(return_value=True),
        ), patch(
            "app.api.v1.audit_log.listar_audit_logs_por_prova",
            new=AsyncMock(side_effect=fake_listar),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(f"{PREFIX}/by-prova/{_uuid.uuid4()}")
        assert resp.status_code == 200
        assert captured["sort"] == "asc"


# ─── Imutabilidade: verbos de mutacao ─────────────────────────────────────


class TestAuditLogImutabilidade:
    """Garantia explicita de que NENHUM verbo de mutacao e aceito.

    Mesmo como admin. RNF-005 — log de auditoria so se le, nunca se altera.
    """

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    async def test_verbo_mutacao_na_listagem_405(
        self, admin_user, mock_db, method
    ):
        _setup(mock_db, admin=admin_user)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            # httpx.AsyncClient.delete() nao aceita kwarg `json` — body
            # nao faz sentido em DELETE. Usa request() generico para
            # uniformizar os 4 verbos.
            resp = await ac.request(method.upper(), PREFIX)
        assert resp.status_code == 405

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    async def test_verbo_mutacao_no_detalhe_405(
        self, admin_user, mock_db, method
    ):
        _setup(mock_db, admin=admin_user)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.request(method.upper(), f"{PREFIX}/{_uuid.uuid4()}")
        assert resp.status_code == 405

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    async def test_verbo_mutacao_no_by_prova_405(
        self, admin_user, mock_db, method
    ):
        _setup(mock_db, admin=admin_user)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.request(
                method.upper(), f"{PREFIX}/by-prova/{_uuid.uuid4()}"
            )
        assert resp.status_code == 405


# ─── Schema Pydantic — validacoes diretas (sem HTTP) ──────────────────────


class TestAuditLogQuerySchema:
    """Testa AuditLogListQuery diretamente — Pydantic v2 invariantes."""

    def test_defaults(self):
        from app.domain.schemas.audit_log import AuditLogListQuery

        q = AuditLogListQuery.model_validate({})
        assert q.page == 1
        assert q.page_size == 50
        assert q.sort == "desc"
        assert q.from_dt is None
        assert q.to_dt is None
        assert q.q is None

    def test_normaliza_naive_datetime_para_utc(self):
        from app.domain.schemas.audit_log import AuditLogListQuery

        naive = datetime(2026, 4, 1, 12, 0, 0)  # sem tzinfo
        q = AuditLogListQuery.model_validate({"from": naive})
        assert q.from_dt is not None
        assert q.from_dt.tzinfo is not None

    def test_q_strip_e_trata_vazio_como_none(self):
        from app.domain.schemas.audit_log import AuditLogListQuery

        q = AuditLogListQuery.model_validate({"q": "  "})
        assert q.q is None

        q2 = AuditLogListQuery.model_validate({"q": "  busca  "})
        assert q2.q == "busca"

    def test_q_rejeita_caracter_de_controle(self):
        from app.domain.schemas.audit_log import AuditLogListQuery
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AuditLogListQuery.model_validate({"q": "linha1\x00linha2"})

    def test_intervalo_invertido_422(self):
        from app.domain.schemas.audit_log import AuditLogListQuery
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AuditLogListQuery.model_validate(
                {
                    "from": datetime(2026, 4, 29, tzinfo=UTC),
                    "to": datetime(2026, 4, 1, tzinfo=UTC),
                }
            )

    def test_intervalo_grande_demais(self):
        from app.domain.schemas.audit_log import AuditLogListQuery
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AuditLogListQuery.model_validate(
                {
                    "from": datetime(2024, 1, 1, tzinfo=UTC),
                    "to": datetime(2026, 1, 1, tzinfo=UTC),
                }
            )

    def test_intervalo_366_dias_exatos_aceito(self):
        from app.domain.schemas.audit_log import AuditLogListQuery

        from_dt = datetime(2026, 1, 1, tzinfo=UTC)
        to_dt = from_dt + timedelta(days=366)
        q = AuditLogListQuery.model_validate({"from": from_dt, "to": to_dt})
        assert q.from_dt == from_dt
        assert q.to_dt == to_dt

    def test_page_size_max_200(self):
        from app.domain.schemas.audit_log import AuditLogListQuery
        from pydantic import ValidationError

        q = AuditLogListQuery.model_validate({"page_size": 200})
        assert q.page_size == 200
        with pytest.raises(ValidationError):
            AuditLogListQuery.model_validate({"page_size": 201})

    def test_sort_aceita_apenas_asc_desc(self):
        from app.domain.schemas.audit_log import AuditLogListQuery
        from pydantic import ValidationError

        for valor in ["asc", "desc"]:
            q = AuditLogListQuery.model_validate({"sort": valor})
            assert q.sort == valor
        with pytest.raises(ValidationError):
            AuditLogListQuery.model_validate({"sort": "ASC"})  # case-sensitive
        with pytest.raises(ValidationError):
            AuditLogListQuery.model_validate({"sort": "ascending"})


# ─── Service — testes diretos com mock de db.execute ──────────────────────


def _make_row(**overrides):
    """Mocka uma row do SQLAlchemy: namespace com atributos."""
    from types import SimpleNamespace

    base = {
        "id": _uuid.uuid4(),
        "acao": "criar_prova",
        "prova_id": _uuid.uuid4(),
        "usuario_id": _uuid.uuid4(),
        "detalhes_json": {"foo": "bar"},
        "ip_address": "127.0.0.1",
        "user_agent": "UA",
        "created_at": datetime.now(UTC),
        "usuario_nome": "Admin",
        "usuario_setor": SetorEnum.STUDIO,
        "prova_nro_requerimento": "REQ-001",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _make_movimentacao_orm(**overrides):
    """Mocka uma instancia de Movimentacao (ORM)."""
    from app.db.models import Movimentacao

    base = {
        "id": _uuid.uuid4(),
        "prova_id": _uuid.uuid4(),
        "usuario_id": _uuid.uuid4(),
        "status_anterior": StatusProvaEnum.CRIADA,
        "status_novo": StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        "assinatura_digital": b"signed",
        "motivo_reprovacao": None,
        "ciclo": 1,
        "rota_no_momento": None,
        "created_at": datetime.now(UTC),
    }
    base.update(overrides)
    return Movimentacao(**base)


class TestServicoListagem:
    """Testa app.services.audit_log_service.listar_audit_logs."""

    async def test_pagina_1_offset_0_com_rows_vazias(self, mock_db):
        from app.domain.schemas.audit_log import AuditLogListQuery
        from app.services.audit_log_service import listar_audit_logs

        result_items = AsyncMock()
        result_items.all = lambda: []
        result_count = AsyncMock()
        result_count.scalar_one = lambda: 0
        mock_db.execute = AsyncMock(side_effect=[result_items, result_count])

        q = AuditLogListQuery.model_validate({"page": 1, "page_size": 50})
        resp = await listar_audit_logs(mock_db, q)
        assert resp.page == 1
        assert resp.page_size == 50
        assert resp.total == 0
        assert resp.items == []

    async def test_pagina_3_size_25_com_rows_vazias(self, mock_db):
        from app.domain.schemas.audit_log import AuditLogListQuery
        from app.services.audit_log_service import listar_audit_logs

        result_items = AsyncMock()
        result_items.all = lambda: []
        result_count = AsyncMock()
        result_count.scalar_one = lambda: 0
        mock_db.execute = AsyncMock(side_effect=[result_items, result_count])

        q = AuditLogListQuery.model_validate({"page": 3, "page_size": 25})
        resp = await listar_audit_logs(mock_db, q)
        assert resp.page == 3
        assert resp.page_size == 25

    async def test_serializa_rows_em_items(self, mock_db):
        """Cobre o list-comprehension de rows -> AuditLogItemResponse."""
        from app.domain.schemas.audit_log import AuditLogListQuery
        from app.services.audit_log_service import listar_audit_logs

        rows = [
            _make_row(acao="criar_prova"),
            _make_row(acao="transitar_status", ip_address=None),
            _make_row(acao="atualizar_configuracao", prova_id=None,
                      prova_nro_requerimento=None),
        ]
        result_items = AsyncMock()
        result_items.all = lambda: rows
        result_count = AsyncMock()
        result_count.scalar_one = lambda: 3
        mock_db.execute = AsyncMock(side_effect=[result_items, result_count])

        q = AuditLogListQuery.model_validate({})
        resp = await listar_audit_logs(mock_db, q)
        assert len(resp.items) == 3
        assert resp.total == 3
        # Item sem ip serializa como None
        assert resp.items[1].ip_address is None
        # Item sem prova_id mantem None
        assert resp.items[2].prova_id is None
        assert resp.items[2].prova_nro_requerimento is None

    async def test_aplica_filtro_q_no_stmt(self, mock_db):
        """O filtro q invoca cast(detalhes_json, Text).ilike — nao quebra."""
        from app.domain.schemas.audit_log import AuditLogListQuery
        from app.services.audit_log_service import listar_audit_logs

        result_items = AsyncMock()
        result_items.all = lambda: []
        result_count = AsyncMock()
        result_count.scalar_one = lambda: 0
        mock_db.execute = AsyncMock(side_effect=[result_items, result_count])

        q = AuditLogListQuery.model_validate({"q": "cor errada"})
        resp = await listar_audit_logs(mock_db, q)
        assert resp.total == 0
        # 2 chamadas a execute (items + count) — confirma que aplicou
        # ambas com filtro sem erro
        assert mock_db.execute.await_count == 2

    async def test_aplica_filtro_periodo_e_acao(self, mock_db):
        from app.domain.schemas.audit_log import AuditLogListQuery
        from app.services.audit_log_service import listar_audit_logs

        result_items = AsyncMock()
        result_items.all = lambda: []
        result_count = AsyncMock()
        result_count.scalar_one = lambda: 0
        mock_db.execute = AsyncMock(side_effect=[result_items, result_count])

        q = AuditLogListQuery.model_validate(
            {
                "from": "2026-04-01T00:00:00Z",
                "to": "2026-04-29T00:00:00Z",
                "acao": "transitar_status",
                "prova_id": str(_uuid.uuid4()),
                "usuario_id": str(_uuid.uuid4()),
                "sort": "asc",
            }
        )
        resp = await listar_audit_logs(mock_db, q)
        assert resp.total == 0


class TestServicoDetalhe:
    """Testa app.services.audit_log_service.buscar_audit_log_detalhe."""

    async def test_id_inexistente_retorna_none(self, mock_db):
        from app.services.audit_log_service import buscar_audit_log_detalhe

        result = AsyncMock()
        result.first = lambda: None
        mock_db.execute = AsyncMock(return_value=result)

        resp = await buscar_audit_log_detalhe(mock_db, _uuid.uuid4())
        assert resp is None

    async def test_acao_sem_movimentacao_relacionada(self, mock_db):
        """acao=criar_prova nao tenta enriquecer com movimentacao."""
        from app.services.audit_log_service import buscar_audit_log_detalhe

        row = _make_row(acao="criar_prova")
        result = AsyncMock()
        result.first = lambda: row
        mock_db.execute = AsyncMock(return_value=result)

        resp = await buscar_audit_log_detalhe(mock_db, row.id)
        assert resp is not None
        assert resp.acao == "criar_prova"
        assert resp.movimentacao_relacionada is None
        # Apenas 1 call — nao chamou _find_movimentacao_relacionada
        assert mock_db.execute.await_count == 1

    async def test_transitar_status_sem_para_em_detalhes_retorna_none(
        self, mock_db
    ):
        """Detalhes_json sem 'para' nao tenta matching."""
        from app.services.audit_log_service import buscar_audit_log_detalhe

        row = _make_row(
            acao="transitar_status", detalhes_json={"foo": "bar"}
        )
        result = AsyncMock()
        result.first = lambda: row
        mock_db.execute = AsyncMock(return_value=result)

        resp = await buscar_audit_log_detalhe(mock_db, row.id)
        assert resp is not None
        assert resp.movimentacao_relacionada is None

    async def test_transitar_status_com_match_de_movimentacao(self, mock_db):
        """Cobre _find_movimentacao_relacionada caminho feliz."""
        from app.services.audit_log_service import buscar_audit_log_detalhe

        prova_id = _uuid.uuid4()
        row = _make_row(
            acao="transitar_status",
            prova_id=prova_id,
            detalhes_json={
                "de": "CRIADA",
                "para": "RETIRADA_PELO_VENDEDOR",
                "ciclo": 1,
            },
        )
        mov = _make_movimentacao_orm(
            prova_id=prova_id,
            status_anterior=StatusProvaEnum.CRIADA,
            status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
            ciclo=1,
            assinatura_digital=b"presente",
            created_at=row.created_at,
        )

        result_audit = AsyncMock()
        result_audit.first = lambda: row
        result_mov = AsyncMock()
        result_mov.scalar_one_or_none = lambda: mov
        mock_db.execute = AsyncMock(side_effect=[result_audit, result_mov])

        resp = await buscar_audit_log_detalhe(mock_db, row.id)
        assert resp is not None
        assert resp.movimentacao_relacionada is not None
        assert resp.movimentacao_relacionada.assinatura_digital_presente is True
        assert resp.movimentacao_relacionada.ciclo == 1

    async def test_transitar_status_assinatura_vazia_retorna_false(
        self, mock_db
    ):
        """Movimentacao com BYTEA vazia => assinatura_digital_presente=False."""
        from app.services.audit_log_service import buscar_audit_log_detalhe

        prova_id = _uuid.uuid4()
        row = _make_row(
            acao="transitar_status",
            prova_id=prova_id,
            detalhes_json={"de": "CRIADA", "para": "CANCELADA", "ciclo": 1},
        )
        mov = _make_movimentacao_orm(
            prova_id=prova_id,
            status_novo=StatusProvaEnum.CANCELADA,
            ciclo=1,
            assinatura_digital=b"",  # vazia — borderline
            created_at=row.created_at,
        )

        result_audit = AsyncMock()
        result_audit.first = lambda: row
        result_mov = AsyncMock()
        result_mov.scalar_one_or_none = lambda: mov
        mock_db.execute = AsyncMock(side_effect=[result_audit, result_mov])

        resp = await buscar_audit_log_detalhe(mock_db, row.id)
        assert resp.movimentacao_relacionada is not None
        assert resp.movimentacao_relacionada.assinatura_digital_presente is False

    async def test_reiniciar_ciclo_tambem_tenta_enriquecer(self, mock_db):
        from app.services.audit_log_service import buscar_audit_log_detalhe

        prova_id = _uuid.uuid4()
        row = _make_row(
            acao="reiniciar_ciclo",
            prova_id=prova_id,
            detalhes_json={
                "de": "REPROVADA_PELO_VENDEDOR",
                "para": "CRIADA",
                "ciclo": 2,
            },
        )
        result_audit = AsyncMock()
        result_audit.first = lambda: row
        result_mov = AsyncMock()
        result_mov.scalar_one_or_none = lambda: None  # sem match
        mock_db.execute = AsyncMock(side_effect=[result_audit, result_mov])

        resp = await buscar_audit_log_detalhe(mock_db, row.id)
        assert resp is not None
        # Tentou matchear e nao achou — segue sem o enriquecimento
        assert resp.movimentacao_relacionada is None
        assert mock_db.execute.await_count == 2


# ─── UX A2 — Filtro semantico tipo_evento ─────────────────────────────────


class TestTipoEvento:
    """Cobre o mapeamento semantico de tipo_evento (Wave 6 UX A2)."""

    @pytest.mark.parametrize(
        "tipo,esperado",
        [
            ("reprovacao", "reprovacao"),
            ("reinicio", "reinicio"),
            ("cancelamento", "cancelamento"),
            ("criacao", "criacao"),
            ("admin", "admin"),
        ],
    )
    def test_schema_aceita_valores_validos(self, tipo, esperado):
        from app.domain.schemas.audit_log import AuditLogListQuery

        q = AuditLogListQuery.model_validate({"tipo_evento": tipo})
        assert q.tipo_evento == esperado

    def test_schema_normaliza_todos_para_none(self):
        from app.domain.schemas.audit_log import AuditLogListQuery

        q = AuditLogListQuery.model_validate({"tipo_evento": "todos"})
        assert q.tipo_evento is None

    def test_schema_normaliza_string_vazia_para_none(self):
        from app.domain.schemas.audit_log import AuditLogListQuery

        q = AuditLogListQuery.model_validate({"tipo_evento": ""})
        assert q.tipo_evento is None

    def test_schema_rejeita_valor_invalido(self):
        from app.domain.schemas.audit_log import AuditLogListQuery
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AuditLogListQuery.model_validate({"tipo_evento": "outras_coisas"})

    def test_schema_normaliza_case_insensitive(self):
        from app.domain.schemas.audit_log import AuditLogListQuery

        q = AuditLogListQuery.model_validate({"tipo_evento": "REPROVACAO"})
        assert q.tipo_evento == "reprovacao"

    async def test_endpoint_aceita_tipo_evento(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        captured = {}

        async def fake_listar(db, query):
            captured["query"] = query
            return _make_list_response(n=0, total=0)

        with patch(
            "app.api.v1.audit_log.listar_audit_logs",
            new=AsyncMock(side_effect=fake_listar),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(f"{PREFIX}?tipo_evento=reprovacao")
        assert resp.status_code == 200
        assert captured["query"].tipo_evento == "reprovacao"

    async def test_endpoint_rejeita_tipo_evento_invalido_422(
        self, admin_user, mock_db
    ):
        _setup(mock_db, admin=admin_user)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(f"{PREFIX}?tipo_evento=foo")
        assert resp.status_code == 422


# ─── UX B4 — Ordenacao clicavel ───────────────────────────────────────────


class TestOrderBy:
    """Cobre order_by dinamico com whitelist (Wave 6 UX B4)."""

    @pytest.mark.parametrize(
        "col", ["created_at", "acao", "usuario_nome"]
    )
    def test_schema_aceita_colunas_whitelisted(self, col):
        from app.domain.schemas.audit_log import AuditLogListQuery

        q = AuditLogListQuery.model_validate({"order_by": col})
        assert q.order_by == col

    def test_schema_default_created_at(self):
        from app.domain.schemas.audit_log import AuditLogListQuery

        q = AuditLogListQuery.model_validate({})
        assert q.order_by == "created_at"

    def test_schema_rejeita_coluna_arbitraria(self):
        """Defesa anti-SQL-injection — whitelist bloqueia entradas
        arbitrarias mesmo que parecessem nome de coluna valida."""
        from app.domain.schemas.audit_log import AuditLogListQuery
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AuditLogListQuery.model_validate({"order_by": "ip_address"})
        with pytest.raises(ValidationError):
            AuditLogListQuery.model_validate({"order_by": "id; DROP TABLE"})

    async def test_endpoint_aceita_order_by_acao(self, admin_user, mock_db):
        _setup(mock_db, admin=admin_user)
        captured = {}

        async def fake_listar(db, query):
            captured["query"] = query
            return _make_list_response(n=0, total=0)

        with patch(
            "app.api.v1.audit_log.listar_audit_logs",
            new=AsyncMock(side_effect=fake_listar),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=BASE
            ) as ac:
                resp = await ac.get(f"{PREFIX}?order_by=acao&sort=asc")
        assert resp.status_code == 200
        assert captured["query"].order_by == "acao"
        assert captured["query"].sort == "asc"

    async def test_endpoint_rejeita_order_by_invalido_422(
        self, admin_user, mock_db
    ):
        _setup(mock_db, admin=admin_user)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=BASE
        ) as ac:
            resp = await ac.get(f"{PREFIX}?order_by=algumacoisa")
        assert resp.status_code == 422

    def test_resolver_order_by_column(self):
        """Helper privado mapeia string -> coluna SQLAlchemy."""
        from app.db.models import AuditLog, Usuario
        from app.services.audit_log_service import _resolver_order_by_column

        assert _resolver_order_by_column("created_at") is AuditLog.created_at
        assert _resolver_order_by_column("acao") is AuditLog.acao
        assert _resolver_order_by_column("usuario_nome") is Usuario.nome
        # Defensive default
        assert _resolver_order_by_column("inexistente") is AuditLog.created_at


# ─── UX A4 — Busca q expandida para nro_requerimento ──────────────────────


class TestBuscaQExpandida:
    """Cobre a busca textual ampliada para nro_requerimento (Wave 6 UX A4)."""

    async def test_q_busca_em_detalhes_e_nro_requerimento(self, mock_db):
        """Verifica via inspecao de SQL que ambos os campos sao tocados."""
        from app.domain.schemas.audit_log import AuditLogListQuery
        from app.services.audit_log_service import listar_audit_logs

        result_items = AsyncMock()
        result_items.all = lambda: []
        result_count = AsyncMock()
        result_count.scalar_one = lambda: 0
        mock_db.execute = AsyncMock(side_effect=[result_items, result_count])

        q = AuditLogListQuery.model_validate({"q": "REQ-123"})
        await listar_audit_logs(mock_db, q)

        # Inspeciona os 2 statements compilados — ambos devem mencionar
        # detalhes_json E nro_requerimento por causa do OR.
        call_args = mock_db.execute.await_args_list
        assert len(call_args) == 2
        for call in call_args:
            stmt = call.args[0]
            sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
            assert "detalhes_json" in sql.lower() or "detalhes" in sql.lower()
            assert "nro_requerimento" in sql.lower()


class TestServicoByProva:
    """Testa app.services.audit_log_service.listar_audit_logs_por_prova."""

    async def test_lista_vazia(self, mock_db):
        from app.services.audit_log_service import listar_audit_logs_por_prova

        result = AsyncMock()
        result.all = lambda: []
        mock_db.execute = AsyncMock(return_value=result)

        resp = await listar_audit_logs_por_prova(mock_db, _uuid.uuid4())
        assert resp.total == 0
        assert resp.items == []
        assert resp.page == 1

    async def test_lista_serializa_rows(self, mock_db):
        from app.services.audit_log_service import listar_audit_logs_por_prova

        rows = [_make_row(), _make_row(), _make_row()]
        result = AsyncMock()
        result.all = lambda: rows
        mock_db.execute = AsyncMock(return_value=result)

        resp = await listar_audit_logs_por_prova(
            mock_db, _uuid.uuid4(), sort="desc"
        )
        assert resp.total == 3
        assert len(resp.items) == 3

    async def test_prova_existe_true(self, mock_db):
        from app.services.audit_log_service import prova_existe

        result = AsyncMock()
        result.scalar_one_or_none = lambda: _uuid.uuid4()
        mock_db.execute = AsyncMock(return_value=result)

        assert await prova_existe(mock_db, _uuid.uuid4()) is True

    async def test_prova_existe_false(self, mock_db):
        from app.services.audit_log_service import prova_existe

        result = AsyncMock()
        result.scalar_one_or_none = lambda: None
        mock_db.execute = AsyncMock(return_value=result)

        assert await prova_existe(mock_db, _uuid.uuid4()) is False
