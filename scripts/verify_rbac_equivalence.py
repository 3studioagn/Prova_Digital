"""verify_rbac_equivalence.py — Wave 1 v4.0, Componente 05.

Valida a equivalencia entre as 3 camadas da Matriz de Acesso:
  1. shared/access-matrix.json (SSoT)
  2. backend/app/access (Python)
  3. backend/migrations/rls/012_*.sql (RLS no Postgres)

Mitiga o risco R-1 da analysis (drift entre camadas).

Como executar:
  cd backend && python ../scripts/verify_rbac_equivalence.py

Pre-requisitos:
  - DATABASE_URL apontando para um Postgres com schema dominio aplicado e
    as RLS 009-012 ativas (validar via apply_migration ou apply_rls.py).
  - Permissoes para INSERT/DELETE em public.usuarios (usa sessao postgres).

Procedimento:
  1. INSERT 4 usuarios "smoke" (1 por perfil) com auth_uid arbitrarios.
     Idempotente (ON CONFLICT DO NOTHING).
  2. Para cada perfil, executa SELECT count(*) em provas_digitais,
     movimentacoes, etiquetas, audit_logs, configuracoes_sistema, usuarios
     impersonando role authenticated via set_config request.jwt.claims.
  3. Para cada perfil, valida que os counts batem com o esperado pela
     Matriz (usando app.access.scope_filter_for + queries equivalentes).
  4. DELETE dos usuarios smoke ao final (best-effort cleanup).

Saida: relatorio textual + exit code 0 (todos batem) ou 1 (divergencias).

Uso tipico: rodar manualmente apos aplicar nova RLS ou alterar a Matriz.
NAO incluido na suite pytest porque exige Postgres real (e dev/staging,
nao mock).
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

# Permite importar app.access sem alterar PYTHONPATH externamente.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.access import (  # noqa: E402
    Acesso,
    Profile,
    evaluate,
    get_matrix,
)

# ─── Config ───────────────────────────────────────────────────────────────


DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    sys.exit(
        "DATABASE_URL nao definida. Use:\n"
        "  DATABASE_URL=postgresql://... python scripts/verify_rbac_equivalence.py"
    )

# UUIDs determinísticos — claramente fora de producao.
SMOKE_USER_AUTH_UIDS: dict[Profile, uuid.UUID] = {
    Profile.STUDIO_ADMIN: uuid.UUID("00000000-0000-4000-8000-eee100000001"),
    Profile.VENDEDOR:     uuid.UUID("00000000-0000-4000-8000-eee100000002"),
    Profile.MOTORISTA:    uuid.UUID("00000000-0000-4000-8000-eee100000003"),
    Profile.CLICHERIA:    uuid.UUID("00000000-0000-4000-8000-eee100000004"),
}
SMOKE_USER_IDS: dict[Profile, uuid.UUID] = {
    Profile.STUDIO_ADMIN: uuid.UUID("00000000-0000-4001-8001-eee200000001"),
    Profile.VENDEDOR:     uuid.UUID("00000000-0000-4001-8001-eee200000002"),
    Profile.MOTORISTA:    uuid.UUID("00000000-0000-4001-8001-eee200000003"),
    Profile.CLICHERIA:    uuid.UUID("00000000-0000-4001-8001-eee200000004"),
}
SMOKE_EMAIL_PREFIX = "wave1v4-rls-equiv-"


@asynccontextmanager
async def conn() -> AsyncIterator:
    import asyncpg  # type: ignore

    url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    c = await asyncpg.connect(url)
    try:
        yield c
    finally:
        await c.close()


async def seed_users() -> None:
    async with conn() as c:
        for profile, auth_uid in SMOKE_USER_AUTH_UIDS.items():
            user_id = SMOKE_USER_IDS[profile]
            email = f"{SMOKE_EMAIL_PREFIX}{profile.value}@local.invalid"
            if profile == Profile.STUDIO_ADMIN:
                setor, is_admin, loc = "STUDIO", True, None
            elif profile == Profile.VENDEDOR:
                setor, is_admin, loc = "VENDEDOR", False, "MATRIZ"
            elif profile == Profile.MOTORISTA:
                setor, is_admin, loc = "MOTORISTA", False, None
            else:
                setor, is_admin, loc = "CLICHERIA", False, None

            await c.execute(
                """
                INSERT INTO public.usuarios
                  (id, auth_uid, nome, email, setor, localizacao, is_admin, ativo)
                VALUES ($1, $2, $3, $4, $5::public.setor_enum,
                        $6::public.localizacao_enum, $7, true)
                ON CONFLICT (auth_uid) DO NOTHING
                """,
                user_id, auth_uid, f"WAVE1V4 RLS EQUIV {profile.value}",
                email, setor, loc, is_admin,
            )


async def cleanup_users() -> None:
    async with conn() as c:
        await c.execute(
            "DELETE FROM public.usuarios WHERE email LIKE $1",
            f"{SMOKE_EMAIL_PREFIX}%",
        )


# ─── Cobertura das 6 tabelas (AUD-W1V4-002) ──────────────────────────
#
# 6 tabelas com policies RLS no schema public, todas referenciando
# helpers app_private.current_user_*. A Wave 1 v4.0 inicial só validava
# provas_digitais. AUD-W1V4-002 estende para o conjunto completo.

TABLES_TO_VALIDATE: tuple[str, ...] = (
    "provas_digitais",       # pol_provas_select
    "movimentacoes",         # pol_movimentacoes_select
    "etiquetas",             # pol_etiquetas_select
    "audit_logs",            # pol_audit_select (admin only)
    "configuracoes_sistema", # pol_config_select (admin only)
    "usuarios",              # pol_usuarios_select (self or admin)
)


# ─── Counts genericos ────────────────────────────────────────────────


async def count_admin_total(table: str) -> int:
    """Total real da tabela (bypass RLS via sessao postgres).

    Usado como expected para perfis FULL. `table` e hardcoded em
    TABLES_TO_VALIDATE — interpolacao em f-string e segura.
    """
    async with conn() as c:
        row = await c.fetchrow(f"SELECT count(*)::int AS n FROM public.{table}")
        return int(row["n"]) if row else 0


async def count_visible_table(auth_uid: uuid.UUID, table: str) -> int:
    """Count visivel sob role `authenticated` impersonado para `auth_uid`.

    AUD-W1V4-002: substitui count_visible_provas (que so cobria
    provas_digitais). Aceita qualquer tabela em TABLES_TO_VALIDATE.
    """
    async with conn() as c:
        async with c.transaction():
            await c.execute(
                "SELECT set_config('request.jwt.claims', $1, true)",
                f'{{"sub":"{auth_uid}","role":"authenticated"}}',
            )
            await c.execute("SELECT set_config('role', 'authenticated', true)")
            row = await c.fetchrow(f"SELECT count(*)::int AS n FROM public.{table}")
            return int(row["n"]) if row else 0


# Aliases retrocompatíveis (mantem legibilidade do main()).

async def count_visible_provas(auth_uid: uuid.UUID) -> int:
    return await count_visible_table(auth_uid, "provas_digitais")


async def count_provas_admin_view() -> int:
    return await count_admin_total("provas_digitais")


# ─── Expectativas por scope (Matriz Python) ──────────────────────────


async def count_provas_motorista_expected() -> int:
    """Provas com status COM_MOTORISTA (scope status_motorista_em_transito)."""
    async with conn() as c:
        row = await c.fetchrow(
            "SELECT count(*)::int AS n FROM public.provas_digitais "
            "WHERE status = 'COM_MOTORISTA'::public.status_prova_enum"
        )
        return int(row["n"]) if row else 0


async def count_provas_clicheria_expected() -> int:
    async with conn() as c:
        row = await c.fetchrow(
            "SELECT count(*)::int AS n FROM public.provas_digitais "
            "WHERE status = ANY (ARRAY["
            "  'ENVIADA_PARA_CLICHERIA'::public.status_prova_enum,"
            "  'ENCAMINHADA_A_CLICHERIA'::public.status_prova_enum,"
            "  'RECEBIDA_PELA_CLICHERIA'::public.status_prova_enum])"
        )
        return int(row["n"]) if row else 0


async def count_provas_vendedor_self_expected(user_id: uuid.UUID) -> int:
    """Provas onde vendedor_id = user_id (scope self_vendedor)."""
    async with conn() as c:
        row = await c.fetchrow(
            "SELECT count(*)::int AS n FROM public.provas_digitais "
            "WHERE vendedor_id = $1",
            user_id,
        )
        return int(row["n"]) if row else 0


# Movimentacoes: pol_movimentacoes_select abrange admin OR self_vendedor
# via prova OR ator_self (usuario_id) OR motorista_status OR clicheria_status.

async def count_movimentacoes_vendedor_self_expected(user_id: uuid.UUID) -> int:
    async with conn() as c:
        row = await c.fetchrow(
            "SELECT count(*)::int AS n FROM public.movimentacoes m "
            "WHERE m.usuario_id = $1 "
            "OR m.prova_id IN (SELECT id FROM public.provas_digitais "
            "                  WHERE vendedor_id = $1)",
            user_id,
        )
        return int(row["n"]) if row else 0


async def count_movimentacoes_motorista_expected(user_id: uuid.UUID) -> int:
    async with conn() as c:
        row = await c.fetchrow(
            "SELECT count(*)::int AS n FROM public.movimentacoes m "
            "WHERE m.usuario_id = $1 "
            "OR m.prova_id IN (SELECT id FROM public.provas_digitais "
            "                  WHERE status = 'COM_MOTORISTA'::public.status_prova_enum)",
            user_id,
        )
        return int(row["n"]) if row else 0


async def count_movimentacoes_clicheria_expected(user_id: uuid.UUID) -> int:
    async with conn() as c:
        row = await c.fetchrow(
            "SELECT count(*)::int AS n FROM public.movimentacoes m "
            "WHERE m.usuario_id = $1 "
            "OR m.prova_id IN (SELECT id FROM public.provas_digitais "
            "                  WHERE status = ANY (ARRAY["
            "                    'ENVIADA_PARA_CLICHERIA'::public.status_prova_enum,"
            "                    'ENCAMINHADA_A_CLICHERIA'::public.status_prova_enum,"
            "                    'RECEBIDA_PELA_CLICHERIA'::public.status_prova_enum]))",
            user_id,
        )
        return int(row["n"]) if row else 0


# Etiquetas: pol_etiquetas_select via prova (sem branch ator_self).

async def count_etiquetas_vendedor_self_expected(user_id: uuid.UUID) -> int:
    async with conn() as c:
        row = await c.fetchrow(
            "SELECT count(*)::int AS n FROM public.etiquetas e "
            "WHERE EXISTS (SELECT 1 FROM public.provas_digitais pd "
            "              WHERE pd.id = e.prova_id AND pd.vendedor_id = $1)",
            user_id,
        )
        return int(row["n"]) if row else 0


async def count_etiquetas_motorista_expected() -> int:
    async with conn() as c:
        row = await c.fetchrow(
            "SELECT count(*)::int AS n FROM public.etiquetas e "
            "WHERE EXISTS (SELECT 1 FROM public.provas_digitais pd "
            "              WHERE pd.id = e.prova_id "
            "              AND pd.status = 'COM_MOTORISTA'::public.status_prova_enum)"
        )
        return int(row["n"]) if row else 0


async def count_etiquetas_clicheria_expected() -> int:
    async with conn() as c:
        row = await c.fetchrow(
            "SELECT count(*)::int AS n FROM public.etiquetas e "
            "WHERE EXISTS (SELECT 1 FROM public.provas_digitais pd "
            "              WHERE pd.id = e.prova_id "
            "              AND pd.status = ANY (ARRAY["
            "                'ENVIADA_PARA_CLICHERIA'::public.status_prova_enum,"
            "                'ENCAMINHADA_A_CLICHERIA'::public.status_prova_enum,"
            "                'RECEBIDA_PELA_CLICHERIA'::public.status_prova_enum]))"
        )
        return int(row["n"]) if row else 0


async def expected_counts_for_smoke_users() -> dict[Profile, dict[str, int]]:
    """Constroi a matriz esperada (profile, table) -> count.

    Para cada perfil smoke, calcula o que a Matriz da Wave 1 v4.0 deve
    permitir ver. Para FULL = total da tabela. Para NEGADO = 0. Para
    PARCIAL, calcula via query equivalente ao scope (espelhando a clausula
    da policy correspondente em RLS 010/011/012).

    AUD-W1V4-002: estende cobertura de 1 (provas_digitais) para 6
    tabelas.
    """
    out: dict[Profile, dict[str, int]] = {p: {} for p in Profile}

    # studio_admin: full em todas as 6 tabelas.
    for t in TABLES_TO_VALIDATE:
        out[Profile.STUDIO_ADMIN][t] = await count_admin_total(t)

    vendedor_id = SMOKE_USER_IDS[Profile.VENDEDOR]
    motorista_id = SMOKE_USER_IDS[Profile.MOTORISTA]
    clicheria_id = SMOKE_USER_IDS[Profile.CLICHERIA]

    # vendedor: parcial self_vendedor em provas/mov/etiquetas; negado em
    # audit/config; self (= 1) em usuarios.
    out[Profile.VENDEDOR]["provas_digitais"] = \
        await count_provas_vendedor_self_expected(vendedor_id)
    out[Profile.VENDEDOR]["movimentacoes"] = \
        await count_movimentacoes_vendedor_self_expected(vendedor_id)
    out[Profile.VENDEDOR]["etiquetas"] = \
        await count_etiquetas_vendedor_self_expected(vendedor_id)
    out[Profile.VENDEDOR]["audit_logs"] = 0
    out[Profile.VENDEDOR]["configuracoes_sistema"] = 0
    out[Profile.VENDEDOR]["usuarios"] = 1  # self via pol_usuarios_select

    # motorista: parcial status_motorista em provas/mov/etiquetas; negado
    # em audit/config; self em usuarios.
    out[Profile.MOTORISTA]["provas_digitais"] = \
        await count_provas_motorista_expected()
    out[Profile.MOTORISTA]["movimentacoes"] = \
        await count_movimentacoes_motorista_expected(motorista_id)
    out[Profile.MOTORISTA]["etiquetas"] = \
        await count_etiquetas_motorista_expected()
    out[Profile.MOTORISTA]["audit_logs"] = 0
    out[Profile.MOTORISTA]["configuracoes_sistema"] = 0
    out[Profile.MOTORISTA]["usuarios"] = 1

    # clicheria: parcial status_clicheria em provas/mov/etiquetas; negado
    # em audit/config; self em usuarios.
    out[Profile.CLICHERIA]["provas_digitais"] = \
        await count_provas_clicheria_expected()
    out[Profile.CLICHERIA]["movimentacoes"] = \
        await count_movimentacoes_clicheria_expected(clicheria_id)
    out[Profile.CLICHERIA]["etiquetas"] = \
        await count_etiquetas_clicheria_expected()
    out[Profile.CLICHERIA]["audit_logs"] = 0
    out[Profile.CLICHERIA]["configuracoes_sistema"] = 0
    out[Profile.CLICHERIA]["usuarios"] = 1

    return out


async def main() -> int:
    print("=" * 70)
    print("verify_rbac_equivalence — Wave 1 v4.0, Componente 05")
    print("=" * 70)

    print("\n[1/4] Carregando matriz (Python + JSON)...")
    matrix = get_matrix()
    print(f"      OK — {len(matrix.rules)} regras x 4 perfis = {len(matrix.rules)*4} celulas")

    print("\n[2/4] Seeding 4 usuarios smoke...")
    try:
        await seed_users()
    except Exception as e:
        print(f"      FALHA: {e}")
        return 1
    print("      OK")

    failures: list[str] = []
    try:
        print("\n[3/4] Validando RLS via SQL impersonado (4 perfis x 6 tabelas)...")
        # AUD-W1V4-002: cobertura estendida de 1 (provas_digitais) para 6
        # tabelas com policies em public.* via app_private.current_user_*.
        # Esperados por (perfil, tabela) constroidos por expected_counts_for_smoke_users
        # (espelha as clausulas das policies em RLS 010/011/012).
        expected = await expected_counts_for_smoke_users()

        rls_counts: dict[Profile, dict[str, int]] = {p: {} for p in Profile}
        for profile in Profile:
            auth_uid = SMOKE_USER_AUTH_UIDS[profile]
            for table in TABLES_TO_VALIDATE:
                rls_counts[profile][table] = await count_visible_table(auth_uid, table)

        # Cabecalho da matriz 4x6.
        col_w = max(len(t) for t in TABLES_TO_VALIDATE) + 2
        print("      " + " ".ljust(14) + "".join(t.ljust(col_w) for t in TABLES_TO_VALIDATE))
        for profile in Profile:
            row = [f"{rls_counts[profile][t]}/{expected[profile][t]}".ljust(col_w)
                   for t in TABLES_TO_VALIDATE]
            print(f"      {profile.value.ljust(14)}" + "".join(row))
        print("      (formato: visto/esperado por (perfil, tabela))")

        # Comparacao dura: cada celula precisa bater.
        for profile in Profile:
            for table in TABLES_TO_VALIDATE:
                seen = rls_counts[profile][table]
                exp = expected[profile][table]
                if seen != exp:
                    failures.append(
                        f"[{profile.value}][{table}] RLS viu {seen}, esperado {exp}"
                    )

        # Aliases retrocompativeis usados pela etapa [4/4].
        admin_total = expected[Profile.STUDIO_ADMIN]["provas_digitais"]
        admin_seen = rls_counts[Profile.STUDIO_ADMIN]["provas_digitais"]
        vendedor_seen = rls_counts[Profile.VENDEDOR]["provas_digitais"]
        motorista_seen = rls_counts[Profile.MOTORISTA]["provas_digitais"]
        clicheria_seen = rls_counts[Profile.CLICHERIA]["provas_digitais"]

        print("\n[4/4] Validando equivalencia Matriz Python <-> RLS por celula...")
        # AUD-W1V4-003: a etapa anterior (M-5) so pegava drift no caso
        # `NEGADO + count > 0`. Cenarios FULL e PARCIAL passavam silenciosamente
        # mesmo com divergencia. AUD-W1V4-107 substituiu o bloco abaixo por
        # validacao explicita de cada (rule, profile, table) onde a regra
        # GOVERNA o SELECT da tabela.
        #
        # O mapping `RULE_GOVERNS_TABLE` lista as regras que controlam
        # diretamente o SELECT em uma ou mais tabelas RLS-protegidas:
        #   - provas.list   -> provas_digitais
        #   - provas.detail -> provas_digitais + movimentacoes + etiquetas
        #     (endpoints derivados do detalhe usam essas tabelas via
        #     pol_movimentacoes_select/pol_etiquetas_select)
        #   - auditoria     -> audit_logs
        #   - configuracoes -> configuracoes_sistema
        # Outras regras (login, dashboard, scanner, provas.create,
        # provas.cancel, provas.restart, usuarios, relatorios) nao governam
        # SELECT direto — ou sao universais, ou controlam INSERT/UPDATE,
        # ou usam SELECT mais permissivo (ex: pol_usuarios_select e
        # self_or_admin, mais largo que a regra de pagina). Para essas,
        # mantemos a validacao de sanity do enum Acesso.
        from datetime import datetime, timezone  # noqa: PLC0415

        # Constroi os 4 usuarios fixture uma unica vez.
        from app.db.models import (  # noqa: PLC0415
            LocalizacaoEnum,
            SetorEnum,
            Usuario,  # noqa: PLC0415
        )
        def _u(setor, is_admin, loc=None):
            return Usuario(
                id=uuid.uuid4(), auth_uid=uuid.uuid4(),
                nome="x", email=f"x-{is_admin}-{setor.value}@test",
                setor=setor, localizacao=loc, is_admin=is_admin, ativo=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        users_by_profile = {
            Profile.STUDIO_ADMIN: _u(SetorEnum.STUDIO, True),
            Profile.VENDEDOR:     _u(SetorEnum.VENDEDOR, False, LocalizacaoEnum.MATRIZ),
            Profile.MOTORISTA:    _u(SetorEnum.MOTORISTA, False),
            Profile.CLICHERIA:    _u(SetorEnum.CLICHERIA, False),
        }

        # Mapping rule_key -> tabelas que a regra governa para SELECT.
        rule_governs_table: dict[str, tuple[str, ...]] = {
            "provas.list":   ("provas_digitais",),
            "provas.detail": ("provas_digitais", "movimentacoes", "etiquetas"),
            "auditoria":     ("audit_logs",),
            "configuracoes": ("configuracoes_sistema",),
        }

        cells_validated = 0
        for rule_key, tables in rule_governs_table.items():
            rule = matrix.rules_by_key[rule_key]
            for profile, user in users_by_profile.items():
                decision = evaluate(rule, user)
                for table in tables:
                    seen = rls_counts[profile][table]
                    admin_total_t = rls_counts[Profile.STUDIO_ADMIN][table]

                    if decision.acesso == Acesso.NEGADO:
                        if seen != 0:
                            failures.append(
                                f"[{rule_key}][{profile.value}][{table}] "
                                f"Matriz=NEGADO mas RLS viu {seen} > 0 (drift)."
                            )
                    elif decision.acesso == Acesso.FULL:
                        if seen != admin_total_t:
                            failures.append(
                                f"[{rule_key}][{profile.value}][{table}] "
                                f"Matriz=FULL mas RLS viu {seen} de "
                                f"{admin_total_t} possiveis (drift)."
                            )
                    elif decision.acesso == Acesso.PARCIAL:
                        # Para PARCIAL, validamos contra `expected` calculado
                        # via espelho da clausula da policy (etapa [3/4]).
                        # Se o smoke vendedor tem 0 provas e expected=0,
                        # passa. Se aparece prova nova com vendedor_id smoke,
                        # expected sobe e RLS deve refletir.
                        exp = expected[profile][table]
                        if seen != exp:
                            failures.append(
                                f"[{rule_key}][{profile.value}][{table}] "
                                f"Matriz=PARCIAL scope={decision.scope} mas "
                                f"RLS viu {seen}, esperado {exp} (drift)."
                            )
                    cells_validated += 1

        # Sanity das outras 8 regras (4 universais + 4 admin-only de acao):
        # validar apenas que decision retorna Acesso enum valido (confirma
        # parsing do JSON sem corrupcao). Sem teste de count direto.
        sanity_validated = 0
        for rule in matrix.rules:
            if rule.key in rule_governs_table:
                continue
            for profile, user in users_by_profile.items():
                decision = evaluate(rule, user)
                if decision.acesso not in (Acesso.FULL, Acesso.PARCIAL, Acesso.NEGADO):
                    failures.append(
                        f"[{rule.key}][{profile.value}] decision invalida: "
                        f"{decision!r}"
                    )
                sanity_validated += 1

        # Total: 4 governadas (1+3+1+1=6 mappings) x 4 perfis = 24 cells +
        # 8 nao-governadas x 4 perfis = 32 cells sanity = 56 validacoes.
        expected_governed = sum(len(ts) for ts in rule_governs_table.values()) * 4
        expected_sanity = (len(matrix.rules) - len(rule_governs_table)) * 4
        if cells_validated != expected_governed:
            failures.append(
                f"Esperava {expected_governed} cells governadas validadas, "
                f"validei {cells_validated}."
            )
        if sanity_validated != expected_sanity:
            failures.append(
                f"Esperava {expected_sanity} cells sanity validadas, "
                f"validei {sanity_validated}."
            )
        if not failures:
            print(f"      OK — {cells_validated} cells governadas (rule x profile x table) "
                  f"+ {sanity_validated} cells sanity validadas contra RLS.")

    finally:
        print("\n[cleanup] Removendo usuarios smoke...")
        try:
            await cleanup_users()
            print("          OK")
        except Exception as e:
            print(f"          ATENCAO: cleanup falhou: {e}")

    print("\n" + "=" * 70)
    if failures:
        print(f"FALHA: {len(failures)} divergencia(s)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("SUCESSO: todas as camadas batem.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
