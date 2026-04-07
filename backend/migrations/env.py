"""
Alembic environment configuration.

IMPORTANTE: Este arquivo usa a DATABASE_URL do .env para conectar ao PostgreSQL.
As migrations Alembic controlam APENAS tabelas de dominio.
Tabelas auth.* sao gerenciadas pelo Supabase — nunca tocar via Alembic.
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

load_dotenv()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Sobrescreve a URL do alembic.ini com a do .env
# Usa a versao sincrona (psycopg2) para migrations — Alembic nao suporta asyncpg nativamente
database_url = os.getenv("DATABASE_URL", "")
# Converte asyncpg -> psycopg2 para migrations (Alembic roda sincrono)
sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
config.set_main_option("sqlalchemy.url", sync_url)

target_metadata = None


def run_migrations_offline() -> None:
    """Gera SQL sem conectar ao banco — util para revisao antes de aplicar."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Conecta ao banco e aplica migrations."""
    connectable = context.config.attributes.get("connection", None)

    if connectable is None:
        from sqlalchemy import create_engine

        connectable = create_engine(
            config.get_main_option("sqlalchemy.url"),
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
