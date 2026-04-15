"""Testes do auditoria_query — cursor codec, timezone helpers, filter
builder e funcoes `listar_audit_logs` / `buscar_audit_log_por_id` com
mock de AsyncSession (Wave 6 Bloco 6.2).

Meta de cobertura: >=90% em `app/services/auditoria_query.py`.
Os testes de integracao HTTP ficam em `test_auditoria_api.py`.
"""
from __future__ import annotations

import base64
import json
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models import AuditLog, ProvaDigital, SetorEnum, Usuario
from app.domain.schemas.auditoria import AuditoriaFiltros, TipoEventoEnum
from app.services.auditoria_query import (
    UTC,
    AuditLogSemUsuarioError,
    CursorInvalidoError,
    _build_filter_clauses,
    _tipo_evento_para_clause,
    buscar_audit_log_por_id,
    data_fim_brt_para_utc,
    data_inicio_brt_para_utc,
    decode_cursor,
    encode_cursor,
    listar_audit_logs,
)

# =============================================================================
# Helpers
# =============================================================================


def _make_audit_log(
    *,
    acao: str = "criar_prova",
    detalhes: dict | None = None,
    usuario_id: uuid.UUID | None = None,
    prova_id: uuid.UUID | None = None,
    created_at: datetime | None = None,
    log_id: uuid.UUID | None = None,
    ip_address: str | None = "127.0.0.1",
    user_agent: str | None = "UA",
) -> AuditLog:
    log = MagicMock(spec=AuditLog)
    log.id = log_id or uuid.uuid4()
    log.acao = acao
    log.detalhes_json = detalhes
    log.usuario_id = usuario_id or uuid.uuid4()
    log.prova_id = prova_id
    log.ip_address = ip_address
    log.user_agent = user_agent
    log.created_at = created_at or datetime.now(timezone.utc)
    return log


def _make_usuario(
    *,
    is_admin: bool = True,
    nome: str = "Admin",
    setor: SetorEnum = SetorEnum.STUDIO,
) -> Usuario:
    u = Usuario(
        id=uuid.uuid4(),
        auth_uid=uuid.uuid4(),
        nome=nome,
        email=f"{nome.lower()}@test.com",
        setor=setor,
        localizacao=None,
        is_admin=is_admin,
        ativo=True,
        created_by=None,
    )
    u.created_at = datetime.now(timezone.utc)
    u.updated_at = datetime.now(timezone.utc)
    return u


def _make_prova(nro_req: str = "REQ-001", nome: str = "Prova Teste") -> ProvaDigital:
    p = MagicMock(spec=ProvaDigital)
    p.id = uuid.uuid4()
    p.nro_requerimento = nro_req
    p.nome = nome
    return p


def _mock_list_result(rows: list[tuple]) -> MagicMock:
    """Simula o Result.all() de um SELECT com tuplas (log, usuario, prova)."""
    r = MagicMock()
    r.all.return_value = rows
    return r


def _mock_first_result(row: tuple | None) -> MagicMock:
    """Simula o Result.first() de um SELECT pontual."""
    r = MagicMock()
    r.first.return_value = row
    return r


def _mock_count_result(value: int) -> MagicMock:
    """Simula o Result.scalar_one() de um SELECT count."""
    r = MagicMock()
    r.scalar_one.return_value = value
    return r


@pytest.fixture
def fake_db():
    """AsyncSession mock com `execute` AsyncMock por teste (configurado
    em cada caso via `side_effect` ou `return_value`)."""
    db = AsyncMock()
    return db


# =============================================================================
# 1. Cursor codec
# =============================================================================


def test_encode_decode_cursor_roundtrip():
    ts = datetime(2026, 4, 14, 12, 30, 45, 123456, tzinfo=timezone.utc)
    log_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
    cursor = encode_cursor(ts, log_id)
    assert isinstance(cursor, str)
    assert len(cursor) > 0

    ts2, id2 = decode_cursor(cursor)
    assert ts2 == ts
    assert id2 == log_id


def test_encode_cursor_e_urlsafe():
    """Cursor nao deve conter caracteres `+`/`/` (base64 padrao), apenas
    `-`/`_` (urlsafe). Importante para uso como query param sem escape."""
    ts = datetime(2026, 4, 14, 12, 30, 45, tzinfo=timezone.utc)
    cursor = encode_cursor(ts, uuid.uuid4())
    assert "+" not in cursor
    assert "/" not in cursor


def test_decode_cursor_base64_invalido_levanta():
    with pytest.raises(CursorInvalidoError, match="base64"):
        decode_cursor("@@@nao-eh-base64@@@")


def test_decode_cursor_json_invalido_levanta():
    invalid_json_b64 = base64.urlsafe_b64encode(b"nao eh json {{{").decode("ascii")
    with pytest.raises(CursorInvalidoError, match="JSON"):
        decode_cursor(invalid_json_b64)


def test_decode_cursor_json_nao_objeto_levanta():
    lista_b64 = base64.urlsafe_b64encode(b'["foo"]').decode("ascii")
    with pytest.raises(CursorInvalidoError, match="objeto"):
        decode_cursor(lista_b64)


def test_decode_cursor_sem_chave_c_levanta():
    data_b64 = base64.urlsafe_b64encode(
        json.dumps({"i": str(uuid.uuid4())}).encode()
    ).decode("ascii")
    with pytest.raises(CursorInvalidoError, match="'c'"):
        decode_cursor(data_b64)


def test_decode_cursor_sem_chave_i_levanta():
    data_b64 = base64.urlsafe_b64encode(
        json.dumps({"c": "2026-04-14T00:00:00+00:00"}).encode()
    ).decode("ascii")
    with pytest.raises(CursorInvalidoError, match="'i'"):
        decode_cursor(data_b64)


def test_decode_cursor_datetime_invalido_levanta():
    data_b64 = base64.urlsafe_b64encode(
        json.dumps({"c": "nao-eh-data", "i": str(uuid.uuid4())}).encode()
    ).decode("ascii")
    with pytest.raises(CursorInvalidoError, match="datetime"):
        decode_cursor(data_b64)


def test_decode_cursor_uuid_invalido_levanta():
    data_b64 = base64.urlsafe_b64encode(
        json.dumps({"c": "2026-04-14T00:00:00+00:00", "i": "nao-eh-uuid"}).encode()
    ).decode("ascii")
    with pytest.raises(CursorInvalidoError, match="UUID"):
        decode_cursor(data_b64)


# =============================================================================
# 2. Timezone helpers
# =============================================================================


def test_data_inicio_brt_para_utc_14_abril():
    """`date(2026, 4, 14)` -> `2026-04-14 03:00:00+00:00` UTC."""
    utc = data_inicio_brt_para_utc(date(2026, 4, 14))
    assert utc.year == 2026
    assert utc.month == 4
    assert utc.day == 14
    assert utc.hour == 3
    assert utc.minute == 0
    assert utc.second == 0
    assert utc.tzinfo == UTC


def test_data_fim_brt_para_utc_14_abril():
    """`date(2026, 4, 14)` fim -> `2026-04-15 03:00:00+00:00` UTC (exclusivo)."""
    utc = data_fim_brt_para_utc(date(2026, 4, 14))
    assert utc.year == 2026
    assert utc.month == 4
    assert utc.day == 15
    assert utc.hour == 3
    assert utc.tzinfo == UTC


def test_data_fim_maior_que_inicio_no_mesmo_dia():
    """Para o mesmo `date`, `fim` e estritamente > `inicio` em 24 horas."""
    d = date(2026, 4, 14)
    diff = data_fim_brt_para_utc(d) - data_inicio_brt_para_utc(d)
    assert diff.total_seconds() == 24 * 3600


def test_data_inicio_virada_do_mes():
    """`date(2026, 5, 1)` vira `2026-05-01 03:00:00 UTC`."""
    utc = data_inicio_brt_para_utc(date(2026, 5, 1))
    assert utc.month == 5
    assert utc.day == 1


def test_data_fim_ultimo_dia_do_mes():
    """`date(2026, 4, 30)` fim vira `2026-05-01 03:00:00 UTC`."""
    utc = data_fim_brt_para_utc(date(2026, 4, 30))
    assert utc.month == 5
    assert utc.day == 1


# =============================================================================
# 3. _tipo_evento_para_clause — verifica compilacao e contem termos-chave
# =============================================================================


@pytest.mark.parametrize("tipo", list(TipoEventoEnum))
def test_tipo_evento_para_clause_compila(tipo: TipoEventoEnum):
    """Toda `TipoEventoEnum` deve gerar uma clause compilavel (verifica
    que o mapping esta completo — se alguem adicionar um enum novo sem
    atualizar o mapping, este teste pega via `raise ValueError`)."""
    clause = _tipo_evento_para_clause(tipo)
    assert clause is not None
    sql_str = str(clause.compile(compile_kwargs={"literal_binds": True}))
    assert len(sql_str) > 0


def test_tipo_evento_cancelamento_menciona_cancelada():
    clause = _tipo_evento_para_clause(TipoEventoEnum.CANCELAMENTO)
    sql_str = str(clause.compile(compile_kwargs={"literal_binds": True}))
    assert "transitar_status" in sql_str
    assert "CANCELADA" in sql_str


def test_tipo_evento_reprovacao_menciona_reprovada():
    clause = _tipo_evento_para_clause(TipoEventoEnum.REPROVACAO)
    sql_str = str(clause.compile(compile_kwargs={"literal_binds": True}))
    assert "transitar_status" in sql_str
    assert "REPROVADA_PELO_VENDEDOR" in sql_str


def test_tipo_evento_transicao_status_exclui_cancelada_e_reprovada():
    clause = _tipo_evento_para_clause(TipoEventoEnum.TRANSICAO_STATUS)
    sql_str = str(clause.compile(compile_kwargs={"literal_binds": True}))
    assert "transitar_status" in sql_str
    # Deve mencionar as duas strings que ele exclui
    assert "CANCELADA" in sql_str
    assert "REPROVADA_PELO_VENDEDOR" in sql_str


def test_tipo_evento_criacao_prova_clause_simples():
    clause = _tipo_evento_para_clause(TipoEventoEnum.CRIACAO_PROVA)
    sql_str = str(clause.compile(compile_kwargs={"literal_binds": True}))
    assert "criar_prova" in sql_str


def test_tipo_evento_para_clause_nao_mapeado_levanta():
    """Defensivo: se um `TipoEventoEnum` nao bater com nenhum caso conhecido
    (ex: Wave futura adiciona enum sem atualizar o mapping), levanta
    `ValueError` claramente em vez de silenciosamente filtrar nada.

    Simulamos isso passando um `MagicMock` que nao bate com nenhum enum
    conhecido via `==`. O `type: ignore` e intencional — em producao o
    type checker previne isso; aqui testamos o safety net runtime.
    """
    fake_tipo = MagicMock()
    # MagicMock nao bate com TipoEventoEnum.X em nenhum == (retorna False
    # em todos os branches), cai no raise final.
    with pytest.raises(ValueError, match="nao mapeado"):
        _tipo_evento_para_clause(fake_tipo)  # type: ignore[arg-type]


# =============================================================================
# 4. _build_filter_clauses
# =============================================================================


def test_build_filter_clauses_sem_filtros_vazio():
    assert _build_filter_clauses(AuditoriaFiltros()) == []


def test_build_filter_clauses_periodo_duas_clauses():
    f = AuditoriaFiltros(data_inicio=date(2026, 4, 10), data_fim=date(2026, 4, 14))
    clauses = _build_filter_clauses(f)
    assert len(clauses) == 2


def test_build_filter_clauses_usuario_id_uma_clause():
    f = AuditoriaFiltros(usuario_id=uuid.uuid4())
    assert len(_build_filter_clauses(f)) == 1


def test_build_filter_clauses_nro_requerimento_uma_clause():
    f = AuditoriaFiltros(nro_requerimento="REQ-001")
    assert len(_build_filter_clauses(f)) == 1


def test_build_filter_clauses_acao_multipla_uma_clause():
    """`acao.in_(...)` conta como 1 clause mesmo com varios valores."""
    f = AuditoriaFiltros(acao=["criar_prova", "escanear_prova"])
    assert len(_build_filter_clauses(f)) == 1


def test_build_filter_clauses_tipo_evento_multiplo_uma_clause():
    """`or_(...)` conta como 1 clause mesmo com varios tipos."""
    f = AuditoriaFiltros(
        tipo_evento=[TipoEventoEnum.CANCELAMENTO, TipoEventoEnum.REPROVACAO]
    )
    assert len(_build_filter_clauses(f)) == 1


def test_build_filter_clauses_combinado_soma():
    """Periodo (2) + usuario (1) + nro_req (1) + acao (1) = 5."""
    f = AuditoriaFiltros(
        data_inicio=date(2026, 4, 1),
        data_fim=date(2026, 4, 14),
        usuario_id=uuid.uuid4(),
        nro_requerimento="REQ-001",
        acao=["criar_prova"],
    )
    assert len(_build_filter_clauses(f)) == 5


# =============================================================================
# 5. listar_audit_logs — mock db.execute
# =============================================================================


async def test_listar_vazio(fake_db):
    fake_db.execute = AsyncMock(
        side_effect=[_mock_list_result([]), _mock_count_result(0)]
    )
    resp = await listar_audit_logs(fake_db, AuditoriaFiltros())
    assert resp.items == []
    assert resp.has_more is False
    assert resp.next_cursor is None
    assert resp.total_estimado == 0


async def test_listar_com_dados_sem_has_more(fake_db):
    usuario = _make_usuario()
    prova = _make_prova()
    log1 = _make_audit_log(acao="criar_prova", prova_id=prova.id)
    log2 = _make_audit_log(acao="escanear_prova", prova_id=prova.id)

    fake_db.execute = AsyncMock(
        side_effect=[
            _mock_list_result([(log1, usuario, prova), (log2, usuario, prova)]),
            _mock_count_result(2),
        ]
    )
    resp = await listar_audit_logs(fake_db, AuditoriaFiltros(limit=10))
    assert len(resp.items) == 2
    assert resp.has_more is False
    assert resp.next_cursor is None
    assert resp.total_estimado == 2
    # Projecao funcionou
    assert resp.items[0].tipo_evento == TipoEventoEnum.CRIACAO_PROVA
    assert resp.items[0].tipo_evento_label == "Criacao de prova"
    assert resp.items[1].tipo_evento == TipoEventoEnum.ESCANEAMENTO


async def test_listar_com_has_more_e_next_cursor(fake_db):
    """Limit=2, mock retorna 3 rows (N+1 pattern) -> has_more=True,
    retorna apenas 2 items, next_cursor aponta para o segundo (ultimo
    da pagina retornada)."""
    usuario = _make_usuario()
    t1 = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 4, 14, 11, 0, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 4, 14, 10, 0, 0, tzinfo=timezone.utc)

    log_a = _make_audit_log(created_at=t1)
    log_b = _make_audit_log(created_at=t2)
    log_c = _make_audit_log(created_at=t3)

    fake_db.execute = AsyncMock(
        side_effect=[
            _mock_list_result(
                [
                    (log_a, usuario, None),
                    (log_b, usuario, None),
                    (log_c, usuario, None),
                ]
            ),
            _mock_count_result(100),
        ]
    )
    resp = await listar_audit_logs(fake_db, AuditoriaFiltros(limit=2))
    assert len(resp.items) == 2
    assert resp.has_more is True
    assert resp.next_cursor is not None
    assert resp.total_estimado == 100

    cts, cid = decode_cursor(resp.next_cursor)
    assert cts == t2
    assert cid == log_b.id


async def test_listar_com_cursor_aplicado(fake_db):
    """Cursor valido e aplicado no WHERE (nao levanta)."""
    ts = datetime(2026, 4, 14, 10, 0, 0, tzinfo=timezone.utc)
    cursor = encode_cursor(ts, uuid.uuid4())

    fake_db.execute = AsyncMock(
        side_effect=[_mock_list_result([]), _mock_count_result(0)]
    )
    resp = await listar_audit_logs(
        fake_db, AuditoriaFiltros(cursor=cursor, limit=10)
    )
    assert resp.items == []
    assert fake_db.execute.call_count == 2


async def test_listar_cursor_invalido_levanta(fake_db):
    with pytest.raises(CursorInvalidoError):
        await listar_audit_logs(
            fake_db, AuditoriaFiltros(cursor="nao-eh-base64-valido-@@@")
        )


async def test_listar_cancelamento_projecao(fake_db):
    """Log `transitar_status` + `para=CANCELADA` vira `CANCELAMENTO`."""
    usuario = _make_usuario()
    prova = _make_prova()
    log = _make_audit_log(
        acao="transitar_status",
        detalhes={
            "de": "APROVADA_PELO_VENDEDOR",
            "para": "CANCELADA",
            "motivo_cancelamento": "cliente cancelou",
        },
        prova_id=prova.id,
    )
    fake_db.execute = AsyncMock(
        side_effect=[
            _mock_list_result([(log, usuario, prova)]),
            _mock_count_result(1),
        ]
    )
    resp = await listar_audit_logs(fake_db, AuditoriaFiltros())
    assert resp.items[0].tipo_evento == TipoEventoEnum.CANCELAMENTO
    assert resp.items[0].tipo_evento_label == "Cancelamento"
    assert resp.items[0].detalhes_json is not None
    assert resp.items[0].detalhes_json["para"] == "CANCELADA"


async def test_listar_prova_none_para_alteracao_config(fake_db):
    usuario = _make_usuario()
    log = _make_audit_log(
        acao="atualizar_configuracao",
        detalhes={"chave": "tempo", "valor_novo": 72, "valor_anterior": 48},
        prova_id=None,
    )
    fake_db.execute = AsyncMock(
        side_effect=[_mock_list_result([(log, usuario, None)]), _mock_count_result(1)]
    )
    resp = await listar_audit_logs(fake_db, AuditoriaFiltros())
    assert resp.items[0].prova is None
    assert resp.items[0].tipo_evento == TipoEventoEnum.ALTERACAO_CONFIG


async def test_listar_usuario_orfao_levanta(fake_db):
    """Defensivo: se usuario=None em um row, levanta AuditLogSemUsuarioError."""
    log = _make_audit_log()
    fake_db.execute = AsyncMock(
        side_effect=[_mock_list_result([(log, None, None)]), _mock_count_result(1)]
    )
    with pytest.raises(AuditLogSemUsuarioError):
        await listar_audit_logs(fake_db, AuditoriaFiltros())


async def test_listar_ip_address_convertido_para_str(fake_db):
    """`ip_address` da tabela e INET — converter para str antes do DTO."""
    usuario = _make_usuario()
    log = _make_audit_log(ip_address="203.0.113.42")
    fake_db.execute = AsyncMock(
        side_effect=[_mock_list_result([(log, usuario, None)]), _mock_count_result(1)]
    )
    resp = await listar_audit_logs(fake_db, AuditoriaFiltros())
    assert resp.items[0].ip_address == "203.0.113.42"


async def test_listar_ip_address_none_permanece_none(fake_db):
    usuario = _make_usuario()
    log = _make_audit_log(ip_address=None)
    fake_db.execute = AsyncMock(
        side_effect=[_mock_list_result([(log, usuario, None)]), _mock_count_result(1)]
    )
    resp = await listar_audit_logs(fake_db, AuditoriaFiltros())
    assert resp.items[0].ip_address is None


async def test_listar_filtros_echoed_em_filtros_aplicados(fake_db):
    """Os filtros de entrada devem aparecer em `filtros_aplicados`."""
    fake_db.execute = AsyncMock(
        side_effect=[_mock_list_result([]), _mock_count_result(0)]
    )
    uid = uuid.uuid4()
    resp = await listar_audit_logs(
        fake_db,
        AuditoriaFiltros(
            data_inicio=date(2026, 4, 1),
            data_fim=date(2026, 4, 14),
            usuario_id=uid,
            acao=["criar_prova"],
            limit=25,
        ),
    )
    assert resp.filtros_aplicados.data_inicio == date(2026, 4, 1)
    assert resp.filtros_aplicados.data_fim == date(2026, 4, 14)
    assert resp.filtros_aplicados.usuario_id == uid
    assert resp.filtros_aplicados.acao == ["criar_prova"]
    assert resp.filtros_aplicados.limit == 25


# =============================================================================
# 6. buscar_audit_log_por_id
# =============================================================================


async def test_buscar_por_id_encontrado(fake_db):
    usuario = _make_usuario()
    prova = _make_prova()
    log = _make_audit_log(acao="criar_prova", prova_id=prova.id)

    fake_db.execute = AsyncMock(
        return_value=_mock_first_result((log, usuario, prova))
    )
    item = await buscar_audit_log_por_id(fake_db, log.id)
    assert item is not None
    assert item.id == log.id
    assert item.tipo_evento == TipoEventoEnum.CRIACAO_PROVA
    assert item.usuario.is_admin is True
    assert item.prova is not None
    assert item.prova.nro_requerimento == "REQ-001"


async def test_buscar_por_id_nao_encontrado(fake_db):
    fake_db.execute = AsyncMock(return_value=_mock_first_result(None))
    item = await buscar_audit_log_por_id(fake_db, uuid.uuid4())
    assert item is None


async def test_buscar_por_id_usuario_orfao_levanta(fake_db):
    log = _make_audit_log()
    fake_db.execute = AsyncMock(
        return_value=_mock_first_result((log, None, None))
    )
    with pytest.raises(AuditLogSemUsuarioError):
        await buscar_audit_log_por_id(fake_db, log.id)


async def test_buscar_por_id_cancelamento_projecao(fake_db):
    """Busca pontual de 1 cancelamento projeta corretamente para
    `CANCELAMENTO`."""
    usuario = _make_usuario()
    prova = _make_prova()
    log = _make_audit_log(
        acao="transitar_status",
        detalhes={"para": "CANCELADA", "motivo_cancelamento": "teste"},
        prova_id=prova.id,
    )
    fake_db.execute = AsyncMock(
        return_value=_mock_first_result((log, usuario, prova))
    )
    item = await buscar_audit_log_por_id(fake_db, log.id)
    assert item is not None
    assert item.tipo_evento == TipoEventoEnum.CANCELAMENTO
    assert item.tipo_evento_label == "Cancelamento"
