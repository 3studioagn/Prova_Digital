"""Maquina de estados da prova digital (ADR-040).

Single source of truth da Secao 5 dos Requisitos + RN-002 + RN-007.

Wave 2 usa apenas `determinar_rota` (derivacao projetada para exibicao na UI
do Componente 06) e as tabelas de transicao + atores (usadas pelos testes
de validacao da estrutura). `executar_transicao` e um stub que Wave 3 vai
implementar quando o fluxo de escanear QR + assinar + confirmar existir.

Como ler a tabela TRANSICOES:
  TRANSICOES[status_atual] -> {status_destinos_validos}

Como ler ATORES_POR_TRANSICAO:
  ATORES_POR_TRANSICAO[(status_from, status_to)] -> {setores_autorizados}

Cancelamento: pode partir de qualquer estado ativo (RN-005), por isso e
tratado separadamente em `pode_cancelar(status)` em vez de listar todas as
combinacoes na tabela principal.
"""
from app.db.models import LocalizacaoEnum, RotaEnum, SetorEnum, StatusProvaEnum, Usuario


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


def executar_transicao(*args, **kwargs):
    """Stub reservado para Wave 3.

    Vai orquestrar: validar_transicao + insert em movimentacoes +
    update em provas_digitais.status/rota + audit log. A assinatura
    final sera definida quando o contrato do endpoint de transicao
    for desenhado no Componente 11.
    """
    raise NotImplementedError(
        "executar_transicao sera implementada no Componente 11 (Wave 3)"
    )
