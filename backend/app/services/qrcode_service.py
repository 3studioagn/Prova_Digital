"""Geracao de hash e imagem do QR Code das provas digitais.

ADR-033: hash = HMAC-SHA256(secret, payload) onde payload combina o prova_id
com o numero de requerimento. Saida hexadecimal (64 chars) — coincide com o
tamanho do campo `provas_digitais.qr_code_hash VARCHAR(64) UNIQUE`.

Caracteristicas:
  - Deterministico: mesmo (prova_id, nro_req) produz sempre o mesmo hash.
  - Nao-reversivel: extrair o prova_id a partir do hash exige a secret.
  - Validavel no scanner da Wave 3 sem ida ao banco: basta recomputar e
    comparar com o hash armazenado.

ADR-034: imagem PNG gerada via `qrcode[pil]` — lib padrao do ecossistema
Python. Pillow vem de sub-dependencia.

Formato do payload do QR escaneavel (decisao interna):
    3SD|{nro_requerimento}|{hash[:16]}

Curto o suficiente para caber num QR Code pequeno, prefixo `3SD` facilita
distinguir de outros QR Codes que o scanner possa encontrar. O hash truncado
(16 chars) e validado comparando com o hash completo armazenado — 64 bits
de entropia sao mais que suficientes para evitar colisao no volume esperado.
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


def gerar_payload_qr(nro_requerimento: str, hash_hex: str) -> str:
    """Payload que vira o conteudo escaneavel do QR Code."""
    if len(hash_hex) < HASH_TRUNCADO_LEN:
        raise ValueError(
            f"Hash muito curto: esperado >= {HASH_TRUNCADO_LEN} chars, recebi {len(hash_hex)}"
        )
    return QR_PAYLOAD_SEPARATOR.join(
        [QR_PAYLOAD_PREFIX, nro_requerimento, hash_hex[:HASH_TRUNCADO_LEN]]
    )


def validar_payload_qr(payload: str, hash_hex_completo: str) -> bool:
    """Verifica se um payload escaneado corresponde ao hash armazenado.

    Usado pela Wave 3 no endpoint de scan. Rejeita prefixo errado, formato
    invalido e hash que nao bate com o esperado.
    """
    parts = payload.split(QR_PAYLOAD_SEPARATOR)
    if len(parts) != 3:
        return False
    prefix, _nro_req, hash_truncado = parts
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
