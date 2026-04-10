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
