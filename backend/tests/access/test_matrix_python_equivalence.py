"""Equivalencia entre Matriz JSON (camada 1) e backend Python (camada 2).

Wave 1 v4.0 C05.

AUD-W1V4-004 (audit Round 2): renomeado de `test_matrix_rls_equivalence.py`
para `test_matrix_python_equivalence.py` — o nome antigo era enganoso
porque sugeria que a camada RLS estava coberta por pytest. Ela NAO esta:
e validada apenas pelo script standalone scripts/verify_rbac_equivalence.py
contra um Postgres real impersonando role authenticated via
set_config request.jwt.claims.

Camadas da Matriz de Acesso:
  1. Declarativa  -> shared/access-matrix.json
  2. Python       -> app/access (matrix.py + enforce.py + scopes.py)
  3. RLS          -> backend/migrations/rls/012_*.sql
                     (validada via scripts/verify_rbac_equivalence.py
                     etapas [3/4] e [4/4] executadas contra um banco
                     real, fora da suite pytest)

Este arquivo cobre APENAS a equivalencia entre 1 e 2 (Python <-> JSON).

Objetivo: garantir que NENHUMA celula da Matriz pode divergir entre o
JSON SSoT e a logica do backend que consulta esse JSON. Mitiga o risco
R-1 da analysis (alteracao parcial = bypass).

48 celulas = 12 regras (login, dashboard, scanner, provas.list,
provas.detail, provas.create, usuarios, relatorios, configuracoes,
auditoria, provas.cancel, provas.restart) x 4 perfis (studio_admin,
vendedor, motorista, clicheria).
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.access import (
    Acesso,
    Profile,
    enforce_access_for,
    evaluate,
    get_matrix,
    resolve_profile,
)
from app.db.models import LocalizacaoEnum, SetorEnum
from tests.conftest import make_user


def _user_for_profile(profile: Profile):
    if profile == Profile.STUDIO_ADMIN:
        return make_user(setor=SetorEnum.STUDIO, is_admin=True)
    if profile == Profile.VENDEDOR:
        return make_user(
            setor=SetorEnum.VENDEDOR,
            localizacao=LocalizacaoEnum.MATRIZ,
            is_admin=False,
        )
    if profile == Profile.MOTORISTA:
        return make_user(setor=SetorEnum.MOTORISTA, is_admin=False)
    if profile == Profile.CLICHERIA:
        return make_user(setor=SetorEnum.CLICHERIA, is_admin=False)
    raise ValueError(f"Profile desconhecido: {profile}")


class TestMatrixPythonEquivalence:
    """Para cada celula, valida que enforce/evaluate/profile sao consistentes."""

    def test_48_cells_matrix_python_consistent(self):
        cells_validated = 0
        seen_pairs: set[tuple[str, str]] = set()
        for rule in get_matrix().rules:
            for profile, decision in rule.perfis.items():
                user = _user_for_profile(profile)

                # (a) Resolve_profile espelha as 4 categorias da Matriz.
                assert resolve_profile(user) == profile

                # (b) evaluate retorna mesma decision que esta no JSON SSoT.
                actual = evaluate(rule, user)
                assert actual.acesso == decision.acesso, (
                    f"{rule.key}[{profile.value}] Python diverge do JSON: "
                    f"evaluate={actual.acesso} vs SSoT={decision.acesso}"
                )
                if decision.acesso == Acesso.PARCIAL:
                    assert actual.scope == decision.scope

                # (c) enforce_access_for cumpre a Matriz literalmente.
                if decision.acesso == Acesso.NEGADO:
                    with pytest.raises(HTTPException) as exc:
                        enforce_access_for(rule.key, user)
                    assert exc.value.status_code == 403, (
                        f"{rule.key}[{profile.value}] devia 403"
                    )
                else:
                    enforce_access_for(rule.key, user)  # nao deve raise

                seen_pairs.add((rule.key, profile.value))
                cells_validated += 1

        # Sanity: bate o total esperado.
        assert cells_validated == 48, (
            f"Esperava 48 celulas (12 rules x 4 perfis), validei {cells_validated}"
        )
        assert len(seen_pairs) == 48, "Pares (rule, profile) duplicados"
