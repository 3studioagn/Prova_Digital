"""Testes do helper enforce_access_for (Wave 1 v4.0).

Cobertura: para cada (regra, perfil) na Matriz:
- FULL -> nao levanta.
- PARCIAL -> nao levanta (escopo e responsabilidade do scope_filter_for).
- NEGADO -> levanta HTTPException(403).

48 celulas total (12 regras x 4 perfis).
"""
import pytest
from fastapi import HTTPException

from app.access import Acesso, Profile, enforce_access_for, get_matrix
from app.db.models import LocalizacaoEnum, SetorEnum
from tests.conftest import make_user


def _user_for_profile(profile: Profile):
    """Factory: cria Usuario que mapeia para um Profile especifico."""
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


@pytest.fixture(scope="module")
def all_cells():
    """Gera todas as 48 celulas (rule_key, profile, acesso esperado)."""
    cells = []
    for rule in get_matrix().rules:
        for profile, decision in rule.perfis.items():
            cells.append((rule.key, profile, decision.acesso))
    return cells


class TestEnforceAccessFor:
    def test_all_cells_match_expected_decision(self, all_cells):
        """Para cada celula: NEGADO levanta 403, FULL/PARCIAL passa."""
        for rule_key, profile, expected_acesso in all_cells:
            user = _user_for_profile(profile)

            if expected_acesso == Acesso.NEGADO:
                with pytest.raises(HTTPException) as exc:
                    enforce_access_for(rule_key, user)
                assert exc.value.status_code == 403, (
                    f"{rule_key}[{profile.value}] devia 403"
                )
            else:
                # FULL ou PARCIAL: nao levanta
                enforce_access_for(rule_key, user)  # nao deve raise

    def test_unmapped_user_raises_403(self):
        """STUDIO sem is_admin nao mapeia em perfil — qualquer regra nega."""
        u = make_user(setor=SetorEnum.STUDIO, is_admin=False)
        # Mesmo em rota universal como 'login', resolve_profile() retorna None
        # -> evaluate retorna NEGADO -> 403.
        with pytest.raises(HTTPException) as exc:
            enforce_access_for("dashboard", u)
        assert exc.value.status_code == 403

    def test_unknown_rule_key_raises_500(self):
        u = make_user(setor=SetorEnum.STUDIO, is_admin=True)
        with pytest.raises(HTTPException) as exc:
            enforce_access_for("foo.bar.does.not.exist", u)
        assert exc.value.status_code == 500

    def test_admin_passes_every_rule(self):
        """3Studio (admin) passa em todas as 12 regras sem excecao."""
        admin = make_user(setor=SetorEnum.STUDIO, is_admin=True)
        for rule in get_matrix().rules:
            enforce_access_for(rule.key, admin)  # nao deve raise

    def test_vendedor_blocked_admin_pages(self):
        v = make_user(
            setor=SetorEnum.VENDEDOR,
            localizacao=LocalizacaoEnum.FILIAL,
            is_admin=False,
        )
        for key in (
            "provas.create",
            "usuarios",
            "relatorios",
            "configuracoes",
            "auditoria",
            "provas.cancel",
            "provas.restart",
        ):
            with pytest.raises(HTTPException) as exc:
                enforce_access_for(key, v)
            assert exc.value.status_code == 403, key

    def test_vendedor_passes_parcial_provas_list(self):
        """provas.list para vendedor e parcial — passa, escopo aplicado depois."""
        v = make_user(
            setor=SetorEnum.VENDEDOR,
            localizacao=LocalizacaoEnum.MATRIZ,
            is_admin=False,
        )
        enforce_access_for("provas.list", v)  # nao deve raise
        enforce_access_for("provas.detail", v)
