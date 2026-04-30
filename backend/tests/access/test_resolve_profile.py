"""Testes do helper resolve_profile (Wave 1 v4.0).

Garante que classifica corretamente todos os casos:
- is_admin=True -> STUDIO_ADMIN (mesmo se setor for diferente).
- is_admin=False + setor in (VENDEDOR/MOTORISTA/CLICHERIA) -> perfil correspondente.
- is_admin=False + setor=STUDIO -> None (nao mapeado, comportamento defensivo).
- user=None -> None.
"""
from app.access import Profile, resolve_profile
from app.db.models import LocalizacaoEnum, SetorEnum
from tests.conftest import make_user


class TestResolveProfile:
    def test_admin_studio_returns_studio_admin(self):
        u = make_user(setor=SetorEnum.STUDIO, is_admin=True)
        assert resolve_profile(u) == Profile.STUDIO_ADMIN

    def test_admin_with_other_setor_still_returns_studio_admin(self):
        """is_admin tem precedencia. Caso teorico (modelo permite, producao nao)."""
        u = make_user(
            setor=SetorEnum.VENDEDOR,
            localizacao=LocalizacaoEnum.MATRIZ,
            is_admin=True,
        )
        assert resolve_profile(u) == Profile.STUDIO_ADMIN

    def test_vendedor_returns_vendedor(self):
        u = make_user(
            setor=SetorEnum.VENDEDOR,
            localizacao=LocalizacaoEnum.FILIAL,
            is_admin=False,
        )
        assert resolve_profile(u) == Profile.VENDEDOR

    def test_motorista_returns_motorista(self):
        u = make_user(setor=SetorEnum.MOTORISTA, is_admin=False)
        assert resolve_profile(u) == Profile.MOTORISTA

    def test_clicheria_returns_clicheria(self):
        u = make_user(setor=SetorEnum.CLICHERIA, is_admin=False)
        assert resolve_profile(u) == Profile.CLICHERIA

    def test_studio_without_admin_returns_none(self):
        """STUDIO sem is_admin nao mapeia — comportamento defensivo (negado)."""
        u = make_user(setor=SetorEnum.STUDIO, is_admin=False)
        assert resolve_profile(u) is None

    def test_none_user_returns_none(self):
        assert resolve_profile(None) is None
