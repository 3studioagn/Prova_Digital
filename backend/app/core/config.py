from pydantic_settings import BaseSettings


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

    # --- Aplicacao ---
    app_env: str = "development"
    app_debug: bool = True
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
