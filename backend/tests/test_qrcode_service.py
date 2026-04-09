"""Testes do QRCodeService (ADR-033, ADR-034)."""
import uuid

import pytest

from app.services.qrcode_service import (
    HASH_TRUNCADO_LEN,
    QR_PAYLOAD_PREFIX,
    gerar_hash,
    gerar_imagem_qr,
    gerar_payload_qr,
    validar_payload_qr,
)

# ─── gerar_hash ──────────────────────────────────────────────────────────


def test_hash_tem_64_chars_hex():
    h = gerar_hash(uuid.uuid4(), "REQ-2026-0001")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_hash_deterministico_mesmo_input():
    prova_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    h1 = gerar_hash(prova_id, "REQ-2026-0001")
    h2 = gerar_hash(prova_id, "REQ-2026-0001")
    assert h1 == h2


def test_hash_difere_para_prova_id_diferente():
    h1 = gerar_hash(uuid.UUID("00000000-0000-0000-0000-000000000001"), "REQ")
    h2 = gerar_hash(uuid.UUID("00000000-0000-0000-0000-000000000002"), "REQ")
    assert h1 != h2


def test_hash_difere_para_nro_req_diferente():
    pid = uuid.uuid4()
    h1 = gerar_hash(pid, "REQ-A")
    h2 = gerar_hash(pid, "REQ-B")
    assert h1 != h2


def test_hash_muda_quando_secret_muda(monkeypatch):
    pid = uuid.uuid4()
    nro = "REQ-X"
    h1 = gerar_hash(pid, nro)

    from app.core.config import settings

    monkeypatch.setattr(settings, "qr_code_hmac_secret", "outra-secret-diferente")
    h2 = gerar_hash(pid, nro)
    assert h1 != h2


# ─── gerar_payload_qr ───────────────────────────────────────────────────


def test_payload_formato_esperado():
    h = "a" * 64
    p = gerar_payload_qr("REQ-2026-0001", h)
    assert p.startswith(QR_PAYLOAD_PREFIX + "|")
    assert "REQ-2026-0001" in p
    parts = p.split("|")
    assert len(parts) == 3
    assert parts[2] == "a" * HASH_TRUNCADO_LEN


def test_payload_rejeita_hash_curto():
    with pytest.raises(ValueError, match="muito curto"):
        gerar_payload_qr("REQ", "abc")


# ─── validar_payload_qr ─────────────────────────────────────────────────


def test_validar_payload_aceita_hash_correto():
    h = "f" * 64
    p = gerar_payload_qr("REQ", h)
    assert validar_payload_qr(p, h) is True


def test_validar_payload_rejeita_prefixo_errado():
    h = "f" * 64
    assert validar_payload_qr("XYZ|REQ|ffffffffffffffff", h) is False


def test_validar_payload_rejeita_hash_errado():
    h1 = "f" * 64
    h2 = "e" * 64
    p = gerar_payload_qr("REQ", h1)
    assert validar_payload_qr(p, h2) is False


def test_validar_payload_rejeita_formato_invalido():
    assert validar_payload_qr("nada", "f" * 64) is False
    assert validar_payload_qr("3SD|REQ", "f" * 64) is False  # faltam partes


# ─── gerar_imagem_qr ────────────────────────────────────────────────────


def test_imagem_qr_tem_magic_bytes_png():
    img = gerar_imagem_qr("3SD|REQ|aaaaaaaaaaaaaaaa", size_px=100)
    # PNG magic: 89 50 4E 47 0D 0A 1A 0A
    assert img[:8] == b"\x89PNG\r\n\x1a\n"


def test_imagem_qr_nao_vazia():
    img = gerar_imagem_qr("3SD|REQ|aaaaaaaaaaaaaaaa")
    assert len(img) > 100  # PNG minimo razoavel


def test_imagem_qr_tamanhos_diferentes():
    img_small = gerar_imagem_qr("payload", size_px=50)
    img_large = gerar_imagem_qr("payload", size_px=300)
    # Imagens maiores geram PNG maiores (mais pixels).
    assert len(img_large) > len(img_small)
