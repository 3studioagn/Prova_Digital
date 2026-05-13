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
        "rota": "MATRIZ",
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
    # Wave 2 v4.0: rota e PERSISTIDA na criacao com a escolha do admin
    # (RN-002 v4.0). Substituiu o ADR-042 + rota_projetada da v3.0.
    assert data["prova"]["rota"] == "MATRIZ"
    assert data["prova"]["ciclo_atual"] == 1
    assert len(data["prova"]["qr_code_hash"]) == 64
    # Wave 2 v4.0: payload do QR embute `codigo_publico` (PRV-AAAA-MM-NNNNNN)
    # em vez de `nro_requerimento` (DAT v3.0 §8.1 — idempotencia camera↔
    # digitacao manual via Componente 19 da Wave 3 v4.0).
    assert data["prova"]["codigo_publico"].startswith("PRV-")
    assert data["qr_code_payload"].startswith(
        f"3SD|{data['prova']['codigo_publico']}|"
    )

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
                    "rota": "FILIAL",
                    "object_key": "provas/2026/04/xyz/arte.png",
                },
            )

    assert resp.status_code == 201
    # Wave 2 v4.0: rota persistida = escolha do admin (FILIAL no payload).
    assert resp.json()["prova"]["rota"] == "FILIAL"


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
                    "rota": "MATRIZ",
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
                    "rota": "MATRIZ",
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
                    "rota": "MATRIZ",
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
                    "rota": "MATRIZ",
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
                    "rota": "MATRIZ",
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
                    "rota": "MATRIZ",
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
                    "rota": "MATRIZ",
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
                    "rota": "MATRIZ",
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
                    "rota": "MATRIZ",
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
                    "rota": "MATRIZ",
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
      - Mapear IntegrityError de constraint do nro_requerimento para
        409 Conflict (nao 500).
      - Mensagem deve deixar claro que o nro_requerimento ja existe.
      - db.rollback e _cleanup_r2 sao chamados, mesma semantica do
        caminho de erro generico.

    AUD-W2V4-004 (atualizado): o handler agora distingue qual constraint
    foi violado. Este teste mantem o cenario nro_requerimento — agora
    a mensagem do erro inclui `provas_digitais_nro_requerimento_key`
    para simular UniqueViolationError real do asyncpg.
    """
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [
        _scalar(None),  # check inicial passou (race: o outro admin ainda nao commitou)
        _scalar(vendedor_matriz),
        _scalar(DEFAULT_TEMPLATE),
    ]
    # O commit levanta IntegrityError. Mensagem inclui o nome do
    # constraint para que o handler novo (AUD-W2V4-004) classifique
    # como race TOCTOU de nro_requerimento.
    mock_db.commit.side_effect = IntegrityError(
        statement="INSERT ...",
        params={},
        orig=Exception(
            "duplicate key value violates unique constraint "
            '"provas_digitais_nro_requerimento_key"'
        ),
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
                    "rota": "MATRIZ",
                    "object_key": "provas/2026/04/race/arte.jpg",
                },
            )
    assert resp.status_code == 409
    assert "ja cadastrado" in resp.json()["detail"]
    mock_db.rollback.assert_awaited()
    mock_delete.assert_awaited_once()


async def test_create_prova_codigo_publico_collision_retry_succeeds(
    admin_user, vendedor_matriz, mock_db
):
    """AUD-W2V4-004: colisao em idx_provas_codigo_publico no primeiro
    commit deve disparar retry com codigo regenerado. Segunda tentativa
    succeeda. Resposta 201 com novo codigo_publico.
    """
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [
        _scalar(None),
        _scalar(vendedor_matriz),
        _scalar(DEFAULT_TEMPLATE),
    ]
    mock_db.refresh.side_effect = _refresh_prova_defaults
    # Primeira tentativa de commit colide em codigo_publico; segunda
    # passa.
    mock_db.commit.side_effect = [
        IntegrityError(
            statement="INSERT ...",
            params={},
            orig=Exception(
                "duplicate key value violates unique constraint "
                '"idx_provas_codigo_publico"'
            ),
        ),
        None,  # commit OK na segunda tentativa
    ]

    with patch(
        "app.api.v1.provas.r2_signed.head_object",
        new=AsyncMock(return_value={"ContentLength": 1024}),
    ), patch(
        "app.api.v1.provas.r2_signed.get_object_head_bytes",
        new=AsyncMock(return_value=FAKE_JPEG_HEAD),
    ), patch("app.api.v1.provas.r2_delete", new=AsyncMock()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(
                f"{PREFIX}/",
                json={
                    "nome": "Retry",
                    "nro_requerimento": "REQ-RETRY",
                    "cliente": "C",
                    "vendedor_id": str(vendedor_matriz.id),
                    "rota": "MATRIZ",
                    "object_key": "provas/2026/04/retry/arte.jpg",
                },
            )
    assert resp.status_code == 201, resp.text
    # Houve 2 commits (1 falhou + 1 sucesso) e 1 rollback do failover.
    assert mock_db.commit.await_count == 2
    mock_db.rollback.assert_awaited()
    # Codigo publico no response existe e segue o formato.
    assert resp.json()["prova"]["codigo_publico"].startswith("PRV-")


async def test_create_prova_codigo_publico_collision_persistent_returns_502(
    admin_user, vendedor_matriz, mock_db
):
    """AUD-W2V4-004: colisao persistente em idx_provas_codigo_publico nas
    3 tentativas retorna 502 (sinaliza problema de entropia).
    """
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [
        _scalar(None),
        _scalar(vendedor_matriz),
        _scalar(DEFAULT_TEMPLATE),
    ]
    erro_codigo = IntegrityError(
        statement="INSERT ...",
        params={},
        orig=Exception(
            "duplicate key value violates unique constraint "
            '"idx_provas_codigo_publico"'
        ),
    )
    mock_db.commit.side_effect = [erro_codigo, erro_codigo, erro_codigo]

    with patch(
        "app.api.v1.provas.r2_signed.head_object",
        new=AsyncMock(return_value={"ContentLength": 1024}),
    ), patch(
        "app.api.v1.provas.r2_signed.get_object_head_bytes",
        new=AsyncMock(return_value=FAKE_JPEG_HEAD),
    ), patch("app.api.v1.provas.r2_delete", new=AsyncMock()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(
                f"{PREFIX}/",
                json={
                    "nome": "Pers",
                    "nro_requerimento": "REQ-PERS",
                    "cliente": "C",
                    "vendedor_id": str(vendedor_matriz.id),
                    "rota": "FILIAL",
                    "object_key": "provas/2026/04/pers/arte.jpg",
                },
            )
    assert resp.status_code == 502
    assert "codigo publico" in resp.json()["detail"].lower()


async def test_create_prova_unclassified_integrity_error_returns_502(
    admin_user, vendedor_matriz, mock_db
):
    """AUD-W2V4-004: IntegrityError sem constraint name reconhecivel
    (ex: FK quebrada, NOT NULL violado) cai no branch "outros" e
    retorna 502 — mudanca de contrato proposital vs antes que
    mapeava 409 generico (mensagem enganosa).
    """
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [
        _scalar(None),
        _scalar(vendedor_matriz),
        _scalar(DEFAULT_TEMPLATE),
    ]
    mock_db.commit.side_effect = IntegrityError(
        statement="INSERT ...",
        params={},
        orig=Exception("foreign key constraint violated"),
    )

    with patch(
        "app.api.v1.provas.r2_signed.head_object",
        new=AsyncMock(return_value={"ContentLength": 1024}),
    ), patch(
        "app.api.v1.provas.r2_signed.get_object_head_bytes",
        new=AsyncMock(return_value=FAKE_JPEG_HEAD),
    ), patch("app.api.v1.provas.r2_delete", new=AsyncMock()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
            resp = await ac.post(
                f"{PREFIX}/",
                json={
                    "nome": "Uncls",
                    "nro_requerimento": "REQ-UNCLS",
                    "cliente": "C",
                    "vendedor_id": str(vendedor_matriz.id),
                    "rota": "LAM_MATRIZ",
                    "object_key": "provas/2026/04/uncls/arte.jpg",
                },
            )
    assert resp.status_code == 502
    assert "persistir" in resp.json()["detail"].lower()


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
                    "rota": "MATRIZ",
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
                "rota": "MATRIZ",
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
                "rota": "MATRIZ",
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
    codigo_publico=None,
    cliente="Cliente X",
    vendedor_id=None,
    status_prova=StatusProvaEnum.CRIADA,
    rota=None,
    ciclo_atual=1,
):
    """Fabrica de ProvaDigital in-memory (sem INSERT real).

    Wave 2 v4.0: `codigo_publico` autopreenchido com PRV-2026-04-XXXXXX
    se nao informado (todos os testes de Wave 2 v4.0+ ganham codigo
    valido sem precisar passar explicitamente).
    """
    now = datetime.now(timezone.utc)
    return ProvaDigital(
        id=id or uuid.uuid4(),
        nome=nome,
        nro_requerimento=nro_requerimento,
        codigo_publico=codigo_publico or f"PRV-2026-04-{uuid.uuid4().hex[:6].upper()}",
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


async def test_list_motorista_inclui_3_contextos_v4(mock_db):
    """AUD-W3C11-001 (pos-auditoria): motorista listando provas ve os
    3 contextos v4.0 alem do COM_MOTORISTA legacy.

    Cenario critico: motorista em Lam.Matriz precisa ver provas em
    COM_MOTORISTA_IDA_LAMINACAO (para confirmar chegada na clicheria),
    COM_MOTORISTA_VOLTA_LAMINACAO (volta para 3Studio) e
    COM_MOTORISTA_ENTREGA_FINAL (entrega final na clicheria)."""
    motorista = make_user(setor=SetorEnum.MOTORISTA, localizacao=None)
    _setup(mock_db, user=motorista)
    _capture_list_stmts(mock_db, count=0, rows=[])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/")

    assert resp.status_code == 200
    sql = _compiled_sql(mock_db._captured_stmts[0])
    for estado in (
        "'COM_MOTORISTA'",
        "'COM_MOTORISTA_IDA_LAMINACAO'",
        "'COM_MOTORISTA_VOLTA_LAMINACAO'",
        "'COM_MOTORISTA_ENTREGA_FINAL'",
    ):
        assert estado in sql, f"esperado {estado} na clausula motorista; sql={sql}"


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


async def test_list_clicheria_inclui_4_estados_v4(mock_db):
    """AUD-W3C11-002 (pos-auditoria): clicheria listando provas ve os
    4 estados v4.0 alem dos 3 v3.0.

    Cenario critico: COM_MOTORISTA_ENTREGA_FINAL precisa estar para
    que clicheria possa concluir a ultima transicao das rotas Matriz
    e Lam.Matriz (RECEBIDA_PELA_CLICHERIA). Antes do fix: 0 linhas."""
    clicheria = make_user(setor=SetorEnum.CLICHERIA, localizacao=None)
    _setup(mock_db, user=clicheria)
    _capture_list_stmts(mock_db, count=0, rows=[])

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/")

    assert resp.status_code == 200
    sql = _compiled_sql(mock_db._captured_stmts[0])
    for estado in (
        # Legacy v3.0
        "'ENVIADA_PARA_CLICHERIA'",
        "'ENCAMINHADA_A_CLICHERIA'",
        "'RECEBIDA_PELA_CLICHERIA'",
        # v4.0 (US-007 + entrega final)
        "'ENCAMINHADA_PARA_LAMINACAO'",
        "'COM_MOTORISTA_IDA_LAMINACAO'",
        "'LAMINACAO_CONCLUIDA'",
        "'COM_MOTORISTA_ENTREGA_FINAL'",
    ):
        assert estado in sql, f"esperado {estado} na clausula clicheria; sql={sql}"


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
    # Wave 2 v4.0: rota persistida na criacao (campo `rota_projetada`
    # foi removido — frontend consome `prova.rota` diretamente).
    # `_make_prova(rota=None)` simula prova legada v3.0 ainda nao
    # backfilled (Wave 7 / Componente 21).
    assert data["rota"] is None
    # F05: apenas 1 execute (scoped), nao 2 como antes da otimizacao.
    assert mock_db.execute.call_count == 1


async def test_get_detail_prova_v4_com_rota_persistida(
    admin_user, vendedor_filial, mock_db
):
    """Wave 2 v4.0: prova v4.0 tem rota persistida desde a criacao —
    `prova.rota` substitui `rota_projetada` da v3.0.
    """
    _setup(mock_db, admin=admin_user)
    prova = _make_prova(vendedor_id=vendedor_filial.id, rota=RotaEnum.LAM_FILIAL)
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_filial.nome, vendedor_filial.localizacao),
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{prova.id}")
    assert resp.status_code == 200
    assert resp.json()["rota"] == "LAM_FILIAL"


async def test_get_detail_prova_legada_rota_null(
    admin_user, mock_db
):
    """Wave 2 v4.0: prova legada v3.0 com `rota=NULL` continua valida —
    a coluna `rota` e NULLABLE ate a Wave 7 (Componente 21) fazer o backfill.

    O campo `rota_projetada` foi removido; o frontend renderiza `rota=None`
    como "rota nao definida (legada)" na UI.
    """
    ex_vendedor = make_user(setor=SetorEnum.STUDIO, localizacao=None, is_admin=False)
    prova = _make_prova(vendedor_id=ex_vendedor.id, rota=None)
    _setup(mock_db, admin=admin_user)
    mock_db.execute.side_effect = [
        _detail_row(prova, ex_vendedor.nome, None, vendedor_setor=SetorEnum.STUDIO),
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/{prova.id}")
    assert resp.status_code == 200
    assert resp.json()["rota"] is None


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
    codigo_publico=None,
):
    """Fabrica de ProvaDigital com controle do `qr_code_hash` (para testes
    de scan). `_make_prova` acima sempre grava `"a"*64` — aqui precisamos
    do hash real que foi usado para gerar o payload de teste.

    Wave 2 v4.0: `codigo_publico` autopreenchido se nao passado.
    """
    now = datetime.now(timezone.utc)
    return ProvaDigital(
        id=uuid.uuid4(),
        nome="Prova Scan",
        nro_requerimento=nro_requerimento,
        codigo_publico=codigo_publico or f"PRV-2026-04-{uuid.uuid4().hex[:6].upper()}",
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
    inclui `origem`, `nro_requerimento`, `codigo_publico`, `status_atual`
    + `transicoes_permitidas` em `detalhes_json`.

    Wave 3 v4.0 (C10): payload com nro_req `REQ-SCAN-...` cai no fallback
    legacy `_por_nro_req` (nao casa o regex PRV-...). `origem='camera'`
    porque o caminho do `payload` e camera por definicao.
    """
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
    # Wave 3 v4.0: novos campos
    assert kwargs["detalhes"]["origem"] == "camera"
    assert kwargs["detalhes"]["codigo_publico"] == prova.codigo_publico
    # AUD-W3C10-010: payload bruto recebido para rastreabilidade forense.
    assert kwargs["detalhes"]["payload_recebido"] == payload[:64]
    assert kwargs["detalhes"]["codigo_recebido"] is None
    # Campos preservados
    assert kwargs["detalhes"]["nro_requerimento"] == nro_req
    assert kwargs["detalhes"]["status_atual"] == "CRIADA"
    assert kwargs["detalhes"]["transicoes_permitidas"] == [
        "RETIRADA_PELO_VENDEDOR"
    ]


# ─── Wave 3 v4.0 (Componente 10) — caminhos polimorficos ────────────


async def test_scan_camera_v4_qr_com_codigo_publico_resolve_pelo_codigo(
    vendedor_matriz, mock_db
):
    """Wave 3 v4.0 (C10): provas v4.0+ tem QR Code com `codigo_publico`
    no segundo campo (`3SD|PRV-...|hash[:16]`). O scan detecta o formato
    PRV via `validar_formato_codigo_publico` e usa
    `_carregar_prova_por_codigo_publico_com_scoping`.

    Antes desta entrega, o scan procurava por `nro_requerimento` mesmo
    quando o segundo campo era um codigo PRV — bug em producao para
    provas v4.0 (R-1 do analysis.md).
    """
    _setup(mock_db, user=vendedor_matriz)
    codigo_publico = "PRV-2026-05-K3T9XB"
    prova_uuid = uuid.uuid4()
    full_hash = qrcode_service.gerar_hash(prova_uuid, "REQ-V4-001")
    payload = qrcode_service.gerar_payload_qr(codigo_publico, full_hash)

    prova = _make_prova_com_hash(
        nro_requerimento="REQ-V4-001",
        codigo_publico=codigo_publico,
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
    assert data["prova"]["codigo_publico"] == codigo_publico
    assert data["transicoes_permitidas"] == ["RETIRADA_PELO_VENDEDOR"]


async def test_scan_camera_legacy_qr_continua_funcionando_via_fallback(
    vendedor_matriz, mock_db
):
    """Wave 3 v4.0 (C10): provas legacy v3.0 tem QR antigo cujo segundo
    campo e o `nro_requerimento`. O scan detecta que o formato NAO e
    `PRV-AAAA-MM-NNNNNN` e cai no fallback `_por_nro_req`. Garantia de
    compatibilidade ate Wave 7 / C21 regerar etiquetas.
    """
    _setup(mock_db, user=vendedor_matriz)
    nro_req = "456987"  # estilo legacy v3.0 — livre, numero do RPC
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
    assert resp.json()["prova"]["nro_requerimento"] == nro_req


async def test_scan_manual_codigo_publico_resolve_pela_coluna(
    vendedor_matriz, mock_db
):
    """Wave 3 v4.0 (C10): caminho de **digitacao manual** (Componente
    19, contrato pronto agora). Usuario digita `PRV-AAAA-MM-NNNNNN`,
    backend lookup por `codigo_publico`. Sem hash a validar.
    """
    _setup(mock_db, user=vendedor_matriz)
    codigo_publico = "PRV-2026-05-9PQYW2"
    prova = _make_prova_com_hash(
        nro_requerimento="qualquer-coisa",
        codigo_publico=codigo_publico,
        qr_code_hash="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        vendedor_id=vendedor_matriz.id,
        status_prova=StatusProvaEnum.CRIADA,
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"codigo": codigo_publico})

    assert resp.status_code == 200, resp.json()
    assert resp.json()["prova"]["codigo_publico"] == codigo_publico


async def test_scan_manual_codigo_formato_invalido_retorna_404_generico(
    admin_user, mock_db
):
    """Wave 3 v4.0 (C10): codigo digitado em formato invalido (nao casa
    `PRV-AAAA-MM-NNNNNN`) retorna 404 generico **sem ir ao banco** —
    proteja contra enumeracao via timing differential (DAT §8.2).

    Mensagem identica a "prova nao encontrada" para nao distinguir
    "formato invalido" de "fora do scope" — alinhado a ADR-049.
    """
    _setup(mock_db, user=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"codigo": "abc-bad"})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Prova nao encontrada"
    # NUNCA chega ao banco
    mock_db.execute.assert_not_called()


async def test_scan_manual_codigo_acima_de_32_chars_retorna_422_pydantic(
    admin_user, mock_db
):
    """AUD-W3C10-012: codigo com mais de 32 chars rejeitado por
    Pydantic ANTES de chegar ao handler. PRV-AAAA-MM-NNNNNN tem 18
    chars; max_length=32 cobre typos sem inflar superficie. Resposta
    422 e distinguivel de 404 generico, mas e razoavel para input
    fora da faixa plausivel — anti-enumeracao continua valida para
    codigos <= 32 chars que sao formato invalido.
    """
    _setup(mock_db, user=admin_user)
    codigo_muito_longo = "PRV-2026-05-" + "X" * 25  # 12 + 25 = 37 chars
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/scan", json={"codigo": codigo_muito_longo}
        )
    assert resp.status_code == 422
    # NUNCA chega ao banco (validacao Pydantic e pre-handler)
    mock_db.execute.assert_not_called()


async def test_scan_manual_codigo_valido_mas_inexistente_retorna_404(
    admin_user, mock_db
):
    """Wave 3 v4.0 (C10): codigo bem formado (`PRV-...`) mas que nao
    existe no banco retorna 404 com a mesma mensagem generica."""
    _setup(mock_db, user=admin_user)
    # Mock retorna None (nada encontrado)
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_db.execute.return_value = mock_result

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/scan", json={"codigo": "PRV-2026-05-NOPENO"}
        )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Prova nao encontrada"


async def test_scan_manual_e_camera_nao_podem_vir_juntos(admin_user, mock_db):
    """Wave 3 v4.0 (C10): `model_validator` exige XOR — fornecer ambos
    `payload` e `codigo` retorna 422 com mensagem clara.
    """
    _setup(mock_db, user=admin_user)
    full_hash, payload = _gerar_hash_e_payload("REQ-X-001")
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/scan",
            json={"payload": payload, "codigo": "PRV-2026-05-K3T9XB"},
        )
    assert resp.status_code == 422


async def test_scan_sem_payload_nem_codigo_retorna_422(admin_user, mock_db):
    """Wave 3 v4.0 (C10): body sem nenhum dos 2 campos retorna 422."""
    _setup(mock_db, user=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={})
    assert resp.status_code == 422


async def test_scan_manual_audit_log_origem_manual(vendedor_matriz, mock_db):
    """Wave 3 v4.0 (C10): audit_log do caminho manual grava
    `detalhes['origem'] = 'manual'`."""
    _setup(mock_db, user=vendedor_matriz)
    codigo_publico = "PRV-2026-05-AAAAAA"
    prova = _make_prova_com_hash(
        nro_requerimento="any",
        codigo_publico=codigo_publico,
        qr_code_hash="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
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
            resp = await ac.post(f"{PREFIX}/scan", json={"codigo": codigo_publico})

    assert resp.status_code == 200
    kwargs = mock_log.call_args.kwargs
    assert kwargs["detalhes"]["origem"] == "manual"
    assert kwargs["detalhes"]["codigo_publico"] == codigo_publico
    # AUD-W3C10-010: codigo bruto recebido (mesmo que o codigo_publico
    # neste caso porque o lookup foi bem sucedido); payload_recebido None.
    assert kwargs["detalhes"]["codigo_recebido"] == codigo_publico
    assert kwargs["detalhes"]["payload_recebido"] is None


async def test_scan_manual_codigo_fora_do_scope_retorna_404_generico(
    vendedor_matriz, mock_db
):
    """Wave 3 v4.0 (C10): vendedor tenta digitar codigo de prova de
    OUTRO vendedor → RLS no SELECT filtra (linha nao volta) → 404
    generico. Mesma mensagem que codigo inexistente."""
    _setup(mock_db, user=vendedor_matriz)
    # Mock retorna None — RLS filtrou ou prova nao existe (indistinguivel)
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_db.execute.return_value = mock_result

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/scan", json={"codigo": "PRV-2026-05-OUTRO9"}
        )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Prova nao encontrada"


async def test_scan_manual_db_error_retorna_502(admin_user, mock_db):
    """Wave 3 v4.0 (C10): erro de DB no caminho manual cai no
    handler 502."""
    _setup(mock_db, user=admin_user)
    mock_db.execute.side_effect = RuntimeError("DB indisponivel")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            f"{PREFIX}/scan", json={"codigo": "PRV-2026-05-K3T9XB"}
        )
    assert resp.status_code == 502


async def test_scan_camera_v4_db_error_retorna_502(admin_user, mock_db):
    """AUD-W3C10-013: erro de DB no caminho camera v4.0 (lookup por
    codigo_publico) tambem cai no handler 502. Espelha o teste do
    caminho manual mas envia payload v4.0 valido."""
    _setup(mock_db, user=admin_user)
    mock_db.execute.side_effect = RuntimeError("DB indisponivel")
    codigo_publico = "PRV-2026-05-K3T9XB"
    payload = f"3SD|{codigo_publico}|0123456789abcdef"

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"payload": payload})
    assert resp.status_code == 502


async def test_scan_camera_legacy_db_error_retorna_502(admin_user, mock_db):
    """AUD-W3C10-013: erro de DB no caminho camera legacy (lookup por
    nro_requerimento via fallback quando segundo campo do payload NAO
    casa formato PRV-AAAA-MM-NNNNNN) tambem retorna 502."""
    _setup(mock_db, user=admin_user)
    mock_db.execute.side_effect = RuntimeError("DB indisponivel")
    nro_req_legacy = "REQ-LEGACY-1234"
    payload = f"3SD|{nro_req_legacy}|0123456789abcdef"

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"payload": payload})
    assert resp.status_code == 502


async def test_scan_camera_v4_qr_hash_invalido_retorna_422_apos_lookup(
    vendedor_matriz, mock_db
):
    """Wave 3 v4.0 (C10): caminho camera com codigo_publico no payload —
    se o hash truncado nao bate (QR adulterado), 422 apos o SELECT
    (mesma protecao da v3.0, agora aplicada ao novo caminho)."""
    _setup(mock_db, user=vendedor_matriz)
    codigo_publico = "PRV-2026-05-HASHBAD"
    prova_uuid = uuid.uuid4()
    full_hash_correto = qrcode_service.gerar_hash(prova_uuid, "REQ-V4-HASH")
    payload_correto = qrcode_service.gerar_payload_qr(codigo_publico, full_hash_correto)
    # Adultera o hash
    parts = payload_correto.split("|")
    parts[2] = "0123456789abcdef"  # 16 chars, formato OK, mas hash errado
    payload_adulterado = "|".join(parts)

    prova = _make_prova_com_hash(
        nro_requerimento="REQ-V4-HASH",
        codigo_publico=codigo_publico,
        qr_code_hash=full_hash_correto,
        vendedor_id=vendedor_matriz.id,
        status_prova=StatusProvaEnum.CRIADA,
    )
    mock_db.execute.side_effect = [
        _detail_row(prova, vendedor_matriz.nome, vendedor_matriz.localizacao),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(f"{PREFIX}/scan", json={"payload": payload_adulterado})
    assert resp.status_code == 422
    assert "QR Code nao corresponde" in resp.json()["detail"]


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
    ciclo_atual incrementado.

    AUD-W2V4-001 (ADR-123): rota e PRESERVADA (RN-006 v4.0 + RF-009 v4.0).
    Pre-correcao: rota era zerada para None.
    """
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
    # AUD-W2V4-001 fix: rota PADRAO PRESERVADA (era None pre-fix).
    assert data["prova"]["rota"] == "PADRAO"
    assert data["movimentacao"]["status_anterior"] == "REPROVADA_PELO_VENDEDOR"
    assert data["movimentacao"]["status_novo"] == "CRIADA"
    assert data["movimentacao"]["ciclo"] == 2
    assert data["movimentacao"]["rota_no_momento"] == "PADRAO"
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
