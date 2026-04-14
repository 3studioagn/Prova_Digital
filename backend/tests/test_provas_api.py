"""Integration tests for /api/v1/provas endpoints (Componente 06+07+08)."""
import base64
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from botocore.exceptions import ClientError
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_admin_user, get_current_user
from app.db.models import (
    Etiqueta,
    LocalizacaoEnum,
    ProvaDigital,
    RotaEnum,  # noqa: F401 — usado indiretamente em fixtures futuras
    SetorEnum,
    StatusProvaEnum,
)
from app.db.session import get_db
from app.main import app
from app.services import qrcode_service
from tests.conftest import make_user

BASE = "http://test"
PREFIX = "/api/v1/provas"


# ─── Helpers ────────────────────────────────────────────────────────────


def _scalar(val=None):
    r = MagicMock()
    r.scalar_one_or_none.return_value = val
    r.scalar.return_value = val
    return r


def _setup(mock_db, *, admin=None, user=None):
    async def _get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db
    if admin is not None:
        app.dependency_overrides[get_admin_user] = lambda: admin
        app.dependency_overrides[get_current_user] = lambda: admin
    elif user is not None:
        app.dependency_overrides[get_current_user] = lambda: user


async def _refresh_prova_defaults(obj):
    """Simulate DB refresh by populating server-default fields."""
    if getattr(obj, "id", None) is None:
        obj.id = uuid.uuid4()
    if not hasattr(obj, "created_at") or obj.created_at is None:
        obj.created_at = datetime.now(timezone.utc)
    if not hasattr(obj, "updated_at") or obj.updated_at is None:
        obj.updated_at = datetime.now(timezone.utc)


# 16 bytes comecando com magic de JPEG
FAKE_JPEG_HEAD = b"\xff\xd8\xff" + b"\x00" * 13
FAKE_PNG_HEAD = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
FAKE_NON_IMAGE_HEAD = b"NOT AN IMAGE...."


def _client_error(code: str) -> ClientError:
    return ClientError(
        error_response={"Error": {"Code": code, "Message": "simulated"}},
        operation_name="TestOp",
    )


DEFAULT_TEMPLATE = {
    "nome": "padrao",
    "formato": "A4",
    "logo_enabled": True,
    "mostrar_data_criacao": False,
}


# ─── POST /upload-url ──────────────────────────────────────────────────


async def test_upload_url_happy_path(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(None)  # sem duplicata

    with patch(
        "app.api.v1.provas.r2_signed.generate_presigned_upload_url",
        new=AsyncMock(return_value="https://r2/upload?sig=abc"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(
                f"{PREFIX}/upload-url",
                json={
                    "nro_requerimento": "REQ-2026-0001",
                    "filename": "arte.jpg",
                    "content_type": "image/jpeg",
                },
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["upload_url"] == "https://r2/upload?sig=abc"
    assert data["object_key"].startswith("provas/")
    assert data["object_key"].endswith(".jpg") or "arte.jpg" in data["object_key"]
    assert data["max_bytes"] == 10 * 1024 * 1024


async def test_upload_url_rejects_invalid_content_type(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/upload-url",
            json={
                "nro_requerimento": "REQ-1",
                "filename": "file.pdf",
                "content_type": "application/pdf",
            },
        )
    assert resp.status_code == 422


async def test_upload_url_rejects_duplicate_nro_req(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(uuid.uuid4())  # prova ja existe

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/upload-url",
            json={
                "nro_requerimento": "REQ-DUP",
                "filename": "arte.jpg",
                "content_type": "image/jpeg",
            },
        )
    assert resp.status_code == 409
    assert "ja cadastrado" in resp.json()["detail"]


async def test_upload_url_requires_admin(regular_user, mock_db):
    _setup(mock_db, user=regular_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/upload-url",
            json={
                "nro_requerimento": "REQ-1",
                "filename": "arte.jpg",
                "content_type": "image/jpeg",
            },
        )
    assert resp.status_code == 403


async def test_upload_url_no_auth(mock_db):
    _setup(mock_db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/upload-url",
            json={
                "nro_requerimento": "REQ-1",
                "filename": "arte.jpg",
                "content_type": "image/jpeg",
            },
        )
    assert resp.status_code == 401


# ─── POST / (criar prova) ──────────────────────────────────────────────


async def test_create_prova_happy_path(admin_user, vendedor_matriz, mock_db):
    _setup(mock_db, admin=admin_user)

    # Ordem das chamadas db.execute:
    # 1. SELECT id FROM provas WHERE nro_req = ... (sem duplicata)
    # 2. SELECT Usuario WHERE id = vendedor_id FOR UPDATE (retorna vendedor)
    # 3. SELECT valor FROM configuracoes_sistema WHERE chave = 'template_etiqueta'
    mock_db.execute.side_effect = [
        _scalar(None),  # nao ha duplicata
        _scalar(vendedor_matriz),  # vendedor encontrado
        _scalar(DEFAULT_TEMPLATE),  # template
    ]
    mock_db.refresh.side_effect = _refresh_prova_defaults

    object_key = "provas/2026/04/abc123def456/arte.jpg"
    payload = {
        "nome": "Rotulo Verao 2026",
        "nro_requerimento": "REQ-2026-0001",
        "cliente": "ACME",
        "vendedor_id": str(vendedor_matriz.id),
        "object_key": object_key,
    }

    with patch(
        "app.api.v1.provas.r2_signed.head_object",
        new=AsyncMock(return_value={"ContentLength": 1024, "ContentType": "image/jpeg"}),
    ), patch(
        "app.api.v1.provas.r2_signed.get_object_head_bytes",
        new=AsyncMock(return_value=FAKE_JPEG_HEAD),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(f"{PREFIX}/", json=payload)

    assert resp.status_code == 201, resp.json()
    data = resp.json()
    assert data["prova"]["nome"] == "Rotulo Verao 2026"
    assert data["prova"]["nro_requerimento"] == "REQ-2026-0001"
    assert data["prova"]["vendedor_nome"] == vendedor_matriz.nome
    assert data["prova"]["status"] == "CRIADA"
    assert data["prova"]["rota"] is None  # ADR-042
    assert data["prova"]["rota_projetada"] == "PADRAO"  # MATRIZ
    assert data["prova"]["ciclo_atual"] == 1
    assert len(data["prova"]["qr_code_hash"]) == 64
    assert data["qr_code_payload"].startswith("3SD|REQ-2026-0001|")

    # PDF base64 decodavel comecando com %PDF-
    pdf_bytes = base64.b64decode(data["etiqueta_pdf_base64"])
    assert pdf_bytes.startswith(b"%PDF-")

    # 2 db.add: prova + etiqueta. audit_logs e inserido via add dentro de log_audit.
    assert mock_db.add.call_count == 3
    mock_db.flush.assert_awaited()
    mock_db.commit.assert_awaited_once()


async def test_create_prova_vendedor_filial_projeta_rota_direta(
    admin_user, vendedor_filial, mock_db
):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [
        _scalar(None),
        _scalar(vendedor_filial),
        _scalar(DEFAULT_TEMPLATE),
    ]
    mock_db.refresh.side_effect = _refresh_prova_defaults

    with patch(
        "app.api.v1.provas.r2_signed.head_object",
        new=AsyncMock(return_value={"ContentLength": 2048}),
    ), patch(
        "app.api.v1.provas.r2_signed.get_object_head_bytes",
        new=AsyncMock(return_value=FAKE_PNG_HEAD),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(
                f"{PREFIX}/",
                json={
                    "nome": "Prova Filial",
                    "nro_requerimento": "REQ-F-001",
                    "cliente": "Cliente Y",
                    "vendedor_id": str(vendedor_filial.id),
                    "object_key": "provas/2026/04/xyz/arte.png",
                },
            )

    assert resp.status_code == 201
    assert resp.json()["prova"]["rota_projetada"] == "DIRETA"


async def test_create_prova_duplicate_nro_req_cleans_up_r2(
    admin_user, vendedor_matriz, mock_db
):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(uuid.uuid4())  # ja existe

    with patch(
        "app.api.v1.provas.r2_delete", new=AsyncMock()
    ) as mock_delete:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(
                f"{PREFIX}/",
                json={
                    "nome": "Dup",
                    "nro_requerimento": "REQ-DUP",
                    "cliente": "C",
                    "vendedor_id": str(vendedor_matriz.id),
                    "object_key": "provas/2026/04/dup/arte.jpg",
                },
            )
    assert resp.status_code == 409
    mock_delete.assert_awaited_once()


async def test_create_prova_vendedor_not_found_cleans_up_r2(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [
        _scalar(None),  # nro_req ok
        _scalar(None),  # vendedor nao encontrado
    ]

    with patch("app.api.v1.provas.r2_delete", new=AsyncMock()) as mock_delete:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(
                f"{PREFIX}/",
                json={
                    "nome": "X",
                    "nro_requerimento": "REQ-X",
                    "cliente": "C",
                    "vendedor_id": str(uuid.uuid4()),
                    "object_key": "provas/2026/04/miss/arte.jpg",
                },
            )
    assert resp.status_code == 404
    mock_delete.assert_awaited_once()


async def test_create_prova_vendedor_nao_e_vendedor(admin_user, mock_db):
    motorista = make_user(setor=SetorEnum.MOTORISTA, localizacao=None)
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [
        _scalar(None),
        _scalar(motorista),
    ]

    with patch("app.api.v1.provas.r2_delete", new=AsyncMock()) as mock_delete:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(
                f"{PREFIX}/",
                json={
                    "nome": "X",
                    "nro_requerimento": "REQ-NOTVEND",
                    "cliente": "C",
                    "vendedor_id": str(motorista.id),
                    "object_key": "provas/2026/04/nv/arte.jpg",
                },
            )
    assert resp.status_code == 422
    assert "VENDEDOR" in resp.json()["detail"]
    mock_delete.assert_awaited_once()


async def test_create_prova_vendedor_inativo(admin_user, mock_db):
    vendedor_inativo = make_user(
        setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ, ativo=False
    )
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [
        _scalar(None),
        _scalar(vendedor_inativo),
    ]

    with patch("app.api.v1.provas.r2_delete", new=AsyncMock()) as mock_delete:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(
                f"{PREFIX}/",
                json={
                    "nome": "X",
                    "nro_requerimento": "REQ-INAT",
                    "cliente": "C",
                    "vendedor_id": str(vendedor_inativo.id),
                    "object_key": "provas/2026/04/i/arte.jpg",
                },
            )
    assert resp.status_code == 422
    assert "inativo" in resp.json()["detail"].lower()
    mock_delete.assert_awaited_once()


async def test_create_prova_object_not_in_r2(admin_user, vendedor_matriz, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [
        _scalar(None),
        _scalar(vendedor_matriz),
    ]

    with patch(
        "app.api.v1.provas.r2_signed.head_object",
        new=AsyncMock(side_effect=_client_error("404")),
    ), patch("app.api.v1.provas.r2_delete", new=AsyncMock()) as mock_delete:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(
                f"{PREFIX}/",
                json={
                    "nome": "X",
                    "nro_requerimento": "REQ-MISS",
                    "cliente": "C",
                    "vendedor_id": str(vendedor_matriz.id),
                    "object_key": "provas/2026/04/miss/arte.jpg",
                },
            )
    assert resp.status_code == 404
    assert "nao encontrado" in resp.json()["detail"].lower()
    mock_delete.assert_awaited_once()


async def test_create_prova_file_too_large(admin_user, vendedor_matriz, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [
        _scalar(None),
        _scalar(vendedor_matriz),
    ]

    with patch(
        "app.api.v1.provas.r2_signed.head_object",
        new=AsyncMock(return_value={"ContentLength": 11 * 1024 * 1024}),
    ), patch("app.api.v1.provas.r2_delete", new=AsyncMock()) as mock_delete:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(
                f"{PREFIX}/",
                json={
                    "nome": "Big",
                    "nro_requerimento": "REQ-BIG",
                    "cliente": "C",
                    "vendedor_id": str(vendedor_matriz.id),
                    "object_key": "provas/2026/04/big/arte.jpg",
                },
            )
    assert resp.status_code == 422
    assert "limite" in resp.json()["detail"].lower() or "10" in resp.json()["detail"]
    mock_delete.assert_awaited_once()


async def test_create_prova_magic_bytes_invalid(admin_user, vendedor_matriz, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [
        _scalar(None),
        _scalar(vendedor_matriz),
    ]

    with patch(
        "app.api.v1.provas.r2_signed.head_object",
        new=AsyncMock(return_value={"ContentLength": 500}),
    ), patch(
        "app.api.v1.provas.r2_signed.get_object_head_bytes",
        new=AsyncMock(return_value=FAKE_NON_IMAGE_HEAD),
    ), patch("app.api.v1.provas.r2_delete", new=AsyncMock()) as mock_delete:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(
                f"{PREFIX}/",
                json={
                    "nome": "FakePng",
                    "nro_requerimento": "REQ-FAKE",
                    "cliente": "C",
                    "vendedor_id": str(vendedor_matriz.id),
                    "object_key": "provas/2026/04/fake/arte.png",
                },
            )
    assert resp.status_code == 422
    assert "magic bytes" in resp.json()["detail"].lower() or "JPG" in resp.json()["detail"]
    mock_delete.assert_awaited_once()


async def test_create_prova_commit_failure_rollback_and_cleanup(
    admin_user, vendedor_matriz, mock_db
):
    """Falha de commit (DB transiente) retorna 502 e limpa R2.

    F01 (auditoria externa): mudanca de 500 -> 502 para alinhar com o padrao
    unificado dos ADR-074 (C07 list), ADR-076 (C08 detalhe) e ADR-078 (C09
    update). 502 = "upstream indisponivel, pode retentar" (DB e upstream do
    FastAPI); 500 seria "bug interno" (nao e o caso aqui).
    """
    _setup(mock_db, admin=admin_user)
    # Ordem de db.execute na nova implementacao (gerar_pdf antes do commit):
    # 1. SELECT nro_req (sem duplicata)
    # 2. SELECT vendedor (FOR UPDATE)
    # 3. SELECT template_etiqueta
    mock_db.execute.side_effect = [
        _scalar(None),
        _scalar(vendedor_matriz),
        _scalar(DEFAULT_TEMPLATE),
    ]
    mock_db.commit.side_effect = Exception("DB unreachable")

    with patch(
        "app.api.v1.provas.r2_signed.head_object",
        new=AsyncMock(return_value={"ContentLength": 1024}),
    ), patch(
        "app.api.v1.provas.r2_signed.get_object_head_bytes",
        new=AsyncMock(return_value=FAKE_JPEG_HEAD),
    ), patch("app.api.v1.provas.r2_delete", new=AsyncMock()) as mock_delete:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(
                f"{PREFIX}/",
                json={
                    "nome": "Fail",
                    "nro_requerimento": "REQ-FAIL",
                    "cliente": "C",
                    "vendedor_id": str(vendedor_matriz.id),
                    "object_key": "provas/2026/04/fail/arte.jpg",
                },
            )
    assert resp.status_code == 502
    assert "persistir prova" in resp.json()["detail"].lower()
    mock_db.rollback.assert_awaited()
    mock_delete.assert_awaited_once()


async def test_create_prova_refresh_failure_after_commit_responds_201(
    admin_user, vendedor_matriz, mock_db
):
    """F02 (auditoria externa): db.refresh falhando APOS o commit bem-sucedido
    deve responder 201 com os dados em memoria em vez de 500.

    Rationale: quando o refresh falha, a prova ja esta persistida no DB (o
    commit teve sucesso). Retornar 500 seria enganoso porque o cliente
    retentaria e pegaria 409 'ja cadastrada' — o usuario acharia que a prova
    nao foi criada quando na verdade foi. O fix constroi o response usando
    o `created_at` gerado no backend antes do INSERT e os dados do ORM em
    memoria.
    """
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [
        _scalar(None),
        _scalar(vendedor_matriz),
        _scalar(DEFAULT_TEMPLATE),
    ]
    # Commit bem-sucedido (default AsyncMock)
    mock_db.refresh.side_effect = Exception("connection dropped after commit")

    with patch(
        "app.api.v1.provas.r2_signed.head_object",
        new=AsyncMock(return_value={"ContentLength": 1024}),
    ), patch(
        "app.api.v1.provas.r2_signed.get_object_head_bytes",
        new=AsyncMock(return_value=FAKE_JPEG_HEAD),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(
                f"{PREFIX}/",
                json={
                    "nome": "Refresh Fail",
                    "nro_requerimento": "REQ-REFRESH-FAIL",
                    "cliente": "C",
                    "vendedor_id": str(vendedor_matriz.id),
                    "object_key": "provas/2026/04/refreshfail/arte.jpg",
                },
            )

    # Response deve ser 201 normal — refresh failure e degradacao graciosa.
    assert resp.status_code == 201, resp.json()
    data = resp.json()
    assert data["prova"]["nome"] == "Refresh Fail"
    assert data["prova"]["nro_requerimento"] == "REQ-REFRESH-FAIL"
    assert data["prova"]["status"] == "CRIADA"
    # created_at/updated_at vem do datetime.now(UTC) gerado no backend antes
    # do INSERT — devem ser strings ISO validas.
    assert data["prova"]["created_at"] is not None
    assert data["prova"]["updated_at"] is not None
    # Commit foi chamado com sucesso; rollback NAO foi chamado (refresh
    # failure nao desfaz o commit).
    mock_db.commit.assert_awaited_once()
    mock_db.rollback.assert_not_awaited()


async def test_create_prova_pdf_generation_failure_rollsback_before_commit(
    admin_user, vendedor_matriz, mock_db
):
    """Falha em gerar_pdf (ex: fonte ausente, template invalido) deve
    retornar 422 e limpar R2, SEM tocar no banco (commit nunca acontece)."""
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [
        _scalar(None),
        _scalar(vendedor_matriz),
        _scalar(DEFAULT_TEMPLATE),  # template carregado com sucesso...
    ]

    with patch(
        "app.api.v1.provas.r2_signed.head_object",
        new=AsyncMock(return_value={"ContentLength": 1024}),
    ), patch(
        "app.api.v1.provas.r2_signed.get_object_head_bytes",
        new=AsyncMock(return_value=FAKE_JPEG_HEAD),
    ), patch(
        "app.api.v1.provas.gerar_pdf",
        side_effect=RuntimeError("Fontes DejaVu ausentes"),
    ), patch("app.api.v1.provas.r2_delete", new=AsyncMock()) as mock_delete:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(
                f"{PREFIX}/",
                json={
                    "nome": "PdfFail",
                    "nro_requerimento": "REQ-PDFFAIL",
                    "cliente": "C",
                    "vendedor_id": str(vendedor_matriz.id),
                    "object_key": "provas/2026/04/pdffail/arte.jpg",
                },
            )

    assert resp.status_code == 422
    # Commit NUNCA foi chamado — prova NAO foi persistida
    mock_db.commit.assert_not_called()
    # R2 foi limpo
    mock_delete.assert_awaited_once()


async def test_create_prova_integrity_error_returns_409(
    admin_user, vendedor_matriz, mock_db
):
    """A2 (auditoria Wave 2) — race TOCTOU: dois admins criam a mesma
    prova simultaneamente. O check inicial de unicidade passa em ambos,
    mas o UNIQUE constraint no banco rejeita o segundo no commit.

    Comportamento esperado:
      - Mapear IntegrityError para 409 Conflict (nao 500).
      - Mensagem deve deixar claro que o nro_requerimento ja existe.
      - db.rollback e _cleanup_r2 sao chamados, mesma semantica do
        caminho de erro generico.
    """
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [
        _scalar(None),  # check inicial passou (race: o outro admin ainda nao commitou)
        _scalar(vendedor_matriz),
        _scalar(DEFAULT_TEMPLATE),
    ]
    # O commit levanta IntegrityError (constraint UNIQUE violado pelo outro admin).
    mock_db.commit.side_effect = IntegrityError(
        statement="INSERT ...",
        params={},
        orig=Exception("duplicate key value violates unique constraint"),
    )

    with patch(
        "app.api.v1.provas.r2_signed.head_object",
        new=AsyncMock(return_value={"ContentLength": 1024}),
    ), patch(
        "app.api.v1.provas.r2_signed.get_object_head_bytes",
        new=AsyncMock(return_value=FAKE_JPEG_HEAD),
    ), patch("app.api.v1.provas.r2_delete", new=AsyncMock()) as mock_delete:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(
                f"{PREFIX}/",
                json={
                    "nome": "Race",
                    "nro_requerimento": "REQ-RACE",
                    "cliente": "C",
                    "vendedor_id": str(vendedor_matriz.id),
                    "object_key": "provas/2026/04/race/arte.jpg",
                },
            )
    assert resp.status_code == 409
    assert "ja cadastrado" in resp.json()["detail"]
    mock_db.rollback.assert_awaited()
    mock_delete.assert_awaited_once()


async def test_create_prova_cleanup_r2_failure_does_not_mask_original_error(
    admin_user, vendedor_matriz, mock_db
):
    """A4 (auditoria Wave 2) — quando o proprio cleanup R2 falha (ex: R2
    temporariamente indisponivel), o log "orfao possivel" e emitido mas o
    erro original do request deve prevalecer. O cliente nao pode receber
    um erro diferente por causa do cleanup.

    Usa-se o caminho de duplicata (409) como gatilho simples para exercitar
    _cleanup_r2: o behavior deve ser identico se o cleanup passar ou falhar.
    """
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(uuid.uuid4())  # ja existe

    # r2_delete levanta — o handler loga mas mantem o 409 original.
    with patch(
        "app.api.v1.provas.r2_delete",
        new=AsyncMock(side_effect=RuntimeError("R2 temporariamente indisponivel")),
    ) as mock_delete:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(
                f"{PREFIX}/",
                json={
                    "nome": "Dup",
                    "nro_requerimento": "REQ-DUP-CLEAN",
                    "cliente": "C",
                    "vendedor_id": str(vendedor_matriz.id),
                    "object_key": "provas/2026/04/dupclean/arte.jpg",
                },
            )

    # Status code do erro original (409 — duplicata) — NAO muda por causa do cleanup falho.
    assert resp.status_code == 409
    assert "ja cadastrado" in resp.json()["detail"]
    # _cleanup_r2 foi tentado e o mock confirma a chamada.
    mock_delete.assert_awaited_once()


async def test_create_prova_requires_admin(regular_user, mock_db):
    _setup(mock_db, user=regular_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/",
            json={
                "nome": "X",
                "nro_requerimento": "REQ-1",
                "cliente": "C",
                "vendedor_id": str(uuid.uuid4()),
                "object_key": "provas/2026/04/x/arte.jpg",
            },
        )
    assert resp.status_code == 403


async def test_create_prova_rejects_object_key_outside_provas(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/",
            json={
                "nome": "X",
                "nro_requerimento": "REQ-1",
                "cliente": "C",
                "vendedor_id": str(uuid.uuid4()),
                "object_key": "etc/passwd",
            },
        )
    assert resp.status_code == 422  # pydantic validation error


# ═══════════════════════════════════════════════════════════════════════
# GET /api/v1/provas/  — Componente 07 (listagem com filtros)
# ═══════════════════════════════════════════════════════════════════════


def _make_prova(
    *,
    id=None,
    nome="Prova Teste",
    nro_requerimento="REQ-TEST-001",
    cliente="Cliente X",
    vendedor_id=None,
    status_prova=StatusProvaEnum.CRIADA,
    rota=None,
    ciclo_atual=1,
):
    """Fabrica de ProvaDigital in-memory (sem INSERT real)."""
    now = datetime.now(timezone.utc)
    return ProvaDigital(
        id=id or uuid.uuid4(),
        nome=nome,
        nro_requerimento=nro_requerimento,
        cliente=cliente,
        vendedor_id=vendedor_id or uuid.uuid4(),
        imagem_url=f"provas/2026/04/{uuid.uuid4().hex}/arte.jpg",
        qr_code_hash="a" * 64,
        status=status_prova,
        rota=rota,
        ciclo_atual=ciclo_atual,
        motivo_cancelamento=None,
        created_at=now,
        updated_at=now,
    )


def _list_result(rows):
    """Mock do resultado de `db.execute(data_stmt)` com JOIN.

    O endpoint faz `result.all()` e itera sobre `(prova, vendedor_nome)`.
    """
    r = MagicMock()
    r.all.return_value = rows
    return r


def _capture_list_stmts(mock_db, *, count=0, rows=None):
    """Configura o mock_db para responder (count, rows) em ordem.

    O endpoint executa 2 queries: count primeiro, depois data. Essa helper
    registra as SQL statements emitidas em `mock_db._captured_stmts` para
    inspecao (verificar clausula WHERE aplicada).
    """
    mock_db._captured_stmts = []

    async def _execute(stmt):
        mock_db._captured_stmts.append(stmt)
        if len(mock_db._captured_stmts) == 1:
            return _scalar(count)
        return _list_result(rows or [])

    mock_db.execute.side_effect = _execute


def _compiled_sql(stmt) -> str:
    """Compila o statement contra dialect PostgreSQL para inspecao textual."""
    from sqlalchemy.dialects import postgresql

    return str(
        stmt.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


# ─── GET list: happy paths ────────────────────────────────────────────


async def test_list_happy_admin_sem_filtros(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    vendedor_id = uuid.uuid4()
    provas = [
        _make_prova(
            nome="Prova 1", nro_requerimento="REQ-001", cliente="ACME",
            vendedor_id=vendedor_id,
        ),
        _make_prova(
            nome="Prova 2", nro_requerimento="REQ-002", cliente="Beta Corp",
            vendedor_id=vendedor_id,
        ),
    ]
    rows = [(p, "Vendedor Teste") for p in provas]
    _capture_list_stmts(mock_db, count=2, rows=rows)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/")

    assert resp.status_code == 200, resp.json()
    data = resp.json()
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["pages"] == 1
    assert len(data["items"]) == 2
    assert data["items"][0]["nome"] == "Prova 1"
    assert data["items"][0]["vendedor_nome"] == "Vendedor Teste"
    assert data["items"][0]["rota"] is None  # ADR-042


async def test_list_filter_status(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(status_prova=StatusProvaEnum.RECEBIDA_PELA_CLICHERIA)
    _capture_list_stmts(mock_db, count=1, rows=[(prova, "Joao")])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/?status=RECEBIDA_PELA_CLICHERIA")

    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    # Confirma que o WHERE inclui o filtro de status
    sql = _compiled_sql(mock_db._captured_stmts[0])
    assert "'RECEBIDA_PELA_CLICHERIA'" in sql
    assert "status" in sql.lower()


async def test_list_filter_periodo(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    _capture_list_stmts(mock_db, count=0, rows=[])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(
            f"{PREFIX}/?periodo_inicio=2026-04-01&periodo_fim=2026-04-30"
        )

    assert resp.status_code == 200
    sql = _compiled_sql(mock_db._captured_stmts[0])
    assert "2026-04-01" in sql
    # Periodo fim e inclusivo — ADR-048 adiciona 1 dia, entao aparece 05-01
    assert "2026-05-01" in sql


async def test_list_filter_periodo_respects_brt_timezone(admin_user, mock_db):
    """F25 (auditoria externa): datas do filtro sao interpretadas em BRT
    (America/Sao_Paulo, UTC-3 fixo), nao em UTC.

    `periodo_inicio=2026-04-09` deve virar `2026-04-09 00:00 BRT` =
    `2026-04-09 03:00 UTC` no SQL compilado. Sem a conversao, seria
    `2026-04-09 00:00 UTC`, o que excluiria provas criadas as 00:00-03:00
    BRT do dia 9 (= 03:00-06:00 UTC do dia 9) e incluiria provas do dia 8
    BRT depois das 21:00 (= 00:00 UTC do dia 9) — ambos comportamentos
    confundem o usuario.
    """
    _setup(mock_db, admin=admin_user)
    _capture_list_stmts(mock_db, count=0, rows=[])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(
            f"{PREFIX}/?periodo_inicio=2026-04-09&periodo_fim=2026-04-09"
        )

    assert resp.status_code == 200
    sql = _compiled_sql(mock_db._captured_stmts[0])
    # Inicio = 2026-04-09 00:00 BRT = 2026-04-09 03:00 UTC
    assert "2026-04-09 03:00:00" in sql
    # Fim = 2026-04-10 00:00 BRT = 2026-04-10 03:00 UTC (adicionou 1 dia)
    assert "2026-04-10 03:00:00" in sql


async def test_list_filter_vendedor_id(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    vid = uuid.uuid4()
    _capture_list_stmts(mock_db, count=0, rows=[])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/?vendedor_id={vid}")

    assert resp.status_code == 200
    sql = _compiled_sql(mock_db._captured_stmts[0])
    assert str(vid) in sql


async def test_list_filter_cliente_ilike(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    _capture_list_stmts(mock_db, count=0, rows=[])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/?cliente=ACME")

    assert resp.status_code == 200
    sql = _compiled_sql(mock_db._captured_stmts[0])
    assert "ILIKE" in sql
    assert "%ACME%" in sql


async def test_list_filter_rota(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    _capture_list_stmts(mock_db, count=0, rows=[])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/?rota=DIRETA")

    assert resp.status_code == 200
    sql = _compiled_sql(mock_db._captured_stmts[0])
    assert "'DIRETA'" in sql


async def test_list_filter_busca_nome_ou_nro(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    _capture_list_stmts(mock_db, count=0, rows=[])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/?busca=REQ-2026")

    assert resp.status_code == 200
    sql = _compiled_sql(mock_db._captured_stmts[0])
    assert "ILIKE" in sql
    assert "%REQ-2026%" in sql
    assert "OR" in sql.upper()  # busca em nome OU nro_requerimento


# ─── C1 (auditoria Wave 2 — Sessao 19) — escape de wildcards ILIKE ────
#
# O ILIKE do Postgres interpreta `%`, `_` e `\` como metacaracteres. Antes
# do fix, um admin que digitasse esses chars no filtro `busca` ou `cliente`
# tinha resultados corrompidos (ex: `%` casava tudo). A solucao e escapar
# cada um com `\` e passar `escape="\\"` no `.ilike()`.
#
# Os testes abaixo inspecionam o SQL compilado para garantir que:
#   1. O SQL contem o char literal escapado com `\\`
#   2. Uma clausula `ESCAPE '\'` aparece no output compilado


async def test_list_filter_busca_escapa_percent_literal(admin_user, mock_db):
    """Busca por `50%` deve encontrar o literal `50%`, nao `50<qualquer coisa>`."""
    _setup(mock_db, admin=admin_user)
    _capture_list_stmts(mock_db, count=0, rows=[])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/?busca=50%25")  # 50% URL-encoded

    assert resp.status_code == 200
    sql = _compiled_sql(mock_db._captured_stmts[0])
    # O pattern escapado tem o `%` literal precedido por `\\`.
    # SQLAlchemy compila isso para a forma `'%50\%%'` com ESCAPE '\'.
    assert "50" in sql
    assert "ESCAPE" in sql.upper()
    # Confirma que o `%` do input foi escapado — o literal `\%` aparece
    # entre os delimitadores de pattern.
    assert r"\%" in sql


async def test_list_filter_busca_escapa_underscore_literal(admin_user, mock_db):
    """Busca por `a_b` nao pode casar `axb` (wildcard single-char)."""
    _setup(mock_db, admin=admin_user)
    _capture_list_stmts(mock_db, count=0, rows=[])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/?busca=a_b")

    assert resp.status_code == 200
    sql = _compiled_sql(mock_db._captured_stmts[0])
    assert "ESCAPE" in sql.upper()
    assert r"\_" in sql  # underscore escapado


async def test_list_filter_cliente_escapa_backslash_literal(admin_user, mock_db):
    """Busca por `foo\\bar` nao pode quebrar o escape char do SQL."""
    _setup(mock_db, admin=admin_user)
    _capture_list_stmts(mock_db, count=0, rows=[])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/?cliente=foo%5Cbar")  # foo\bar URL-encoded

    assert resp.status_code == 200
    sql = _compiled_sql(mock_db._captured_stmts[0])
    assert "ESCAPE" in sql.upper()
    # O `\` literal do input vira `\\` no pattern (escapado primeiro) para
    # nao interferir nos escapes de `%` e `_`.
    assert r"\\" in sql


# ─── A3 (auditoria Wave 2 — Sessao 19) — validacao cruzada de periodo ─


async def test_list_periodo_fim_antes_de_inicio_422(admin_user, mock_db):
    """Periodos invertidos devem retornar 422 em vez de lista vazia silenciosa."""
    _setup(mock_db, admin=admin_user)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(
            f"{PREFIX}/?periodo_inicio=2026-05-01&periodo_fim=2026-04-01"
        )

    assert resp.status_code == 422
    assert "anterior" in resp.json()["detail"].lower()
    # A validacao deve acontecer ANTES de qualquer query — garantimos que
    # o mock de DB nao foi chamado.
    mock_db.execute.assert_not_called()


async def test_list_periodo_mesma_data_aceita(admin_user, mock_db):
    """Periodo inicio == fim (um unico dia) deve ser aceito."""
    _setup(mock_db, admin=admin_user)
    _capture_list_stmts(mock_db, count=0, rows=[])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(
            f"{PREFIX}/?periodo_inicio=2026-04-10&periodo_fim=2026-04-10"
        )

    assert resp.status_code == 200
    sql = _compiled_sql(mock_db._captured_stmts[0])
    assert "2026-04-10" in sql
    # fim inclusivo -> fim + 1 dia
    assert "2026-04-11" in sql


# ─── A2 (auditoria Wave 2 — Sessao 19) — try/except em list_provas ────


async def test_list_db_error_returns_502(admin_user, mock_db):
    """Erro transitorio no DB (timeout, connection reset) deve retornar
    502 com mensagem acionavel em vez de 500 generico do handler global.
    """
    _setup(mock_db, admin=admin_user)
    # O count_stmt e a primeira execute — falhamos logo no count.
    mock_db.execute.side_effect = RuntimeError("connection reset by peer")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/")

    assert resp.status_code == 502
    assert "carregar provas" in resp.json()["detail"].lower()


async def test_list_combined_filters(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    _capture_list_stmts(mock_db, count=0, rows=[])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(
            f"{PREFIX}/?status=CRIADA&cliente=ACME&busca=REQ"
        )

    assert resp.status_code == 200
    sql = _compiled_sql(mock_db._captured_stmts[0])
    assert "'CRIADA'" in sql
    assert "%ACME%" in sql
    assert "%REQ%" in sql


async def test_list_pagination_offset_limit(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    _capture_list_stmts(mock_db, count=50, rows=[])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/?page=3&page_size=10")

    assert resp.status_code == 200
    assert resp.json()["total"] == 50
    assert resp.json()["page"] == 3
    assert resp.json()["page_size"] == 10
    assert resp.json()["pages"] == 5
    # Data stmt e o segundo — contem OFFSET/LIMIT
    data_sql = _compiled_sql(mock_db._captured_stmts[1])
    assert "LIMIT 10" in data_sql
    assert "OFFSET 20" in data_sql


async def test_list_pages_calcula_corretamente(admin_user, mock_db):
    """Borda: 21 items / page_size=10 -> 3 paginas."""
    _setup(mock_db, admin=admin_user)
    _capture_list_stmts(mock_db, count=21, rows=[])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/?page=1&page_size=10")

    assert resp.json()["pages"] == 3


async def test_list_zero_items(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    _capture_list_stmts(mock_db, count=0, rows=[])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/")

    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["pages"] == 0
    assert resp.json()["items"] == []


# ─── Scoping por setor (ADR-046) ──────────────────────────────────────


async def test_list_vendedor_scope_own_provas(vendedor_matriz, mock_db):
    """VENDEDOR ve apenas provas onde vendedor_id = user.id."""
    _setup(mock_db, user=vendedor_matriz)
    _capture_list_stmts(mock_db, count=0, rows=[])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/")

    assert resp.status_code == 200
    sql = _compiled_sql(mock_db._captured_stmts[0])
    assert str(vendedor_matriz.id) in sql
    assert "vendedor_id" in sql.lower()


async def test_list_motorista_scope_com_motorista(mock_db):
    """MOTORISTA ve apenas provas em status COM_MOTORISTA."""
    motorista = make_user(setor=SetorEnum.MOTORISTA, localizacao=None)
    _setup(mock_db, user=motorista)
    _capture_list_stmts(mock_db, count=0, rows=[])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/")

    assert resp.status_code == 200
    sql = _compiled_sql(mock_db._captured_stmts[0])
    assert "'COM_MOTORISTA'" in sql


async def test_list_clicheria_scope_status(mock_db):
    """CLICHERIA ve apenas provas em status ENVIADA/ENCAMINHADA/RECEBIDA clicheria."""
    clicheria = make_user(setor=SetorEnum.CLICHERIA, localizacao=None)
    _setup(mock_db, user=clicheria)
    _capture_list_stmts(mock_db, count=0, rows=[])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/")

    assert resp.status_code == 200
    sql = _compiled_sql(mock_db._captured_stmts[0])
    assert "'ENVIADA_PARA_CLICHERIA'" in sql
    assert "'ENCAMINHADA_A_CLICHERIA'" in sql
    assert "'RECEBIDA_PELA_CLICHERIA'" in sql


async def test_list_admin_sem_scope(admin_user, mock_db):
    """Admin nao tem filtro de scoping — WHERE nao inclui vendedor_id/status base."""
    _setup(mock_db, admin=admin_user)
    _capture_list_stmts(mock_db, count=0, rows=[])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/")

    assert resp.status_code == 200
    # Admin sem filtros explicitos deve gerar uma query sem WHERE de scoping.
    # Confirmamos pela ausencia das clausulas base de scoping:
    sql = _compiled_sql(mock_db._captured_stmts[0])
    # Admin deve ter apenas um count simples — sem nenhuma das clausulas de scoping
    assert "vendedor_id =" not in sql
    assert "'COM_MOTORISTA'" not in sql


async def test_list_studio_sem_admin_ve_zero(mock_db):
    """A5 (auditoria Wave 2) — branch defensivo de `_scoping_filter`.

    A combinacao STUDIO + is_admin=false nao deveria existir pos-ADR-018,
    mas `_scoping_filter` tem um `return func.false()` como defesa em
    profundidade: se por qualquer razao um STUDIO nao-admin for criado
    (bug de migration, SQL direto, etc), ele NAO pode ver nenhuma prova.

    Este teste blinda esse branch contra regressao futura. Se alguem
    remover o `func.false()` ou trocar por `None` (sem filtro), o teste
    falha imediatamente.
    """
    studio_nao_admin = make_user(
        setor=SetorEnum.STUDIO, localizacao=None, is_admin=False
    )
    _setup(mock_db, user=studio_nao_admin)
    _capture_list_stmts(mock_db, count=0, rows=[])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/")

    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    # O SQL compilado deve conter a clausula constante `false` emitida
    # pelo `func.false()`. A forma exata depende do dialect do Postgres
    # (SQLAlchemy pode serializar como `false` ou `false`).
    sql = _compiled_sql(mock_db._captured_stmts[0]).lower()
    assert "false" in sql


# ─── Validacao de query params ───────────────────────────────────────


async def test_list_invalid_status_422(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/?status=STATUS_INVALIDO")
    assert resp.status_code == 422


async def test_list_invalid_rota_422(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/?rota=LATERAL")
    assert resp.status_code == 422


async def test_list_page_zero_422(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/?page=0")
    assert resp.status_code == 422


async def test_list_page_size_over_max_422(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/?page_size=101")
    assert resp.status_code == 422


async def test_list_invalid_date_format_422(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/?periodo_inicio=2026/04/01")
    assert resp.status_code == 422


async def test_list_no_auth_401(mock_db):
    _setup(mock_db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/")
    assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════
# GET /api/v1/provas/{prova_id}  — Componente 08 (detalhe)
# ═══════════════════════════════════════════════════════════════════════


def _detail_row(
    prova, vendedor_nome, vendedor_localizacao, vendedor_setor=SetorEnum.VENDEDOR
):
    """Mock do `result.first()` para query de detalhe com JOIN.

    F05 (auditoria externa Wave 2): o JOIN agora retorna 4 colunas
    (prova, vendedor_nome, vendedor_localizacao, vendedor_setor) para
    eliminar a segunda query do `get_prova_detail`. O default de setor
    e VENDEDOR porque esse e o caso de 99% dos testes de detalhe.
    """
    r = MagicMock()
    r.first.return_value = (
        prova,
        vendedor_nome,
        vendedor_localizacao,
        vendedor_setor,
    )
    return r


def _detail_row_none():
    r = MagicMock()
    r.first.return_value = None
    return r


def _scalars_all(items):
    r = MagicMock()
    s = MagicMock()
    s.all.return_value = items
    r.scalars.return_value = s
    # Tambem suporta .all() direto (para queries de movimentacoes com tuplas).
    r.all.return_value = items
    return r


# ─── GET /{id} ────────────────────────────────────────────────────────


async def test_get_detail_happy_admin(admin_user, vendedor_matriz, mock_db):
    """F05 (auditoria externa): apos a mudanca no helper
    `_carregar_prova_com_scoping` que ja inclui `vendedor_setor` no JOIN,
    o handler nao faz mais uma segunda query — o side_effect tem apenas
    o `_detail_row` unico.
    """
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(
        nome="Prova Detalhe",
        nro_requerimento="REQ-D-001",
        cliente="Cliente D",
        vendedor_id=vendedor_matriz.id,
    )

    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{prova.id}")

    assert resp.status_code == 200, resp.json()
    data = resp.json()
    assert data["nome"] == "Prova Detalhe"
    assert data["vendedor_nome"] == vendedor_matriz.nome
    assert data["vendedor_localizacao"] == "MATRIZ"
    assert data["rota_projetada"] == "PADRAO"
    assert data["rota"] is None
    # F05: apenas 1 execute (scoped), nao 2 como antes da otimizacao.
    assert mock_db.execute.call_count == 1


async def test_get_detail_rota_projetada_filial(
    admin_user, vendedor_filial, mock_db
):
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(vendedor_id=vendedor_filial.id)
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_filial.nome, vendedor_filial.localizacao),
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{prova.id}")
    assert resp.status_code == 200
    assert resp.json()["rota_projetada"] == "DIRETA"


async def test_get_detail_rota_projetada_none_para_nao_vendedor(
    admin_user, mock_db
):
    """Edge case: vendedor original nao e mais VENDEDOR (setor mudou).

    F05: passamos `vendedor_setor=SetorEnum.STUDIO` explicitamente no
    _detail_row — antes o setor vinha de um segundo SELECT Usuario.
    """
    ex_vendedor = make_user(setor=SetorEnum.STUDIO, localizacao=None, is_admin=False)
    prova = _make_prova(vendedor_id=ex_vendedor.id)
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [
        _detail_row(prova, ex_vendedor.nome, None, vendedor_setor=SetorEnum.STUDIO),
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{prova.id}")
    assert resp.status_code == 200
    assert resp.json()["rota_projetada"] is None


async def test_get_detail_vendedor_scoping_happy(vendedor_matriz, mock_db):
    """VENDEDOR consegue ver a propria prova."""
    _setup(mock_db, user=vendedor_matriz)
    prova = _make_prova(vendedor_id=vendedor_matriz.id)
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{prova.id}")
    assert resp.status_code == 200


async def test_get_detail_vendedor_scoping_other_owner_404(
    vendedor_matriz, mock_db
):
    """VENDEDOR tentando ver prova de OUTRO vendedor -> 404 (nao vaza existencia)."""
    _setup(mock_db, user=vendedor_matriz)
    # Scoping aplica `vendedor_id == user.id`, entao a query retorna None
    mock_db.execute.side_effect = [_detail_row_none()]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{uuid.uuid4()}")

    assert resp.status_code == 404
    assert "nao encontrada" in resp.json()["detail"].lower()


async def test_get_detail_not_found(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [_detail_row_none()]
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_get_detail_no_auth_401(mock_db):
    _setup(mock_db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{uuid.uuid4()}")
    assert resp.status_code == 401


async def test_get_detail_invalid_uuid_retorna_404(admin_user, mock_db):
    """C08 M3 (auditoria externa Wave 2): UUID invalido no path retorna 404
    'Prova nao encontrada' em vez de 422 verbose do Pydantic validator.

    Antes deste fix, o FastAPI retornava 422 com mensagem verbose do tipo
    'Input should be a valid UUID, invalid character: expected an optional
    prefix of `urn:uuid:`...' — vazava detalhes do validator e era
    inconsistente com o 404 retornado quando um UUID valido aponta para
    prova inexistente. Agora ambos os casos retornam o mesmo 404 generico
    em todos os 5 endpoints de detalhe.
    """
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        for path in ("abc-not-uuid", "123", "xxx"):
            resp_detail = await ac.get(f"{PREFIX}/{path}")
            assert resp_detail.status_code == 404, (
                f"GET /{path} retornou {resp_detail.status_code}"
            )
            assert resp_detail.json()["detail"] == "Prova nao encontrada"

            resp_imagem = await ac.get(f"{PREFIX}/{path}/imagem-url")
            assert resp_imagem.status_code == 404

            resp_mov = await ac.get(f"{PREFIX}/{path}/movimentacoes")
            assert resp_mov.status_code == 404

            resp_pdf = await ac.get(f"{PREFIX}/{path}/etiqueta.pdf")
            assert resp_pdf.status_code == 404

            resp_qr = await ac.get(f"{PREFIX}/{path}/qr-code.png")
            assert resp_qr.status_code == 404


# ─── GET /{id}/imagem-url ─────────────────────────────────────────────


async def test_get_imagem_url_happy(admin_user, vendedor_matriz, mock_db):
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(vendedor_id=vendedor_matriz.id)
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]

    with patch(
        "app.api.v1.provas.r2_signed.generate_presigned_get_url",
        new=AsyncMock(return_value="https://r2/arte?sig=abc"),
    ) as mock_gen:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get(f"{PREFIX}/{prova.id}/imagem-url")

    assert resp.status_code == 200
    assert resp.json()["url"] == "https://r2/arte?sig=abc"
    assert "expires_at" in resp.json()
    mock_gen.assert_awaited_once()


async def test_get_imagem_url_scoping_vendedor_other_owner_404(
    vendedor_matriz, mock_db
):
    _setup(mock_db, user=vendedor_matriz)
    mock_db.execute.side_effect = [_detail_row_none()]
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{uuid.uuid4()}/imagem-url")
    assert resp.status_code == 404


async def test_get_imagem_url_not_found(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [_detail_row_none()]
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{uuid.uuid4()}/imagem-url")
    assert resp.status_code == 404


async def test_get_imagem_url_r2_failure_502(
    admin_user, vendedor_matriz, mock_db
):
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(vendedor_id=vendedor_matriz.id)
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]
    with patch(
        "app.api.v1.provas.r2_signed.generate_presigned_get_url",
        new=AsyncMock(side_effect=Exception("R2 down")),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get(f"{PREFIX}/{prova.id}/imagem-url")
    assert resp.status_code == 502


# ─── GET /{id}/movimentacoes ──────────────────────────────────────────


async def test_get_movimentacoes_empty_on_wave2(
    admin_user, vendedor_matriz, mock_db
):
    """Na Wave 2 nao ha transicoes — endpoint retorna items=[] total=0."""
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(vendedor_id=vendedor_matriz.id)
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
        _scalars_all([]),  # SELECT movimentacoes
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{prova.id}/movimentacoes")
    assert resp.status_code == 200
    assert resp.json()["items"] == []
    assert resp.json()["total"] == 0


async def test_get_movimentacoes_scoping_vendedor_other_owner_404(
    vendedor_matriz, mock_db
):
    _setup(mock_db, user=vendedor_matriz)
    mock_db.execute.side_effect = [_detail_row_none()]
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{uuid.uuid4()}/movimentacoes")
    assert resp.status_code == 404


async def test_get_movimentacoes_not_found(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [_detail_row_none()]
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{uuid.uuid4()}/movimentacoes")
    assert resp.status_code == 404


# ─── GET /{id}/etiqueta.pdf ───────────────────────────────────────────


async def test_get_etiqueta_pdf_happy(admin_user, vendedor_matriz, mock_db):
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(
        vendedor_id=vendedor_matriz.id,
        nro_requerimento="REQ-PDF-001",
    )
    etiqueta = Etiqueta(
        id=uuid.uuid4(),
        prova_id=prova.id,
        nome_prova=prova.nome,
        nro_requerimento=prova.nro_requerimento,
        vendedor_nome=vendedor_matriz.nome,
        qr_code_image=b"\x89PNG\r\n\x1a\n" + b"\x00" * 100,  # PNG fake minimo
        created_at=datetime.now(timezone.utc),
    )

    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
        _scalar(etiqueta),  # busca etiqueta
        _scalar(
            {
                "nome": "padrao",
                "formato": "A4",
                "logo_enabled": True,
                "mostrar_data_criacao": False,
            }
        ),  # template
    ]

    # Usa um QR image real para fpdf2 nao quebrar ao embutir PNG invalido
    real_qr = qrcode_service.gerar_imagem_qr("3SD|REQ-PDF-001|aaaaaaaaaaaaaaaa")
    etiqueta.qr_code_image = real_qr

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{prova.id}/etiqueta.pdf")

    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"].lower()
    assert "REQ-PDF-001" in resp.headers["content-disposition"]
    assert resp.content.startswith(b"%PDF-")


async def test_get_etiqueta_pdf_scoping_404(vendedor_matriz, mock_db):
    _setup(mock_db, user=vendedor_matriz)
    mock_db.execute.side_effect = [_detail_row_none()]
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{uuid.uuid4()}/etiqueta.pdf")
    assert resp.status_code == 404


async def test_get_etiqueta_pdf_etiqueta_ausente_404(
    admin_user, vendedor_matriz, mock_db
):
    """Edge case defensivo: prova existe mas etiqueta ausente."""
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(vendedor_id=vendedor_matriz.id)
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
        _scalar(None),  # etiqueta nao encontrada
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{prova.id}/etiqueta.pdf")
    assert resp.status_code == 404


async def test_get_etiqueta_pdf_no_auth_401(mock_db):
    _setup(mock_db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{uuid.uuid4()}/etiqueta.pdf")
    assert resp.status_code == 401


# ─── GET /{id}/qr-code.png ────────────────────────────────────────────


async def test_get_qr_code_png_happy(admin_user, vendedor_matriz, mock_db):
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(vendedor_id=vendedor_matriz.id)
    # PNG magic bytes + padding
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 200

    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
        _scalar(png_bytes),  # SELECT qr_code_image
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{prova.id}/qr-code.png")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert "inline" in resp.headers["content-disposition"].lower()
    assert "private" in resp.headers["cache-control"].lower()


async def test_get_qr_code_png_scoping_404(vendedor_matriz, mock_db):
    _setup(mock_db, user=vendedor_matriz)
    mock_db.execute.side_effect = [_detail_row_none()]
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{uuid.uuid4()}/qr-code.png")
    assert resp.status_code == 404


async def test_get_qr_code_png_etiqueta_ausente_404(
    admin_user, vendedor_matriz, mock_db
):
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(vendedor_id=vendedor_matriz.id)
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
        _scalar(None),
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{prova.id}/qr-code.png")
    assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════
# A1 + A2 (auditoria Wave 2 — Sessao 20) — robustez dos endpoints do C08
# ═══════════════════════════════════════════════════════════════════════
#
# Os 5 testes abaixo cobrem os fixes da auditoria senior do Componente 08:
#   A1 — try/except em 4 endpoints (detail, movimentacoes, etiqueta.pdf,
#        qr-code.png) que antes nao tinham protecao contra erros transitorios
#        de DB. Mapeiam para 502 em vez de 500 generico.
#   A2 — try/except dedicado ao `gerar_pdf` no handler de etiqueta.pdf,
#        separando falhas de rendering (422) de falhas de DB (502). Mesma
#        filosofia do ADR-054 (create_prova).


async def test_get_detail_db_error_returns_502(admin_user, mock_db):
    """A1 — erro transitorio no DB do `get_prova_detail` retorna 502."""
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = RuntimeError("connection reset by peer")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{uuid.uuid4()}")

    assert resp.status_code == 502
    assert "carregar prova" in resp.json()["detail"].lower()


async def test_get_movimentacoes_db_error_returns_502(admin_user, mock_db):
    """A1 — erro transitorio no DB do `list_movimentacoes` retorna 502."""
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = RuntimeError("pooler not reachable")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{uuid.uuid4()}/movimentacoes")

    assert resp.status_code == 502
    assert "movimentacoes" in resp.json()["detail"].lower()


async def test_get_etiqueta_pdf_db_error_returns_502(admin_user, mock_db):
    """A1 — erro transitorio no DB durante carga da etiqueta retorna 502."""
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = RuntimeError("db timeout")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{uuid.uuid4()}/etiqueta.pdf")

    assert resp.status_code == 502
    assert "carregar dados da etiqueta" in resp.json()["detail"].lower()


async def test_get_etiqueta_pdf_gerar_pdf_failure_returns_422(
    admin_user, vendedor_matriz, mock_db
):
    """A2 — falha de rendering em `gerar_pdf` retorna 422 com mensagem
    acionavel, separado do caminho 502 de erro de DB.

    Setup: todas as queries de DB retornam com sucesso (scoped, etiqueta,
    template). Mockamos `gerar_pdf` para lancar RuntimeError. O handler
    deve capturar no bloco dedicado ao rendering e retornar 422.
    """
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(vendedor_id=vendedor_matriz.id, nro_requerimento="REQ-PDF-ERR")
    etiqueta = Etiqueta(
        id=uuid.uuid4(),
        prova_id=prova.id,
        nome_prova=prova.nome,
        nro_requerimento=prova.nro_requerimento,
        vendedor_nome=vendedor_matriz.nome,
        qr_code_image=qrcode_service.gerar_imagem_qr("3SD|REQ-PDF-ERR|aaaaaaaaaaaaaaaa"),
        created_at=datetime.now(timezone.utc),
    )

    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
        _scalar(etiqueta),
        _scalar(DEFAULT_TEMPLATE),
    ]

    with patch(
        "app.api.v1.provas.gerar_pdf",
        side_effect=RuntimeError("Fontes DejaVu ausentes"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.get(f"{PREFIX}/{prova.id}/etiqueta.pdf")

    assert resp.status_code == 422
    detail = resp.json()["detail"].lower()
    assert "gerar etiqueta" in detail
    assert "dejavu" in detail  # propaga mensagem da exception


async def test_get_qr_code_png_db_error_returns_502(admin_user, mock_db):
    """A1 — erro transitorio no DB do `get_qr_code_png` retorna 502."""
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = RuntimeError("connection lost")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{uuid.uuid4()}/qr-code.png")

    assert resp.status_code == 502
    assert "qr code" in resp.json()["detail"].lower()


# ═══════════════════════════════════════════════════════════════════════
# POST /api/v1/provas/scan  — Componente 10 (Wave 3 Lote A sub-bloco A.3)
# ═══════════════════════════════════════════════════════════════════════
#
# Padrao de mock:
#   - O handler faz 1 query SELECT (`_carregar_prova_por_nro_req_com_scoping`)
#     + 1 audit via `log_audit` (que faz INSERT em audit_logs via db.add +
#     db.flush). O `db.commit()` explicito no final fecha a transacao.
#   - `mock_db.execute.side_effect = [_detail_row(...)]` entrega a prova.
#   - Para valida-lo com hash correto geramos um payload real via
#     `qrcode_service.gerar_payload_qr(nro_req, hash)` e passamos o mesmo
#     hash pra prova via `_make_prova_com_hash(...)` local.


def _make_prova_com_hash(
    *, nro_requerimento, qr_code_hash, vendedor_id=None,
    status_prova=StatusProvaEnum.CRIADA, rota=None,
):
    """Fabrica de ProvaDigital com controle do `qr_code_hash` (para testes
    de scan). `_make_prova` acima sempre grava `"a"*64` — aqui precisamos
    do hash real que foi usado para gerar o payload de teste.
    """
    now = datetime.now(timezone.utc)
    return ProvaDigital(
        id=uuid.uuid4(),
        nome="Prova Scan",
        nro_requerimento=nro_requerimento,
        cliente="Cliente Scan",
        vendedor_id=vendedor_id or uuid.uuid4(),
        imagem_url=f"provas/2026/04/{uuid.uuid4().hex}/arte.jpg",
        qr_code_hash=qr_code_hash,
        status=status_prova,
        rota=rota,
        ciclo_atual=1,
        motivo_cancelamento=None,
        created_at=now,
        updated_at=now,
    )


def _gerar_hash_e_payload(nro_req: str) -> tuple[str, str]:
    """Gera um (qr_code_hash, payload) consistente para usar nos testes.

    Usa um UUID arbitrario para o `prova_id` do HMAC — o que importa pro
    teste e que o hash seja estavel e que o payload bata com
    `validar_payload_qr` contra ele.
    """
    prova_uuid = uuid.uuid4()
    full_hash = qrcode_service.gerar_hash(prova_uuid, nro_req)
    payload = qrcode_service.gerar_payload_qr(nro_req, full_hash)
    return full_hash, payload


# ─── POST /scan: happy paths ─────────────────────────────────────────


async def test_scan_happy_vendedor_matriz_retorna_transicoes_corretas(
    vendedor_matriz, mock_db
):
    """Cenario principal: vendedor escaneia prova em CRIADA e recebe
    `[RETIRADA_PELO_VENDEDOR]` como transicoes permitidas."""
    _setup(mock_db, user=vendedor_matriz)
    nro_req = "REQ-SCAN-001"
    full_hash, payload = _gerar_hash_e_payload(nro_req)
    prova = _make_prova_com_hash(
        nro_requerimento=nro_req,
        qr_code_hash=full_hash,
        vendedor_id=vendedor_matriz.id,
        status_prova=StatusProvaEnum.CRIADA,
    )

    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"payload": payload})

    assert resp.status_code == 200, resp.json()
    data = resp.json()
    assert data["prova"]["nro_requerimento"] == nro_req
    assert data["prova"]["status"] == "CRIADA"
    assert data["transicoes_permitidas"] == ["RETIRADA_PELO_VENDEDOR"]
    assert data["motivo_obrigatorio_em"] == []
    # Audit via log_audit -> db.add + commit
    mock_db.add.assert_called()
    mock_db.commit.assert_awaited_once()


async def test_scan_vendedor_matriz_em_retirada_retorna_aprovada_e_reprovada(
    vendedor_matriz, mock_db
):
    """No estado RETIRADA_PELO_VENDEDOR, vendedor pode APROVAR ou REPROVAR.
    Reprovada exige motivo, entao aparece em `motivo_obrigatorio_em`."""
    _setup(mock_db, user=vendedor_matriz)
    full_hash, payload = _gerar_hash_e_payload("REQ-SCAN-R-01")
    prova = _make_prova_com_hash(
        nro_requerimento="REQ-SCAN-R-01",
        qr_code_hash=full_hash,
        vendedor_id=vendedor_matriz.id,
        status_prova=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
    )

    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"payload": payload})

    assert resp.status_code == 200
    data = resp.json()
    assert sorted(data["transicoes_permitidas"]) == [
        "APROVADA_PELO_VENDEDOR",
        "REPROVADA_PELO_VENDEDOR",
    ]
    assert data["motivo_obrigatorio_em"] == ["REPROVADA_PELO_VENDEDOR"]


async def test_scan_vendedor_matriz_em_aprovada_retorna_so_de_volta(
    vendedor_matriz, mock_db
):
    """MATRIZ em APROVADA → so pode DE_VOLTA_3STUDIO (RF-009).
    ENCAMINHADA_A_CLICHERIA e FILIAL-only — deve ser filtrada."""
    _setup(mock_db, user=vendedor_matriz)
    full_hash, payload = _gerar_hash_e_payload("REQ-SCAN-AM-01")
    prova = _make_prova_com_hash(
        nro_requerimento="REQ-SCAN-AM-01",
        qr_code_hash=full_hash,
        vendedor_id=vendedor_matriz.id,
        status_prova=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        rota=RotaEnum.PADRAO,
    )

    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"payload": payload})

    assert resp.status_code == 200
    assert resp.json()["transicoes_permitidas"] == ["DE_VOLTA_3STUDIO"]


async def test_scan_vendedor_filial_em_aprovada_retorna_so_encaminhada(
    vendedor_filial, mock_db
):
    """FILIAL em APROVADA → so pode ENCAMINHADA_A_CLICHERIA."""
    _setup(mock_db, user=vendedor_filial)
    full_hash, payload = _gerar_hash_e_payload("REQ-SCAN-AF-01")
    prova = _make_prova_com_hash(
        nro_requerimento="REQ-SCAN-AF-01",
        qr_code_hash=full_hash,
        vendedor_id=vendedor_filial.id,
        status_prova=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        rota=RotaEnum.DIRETA,
    )

    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_filial.nome, vendedor_filial.localizacao),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"payload": payload})

    assert resp.status_code == 200
    assert resp.json()["transicoes_permitidas"] == ["ENCAMINHADA_A_CLICHERIA"]


async def test_scan_estado_terminal_recebida_retorna_lista_vazia(
    admin_user, mock_db
):
    """Prova em RECEBIDA_PELA_CLICHERIA (terminal) → zero transicoes.
    O scan em si e permitido (admin ve tudo), so nao ha acoes para
    oferecer."""
    _setup(mock_db, admin=admin_user)
    full_hash, payload = _gerar_hash_e_payload("REQ-SCAN-T-01")
    prova = _make_prova_com_hash(
        nro_requerimento="REQ-SCAN-T-01",
        qr_code_hash=full_hash,
        status_prova=StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
    )

    mock_db.execute.side_effect = [
        _detail_row(prova, "Vendedor X", LocalizacaoEnum.MATRIZ),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"payload": payload})

    assert resp.status_code == 200
    assert resp.json()["transicoes_permitidas"] == []


async def test_scan_reprovada_para_criada_filtrada_gancho_c14(
    admin_user, mock_db
):
    """REPROVADA_PELO_VENDEDOR → CRIADA existe na state_machine (reinicio
    de ciclo, gancho C14) mas e FILTRADA do response do scan porque o
    endpoint POST /transicoes do Lote A rejeita CRIADA como destino."""
    _setup(mock_db, admin=admin_user)
    full_hash, payload = _gerar_hash_e_payload("REQ-SCAN-RE-01")
    prova = _make_prova_com_hash(
        nro_requerimento="REQ-SCAN-RE-01",
        qr_code_hash=full_hash,
        status_prova=StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
    )

    mock_db.execute.side_effect = [
        _detail_row(prova, "Vendedor X", LocalizacaoEnum.MATRIZ),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"payload": payload})

    assert resp.status_code == 200
    # CANCELADA e CRIADA ambos filtrados — lista vazia
    assert resp.json()["transicoes_permitidas"] == []


# ─── POST /scan: cenarios de rejeicao ───────────────────────────────


async def test_scan_payload_formato_invalido_retorna_422(admin_user, mock_db):
    """Payload sem prefixo `3SD|` e rejeitado pelo Pydantic."""
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"payload": "abc|123|xyz"})
    assert resp.status_code == 422


async def test_scan_payload_poucos_campos_retorna_422(admin_user, mock_db):
    """Payload com menos de 3 campos e rejeitado pelo Pydantic."""
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"payload": "3SD|REQ-001"})
    assert resp.status_code == 422


async def test_scan_payload_hash_tamanho_errado_retorna_422(admin_user, mock_db):
    """Hash truncado com tamanho diferente de 16 chars e rejeitado pelo Pydantic."""
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"payload": "3SD|REQ-001|abcdef"})
    assert resp.status_code == 422


async def test_scan_payload_nro_req_vazio_retorna_422(admin_user, mock_db):
    """Payload `3SD||xxxxxxxxxxxxxxxx` com nro_requerimento vazio e rejeitado."""
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/scan", json={"payload": "3SD|   |aaaaaaaaaaaaaaaa"}
        )
    assert resp.status_code == 422


async def test_scan_payload_so_whitespace_retorna_422(admin_user, mock_db):
    """Payload com so espacos (apos strip, vira vazio). Cobre branch
    `if not v` apos `v.strip()` no validator Pydantic."""
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"payload": "   "})
    assert resp.status_code == 422


async def test_scan_prova_nao_encontrada_retorna_404(admin_user, mock_db):
    """Payload valido mas `nro_requerimento` inexistente → 404."""
    _setup(mock_db, admin=admin_user)
    _, payload = _gerar_hash_e_payload("REQ-INEXISTENTE")

    mock_db.execute.side_effect = [_detail_row_none()]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"payload": payload})

    assert resp.status_code == 404
    assert "nao encontrada" in resp.json()["detail"].lower()
    # Nao chegou a chamar log_audit
    mock_db.commit.assert_not_awaited()


async def test_scan_hash_nao_bate_retorna_422(admin_user, mock_db):
    """Payload com `nro_requerimento` correto mas hash errado → 422.

    Cenario: alguem adulterou o QR Code impresso ou o payload do frontend
    e o hash truncado nao bate com o qr_code_hash armazenado. A validacao
    e constant-time via `validar_payload_qr`.
    """
    _setup(mock_db, admin=admin_user)
    nro_req = "REQ-SCAN-BAD"
    # Gera o payload com um hash — mas a prova no banco tem hash diferente
    _hash_correto, payload = _gerar_hash_e_payload(nro_req)
    prova = _make_prova_com_hash(
        nro_requerimento=nro_req,
        qr_code_hash="f" * 64,  # hash armazenado DIFERENTE
        status_prova=StatusProvaEnum.CRIADA,
    )

    mock_db.execute.side_effect = [
        _detail_row(prova, "Vendedor X", LocalizacaoEnum.MATRIZ),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"payload": payload})

    assert resp.status_code == 422
    assert "nao corresponde" in resp.json()["detail"].lower()
    # Nao grava audit em caso de hash invalido
    mock_db.commit.assert_not_awaited()


async def test_scan_vendedor_escapando_outra_prova_retorna_404(
    vendedor_matriz, mock_db
):
    """Vendedor escaneando prova de outro vendedor → 404 por scoping.

    O `_scoping_filter(vendedor)` adiciona `vendedor_id == user.id` na
    clausula WHERE, entao o SELECT retorna None mesmo sendo uma prova
    valida e com hash batendo. O handler nao distingue ausencia de
    escondida-por-scoping — ambos viram 404 (ADR-049).
    """
    _setup(mock_db, user=vendedor_matriz)
    _, payload = _gerar_hash_e_payload("REQ-SCAN-OUTRO")

    # O scoping impede de carregar — simulamos com _detail_row_none.
    mock_db.execute.side_effect = [_detail_row_none()]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"payload": payload})

    assert resp.status_code == 404


async def test_scan_motorista_fora_status_retorna_404(mock_db):
    """Motorista escaneando prova em CRIADA → scoping esconde (so ve
    COM_MOTORISTA). 404."""
    motorista = make_user(
        setor=SetorEnum.MOTORISTA, localizacao=None, nome="Motorista Test"
    )
    _setup(mock_db, user=motorista)
    _, payload = _gerar_hash_e_payload("REQ-SCAN-FORA-M")

    mock_db.execute.side_effect = [_detail_row_none()]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"payload": payload})

    assert resp.status_code == 404


async def test_scan_db_error_retorna_502(admin_user, mock_db):
    """Erro transitorio no SELECT retorna 502 acionavel (padrao ADR-074)."""
    _setup(mock_db, admin=admin_user)
    _, payload = _gerar_hash_e_payload("REQ-SCAN-DB")
    mock_db.execute.side_effect = RuntimeError("connection lost")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"payload": payload})

    assert resp.status_code == 502
    assert "carregar prova" in resp.json()["detail"].lower()


async def test_scan_audit_commit_failure_retorna_502(admin_user, mock_db):
    """Erro no commit do audit_log retorna 502 + rollback."""
    _setup(mock_db, admin=admin_user)
    nro_req = "REQ-SCAN-COM"
    full_hash, payload = _gerar_hash_e_payload(nro_req)
    prova = _make_prova_com_hash(
        nro_requerimento=nro_req,
        qr_code_hash=full_hash,
        status_prova=StatusProvaEnum.CRIADA,
    )

    mock_db.execute.side_effect = [
        _detail_row(prova, "Vendedor X", LocalizacaoEnum.MATRIZ),
    ]
    mock_db.commit.side_effect = RuntimeError("commit failure")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"payload": payload})

    assert resp.status_code == 502
    assert "registrar scan" in resp.json()["detail"].lower()
    mock_db.rollback.assert_awaited()


async def test_scan_sem_auth_retorna_401(mock_db):
    """Scan sem token → 401 (herdado de `get_current_user`)."""
    _setup(mock_db)
    _, payload = _gerar_hash_e_payload("REQ-NO-AUTH")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"payload": payload})

    assert resp.status_code == 401


async def test_scan_vendedor_em_prova_com_motorista_retorna_lista_vazia(
    vendedor_matriz, mock_db
):
    """Vendedor escaneando sua propria prova em COM_MOTORISTA (cenario
    real: prova do vendedor ja virou responsabilidade do motorista, mas
    ele ainda consegue escanear por scoping de vendedor_id).

    Todos os destinos da state_machine para COM_MOTORISTA exigem ator
    MOTORISTA (ou cancelamento pelo STUDIO — filtrado). O vendedor nao
    e MOTORISTA, entao `validar_transicao` levanta `AtorNaoAutorizadoError`
    e o destino candidato e filtrado. Resultado: `transicoes_permitidas=[]`.

    Cobre o except `(TransicaoInvalidaError, AtorNaoAutorizadoError)`
    de `_computar_transicoes_permitidas`.
    """
    _setup(mock_db, user=vendedor_matriz)
    full_hash, payload = _gerar_hash_e_payload("REQ-SCAN-CM-01")
    prova = _make_prova_com_hash(
        nro_requerimento="REQ-SCAN-CM-01",
        qr_code_hash=full_hash,
        vendedor_id=vendedor_matriz.id,  # prova do proprio vendedor
        status_prova=StatusProvaEnum.COM_MOTORISTA,
        rota=RotaEnum.PADRAO,
    )

    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"payload": payload})

    assert resp.status_code == 200
    # Unica transicao saindo de COM_MOTORISTA (exceto CANCELADA, que
    # filtramos) e ENVIADA_PARA_CLICHERIA por MOTORISTA — vendedor nao
    # pode executar.
    assert resp.json()["transicoes_permitidas"] == []


async def test_scan_audit_log_contem_acao_e_status_atual(
    vendedor_matriz, mock_db
):
    """Verifica que o audit_log e chamado com `acao="escanear_prova"` e
    inclui `nro_requerimento` + `status_atual` + `transicoes_permitidas`
    em `detalhes_json`."""
    _setup(mock_db, user=vendedor_matriz)
    nro_req = "REQ-SCAN-AU-01"
    full_hash, payload = _gerar_hash_e_payload(nro_req)
    prova = _make_prova_com_hash(
        nro_requerimento=nro_req,
        qr_code_hash=full_hash,
        vendedor_id=vendedor_matriz.id,
        status_prova=StatusProvaEnum.CRIADA,
    )

    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]

    with patch(
        "app.api.v1.provas.log_audit", new_callable=AsyncMock
    ) as mock_log:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(f"{PREFIX}/scan", json={"payload": payload})

    assert resp.status_code == 200
    mock_log.assert_awaited_once()
    kwargs = mock_log.call_args.kwargs
    assert kwargs["acao"] == "escanear_prova"
    assert kwargs["usuario_id"] == vendedor_matriz.id
    assert kwargs["prova_id"] == prova.id
    assert kwargs["detalhes"]["nro_requerimento"] == nro_req
    assert kwargs["detalhes"]["status_atual"] == "CRIADA"
    assert kwargs["detalhes"]["transicoes_permitidas"] == [
        "RETIRADA_PELO_VENDEDOR"
    ]


# ═══════════════════════════════════════════════════════════════════════
# POST /api/v1/provas/{prova_id}/transicoes  — Componente 11 (sub-bloco A.4)
# ═══════════════════════════════════════════════════════════════════════
#
# Padrao de mock:
#   - 1 execute = `_carregar_prova_com_scoping` (com lock=True interno,
#     mas o mock nao se importa com isso — ve apenas um `execute` call).
#   - `executar_transicao` e importada em `app.api.v1.provas` — o real e
#     chamado, entao precisamos mockar `db.add` + `db.flush` (ja sao
#     MagicMock/AsyncMock no `mock_db` fixture) + verificar efeitos em
#     `prova.status` etc.
#   - Para testes de tracing especifico (audit, exceptions), patchamos
#     `app.services.state_machine.log_audit` porque `state_machine`
#     importa `log_audit` la.


# Assinatura de teste: PNG valido minimo em base64.
# Geramos uma vez em runtime para garantir validade + usar um valor realista.
ASSINATURA_B64 = base64.b64encode(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rfake-signature-data-not-real-png"
).decode("ascii")


def _transicao_body(
    *,
    status_novo: str,
    motivo_reprovacao: str | None = None,
    assinatura_base64: str | None = None,
) -> dict:
    """Helper para construir um payload valido de TransicaoRequest."""
    body = {
        "status_novo": status_novo,
        "assinatura_base64": assinatura_base64 or ASSINATURA_B64,
    }
    if motivo_reprovacao is not None:
        body["motivo_reprovacao"] = motivo_reprovacao
    return body


# ─── POST /{id}/transicoes: happy paths (9 HUs do Lote A) ─────────────


async def test_transicao_happy_criada_para_retirada_vendedor_matriz(
    vendedor_matriz, mock_db
):
    """US-002 — vendedor MATRIZ escaneia CRIADA e retira. Verifica
    efeitos: status atualizado, movimentacao criada, response 201."""
    _setup(mock_db, user=vendedor_matriz)
    prova = _make_prova(
        vendedor_id=vendedor_matriz.id, status_prova=StatusProvaEnum.CRIADA
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/transicoes",
            json=_transicao_body(status_novo="RETIRADA_PELO_VENDEDOR"),
        )

    assert resp.status_code == 201, resp.json()
    data = resp.json()
    assert data["prova"]["status"] == "RETIRADA_PELO_VENDEDOR"
    assert data["prova"]["rota"] is None  # ainda sem rota (so na aprovacao)
    assert data["movimentacao"]["status_anterior"] == "CRIADA"
    assert data["movimentacao"]["status_novo"] == "RETIRADA_PELO_VENDEDOR"
    assert data["movimentacao"]["ciclo"] == 1
    assert data["movimentacao"]["rota_no_momento"] is None
    assert data["movimentacao"]["motivo_reprovacao"] is None
    assert data["movimentacao"]["usuario_nome"] == vendedor_matriz.nome
    assert data["movimentacao"]["usuario_setor"] == "VENDEDOR"
    # In-memory: o objeto prova teve seu status mutado
    assert prova.status == StatusProvaEnum.RETIRADA_PELO_VENDEDOR
    mock_db.commit.assert_awaited_once()


async def test_transicao_happy_retirada_para_aprovada_matriz_persiste_rota_padrao(
    vendedor_matriz, mock_db
):
    """US-003 — vendedor MATRIZ aprova prova retirada. Rota PADRAO
    persiste na `prova.rota` (RN-007)."""
    _setup(mock_db, user=vendedor_matriz)
    prova = _make_prova(
        vendedor_id=vendedor_matriz.id,
        status_prova=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/transicoes",
            json=_transicao_body(status_novo="APROVADA_PELO_VENDEDOR"),
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["prova"]["rota"] == "PADRAO"
    assert data["movimentacao"]["rota_no_momento"] == "PADRAO"
    assert prova.rota == RotaEnum.PADRAO


async def test_transicao_happy_retirada_para_aprovada_filial_persiste_rota_direta(
    vendedor_filial, mock_db
):
    """US-003 (filial) — vendedor FILIAL aprova prova retirada. Rota
    DIRETA persiste."""
    _setup(mock_db, user=vendedor_filial)
    prova = _make_prova(
        vendedor_id=vendedor_filial.id,
        status_prova=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_filial.nome, vendedor_filial.localizacao),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/transicoes",
            json=_transicao_body(status_novo="APROVADA_PELO_VENDEDOR"),
        )

    assert resp.status_code == 201
    assert resp.json()["prova"]["rota"] == "DIRETA"
    assert prova.rota == RotaEnum.DIRETA


async def test_transicao_happy_reprovacao_com_motivo(vendedor_matriz, mock_db):
    """US-004 — reprovacao exige motivo (RF-007). Valor eh normalizado
    (strip) e propagado para a movimentacao."""
    _setup(mock_db, user=vendedor_matriz)
    prova = _make_prova(
        vendedor_id=vendedor_matriz.id,
        status_prova=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/transicoes",
            json=_transicao_body(
                status_novo="REPROVADA_PELO_VENDEDOR",
                motivo_reprovacao="  Cor do logo errada  ",
            ),
        )

    assert resp.status_code == 201
    assert resp.json()["movimentacao"]["motivo_reprovacao"] == "Cor do logo errada"
    assert prova.status == StatusProvaEnum.REPROVADA_PELO_VENDEDOR


async def test_transicao_happy_aprovada_matriz_para_de_volta_3studio(
    vendedor_matriz, mock_db
):
    """US-005 — vendedor MATRIZ devolve a 3Studio (rota padrao)."""
    _setup(mock_db, user=vendedor_matriz)
    prova = _make_prova(
        vendedor_id=vendedor_matriz.id,
        status_prova=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        rota=RotaEnum.PADRAO,
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/transicoes",
            json=_transicao_body(status_novo="DE_VOLTA_3STUDIO"),
        )

    assert resp.status_code == 201
    assert resp.json()["prova"]["status"] == "DE_VOLTA_3STUDIO"


async def test_transicao_happy_aprovada_filial_para_encaminhada_clicheria(
    vendedor_filial, mock_db
):
    """US-006 — vendedor FILIAL encaminha direto a clicheria."""
    _setup(mock_db, user=vendedor_filial)
    prova = _make_prova(
        vendedor_id=vendedor_filial.id,
        status_prova=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        rota=RotaEnum.DIRETA,
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_filial.nome, vendedor_filial.localizacao),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/transicoes",
            json=_transicao_body(status_novo="ENCAMINHADA_A_CLICHERIA"),
        )

    assert resp.status_code == 201
    assert resp.json()["prova"]["status"] == "ENCAMINHADA_A_CLICHERIA"


async def test_transicao_happy_de_volta_para_com_motorista_studio(mock_db):
    """US-007 — 3Studio recebe devolucao e envia ao motorista."""
    studio = make_user(
        setor=SetorEnum.STUDIO, localizacao=None, nome="Studio Ops"
    )
    _setup(mock_db, user=studio)
    prova = _make_prova(
        status_prova=StatusProvaEnum.DE_VOLTA_3STUDIO, rota=RotaEnum.PADRAO
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, "Vendedor X", LocalizacaoEnum.MATRIZ),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/transicoes",
            json=_transicao_body(status_novo="COM_MOTORISTA"),
        )

    assert resp.status_code == 201
    assert resp.json()["prova"]["status"] == "COM_MOTORISTA"


async def test_transicao_happy_com_motorista_para_enviada_motorista(mock_db):
    """US-008 — motorista confirma transporte."""
    motorista = make_user(
        setor=SetorEnum.MOTORISTA, localizacao=None, nome="Motorista Test"
    )
    _setup(mock_db, user=motorista)
    prova = _make_prova(
        status_prova=StatusProvaEnum.COM_MOTORISTA, rota=RotaEnum.PADRAO
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, "Vendedor X", LocalizacaoEnum.MATRIZ),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/transicoes",
            json=_transicao_body(status_novo="ENVIADA_PARA_CLICHERIA"),
        )

    assert resp.status_code == 201
    assert resp.json()["prova"]["status"] == "ENVIADA_PARA_CLICHERIA"


async def test_transicao_happy_enviada_para_recebida_clicheria(mock_db):
    """US-009 (rota padrao) — clicheria recebe via motorista."""
    clicheria = make_user(
        setor=SetorEnum.CLICHERIA, localizacao=None, nome="Clicheria Test"
    )
    _setup(mock_db, user=clicheria)
    prova = _make_prova(
        status_prova=StatusProvaEnum.ENVIADA_PARA_CLICHERIA,
        rota=RotaEnum.PADRAO,
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, "Vendedor X", LocalizacaoEnum.MATRIZ),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/transicoes",
            json=_transicao_body(status_novo="RECEBIDA_PELA_CLICHERIA"),
        )

    assert resp.status_code == 201
    assert resp.json()["prova"]["status"] == "RECEBIDA_PELA_CLICHERIA"


async def test_transicao_happy_encaminhada_para_recebida_clicheria(mock_db):
    """US-009 (rota direta) — clicheria recebe pela filial."""
    clicheria = make_user(
        setor=SetorEnum.CLICHERIA, localizacao=None, nome="Clicheria Test"
    )
    _setup(mock_db, user=clicheria)
    prova = _make_prova(
        status_prova=StatusProvaEnum.ENCAMINHADA_A_CLICHERIA,
        rota=RotaEnum.DIRETA,
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, "Vendedor X", LocalizacaoEnum.FILIAL),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/transicoes",
            json=_transicao_body(status_novo="RECEBIDA_PELA_CLICHERIA"),
        )

    assert resp.status_code == 201
    assert resp.json()["prova"]["status"] == "RECEBIDA_PELA_CLICHERIA"


# ─── POST /{id}/transicoes: validacoes Pydantic (ganchos C13/C14) ─────


async def test_transicao_rejeita_cancelada_como_destino_422(
    admin_user, mock_db
):
    """CANCELADA rejeitada pelo validator — gancho C13."""
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{uuid.uuid4()}/transicoes",
            json=_transicao_body(status_novo="CANCELADA"),
        )
    assert resp.status_code == 422


async def test_transicao_rejeita_criada_como_destino_422(admin_user, mock_db):
    """CRIADA rejeitada pelo validator — gancho C14."""
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{uuid.uuid4()}/transicoes",
            json=_transicao_body(status_novo="CRIADA"),
        )
    assert resp.status_code == 422


async def test_transicao_assinatura_vazia_422(admin_user, mock_db):
    """String vazia rejeitada pelo min_length=1 do Pydantic."""
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{uuid.uuid4()}/transicoes",
            json={
                "status_novo": "RETIRADA_PELO_VENDEDOR",
                "assinatura_base64": "",
            },
        )
    assert resp.status_code == 422


async def test_transicao_assinatura_base64_invalido_422(
    vendedor_matriz, mock_db
):
    """Input com caracteres que nao sao base64 validos → 422 do handler
    (nao do Pydantic — Pydantic aceita qualquer string nao vazia)."""
    _setup(mock_db, user=vendedor_matriz)
    prova = _make_prova(
        vendedor_id=vendedor_matriz.id, status_prova=StatusProvaEnum.CRIADA
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/transicoes",
            json={
                "status_novo": "RETIRADA_PELO_VENDEDOR",
                "assinatura_base64": "!!!not-base64!!!",
            },
        )

    assert resp.status_code == 422
    assert "base64 invalida" in resp.json()["detail"].lower()
    # db.execute nem chega a ser chamado porque o decode falha antes
    mock_db.execute.assert_not_called()


async def test_transicao_assinatura_muito_grande_422(admin_user, mock_db):
    """max_length=700000 rejeita payloads maiores."""
    _setup(mock_db, admin=admin_user)
    big_b64 = "A" * 700_001  # acima do limite
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{uuid.uuid4()}/transicoes",
            json={
                "status_novo": "RETIRADA_PELO_VENDEDOR",
                "assinatura_base64": big_b64,
            },
        )
    assert resp.status_code == 422


# ─── POST /{id}/transicoes: rejeicoes do handler/dominio ──────────────


async def test_transicao_reprovacao_sem_motivo_422(vendedor_matriz, mock_db):
    """Reprovacao sem motivo → state_machine levanta ValueError → 422."""
    _setup(mock_db, user=vendedor_matriz)
    prova = _make_prova(
        vendedor_id=vendedor_matriz.id,
        status_prova=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/transicoes",
            json=_transicao_body(
                status_novo="REPROVADA_PELO_VENDEDOR",
                motivo_reprovacao=None,
            ),
        )

    assert resp.status_code == 422
    assert "motivo da reprovacao" in resp.json()["detail"].lower()
    mock_db.rollback.assert_awaited()


async def test_transicao_reprovacao_motivo_whitespace_422(
    vendedor_matriz, mock_db
):
    """Motivo so-whitespace → Pydantic normaliza para None → state_machine
    levanta ValueError → 422."""
    _setup(mock_db, user=vendedor_matriz)
    prova = _make_prova(
        vendedor_id=vendedor_matriz.id,
        status_prova=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/transicoes",
            json=_transicao_body(
                status_novo="REPROVADA_PELO_VENDEDOR",
                motivo_reprovacao="   \t  ",
            ),
        )

    assert resp.status_code == 422


async def test_transicao_ator_errado_422(vendedor_matriz, mock_db):
    """Vendedor tentando executar transicao de MOTORISTA → 422."""
    _setup(mock_db, user=vendedor_matriz)
    prova = _make_prova(
        vendedor_id=vendedor_matriz.id,
        status_prova=StatusProvaEnum.COM_MOTORISTA,
        rota=RotaEnum.PADRAO,
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/transicoes",
            json=_transicao_body(status_novo="ENVIADA_PARA_CLICHERIA"),
        )

    assert resp.status_code == 422
    assert "nao autorizado" in resp.json()["detail"].lower()
    mock_db.rollback.assert_awaited()


async def test_transicao_aprovada_matriz_tentando_encaminhada_422(
    vendedor_matriz, mock_db
):
    """RF-009 — MATRIZ tentando rota direta (ENCAMINHADA) → 422 pelo
    AtorNaoAutorizadoError da regra extra de localizacao."""
    _setup(mock_db, user=vendedor_matriz)
    prova = _make_prova(
        vendedor_id=vendedor_matriz.id,
        status_prova=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        rota=RotaEnum.PADRAO,
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/transicoes",
            json=_transicao_body(status_novo="ENCAMINHADA_A_CLICHERIA"),
        )

    assert resp.status_code == 422
    assert "filial" in resp.json()["detail"].lower()


async def test_transicao_aprovada_filial_tentando_de_volta_422(
    vendedor_filial, mock_db
):
    """RF-009 — FILIAL tentando rota padrao (DE_VOLTA) → 422."""
    _setup(mock_db, user=vendedor_filial)
    prova = _make_prova(
        vendedor_id=vendedor_filial.id,
        status_prova=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        rota=RotaEnum.DIRETA,
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_filial.nome, vendedor_filial.localizacao),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/transicoes",
            json=_transicao_body(status_novo="DE_VOLTA_3STUDIO"),
        )

    assert resp.status_code == 422
    assert "matriz" in resp.json()["detail"].lower()


async def test_transicao_admin_sem_localizacao_aprovando_422(
    admin_user, mock_db
):
    """Admin STUDIO tentando aprovar diretamente → RotaIndeterminavelError
    → 422. RN-007: rota precisa da localizacao do vendedor, mas o admin
    nao e vendedor."""
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(
        status_prova=StatusProvaEnum.RETIRADA_PELO_VENDEDOR
    )
    mock_db.execute.side_effect = [
        _detail_row(
            prova, "Admin Master", None, vendedor_setor=SetorEnum.VENDEDOR
        ),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/transicoes",
            json=_transicao_body(status_novo="APROVADA_PELO_VENDEDOR"),
        )

    assert resp.status_code == 422
    assert "rota" in resp.json()["detail"].lower()


async def test_transicao_ilegal_pos_lock_retorna_409(admin_user, mock_db):
    """ADR-084: TransicaoInvalidaError apos FOR UPDATE → 409 + mensagem.

    Cenario: admin tenta forcar transicao ilegal (CRIADA → COM_MOTORISTA).
    A state_machine levanta TransicaoInvalidaError. O handler traduz
    para 409 assumindo "status mudou". Na pratica pode tambem ser cliente
    malicioso — em ambos os casos, o cliente deve recarregar o scan.
    """
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(status_prova=StatusProvaEnum.CRIADA)
    mock_db.execute.side_effect = [
        _detail_row(prova, "Vendedor X", LocalizacaoEnum.MATRIZ),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/transicoes",
            json=_transicao_body(status_novo="COM_MOTORISTA"),
        )

    assert resp.status_code == 409
    detail = resp.json()["detail"].lower()
    assert "mudou" in detail
    assert "recarregue" in detail
    mock_db.rollback.assert_awaited()


async def test_transicao_estado_terminal_recebida_retorna_409(
    admin_user, mock_db
):
    """Prova em RECEBIDA (terminal) nao aceita transicao →
    TransicaoInvalidaError → 409."""
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(
        status_prova=StatusProvaEnum.RECEBIDA_PELA_CLICHERIA
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, "Vendedor X", LocalizacaoEnum.MATRIZ),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/transicoes",
            json=_transicao_body(status_novo="ENVIADA_PARA_CLICHERIA"),
        )

    assert resp.status_code == 409


async def test_transicao_prova_inexistente_404(admin_user, mock_db):
    """UUID valido mas prova nao encontrada → 404."""
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [_detail_row_none()]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{uuid.uuid4()}/transicoes",
            json=_transicao_body(status_novo="RETIRADA_PELO_VENDEDOR"),
        )

    assert resp.status_code == 404


async def test_transicao_uuid_invalido_404(admin_user, mock_db):
    """Path param nao-UUID → 404 via `parse_prova_id` (C08 M3 pattern)."""
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/abc-not-uuid/transicoes",
            json=_transicao_body(status_novo="RETIRADA_PELO_VENDEDOR"),
        )
    assert resp.status_code == 404


async def test_transicao_scoping_esconde_prova_404(vendedor_matriz, mock_db):
    """Vendedor tentando transitar prova de outro vendedor → scoping
    devolve None → 404."""
    _setup(mock_db, user=vendedor_matriz)
    mock_db.execute.side_effect = [_detail_row_none()]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{uuid.uuid4()}/transicoes",
            json=_transicao_body(status_novo="RETIRADA_PELO_VENDEDOR"),
        )

    assert resp.status_code == 404


async def test_transicao_db_error_carregamento_502(admin_user, mock_db):
    """Erro transitorio no SELECT → 502 (padrao ADR-074)."""
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = RuntimeError("connection lost")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{uuid.uuid4()}/transicoes",
            json=_transicao_body(status_novo="RETIRADA_PELO_VENDEDOR"),
        )

    assert resp.status_code == 502
    assert "carregar prova" in resp.json()["detail"].lower()


async def test_transicao_db_error_commit_502(vendedor_matriz, mock_db):
    """Erro transitorio no commit → 502 + rollback."""
    _setup(mock_db, user=vendedor_matriz)
    prova = _make_prova(
        vendedor_id=vendedor_matriz.id, status_prova=StatusProvaEnum.CRIADA
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]
    mock_db.commit.side_effect = RuntimeError("commit failure")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/transicoes",
            json=_transicao_body(status_novo="RETIRADA_PELO_VENDEDOR"),
        )

    assert resp.status_code == 502
    assert "persistir transicao" in resp.json()["detail"].lower()
    mock_db.rollback.assert_awaited()


async def test_transicao_erro_inesperado_em_executar_502(
    vendedor_matriz, mock_db
):
    """Exception nao-dominio dentro de `executar_transicao` (ex: falha
    de log_audit) → 502 + rollback."""
    _setup(mock_db, user=vendedor_matriz)
    prova = _make_prova(
        vendedor_id=vendedor_matriz.id, status_prova=StatusProvaEnum.CRIADA
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]

    # Patch log_audit (importado dentro do modulo state_machine) para falhar
    with patch(
        "app.services.state_machine.log_audit",
        new=AsyncMock(side_effect=RuntimeError("audit failure")),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(
                f"{PREFIX}/{prova.id}/transicoes",
                json=_transicao_body(status_novo="RETIRADA_PELO_VENDEDOR"),
            )

    assert resp.status_code == 502
    assert "executar transicao" in resp.json()["detail"].lower()
    mock_db.rollback.assert_awaited()


async def test_transicao_sem_auth_retorna_401(mock_db):
    """Transicao sem token → 401."""
    _setup(mock_db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{uuid.uuid4()}/transicoes",
            json=_transicao_body(status_novo="RETIRADA_PELO_VENDEDOR"),
        )
    assert resp.status_code == 401


async def test_transicao_admin_bypass_setor(admin_user, mock_db):
    """Admin bypassa validacao de setor — pode executar qualquer
    transicao valida. Mesmo padrao do sub-bloco A.1."""
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(
        status_prova=StatusProvaEnum.COM_MOTORISTA, rota=RotaEnum.PADRAO
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, "Vendedor X", LocalizacaoEnum.MATRIZ),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/transicoes",
            json=_transicao_body(status_novo="ENVIADA_PARA_CLICHERIA"),
        )

    assert resp.status_code == 201


async def test_transicao_payload_sem_status_novo_422(admin_user, mock_db):
    """Request sem `status_novo` → 422 do Pydantic (campo obrigatorio)."""
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{uuid.uuid4()}/transicoes",
            json={"assinatura_base64": ASSINATURA_B64},
        )
    assert resp.status_code == 422


async def test_transicao_status_novo_enum_invalido_422(admin_user, mock_db):
    """Valor fora do StatusProvaEnum → 422."""
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{uuid.uuid4()}/transicoes",
            json={
                "status_novo": "ESTADO_INVENTADO",
                "assinatura_base64": ASSINATURA_B64,
            },
        )
    assert resp.status_code == 422


# ─── Unit tests / defensive paths (cobertura 100% do A.4) ─────────────


async def test_decode_assinatura_vazia_apos_decode_raise_422():
    """Unit test do helper `_decode_assinatura`. Cenario: base64 que
    decodifica para zero bytes (ex: string vazia, normalmente bloqueada
    pelo Pydantic `min_length=1`, mas o helper defende defensivamente).

    Cobre as linhas 1580-1583 de `provas.py`.
    """
    from fastapi import HTTPException as _HTTPException

    from app.api.v1.provas import _decode_assinatura

    try:
        _decode_assinatura("")  # base64 vazio decodifica para b""
    except _HTTPException as exc:
        assert exc.status_code == 422
        assert "vazia apos decode" in exc.detail.lower()
    else:
        raise AssertionError("_decode_assinatura nao levantou HTTPException")


async def test_transicao_httpexception_no_carregamento_propaga(
    admin_user, mock_db
):
    """Defensive: se `_carregar_prova_com_scoping` levantar HTTPException
    diretamente (hipotetico no futuro), o handler propaga o status
    original em vez de virar 502.

    Cobre o `except HTTPException: raise` pos-carregamento (linhas 1618-1619).
    """
    from fastapi import HTTPException as _HTTPException

    _setup(mock_db, admin=admin_user)

    with patch(
        "app.api.v1.provas._carregar_prova_com_scoping",
        side_effect=_HTTPException(status_code=418, detail="I am a teapot"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(
                f"{PREFIX}/{uuid.uuid4()}/transicoes",
                json=_transicao_body(status_novo="RETIRADA_PELO_VENDEDOR"),
            )

    assert resp.status_code == 418
    assert resp.json()["detail"] == "I am a teapot"


async def test_transicao_httpexception_em_executar_propaga(
    vendedor_matriz, mock_db
):
    """Defensive: se `executar_transicao` levantar HTTPException, o
    handler propaga em vez de virar 502.

    Cobre o `except HTTPException: raise` pos-executar_transicao
    (linhas 1691-1694).
    """
    from fastapi import HTTPException as _HTTPException

    _setup(mock_db, user=vendedor_matriz)
    prova = _make_prova(
        vendedor_id=vendedor_matriz.id, status_prova=StatusProvaEnum.CRIADA
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]

    with patch(
        "app.api.v1.provas.executar_transicao",
        side_effect=_HTTPException(status_code=418, detail="I am a teapot"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(
                f"{PREFIX}/{prova.id}/transicoes",
                json=_transicao_body(status_novo="RETIRADA_PELO_VENDEDOR"),
            )

    assert resp.status_code == 418


def test_transicao_request_strip_motivo_aceita_none_explicito():
    """Unit test do validator `_strip_motivo` do TransicaoRequest.

    Cobre a linha `return None` (schemas/prova.py:400) que e exercitada
    quando o campo `motivo_reprovacao` vem explicitamente como `None`.
    """
    from app.domain.schemas.prova import TransicaoRequest

    req = TransicaoRequest(
        status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        assinatura_base64="QUFBQQ==",  # "AAAA" em base64
        motivo_reprovacao=None,
    )
    assert req.motivo_reprovacao is None


# ═══════════════════════════════════════════════════════════════════════
# POST /{id}/cancelar — Componente 13 (Wave 3 Lote C)
# ═══════════════════════════════════════════════════════════════════════


async def test_cancelar_happy_prova_criada(admin_user, mock_db):
    """C13 — admin cancela prova em CRIADA. Motivo gravado, status=CANCELADA."""
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(vendedor_id=uuid.uuid4(), status_prova=StatusProvaEnum.CRIADA)
    mock_db.execute.side_effect = [
        _detail_row(prova, "Vendedor Teste", LocalizacaoEnum.MATRIZ),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/cancelar",
            json={"motivo_cancelamento": "Prova duplicada"},
        )

    assert resp.status_code == 200, resp.json()
    data = resp.json()
    assert data["prova"]["status"] == "CANCELADA"
    assert data["prova"]["motivo_cancelamento"] == "Prova duplicada"
    assert data["movimentacao"]["status_anterior"] == "CRIADA"
    assert data["movimentacao"]["status_novo"] == "CANCELADA"
    assert prova.status == StatusProvaEnum.CANCELADA
    mock_db.commit.assert_awaited_once()


async def test_cancelar_happy_prova_retirada(admin_user, mock_db):
    """C13 — cancelar prova em RETIRADA_PELO_VENDEDOR (estado ativo)."""
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(status_prova=StatusProvaEnum.RETIRADA_PELO_VENDEDOR)
    mock_db.execute.side_effect = [
        _detail_row(prova, "Vendedor X", LocalizacaoEnum.FILIAL),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/cancelar",
            json={"motivo_cancelamento": "Solicitacao do cliente"},
        )

    assert resp.status_code == 200
    assert resp.json()["prova"]["status"] == "CANCELADA"
    assert resp.json()["movimentacao"]["status_anterior"] == "RETIRADA_PELO_VENDEDOR"


async def test_cancelar_happy_prova_com_motorista(admin_user, mock_db):
    """C13 — cancelar prova em COM_MOTORISTA."""
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(status_prova=StatusProvaEnum.COM_MOTORISTA, rota=RotaEnum.PADRAO)
    mock_db.execute.side_effect = [
        _detail_row(prova, "V", LocalizacaoEnum.MATRIZ),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/cancelar",
            json={"motivo_cancelamento": "Erro de cadastro"},
        )

    assert resp.status_code == 200
    assert resp.json()["prova"]["status"] == "CANCELADA"


async def test_cancelar_rejeita_motivo_vazio(admin_user, mock_db):
    """C13 — motivo vazio retorna 422 (Pydantic min_length=1)."""
    _setup(mock_db, admin=admin_user)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{uuid.uuid4()}/cancelar",
            json={"motivo_cancelamento": ""},
        )

    assert resp.status_code == 422


async def test_cancelar_rejeita_motivo_somente_espacos(admin_user, mock_db):
    """C13 — motivo com apenas espacos retorna 422."""
    _setup(mock_db, admin=admin_user)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{uuid.uuid4()}/cancelar",
            json={"motivo_cancelamento": "   "},
        )

    assert resp.status_code == 422


async def test_cancelar_rejeita_prova_ja_cancelada(admin_user, mock_db):
    """C13 — prova ja CANCELADA retorna 409."""
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(status_prova=StatusProvaEnum.CANCELADA)
    mock_db.execute.side_effect = [
        _detail_row(prova, "V", LocalizacaoEnum.MATRIZ),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/cancelar",
            json={"motivo_cancelamento": "Tentativa dupla"},
        )

    assert resp.status_code == 409
    assert "nao pode ser cancelada" in resp.json()["detail"]


async def test_cancelar_rejeita_prova_recebida_terminal(admin_user, mock_db):
    """C13 — RECEBIDA_PELA_CLICHERIA e terminal, retorna 409."""
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(status_prova=StatusProvaEnum.RECEBIDA_PELA_CLICHERIA)
    mock_db.execute.side_effect = [
        _detail_row(prova, "V", LocalizacaoEnum.MATRIZ),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/cancelar",
            json={"motivo_cancelamento": "Tentativa terminal"},
        )

    assert resp.status_code == 409


async def test_cancelar_rejeita_usuario_nao_admin(mock_db):
    """C13 — usuario nao-admin recebe 403."""
    vendedor = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ)
    _setup(mock_db, user=vendedor)
    # get_admin_user nao e sobreescrito — usa o default que requer is_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{uuid.uuid4()}/cancelar",
            json={"motivo_cancelamento": "Teste"},
        )

    assert resp.status_code == 403


async def test_cancelar_prova_inexistente_404(admin_user, mock_db):
    """C13 — prova nao encontrada retorna 404."""
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [_detail_row_none()]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{uuid.uuid4()}/cancelar",
            json={"motivo_cancelamento": "Teste"},
        )

    assert resp.status_code == 404


async def test_cancelar_db_error_502(admin_user, mock_db):
    """C13 — exception no commit retorna 502."""
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(status_prova=StatusProvaEnum.CRIADA)
    mock_db.execute.side_effect = [
        _detail_row(prova, "V", LocalizacaoEnum.MATRIZ),
    ]
    mock_db.commit.side_effect = Exception("DB down")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/{prova.id}/cancelar",
            json={"motivo_cancelamento": "DB error test"},
        )

    assert resp.status_code == 502
    mock_db.rollback.assert_awaited()


# ═══════════════════════════════════════════════════════════════════════
# POST /{id}/reiniciar-ciclo — Componente 14 (Wave 3 Lote C)
# ═══════════════════════════════════════════════════════════════════════


async def test_reiniciar_happy_prova_reprovada(admin_user, mock_db):
    """C14 — admin reinicia ciclo de prova REPROVADA. Status=CRIADA,
    ciclo_atual incrementado, rota resetada."""
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(
        status_prova=StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
        rota=RotaEnum.PADRAO,
        ciclo_atual=1,
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, "Vendedor Teste", LocalizacaoEnum.MATRIZ),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/{prova.id}/reiniciar-ciclo")

    assert resp.status_code == 200, resp.json()
    data = resp.json()
    assert data["prova"]["status"] == "CRIADA"
    assert data["prova"]["ciclo_atual"] == 2
    assert data["prova"]["rota"] is None
    assert data["movimentacao"]["status_anterior"] == "REPROVADA_PELO_VENDEDOR"
    assert data["movimentacao"]["status_novo"] == "CRIADA"
    assert data["movimentacao"]["ciclo"] == 2
    assert data["movimentacao"]["rota_no_momento"] is None
    assert prova.ciclo_atual == 2
    mock_db.commit.assert_awaited_once()


async def test_reiniciar_happy_ciclo_2(admin_user, mock_db):
    """C14 — reinicio de ciclo 2 gera ciclo 3."""
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(
        status_prova=StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
        ciclo_atual=2,
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, "V", LocalizacaoEnum.FILIAL),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/{prova.id}/reiniciar-ciclo")

    assert resp.status_code == 200
    assert resp.json()["prova"]["ciclo_atual"] == 3


async def test_reiniciar_rejeita_prova_criada(admin_user, mock_db):
    """C14 — prova CRIADA nao pode ser reiniciada, retorna 409."""
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(status_prova=StatusProvaEnum.CRIADA)
    mock_db.execute.side_effect = [
        _detail_row(prova, "V", LocalizacaoEnum.MATRIZ),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/{prova.id}/reiniciar-ciclo")

    assert resp.status_code == 409
    assert "reprovadas" in resp.json()["detail"]


async def test_reiniciar_rejeita_prova_aprovada(admin_user, mock_db):
    """C14 — prova APROVADA nao pode ser reiniciada."""
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(
        status_prova=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        rota=RotaEnum.PADRAO,
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, "V", LocalizacaoEnum.MATRIZ),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/{prova.id}/reiniciar-ciclo")

    assert resp.status_code == 409


async def test_reiniciar_rejeita_prova_cancelada(admin_user, mock_db):
    """C14 — prova CANCELADA nao pode ser reiniciada."""
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(status_prova=StatusProvaEnum.CANCELADA)
    mock_db.execute.side_effect = [
        _detail_row(prova, "V", LocalizacaoEnum.MATRIZ),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/{prova.id}/reiniciar-ciclo")

    assert resp.status_code == 409


async def test_reiniciar_rejeita_usuario_nao_admin(mock_db):
    """C14 — usuario nao-admin recebe 403."""
    vendedor = make_user(setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.FILIAL)
    _setup(mock_db, user=vendedor)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/{uuid.uuid4()}/reiniciar-ciclo")

    assert resp.status_code == 403


async def test_reiniciar_prova_inexistente_404(admin_user, mock_db):
    """C14 — prova nao encontrada retorna 404."""
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [_detail_row_none()]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/{uuid.uuid4()}/reiniciar-ciclo")

    assert resp.status_code == 404


async def test_reiniciar_db_error_502(admin_user, mock_db):
    """C14 — exception no commit retorna 502."""
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(status_prova=StatusProvaEnum.REPROVADA_PELO_VENDEDOR)
    mock_db.execute.side_effect = [
        _detail_row(prova, "V", LocalizacaoEnum.MATRIZ),
    ]
    mock_db.commit.side_effect = Exception("DB down")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/{prova.id}/reiniciar-ciclo")

    assert resp.status_code == 502
    mock_db.rollback.assert_awaited()


# ═══════════════════════════════════════════════════════════════════════════
# GET /dashboard — Wave 4 (Componente 15)
# ═══════════════════════════════════════════════════════════════════════════


def _dashboard_mocks(
    *,
    com_vendedor=0,
    aprovadas=0,
    reprovadas=0,
    aguardando_envio=0,
    com_motorista=0,
    na_clicheria=0,
    concluidas=0,
    criadas_hoje=0,
    total_ativas=0,
    atrasadas=0,
    tempo_atraso=48,
    atrasadas_vendedor=None,
):
    """Cria 3 mocks sequenciais para o handler de dashboard (ADR-092).

    O handler faz 3 queries em ordem:
      Q1: SELECT config valor → .scalar_one_or_none() retorna int | None
      Q2: Query consolidada → .one() retorna named tuple com 10 campos
      Q3: Atrasadas por vendedor → .all() retorna lista de (nome, qtd)
    """
    # Q1: tempo atraso config
    q1 = MagicMock()
    q1.scalar_one_or_none.return_value = tempo_atraso

    # Q2: query consolidada — .one() retorna named tuple
    row = MagicMock()
    row.com_vendedor = com_vendedor
    row.aprovadas = aprovadas
    row.reprovadas = reprovadas
    row.aguardando_envio = aguardando_envio
    row.com_motorista = com_motorista
    row.na_clicheria = na_clicheria
    row.concluidas = concluidas
    row.criadas_hoje = criadas_hoje
    row.total_ativas = total_ativas
    row.atrasadas = atrasadas
    q2 = MagicMock()
    q2.one.return_value = row

    # Q3: atrasadas por vendedor — .all() retorna lista de named tuples
    vendor_rows = []
    for v_nome, v_qtd in (atrasadas_vendedor or []):
        vr = MagicMock()
        vr.vendedor_nome = v_nome
        vr.quantidade = v_qtd
        vendor_rows.append(vr)
    q3 = MagicMock()
    q3.all.return_value = vendor_rows

    return [q1, q2, q3]


DASHBOARD_URL = f"{PREFIX}/dashboard"


def _clear_dashboard_cache():
    """Limpa o cache do dashboard entre testes."""
    from app.api.v1.provas import _dashboard_cache
    _dashboard_cache.clear()


# ─── Happy paths ──────────────────────────────────────────────────────────


async def test_dashboard_happy_admin_all_counters(admin_user, mock_db):
    """Admin ve todos os contadores corretamente populados."""
    _clear_dashboard_cache()
    _setup(mock_db, admin=admin_user)

    mock_db.execute.side_effect = _dashboard_mocks(
        com_vendedor=2,
        aprovadas=1,
        reprovadas=1,
        aguardando_envio=1,
        com_motorista=1,
        na_clicheria=3,
        concluidas=5,
        criadas_hoje=4,
        total_ativas=12,
        atrasadas=2,
        tempo_atraso=48,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(DASHBOARD_URL)

    assert resp.status_code == 200, resp.json()
    data = resp.json()
    c = data["contadores"]

    assert c["criadas_hoje"] == 4
    assert c["com_vendedor"] == 2
    assert c["aprovadas"] == 1
    assert c["reprovadas"] == 1
    assert c["aguardando_envio"] == 1
    assert c["com_motorista"] == 1
    assert c["na_clicheria"] == 3
    assert c["concluidas"] == 5
    assert c["atrasadas"] == 2
    assert data["total_ativas"] == 12
    assert data["tempo_atraso_horas"] == 48
    assert "atualizado_em" in data


async def test_dashboard_happy_empty_db(admin_user, mock_db):
    """Dashboard retorna zeros quando nao ha provas."""
    _clear_dashboard_cache()
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = _dashboard_mocks()

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(DASHBOARD_URL)

    assert resp.status_code == 200
    c = resp.json()["contadores"]
    assert all(v == 0 for v in c.values())
    assert resp.json()["total_ativas"] == 0


async def test_dashboard_na_clicheria_valor_correto(admin_user, mock_db):
    """na_clicheria reflete o valor consolidado da query."""
    _clear_dashboard_cache()
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = _dashboard_mocks(na_clicheria=7)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(DASHBOARD_URL)

    assert resp.status_code == 200
    assert resp.json()["contadores"]["na_clicheria"] == 7


async def test_dashboard_total_ativas_vem_da_query(admin_user, mock_db):
    """total_ativas vem diretamente da query consolidada."""
    _clear_dashboard_cache()
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = _dashboard_mocks(total_ativas=5, concluidas=10)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(DASHBOARD_URL)

    assert resp.status_code == 200
    assert resp.json()["total_ativas"] == 5


async def test_dashboard_tempo_atraso_from_config(admin_user, mock_db):
    """tempo_atraso_horas reflete o valor configurado no banco."""
    _clear_dashboard_cache()
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = _dashboard_mocks(tempo_atraso=72)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(DASHBOARD_URL)

    assert resp.status_code == 200
    assert resp.json()["tempo_atraso_horas"] == 72


async def test_dashboard_tempo_atraso_fallback_48(admin_user, mock_db):
    """Se config nao existir, fallback para 48h."""
    _clear_dashboard_cache()
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = _dashboard_mocks(tempo_atraso=None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(DASHBOARD_URL)

    assert resp.status_code == 200
    assert resp.json()["tempo_atraso_horas"] == 48


# ─── Cache ────────────────────────────────────────────────────────────────


async def test_dashboard_cache_hit_nao_executa_query(admin_user, mock_db):
    """Segunda chamada dentro do TTL retorna cache sem query."""
    _clear_dashboard_cache()
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = _dashboard_mocks(com_vendedor=5)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp1 = await ac.get(DASHBOARD_URL)
        # Reset side_effect — se cache funciona, nao precisa de mock
        mock_db.execute.side_effect = RuntimeError("should not be called")
        resp2 = await ac.get(DASHBOARD_URL)

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json() == resp2.json()
    assert resp2.json()["contadores"]["com_vendedor"] == 5


# ─── Scoping ──────────────────────────────────────────────────────────────


async def test_dashboard_scoping_vendedor(vendedor_matriz, mock_db):
    """Vendedor ve contadores scoped."""
    _clear_dashboard_cache()
    _setup(mock_db, user=vendedor_matriz)
    mock_db.execute.side_effect = _dashboard_mocks(
        aprovadas=1, criadas_hoje=1, total_ativas=2,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(DASHBOARD_URL)

    assert resp.status_code == 200
    c = resp.json()["contadores"]
    assert c["criadas_hoje"] == 1
    assert c["aprovadas"] == 1
    assert resp.json()["total_ativas"] == 2


async def test_dashboard_scoping_motorista(mock_db):
    """Motorista ve contadores scoped por COM_MOTORISTA."""
    _clear_dashboard_cache()
    motorista = make_user(
        nome="Motorista", email="moto@test.com",
        setor=SetorEnum.MOTORISTA,
    )
    _setup(mock_db, user=motorista)
    mock_db.execute.side_effect = _dashboard_mocks(com_motorista=3)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(DASHBOARD_URL)

    assert resp.status_code == 200
    assert resp.json()["contadores"]["com_motorista"] == 3


async def test_dashboard_scoping_clicheria(mock_db):
    """Clicheria ve contadores scoped."""
    _clear_dashboard_cache()
    clicheria = make_user(
        nome="Clicheria", email="cliche@test.com",
        setor=SetorEnum.CLICHERIA,
    )
    _setup(mock_db, user=clicheria)
    mock_db.execute.side_effect = _dashboard_mocks(na_clicheria=3, concluidas=4)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(DASHBOARD_URL)

    assert resp.status_code == 200
    c = resp.json()["contadores"]
    assert c["na_clicheria"] == 3
    assert c["concluidas"] == 4


# ─── Auth ─────────────────────────────────────────────────────────────────


async def test_dashboard_401_sem_auth(mock_db):
    """Sem token retorna 401."""
    _clear_dashboard_cache()
    async def _get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(DASHBOARD_URL)

    assert resp.status_code == 401


# ─── Error handling ───────────────────────────────────────────────────────


async def test_dashboard_502_db_error(admin_user, mock_db):
    """Erro de banco retorna 502."""
    _clear_dashboard_cache()
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = RuntimeError("connection lost")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(DASHBOARD_URL)

    assert resp.status_code == 502


# ─── Schema validation ───────────────────────────────────────────────────


async def test_dashboard_response_schema_complete(admin_user, mock_db):
    """Resposta contem todos os campos exigidos pelo schema."""
    _clear_dashboard_cache()
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = _dashboard_mocks(criadas_hoje=1)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(DASHBOARD_URL)

    assert resp.status_code == 200
    data = resp.json()

    assert "contadores" in data
    assert "total_ativas" in data
    assert "tempo_atraso_horas" in data
    assert "atualizado_em" in data

    c = data["contadores"]
    expected_keys = {
        "criadas_hoje", "com_vendedor", "aprovadas", "reprovadas",
        "aguardando_envio", "com_motorista", "na_clicheria",
        "concluidas", "atrasadas",
    }
    assert set(c.keys()) == expected_keys

    for key, val in c.items():
        assert isinstance(val, int) and val >= 0, f"{key}={val}"


async def test_dashboard_atrasadas_independente_dos_status(admin_user, mock_db):
    """Atrasadas vem do calculo RN-008 na query consolidada."""
    _clear_dashboard_cache()
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = _dashboard_mocks(
        com_vendedor=3, total_ativas=8, atrasadas=2,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(DASHBOARD_URL)

    assert resp.status_code == 200
    assert resp.json()["contadores"]["atrasadas"] == 2
    assert resp.json()["total_ativas"] == 8


async def test_dashboard_zero_counters_default(admin_user, mock_db):
    """Contadores nao populados retornam 0."""
    _clear_dashboard_cache()
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = _dashboard_mocks(criadas_hoje=3)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(DASHBOARD_URL)

    assert resp.status_code == 200
    c = resp.json()["contadores"]
    assert c["criadas_hoje"] == 3
    assert c["com_vendedor"] == 0
    assert c["aprovadas"] == 0
    assert c["reprovadas"] == 0
    assert c["aguardando_envio"] == 0
    assert c["com_motorista"] == 0
    assert c["na_clicheria"] == 0
    assert c["concluidas"] == 0


async def test_dashboard_atrasadas_por_vendedor(admin_user, mock_db):
    """Breakdown de atrasadas por vendedor retorna lista ordenada."""
    _clear_dashboard_cache()
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = _dashboard_mocks(
        atrasadas=5,
        atrasadas_vendedor=[
            ("Regiane", 3),
            ("Paulinho", 2),
        ],
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(DASHBOARD_URL)

    assert resp.status_code == 200
    av = resp.json()["atrasadas_por_vendedor"]
    assert len(av) == 2
    assert av[0]["vendedor_nome"] == "Regiane"
    assert av[0]["quantidade"] == 3
    assert av[1]["vendedor_nome"] == "Paulinho"
    assert av[1]["quantidade"] == 2


async def test_dashboard_atrasadas_por_vendedor_empty(admin_user, mock_db):
    """Sem atrasadas, a lista de vendedores vem vazia."""
    _clear_dashboard_cache()
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = _dashboard_mocks(atrasadas=0)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(DASHBOARD_URL)

    assert resp.status_code == 200
    assert resp.json()["atrasadas_por_vendedor"] == []


# ═══════════════════════════════════════════════════════════════════════════
# Relatorios Gerenciais — Wave 5 Componente 16 (RF-015, US-014)
# ═══════════════════════════════════════════════════════════════════════════

RELATORIOS_URL = f"{PREFIX}/relatorios"


def _relatorio_mocks(
    *,
    tempo_atraso=48,
    total_geral=10,
    rota_rows=None,
    status_rows=None,
    tempo_medio_raw=None,
    vendedor_rows=None,
    atrasadas_rows=None,
):
    """Cria mocks sequenciais para o handler de relatorios.

    O handler faz 7 queries em ordem:
      Q1: config tempo_atraso → .scalar_one_or_none()
      Q2: total_geral → .scalar_one()
      Q3: distribuicao por rota → .all()
      Q4: distribuicao por status → .all()
      Q5: tempo medio aprovacao → .scalar_one()
      Q6: metricas por vendedor → .all()
      Q7: provas atrasadas → .all()
    """
    # Q1: config
    q1 = MagicMock()
    q1.scalar_one_or_none.return_value = tempo_atraso

    # Q2: total_geral
    q2 = MagicMock()
    q2.scalar_one.return_value = total_geral

    # Q3: distribuicao por rota
    rows_rota = []
    for rota_val, cnt in (rota_rows or []):
        r = MagicMock()
        r.rota = rota_val
        r.cnt = cnt
        rows_rota.append(r)
    q3 = MagicMock()
    q3.all.return_value = rows_rota

    # Q4: distribuicao por status
    rows_status = []
    for st_val, cnt in (status_rows or []):
        r = MagicMock()
        r.status = st_val
        r.cnt = cnt
        rows_status.append(r)
    q4 = MagicMock()
    q4.all.return_value = rows_status

    # Q5: tempo medio
    q5 = MagicMock()
    q5.scalar_one.return_value = tempo_medio_raw

    # Q6: vendedor rows
    q6 = MagicMock()
    q6.all.return_value = vendedor_rows or []

    # Q7: atrasadas lista
    q7 = MagicMock()
    q7.all.return_value = atrasadas_rows or []

    return [q1, q2, q3, q4, q5, q6, q7]


async def test_relatorios_200_admin_basic(admin_user, mock_db):
    """Admin recebe 200 com estrutura basica vazia."""
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = _relatorio_mocks()

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    assert resp.status_code == 200
    data = resp.json()
    assert "periodo" in data
    assert "total_geral" in data
    assert "tempo_medio_aprovacao_horas" in data
    # L-10 (auditoria Wave 5 ronda 2): taxa_reprovacao_geral_pct centralizada
    # no backend
    assert "taxa_reprovacao_geral_pct" in data
    assert "distribuicao_por_rota" in data
    assert "distribuicao_por_status" in data
    assert "por_vendedor" in data
    assert "atrasadas" in data
    assert "atualizado_em" in data
    assert data["total_geral"] == 10


async def test_relatorios_403_vendedor(vendedor_matriz, mock_db):
    """Vendedor recebe 403 (relatorios sao admin-only)."""
    _setup(mock_db, user=vendedor_matriz)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    assert resp.status_code == 403


async def test_relatorios_401_sem_auth(mock_db):
    """Sem autenticacao recebe 401."""
    async def _get_db():
        yield mock_db
    app.dependency_overrides[get_db] = _get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    assert resp.status_code == 401


async def test_relatorios_422_periodo_invalido(admin_user, mock_db):
    """inicio > fim retorna 422."""
    _setup(mock_db, admin=admin_user)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(
            RELATORIOS_URL,
            params={"periodo_inicio": "2026-04-15", "periodo_fim": "2026-04-01"},
        )

    assert resp.status_code == 422


async def test_relatorios_total_geral(admin_user, mock_db):
    """total_geral reflete o valor retornado pela query."""
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = _relatorio_mocks(total_geral=25)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    assert resp.status_code == 200
    assert resp.json()["total_geral"] == 25


async def test_relatorios_distribuicao_rota(admin_user, mock_db):
    """Distribuicao por rota agrupa corretamente."""
    from app.db.models import RotaEnum
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = _relatorio_mocks(
        rota_rows=[
            (RotaEnum.PADRAO, 5),
            (RotaEnum.DIRETA, 3),
            (None, 2),
        ]
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    assert resp.status_code == 200
    dr = resp.json()["distribuicao_por_rota"]
    assert dr["PADRAO"] == 5
    assert dr["DIRETA"] == 3
    assert dr["SEM_ROTA"] == 2


async def test_relatorios_distribuicao_status(admin_user, mock_db):
    """Distribuicao por status retorna lista com labels."""
    from app.db.models import StatusProvaEnum
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = _relatorio_mocks(
        status_rows=[
            (StatusProvaEnum.RETIRADA_PELO_VENDEDOR, 3),
            (StatusProvaEnum.APROVADA_PELO_VENDEDOR, 2),
        ]
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    assert resp.status_code == 200
    ds = resp.json()["distribuicao_por_status"]
    assert len(ds) == 2
    assert ds[0]["status"] == "RETIRADA_PELO_VENDEDOR"
    assert ds[0]["label"] == "Com vendedor"
    assert ds[0]["quantidade"] == 3


async def test_relatorios_tempo_medio_com_dados(admin_user, mock_db):
    """Tempo medio retorna valor em horas quando ha aprovacoes."""
    _setup(mock_db, admin=admin_user)
    # 10800 seconds = 3 hours
    mock_db.execute.side_effect = _relatorio_mocks(tempo_medio_raw=10800)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    assert resp.status_code == 200
    assert resp.json()["tempo_medio_aprovacao_horas"] == 3.0


async def test_relatorios_tempo_medio_null(admin_user, mock_db):
    """Tempo medio retorna null quando nao ha aprovacoes."""
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = _relatorio_mocks(tempo_medio_raw=None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    assert resp.status_code == 200
    assert resp.json()["tempo_medio_aprovacao_horas"] is None


async def test_relatorios_por_vendedor(admin_user, mock_db):
    """Metricas por vendedor retornam com taxa de reprovacao."""
    from app.db.models import LocalizacaoEnum
    _setup(mock_db, admin=admin_user)
    vr = MagicMock()
    vr.vendedor_id = uuid.uuid4()
    vr.vendedor_nome = "Mario Souza"
    vr.vendedor_localizacao = LocalizacaoEnum.FILIAL
    vr.total_provas = 10
    vr.aprovadas = 7
    vr.reprovadas = 2
    vr.avg_sec = 7200  # 2 hours

    mock_db.execute.side_effect = _relatorio_mocks(vendedor_rows=[vr])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    assert resp.status_code == 200
    pv = resp.json()["por_vendedor"]
    assert len(pv) == 1
    assert pv[0]["vendedor_nome"] == "Mario Souza"
    assert pv[0]["total_provas"] == 10
    assert pv[0]["aprovadas"] == 7
    assert pv[0]["reprovadas"] == 2
    assert pv[0]["taxa_reprovacao_pct"] == 20.0
    assert pv[0]["tempo_medio_aprovacao_horas"] == 2.0
    assert pv[0]["vendedor_localizacao"] == "FILIAL"


async def test_relatorios_vendedor_taxa_zero(admin_user, mock_db):
    """Vendedor com zero provas tem taxa 0.0."""
    _setup(mock_db, admin=admin_user)
    vr = MagicMock()
    vr.vendedor_id = uuid.uuid4()
    vr.vendedor_nome = "Empty Seller"
    vr.vendedor_localizacao = None
    vr.total_provas = 0
    vr.aprovadas = 0
    vr.reprovadas = 0
    vr.avg_sec = None

    mock_db.execute.side_effect = _relatorio_mocks(vendedor_rows=[vr])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    assert resp.status_code == 200
    pv = resp.json()["por_vendedor"]
    assert pv[0]["taxa_reprovacao_pct"] == 0.0
    assert pv[0]["tempo_medio_aprovacao_horas"] is None
    assert pv[0]["vendedor_localizacao"] is None


async def test_relatorios_atrasadas_lista(admin_user, mock_db):
    """Lista de atrasadas retorna com dias de atraso."""
    from datetime import timedelta

    from app.db.models import RotaEnum, StatusProvaEnum

    _setup(mock_db, admin=admin_user)
    now = datetime.now(timezone.utc)
    old_date = now - timedelta(days=5)

    ar = MagicMock()
    ar.prova_id = uuid.uuid4()
    ar.nome = "Arte Atrasada"
    ar.nro_requerimento = "REQ-999"
    ar.cliente = "Cliente Atraso"
    ar.vendedor_nome = "Vendedor Lento"
    ar.status = StatusProvaEnum.RETIRADA_PELO_VENDEDOR
    ar.rota = RotaEnum.PADRAO
    ar.ultima_mov_at = old_date

    mock_db.execute.side_effect = _relatorio_mocks(atrasadas_rows=[ar])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    assert resp.status_code == 200
    atrasadas = resp.json()["atrasadas"]
    assert len(atrasadas) == 1
    assert atrasadas[0]["nome"] == "Arte Atrasada"
    assert atrasadas[0]["nro_requerimento"] == "REQ-999"
    assert atrasadas[0]["status"] == "RETIRADA_PELO_VENDEDOR"
    assert atrasadas[0]["rota"] == "PADRAO"
    assert atrasadas[0]["dias_atraso"] >= 4.9


async def test_relatorios_atrasadas_sem_rota(admin_user, mock_db):
    """Prova atrasada sem rota retorna rota=null."""
    from datetime import timedelta as _td

    from app.db.models import StatusProvaEnum

    _setup(mock_db, admin=admin_user)
    now = datetime.now(timezone.utc)
    ar = MagicMock()
    ar.prova_id = uuid.uuid4()
    ar.nome = "Sem Rota"
    ar.nro_requerimento = "REQ-000"
    ar.cliente = "C"
    ar.vendedor_nome = "V"
    ar.status = StatusProvaEnum.CRIADA
    ar.rota = None
    ar.ultima_mov_at = now - _td(days=3)

    mock_db.execute.side_effect = _relatorio_mocks(atrasadas_rows=[ar])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    assert resp.status_code == 200
    assert resp.json()["atrasadas"][0]["rota"] is None


async def test_relatorios_periodo_default_30_dias(admin_user, mock_db):
    """Sem parametros de periodo, usa default de 30 dias."""
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = _relatorio_mocks()

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    assert resp.status_code == 200
    p = resp.json()["periodo"]
    from datetime import date as _date
    inicio = _date.fromisoformat(p["inicio"])
    fim = _date.fromisoformat(p["fim"])
    assert (fim - inicio).days == 30


async def test_relatorios_502_db_error(admin_user, mock_db):
    """Erro de DB retorna 502."""
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = Exception("DB connection lost")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    assert resp.status_code == 502


async def test_relatorios_response_schema_completo(admin_user, mock_db):
    """Response contem todos os campos esperados pelo RelatorioResponse."""
    from datetime import timedelta

    from app.db.models import LocalizacaoEnum, RotaEnum, StatusProvaEnum
    _setup(mock_db, admin=admin_user)
    now = datetime.now(timezone.utc)

    vr = MagicMock()
    vr.vendedor_id = uuid.uuid4()
    vr.vendedor_nome = "V1"
    vr.vendedor_localizacao = LocalizacaoEnum.MATRIZ
    vr.total_provas = 5
    vr.aprovadas = 3
    vr.reprovadas = 1
    vr.avg_sec = 3600

    ar = MagicMock()
    ar.prova_id = uuid.uuid4()
    ar.nome = "A1"
    ar.nro_requerimento = "R1"
    ar.cliente = "C1"
    ar.vendedor_nome = "V1"
    ar.status = StatusProvaEnum.COM_MOTORISTA
    ar.rota = RotaEnum.PADRAO
    ar.ultima_mov_at = now - timedelta(days=3)

    mock_db.execute.side_effect = _relatorio_mocks(
        total_geral=15,
        tempo_medio_raw=7200,
        rota_rows=[(RotaEnum.PADRAO, 10), (RotaEnum.DIRETA, 5)],
        status_rows=[(StatusProvaEnum.COM_MOTORISTA, 2)],
        vendedor_rows=[vr],
        atrasadas_rows=[ar],
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_geral"] == 15
    assert data["tempo_medio_aprovacao_horas"] == 2.0
    assert data["total_atrasadas"] == 1
    assert data["distribuicao_por_rota"]["PADRAO"] == 10
    assert data["distribuicao_por_rota"]["DIRETA"] == 5
    assert len(data["distribuicao_por_status"]) == 1
    assert len(data["por_vendedor"]) == 1
    assert len(data["atrasadas"]) == 1


async def test_relatorios_taxa_reprovacao_geral_calculada(admin_user, mock_db):
    """Taxa de reprovacao geral e calculada no backend (L-10 auditoria Wave 5 ronda 2).

    Valida o novo campo `taxa_reprovacao_geral_pct` que foi movido do
    frontend para o backend. Soma das reprovadas de todos os vendedores
    dividido pelo total_geral, x100, arredondado a 1 casa decimal.

    Cenario: total_geral=20, 2 vendedores com 3 + 1 = 4 reprovadas.
    Taxa esperada: (4 / 20) * 100 = 20.0%.
    """
    from app.db.models import LocalizacaoEnum

    _setup(mock_db, admin=admin_user)

    v1 = MagicMock()
    v1.vendedor_id = uuid.uuid4()
    v1.vendedor_nome = "Vendedor A"
    v1.vendedor_localizacao = LocalizacaoEnum.MATRIZ
    v1.total_provas = 12
    v1.aprovadas = 8
    v1.reprovadas = 3
    v1.avg_sec = 3600

    v2 = MagicMock()
    v2.vendedor_id = uuid.uuid4()
    v2.vendedor_nome = "Vendedor B"
    v2.vendedor_localizacao = LocalizacaoEnum.FILIAL
    v2.total_provas = 8
    v2.aprovadas = 5
    v2.reprovadas = 1
    v2.avg_sec = 7200

    mock_db.execute.side_effect = _relatorio_mocks(
        total_geral=20,
        vendedor_rows=[v1, v2],
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    assert resp.status_code == 200
    data = resp.json()
    # 4 reprovadas / 20 total = 20.0%
    assert data["taxa_reprovacao_geral_pct"] == 20.0


async def test_relatorios_taxa_reprovacao_geral_zero_division(admin_user, mock_db):
    """Taxa de reprovacao geral retorna 0.0 quando total_geral = 0 (L-10).

    Protege contra ZeroDivisionError. O handler deve detectar total_geral
    zero e retornar 0.0 sem dividir.
    """
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = _relatorio_mocks(
        total_geral=0,
        vendedor_rows=[],
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    assert resp.status_code == 200
    data = resp.json()
    assert data["taxa_reprovacao_geral_pct"] == 0.0


# ── Testes negativos de exclusao de status terminais ─────────────────────────
#
# Auditoria Wave 5 (achado M-04): os filtros `status.not_in(TERMINAL_STATUSES)`
# em Q4 (distribuicao_por_status, provas.py:1324) e Q7 (atrasadas_stmt,
# provas.py:1488) sao cruciais para a corretude dos relatorios. Um bug em
# Wave 4 (ADR-094 L-01) mostra que filtros SQL podem quebrar silenciosamente.
#
# LIMITACAO HONESTA: como `_relatorio_mocks` retorna mocks pre-fabricados sem
# passar pelo Postgres real, estes testes NAO exercitam o SQL `WHERE not_in`.
# Eles validam o *contrato do mock* — que o handler so recebe status ativos —
# e falhariam se alguem introduzisse um pos-processamento Python que vazasse
# terminais no response. Validacao real do SQL pende de suite de integracao
# contra Postgres (achado H-01 rejeitado pelo stakeholder em 2026-04-14).


async def test_relatorios_distribuicao_status_exclui_terminais(admin_user, mock_db):
    """Distribuicao por status nunca inclui CANCELADA/RECEBIDA (Q4, M-04).

    Limitacao: o mock bypassa o WHERE not_in(TERMINAL_STATUSES). Este teste
    valida o contrato + o pos-processamento Python do handler, nao o SQL.
    """
    from app.db.models import StatusProvaEnum
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = _relatorio_mocks(
        status_rows=[
            (StatusProvaEnum.RETIRADA_PELO_VENDEDOR, 3),
            (StatusProvaEnum.APROVADA_PELO_VENDEDOR, 2),
            (StatusProvaEnum.COM_MOTORISTA, 1),
        ]
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    assert resp.status_code == 200
    ds = resp.json()["distribuicao_por_status"]
    status_vals = {s["status"] for s in ds}
    # Nenhum status terminal deve aparecer
    assert "CANCELADA" not in status_vals
    assert "RECEBIDA_PELA_CLICHERIA" not in status_vals
    # Status ativos devem aparecer
    assert "RETIRADA_PELO_VENDEDOR" in status_vals
    assert "APROVADA_PELO_VENDEDOR" in status_vals
    assert "COM_MOTORISTA" in status_vals
    assert len(ds) == 3


async def test_relatorios_atrasadas_exclui_terminais(admin_user, mock_db):
    """Lista de atrasadas nunca inclui provas em status terminal (Q7, M-04).

    Limitacao: idem M-04 — valida contrato + pos-processamento, nao o SQL.
    """
    from datetime import timedelta

    from app.db.models import RotaEnum, StatusProvaEnum

    _setup(mock_db, admin=admin_user)
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=5)

    # Apenas 1 linha ativa (COM_MOTORISTA) — o SQL Q7 ja filtrou os terminais
    ar = MagicMock()
    ar.prova_id = uuid.uuid4()
    ar.nome = "Atrasada ativa"
    ar.nro_requerimento = "REQ-M04"
    ar.cliente = "C"
    ar.vendedor_nome = "V"
    ar.status = StatusProvaEnum.COM_MOTORISTA
    ar.rota = RotaEnum.PADRAO
    ar.ultima_mov_at = old

    mock_db.execute.side_effect = _relatorio_mocks(atrasadas_rows=[ar])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    assert resp.status_code == 200
    atrasadas = resp.json()["atrasadas"]
    assert len(atrasadas) == 1
    status_in_list = {a["status"] for a in atrasadas}
    # Nenhum terminal deve ter escapado do mock para o response
    assert "CANCELADA" not in status_in_list
    assert "RECEBIDA_PELA_CLICHERIA" not in status_in_list
    assert atrasadas[0]["status"] == "COM_MOTORISTA"


# ═══════════════════════════════════════════════════════════════════════════
# Relatorios CSV — Wave 5 (RF-015 exportacao)
# ═══════════════════════════════════════════════════════════════════════════

RELATORIOS_CSV_URL = f"{PREFIX}/relatorios/csv"


def _csv_mocks(*, rows=None):
    """Mocks para o handler de CSV.

    O handler faz 1 query:
      Q1: SELECT provas + JOIN usuarios + subqueries → .all()
    """
    q1 = MagicMock()
    q1.all.return_value = rows or []
    return [q1]


def _make_csv_row(
    *,
    nome="Arte Test",
    nro_req="REQ-001",
    cliente="Cliente A",
    vendedor_nome="Mario",
    localizacao=None,
    status_val=None,
    rota_val=None,
    ciclo=1,
    created_at=None,
    ultima_mov_at=None,
    aprovada_cnt=0,
    reprovada_cnt=0,
):
    from app.db.models import StatusProvaEnum

    r = MagicMock()
    r.nome = nome
    r.nro_requerimento = nro_req
    r.cliente = cliente
    r.vendedor_nome = vendedor_nome
    r.vendedor_localizacao = localizacao
    r.status = status_val or StatusProvaEnum.CRIADA
    r.rota = rota_val
    r.ciclo_atual = ciclo
    r.created_at = created_at or datetime.now(timezone.utc)
    r.ultima_mov_at = ultima_mov_at or datetime.now(timezone.utc)
    r.aprovada_cnt = aprovada_cnt
    r.reprovada_cnt = reprovada_cnt
    return r


async def test_relatorios_csv_200_admin(admin_user, mock_db):
    """Admin recebe 200 com Content-Type text/csv + Cache-Control no-store (L-03)."""
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = _csv_mocks()

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_CSV_URL)

    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment" in resp.headers["content-disposition"]
    assert ".csv" in resp.headers["content-disposition"]
    # L-03 (auditoria Wave 5 ronda 2): header Cache-Control previne browser
    # de servir CSV cached depois que os dados mudam entre downloads.
    assert resp.headers.get("cache-control") == "no-store"


async def test_relatorios_csv_403_vendedor(vendedor_matriz, mock_db):
    """Vendedor recebe 403."""
    _setup(mock_db, user=vendedor_matriz)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_CSV_URL)

    assert resp.status_code == 403


async def test_relatorios_csv_conteudo_header(admin_user, mock_db):
    """CSV contem header pt-BR correto."""
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = _csv_mocks()

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_CSV_URL)

    assert resp.status_code == 200
    text = resp.text
    lines = text.strip().split("\n")
    assert len(lines) >= 1
    header = lines[0].replace("\ufeff", "")
    assert "Nome da Prova" in header
    assert "Nro Requerimento" in header
    assert "Vendedor" in header
    assert "Dias Parada" in header


async def test_relatorios_csv_conteudo_dados(admin_user, mock_db):
    """CSV inclui dados formatados."""
    from app.db.models import LocalizacaoEnum, RotaEnum, StatusProvaEnum

    _setup(mock_db, admin=admin_user)
    row = _make_csv_row(
        nome="Arte CSV",
        nro_req="REQ-CSV",
        cliente="Client CSV",
        vendedor_nome="Vendedor CSV",
        localizacao=LocalizacaoEnum.FILIAL,
        status_val=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        rota_val=RotaEnum.DIRETA,
        aprovada_cnt=1,
    )
    mock_db.execute.side_effect = _csv_mocks(rows=[row])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_CSV_URL)

    assert resp.status_code == 200
    text = resp.text
    assert "Arte CSV" in text
    assert "REQ-CSV" in text
    assert "Filial" in text
    assert "Aprovada pelo vendedor" in text
    assert "Rota Direta" in text
    assert "Sim" in text


async def test_relatorios_csv_422_periodo_invalido(admin_user, mock_db):
    """inicio > fim retorna 422."""
    _setup(mock_db, admin=admin_user)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(
            RELATORIOS_CSV_URL,
            params={"periodo_inicio": "2026-04-15", "periodo_fim": "2026-04-01"},
        )

    assert resp.status_code == 422


async def test_relatorios_csv_utf8_bom(admin_user, mock_db):
    """CSV inicia com UTF-8 BOM para Excel."""
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = _csv_mocks()

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_CSV_URL)

    assert resp.status_code == 200
    assert resp.text.startswith("\ufeff")


async def test_relatorios_csv_nao_truncado_sem_header(admin_user, mock_db):
    """CSV abaixo do limite nao tem header X-CSV-Truncated (L-04 auditoria Wave 5 ronda 2).

    Valida que requests dentro do limite CSV_MAX_ROWS (10000) nao sinalizam
    truncamento. Usa um mock pequeno (5 linhas) para confirmar que o header
    `X-CSV-Truncated` NAO aparece no response.
    """
    _setup(mock_db, admin=admin_user)
    rows = [_make_csv_row(nome=f"Arte {i}", nro_req=f"REQ-{i}") for i in range(5)]
    mock_db.execute.side_effect = _csv_mocks(rows=rows)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_CSV_URL)

    assert resp.status_code == 200
    assert "x-csv-truncated" not in resp.headers
    assert "x-csv-max-rows" not in resp.headers


async def test_relatorios_csv_truncado_com_header(admin_user, mock_db):
    """CSV no limite sinaliza truncamento via X-CSV-Truncated=true (L-04).

    Simula um dataset de CSV_MAX_ROWS + 1 linhas (10001). O handler deve:
      1. Detectar que len(rows) > CSV_MAX_ROWS
      2. Truncar para CSV_MAX_ROWS (10000 linhas)
      3. Setar header X-CSV-Truncated: true + X-CSV-Max-Rows: 10000
    """
    from app.api.v1.provas import CSV_MAX_ROWS

    _setup(mock_db, admin=admin_user)
    # Gera CSV_MAX_ROWS + 1 linhas (o limit da query busca CSV_MAX_ROWS + 1)
    rows = [
        _make_csv_row(nome=f"Arte {i}", nro_req=f"REQ-{i:05d}")
        for i in range(CSV_MAX_ROWS + 1)
    ]
    mock_db.execute.side_effect = _csv_mocks(rows=rows)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_CSV_URL)

    assert resp.status_code == 200
    assert resp.headers.get("x-csv-truncated") == "true"
    assert resp.headers.get("x-csv-max-rows") == str(CSV_MAX_ROWS)

    # O CSV renderizado deve conter exatamente CSV_MAX_ROWS linhas de dados
    # (+ 1 header + BOM). Simples contagem de \n.
    body = resp.text
    line_count = body.count("\n")
    # CSV_MAX_ROWS (10000 linhas de dados) + 1 header
    assert line_count == CSV_MAX_ROWS + 1


async def test_relatorios_csv_502_db_error(admin_user, mock_db):
    """Erro de DB no CSV retorna 502 (L-09 auditoria Wave 5).

    Cobre o `except Exception:` do handler get_relatorios_csv que ate entao
    nao tinha teste — o coverage da auditoria identificou as linhas como
    nao cobertas.
    """
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = Exception("DB connection lost")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_CSV_URL)

    assert resp.status_code == 502


async def test_relatorios_csv_injection_sanitized(admin_user, mock_db):
    """CSV Injection nos campos de texto livre e neutralizado (M-01 auditoria Wave 5).

    Verifica que nome/cliente/vendedor_nome comecando com chars de formula
    (=, +, -, @, \\t, \\r) sao prefixados com apostrofo antes de serem escritos
    no CSV, protegendo admins que abrem o export no Excel/Calc/Sheets contra
    execucao acidental de formulas maliciosas. CWE-1236 / OWASP CSV Injection.

    Campos testados:
      - nome: `=1+1` (formula basica)
      - cliente: `+cmd|' /C calc'!A1` (DDE — Excel dispara commando externo)
      - vendedor_nome: `@SUM(A1:A9)` (formula com prefixo @)

    `nro_requerimento` nao entra neste teste porque o schema Pydantic
    (NRO_REQ_RE) ja proibe os chars perigosos na criacao da prova.
    """
    from app.db.models import StatusProvaEnum

    _setup(mock_db, admin=admin_user)
    row = _make_csv_row(
        nome="=1+1",
        nro_req="REQ-SAFE",
        cliente="+cmd|' /C calc'!A1",
        vendedor_nome="@SUM(A1:A9)",
        status_val=StatusProvaEnum.CRIADA,
    )
    mock_db.execute.side_effect = _csv_mocks(rows=[row])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_CSV_URL)

    assert resp.status_code == 200
    text = resp.text

    # Os 3 campos vulneraveis devem ter apostrofo prefixado
    assert "'=1+1" in text
    assert "'+cmd|' /C calc'!A1" in text
    assert "'@SUM(A1:A9)" in text

    # O apostrofo e o UNICO char adicionado — o valor original segue logo depois
    # Garante que nao ha escape duplo ou perda de dados
    assert "=1+1" in text  # presente apos o apostrofo
    assert "@SUM(A1:A9)" in text  # idem

    # Campos nao vulneraveis NAO devem ter apostrofo adicionado
    assert "'REQ-SAFE" not in text  # nro_requerimento intacto
    assert "REQ-SAFE" in text


# ── SQL-level assertions em TERMINAL_STATUSES (M-04 auditoria Wave 5) ──────
#
# A auditoria anterior adicionou os testes `*_exclui_terminais` que validam
# o *contrato do mock* — se alguem remover o WHERE NOT IN do SQL, esses
# testes continuam passando porque o mock devolve rows pre-fabricados.
#
# A suite real contra Postgres (H-01) continua rejeitada, mas esta re-auditoria
# propoe uma mitigacao barata e ortogonal: compilar o stmt para SQL string e
# fazer assertion na estrutura. Os testes abaixo capturam os stmts enviados ao
# `mock_db.execute` via side_effect callable e inspecionam o SQL gerado pelo
# dialeto Postgres.
#
# Esta tecnica NAO substitui integracao real (nao valida que o WHERE esta
# semanticamente correto em um banco ativo), mas GARANTE que o SQL contem a
# clausula — pega regressoes tipo "alguem comentou o .where(...)" que os
# testes de contrato de mock nao pegam.


async def test_relatorios_fallback_tempo_atraso_valor_invalido(admin_user, mock_db):
    """Fallback 48h quando configuracoes_sistema.tempo_atraso_horas_uteis
    retorna valor nao-numerico (L-02 auditoria Wave 5 ronda 2).

    O handler tem um try/except (ValueError, TypeError) em torno do
    int(tempo_atraso_raw) que protege contra valores invalidos no banco
    (ex: alguem editou a configuracao via painel e colocou string).
    As linhas 1282-1283 do handler estavam marcadas como missing no
    coverage — este teste as exercita.

    Estrategia: substituir apenas a 1a query (Q1 tempo_atraso config) para
    retornar 'abc' (string nao-numerica), e deixar as demais queries
    retornando vazio. O handler deve:
      1. Tentar int('abc') -> ValueError
      2. Cair no except e usar fallback tempo_atraso_horas = 48
      3. Prosseguir normalmente e retornar 200
    """
    _setup(mock_db, admin=admin_user)

    # Q1 retorna string nao-numerica; Q2-Q7 retornam defaults do _relatorio_mocks
    mocks = _relatorio_mocks()
    mocks[0].scalar_one_or_none.return_value = "abc"  # valor invalido
    mock_db.execute.side_effect = mocks

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    # O handler nao deve quebrar — fallback 48h e usado e o response e 200
    assert resp.status_code == 200
    data = resp.json()
    assert "total_geral" in data
    assert data["total_geral"] == 10  # default do _relatorio_mocks


async def test_relatorios_fallback_tempo_atraso_none(admin_user, mock_db):
    """Fallback 48h quando configuracoes_sistema.tempo_atraso_horas_uteis nao existe
    (L-02 auditoria Wave 5 ronda 2).

    Cobre o outro ramo do try/except: o branch `if tempo_atraso_raw is not None`
    que ja e default (None -> usa 48h). Garante que o handler aceita o cenario
    de configuracao ausente.
    """
    _setup(mock_db, admin=admin_user)

    mocks = _relatorio_mocks()
    mocks[0].scalar_one_or_none.return_value = None  # configuracao ausente
    mock_db.execute.side_effect = mocks

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    assert resp.status_code == 200


async def test_relatorios_q4_sql_literal_contem_not_in_terminais(admin_user, mock_db):
    """Q4 SQL contem WHERE status NOT IN com terminais (M-04 auditoria Wave 5).

    Captura os stmts enviados a `db.execute` e inspeciona o SQL compilado
    para o dialeto Postgres. Valida que a 4a query (distribuicao_por_status)
    contem `NOT IN` e os valores `CANCELADA` e `RECEBIDA_PELA_CLICHERIA`.
    """
    from sqlalchemy.dialects import postgresql

    _setup(mock_db, admin=admin_user)

    captured_stmts: list = []
    mock_iter = iter(_relatorio_mocks())

    def capture(stmt, *args, **kwargs):
        captured_stmts.append(stmt)
        return next(mock_iter)

    mock_db.execute.side_effect = capture

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    assert resp.status_code == 200
    # Q1=config, Q2=total_geral, Q3=rota, Q4=status, Q5=tempo_medio, Q6=vendedor, Q7=atrasadas
    assert len(captured_stmts) >= 4

    q4_sql = str(
        captured_stmts[3].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    q4_upper = q4_sql.upper()
    assert "NOT IN" in q4_upper, (
        f"Q4 (distribuicao_por_status) perdeu WHERE NOT IN.\nSQL:\n{q4_sql}"
    )
    assert "RECEBIDA_PELA_CLICHERIA" in q4_sql, (
        f"Q4 nao esta excluindo RECEBIDA_PELA_CLICHERIA.\nSQL:\n{q4_sql}"
    )
    assert "CANCELADA" in q4_sql, (
        f"Q4 nao esta excluindo CANCELADA.\nSQL:\n{q4_sql}"
    )


async def test_relatorios_q7_sql_literal_contem_not_in_terminais(admin_user, mock_db):
    """Q7 SQL (atrasadas) contem WHERE status NOT IN com terminais (M-04).

    Mesmo principio do teste Q4 — captura o stmt da 7a query e verifica
    que a lista de atrasadas exclui status terminais no SQL real.
    """
    from sqlalchemy.dialects import postgresql

    _setup(mock_db, admin=admin_user)

    captured_stmts: list = []
    mock_iter = iter(_relatorio_mocks())

    def capture(stmt, *args, **kwargs):
        captured_stmts.append(stmt)
        return next(mock_iter)

    mock_db.execute.side_effect = capture

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_URL)

    assert resp.status_code == 200
    assert len(captured_stmts) >= 7, (
        f"Esperava 7 queries executadas, got {len(captured_stmts)}"
    )

    q7_sql = str(
        captured_stmts[6].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    q7_upper = q7_sql.upper()
    assert "NOT IN" in q7_upper, (
        f"Q7 (atrasadas) perdeu WHERE NOT IN.\nSQL:\n{q7_sql}"
    )
    assert "RECEBIDA_PELA_CLICHERIA" in q7_sql, (
        f"Q7 nao esta excluindo RECEBIDA_PELA_CLICHERIA.\nSQL:\n{q7_sql}"
    )
    assert "CANCELADA" in q7_sql, (
        f"Q7 nao esta excluindo CANCELADA.\nSQL:\n{q7_sql}"
    )


async def test_relatorios_csv_injection_valores_seguros_inalterados(admin_user, mock_db):
    """Valores que nao comecam com char de formula passam inalterados (M-01).

    Confirma que o sanitizer e cirurgico: apenas strings comecando com
    `=+-@\\t\\r` recebem apostrofo. Nomes normais, nomes com `=` no meio,
    numeros negativos formatados como string etc nao devem ser afetados.
    """
    from app.db.models import StatusProvaEnum

    _setup(mock_db, admin=admin_user)
    row = _make_csv_row(
        nome="Arte Normal 2026",
        nro_req="REQ-123",
        cliente="Empresa X = Best (desde 1990)",  # `=` no meio, nao no comeco
        vendedor_nome="Mario Souza",
        status_val=StatusProvaEnum.CRIADA,
    )
    mock_db.execute.side_effect = _csv_mocks(rows=[row])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(RELATORIOS_CSV_URL)

    assert resp.status_code == 200
    text = resp.text

    # Valores seguros devem aparecer sem alteracao
    assert "Arte Normal 2026" in text
    assert "Empresa X = Best (desde 1990)" in text
    assert "Mario Souza" in text

    # NAO deve prefixar nenhum dos 3 (nenhum comeca com char de formula)
    assert "'Arte Normal" not in text
    assert "'Empresa X" not in text
    assert "'Mario Souza" not in text
