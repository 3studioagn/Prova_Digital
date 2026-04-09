"""Testes do audit_service (ADR-039)."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models import AuditLog
from app.services.audit_service import log_audit


@pytest.fixture
def fake_db():
    """AsyncSession mock com add() sincrono e flush() async."""
    db = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def fake_request():
    """FastAPI Request mock com client + headers."""
    req = MagicMock()
    req.client = MagicMock(host="10.0.0.42")
    req.headers = {"user-agent": "TestAgent/1.0"}
    return req


async def test_log_audit_happy_path(fake_db, fake_request):
    usuario_id = uuid.uuid4()
    prova_id = uuid.uuid4()

    entry = await log_audit(
        fake_db,
        acao="criar_prova",
        usuario_id=usuario_id,
        prova_id=prova_id,
        detalhes={"campo": "valor"},
        request=fake_request,
    )

    assert isinstance(entry, AuditLog)
    assert entry.acao == "criar_prova"
    assert entry.usuario_id == usuario_id
    assert entry.prova_id == prova_id
    assert entry.detalhes_json == {"campo": "valor"}
    assert entry.ip_address == "10.0.0.42"
    assert entry.user_agent == "TestAgent/1.0"
    fake_db.add.assert_called_once_with(entry)
    fake_db.flush.assert_awaited_once()


async def test_log_audit_sem_request(fake_db):
    entry = await log_audit(
        fake_db,
        acao="atualizar_config",
        usuario_id=uuid.uuid4(),
        detalhes={"chave": "tempo_atraso_horas_uteis", "novo_valor": 72},
    )
    assert entry.ip_address is None
    assert entry.user_agent is None
    assert entry.prova_id is None
    fake_db.add.assert_called_once()
    fake_db.flush.assert_awaited_once()


async def test_log_audit_sem_client_no_request(fake_db):
    req = MagicMock()
    req.client = None
    req.headers = {"user-agent": "Agent"}
    entry = await log_audit(
        fake_db,
        acao="acao",
        usuario_id=uuid.uuid4(),
        request=req,
    )
    assert entry.ip_address is None
    assert entry.user_agent == "Agent"


async def test_log_audit_user_agent_truncado(fake_db):
    req = MagicMock()
    req.client = MagicMock(host="1.1.1.1")
    ua = "X" * 5000
    req.headers = {"user-agent": ua}
    entry = await log_audit(
        fake_db,
        acao="acao",
        usuario_id=uuid.uuid4(),
        request=req,
    )
    assert len(entry.user_agent) == 2000  # truncado
