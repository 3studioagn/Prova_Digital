"""Geracao de hash e imagem do QR Code das provas digitais.

ADR-033: hash = HMAC-SHA256(secret, payload) onde payload combina o prova_id
com o numero de requerimento. Saida hexadecimal (64 chars) — coincide com o
tamanho do campo `provas_digitais.qr_code_hash VARCHAR(64) UNIQUE`.

Caracteristicas:
  - Deterministico: mesmo (prova_id, nro_req) produz sempre o mesmo hash.
  - Nao-reversivel: extrair o prova_id a partir do hash exige a secret.
  - Validavel no scanner sem ida ao banco: basta recomputar e comparar
    com o hash armazenado.

ADR-034: imagem PNG gerada via `qrcode[pil]` — lib padrao do ecossistema
Python. Pillow vem de sub-dependencia.

Formato do payload do QR escaneavel:
  Wave 2 v4.0 (Componente 06):
    3SD|{codigo_publico}|{hash[:16]}    # novo formato
  Wave 0/v3.0 (legado, ainda suportado para validacao):
    3SD|{nro_requerimento}|{hash[:16]}

A v4.0 embute o `codigo_publico` (DAT v3.0 §8.1 — idempotencia entre
camera e digitacao manual). Provas legadas v3.0 que ainda tem QRs com
`nro_requerimento` continuam validas via `validar_payload_qr` flexivel
ate a Wave 7 / Componente 21 (regerar etiquetas no backfill).
"""
import hashlib
import hmac
import io
from uuid import UUID

import qrcode

from app.core.config import settings

QR_PAYLOAD_PREFIX = "3SD"
QR_PAYLOAD_SEPARATOR = "|"
HASH_TRUNCADO_LEN = 16


def gerar_hash(prova_id: UUID, nro_requerimento: str) -> str:
    """HMAC-SHA256 hexadecimal (64 chars) — unico por prova."""
    message = f"{prova_id}:{nro_requerimento}".encode("utf-8")
    key = settings.qr_code_hmac_secret.encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def gerar_payload_qr(identificador: str, hash_hex: str) -> str:
    """Payload que vira o conteudo escaneavel do QR Code.

    Wave 2 v4.0 (Componente 06): `identificador` deve ser o
    `codigo_publico` (`PRV-AAAA-MM-NNNNNN`) para garantir idempotencia
    entre camera e digitacao manual (DAT v3.0 §8.1). O parametro foi
    renomeado de `nro_requerimento` para `identificador` para refletir
    essa mudanca semantica — o caller passa o que for adequado.
    """
    if len(hash_hex) < HASH_TRUNCADO_LEN:
        raise ValueError(
            f"Hash muito curto: esperado >= {HASH_TRUNCADO_LEN} chars, recebi {len(hash_hex)}"
        )
    return QR_PAYLOAD_SEPARATOR.join(
        [QR_PAYLOAD_PREFIX, identificador, hash_hex[:HASH_TRUNCADO_LEN]]
    )


def validar_payload_qr(payload: str, hash_hex_completo: str) -> bool:
    """Verifica se um payload escaneado corresponde ao hash armazenado.

    Aceita tanto formato v4.0 (`codigo_publico` no segundo campo) quanto
    formato legacy v3.0 (`nro_requerimento` no segundo campo) — a
    validacao usa apenas o hash truncado, nao o segundo campo. Wave 3
    v4.0 (Componente 19) faz o lookup pelo segundo campo decidindo se e
    `codigo_publico` (formato `PRV-...`) ou `nro_requerimento` (livre).

    Rejeita prefixo errado, formato invalido e hash que nao bate.
    """
    parts = payload.split(QR_PAYLOAD_SEPARATOR)
    if len(parts) != 3:
        return False
    prefix, _identificador, hash_truncado = parts
    if prefix != QR_PAYLOAD_PREFIX:
        return False
    if len(hash_truncado) != HASH_TRUNCADO_LEN:
        return False
    # Comparacao constant-time para evitar timing attacks.
    return hmac.compare_digest(hash_truncado, hash_hex_completo[:HASH_TRUNCADO_LEN])


def gerar_imagem_qr(payload: str, size_px: int = 200) -> bytes:
    """Renderiza o payload como PNG (bytes).

    Parametros do qrcode otimizados para leitura em tela de celular:
      - version=None -> auto, cresce conforme necessario
      - error_correction=ERROR_CORRECT_M -> 15% de tolerancia a dano
      - box_size calculado para aproximar `size_px`
      - border=2 -> quiet zone padrao ISO 18004
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    # Redimensiona para `size_px` mantendo o aspect 1:1 e nearest neighbor
    # (preservar bordas nitidas do QR — interpolacao suavizaria as celulas).
    img = img.resize((size_px, size_px), resample=0)  # 0 = NEAREST em Pillow

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
