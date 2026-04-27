"""Seed deterministico para validacao manual de Relatorios em staging.

Wave 5, Componente 16. Uso primario: smoke E2E manual antes do deploy.
Os testes unit/integration do projeto (`tests/test_reports_api.py`) NAO
usam este script — eles seguem o padrao do projeto (mocks SQLAlchemy).

Cenarios criados:
  - 2 vendedores: 1 MATRIZ + 1 FILIAL.
  - 1 motorista, 1 clicheria.
  - 8 provas espalhadas:
      * 2 ainda em status RETIRADA_PELO_VENDEDOR (1 fresca, 1 atrasada)
      * 1 APROVADA_PELO_VENDEDOR (rota PADRAO)
      * 1 RECEBIDA_PELA_CLICHERIA via rota PADRAO
      * 1 RECEBIDA_PELA_CLICHERIA via rota DIRETA
      * 1 REPROVADA_PELO_VENDEDOR aguardando reinicio
      * 1 reiniciada (ciclo 2) ja RECEBIDA
      * 1 CANCELADA com motivo
  - Movimentacoes com timestamps espalhados nas ultimas 30h-15d
    para gerar tempos medios calculaveis.

Uso:
    python scripts/seed_reports_fixture.py [--cleanup] [--dry-run]

  --cleanup: remove TODAS as linhas criadas por este seed (idempotente).
             Provas sao marcadas como CANCELADA (nao podem ser deletadas
             pelos triggers de imutabilidade — ADR-009/RNF-005).
             Usuarios criados pelo seed sao desativados, nao deletados.
  --dry-run: mostra o que faria, sem tocar o banco.

Identificacao das linhas: prefixo `SEED:WAVE5:` em audit_logs.detalhes_json
e em motivos/clientes — facilita o cleanup.

Connect string: usa DATABASE_URL do .env (mesma que Alembic).

ATENCAO: nao rodar em producao com volume real — o cleanup pode marcar
provas legitimas como canceladas se houver colisao de nro_requerimento.
Os nros usados aqui (`SEED-W5-NNN`) sao reservados para o seed.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Permite rodar `python scripts/seed_reports_fixture.py` direto do repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "backend"))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.db.models import (  # noqa: E402
    Etiqueta,
    LocalizacaoEnum,
    Movimentacao,
    ProvaDigital,
    RotaEnum,
    SetorEnum,
    StatusProvaEnum,
    Usuario,
)
from app.db.session import async_session  # noqa: E402

UTC = timezone.utc

SEED_PREFIX = "SEED-W5-"
SEED_TAG = "SEED:WAVE5:"

NRO_PROVAS = [f"{SEED_PREFIX}{i:03d}" for i in range(1, 9)]


# ─── Fixtures de dados ────────────────────────────────────────────────────


async def _ensure_user(
    db: AsyncSession,
    *,
    nome: str,
    email: str,
    setor: SetorEnum,
    localizacao: LocalizacaoEnum | None = None,
    is_admin: bool = False,
) -> Usuario:
    """Le ou cria um usuario do seed. Idempotente por email."""
    existing = (
        await db.execute(select(Usuario).where(Usuario.email == email))
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    user = Usuario(
        auth_uid=uuid.uuid4(),
        nome=nome,
        email=email,
        setor=setor,
        localizacao=localizacao,
        is_admin=is_admin,
        ativo=True,
    )
    db.add(user)
    await db.flush()
    return user


async def _create_prova(
    db: AsyncSession,
    *,
    nro: str,
    nome: str,
    cliente: str,
    vendedor_id: uuid.UUID,
    status: StatusProvaEnum,
    rota: RotaEnum | None,
    ciclo_atual: int,
    created_at: datetime,
    motivo_cancelamento: str | None = None,
) -> ProvaDigital:
    """Cria uma prova + etiqueta de seed. Idempotente por nro_requerimento."""
    existing = (
        await db.execute(
            select(ProvaDigital).where(ProvaDigital.nro_requerimento == nro)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    prova = ProvaDigital(
        id=uuid.uuid4(),
        nome=nome,
        nro_requerimento=nro,
        cliente=cliente,
        vendedor_id=vendedor_id,
        imagem_url=f"r2://seed/{nro}.jpg",
        qr_code_hash=uuid.uuid4().hex[:32].ljust(64, "0"),
        status=status,
        rota=rota,
        ciclo_atual=ciclo_atual,
        motivo_cancelamento=motivo_cancelamento,
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(prova)
    await db.flush()

    etiqueta = Etiqueta(
        prova_id=prova.id,
        nome_prova=nome,
        nro_requerimento=nro,
        vendedor_nome=f"{SEED_TAG}vendedor",
        qr_code_image=b"\x89PNG\r\n\x1a\n" + b"\x00" * 64,
        created_at=created_at,
    )
    db.add(etiqueta)
    await db.flush()
    return prova


async def _add_mov(
    db: AsyncSession,
    *,
    prova_id: uuid.UUID,
    usuario_id: uuid.UUID,
    status_anterior: StatusProvaEnum,
    status_novo: StatusProvaEnum,
    ciclo: int,
    created_at: datetime,
    rota_no_momento: RotaEnum | None = None,
    motivo_reprovacao: str | None = None,
) -> Movimentacao:
    """Insere uma movimentacao de seed. Trigger de imutabilidade impede UPDATE."""
    mov = Movimentacao(
        prova_id=prova_id,
        usuario_id=usuario_id,
        status_anterior=status_anterior,
        status_novo=status_novo,
        assinatura_digital=b"SEED-FAKE-SIGNATURE",
        motivo_reprovacao=motivo_reprovacao,
        ciclo=ciclo,
        rota_no_momento=rota_no_momento,
        created_at=created_at,
    )
    db.add(mov)
    await db.flush()
    return mov


# ─── Seed principal ───────────────────────────────────────────────────────


async def seed(db: AsyncSession) -> dict[str, int]:
    """Cria a fixture completa. Retorna contagens.

    Idempotente: re-rodar nao duplica (checks por email/nro_requerimento).
    """
    now = datetime.now(UTC)
    counts: dict[str, int] = {"users": 0, "provas": 0, "movs": 0}

    # ── Usuarios ──
    vendedor_matriz = await _ensure_user(
        db,
        nome=f"{SEED_TAG}Vendedor Matriz",
        email="seed-vendedor-matriz@wave5.local",
        setor=SetorEnum.VENDEDOR,
        localizacao=LocalizacaoEnum.MATRIZ,
    )
    vendedor_filial = await _ensure_user(
        db,
        nome=f"{SEED_TAG}Vendedor Filial",
        email="seed-vendedor-filial@wave5.local",
        setor=SetorEnum.VENDEDOR,
        localizacao=LocalizacaoEnum.FILIAL,
    )
    studio = await _ensure_user(
        db,
        nome=f"{SEED_TAG}Admin Studio",
        email="seed-admin@wave5.local",
        setor=SetorEnum.STUDIO,
        is_admin=True,
    )
    motorista = await _ensure_user(
        db,
        nome=f"{SEED_TAG}Motorista",
        email="seed-motorista@wave5.local",
        setor=SetorEnum.MOTORISTA,
    )
    clicheria = await _ensure_user(
        db,
        nome=f"{SEED_TAG}Clicheria",
        email="seed-clicheria@wave5.local",
        setor=SetorEnum.CLICHERIA,
    )
    counts["users"] = 5

    # ── Provas + Movimentacoes ──
    # Nro 001: RETIRADA fresca (vendedor matriz, ainda no prazo)
    p1 = await _create_prova(
        db,
        nro=NRO_PROVAS[0],
        nome=f"{SEED_TAG}Prova 1 - retirada fresca",
        cliente=f"{SEED_TAG}Cliente A",
        vendedor_id=vendedor_matriz.id,
        status=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        rota=None,
        ciclo_atual=1,
        created_at=now - timedelta(hours=4),
    )
    await _add_mov(
        db,
        prova_id=p1.id,
        usuario_id=vendedor_matriz.id,
        status_anterior=StatusProvaEnum.CRIADA,
        status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        ciclo=1,
        created_at=now - timedelta(hours=3, minutes=30),
    )

    # Nro 002: RETIRADA atrasada (vendedor matriz, parada ha 72h)
    p2 = await _create_prova(
        db,
        nro=NRO_PROVAS[1],
        nome=f"{SEED_TAG}Prova 2 - retirada atrasada",
        cliente=f"{SEED_TAG}Cliente B",
        vendedor_id=vendedor_matriz.id,
        status=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        rota=None,
        ciclo_atual=1,
        created_at=now - timedelta(hours=80),
    )
    await _add_mov(
        db,
        prova_id=p2.id,
        usuario_id=vendedor_matriz.id,
        status_anterior=StatusProvaEnum.CRIADA,
        status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        ciclo=1,
        created_at=now - timedelta(hours=72),
    )

    # Nro 003: APROVADA pelo vendedor (rota PADRAO)
    p3 = await _create_prova(
        db,
        nro=NRO_PROVAS[2],
        nome=f"{SEED_TAG}Prova 3 - aprovada matriz",
        cliente=f"{SEED_TAG}Cliente C",
        vendedor_id=vendedor_matriz.id,
        status=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        rota=RotaEnum.PADRAO,
        ciclo_atual=1,
        created_at=now - timedelta(days=2),
    )
    await _add_mov(
        db,
        prova_id=p3.id,
        usuario_id=vendedor_matriz.id,
        status_anterior=StatusProvaEnum.CRIADA,
        status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        ciclo=1,
        created_at=now - timedelta(days=2, hours=-1),
    )
    await _add_mov(
        db,
        prova_id=p3.id,
        usuario_id=vendedor_matriz.id,
        status_anterior=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        status_novo=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        ciclo=1,
        rota_no_momento=RotaEnum.PADRAO,
        created_at=now - timedelta(days=1, hours=20),
    )

    # Nro 004: ciclo completo PADRAO -> RECEBIDA_PELA_CLICHERIA
    p4 = await _create_prova(
        db,
        nro=NRO_PROVAS[3],
        nome=f"{SEED_TAG}Prova 4 - completa padrao",
        cliente=f"{SEED_TAG}Cliente D",
        vendedor_id=vendedor_matriz.id,
        status=StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
        rota=RotaEnum.PADRAO,
        ciclo_atual=1,
        created_at=now - timedelta(days=10),
    )
    base = now - timedelta(days=10)
    st = StatusProvaEnum
    movs_padrao = [
        (st.CRIADA, st.RETIRADA_PELO_VENDEDOR, 1, vendedor_matriz),
        (st.RETIRADA_PELO_VENDEDOR, st.APROVADA_PELO_VENDEDOR, 1, vendedor_matriz),
        (st.APROVADA_PELO_VENDEDOR, st.DE_VOLTA_3STUDIO, 1, vendedor_matriz),
        (st.DE_VOLTA_3STUDIO, st.COM_MOTORISTA, 1, studio),
        (st.COM_MOTORISTA, st.ENVIADA_PARA_CLICHERIA, 1, motorista),
        (st.ENVIADA_PARA_CLICHERIA, st.RECEBIDA_PELA_CLICHERIA, 1, clicheria),
    ]
    for i, (ant, novo, ciclo, user) in enumerate(movs_padrao):
        await _add_mov(
            db,
            prova_id=p4.id,
            usuario_id=user.id,
            status_anterior=ant,
            status_novo=novo,
            ciclo=ciclo,
            rota_no_momento=RotaEnum.PADRAO if i >= 1 else None,
            created_at=base + timedelta(hours=i * 12),
        )

    # Nro 005: ciclo completo DIRETA (vendedor filial)
    p5 = await _create_prova(
        db,
        nro=NRO_PROVAS[4],
        nome=f"{SEED_TAG}Prova 5 - completa direta",
        cliente=f"{SEED_TAG}Cliente E",
        vendedor_id=vendedor_filial.id,
        status=StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
        rota=RotaEnum.DIRETA,
        ciclo_atual=1,
        created_at=now - timedelta(days=8),
    )
    base = now - timedelta(days=8)
    direta = RotaEnum.DIRETA
    movs_direta = [
        (st.CRIADA, st.RETIRADA_PELO_VENDEDOR, vendedor_filial, None),
        (st.RETIRADA_PELO_VENDEDOR, st.APROVADA_PELO_VENDEDOR, vendedor_filial, direta),
        (st.APROVADA_PELO_VENDEDOR, st.ENCAMINHADA_A_CLICHERIA, vendedor_filial, direta),
        (st.ENCAMINHADA_A_CLICHERIA, st.RECEBIDA_PELA_CLICHERIA, clicheria, direta),
    ]
    for i, (ant, novo, user, rota) in enumerate(movs_direta):
        await _add_mov(
            db,
            prova_id=p5.id,
            usuario_id=user.id,
            status_anterior=ant,
            status_novo=novo,
            ciclo=1,
            rota_no_momento=rota,
            created_at=base + timedelta(hours=i * 8),
        )

    # Nro 006: REPROVADA aguardando reinicio
    p6 = await _create_prova(
        db,
        nro=NRO_PROVAS[5],
        nome=f"{SEED_TAG}Prova 6 - reprovada",
        cliente=f"{SEED_TAG}Cliente F",
        vendedor_id=vendedor_matriz.id,
        status=StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
        rota=None,
        ciclo_atual=1,
        created_at=now - timedelta(days=3),
    )
    await _add_mov(
        db,
        prova_id=p6.id,
        usuario_id=vendedor_matriz.id,
        status_anterior=StatusProvaEnum.CRIADA,
        status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        ciclo=1,
        created_at=now - timedelta(days=3, hours=-2),
    )
    await _add_mov(
        db,
        prova_id=p6.id,
        usuario_id=vendedor_matriz.id,
        status_anterior=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        status_novo=StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
        ciclo=1,
        motivo_reprovacao=f"{SEED_TAG}Cor incorreta",
        created_at=now - timedelta(days=2, hours=10),
    )

    # Nro 007: ciclo reiniciado (RN-006) — agora em ciclo 2 RECEBIDA
    p7 = await _create_prova(
        db,
        nro=NRO_PROVAS[6],
        nome=f"{SEED_TAG}Prova 7 - ciclo reiniciado",
        cliente=f"{SEED_TAG}Cliente G",
        vendedor_id=vendedor_filial.id,
        status=StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
        rota=RotaEnum.DIRETA,
        ciclo_atual=2,
        created_at=now - timedelta(days=12),
    )
    base = now - timedelta(days=12)
    # Ciclo 1: reprovacao
    await _add_mov(
        db,
        prova_id=p7.id,
        usuario_id=vendedor_filial.id,
        status_anterior=StatusProvaEnum.CRIADA,
        status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        ciclo=1,
        created_at=base + timedelta(hours=2),
    )
    await _add_mov(
        db,
        prova_id=p7.id,
        usuario_id=vendedor_filial.id,
        status_anterior=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        status_novo=StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
        ciclo=1,
        motivo_reprovacao=f"{SEED_TAG}Texto errado",
        created_at=base + timedelta(hours=14),
    )
    # Reinicio
    await _add_mov(
        db,
        prova_id=p7.id,
        usuario_id=studio.id,
        status_anterior=StatusProvaEnum.REPROVADA_PELO_VENDEDOR,
        status_novo=StatusProvaEnum.CRIADA,
        ciclo=2,
        created_at=base + timedelta(days=1),
    )
    # Ciclo 2: aprovacao + entrega direta
    await _add_mov(
        db,
        prova_id=p7.id,
        usuario_id=vendedor_filial.id,
        status_anterior=StatusProvaEnum.CRIADA,
        status_novo=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        ciclo=2,
        created_at=base + timedelta(days=1, hours=4),
    )
    await _add_mov(
        db,
        prova_id=p7.id,
        usuario_id=vendedor_filial.id,
        status_anterior=StatusProvaEnum.RETIRADA_PELO_VENDEDOR,
        status_novo=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        ciclo=2,
        rota_no_momento=RotaEnum.DIRETA,
        created_at=base + timedelta(days=1, hours=10),
    )
    await _add_mov(
        db,
        prova_id=p7.id,
        usuario_id=vendedor_filial.id,
        status_anterior=StatusProvaEnum.APROVADA_PELO_VENDEDOR,
        status_novo=StatusProvaEnum.ENCAMINHADA_A_CLICHERIA,
        ciclo=2,
        rota_no_momento=RotaEnum.DIRETA,
        created_at=base + timedelta(days=2),
    )
    await _add_mov(
        db,
        prova_id=p7.id,
        usuario_id=clicheria.id,
        status_anterior=StatusProvaEnum.ENCAMINHADA_A_CLICHERIA,
        status_novo=StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
        ciclo=2,
        rota_no_momento=RotaEnum.DIRETA,
        created_at=base + timedelta(days=3),
    )

    # Nro 008: CANCELADA com motivo
    p8 = await _create_prova(
        db,
        nro=NRO_PROVAS[7],
        nome=f"{SEED_TAG}Prova 8 - cancelada",
        cliente=f"{SEED_TAG}Cliente H",
        vendedor_id=vendedor_matriz.id,
        status=StatusProvaEnum.CANCELADA,
        rota=None,
        ciclo_atual=1,
        created_at=now - timedelta(days=5),
        motivo_cancelamento=f"{SEED_TAG}Cliente desistiu",
    )
    await _add_mov(
        db,
        prova_id=p8.id,
        usuario_id=studio.id,
        status_anterior=StatusProvaEnum.CRIADA,
        status_novo=StatusProvaEnum.CANCELADA,
        ciclo=1,
        created_at=now - timedelta(days=4),
    )

    counts["provas"] = 8
    movs_count = (
        await db.execute(
            select(Movimentacao).where(
                Movimentacao.prova_id.in_([p1.id, p2.id, p3.id, p4.id, p5.id, p6.id, p7.id, p8.id])
            )
        )
    ).all()
    counts["movs"] = len(movs_count)

    return counts


# ─── Cleanup ──────────────────────────────────────────────────────────────


async def cleanup(db: AsyncSession) -> dict[str, int]:
    """Marca provas do seed como CANCELADA + desativa usuarios do seed.

    Provas, movimentacoes, etiquetas e audit_logs sao IMUTAVEIS (triggers).
    Nao podemos DELETE — o melhor e marcar provas como CANCELADA.
    """
    counts: dict[str, int] = {"provas_marcadas": 0, "users_desativados": 0}

    # Provas: SET status = CANCELADA (UPDATE permitido em provas_digitais)
    provas = (
        await db.execute(
            select(ProvaDigital).where(
                ProvaDigital.nro_requerimento.in_(NRO_PROVAS)
            )
        )
    ).scalars().all()
    for p in provas:
        if p.status != StatusProvaEnum.CANCELADA:
            p.status = StatusProvaEnum.CANCELADA
            p.motivo_cancelamento = f"{SEED_TAG}cleanup"
            counts["provas_marcadas"] += 1

    # Usuarios: ativo = false (RN-010 nao se aplica — nao sao admins do sistema)
    users = (
        await db.execute(
            select(Usuario).where(Usuario.email.like("seed-%@wave5.local"))
        )
    ).scalars().all()
    for u in users:
        if u.ativo:
            u.ativo = False
            counts["users_desativados"] += 1

    return counts


# ─── CLI ──────────────────────────────────────────────────────────────────


async def main_async(args: argparse.Namespace) -> None:
    if args.dry_run:
        print(f"[DRY-RUN] Modo: {'cleanup' if args.cleanup else 'seed'}")
        print(f"[DRY-RUN] Numero de provas: {len(NRO_PROVAS)}")
        print(f"[DRY-RUN] Tag: {SEED_TAG}")
        return

    async with async_session() as db:
        if args.cleanup:
            print(f"Cleanup do {SEED_TAG}...")
            counts = await cleanup(db)
            await db.commit()
            print(f"  Provas marcadas como CANCELADA: {counts['provas_marcadas']}")
            print(f"  Usuarios desativados: {counts['users_desativados']}")
        else:
            print(f"Seed do {SEED_TAG}...")
            counts = await seed(db)
            await db.commit()
            print(f"  Usuarios criados/lidos: {counts['users']}")
            print(f"  Provas criadas/lidas: {counts['provas']}")
            print(f"  Movimentacoes inseridas: {counts['movs']}")
        print("OK")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed deterministico para validacao manual de Relatorios (Wave 5)"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove provas do seed (marca como CANCELADA) + desativa usuarios.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o que faria sem tocar o banco.",
    )
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
