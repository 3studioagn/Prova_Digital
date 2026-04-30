"""Testes de invariantes estruturais da Matriz de Acesso (Wave 1 v4.0).

Carregam o shared/access-matrix.json via app.access.matrix.get_matrix() e
validam:
- Os 4 perfis estao corretos.
- Toda regra cobre os 4 perfis.
- Toda regra com acesso='parcial' tem campo 'scope' valido.
- Numero esperado de regras (12 = 13 linhas da Matriz, com Visualizacao+
  Timeline unificadas em provas.detail).
- home_by_profile cobre os 4 perfis.
- Scope kinds usados sao apenas os 3 definidos (self_vendedor /
  status_motorista_em_transito / status_clicheria).
"""
from app.access import (
    Acesso,
    Profile,
    get_matrix,
    get_rule_for_key,
)

VALID_SCOPES = {
    "self_vendedor",
    "status_motorista_em_transito",
    "status_clicheria",
}

# 12 keys esperadas (cobrem as 13 linhas da Matriz; Timeline herda de detail).
EXPECTED_KEYS = {
    "login",
    "dashboard",
    "scanner",
    "provas.list",
    "provas.detail",
    "provas.create",
    "usuarios",
    "relatorios",
    "configuracoes",
    "auditoria",
    "provas.cancel",
    "provas.restart",
}


class TestMatrixStructure:
    """Garantias de integridade da Matriz."""

    def test_matrix_loads_without_error(self):
        m = get_matrix()
        assert m.version == "1"

    def test_has_exactly_expected_rule_keys(self):
        m = get_matrix()
        actual = {r.key for r in m.rules}
        assert actual == EXPECTED_KEYS, (
            f"Sobrando: {actual - EXPECTED_KEYS} ; "
            f"Faltando: {EXPECTED_KEYS - actual}"
        )

    def test_every_rule_covers_4_profiles(self):
        m = get_matrix()
        expected_profiles = set(Profile)
        for rule in m.rules:
            assert set(rule.perfis.keys()) == expected_profiles, (
                f"Regra {rule.key} cobre apenas {set(rule.perfis.keys())}"
            )

    def test_partial_access_has_valid_scope(self):
        m = get_matrix()
        for rule in m.rules:
            for profile, decision in rule.perfis.items():
                if decision.acesso == Acesso.PARCIAL:
                    assert decision.scope is not None, (
                        f"{rule.key}[{profile.value}] e PARCIAL mas scope=None"
                    )
                    assert decision.scope in VALID_SCOPES, (
                        f"{rule.key}[{profile.value}] scope='{decision.scope}' "
                        f"nao esta em {VALID_SCOPES}"
                    )

    def test_full_or_negado_has_no_scope(self):
        """Acesso FULL/NEGADO nao deve ter scope (defensivo)."""
        m = get_matrix()
        for rule in m.rules:
            for profile, decision in rule.perfis.items():
                if decision.acesso in (Acesso.FULL, Acesso.NEGADO):
                    assert decision.scope is None, (
                        f"{rule.key}[{profile.value}] acesso={decision.acesso} "
                        f"mas scope='{decision.scope}'"
                    )

    def test_home_by_profile_covers_all_profiles(self):
        m = get_matrix()
        assert set(m.home_by_profile.keys()) == set(Profile)
        for profile, path in m.home_by_profile.items():
            assert path.startswith("/"), f"home invalido p/ {profile}: {path}"

    def test_get_rule_for_key_known(self):
        rule = get_rule_for_key("auditoria")
        assert rule is not None
        assert rule.path == "/auditoria"
        assert rule.match == "prefix"

    def test_get_rule_for_key_unknown(self):
        assert get_rule_for_key("inexistente.foo") is None

    def test_match_kinds_are_known(self):
        """Apenas 4 kinds de match aceitos."""
        m = get_matrix()
        valid = {"exact", "prefix", "dynamic", "action"}
        for rule in m.rules:
            assert rule.match in valid, (
                f"Regra {rule.key} match='{rule.match}' invalido"
            )

    def test_action_rules_use_action_path(self):
        """Regras 'action' (provas.cancel/restart) tem path='(action)'."""
        m = get_matrix()
        for rule in m.rules:
            if rule.match == "action":
                assert rule.path == "(action)", (
                    f"Regra action {rule.key} deve ter path='(action)', "
                    f"tem '{rule.path}'"
                )


class TestMatrixSemanticInvariants:
    """Invariantes semanticos especificos da v4.0."""

    def test_admin_has_full_access_everywhere(self):
        """3Studio (admin) DEVE ter acesso a tudo."""
        m = get_matrix()
        for rule in m.rules:
            assert rule.perfis[Profile.STUDIO_ADMIN].acesso == Acesso.FULL, (
                f"Regra {rule.key} nao da FULL ao admin"
            )

    def test_vendedor_motorista_clicheria_denied_admin_pages(self):
        """Paginas admin-only devem negar os 3 perfis nao-admin."""
        admin_only_keys = {
            "provas.create",
            "usuarios",
            "relatorios",
            "configuracoes",
            "auditoria",
            "provas.cancel",
            "provas.restart",
        }
        m = get_matrix()
        for key in admin_only_keys:
            rule = m.rules_by_key[key]
            for profile in (Profile.VENDEDOR, Profile.MOTORISTA, Profile.CLICHERIA):
                assert rule.perfis[profile].acesso == Acesso.NEGADO, (
                    f"{key}[{profile.value}] deveria ser NEGADO"
                )

    def test_universal_pages_grant_all_profiles(self):
        """login, dashboard, scanner sao universais (RF-021 + Matriz)."""
        m = get_matrix()
        for key in ("login", "dashboard", "scanner"):
            rule = m.rules_by_key[key]
            for profile in Profile:
                assert rule.perfis[profile].acesso == Acesso.FULL, (
                    f"{key}[{profile.value}] deveria ser FULL"
                )

    def test_provas_list_partial_scopes_match_v3_behaviour(self):
        """provas.list: vendedor=self, motorista=transito, clicheria=status_clicheria, admin=full.

        NOTA: a Matriz v4.0 literal (Secao 6) diz Clicheria='●' (full).
        A Wave 1 v4.0 mantem PARCIAL por status_clicheria para preservar
        o comportamento da v3.0. Ver _clicheria_divergence_note em
        shared/access-matrix.json + DECISIONS.md (follow-up obrigatorio).
        """
        m = get_matrix()
        rule = m.rules_by_key["provas.list"]
        assert rule.perfis[Profile.STUDIO_ADMIN].acesso == Acesso.FULL
        assert rule.perfis[Profile.VENDEDOR].acesso == Acesso.PARCIAL
        assert rule.perfis[Profile.VENDEDOR].scope == "self_vendedor"
        assert rule.perfis[Profile.MOTORISTA].acesso == Acesso.PARCIAL
        assert (
            rule.perfis[Profile.MOTORISTA].scope == "status_motorista_em_transito"
        )
        assert rule.perfis[Profile.CLICHERIA].acesso == Acesso.PARCIAL
        assert rule.perfis[Profile.CLICHERIA].scope == "status_clicheria"

    def test_provas_detail_inherits_provas_list_scopes(self):
        """provas.detail tem mesmos escopos que provas.list (Visualizacao=Timeline)."""
        m = get_matrix()
        rl = m.rules_by_key["provas.list"]
        rd = m.rules_by_key["provas.detail"]
        for profile in Profile:
            assert rl.perfis[profile].acesso == rd.perfis[profile].acesso, (
                f"detail[{profile.value}] != list[{profile.value}]"
            )
            assert rl.perfis[profile].scope == rd.perfis[profile].scope


class TestMatrixRuntimeValidation:
    """M-2 (audit fixes): JSON com schema invalido faz startup falhar.

    Recreia _load_matrix em isolamento (sem o lru_cache global) com cada
    payload mockado e verifica que ValueError e levantado com a mensagem
    correta. Garante que typos no JSON (acesso='fulll', parcial sem scope,
    etc.) nao passam silenciosamente.
    """

    def _build_payload(self, rules: list[dict]) -> dict:
        """Payload base com perfis/home_by_profile validos + rules custom."""
        return {
            "version": "1",
            "perfis": ["studio_admin", "vendedor", "motorista", "clicheria"],
            "home_by_profile": {
                "studio_admin": "/dashboard",
                "vendedor": "/dashboard",
                "motorista": "/escanear",
                "clicheria": "/dashboard",
            },
            "rules": rules,
        }

    def _full_decision_for_all_4(self) -> dict:
        return {
            "studio_admin": {"acesso": "full"},
            "vendedor": {"acesso": "full"},
            "motorista": {"acesso": "full"},
            "clicheria": {"acesso": "full"},
        }

    def _validate(self, payload: dict) -> None:
        """Reimplementa o nucleo da validacao do _load_matrix com payload
        em memoria. Mantemos sincronia manual com matrix.py — se mudar
        lá, mudar aqui."""
        import json
        from pathlib import Path
        from unittest.mock import patch

        import app.access.matrix as matrix_module

        # Limpa cache
        matrix_module._load_matrix.cache_clear()

        # Escreve payload temporariamente em arquivo, pois _load_matrix le
        # do disco. tmp_path do pytest seria mais limpo, mas isolar cache
        # por um teste e suficiente.
        import tempfile

        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(payload, f)
            tmp = Path(f.name)
        try:
            with patch.object(matrix_module, "_MATRIX_JSON_PATH", tmp):
                matrix_module._load_matrix.cache_clear()
                matrix_module._load_matrix()
        finally:
            tmp.unlink(missing_ok=True)
            matrix_module._load_matrix.cache_clear()

    def test_parcial_sem_scope_raises(self):
        import pytest

        rule = {
            "key": "x",
            "path": "/x",
            "match": "exact",
            "perfis": {
                "studio_admin": {"acesso": "full"},
                "vendedor": {"acesso": "parcial"},  # parcial sem scope
                "motorista": {"acesso": "full"},
                "clicheria": {"acesso": "full"},
            },
        }
        with pytest.raises(ValueError, match="parcial mas nao tem campo 'scope'"):
            self._validate(self._build_payload([rule]))

    def test_parcial_com_scope_invalido_raises(self):
        import pytest

        rule = {
            "key": "x",
            "path": "/x",
            "match": "exact",
            "perfis": {
                "studio_admin": {"acesso": "full"},
                "vendedor": {"acesso": "parcial", "scope": "scope_inexistente"},
                "motorista": {"acesso": "full"},
                "clicheria": {"acesso": "full"},
            },
        }
        with pytest.raises(ValueError, match="scope='scope_inexistente' invalido"):
            self._validate(self._build_payload([rule]))

    def test_full_com_scope_raises(self):
        import pytest

        rule = {
            "key": "x",
            "path": "/x",
            "match": "exact",
            "perfis": {
                "studio_admin": {"acesso": "full", "scope": "self_vendedor"},
                "vendedor": {"acesso": "full"},
                "motorista": {"acesso": "full"},
                "clicheria": {"acesso": "full"},
            },
        }
        with pytest.raises(ValueError, match="'scope' so faz sentido"):
            self._validate(self._build_payload([rule]))

    def test_payload_valido_passa(self):
        rule = {
            "key": "x",
            "path": "/x",
            "match": "exact",
            "perfis": {
                "studio_admin": {"acesso": "full"},
                "vendedor": {"acesso": "parcial", "scope": "self_vendedor"},
                "motorista": {"acesso": "negado"},
                "clicheria": {"acesso": "negado"},
            },
        }
        # Nao deve lancar.
        self._validate(self._build_payload([rule]))
