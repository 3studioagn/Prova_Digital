"""Integration tests para GET /api/v1/auditoria/* (Wave 6, Componente 18).

Testes de camada HTTP com `AsyncClient + ASGITransport + app`. Mockam o
service layer (`listar_audit_logs` / `buscar_audit_log_por_id`) para
isolar as responsabilidades do handler:

  - Autenticacao (401 sem token, 403 nao-admin)
  - Validacao Pydantic (422 varias combinacoes)
  - Shape da resposta
  - Imutabilidade (405 para POST/PUT/PATCH/DELETE)
  - Error handling (500 para dado inconsistente, 502 para falha transiente)

A logica SQL e testada separadamente em `test_auditoria_query.py`.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.api.deps import get_admin_user, get_current_user
from app.db.session import get_db
from app.domain.schemas.auditoria import (
    LIMIT_DEFAULT,
    AuditLogItem,
    AuditoriaListResponse,
    FiltrosAplicados,
    ProvaAuditoria,
    TipoEventoEnum,
    UsuarioAuditoria,
)
from app.main import app
from app.services.auditoria_query import (
    AuditLogSemUsuarioError,
    CursorInvalidoError,
)

BASE = "http://test"
PREFIX = "/api/v1/auditoria"


# =============================================================================
# Helpers
# =============================================================================


def _setup(mock_db, *, admin=None, user=None):
    """Configura dependency overrides — segue o padrao de test_provas_api.py."""

    async def _get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db
    if admin is not None:
        app.dependency_overrides[get_admin_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin
    elif user is not None:
        app.dependency_overrides[get_current_user] = lambda: user


def _fake_item(
    *,
    acao: str = "criar_prova",
    tipo_evento: TipoEventoEnum = TipoEventoEnum.CRIACAO_PROVA,
    label: str = "Criacao de prova",
    com_prova: bool = True,
    log_id: uuid.UUID | None = None,
    created_at: datetime | None = None,
) -> AuditLogItem:
    return AuditLogItem(
        id=log_id or uuid.uuid4(),
        acao=acao,
        tipo_evento=tipo_evento,
        tipo_evento_label=label,
        usuario=UsuarioAuditoria(
            id=uuid.uuid4(),
            nome="Admin",
            setor="STUDIO",
            is_admin=True,
        ),
        prova=(
            ProvaAuditoria(
                id=uuid.uuid4(),
                nro_requerimento="REQ-001",
                nome="Rotulo Teste",
            )
            if com_prova
            else None
        ),
        detalhes_json={"cliente": "Claudio", "nro_requerimento": "REQ-001"},
        ip_address="203.0.113.42",
        user_agent="Mozilla/5.0",
        created_at=created_at or datetime(2026, 4, 14, 19, 55, tzinfo=timezone.utc),
    )


def _fake_response(
    *,
    items: list[AuditLogItem] | None = None,
    has_more: bool = False,
    total: int = 0,
    next_cursor: str | None = None,
) -> AuditoriaListResponse:
    return AuditoriaListResponse(
        items=items or [],
        next_cursor=next_cursor,
        has_more=has_more,
        total_estimado=total,
        filtros_aplicados=FiltrosAplicados(
            data_inicio=None,
            data_fim=None,
            usuario_id=None,
            nro_requerimento=None,
            acao=None,
            tipo_evento=None,
            limit=LIMIT_DEFAULT,
        ),
    )


# =============================================================================
# 1. Autenticacao (401 / 403)
# =============================================================================


async def test_listar_401_sem_token(mock_db):
    """Sem override de `get_current_user` e sem `Authorization` header -> 401."""

    async def _get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/")
    assert resp.status_code == 401


async def test_listar_403_vendedor(regular_user, mock_db):
    """Vendedor autenticado mas com `is_admin=false` -> 403."""
    _setup(mock_db, user=regular_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/")
    assert resp.status_code == 403
    assert "admin" in resp.json()["detail"].lower()


async def test_listar_403_vendedor_matriz(vendedor_matriz, mock_db):
    _setup(mock_db, user=vendedor_matriz)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/")
    assert resp.status_code == 403


async def test_detail_401_sem_token(mock_db):
    async def _get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{uuid.uuid4()}")
    assert resp.status_code == 401


async def test_detail_403_vendedor(regular_user, mock_db):
    _setup(mock_db, user=regular_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{uuid.uuid4()}")
    assert resp.status_code == 403


# =============================================================================
# 2. Happy path (200)
# =============================================================================


async def test_listar_200_admin_lista_vazia(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    with patch(
        "app.api.v1.auditoria.listar_audit_logs",
        new=AsyncMock(return_value=_fake_response()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get(f"{PREFIX}/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["has_more"] is False
    assert data["total_estimado"] == 0
    assert data["next_cursor"] is None


async def test_listar_200_admin_com_dados(admin_user, mock_db):
    items = [
        _fake_item(acao="criar_prova", tipo_evento=TipoEventoEnum.CRIACAO_PROVA),
        _fake_item(
            acao="escanear_prova",
            tipo_evento=TipoEventoEnum.ESCANEAMENTO,
            label="Escaneamento",
        ),
    ]
    _setup(mock_db, admin=admin_user)
    with patch(
        "app.api.v1.auditoria.listar_audit_logs",
        new=AsyncMock(return_value=_fake_response(items=items, total=2)),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get(f"{PREFIX}/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["items"][0]["tipo_evento"] == "CRIACAO_PROVA"
    assert data["items"][1]["tipo_evento"] == "ESCANEAMENTO"
    assert data["total_estimado"] == 2


async def test_listar_200_com_has_more_e_cursor(admin_user, mock_db):
    items = [_fake_item() for _ in range(2)]
    _setup(mock_db, admin=admin_user)
    with patch(
        "app.api.v1.auditoria.listar_audit_logs",
        new=AsyncMock(
            return_value=_fake_response(
                items=items, has_more=True, total=100, next_cursor="eyJjIjogIngifQ=="
            )
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get(f"{PREFIX}/", params={"limit": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_more"] is True
    assert data["next_cursor"] == "eyJjIjogIngifQ=="
    assert data["total_estimado"] == 100


async def test_listar_200_cancelamento_aparece_como_tal(admin_user, mock_db):
    item = _fake_item(
        acao="transitar_status",
        tipo_evento=TipoEventoEnum.CANCELAMENTO,
        label="Cancelamento",
    )
    _setup(mock_db, admin=admin_user)
    with patch(
        "app.api.v1.auditoria.listar_audit_logs",
        new=AsyncMock(return_value=_fake_response(items=[item], total=1)),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get(f"{PREFIX}/")
    data = resp.json()
    assert data["items"][0]["tipo_evento"] == "CANCELAMENTO"
    assert data["items"][0]["tipo_evento_label"] == "Cancelamento"


# =============================================================================
# 3. Validacao 422
# =============================================================================


async def test_listar_422_acao_invalida(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/", params={"acao": "acao_inexistente"})
    assert resp.status_code == 422
    assert "acao_inexistente" in str(resp.json())


async def test_listar_422_acao_e_tipo_evento_simultaneos(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(
            f"{PREFIX}/",
            params={"acao": "criar_prova", "tipo_evento": "CANCELAMENTO"},
        )
    assert resp.status_code == 422
    assert "mutuamente exclusivos" in str(resp.json())


async def test_listar_422_data_invertida(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(
            f"{PREFIX}/",
            params={"data_inicio": "2026-04-15", "data_fim": "2026-04-10"},
        )
    assert resp.status_code == 422
    assert "data_inicio" in str(resp.json()).lower()


async def test_listar_422_limit_zero(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/", params={"limit": 0})
    assert resp.status_code == 422


async def test_listar_422_limit_acima_do_max(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/", params={"limit": 101})
    assert resp.status_code == 422


async def test_listar_422_nro_requerimento_longo(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(
            f"{PREFIX}/", params={"nro_requerimento": "A" * 51}
        )
    assert resp.status_code == 422


async def test_listar_422_data_invalida(admin_user, mock_db):
    """Data malformada pelo FastAPI (antes dos validators Pydantic)."""
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/", params={"data_inicio": "nao-eh-data"})
    assert resp.status_code == 422


async def test_listar_422_usuario_id_nao_uuid(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/", params={"usuario_id": "nao-eh-uuid"})
    assert resp.status_code == 422


async def test_listar_422_cursor_corrompido(admin_user, mock_db):
    """Cursor malformado levanta `CursorInvalidoError` no service e e
    traduzido em 422 pelo handler."""
    _setup(mock_db, admin=admin_user)
    with patch(
        "app.api.v1.auditoria.listar_audit_logs",
        new=AsyncMock(side_effect=CursorInvalidoError("cursor corrompido")),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get(f"{PREFIX}/", params={"cursor": "xxx"})
    assert resp.status_code == 422
    assert "cursor" in str(resp.json()).lower()


async def test_listar_422_tipo_evento_invalido(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(
            f"{PREFIX}/", params={"tipo_evento": "TIPO_INEXISTENTE"}
        )
    assert resp.status_code == 422


# =============================================================================
# 4. Filtros -> passagem correta ao service
# =============================================================================


async def test_listar_passa_filtros_periodo_ao_service(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    captured = {}

    async def _fake_listar(db, filtros):
        captured["filtros"] = filtros
        return _fake_response()

    with patch("app.api.v1.auditoria.listar_audit_logs", new=_fake_listar):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get(
                f"{PREFIX}/",
                params={
                    "data_inicio": "2026-04-01",
                    "data_fim": "2026-04-14",
                    "limit": 25,
                },
            )
    assert resp.status_code == 200
    filtros = captured["filtros"]
    assert filtros.data_inicio.isoformat() == "2026-04-01"
    assert filtros.data_fim.isoformat() == "2026-04-14"
    assert filtros.limit == 25


async def test_listar_passa_filtros_acao_multi_ao_service(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    captured = {}

    async def _fake_listar(db, filtros):
        captured["filtros"] = filtros
        return _fake_response()

    with patch("app.api.v1.auditoria.listar_audit_logs", new=_fake_listar):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get(
                f"{PREFIX}/",
                params=[("acao", "criar_prova"), ("acao", "escanear_prova")],
            )
    assert resp.status_code == 200
    assert captured["filtros"].acao == ["criar_prova", "escanear_prova"]


async def test_listar_passa_filtros_tipo_evento_ao_service(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    captured = {}

    async def _fake_listar(db, filtros):
        captured["filtros"] = filtros
        return _fake_response()

    with patch("app.api.v1.auditoria.listar_audit_logs", new=_fake_listar):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get(
                f"{PREFIX}/",
                params=[
                    ("tipo_evento", "CANCELAMENTO"),
                    ("tipo_evento", "REPROVACAO"),
                ],
            )
    assert resp.status_code == 200
    assert captured["filtros"].tipo_evento == [
        TipoEventoEnum.CANCELAMENTO,
        TipoEventoEnum.REPROVACAO,
    ]


async def test_listar_passa_usuario_id_ao_service(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    captured = {}
    uid = uuid.uuid4()

    async def _fake_listar(db, filtros):
        captured["filtros"] = filtros
        return _fake_response()

    with patch("app.api.v1.auditoria.listar_audit_logs", new=_fake_listar):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get(f"{PREFIX}/", params={"usuario_id": str(uid)})
    assert resp.status_code == 200
    assert captured["filtros"].usuario_id == uid


async def test_listar_passa_nro_requerimento_ao_service(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    captured = {}

    async def _fake_listar(db, filtros):
        captured["filtros"] = filtros
        return _fake_response()

    with patch("app.api.v1.auditoria.listar_audit_logs", new=_fake_listar):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get(
                f"{PREFIX}/", params={"nro_requerimento": "REQ-001"}
            )
    assert resp.status_code == 200
    assert captured["filtros"].nro_requerimento == "REQ-001"


# =============================================================================
# 5. GET /{id}
# =============================================================================


async def test_detail_200_admin(admin_user, mock_db):
    item = _fake_item()
    _setup(mock_db, admin=admin_user)
    with patch(
        "app.api.v1.auditoria.buscar_audit_log_por_id",
        new=AsyncMock(return_value=item),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get(f"{PREFIX}/{item.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(item.id)
    assert data["tipo_evento"] == "CRIACAO_PROVA"


async def test_detail_200_com_prova_none(admin_user, mock_db):
    """Detalhe de `atualizar_configuracao` vem com `prova=None`."""
    item = _fake_item(
        acao="atualizar_configuracao",
        tipo_evento=TipoEventoEnum.ALTERACAO_CONFIG,
        label="Alteracao de configuracao",
        com_prova=False,
    )
    _setup(mock_db, admin=admin_user)
    with patch(
        "app.api.v1.auditoria.buscar_audit_log_por_id",
        new=AsyncMock(return_value=item),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get(f"{PREFIX}/{item.id}")
    assert resp.status_code == 200
    assert resp.json()["prova"] is None


async def test_detail_404_nao_existe(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    with patch(
        "app.api.v1.auditoria.buscar_audit_log_por_id",
        new=AsyncMock(return_value=None),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get(f"{PREFIX}/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert "nao encontrado" in resp.json()["detail"].lower()


async def test_detail_422_log_id_nao_uuid(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/nao-eh-uuid")
    assert resp.status_code == 422


# =============================================================================
# 6. Imutabilidade — nenhuma rota de escrita
# =============================================================================


async def test_imutabilidade_post_list_405(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/", json={})
    assert resp.status_code == 405


async def test_imutabilidade_put_detail_405(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.put(f"{PREFIX}/{uuid.uuid4()}", json={})
    assert resp.status_code == 405


async def test_imutabilidade_patch_detail_405(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(f"{PREFIX}/{uuid.uuid4()}", json={})
    assert resp.status_code == 405


async def test_imutabilidade_delete_detail_405(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.delete(f"{PREFIX}/{uuid.uuid4()}")
    assert resp.status_code == 405


# =============================================================================
# 7. Error handling (500 / 502)
# =============================================================================


async def test_listar_500_quando_usuario_orfao(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    with patch(
        "app.api.v1.auditoria.listar_audit_logs",
        new=AsyncMock(
            side_effect=AuditLogSemUsuarioError("usuario_id orfao")
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get(f"{PREFIX}/")
    assert resp.status_code == 500
    assert "inconsistente" in resp.json()["detail"].lower()


async def test_listar_502_quando_db_falha(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    with patch(
        "app.api.v1.auditoria.listar_audit_logs",
        new=AsyncMock(side_effect=RuntimeError("db down")),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get(f"{PREFIX}/")
    assert resp.status_code == 502


async def test_detail_500_quando_usuario_orfao(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    with patch(
        "app.api.v1.auditoria.buscar_audit_log_por_id",
        new=AsyncMock(side_effect=AuditLogSemUsuarioError("orfao")),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get(f"{PREFIX}/{uuid.uuid4()}")
    assert resp.status_code == 500


async def test_detail_502_quando_db_falha(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    with patch(
        "app.api.v1.auditoria.buscar_audit_log_por_id",
        new=AsyncMock(side_effect=RuntimeError("db down")),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get(f"{PREFIX}/{uuid.uuid4()}")
    assert resp.status_code == 502


# =============================================================================
# 8. Cobertura adicional (branches defensivos)
# =============================================================================


async def test_listar_reraise_http_exception_do_service(admin_user, mock_db):
    """Se o service levantar `HTTPException` (nao deveria acontecer em
    producao, mas e defensivo), o handler deixa propagar via `except
    HTTPException: raise`. Cobre a linha defensiva."""
    from fastapi import HTTPException

    _setup(mock_db, admin=admin_user)
    http_exc = HTTPException(status_code=418, detail="sou uma chaleira")
    with patch(
        "app.api.v1.auditoria.listar_audit_logs",
        new=AsyncMock(side_effect=http_exc),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get(f"{PREFIX}/")
    assert resp.status_code == 418
    assert resp.json()["detail"] == "sou uma chaleira"


async def test_detail_reraise_http_exception_do_service(admin_user, mock_db):
    """Idem para o endpoint de detalhe — cobre o re-raise defensivo."""
    from fastapi import HTTPException

    _setup(mock_db, admin=admin_user)
    http_exc = HTTPException(status_code=418, detail="sou uma chaleira")
    with patch(
        "app.api.v1.auditoria.buscar_audit_log_por_id",
        new=AsyncMock(side_effect=http_exc),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get(f"{PREFIX}/{uuid.uuid4()}")
    assert resp.status_code == 418


def test_format_validation_error_sem_erros():
    """Fallback de `_format_validation_error` quando `exc.errors()==[]`.

    Em producao, um ValidationError sempre tem pelo menos 1 erro — mas o
    helper tem um fallback defensivo. Testamos ele diretamente com Mock.
    """
    from pydantic import ValidationError

    from app.api.v1.auditoria import _format_validation_error

    fake_exc = AsyncMock(spec=ValidationError)
    fake_exc.errors = lambda: []
    assert _format_validation_error(fake_exc) == "parametros invalidos"


def test_format_validation_error_sem_msg_usa_fallback():
    """Quando o dict de erro nao tem `msg`, usa 'parametros invalidos'."""
    from pydantic import ValidationError

    from app.api.v1.auditoria import _format_validation_error

    fake_exc = AsyncMock(spec=ValidationError)
    fake_exc.errors = lambda: [{"type": "something"}]  # sem chave msg
    assert _format_validation_error(fake_exc) == "parametros invalidos"


def test_format_validation_error_sem_prefixo_value_error():
    """Mensagens que NAO comecam com 'Value error, ' sao retornadas as-is."""
    from pydantic import ValidationError

    from app.api.v1.auditoria import _format_validation_error

    fake_exc = AsyncMock(spec=ValidationError)
    fake_exc.errors = lambda: [{"msg": "mensagem direta sem prefixo"}]
    assert _format_validation_error(fake_exc) == "mensagem direta sem prefixo"
