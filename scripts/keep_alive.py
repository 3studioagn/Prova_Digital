"""
Keep-alive para o Supabase free tier.

O Supabase pausa projetos apos 7 dias sem requisicoes.
Este script faz uma requisicao leve ao /health/db, forcando um SELECT 1
no PostgreSQL e mantendo o projeto ativo.

Agendado via GitHub Actions cron a cada 6 dias (margem de seguranca).

Uso: python scripts/keep_alive.py [URL_BASE]
"""

import sys
import time
from datetime import datetime, timezone

import httpx

DEFAULT_URL = "http://localhost:8000"


def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    url = f"{base_url}/health/db"

    now = datetime.now(timezone.utc).isoformat()
    print(f"[{now}] Keep-alive: requisitando {url}")

    start = time.monotonic()
    try:
        response = httpx.get(url, timeout=30)
        elapsed_ms = (time.monotonic() - start) * 1000

        print(f"  Status: {response.status_code}")
        print(f"  Resposta: {response.json()}")
        print(f"  Tempo: {elapsed_ms:.0f}ms")

        if response.status_code != 200 or response.json().get("status") != "ok":
            print("  ALERTA: resposta inesperada!")
            sys.exit(1)

        print("  OK - projeto Supabase mantido ativo.")
    except Exception as e:
        elapsed_ms = (time.monotonic() - start) * 1000
        print(f"  ERRO: {e}")
        print(f"  Tempo: {elapsed_ms:.0f}ms")
        sys.exit(1)


if __name__ == "__main__":
    main()
