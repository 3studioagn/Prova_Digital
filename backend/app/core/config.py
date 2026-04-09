from pathlib import Path

from pydantic_settings import BaseSettings

# Resolve o caminho absoluto do .env baseado na localizacao deste arquivo:
#   backend/app/core/config.py  →  backend/.env
# Isso garante que o .env e encontrado mesmo quando o backend e executado
# a partir de um cwd diferente de `backend/` (por exemplo, uvicorn rodando
# do repo root com `--app-dir backend`). Ver Sessao 10b no CHANGELOG.
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    # --- Supabase ---
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_jwt_secret: str

    # --- PostgreSQL ---
    database_url: str

    # --- Cloudflare R2 ---
    r2_account_id: str
    r2_access_key_id: str
    r2_secret_access_key: str
    r2_bucket_name: str = "rastreio-provas-artes"
    r2_endpoint_url: str

    # --- QR Code (Wave 2, ADR-033) ---
    # HMAC-SHA256 secret usado para derivar o `qr_code_hash` de cada prova digital.
    # Nunca commitar. Gerar via `python -c "import secrets; print(secrets.token_hex(32))"`.
    # Rotacao invalida TODOS os QR Codes existentes — nao rotacionar sem plano de migracao.
    qr_code_hmac_secret: str

    # --- Aplicacao ---
    app_env: str = "development"
    app_debug: bool = True
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    model_config = {
        "env_file": str(_ENV_FILE),
        "env_file_encoding": "utf-8",
    }


settings = Settings()
