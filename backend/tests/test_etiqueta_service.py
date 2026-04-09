"""Testes do EtiquetaService (ADR-035)."""
from datetime import datetime, timezone

from app.services.etiqueta_service import TEMPLATE_PADRAO, gerar_pdf
from app.services.qrcode_service import gerar_imagem_qr

QR_IMG = gerar_imagem_qr("3SD|REQ-TEST|aaaaaaaaaaaaaaaa", size_px=200)


def test_pdf_tem_magic_header_padrao():
    pdf = gerar_pdf(
        nome_prova="Rotulo Verao",
        nro_requerimento="REQ-2026-0001",
        vendedor_nome="Joao Silva",
        qr_image_bytes=QR_IMG,
    )
    assert pdf.startswith(b"%PDF-")
    assert b"%%EOF" in pdf[-50:]


def test_pdf_a4_e_maior_que_vazio():
    pdf = gerar_pdf(
        nome_prova="Teste",
        nro_requerimento="REQ-1",
        vendedor_nome="Vendedor",
        qr_image_bytes=QR_IMG,
        template={**TEMPLATE_PADRAO, "formato": "A4"},
    )
    assert len(pdf) > 1000


def test_pdf_80mm_thermal_tem_tamanho_diferente_do_a4():
    a4 = gerar_pdf(
        nome_prova="Teste",
        nro_requerimento="REQ-1",
        vendedor_nome="Vendedor",
        qr_image_bytes=QR_IMG,
        template={**TEMPLATE_PADRAO, "formato": "A4"},
    )
    thermal = gerar_pdf(
        nome_prova="Teste",
        nro_requerimento="REQ-1",
        vendedor_nome="Vendedor",
        qr_image_bytes=QR_IMG,
        template={**TEMPLATE_PADRAO, "formato": "80mm_thermal"},
    )
    # Ambos validos, tamanhos distintos (layout e dimensoes da pagina diferem).
    assert a4.startswith(b"%PDF-")
    assert thermal.startswith(b"%PDF-")
    assert a4 != thermal


def test_pdf_sem_logo_gera_menor():
    com_logo = gerar_pdf(
        nome_prova="Teste",
        nro_requerimento="REQ-1",
        vendedor_nome="Vendedor",
        qr_image_bytes=QR_IMG,
        template={**TEMPLATE_PADRAO, "logo_enabled": True},
    )
    sem_logo = gerar_pdf(
        nome_prova="Teste",
        nro_requerimento="REQ-1",
        vendedor_nome="Vendedor",
        qr_image_bytes=QR_IMG,
        template={**TEMPLATE_PADRAO, "logo_enabled": False},
    )
    assert len(com_logo) >= len(sem_logo)


def test_pdf_com_data_criacao():
    """mostrar_data_criacao=True nao deve quebrar a geracao."""
    pdf = gerar_pdf(
        nome_prova="Teste",
        nro_requerimento="REQ-1",
        vendedor_nome="Vendedor",
        qr_image_bytes=QR_IMG,
        template={**TEMPLATE_PADRAO, "mostrar_data_criacao": True},
        created_at=datetime(2026, 4, 9, 14, 30, tzinfo=timezone.utc),
    )
    assert pdf.startswith(b"%PDF-")


def test_pdf_template_none_usa_padrao():
    pdf = gerar_pdf(
        nome_prova="Teste",
        nro_requerimento="REQ-1",
        vendedor_nome="Vendedor",
        qr_image_bytes=QR_IMG,
        template=None,
    )
    assert pdf.startswith(b"%PDF-")


def test_pdf_nome_longo_nao_quebra():
    nome_gigante = "A" * 200  # limite do schema
    pdf = gerar_pdf(
        nome_prova=nome_gigante,
        nro_requerimento="REQ-1",
        vendedor_nome="Vendedor",
        qr_image_bytes=QR_IMG,
    )
    assert pdf.startswith(b"%PDF-")


# ─── C1 — Unicode hardening (post-audit) ──────────────────────────────────


def test_pdf_acentos_latin1_ok():
    pdf = gerar_pdf(
        nome_prova="Edição Verão 2026",
        nro_requerimento="REQ-1",
        vendedor_nome="João Gonçalves",
        qr_image_bytes=QR_IMG,
    )
    assert pdf.startswith(b"%PDF-")


def test_pdf_euro_simbolo_ok():
    """Euro sign (U+20AC) fora de Latin-1 — quebrava com Helvetica."""
    pdf = gerar_pdf(
        nome_prova="Preço €1.234,56",
        nro_requerimento="REQ-1",
        vendedor_nome="Vendedor",
        qr_image_bytes=QR_IMG,
    )
    assert pdf.startswith(b"%PDF-")


def test_pdf_smart_quotes_ok():
    """U+2018/U+2019 (smart quotes) — Word/Google Docs geram auto."""
    pdf = gerar_pdf(
        nome_prova="Rotulo 'premium' edicao",
        nro_requerimento="REQ-1",
        vendedor_nome="Vendedor",
        qr_image_bytes=QR_IMG,
    )
    assert pdf.startswith(b"%PDF-")


def test_pdf_em_en_dash_ok():
    """U+2013 (en-dash) e U+2014 (em-dash) — auto-gerados por editores."""
    pdf = gerar_pdf(
        nome_prova="Coleção – Outono — 2026",
        nro_requerimento="REQ-1",
        vendedor_nome="Vendedor",
        qr_image_bytes=QR_IMG,
    )
    assert pdf.startswith(b"%PDF-")


def test_pdf_chars_fora_do_font_nao_crashea():
    """CJK e emoji ficam como glyph faltando, mas nao quebram geracao.

    fpdf2 loga warning mas devolve PDF valido.
    """
    pdf = gerar_pdf(
        nome_prova="Multi 中文 🎨 test",
        nro_requerimento="REQ-1",
        vendedor_nome="Vendedor",
        qr_image_bytes=QR_IMG,
    )
    assert pdf.startswith(b"%PDF-")
