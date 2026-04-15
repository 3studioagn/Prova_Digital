"""Testes unitarios dos schemas Pydantic de Auditoria (Wave 6, ADR-099).

Cobre o `AuditoriaFiltros` (query params do endpoint `GET /api/v1/auditoria/`)
com foco nos validators cruzados e de whitelist.

Objetivo: levar a cobertura de `app/domain/schemas/auditoria.py` a 100%
dentro do Bloco 6.1, antes dos testes de integracao do Bloco 6.2.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.domain.schemas.auditoria import (
    ACOES_VALIDAS,
    LIMIT_DEFAULT,
    LIMIT_MAX,
    TIPO_EVENTO_LABELS,
    TOTAL_ESTIMADO_CAP,
    AuditLogItem,
    AuditoriaFiltros,
    AuditoriaListResponse,
    FiltrosAplicados,
    ProvaAuditoria,
    TipoEventoEnum,
    UsuarioAuditoria,
)

# =============================================================================
# Constantes exportadas
# =============================================================================


def test_acoes_validas_contem_exatamente_5_valores():
    """Whitelist de `acao` deve ter exatamente os 5 valores produzidos pelas
    Waves 2-5. Qualquer adicao/remocao quebra este teste intencionalmente."""
    assert ACOES_VALIDAS == frozenset(
        {
            "criar_prova",
            "escanear_prova",
            "transitar_status",
            "reiniciar_ciclo",
            "atualizar_configuracao",
        }
    )


def test_limit_default_e_max_sao_coerentes():
    """`LIMIT_DEFAULT <= LIMIT_MAX` e ambos > 0."""
    assert 0 < LIMIT_DEFAULT <= LIMIT_MAX
    assert LIMIT_DEFAULT == 50
    assert LIMIT_MAX == 100


def test_total_estimado_cap_coerente():
    """Cap do total e 100_001 (1 acima de 100k) — sinaliza "100k+" pra UI."""
    assert TOTAL_ESTIMADO_CAP == 100_001


# =============================================================================
# AuditoriaFiltros — instanciacao default e com todos os campos
# =============================================================================


def test_filtros_default_tudo_none_com_limit_padrao():
    """Sem nenhum campo, instanciacao funciona e `limit=LIMIT_DEFAULT`."""
    f = AuditoriaFiltros()
    assert f.data_inicio is None
    assert f.data_fim is None
    assert f.usuario_id is None
    assert f.nro_requerimento is None
    assert f.acao is None
    assert f.tipo_evento is None
    assert f.cursor is None
    assert f.limit == LIMIT_DEFAULT


def test_filtros_com_todos_os_campos():
    """Preencher tudo (menos mutuamente exclusivos) retorna instancia valida."""
    uid = UUID("550e8400-e29b-41d4-a716-446655440000")
    f = AuditoriaFiltros(
        data_inicio=date(2026, 4, 1),
        data_fim=date(2026, 4, 14),
        usuario_id=uid,
        nro_requerimento="REQ-001",
        acao=["criar_prova", "escanear_prova"],
        tipo_evento=None,
        cursor="eyJjcmVhdGVkX2F0IjogIjIwMjYtMDQtMTQifQ==",
        limit=25,
    )
    assert f.data_inicio == date(2026, 4, 1)
    assert f.usuario_id == uid
    assert f.nro_requerimento == "REQ-001"
    assert f.acao == ["criar_prova", "escanear_prova"]
    assert f.limit == 25


def test_filtros_extra_forbid():
    """`extra='forbid'` rejeita campos desconhecidos — protege contra
    typos em query params."""
    with pytest.raises(ValidationError) as exc_info:
        AuditoriaFiltros(data_inicio=date(2026, 4, 1), campo_inexistente="xyz")
    assert "extra_forbidden" in str(exc_info.value)


def test_filtros_frozen_imutavel():
    """`frozen=True` impede mutacao apos instanciacao."""
    f = AuditoriaFiltros(limit=10)
    with pytest.raises(ValidationError):
        f.limit = 20  # type: ignore[misc]


# =============================================================================
# Validator: acao whitelist
# =============================================================================


def test_filtros_acao_invalida_levanta():
    """Valor fora da whitelist ACOES_VALIDAS e rejeitado no validator."""
    with pytest.raises(ValidationError) as exc_info:
        AuditoriaFiltros(acao=["criar_prova", "FOOBAR_INEXISTENTE"])
    assert "FOOBAR_INEXISTENTE" in str(exc_info.value)


def test_filtros_acao_dedupe_preservando_ordem():
    """Duplicados na lista sao removidos preservando a ordem de primeira
    aparicao — evita explodir a query com WHERE acao IN (...) redundante."""
    f = AuditoriaFiltros(
        acao=["escanear_prova", "criar_prova", "escanear_prova", "criar_prova"]
    )
    assert f.acao == ["escanear_prova", "criar_prova"]


def test_filtros_acao_todos_os_valores_validos():
    """Todos os 5 valores da whitelist sao aceitos juntos."""
    valores = sorted(ACOES_VALIDAS)
    f = AuditoriaFiltros(acao=valores)
    assert set(f.acao or []) == ACOES_VALIDAS


def test_filtros_acao_none_explicito_passa_pelo_validator():
    """Passando `acao=None` explicitamente exercita a branch `if v is None`
    do validator (Pydantic v2 pula validator para campos com default, entao
    precisa de valor explicito para cobrir esta linha)."""
    f = AuditoriaFiltros(acao=None)
    assert f.acao is None


# =============================================================================
# Validator: tipo_evento dedupe
# =============================================================================


def test_filtros_tipo_evento_dedupe():
    """Duplicados em tipo_evento sao removidos preservando ordem."""
    f = AuditoriaFiltros(
        tipo_evento=[
            TipoEventoEnum.CANCELAMENTO,
            TipoEventoEnum.REPROVACAO,
            TipoEventoEnum.CANCELAMENTO,  # duplicado
            TipoEventoEnum.TRANSICAO_STATUS,
        ]
    )
    assert f.tipo_evento == [
        TipoEventoEnum.CANCELAMENTO,
        TipoEventoEnum.REPROVACAO,
        TipoEventoEnum.TRANSICAO_STATUS,
    ]


def test_filtros_tipo_evento_invalido_levanta():
    """Valor string fora do enum vira ValidationError do Pydantic
    (cobertura do mecanismo Pydantic, nao do validator custom)."""
    with pytest.raises(ValidationError):
        AuditoriaFiltros(tipo_evento=["TIPO_INEXISTENTE"])  # type: ignore[list-item]


# =============================================================================
# Validator: mutuamente exclusivos (acao + tipo_evento)
# =============================================================================


def test_filtros_acao_e_tipo_evento_simultaneos_levanta():
    """Usar `acao` e `tipo_evento` ao mesmo tempo e 422 com mensagem clara."""
    with pytest.raises(ValidationError) as exc_info:
        AuditoriaFiltros(
            acao=["transitar_status"],
            tipo_evento=[TipoEventoEnum.CANCELAMENTO],
        )
    msg = str(exc_info.value)
    assert "mutuamente exclusivos" in msg


def test_filtros_apenas_acao_ok():
    """Apenas `acao` preenchido e valido."""
    f = AuditoriaFiltros(acao=["criar_prova"])
    assert f.acao == ["criar_prova"]
    assert f.tipo_evento is None


def test_filtros_apenas_tipo_evento_ok():
    """Apenas `tipo_evento` preenchido e valido."""
    f = AuditoriaFiltros(tipo_evento=[TipoEventoEnum.CANCELAMENTO])
    assert f.tipo_evento == [TipoEventoEnum.CANCELAMENTO]
    assert f.acao is None


# =============================================================================
# Validator: intervalo de datas
# =============================================================================


def test_filtros_data_inicio_maior_que_data_fim_levanta():
    """`data_inicio > data_fim` e 422 com mensagem clara."""
    with pytest.raises(ValidationError) as exc_info:
        AuditoriaFiltros(
            data_inicio=date(2026, 4, 15),
            data_fim=date(2026, 4, 10),
        )
    assert "data_inicio nao pode ser posterior a data_fim" in str(exc_info.value)


def test_filtros_data_inicio_igual_data_fim_ok():
    """`data_inicio == data_fim` e valido — filtro de 1 dia especifico."""
    f = AuditoriaFiltros(
        data_inicio=date(2026, 4, 14),
        data_fim=date(2026, 4, 14),
    )
    assert f.data_inicio == f.data_fim


def test_filtros_apenas_data_inicio_ok():
    """Apenas `data_inicio` (sem `data_fim`) e valido — abre-final."""
    f = AuditoriaFiltros(data_inicio=date(2026, 4, 1))
    assert f.data_inicio == date(2026, 4, 1)
    assert f.data_fim is None


def test_filtros_apenas_data_fim_ok():
    """Apenas `data_fim` (sem `data_inicio`) e valido — fechado-inicial."""
    f = AuditoriaFiltros(data_fim=date(2026, 4, 14))
    assert f.data_inicio is None
    assert f.data_fim == date(2026, 4, 14)


# =============================================================================
# Validator: limit
# =============================================================================


def test_filtros_limit_zero_levanta():
    """`limit=0` e rejeitado (ge=1)."""
    with pytest.raises(ValidationError):
        AuditoriaFiltros(limit=0)


def test_filtros_limit_acima_do_max_levanta():
    """`limit > LIMIT_MAX` e rejeitado."""
    with pytest.raises(ValidationError):
        AuditoriaFiltros(limit=LIMIT_MAX + 1)


def test_filtros_limit_nos_extremos_ok():
    """`limit=1` e `limit=LIMIT_MAX` sao aceitos."""
    assert AuditoriaFiltros(limit=1).limit == 1
    assert AuditoriaFiltros(limit=LIMIT_MAX).limit == LIMIT_MAX


def test_filtros_nro_requerimento_max_length():
    """`nro_requerimento` aceita ate 50 chars (constraint da tabela)."""
    f = AuditoriaFiltros(nro_requerimento="A" * 50)
    assert f.nro_requerimento is not None
    assert len(f.nro_requerimento) == 50

    with pytest.raises(ValidationError):
        AuditoriaFiltros(nro_requerimento="A" * 51)


# =============================================================================
# DTOs de response — smoke tests (instanciacao)
# =============================================================================


def test_usuario_auditoria_instanciavel():
    u = UsuarioAuditoria(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        nome="Mario Souza",
        setor="STUDIO",
        is_admin=True,
    )
    assert u.nome == "Mario Souza"
    assert u.is_admin is True


def test_prova_auditoria_instanciavel():
    p = ProvaAuditoria(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        nro_requerimento="REQ-001",
        nome="Rotulo Lata 350ml",
    )
    assert p.nro_requerimento == "REQ-001"


def test_audit_log_item_com_prova():
    from datetime import datetime, timezone

    item = AuditLogItem(
        id=UUID("33333333-3333-3333-3333-333333333333"),
        acao="transitar_status",
        tipo_evento=TipoEventoEnum.CANCELAMENTO,
        tipo_evento_label="Cancelamento",
        usuario=UsuarioAuditoria(
            id=UUID("11111111-1111-1111-1111-111111111111"),
            nome="Admin",
            setor="STUDIO",
            is_admin=True,
        ),
        prova=ProvaAuditoria(
            id=UUID("22222222-2222-2222-2222-222222222222"),
            nro_requerimento="REQ-001",
            nome="Rotulo",
        ),
        detalhes_json={"para": "CANCELADA", "motivo_cancelamento": "teste"},
        ip_address="203.0.113.42",
        user_agent="Mozilla/5.0",
        created_at=datetime(2026, 4, 14, 19, 55, 0, tzinfo=timezone.utc),
    )
    assert item.tipo_evento == TipoEventoEnum.CANCELAMENTO
    assert item.prova is not None
    assert item.detalhes_json is not None
    assert item.detalhes_json["para"] == "CANCELADA"


def test_audit_log_item_prova_none_para_alteracao_config():
    """Para `atualizar_configuracao`, `prova` e None."""
    from datetime import datetime, timezone

    item = AuditLogItem(
        id=UUID("33333333-3333-3333-3333-333333333333"),
        acao="atualizar_configuracao",
        tipo_evento=TipoEventoEnum.ALTERACAO_CONFIG,
        tipo_evento_label="Alteracao de configuracao",
        usuario=UsuarioAuditoria(
            id=UUID("11111111-1111-1111-1111-111111111111"),
            nome="Admin",
            setor="STUDIO",
            is_admin=True,
        ),
        prova=None,
        detalhes_json={"chave": "x", "valor_novo": 1, "valor_anterior": 0},
        ip_address=None,
        user_agent=None,
        created_at=datetime(2026, 4, 9, 14, 58, 49, tzinfo=timezone.utc),
    )
    assert item.prova is None
    assert item.ip_address is None


def test_auditoria_list_response_vazio():
    """Response com lista vazia e valida."""
    resp = AuditoriaListResponse(
        items=[],
        next_cursor=None,
        has_more=False,
        total_estimado=0,
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
    assert resp.items == []
    assert resp.has_more is False
    assert resp.total_estimado == 0


def test_tipo_evento_labels_export():
    """`TIPO_EVENTO_LABELS` e exportavel e tem entrada para cada enum."""
    assert len(TIPO_EVENTO_LABELS) == len(list(TipoEventoEnum))
    for tipo in TipoEventoEnum:
        assert tipo in TIPO_EVENTO_LABELS
