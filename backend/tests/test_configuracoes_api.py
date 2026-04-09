"""Integration tests for /api/v1/configuracoes endpoints (Componente 09)."""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

from httpx import ASGITransport, AsyncClient

from app.api.deps import get_admin_user, get_current_user
from app.db.models import ConfiguracaoSistema
from app.db.session import get_db
from app.main import app

BASE = "http://test"
PREFIX = "/api/v1/configuracoes"


# ─── Helpers ────────────────────────────────────────────────────────────


def _scalar(val=None):
    r = MagicMock()
    r.scalar_one_or_none.return_value = val
    r.scalar.return_value = val
    return r


def _scalars(items):
    r = MagicMock()
    s = MagicMock()
    s.all.return_value = items
    r.scalars.return_value = s
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


def _make_config(
    chave: str,
    valor,
    descricao: str | None = None,
    updated_by=None,
):
    return ConfiguracaoSistema(
        id=uuid.uuid4(),
        chave=chave,
        valor=valor,
        descricao=descricao or f"desc de {chave}",
        updated_by=updated_by,
        updated_at=datetime.now(timezone.utc),
    )


_DEFAULT_TEMPLATE = {
    "nome": "padrao",
    "formato": "A4",
    "logo_enabled": True,
    "mostrar_data_criacao": False,
}


# ─── GET / ──────────────────────────────────────────────────────────────


async def test_list_configuracoes_happy(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    cfgs = [
        _make_config("template_etiqueta", _DEFAULT_TEMPLATE),
        _make_config("tempo_atraso_horas_uteis", 48),
    ]
    mock_db.execute.return_value = _scalars(cfgs)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    chaves = {item["chave"] for item in data["items"]}
    assert chaves == {"template_etiqueta", "tempo_atraso_horas_uteis"}


async def test_list_configuracoes_requires_admin(regular_user, mock_db):
    _setup(mock_db, user=regular_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/")
    assert resp.status_code == 403


async def test_list_configuracoes_no_auth(mock_db):
    _setup(mock_db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/")
    assert resp.status_code == 401


# ─── GET /{chave} ───────────────────────────────────────────────────────


async def test_get_configuracao_tempo_atraso_happy(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    cfg = _make_config("tempo_atraso_horas_uteis", 48)
    mock_db.execute.return_value = _scalar(cfg)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/tempo_atraso_horas_uteis")

    assert resp.status_code == 200
    assert resp.json()["chave"] == "tempo_atraso_horas_uteis"
    assert resp.json()["valor"] == 48


async def test_get_configuracao_template_happy(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    cfg = _make_config("template_etiqueta", _DEFAULT_TEMPLATE)
    mock_db.execute.return_value = _scalar(cfg)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/template_etiqueta")

    assert resp.status_code == 200
    assert resp.json()["chave"] == "template_etiqueta"
    assert resp.json()["valor"]["formato"] == "A4"


async def test_get_configuracao_nao_whitelisted(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/chave_inexistente")
    assert resp.status_code == 404
    assert "nao e editavel" in resp.json()["detail"]
    # Nao chega a executar SELECT — bloqueado pela whitelist.
    mock_db.execute.assert_not_called()


async def test_get_configuracao_whitelisted_mas_ausente_no_db(admin_user, mock_db):
    """Caso edge: chave esta na whitelist mas nao foi seedada."""
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/tempo_atraso_horas_uteis")
    assert resp.status_code == 404
    assert "nao esta cadastrada" in resp.json()["detail"]


async def test_get_configuracao_requires_admin(regular_user, mock_db):
    _setup(mock_db, user=regular_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get(f"{PREFIX}/tempo_atraso_horas_uteis")
    assert resp.status_code == 403


# ─── PATCH /tempo_atraso_horas_uteis ────────────────────────────────────


async def test_patch_tempo_atraso_happy(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    cfg = _make_config("tempo_atraso_horas_uteis", 48)
    mock_db.execute.return_value = _scalar(cfg)

    async def _refresh(obj):
        obj.updated_at = datetime.now(timezone.utc)
    mock_db.refresh.side_effect = _refresh

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(
            f"{PREFIX}/tempo_atraso_horas_uteis",
            json={"valor": 72},
        )

    assert resp.status_code == 200, resp.json()
    data = resp.json()
    assert data["valor"] == 72
    assert cfg.valor == 72
    assert cfg.updated_by == admin_user.id
    mock_db.flush.assert_awaited()
    mock_db.commit.assert_awaited_once()
    # audit_log foi inserido via db.add dentro de log_audit
    mock_db.add.assert_called_once()


async def test_patch_tempo_atraso_rejects_zero(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    cfg = _make_config("tempo_atraso_horas_uteis", 48)
    mock_db.execute.return_value = _scalar(cfg)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(
            f"{PREFIX}/tempo_atraso_horas_uteis",
            json={"valor": 0},
        )
    assert resp.status_code == 422
    assert "entre 1 e 168" in resp.json()["detail"]


async def test_patch_tempo_atraso_rejects_negative(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(
        _make_config("tempo_atraso_horas_uteis", 48)
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(
            f"{PREFIX}/tempo_atraso_horas_uteis",
            json={"valor": -5},
        )
    assert resp.status_code == 422


async def test_patch_tempo_atraso_rejects_above_max(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(
        _make_config("tempo_atraso_horas_uteis", 48)
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(
            f"{PREFIX}/tempo_atraso_horas_uteis",
            json={"valor": 169},
        )
    assert resp.status_code == 422


async def test_patch_tempo_atraso_rejects_string(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(
        _make_config("tempo_atraso_horas_uteis", 48)
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(
            f"{PREFIX}/tempo_atraso_horas_uteis",
            json={"valor": "72"},
        )
    assert resp.status_code == 422
    assert "inteiro" in resp.json()["detail"]


async def test_patch_tempo_atraso_rejects_bool(admin_user, mock_db):
    """bool e subclass de int em Python — a validacao precisa rejeitar explicitamente."""
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(
        _make_config("tempo_atraso_horas_uteis", 48)
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(
            f"{PREFIX}/tempo_atraso_horas_uteis",
            json={"valor": True},
        )
    assert resp.status_code == 422


# ─── PATCH /template_etiqueta ───────────────────────────────────────────


async def test_patch_template_etiqueta_happy(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    cfg = _make_config("template_etiqueta", _DEFAULT_TEMPLATE)
    mock_db.execute.return_value = _scalar(cfg)

    async def _refresh(obj):
        obj.updated_at = datetime.now(timezone.utc)
    mock_db.refresh.side_effect = _refresh

    novo_template = {
        "nome": "padrao",
        "formato": "80mm_thermal",
        "logo_enabled": False,
        "mostrar_data_criacao": True,
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(
            f"{PREFIX}/template_etiqueta",
            json={"valor": novo_template},
        )

    assert resp.status_code == 200, resp.json()
    assert cfg.valor == novo_template
    assert cfg.updated_by == admin_user.id


async def test_patch_template_rejects_formato_invalido(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(
        _make_config("template_etiqueta", _DEFAULT_TEMPLATE)
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(
            f"{PREFIX}/template_etiqueta",
            json={"valor": {**_DEFAULT_TEMPLATE, "formato": "Letter"}},
        )
    assert resp.status_code == 422
    assert "formato" in resp.json()["detail"].lower()


async def test_patch_template_rejects_campo_faltando(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(
        _make_config("template_etiqueta", _DEFAULT_TEMPLATE)
    )

    incompleto = {k: v for k, v in _DEFAULT_TEMPLATE.items() if k != "logo_enabled"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(
            f"{PREFIX}/template_etiqueta",
            json={"valor": incompleto},
        )
    assert resp.status_code == 422
    assert "logo_enabled" in resp.json()["detail"]


async def test_patch_template_rejects_tipo_errado(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(
        _make_config("template_etiqueta", _DEFAULT_TEMPLATE)
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(
            f"{PREFIX}/template_etiqueta",
            json={"valor": {**_DEFAULT_TEMPLATE, "logo_enabled": "sim"}},
        )
    assert resp.status_code == 422
    assert "logo_enabled" in resp.json()["detail"]


async def test_patch_template_rejects_nao_objeto(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    mock_db.execute.return_value = _scalar(
        _make_config("template_etiqueta", _DEFAULT_TEMPLATE)
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(
            f"{PREFIX}/template_etiqueta",
            json={"valor": "padrao"},  # string em vez de objeto
        )
    assert resp.status_code == 422
    assert "objeto" in resp.json()["detail"]


async def test_patch_template_descarta_campos_extras(admin_user, mock_db):
    """Campos extras no body sao descartados — nao causam erro."""
    _setup(mock_db, admin=admin_user)
    cfg = _make_config("template_etiqueta", _DEFAULT_TEMPLATE)
    mock_db.execute.return_value = _scalar(cfg)

    async def _refresh(obj):
        obj.updated_at = datetime.now(timezone.utc)
    mock_db.refresh.side_effect = _refresh

    with_extras = {**_DEFAULT_TEMPLATE, "campo_desconhecido": "foo"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(
            f"{PREFIX}/template_etiqueta",
            json={"valor": with_extras},
        )
    assert resp.status_code == 200
    assert "campo_desconhecido" not in cfg.valor


# ─── PATCH edge cases ──────────────────────────────────────────────────


async def test_patch_chave_nao_whitelisted(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(
            f"{PREFIX}/feature_flag_foo",
            json={"valor": True},
        )
    assert resp.status_code == 404
    mock_db.execute.assert_not_called()


async def test_patch_requires_admin(regular_user, mock_db):
    _setup(mock_db, user=regular_user)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(
            f"{PREFIX}/tempo_atraso_horas_uteis",
            json={"valor": 72},
        )
    assert resp.status_code == 403


async def test_patch_no_auth(mock_db):
    _setup(mock_db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(
            f"{PREFIX}/tempo_atraso_horas_uteis",
            json={"valor": 72},
        )
    assert resp.status_code == 401


async def test_patch_commit_failure_rollback(admin_user, mock_db):
    _setup(mock_db, admin=admin_user)
    cfg = _make_config("tempo_atraso_horas_uteis", 48)
    mock_db.execute.return_value = _scalar(cfg)
    mock_db.commit.side_effect = Exception("DB unreachable")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(
            f"{PREFIX}/tempo_atraso_horas_uteis",
            json={"valor": 72},
        )
    assert resp.status_code == 500
    mock_db.rollback.assert_awaited()


async def test_patch_atualiza_descricao(admin_user, mock_db):
    """Descricao e opcional — quando enviada, substitui a atual."""
    _setup(mock_db, admin=admin_user)
    cfg = _make_config("tempo_atraso_horas_uteis", 48, descricao="desc antiga")
    mock_db.execute.return_value = _scalar(cfg)

    async def _refresh(obj):
        obj.updated_at = datetime.now(timezone.utc)
    mock_db.refresh.side_effect = _refresh

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(
            f"{PREFIX}/tempo_atraso_horas_uteis",
            json={"valor": 72, "descricao": "nova descricao"},
        )
    assert resp.status_code == 200
    assert cfg.descricao == "nova descricao"


async def test_patch_sem_descricao_mantem_atual(admin_user, mock_db):
    """Sem descricao no body, a descricao atual nao muda."""
    _setup(mock_db, admin=admin_user)
    cfg = _make_config(
        "tempo_atraso_horas_uteis", 48, descricao="desc atual preservada"
    )
    mock_db.execute.return_value = _scalar(cfg)

    async def _refresh(obj):
        obj.updated_at = datetime.now(timezone.utc)
    mock_db.refresh.side_effect = _refresh

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.patch(
            f"{PREFIX}/tempo_atraso_horas_uteis",
            json={"valor": 72},
        )
    assert resp.status_code == 200
    assert cfg.descricao == "desc atual preservada"
