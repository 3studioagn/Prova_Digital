"""
Esse script de conectividade com o Cloudflare R2.
Valida o ciclo completo: upload -> list -> download -> delete.
Este script NAO deve subir para producao — serve apenas como validacao.
Uso: python scripts/smoke_r2.py
"""

import os
import sys
import tempfile

import boto3
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

BUCKET = os.getenv("R2_BUCKET_NAME", "rastreio-provas-artes")
TEST_KEY = "_smoke_test/dummy.txt"
TEST_CONTENT = b"smoke test - pode deletar"


def get_client():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("R2_ENDPOINT_URL"),
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
    )


def main():
    client = get_client()
    print(f"[1/4] Upload de arquivo dummy para {BUCKET}/{TEST_KEY}...")
    client.put_object(Bucket=BUCKET, Key=TEST_KEY, Body=TEST_CONTENT)
    print("       OK")

    print(f"[2/4] Listando objetos com prefixo '_smoke_test/'...")
    response = client.list_objects_v2(Bucket=BUCKET, Prefix="_smoke_test/")
    found = any(obj["Key"] == TEST_KEY for obj in response.get("Contents", []))
    if not found:
        print("       FALHA: arquivo nao encontrado na listagem")
        sys.exit(1)
    print("       OK")

    print(f"[3/4] Download do arquivo...")
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        client.download_fileobj(BUCKET, TEST_KEY, tmp)
        tmp.seek(0)
        downloaded = tmp.read()
    if downloaded != TEST_CONTENT:
        print("       FALHA: conteudo diferente do esperado")
        sys.exit(1)
    print("       OK")

    print(f"[4/4] Deletando arquivo de teste...")
    client.delete_object(Bucket=BUCKET, Key=TEST_KEY)
    print("       OK")

    print("\nSmoke test R2 concluido com sucesso!")


if __name__ == "__main__":
    main()
