"""Geracao do PDF da etiqueta imprimivel (RF-003, RN-011, ADR-035).

Usa `fpdf2` — zero dependencias nativas, suficiente para o layout "padrao".
O template vem de `configuracoes_sistema.template_etiqueta` (ADR-036), que
apos a migration 009 e um objeto JSONB:
  {
    "nome": "padrao",
    "formato": "A4" | "80mm_thermal",
    "logo_enabled": bool,
    "mostrar_data_criacao": bool
  }

Dois formatos suportados:
  - A4: folha inteira, layout centralizado, util para impressao em jato/laser
    quando ainda nao ha impressora termica.
  - 80mm_thermal: etiqueta compacta 80x100mm, para impressora termica que
    aceita o formato bobina.

Ambos renderizam: nome da prova, numero do requerimento, vendedor responsavel
e imagem do QR Code (gerada por `qrcode_service.gerar_imagem_qr`).

FONTE UNICODE (post-Wave 2 hardening):
  `fpdf2` nao consegue renderizar caracteres fora de Latin-1 com a fonte
  builtin Helvetica — chars como €, smart quotes, em/en dash, CJK, emoji
  lancam FPDFUnicodeEncodingException e quebram a criacao da prova.

  Fix: usar DejaVu Sans TTF em `app/services/fonts/`. DejaVu cobre todo o
  Latin Extended + Greek + Cyrillic + muitos simbolos matematicos. Chars
  fora do range coberto (CJK, emoji) renderizam como glyph faltando com
  warning — sem crash.

  Licenca: Bitstream Vera Font License (permite uso comercial + redistribuicao,
  ver `backend/app/services/fonts/LICENSE`).
"""
import io
import logging
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

logger = logging.getLogger(__name__)


TEMPLATE_PADRAO = {
    "nome": "padrao",
    "formato": "A4",
    "logo_enabled": True,
    "mostrar_data_criacao": False,
}


# ─── Fonte Unicode ────────────────────────────────────────────────────────
# Resolve o caminho absoluto dos TTF independente do cwd.
_FONTS_DIR = Path(__file__).resolve().parent / "fonts"
_FONT_REGULAR = _FONTS_DIR / "DejaVuSans.ttf"
_FONT_BOLD = _FONTS_DIR / "DejaVuSans-Bold.ttf"
_FONT_FAMILY = "DejaVu"


def _register_fonts(pdf: FPDF) -> None:
    """Registra a familia DejaVu no objeto FPDF.

    fpdf2 exige add_font por instancia. Silencioso se ambos os arquivos
    existem — lanca RuntimeError se faltam (sinal de deploy incompleto).
    """
    if not _FONT_REGULAR.exists() or not _FONT_BOLD.exists():
        raise RuntimeError(
            f"Fontes DejaVu ausentes em {_FONTS_DIR}. "
            "Reinstale o repositorio ou baixe do release dejavu-fonts 2.37."
        )
    pdf.add_font(_FONT_FAMILY, "", str(_FONT_REGULAR))
    pdf.add_font(_FONT_FAMILY, "B", str(_FONT_BOLD))


def _fmt_datetime(dt: datetime) -> str:
    """Formata em pt-BR sem depender de locale do sistema."""
    return dt.strftime("%d/%m/%Y %H:%M")


def gerar_pdf(
    *,
    nome_prova: str,
    nro_requerimento: str,
    vendedor_nome: str,
    qr_image_bytes: bytes,
    template: dict | None = None,
    created_at: datetime | None = None,
) -> bytes:
    """Renderiza a etiqueta como PDF e retorna os bytes.

    Args:
        nome_prova: Texto exibido em destaque.
        nro_requerimento: Numero do requerimento.
        vendedor_nome: Nome completo do vendedor responsavel.
        qr_image_bytes: PNG do QR Code (de qrcode_service.gerar_imagem_qr).
        template: Dict com as chaves do template_etiqueta. Se None, usa TEMPLATE_PADRAO.
        created_at: Usado apenas quando template["mostrar_data_criacao"] = True.

    Returns:
        Bytes do PDF (comeca com b'%PDF-').

    Raises:
        RuntimeError: se os TTFs de DejaVu nao estiverem presentes no deploy.
    """
    tpl = {**TEMPLATE_PADRAO, **(template or {})}
    formato = tpl.get("formato", "A4")
    logo_enabled = bool(tpl.get("logo_enabled", True))
    mostrar_data = bool(tpl.get("mostrar_data_criacao", False))

    if formato == "80mm_thermal":
        pdf = FPDF(orientation="P", unit="mm", format=(80, 120))
        largura_util = 74  # 80mm - 2*3mm margem
        qr_size = 40
    else:
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        largura_util = 190  # A4 = 210mm - 2*10mm margem
        qr_size = 70

    _register_fonts(pdf)

    pdf.set_auto_page_break(auto=False)
    pdf.set_margins(
        left=10 if formato != "80mm_thermal" else 3,
        top=10 if formato != "80mm_thermal" else 5,
        right=10 if formato != "80mm_thermal" else 3,
    )
    pdf.add_page()

    # ─── Cabecalho ────────────────────────────────────────────────────────
    if logo_enabled:
        pdf.set_font(_FONT_FAMILY, "B", 18 if formato != "80mm_thermal" else 14)
        pdf.cell(largura_util, 10, "3STUDIO", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    pdf.set_font(_FONT_FAMILY, "B", 14 if formato != "80mm_thermal" else 10)
    pdf.cell(
        largura_util,
        8,
        "PROVA DIGITAL",
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
        border="B",
    )
    pdf.ln(4)

    # ─── Campos de texto ─────────────────────────────────────────────────
    label_font_size = 10 if formato != "80mm_thermal" else 8
    value_font_size = 12 if formato != "80mm_thermal" else 9

    def _linha_campo(label: str, valor: str) -> None:
        pdf.set_font(_FONT_FAMILY, "B", label_font_size)
        pdf.cell(largura_util, 5, label, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(_FONT_FAMILY, "", value_font_size)
        # multi_cell permite quebra automatica de linhas longas.
        pdf.multi_cell(largura_util, 6, valor, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    _linha_campo("NOME DA PROVA", nome_prova)
    _linha_campo("NUMERO DO REQUERIMENTO", nro_requerimento)
    _linha_campo("VENDEDOR RESPONSAVEL", vendedor_nome)

    if mostrar_data and created_at is not None:
        _linha_campo("DATA DE CRIACAO", _fmt_datetime(created_at))

    pdf.ln(3)

    # ─── QR Code ─────────────────────────────────────────────────────────
    # Centraliza horizontalmente o QR na area util.
    qr_io = io.BytesIO(qr_image_bytes)
    current_y = pdf.get_y()
    pdf.image(
        qr_io,
        x=(pdf.w - qr_size) / 2,
        y=current_y,
        w=qr_size,
        h=qr_size,
    )
    pdf.set_y(current_y + qr_size + 3)

    # Legenda abaixo do QR. Nao usamos italico porque DejaVu Oblique nao esta
    # bundled (economiza ~700KB) — peso regular em tamanho menor da o mesmo
    # destaque visual.
    pdf.set_font(_FONT_FAMILY, "", 8)
    pdf.cell(
        largura_util,
        4,
        "Escaneie o QR Code com o sistema para movimentar esta prova",
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    # fpdf2 retorna bytearray. Convertemos para bytes imutavel para
    # compatibilidade com quem espera bytes (base64, testes, etc).
    output = pdf.output()
    if isinstance(output, bytearray):
        return bytes(output)
    return output
