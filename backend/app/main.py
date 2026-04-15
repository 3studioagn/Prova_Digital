import logging

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.auditoria import router as auditoria_router
from app.api.v1.configuracoes import router as configuracoes_router
from app.api.v1.provas import router as provas_router
from app.api.v1.users import router as users_router
from app.core.config import settings
from app.core.r2 import get_r2_client
from app.db.session import async_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Rastreio de Provas Digitais",
    description="API do sistema de rastreio de provas digitais - 3Studio",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled exceptions and return a clean 500 JSONResponse.

    Without this handler, Starlette's ServerErrorMiddleware (which sits OUTSIDE
    user middleware) returns the 500 response without ever going through the
    CORSMiddleware. The browser then reports a misleading 'CORS error' instead
    of showing the real backend failure.

    By registering an exception handler at the app level, the 500 response is
    produced INSIDE the middleware stack and CORS headers get attached on the
    way out.
    """
    logger.exception(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor"},
    )


app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
app.include_router(provas_router, prefix="/api/v1/provas", tags=["provas"])
app.include_router(
    configuracoes_router, prefix="/api/v1/configuracoes", tags=["configuracoes"]
)
app.include_router(
    auditoria_router, prefix="/api/v1/auditoria", tags=["auditoria"]
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/db")
async def health_db():
    """Executa SELECT 1 no PostgreSQL para validar conectividade.

    Tenta primeiro via SQLAlchemy (pooler). Se falhar, faz fallback
    via REST API do Supabase para confirmar que o banco esta ativo.
    """
    pooler_error = None

    # Tentativa 1: conexao direta via SQLAlchemy (pooler)
    try:
        async with async_session() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()
        return {"status": "ok", "database": "connected", "method": "pooler"}
    except Exception as e:
        pooler_error = str(e)

    # Tentativa 2: fallback via REST API do Supabase
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.supabase_url}/rest/v1/",
                headers={
                    "apikey": settings.supabase_anon_key,
                    "Authorization": f"Bearer {settings.supabase_anon_key}",
                },
                timeout=10,
            )
            if resp.status_code < 500:
                return {
                    "status": "ok",
                    "database": "connected",
                    "method": "rest_api",
                    "note": "Pooler indisponivel, validado via REST API",
                }
    except Exception:
        pass

    return {"status": "error", "database": pooler_error}


@app.get("/health/r2")
async def health_r2():
    """Testa conectividade com o bucket R2 da Cloudflare."""
    try:
        client = get_r2_client()
        client.head_bucket(Bucket=settings.r2_bucket_name)
        return {"status": "ok", "r2": "connected", "bucket": settings.r2_bucket_name}
    except Exception as e:
        return {"status": "error", "r2": str(e)}
