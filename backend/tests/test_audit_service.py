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


# ─── F04 (auditoria externa Wave 2) — X-Forwarded-For / X-Real-IP ─────────


async def test_log_audit_usa_x_forwarded_for_quando_presente(fake_db):
    """F04: em producao atras do Railway, o IP real do cliente vem no header
    X-Forwarded-For. `request.client.host` e o IP do gateway do Railway e
    NAO deve ser usado quando XFF esta presente.
    """
    req = MagicMock()
    req.client = MagicMock(host="172.18.0.5")  # gateway Railway
    req.headers = {
        "x-forwarded-for": "203.0.113.42",  # IP real do cliente
        "user-agent": "Mozilla/5.0",
    }
    entry = await log_audit(
        fake_db,
        acao="acao",
        usuario_id=uuid.uuid4(),
        request=req,
    )
    assert entry.ip_address == "203.0.113.42"


async def test_log_audit_x_forwarded_for_pega_primeiro_ip_da_cadeia(fake_db):
    """Quando X-Forwarded-For tem multiplos IPs (cliente, proxy1, proxy2),
    usamos o PRIMEIRO — e o cliente original. Trailing proxies sao
    appendados pela cadeia de proxies.
    """
    req = MagicMock()
    req.client = MagicMock(host="10.0.0.1")
    req.headers = {
        "x-forwarded-for": "203.0.113.42, 172.18.0.5, 10.0.0.1",
        "user-agent": "UA",
    }
    entry = await log_audit(
        fake_db,
        acao="acao",
        usuario_id=uuid.uuid4(),
        request=req,
    )
    assert entry.ip_address == "203.0.113.42"


async def test_log_audit_usa_x_real_ip_como_fallback(fake_db):
    """Se X-Forwarded-For ausente mas X-Real-IP presente (alguns proxies),
    usa X-Real-IP.
    """
    req = MagicMock()
    req.client = MagicMock(host="172.18.0.5")
    req.headers = {
        "x-real-ip": "198.51.100.7",
        "user-agent": "UA",
    }
    entry = await log_audit(
        fake_db,
        acao="acao",
        usuario_id=uuid.uuid4(),
        request=req,
    )
    assert entry.ip_address == "198.51.100.7"


async def test_log_audit_fallback_para_client_host_sem_headers(fake_db):
    """Sem X-Forwarded-For nem X-Real-IP, usa request.client.host.
    Este e o caminho de dev local e testes.
    """
    req = MagicMock()
    req.client = MagicMock(host="127.0.0.1")
    req.headers = {"user-agent": "UA"}
    entry = await log_audit(
        fake_db,
        acao="acao",
        usuario_id=uuid.uuid4(),
        request=req,
    )
    assert entry.ip_address == "127.0.0.1"


async def test_log_audit_x_forwarded_for_vazio_cai_no_fallback(fake_db):
    """Se X-Forwarded-For esta presente mas vazio (edge case), ignora e
    cai no fallback.
    """
    req = MagicMock()
    req.client = MagicMock(host="127.0.0.1")
    req.headers = {"x-forwarded-for": "   ", "user-agent": "UA"}
    entry = await log_audit(
        fake_db,
        acao="acao",
        usuario_id=uuid.uuid4(),
        request=req,
    )
    assert entry.ip_address == "127.0.0.1"
