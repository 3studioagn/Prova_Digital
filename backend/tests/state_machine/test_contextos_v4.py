"""Testes de contextos.py - deteccao dos 3 contextos do Motorista.

Wave 3 v4.0 / Componente 11. Decisao M-5 do Gate 1.

Cobertura: 4 mappings que produzem contexto + todos os outros estados
que produzem None.
"""
from __future__ import annotations

import pytest

from app.db.models import StatusProvaEnum
from app.state_machine.v4.contextos import contexto_motorista


def test_ida_laminacao():
    assert contexto_motorista(StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO) == "ida_laminacao"


def test_volta_laminacao():
    assert contexto_motorista(StatusProvaEnum.COM_MOTORISTA_VOLTA_LAMINACAO) == "volta_laminacao"


def test_entrega_final_v4():
    assert contexto_motorista(StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL) == "entrega_final"


def test_entrega_final_legacy_v3():
    """Decisao M-2b(a): COM_MOTORISTA legacy v3.0 mapeia para 'entrega_final'."""
    assert contexto_motorista(StatusProvaEnum.COM_MOTORISTA) == "entrega_final"


@pytest.mark.parametrize(
    "status",
    [
        StatusProvaEnum.CRIADA,
        StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        StatusProvaEnum.DE_VOLTA_3STUDIO,
        StatusProvaEnum.ENVIADA_PARA_CLICHERIA,
        StatusProvaEnum.ENCAMINHADA_A_CLICHERIA,
        StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
        StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
        StatusProvaEnum.CANCELADA,
        StatusProvaEnum.ENCAMINHADA_PARA_LAMINACAO,
        StatusProvaEnum.LAMINACAO_CONCLUIDA,
        StatusProvaEnum.DE_VOLTA_3STUDIO_POS_LAMINACAO,
        StatusProvaEnum.ENCAMINHADA_PARA_O_VENDEDOR,
    ],
)
def test_status_nao_motorista_retorna_none(status: StatusProvaEnum):
    """Apenas os 4 estados com 'COM_MOTORISTA' produzem contexto. Demais 13 retornam None."""
    assert contexto_motorista(status) is None


def test_todos_estados_motorista_mapeados():
    """Defensive: garante exhaustividade entre os 4 estados que envolvem motorista."""
    estados_motorista = [
        StatusProvaEnum.COM_MOTORISTA,
        StatusProvaEnum.COM_MOTORISTA_IDA_LAMINACAO,
        StatusProvaEnum.COM_MOTORISTA_VOLTA_LAMINACAO,
        StatusProvaEnum.COM_MOTORISTA_ENTREGA_FINAL,
    ]
    for s in estados_motorista:
        assert contexto_motorista(s) is not None, f"{s.value} deveria mapear para um contexto"
