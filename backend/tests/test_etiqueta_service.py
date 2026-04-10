"""Testes do EtiquetaService (ADR-035)."""
from datetime import datetime, timezone

from app.services.etiqueta_service import (
    _ASSETS_DIR,
    _FONTS_DIR,
    _LOGO_3STUDIO,
    _LOGO_STUDIO_ART,
    TEMPLATE_PADRAO,
    _check_assets,
    gerar_pdf,
)
from app.services.qrcode_service import gerar_imagem_qr

QR_IMG = gerar_imagem_qr("3SD|REQ-TEST|aaaaaaaaaaaaaaaa", size_px=200)


# ─── Deploy smoke (C1 — hardening pos-auditoria) ──────────────────────────


def test_etiqueta_assets_existem_no_repo():
    """Falha rapido se os SVGs dos logos nao estiverem versionados.

    C1 da auditoria Wave 2: os assets estavam untracked no git, o que
    teria quebrado o deploy em producao (Railway). Este teste existe para
    garantir que alguem que apague ou esqueca de commitar os SVGs veja a
    falha no CI, nao em producao.
    """
    assert _ASSETS_DIR.exists(), f"Diretorio de assets nao existe: {_ASSETS_DIR}"
    assert _LOGO_3STUDIO.exists(), (
        f"logo_3studio.svg ausente em {_LOGO_3STUDIO}. Versione o arquivo."
    )
    assert _LOGO_STUDIO_ART.exists(), (
        f"logo_studio_e_arte.svg ausente em {_LOGO_STUDIO_ART}. Versione o arquivo."
    )
    # Sanity check de formato: SVGs validos comecam com header XML ou tag svg.
    for path in (_LOGO_3STUDIO, _LOGO_STUDIO_ART):
        head = path.read_bytes()[:200].lower()
        assert b"<svg" in head or b"<?xml" in head, (
            f"{path.name} nao parece ser um SVG valido"
        )


def test_etiqueta_fonts_existem_no_repo():
    """Mesmo espirito de test_etiqueta_assets_existem_no_repo, mas para os TTFs.

    Se os arquivos DejaVu sumirem, _register_fonts levanta RuntimeError
    e nenhuma prova pode ser criada.
    """
    assert _FONTS_DIR.exists(), f"Diretorio de fontes nao existe: {_FONTS_DIR}"
    regular = _FONTS_DIR / "DejaVuSans.ttf"
    bold = _FONTS_DIR / "DejaVuSans-Bold.ttf"
    assert regular.exists(), f"DejaVuSans.ttf ausente em {regular}"
    assert bold.exists(), f"DejaVuSans-Bold.ttf ausente em {bold}"


def test_check_assets_nao_levanta_com_arquivos_presentes():
    """_check_assets e chamada em cada gerar_pdf — garante que nao quebra."""
    _check_assets()  # nao deve levantar



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


def test_pdf_formato_legacy_e_aceito_mas_ignorado(monkeypatch):
    """Sessao 14: o campo `formato` do template foi obsoleto.

    A etiqueta tem dimensao fixa 90x57mm conforme design Figma. Os valores
    legacy "A4" e "80mm_thermal" continuam sendo aceitos pelo schema (para
    compat com configuracao existente) mas nao afetam o render — geram
    PDFs identicos byte-a-byte (com os mesmos inputs).

    Flake fix (auditoria externa Wave 2): antes esse teste era flaky porque
    comparava os bytes de 2 PDFs gerados em sucessao — o fpdf2 embute o
    timestamp de `CreationDate` no metadata do PDF com resolucao de segundo,
    entao 2 chamadas que cruzam a fronteira de segundo geravam PDFs com
    metadata diferente e o `assert a4 == thermal` falhava. O fix congela o
    `datetime.now()` dentro do modulo `fpdf.fpdf` e `fpdf.output` durante
    a execucao do teste, via monkeypatch em classe auxiliar. Mesma saida
    binaria garantida.
    """
    import fpdf.fpdf
    import fpdf.output

    # Cria um datetime falso cujo .now() sempre retorna o mesmo valor.
    fixed_now = datetime(2026, 4, 10, 12, 0, 0, tzinfo=timezone.utc)

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz is None else fixed_now.astimezone(tz)

    monkeypatch.setattr(fpdf.fpdf, "datetime", _FrozenDatetime)
    monkeypatch.setattr(fpdf.output, "datetime", _FrozenDatetime)

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
    assert a4.startswith(b"%PDF-")
    assert thermal.startswith(b"%PDF-")
    # Ambos geram o MESMO output — formato e ignorado pelo render.
    assert a4 == thermal


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
