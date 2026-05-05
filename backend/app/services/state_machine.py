"""Maquina de estados da prova digital (ADR-040).

Single source of truth da Secao 5 dos Requisitos + RN-002 + RN-007.

Wave 2 usou apenas `determinar_rota` (derivacao projetada para exibicao na
UI do Componente 06) e as tabelas de transicao + atores. Wave 3 (Lote A —
Componente 11) implementa `executar_transicao`, que orquestra validacao +
persistencia + audit log de uma transicao completa (ADR-081).

Como ler a tabela TRANSICOES:
  TRANSICOES[status_atual] -> {status_destinos_validos}

Como ler ATORES_POR_TRANSICAO:
  ATORES_POR_TRANSICAO[(status_from, status_to)] -> {setores_autorizados}

Cancelamento: pode partir de qualquer estado ativo (RN-005), por isso e
tratado separadamente em `pode_cancelar(status)` em vez de listar todas as
combinacoes na tabela principal.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    LocalizacaoEnum,
    Movimentacao,
    ProvaDigital,
    RotaEnum,
    SetorEnum,
    StatusProvaEnum,
    Usuario,
)
from app.services.audit_service import log_audit


class TransicaoInvalidaError(ValueError):
    """Transicao rejeitada: o destino nao e alcancavel a partir do estado atual."""


class AtorNaoAutorizadoError(PermissionError):
    """Transicao valida, mas o ator nao tem setor autorizado para executa-la."""


class RotaIndeterminavelError(ValueError):
    """Nao e possivel determinar a rota — usuario nao e vendedor ou sem localizacao."""


# ─── Tabela de transicoes validas (Matriz Secao 5 dos Requisitos) ─────────

TRANSICOES: dict[StatusProvaEnum, set[StatusProvaEnum]] = {
    StatusProvaEnum.CRIADA: {
        StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        StatusProvaEnum.CANCELADA,
    },
    StatusProvaEnum.RETIRADA_PELO_VENDEDOR: {
        StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
        StatusProvaEnum.CANCELADA,
    },
    StatusProvaEnum.APROVADA_PELO_VENDEDOR: {
        # Matriz -> Padrao
        StatusProvaEnum.DE_VOLTA_3STUDIO,
        # Filial -> Direta
        StatusProvaEnum.ENCAMINHADA_A_CLICHERIA,
        StatusProvaEnum.CANCELADA,
    },
    StatusProvaEnum.DE_VOLTA_3STUDIO: {
        StatusProvaEnum.COM_MOTORISTA,
        StatusProvaEnum.CANCELADA,
    },
    StatusProvaEnum.COM_MOTORISTA: {
        StatusProvaEnum.ENVIADA_PARA_CLICHERIA,
        StatusProvaEnum.CANCELADA,
    },
    StatusProvaEnum.ENVIADA_PARA_CLICHERIA: {
        StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
        StatusProvaEnum.CANCELADA,
    },
    StatusProvaEnum.ENCAMINHADA_A_CLICHERIA: {
        StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
        StatusProvaEnum.CANCELADA,
    },
    StatusProvaEnum.REPROVADA_PELO_VENDEDOR: {
        # RN-006: reinicio de ciclo so pelo 3Studio. Volta a CRIADA e
        # incrementa ciclo_atual (tratado no handler da Wave 3).
        StatusProvaEnum.CRIADA,
        StatusProvaEnum.CANCELADA,
    },
    # Estados terminais — nenhuma transicao subsequente.
    StatusProvaEnum.RECEBIDA_PELA_CLICHERIA: set(),
    StatusProvaEnum.CANCELADA: set(),
}


# ─── Tabela de atores autorizados por transicao ──────────────────────────

ATORES_POR_TRANSICAO: dict[tuple[StatusProvaEnum, StatusProvaEnum], set[SetorEnum]] = {
    (StatusProvaEnum.CRIADA, StatusProvaEnum.RETIRADA_PELO_VENDEDOR): {SetorEnum.VENDEDOR},
    (StatusProvaEnum.RETIRADA_PELO_VENDEDOR, StatusProvaEnum.APROVADA_PELO_VENDEDOR): {
        SetorEnum.VENDEDOR
    },
    (StatusProvaEnum.RETIRADA_PELO_VENDEDOR, StatusProvaEnum.REPROVADA_PELO_VENDEDOR): {
        SetorEnum.VENDEDOR
    },
    (StatusProvaEnum.APROVADA_PELO_VENDEDOR, StatusProvaEnum.DE_VOLTA_3STUDIO): {
        SetorEnum.VENDEDOR
    },
    (StatusProvaEnum.APROVADA_PELO_VENDEDOR, StatusProvaEnum.ENCAMINHADA_A_CLICHERIA): {
        SetorEnum.VENDEDOR
    },
    (StatusProvaEnum.DE_VOLTA_3STUDIO, StatusProvaEnum.COM_MOTORISTA): {SetorEnum.STUDIO},
    (StatusProvaEnum.COM_MOTORISTA, StatusProvaEnum.ENVIADA_PARA_CLICHERIA): {
        SetorEnum.MOTORISTA
    },
    (StatusProvaEnum.ENVIADA_PARA_CLICHERIA, StatusProvaEnum.RECEBIDA_PELA_CLICHERIA): {
        SetorEnum.CLICHERIA
    },
    (StatusProvaEnum.ENCAMINHADA_A_CLICHERIA, StatusProvaEnum.RECEBIDA_PELA_CLICHERIA): {
        SetorEnum.CLICHERIA
    },
    (StatusProvaEnum.REPROVADA_PELO_VENDEDOR, StatusProvaEnum.CRIADA): {SetorEnum.STUDIO},
    # Cancelamentos (de todos os estados ativos) — apenas STUDIO (RN-005).
    # Nao listados exaustivamente aqui: usar pode_cancelar() + setor=STUDIO.
}


# ─── API publica ─────────────────────────────────────────────────────────


def determinar_rota(vendedor: Usuario) -> RotaEnum:
    """Calcula a rota que uma prova vai seguir dado o vendedor responsavel (RN-007).

    MATRIZ -> PADRAO (via motorista para clicheria).
    FILIAL -> DIRETA (do vendedor direto para clicheria).

    Wave 2 usa este valor apenas para EXIBICAO no Componente 06 (campo
    `rota_projetada` no response). A rota so e PERSISTIDA em
    `provas_digitais.rota` quando a prova e aprovada (Wave 3).
    """
    if vendedor.setor != SetorEnum.VENDEDOR:
        raise RotaIndeterminavelError(
            f"Rota so se aplica a vendedores (setor atual: {vendedor.setor.value})"
        )
    if vendedor.localizacao is None:
        raise RotaIndeterminavelError(
            f"Vendedor {vendedor.id} nao tem localizacao cadastrada"
        )
    if vendedor.localizacao == LocalizacaoEnum.MATRIZ:
        return RotaEnum.PADRAO
    if vendedor.localizacao == LocalizacaoEnum.FILIAL:
        return RotaEnum.DIRETA
    raise RotaIndeterminavelError(
        f"Localizacao desconhecida: {vendedor.localizacao}"
    )


def transicao_e_valida(
    status_atual: StatusProvaEnum, status_novo: StatusProvaEnum
) -> bool:
    """True se a transicao `status_atual -> status_novo` consta na tabela."""
    return status_novo in TRANSICOES.get(status_atual, set())


def pode_cancelar(status_atual: StatusProvaEnum) -> bool:
    """RN-005: cancelamento permitido em qualquer estado ativo.

    Estados ativos = todos exceto `CANCELADA` e `RECEBIDA_PELA_CLICHERIA`
    (este ultimo e terminal de sucesso).
    """
    return status_atual not in {
        StatusProvaEnum.CANCELADA,
        StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
    }


def atores_permitidos(
    status_atual: StatusProvaEnum, status_novo: StatusProvaEnum
) -> set[SetorEnum]:
    """Conjunto de setores autorizados para executar uma transicao especifica.

    Para transicoes de cancelamento (qualquer status -> CANCELADA) retorna
    `{STUDIO}` universalmente.
    """
    if status_novo == StatusProvaEnum.CANCELADA:
        return {SetorEnum.STUDIO}
    return ATORES_POR_TRANSICAO.get((status_atual, status_novo), set())


def validar_transicao(
    status_atual: StatusProvaEnum,
    status_novo: StatusProvaEnum,
    usuario: Usuario,
) -> None:
    """Valida que a transicao e legal E que o usuario pode executa-la.

    Raises:
        TransicaoInvalidaError: destino nao alcancavel a partir da origem.
        AtorNaoAutorizadoError: transicao valida mas o setor nao permite.
    """
    # Cancelamento tem regra propria (RN-005).
    if status_novo == StatusProvaEnum.CANCELADA:
        if not pode_cancelar(status_atual):
            raise TransicaoInvalidaError(
                f"Nao e possivel cancelar prova em estado {status_atual.value}"
            )
        if usuario.setor != SetorEnum.STUDIO and not usuario.is_admin:
            raise AtorNaoAutorizadoError(
                f"Cancelamento restrito ao perfil 3Studio (RN-005). "
                f"Setor atual: {usuario.setor.value}"
            )
        return

    if not transicao_e_valida(status_atual, status_novo):
        raise TransicaoInvalidaError(
            f"Transicao invalida: {status_atual.value} -> {status_novo.value} "
            f"nao consta na Matriz Secao 5 (RN-002)"
        )

    permitidos = atores_permitidos(status_atual, status_novo)
    if usuario.setor not in permitidos and not usuario.is_admin:
        raise AtorNaoAutorizadoError(
            f"Setor {usuario.setor.value} nao autorizado para "
            f"{status_atual.value} -> {status_novo.value}. "
            f"Permitidos: {sorted(s.value for s in permitidos)} (RN-004)"
        )


async def executar_transicao(
    db: AsyncSession,
    *,
    prova: ProvaDigital,
    status_novo: StatusProvaEnum,
    usuario: Usuario,
    assinatura_digital: bytes,
    motivo_reprovacao: str | None = None,
    motivo_cancelamento: str | None = None,
    request: Request | None = None,
) -> Movimentacao:
    """Executa uma transicao de status end-to-end (Componente 11, Wave 3).

    Orquestra:
      1. Valida assinatura nao-vazia (RN-003).
      2. Delega validacao de transicao + ator a `validar_transicao`.
      3. Valida motivo obrigatorio conforme destino:
         - `REPROVADA_PELO_VENDEDOR` exige `motivo_reprovacao` (RF-007).
         - `CANCELADA` exige `motivo_cancelamento` (RN-005, reservado C13).
      4. Aplica regra extra de rota em `APROVADA_PELO_VENDEDOR -> *` (RF-009):
         - `DE_VOLTA_3STUDIO` so para vendedor MATRIZ (rota padrao).
         - `ENCAMINHADA_A_CLICHERIA` so para vendedor FILIAL (rota direta).
         Admin (`is_admin=true`) bypassa essa checagem — mesmo padrao de
         `validar_transicao`.
      5. Aprovacao (`RETIRADA_PELO_VENDEDOR -> APROVADA_PELO_VENDEDOR`):
         grava `prova.rota = determinar_rota(usuario)` (RN-007).
      6. Reinicio de ciclo (`REPROVADA_PELO_VENDEDOR -> CRIADA`): incrementa
         `prova.ciclo_atual`, zera `prova.rota`, usa `acao="reiniciar_ciclo"`
         no audit log. Gancho para o Componente 14 (Lote C) — o endpoint
         `POST /transicoes` do Lote A rejeita `CRIADA` como destino, mas a
         state_machine suporta para que C14 possa chamar via endpoint
         administrativo dedicado sem refactor.
      7. Cancelamento (`* -> CANCELADA`): grava `prova.motivo_cancelamento`.
         Gancho para o Componente 13 (Lote C) — o endpoint `POST /transicoes`
         do Lote A tambem rejeita `CANCELADA`.
      8. INSERT em `movimentacoes` (via `db.add` + `db.flush`).
      9. UPDATE implicito em `provas_digitais` (mutacao do objeto ORM).
     10. `log_audit` com `detalhes_json` estruturado.
     11. Retorna a `Movimentacao` criada — SEM commit, o caller orquestra
         a transacao.

    O caller (endpoint `POST /provas/{id}/transicoes` — sub-bloco A.4) e
    responsavel por:
      - Carregar `prova` com FOR UPDATE (evita race entre transicoes).
      - Chamar `db.commit()` apos este retorno bem-sucedido.
      - Capturar as excecoes de dominio abaixo e traduzi-las para HTTP
        (ver sub-bloco A.4 para o mapeamento HTTP).

    Raises:
        TransicaoInvalidaError: destino ilegal na Matriz Secao 5.
        AtorNaoAutorizadoError: setor nao autorizado OU localizacao errada
            em `APROVADA_PELO_VENDEDOR -> *`.
        ValueError: `assinatura_digital` vazia, `motivo_reprovacao` ausente
            na reprovacao, `motivo_cancelamento` ausente no cancelamento.
        RotaIndeterminavelError: aprovacao executada por usuario sem
            localizacao valida (ex: admin STUDIO aprovando direto sem
            vendedor).
    """
    # 1. Assinatura obrigatoria (RN-003).
    if not assinatura_digital:
        raise ValueError("Assinatura digital e obrigatoria (RN-003)")

    status_atual = prova.status

    # 2. Validacao de transicao + ator — reutiliza a funcao existente.
    validar_transicao(status_atual, status_novo, usuario)

    # 3. Motivo obrigatorio conforme destino.
    motivo_reprovacao_norm: str | None = None
    motivo_cancelamento_norm: str | None = None

    if status_novo == StatusProvaEnum.REPROVADA_PELO_VENDEDOR:
        if motivo_reprovacao is None or not motivo_reprovacao.strip():
            raise ValueError(
                "Motivo da reprovacao e obrigatorio (RF-007)"
            )
        motivo_reprovacao_norm = motivo_reprovacao.strip()

    if status_novo == StatusProvaEnum.CANCELADA:
        if motivo_cancelamento is None or not motivo_cancelamento.strip():
            raise ValueError(
                "Motivo do cancelamento e obrigatorio (RN-005)"
            )
        motivo_cancelamento_norm = motivo_cancelamento.strip()

    # 4. Regra extra de rota para APROVADA_PELO_VENDEDOR -> *.
    #
    # A state_machine `TRANSICOES` + `ATORES_POR_TRANSICAO` ja autoriza
    # qualquer VENDEDOR a transitar APROVADA para DE_VOLTA_3STUDIO ou
    # ENCAMINHADA_A_CLICHERIA (porque a tabela nao distingue localizacao).
    # O RF-009 (e RN-007 "rota determinada pela localizacao") exige que o
    # destino bata com a localizacao do vendedor:
    #   - MATRIZ usa rota padrao: DE_VOLTA_3STUDIO -> ... -> RECEBIDA
    #   - FILIAL usa rota direta: ENCAMINHADA_A_CLICHERIA -> RECEBIDA
    # Admin bypassa essa validacao (consistente com `validar_transicao`).
    if (
        status_atual == StatusProvaEnum.APROVADA_PELO_VENDEDOR
        and not usuario.is_admin
    ):
        if status_novo == StatusProvaEnum.DE_VOLTA_3STUDIO:
            if usuario.localizacao != LocalizacaoEnum.MATRIZ:
                raise AtorNaoAutorizadoError(
                    "Devolucao a 3Studio so permitida para vendedor MATRIZ "
                    "(rota padrao — RF-009)"
                )
        elif status_novo == StatusProvaEnum.ENCAMINHADA_A_CLICHERIA:
            if usuario.localizacao != LocalizacaoEnum.FILIAL:
                raise AtorNaoAutorizadoError(
                    "Encaminhamento direto a clicheria so permitido para "
                    "vendedor FILIAL (rota direta — RF-009)"
                )

    # 5, 6, 7. Calcula efeitos no modelo `provas_digitais`.
    rota_antes = prova.rota
    ciclo_antes = prova.ciclo_atual
    rota_depois: RotaEnum | None = rota_antes
    ciclo_depois: int = ciclo_antes
    acao_audit = "transitar_status"

    aprovando = (
        status_atual == StatusProvaEnum.RETIRADA_PELO_VENDEDOR
        and status_novo == StatusProvaEnum.APROVADA_PELO_VENDEDOR
    )
    reiniciando_ciclo = (
        status_atual == StatusProvaEnum.REPROVADA_PELO_VENDEDOR
        and status_novo == StatusProvaEnum.CRIADA
    )

    if aprovando:
        # Wave 2 v4.0 (Componente 06): a rota e IMUTAVEL apos a criacao
        # (RN-002 v4.0). Provas v4.0 tem `rota` ja persistida desde o
        # POST /api/v1/provas/ — preservamos. Apenas provas legadas v3.0
        # com `rota = NULL` (criadas antes da Wave 2 v4.0) recebem rota
        # derivada da localizacao do vendedor neste ponto, mantendo o
        # comportamento v3.0 ate a Wave 7 (Componente 21) fazer o backfill.
        #
        # SEM esta condicional, o trigger `trg_provas_rota_imutavel`
        # rejeitaria UPDATE da rota com SQLSTATE 22023 e a aprovacao
        # falharia para toda prova v4.0.
        if prova.rota is None:
            # Prova legada v3.0 — derivar via localizacao (compat).
            rota_depois = determinar_rota(usuario)
        else:
            # Prova v4.0 — preservar rota imutavel (RN-002 v4.0).
            rota_depois = prova.rota

    if reiniciando_ciclo:
        # Gancho para C14 (Lote C). O Lote A implementa mecanicamente
        # porque deixar o incremento de ciclo para depois seria uma
        # ramificacao de logica que complicaria o handler de transicao
        # agora. Ver §3.3 do WAVE3_LOTE_A_ANALYSIS.md.
        #
        # Wave 2 v4.0 (Audit Fix AUD-W2V4-001 — ADR-123): a rota e
        # IMUTAVEL apos a criacao (RN-002 v4.0) — preservamos `rota_antes`
        # em vez de zerar. Isso vale para os 3 cenarios:
        #   - Prova v4.0 (rota=MATRIZ/LAM_MATRIZ/FILIAL/LAM_FILIAL):
        #     rota_depois = rota_antes; trigger nao dispara
        #     (`OLD.rota IS NOT DISTINCT FROM NEW.rota` -> WHEN false).
        #   - Prova legada v3.0 (rota=PADRAO/DIRETA): rota_depois =
        #     rota_antes; mantem coerencia historica ate Wave 7.
        #   - Prova legada v3.0 (rota=NULL): rota_depois = None
        #     (rota_antes ja era None); trigger ainda nao se aplica.
        # RF-009 v4.0, RN-006 v4.0, US-010 explicitamente exigem
        # preservacao no reinicio.
        ciclo_depois = ciclo_antes + 1
        rota_depois = rota_antes
        acao_audit = "reiniciar_ciclo"

    # 8. Cria a movimentacao. `rota_no_momento` e `ciclo` carregam os
    # valores "depois da transicao", refletindo o estado da prova no
    # instante do registro (inclusive para reinicio de ciclo onde a
    # rota foi zerada).
    #
    # Geramos `id` e `created_at` no Python (nao contamos com o
    # server_default do banco). Mesmo padrao do `create_prova` da Wave 2
    # que gera `prova_id = uuid.uuid4()` antes do INSERT. Beneficios:
    #   1. O caller recebe uma Movimentacao totalmente populada para
    #      serializar no response (sem precisar de `db.refresh`).
    #   2. Testes com `mock_db` nao precisam simular o server_default.
    #   3. Determinismo em logs: o ID e conhecido antes do commit.
    nova_movimentacao = Movimentacao(
        id=uuid.uuid4(),
        prova_id=prova.id,
        usuario_id=usuario.id,
        status_anterior=status_atual,
        status_novo=status_novo,
        assinatura_digital=assinatura_digital,
        motivo_reprovacao=motivo_reprovacao_norm,
        ciclo=ciclo_depois,
        rota_no_momento=rota_depois,
        created_at=datetime.now(tz=timezone.utc),
    )

    # 9. Aplica mudancas no objeto ORM da prova. SQLAlchemy detecta o
    # dirty state e persiste no UPDATE implicito durante o flush.
    prova.status = status_novo
    prova.rota = rota_depois
    prova.ciclo_atual = ciclo_depois
    if status_novo == StatusProvaEnum.CANCELADA:
        prova.motivo_cancelamento = motivo_cancelamento_norm

    # Flush garante INSERT de movimentacoes antes do audit_log — mesmo
    # padrao do `create_prova` da Wave 2 (evita race de ordem de flush
    # sem relationships declaradas).
    db.add(nova_movimentacao)
    await db.flush()

    # 10. Audit log com `detalhes_json` estruturado. `de` e `para` sao
    # sempre strings do enum para facilitar query SQL posterior via
    # `detalhes_json->>'para' = 'APROVADA_PELO_VENDEDOR'`.
    detalhes: dict[str, Any] = {
        "de": status_atual.value,
        "para": status_novo.value,
        "ciclo": ciclo_depois,
        "rota_antes": rota_antes.value if rota_antes is not None else None,
        "rota_depois": rota_depois.value if rota_depois is not None else None,
    }
    if motivo_reprovacao_norm:
        detalhes["motivo_reprovacao"] = motivo_reprovacao_norm
    if motivo_cancelamento_norm:
        detalhes["motivo_cancelamento"] = motivo_cancelamento_norm

    await log_audit(
        db,
        acao=acao_audit,
        usuario_id=usuario.id,
        prova_id=prova.id,
        detalhes=detalhes,
        request=request,
    )

    # 11. Retorna sem commit — o caller (endpoint) orquestra a transacao.
    return nova_movimentacao
