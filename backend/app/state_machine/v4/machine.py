"""Maquina de Estados v4.0 — funcoes puras de validacao + executar_transicao.

Wave 3 v4.0 / Componente 11.

Esta eh a camada de DOMINIO. As funcoes nao sabem de HTTP. O caller
(`provas.py`) traduz excecoes de dominio para codigos HTTP (mapeamento
herdado do ADR-084: TransicaoInvalidaError -> 409, AtorNaoAutorizadoError
-> 422, ValueError -> 422, RotaIndeterminavelError -> 422).

Diferencas chave vs v3.0 (`app.services.state_machine`):
  - RF-010 v4.0: rota eh imutavel e ja persistida desde a criacao. NAO
    bifurca por localizacao do vendedor em APROVADA -> * (RF-009 v3.0
    obsoleto). A tabela TRANSITION_RULES por rota ja determina o
    destino correto.
  - RN-002 v4.0: rota nao muda nunca apos definicao. `rota_depois` no
    `executar_transicao_v4` sempre eh `rota_antes` (mesmo em reinicio
    de ciclo — RF-009 v4.0 e ADR-123 mantidos).
  - Decisao M-5 do Gate 1: audit_log.detalhes_json["contexto_motorista"]
    eh populado quando `status_novo` eh um dos 3 estados de motorista.

Excecoes reusadas do v3.0 (mesmas semanticas):
  - TransicaoInvalidaError: destino nao consta na Matriz §5 para a rota.
  - AtorNaoAutorizadoError: setor nao autorizado para a transicao.
  - ValueError: motivo ausente quando obrigatorio, assinatura vazia.

NAO levanta `RotaIndeterminavelError` (era usado pelo v3.0 quando admin
tentava aprovar sem localizacao — irrelevante na v4.0 ja que rota nao
eh derivada).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Movimentacao,
    ProvaDigital,
    RotaEnum,
    SetorEnum,
    StatusProvaEnum,
    Usuario,
)
from app.services.audit_service import log_audit
from app.services.state_machine import (
    AtorNaoAutorizadoError,
    TransicaoInvalidaError,
)
from app.state_machine.v4.contextos import contexto_motorista
from app.state_machine.v4.rules import (
    ROTAS_V4,
    TERMINAIS_V4,
    TRANSITION_RULES,
    Transition,
)


# ─── pode_cancelar (compat v3.0 + v4.0) ────────────────────────────────────


def pode_cancelar(status_atual: StatusProvaEnum) -> bool:
    """RN-005: cancelamento permitido em qualquer estado ativo.

    Estado ativo = qualquer status que NAO seja:
      - RECEBIDA_PELA_CLICHERIA (terminal sucesso)
      - CANCELADA (terminal cancelamento)

    Os outros 15 valores do enum (10 v3.0 + 5 v4.0 ativos) sao todos
    cancelaveis. Funciona identicamente para provas v3.0 e v4.0 — o
    cancelamento eh transversal (ver §5.6 do Requisitos).
    """
    return status_atual not in TERMINAIS_V4


# ─── transicoes_validas_v4 ────────────────────────────────────────────────


def transicoes_validas_v4(
    rota: RotaEnum, status_atual: StatusProvaEnum, usuario: Usuario
) -> frozenset[StatusProvaEnum]:
    """Conjunto de destinos validos para o usuario na rota+estado atual.

    Consulta `TRANSITION_RULES[(rota, status_atual)]` e filtra por:
      1. Estados terminais (sem transicoes — retorna conjunto vazio).
      2. Setor do usuario casa o ator da Transition. Admin (is_admin=True)
         bypassa o filtro de setor (consistencia com Wave 1 / ADR-018).

    NAO inclui CANCELADA (transversal, endpoint dedicado) nem CRIADA
    (reinicio de ciclo, transversal admin-only).

    Para rotas legacy (PADRAO, DIRETA, NULL) retorna frozenset vazio —
    o caller (scan endpoint) usa logica v3.0.
    """
    if rota not in ROTAS_V4:
        return frozenset()
    if status_atual in TERMINAIS_V4:
        return frozenset()

    candidatos: frozenset[Transition] = TRANSITION_RULES.get(
        (rota, status_atual), frozenset()
    )
    permitidas: set[StatusProvaEnum] = set()
    for t in candidatos:
        if usuario.is_admin or usuario.setor == t.ator:
            permitidas.add(t.destino)
    return frozenset(permitidas)


# ─── motivo_obrigatorio_em_v4 ─────────────────────────────────────────────


def motivo_obrigatorio_em_v4(
    rota: RotaEnum, status_atual: StatusProvaEnum, usuario: Usuario
) -> frozenset[StatusProvaEnum]:
    """Subset de `transicoes_validas_v4` onde motivo eh obrigatorio.

    Wave 3 v4.0: apenas REPROVADA_PELO_VENDEDOR exige motivo no submit
    (RF-007). Cancelamento tambem exige, mas eh transversal — endpoint
    dedicado.
    """
    if rota not in ROTAS_V4 or status_atual in TERMINAIS_V4:
        return frozenset()
    candidatos: frozenset[Transition] = TRANSITION_RULES.get(
        (rota, status_atual), frozenset()
    )
    return frozenset(
        t.destino
        for t in candidatos
        if t.motivo_obrigatorio
        and (usuario.is_admin or usuario.setor == t.ator)
    )


# ─── validar_transicao_v4 ─────────────────────────────────────────────────


def validar_transicao_v4(
    rota: RotaEnum,
    status_atual: StatusProvaEnum,
    status_destino: StatusProvaEnum,
    usuario: Usuario,
) -> None:
    """Valida que a transicao eh legal E que o usuario pode executa-la.

    Cancelamento e reinicio de ciclo sao transversais e tratados
    SEPARADAMENTE (ver `executar_transicao_v4`). Esta funcao foca em
    transicoes da Matriz §5.

    Raises:
        TransicaoInvalidaError: destino nao consta na Matriz para
            (rota, status_atual). Caller (handler HTTP) traduz para 409
            apos FOR UPDATE (ADR-084).
        AtorNaoAutorizadoError: transicao consta na Matriz mas o setor
            do usuario nao eh autorizado. Caller traduz para 422.
    """
    # Cancelamento: nao chega aqui (caller usa endpoint dedicado).
    # Reinicio: idem.
    if status_destino == StatusProvaEnum.CANCELADA:
        raise TransicaoInvalidaError(
            "Cancelamento NAO deve passar por validar_transicao_v4. "
            "Use o endpoint POST /{id}/cancelar (admin-only)."
        )
    if (
        status_atual == StatusProvaEnum.REPROVADA_PELO_VENDEDOR
        and status_destino == StatusProvaEnum.CRIADA
    ):
        raise TransicaoInvalidaError(
            "Reinicio de ciclo NAO deve passar por validar_transicao_v4. "
            "Use o endpoint POST /{id}/reiniciar-ciclo (admin-only)."
        )

    if rota not in ROTAS_V4:
        raise TransicaoInvalidaError(
            f"Rota {rota.value} nao eh v4.0. Use a maquina v3.0 para "
            f"provas legacy (rota IS NULL ou PADRAO/DIRETA)."
        )

    candidatos: frozenset[Transition] = TRANSITION_RULES.get(
        (rota, status_atual), frozenset()
    )
    if not candidatos:
        raise TransicaoInvalidaError(
            f"Esta prova segue a rota {rota.value}, que nao permite "
            f"a transicao {status_atual.value} -> {status_destino.value}."
        )

    match: Transition | None = None
    for t in candidatos:
        if t.destino == status_destino:
            match = t
            break

    if match is None:
        raise TransicaoInvalidaError(
            f"Esta prova segue a rota {rota.value}, que nao permite "
            f"a transicao {status_atual.value} -> {status_destino.value}."
        )

    # Admin bypassa setor (ADR-018, consistencia com v3.0).
    if not usuario.is_admin and usuario.setor != match.ator:
        raise AtorNaoAutorizadoError(
            f"Voce nao tem permissao para esta transicao "
            f"(setor {usuario.setor.value})."
        )


# ─── executar_transicao_v4 ────────────────────────────────────────────────


async def executar_transicao_v4(
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
    """Executa uma transicao v4.0 end-to-end.

    Caller (handler em provas.py) eh responsavel por:
      - Carregar `prova` com FOR UPDATE (ADR-084).
      - Commit() apos retorno bem-sucedido.
      - Traduzir excecoes de dominio para HTTP.

    Esta funcao orquestra:
      1. Valida assinatura nao-vazia (RN-003).
      2. Trata 3 casos especiais transversais:
         - Cancelamento (status_novo=CANCELADA) — admin-only, motivo
           obrigatorio.
         - Reinicio de ciclo (status_atual=REPROVADA AND
           status_novo=CRIADA) — admin-only, ciclo+1, rota preservada.
         - Reprovacao (status_novo=REPROVADA_PELO_VENDEDOR) —
           motivo obrigatorio (Matriz §5.6).
      3. Para transicao normal: delega validacao a `validar_transicao_v4`.
      4. Atualiza prova.status (e ciclo_atual se reinicio).
      5. Rota NUNCA muda (RN-002 v4.0). Mesmo em reinicio de ciclo,
         `rota_depois = rota_antes` (preservado por ADR-123).
      6. INSERT em movimentacoes (rota_no_momento = prova.rota POS-update,
         que eh sempre identico a rota_antes — RN-002 v4.0).
      7. Audit log com `de`/`para`/`ciclo`/`rota_antes`/`rota_depois` +
         `contexto_motorista` opcional (Decisao M-5 do Gate 1).
      8. Retorna Movimentacao SEM commit.

    Raises:
        TransicaoInvalidaError: destino ilegal na Matriz.
        AtorNaoAutorizadoError: setor nao autorizado.
        ValueError: assinatura vazia, motivo ausente em reprovacao/
            cancelamento.
    """
    # 1. Assinatura obrigatoria (RN-003).
    if not assinatura_digital:
        raise ValueError("Assinatura digital eh obrigatoria (RN-003)")

    status_atual = prova.status
    rota = prova.rota

    if rota is None or rota not in ROTAS_V4:
        # Defesa em profundidade: o roteador no facade ja deveria ter
        # despachado para v3.0. Se chegou aqui, eh bug.
        raise TransicaoInvalidaError(
            f"Prova com rota={rota.value if rota else 'NULL'} nao deve "
            f"ser processada pela maquina v4.0. Provavel bug no roteador."
        )

    motivo_reprovacao_norm: str | None = None
    motivo_cancelamento_norm: str | None = None

    # ── Caso 1: Cancelamento (transversal §5.6) ──────────────────────────
    is_cancelamento = status_novo == StatusProvaEnum.CANCELADA
    if is_cancelamento:
        if not pode_cancelar(status_atual):
            raise TransicaoInvalidaError(
                f"Prova em {status_atual.value} eh estado final."
            )
        if usuario.setor != SetorEnum.STUDIO and not usuario.is_admin:
            raise AtorNaoAutorizadoError(
                f"Voce nao tem permissao para esta transicao "
                f"(setor {usuario.setor.value})."
            )
        if motivo_cancelamento is None or not motivo_cancelamento.strip():
            raise ValueError(
                "Motivo do cancelamento eh obrigatorio (RN-005)"
            )
        motivo_cancelamento_norm = motivo_cancelamento.strip()

    # ── Caso 2: Reinicio de ciclo (transversal §5.6) ─────────────────────
    is_reinicio = (
        status_atual == StatusProvaEnum.REPROVADA_PELO_VENDEDOR
        and status_novo == StatusProvaEnum.CRIADA
    )
    if is_reinicio:
        if usuario.setor != SetorEnum.STUDIO and not usuario.is_admin:
            raise AtorNaoAutorizadoError(
                f"Voce nao tem permissao para esta transicao "
                f"(setor {usuario.setor.value})."
            )

    # ── Caso 3: Reprovacao (transversal — disponivel em todas as rotas) ──
    is_reprovacao = status_novo == StatusProvaEnum.REPROVADA_PELO_VENDEDOR

    # ── Caso 4: Transicao normal (Matriz §5.2-5.5) ───────────────────────
    if not is_cancelamento and not is_reinicio:
        validar_transicao_v4(rota, status_atual, status_novo, usuario)
        if is_reprovacao:
            if motivo_reprovacao is None or not motivo_reprovacao.strip():
                raise ValueError(
                    "Motivo da reprovacao eh obrigatorio (RF-007)"
                )
            motivo_reprovacao_norm = motivo_reprovacao.strip()

    # ── Calcula efeitos no modelo ────────────────────────────────────────
    rota_antes = prova.rota
    ciclo_antes = prova.ciclo_atual

    # RN-002 v4.0: rota eh IMUTAVEL apos definicao. Mesmo em reinicio,
    # rota_depois = rota_antes (ADR-123).
    rota_depois: RotaEnum | None = rota_antes
    ciclo_depois = ciclo_antes
    acao_audit = "transitar_status"

    if is_reinicio:
        ciclo_depois = ciclo_antes + 1
        acao_audit = "reiniciar_ciclo"

    # ── Cria a movimentacao ──────────────────────────────────────────────
    # `rota_no_momento` reflete a rota POS-transicao (sempre = rota_antes
    # na v4.0 por causa da imutabilidade). `id` e `created_at` gerados no
    # Python (mesmo padrao do v3.0 / ADR-084 Decisao 6) para evitar None
    # apos flush em mock_db.
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

    # ── Aplica mudancas no objeto ORM ────────────────────────────────────
    prova.status = status_novo
    prova.ciclo_atual = ciclo_depois
    # prova.rota NAO eh mutada (RN-002 v4.0 + trigger trg_provas_rota_imutavel)
    if is_cancelamento:
        prova.motivo_cancelamento = motivo_cancelamento_norm

    db.add(nova_movimentacao)
    await db.flush()

    # ── Audit log estruturado ────────────────────────────────────────────
    # Decisao M-5 do Gate 1: contexto_motorista derivado de status_novo,
    # registrado em audit_log.detalhes_json para investigacao futura
    # (NAO em coluna separada de movimentacoes).
    detalhes: dict[str, Any] = {
        "de": status_atual.value,
        "para": status_novo.value,
        "ciclo": ciclo_depois,
        "rota_antes": rota_antes.value if rota_antes is not None else None,
        "rota_depois": rota_depois.value if rota_depois is not None else None,
        "maquina": "v4",
    }
    contexto = contexto_motorista(status_novo)
    if contexto is not None:
        detalhes["contexto_motorista"] = contexto
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

    # Retorna SEM commit — caller orquestra a transacao.
    return nova_movimentacao
