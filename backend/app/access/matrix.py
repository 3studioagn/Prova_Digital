"""Matriz de Acesso (RBAC) — Wave 1 v4.0, Componente 05.

Le shared/access-matrix.json (fonte unica espelhada por TS, Python e RLS)
e expoe API tipada para o backend FastAPI.

Ver tambem:
- shared/access-matrix.json (SSoT)
- frontend/src/lib/access-matrix.ts (espelho TS)
- backend/migrations/rls/012_move_helpers_to_app_private.sql (espelho RLS)
- docs/wave1-v4/analysis.md Secao 4
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Final, Literal

from app.db.models import SetorEnum, Usuario

# Caminho relativo a backend/app/access/matrix.py:
#   backend/app/access/matrix.py
#   backend/app/access/                  parent
#   backend/app/                         parent.parent
#   backend/                             parent.parent.parent
#   <repo root>/                         parent.parent.parent.parent
#   shared/access-matrix.json
_MATRIX_JSON_PATH: Final[Path] = (
    Path(__file__).resolve().parent.parent.parent.parent / "shared" / "access-matrix.json"
)


class Profile(str, Enum):
    """Perfis da Matriz de Acesso. Espelha JSON `perfis` exatamente."""

    STUDIO_ADMIN = "studio_admin"
    VENDEDOR = "vendedor"
    MOTORISTA = "motorista"
    CLICHERIA = "clicheria"


class Acesso(str, Enum):
    FULL = "full"
    PARCIAL = "parcial"
    NEGADO = "negado"


# Strings de scope usadas pelo Pydantic e pelo helper scope_filter_for em
# scopes.py. Tipo Literal restringe valores aceitos.
ScopeKind = Literal[
    "self_vendedor",
    "status_motorista_em_transito",
    "status_clicheria",
]


@dataclass(frozen=True)
class PerfilDecision:
    acesso: Acesso
    scope: ScopeKind | None = None


@dataclass(frozen=True)
class AccessRule:
    key: str
    path: str
    match: Literal["exact", "prefix", "dynamic", "action"]
    matrix_row: str
    perfis: dict[Profile, PerfilDecision]


@dataclass(frozen=True)
class MatrixSnapshot:
    """Snapshot imutavel da matriz lida do JSON."""

    version: str
    rules: tuple[AccessRule, ...]
    home_by_profile: dict[Profile, str]
    rules_by_key: dict[str, AccessRule]


@lru_cache(maxsize=1)
def _load_matrix() -> MatrixSnapshot:
    """Carrega e valida o JSON SSoT uma unica vez por processo."""
    if not _MATRIX_JSON_PATH.exists():
        raise FileNotFoundError(
            f"shared/access-matrix.json nao encontrado em {_MATRIX_JSON_PATH}. "
            "Verifique a estrutura do repositorio."
        )

    with _MATRIX_JSON_PATH.open(encoding="utf-8") as f:
        raw = json.load(f)

    # Validacao basica de estrutura — falhas aqui abortam o startup do app.
    expected_perfis = {p.value for p in Profile}
    if set(raw.get("perfis", [])) != expected_perfis:
        raise ValueError(
            f"shared/access-matrix.json: campo 'perfis' deve ser exatamente "
            f"{sorted(expected_perfis)}, recebido {raw.get('perfis')}."
        )

    home_by_profile_raw = {
        k: v for k, v in raw.get("home_by_profile", {}).items() if not k.startswith("_")
    }
    if set(home_by_profile_raw.keys()) != expected_perfis:
        raise ValueError(
            "shared/access-matrix.json: 'home_by_profile' deve ter os 4 perfis."
        )
    home_by_profile = {Profile(k): v for k, v in home_by_profile_raw.items()}

    rules: list[AccessRule] = []
    for rule_dict in raw.get("rules", []):
        perfis_raw = rule_dict["perfis"]
        if set(perfis_raw.keys()) != expected_perfis:
            raise ValueError(
                f"shared/access-matrix.json: regra '{rule_dict.get('key')}' deve "
                f"ter decisao para os 4 perfis, tem {sorted(perfis_raw.keys())}."
            )
        perfis = {
            Profile(p): PerfilDecision(
                acesso=Acesso(d["acesso"]),
                scope=d.get("scope"),
            )
            for p, d in perfis_raw.items()
        }
        rules.append(
            AccessRule(
                key=rule_dict["key"],
                path=rule_dict["path"],
                match=rule_dict["match"],
                matrix_row=rule_dict.get("_matrix_row", ""),
                perfis=perfis,
            )
        )

    return MatrixSnapshot(
        version=str(raw.get("version", "")),
        rules=tuple(rules),
        home_by_profile=home_by_profile,
        rules_by_key={r.key: r for r in rules},
    )


def get_matrix() -> MatrixSnapshot:
    """API publica para obter a matriz."""
    return _load_matrix()


def resolve_profile(user: Usuario | None) -> Profile | None:
    """Classifica um Usuario em um Profile.

    Regra: admin tem precedencia sobre setor. Se is_admin=True -> STUDIO_ADMIN
    (mesmo que setor seja STUDIO/VENDEDOR/etc — nao deveria acontecer em
    producao, mas e a regra robusta). Senao mapeia setor para perfil.

    STUDIO sem is_admin retorna None (perfil "negado em tudo" — nao mapeia
    para nenhuma das 4 entradas da Matriz). Isso e seguro: enforce_access_for
    e get_rule_for_path tratam None como acesso negado.
    """
    if user is None:
        return None
    if user.is_admin:
        return Profile.STUDIO_ADMIN
    if user.setor == SetorEnum.VENDEDOR:
        return Profile.VENDEDOR
    if user.setor == SetorEnum.MOTORISTA:
        return Profile.MOTORISTA
    if user.setor == SetorEnum.CLICHERIA:
        return Profile.CLICHERIA
    # SetorEnum.STUDIO sem is_admin: nao ha entrada na Matriz
    return None


def evaluate(rule: AccessRule, user: Usuario | None) -> PerfilDecision:
    """Avalia o acesso de um Usuario para uma AccessRule especifica.

    Sem user (anon) ou perfil nao mapeado -> NEGADO.
    """
    profile = resolve_profile(user)
    if profile is None:
        return PerfilDecision(acesso=Acesso.NEGADO)
    return rule.perfis[profile]


def get_rule_for_key(key: str) -> AccessRule | None:
    """Busca uma regra pela `key` (ex.: 'provas.list', 'auditoria')."""
    return get_matrix().rules_by_key.get(key)


def home_for_profile(profile: Profile | None) -> str:
    """Pagina inicial para redirect 302 quando acesso e negado.

    Sem perfil resolvido (anon / setor nao mapeado), redireciona para login.
    """
    if profile is None:
        return "/login"
    return get_matrix().home_by_profile[profile]
