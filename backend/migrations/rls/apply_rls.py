"""
Script idempotente para aplicar todas as politicas RLS versionadas.

Uso: python backend/migrations/rls/apply_rls.py

Executa todos os arquivos .sql em ordem numerica no banco definido
pela DATABASE_URL do .env. Cada script e idempotente (usa DROP IF EXISTS
antes de CREATE), entao pode ser reaplicado com seguranca apos
recriacao de tabelas via Alembic.

IMPORTANTE: Este script usa a connection string SINCRONA (psycopg2),
nao a asyncpg usada pelo FastAPI.
"""

import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


def main():
    database_url = os.getenv("DATABASE_URL", "")
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    rls_dir = Path(__file__).resolve().parent
    sql_files = sorted(rls_dir.glob("*.sql"))

    if not sql_files:
        print("Nenhum arquivo .sql encontrado em", rls_dir)
        sys.exit(0)

    conn = psycopg2.connect(sync_url)
    conn.autocommit = True

    for sql_file in sql_files:
        print(f"Aplicando {sql_file.name}...")
        sql = sql_file.read_text(encoding="utf-8")
        with conn.cursor() as cur:
            cur.execute(sql)
        print(f"  OK")

    conn.close()
    print(f"\n{len(sql_files)} script(s) RLS aplicado(s) com sucesso.")


if __name__ == "__main__":
    main()
