"""Cliente Cloudflare R2 (S3-compatible).

Correcoes de auditoria:
  C3: boto3 e sincrono — todas as operacoes DEVEM ser chamadas via
      run_in_executor para nao bloquear o event loop do FastAPI.
  M5: Cliente e singleton (reutiliza conexoes em vez de recriar a cada chamada).

Uso nos endpoints:
    from app.core.r2 import r2_upload, r2_download, r2_delete

    await r2_upload(key="artes/foto.png", body=file_bytes)
    data = await r2_download(key="artes/foto.png")
    await r2_delete(key="artes/foto.png")
"""
import asyncio
import functools
from typing import Optional

import boto3

from app.core.config import settings

# Singleton: criado uma vez, reutilizado em todas as chamadas.
_client = None


def _get_client():
    """Retorna o cliente boto3 singleton (thread-safe por design do boto3)."""
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint_url,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name="auto",
        )
    return _client


def get_r2_client():
    """Acesso direto ao client (para health checks e scripts sync).

    NAO usar em endpoints async — prefira r2_upload/r2_download/r2_delete.
    """
    return _get_client()


async def _run_sync(func, *args, **kwargs):
    """Executa funcao sincrona no thread pool sem bloquear o event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, functools.partial(func, *args, **kwargs)
    )


async def r2_upload(
    key: str,
    body: bytes,
    content_type: Optional[str] = None,
    bucket: Optional[str] = None,
) -> dict:
    """Upload async para R2. Retorna resposta do S3."""
    client = _get_client()
    kwargs = {
        "Bucket": bucket or settings.r2_bucket_name,
        "Key": key,
        "Body": body,
    }
    if content_type:
        kwargs["ContentType"] = content_type
    return await _run_sync(client.put_object, **kwargs)


async def r2_download(key: str, bucket: Optional[str] = None) -> bytes:
    """Download async do R2. Retorna bytes do objeto."""
    client = _get_client()

    def _download():
        response = client.get_object(
            Bucket=bucket or settings.r2_bucket_name,
            Key=key,
        )
        return response["Body"].read()

    return await _run_sync(_download)


async def r2_delete(key: str, bucket: Optional[str] = None) -> dict:
    """Delete async no R2."""
    client = _get_client()
    return await _run_sync(
        client.delete_object,
        Bucket=bucket or settings.r2_bucket_name,
        Key=key,
    )
