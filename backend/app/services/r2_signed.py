"""Operacoes R2 que precisam de Signed URL ou metadata (ADR-031).

Complementa `app/core/r2.py` com:
  - `generate_presigned_upload_url`: backend assina uma URL pre-assinada que
    o frontend usa para fazer PUT direto no R2. Evita que o binario passe
    pelo Railway (economiza banda e memoria do container).
  - `head_object`: pega metadata (ContentLength, ContentType, ETag) sem
    baixar o conteudo. Usado para validar o upload antes de inserir no DB.
  - `get_object_head_bytes`: Range GET dos primeiros N bytes do objeto.
    Usado pela validacao de magic bytes (ADR-032).

Todas as operacoes sao async via run_in_executor do asyncio — segue o
mesmo padrao de `app/core/r2.py` (ADR-008). Nao substitui nem importa do
modulo legado: coexistem.
"""
import asyncio
import functools
from typing import Any

from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.r2 import get_r2_client


async def _run_sync(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))


async def generate_presigned_upload_url(
    key: str,
    content_type: str,
    expires_in: int = 900,
    bucket: str | None = None,
) -> str:
    """Gera URL pre-assinada que o browser pode usar no PUT.

    O client DEVE usar exatamente o mesmo `Content-Type` que foi assinado —
    caso contrario, o R2 rejeita o PUT com 403 SignatureDoesNotMatch.

    Args:
        key: Caminho do objeto no bucket (e.g. "provas/2026/04/abc.../arte.jpg").
        content_type: MIME type que o client vai enviar no PUT (image/jpeg ou image/png).
        expires_in: TTL da URL em segundos. Default 900 (15min).
        bucket: Bucket alvo. Default usa settings.r2_bucket_name.

    Returns:
        URL completa com os parametros de assinatura.
    """
    client = get_r2_client()
    return await _run_sync(
        client.generate_presigned_url,
        "put_object",
        Params={
            "Bucket": bucket or settings.r2_bucket_name,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=expires_in,
    )


async def generate_presigned_get_url(
    key: str,
    expires_in: int = 900,
    bucket: str | None = None,
) -> str:
    """Gera URL pre-assinada para download/visualizacao do objeto.

    Sera usada pelo Componente 08 (preview da arte na tela de detalhe).
    """
    client = get_r2_client()
    return await _run_sync(
        client.generate_presigned_url,
        "get_object",
        Params={
            "Bucket": bucket or settings.r2_bucket_name,
            "Key": key,
        },
        ExpiresIn=expires_in,
    )


async def head_object(key: str, bucket: str | None = None) -> dict[str, Any]:
    """Retorna metadata do objeto (ContentLength, ContentType, ETag, LastModified).

    Raises:
        botocore.exceptions.ClientError com Code='404' se o objeto nao existe.
    """
    client = get_r2_client()
    return await _run_sync(
        client.head_object,
        Bucket=bucket or settings.r2_bucket_name,
        Key=key,
    )


async def get_object_head_bytes(
    key: str, n: int = 16, bucket: str | None = None
) -> bytes:
    """Le os primeiros `n` bytes do objeto via Range GET.

    Usado para validacao de magic bytes (ADR-032) sem baixar o arquivo todo.
    """
    client = get_r2_client()

    def _range_get() -> bytes:
        response = client.get_object(
            Bucket=bucket or settings.r2_bucket_name,
            Key=key,
            Range=f"bytes=0-{n - 1}",
        )
        return response["Body"].read()

    return await _run_sync(_range_get)


def extract_error_code(exc: Exception) -> str:
    """Helper para classificar ClientError do botocore em handlers de API."""
    if isinstance(exc, ClientError):
        return exc.response.get("Error", {}).get("Code", "")
    return ""
