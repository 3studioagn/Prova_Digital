"""Geracao do PDF da etiqueta imprimivel (RF-003, RN-011, ADR-035).

Wave 2 v4.0 (Componente 06): adiciona dois elementos novos ao layout:
  - `codigo_publico` em destaque ABAIXO do QR Code (DAT v3.0 §8.3 +
    RF-003 v4.0 — fallback para escaneamento manual).
  - Badge da rota (`MATRIZ`/`LAM. MATRIZ`/`FILIAL`/`LAM. FILIAL`) no
    rodape esquerdo (RN-011 v4.0).

Ambos os parametros sao Optional para suportar provas legadas v3.0
sem rota persistida e/ou sem codigo_publico (estas ultimas serao
backfilled pela migration 012; PROVAS LEGADAS COM `rota=NULL`
continuam ate a Wave 7).

Usa `fpdf2` — zero dependencias nativas, suficiente para o layout "padrao".
O template vem de `configuracoes_sistema.template_etiqueta` (ADR-036), que
apos a migration 009 e um objeto JSONB:
  {
    "nome": "padrao",
    "formato": "A4" | "80mm_thermal",  # legacy, nao usado mais
    "logo_enabled": bool,
    "mostrar_data_criacao": bool
  }

A etiqueta tem dimensao fixa **90mm x 57mm (paisagem)** definida pelo
design no Figma — comprimento 9cm e altura 5,7cm. O campo `formato` no
template e ignorado pelo render, mas continua sendo aceito pelo schema
para compatibilidade com a configuracao existente.

LAYOUT (matching o design Figma — Sessao 14):
  - Linha horizontal preta no topo (border-top sutil)
  - Cabecalho esquerdo: 2 logos lado a lado (3STUDIO + studio&ART!)
  - Cabecalho direito: texto "Aponte a camera para o QR CODE"
  - Banner preto horizontal abaixo dos logos (separator visual grosso)
  - Conteudo esquerdo: Nome, Requerimento, Vendedor (label bold + valor)
  - Conteudo direito: QR Code dentro de retangulo com cantos arredondados
  - Rodape esquerdo: ano de criacao
  - Rodape direito: "Etiqueta de rastreio"
  - Linha horizontal preta no rodape (border-bottom sutil)

LOGOS:
  Os 2 logos sao SVG vetoriais em `app/services/etiqueta_assets/`.
  fpdf2 (>=2.7) renderiza SVG nativamente via `pdf.image()` — exige
  `defusedxml` instalado (ja vem com fpdf2[svg]).

FONTE UNICODE (post-Wave 2 hardening, Sessao 12):
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

from app.db.models import RotaEnum

logger = logging.getLogger(__name__)


TEMPLATE_PADRAO = {
    "nome": "padrao",
    "formato": "A4",  # legacy, nao usado mais — etiqueta sempre 90x57mm
    "logo_enabled": True,
    "mostrar_data_criacao": False,
}


# Wave 2 v4.0 (Componente 06): texto exibido no badge de rota da etiqueta.
# Inclui valores legacy (PADRAO/DIRETA) com sufixo "(legada)" para o caso
# de regerar etiqueta de prova v3.0 antes do backfill da Wave 7.
ROTA_BADGE_LABELS: dict[RotaEnum, str] = {
    RotaEnum.MATRIZ: "MATRIZ",
    RotaEnum.LAM_MATRIZ: "LAM. MATRIZ",
    RotaEnum.FILIAL: "FILIAL",
    RotaEnum.LAM_FILIAL: "LAM. FILIAL",
    # Legacy v3.0 — substituidos no backfill da Wave 7 (Componente 21).
    RotaEnum.PADRAO: "MATRIZ (legada)",
    RotaEnum.DIRETA: "FILIAL (legada)",
}


# ─── Fonte Unicode ────────────────────────────────────────────────────────
# Resolve o caminho absoluto dos TTF independente do cwd.
_FONTS_DIR = Path(__file__).resolve().parent / "fonts"
_FONT_REGULAR = _FONTS_DIR / "DejaVuSans.ttf"
_FONT_BOLD = _FONTS_DIR / "DejaVuSans-Bold.ttf"
_FONT_FAMILY = "DejaVu"

# ─── Assets visuais (logos vetoriais) ─────────────────────────────────────
_ASSETS_DIR = Path(__file__).resolve().parent / "etiqueta_assets"
_LOGO_3STUDIO = _ASSETS_DIR / "logo_3studio.svg"
_LOGO_STUDIO_ART = _ASSETS_DIR / "logo_studio_e_arte.svg"

# ─── Dimensoes da etiqueta ────────────────────────────────────────────────
# 9cm x 5.7cm = 90mm x 57mm (paisagem)
ETIQUETA_W = 90.0
ETIQUETA_H = 57.0

# ─── Parametros do adaptive sizing dos campos ─────────────────────────────
# Largura do bloco de texto esquerdo (x=3 a x=56, antes do QR em x=58).
# O multi_cell com markdown=True tem ~5mm de overhead (cell padding interno
# + margem de seguranca pro wrap) comparado ao que `get_string_width` mede
# diretamente. Calibrado empiricamente contra o caso real "ETIQ CAFE
# CAPRONI CLASSICO" — nome longo que no 7pt cabe em uma linha.
_CAMPO_W = 53.0
_CAMPO_INNER_W = _CAMPO_W - 5.0
_LINE_H_DEFAULT = 4.8
_FONT_SIZE_DEFAULT = 9.0
_FONT_SIZE_MIN = 7.0
_SIZES_TO_TRY = (9.0, 8.5, 8.0, 7.5, 7.0)


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


def _check_assets() -> None:
    """Verifica que os SVGs dos logos existem no deploy."""
    missing = [p for p in (_LOGO_3STUDIO, _LOGO_STUDIO_ART) if not p.exists()]
    if missing:
        raise RuntimeError(
            f"Assets de etiqueta ausentes: {[str(p) for p in missing]}. "
            "Verifique backend/app/services/etiqueta_assets/."
        )


def _fmt_datetime(dt: datetime) -> str:
    """Formata em pt-BR sem depender de locale do sistema."""
    return dt.strftime("%d/%m/%Y %H:%M")


def _fmt_year(dt: datetime) -> str:
    return dt.strftime("%Y")


def gerar_pdf(
    *,
    nome_prova: str,
    nro_requerimento: str,
    vendedor_nome: str,
    qr_image_bytes: bytes,
    codigo_publico: str | None = None,
    rota: RotaEnum | None = None,
    template: dict | None = None,
    created_at: datetime | None = None,
) -> bytes:
    """Renderiza a etiqueta como PDF e retorna os bytes.

    Dimensao FIXA de 90mm x 57mm (paisagem) — matching o design do Figma.
    O campo `formato` do template e aceito mas ignorado pelo render.

    Args:
        nome_prova: Texto exibido em destaque.
        nro_requerimento: Numero do requerimento.
        vendedor_nome: Nome completo do vendedor responsavel.
        qr_image_bytes: PNG do QR Code (de qrcode_service.gerar_imagem_qr).
        codigo_publico: Codigo legivel `PRV-AAAA-MM-NNNNNN` (Wave 2 v4.0).
                        Se None, omite o bloco do codigo (provas v3.0
                        pre-migration 012). Renderizado abaixo do QR.
        rota: RotaEnum (Wave 2 v4.0). Se None, omite o badge (provas v3.0
              com `rota = NULL`). Renderizado no rodape esquerdo.
        template: Dict com as chaves do template_etiqueta. Se None, usa TEMPLATE_PADRAO.
                  Campos respeitados: `logo_enabled`, `mostrar_data_criacao`.
        created_at: Usado para extrair o ano (rodape) e a data completa
                    (quando `mostrar_data_criacao` = True).

    Returns:
        Bytes do PDF (comeca com b'%PDF-').

    Raises:
        RuntimeError: se TTFs ou SVGs estiverem ausentes no deploy.
    """
    tpl = {**TEMPLATE_PADRAO, **(template or {})}
    logo_enabled = bool(tpl.get("logo_enabled", True))
    mostrar_data = bool(tpl.get("mostrar_data_criacao", False))

    _check_assets()

    pdf = FPDF(orientation="P", unit="mm", format=(ETIQUETA_W, ETIQUETA_H))
    pdf.set_auto_page_break(auto=False)
    pdf.set_margins(left=3, top=3, right=3)
    pdf.add_page()
    _register_fonts(pdf)

    # Cor padrao: tudo preto sobre branco
    pdf.set_draw_color(0, 0, 0)
    pdf.set_fill_color(0, 0, 0)
    pdf.set_text_color(0, 0, 0)

    # ─── Linha horizontal superior ────────────────────────────────────────
    pdf.set_line_width(0.4)
    pdf.line(3, 3, ETIQUETA_W - 3, 3)

    # ─── Cabecalho: logos a esquerda + texto QR a direita ────────────────
    if logo_enabled:
        # Logo 3STUDIO — viewBox 56.23 x 11.85 (ratio ~4.75:1).
        # 22mm largura -> ~4.6mm altura. Posicionado com respiro do topo.
        pdf.image(str(_LOGO_3STUDIO), x=4, y=8, w=22)

        # Logo studio &ART! — viewBox 45.57 x 23.79 (ratio ~1.92:1).
        # 13mm largura -> ~6.8mm altura. Posicionado um pouco acima para
        # que o ponto de exclamacao alongado fique alinhado ao topo do
        # 3STUDIO.
        pdf.image(str(_LOGO_STUDIO_ART), x=28.5, y=6.5, w=13)

    # Texto direito: "Aponte a camera para o QR CODE"
    # Centralizado horizontalmente EM CIMA do QR Code (que comeca em
    # x=58, w=29 → centro em x=72.5). Usa multi_cell com markdown=True
    # + align="C" para suportar **bold** inline e auto-centralizar.
    pdf.set_xy(58, 6)
    pdf.set_font(_FONT_FAMILY, "", 7.5)
    pdf.multi_cell(
        w=29,
        h=3.5,
        text="Aponte a camera\npara o **QR CODE**",
        markdown=True,
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    # ─── Banner preto horizontal (separador grosso) ──────────────────────
    # Vai apenas do inicio (x=3) ate o fim do bloco dos logos (~x=46),
    # NAO se estende ate o lado direito onde fica o QR code.
    pdf.set_fill_color(0, 0, 0)
    pdf.rect(3, 16, 44, 2, style="F")

    # ─── Conteudo esquerdo: Nome / Requerimento / Vendedor ───────────────
    # Adaptive sizing: usa multi_cell com markdown=True (suporta **bold**
    # inline). Tenta os tamanhos do MAIOR pro MENOR e usa o primeiro que
    # couber em uma unica linha. Constantes (_CAMPO_W, _SIZES_TO_TRY, etc)
    # definidas no topo do modulo.

    def _measure_one_line(label: str, valor: str, size: float) -> bool:
        """Retorna True se 'Label: valor' (label bold + valor regular)
        cabe em _CAMPO_INNER_W."""
        pdf.set_font(_FONT_FAMILY, "B", size)
        w_label = pdf.get_string_width(f"{label}: ")
        pdf.set_font(_FONT_FAMILY, "", size)
        w_valor = pdf.get_string_width(valor)
        return w_label + w_valor < _CAMPO_INNER_W

    def _campo(label: str, valor: str) -> None:
        # Procura o maior tamanho de fonte (dos _SIZES_TO_TRY) que faz
        # o conteudo caber em uma unica linha. Se nenhum couber, usa o
        # menor (_FONT_SIZE_MIN) e deixa o multi_cell quebrar em 2 linhas.
        chosen_size = _FONT_SIZE_MIN
        for size in _SIZES_TO_TRY:
            if _measure_one_line(label, valor, size):
                chosen_size = size
                break
        pdf.set_x(3)
        pdf.set_font(_FONT_FAMILY, "", chosen_size)
        line_h = _LINE_H_DEFAULT * (chosen_size / _FONT_SIZE_DEFAULT)
        pdf.multi_cell(
            w=_CAMPO_W,
            h=line_h,
            text=f"**{label}:** {valor}",
            markdown=True,
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.ln(0.8)

    # Centralizacao vertical dos 3 campos entre o banner (y=18) e o
    # rodape (y=49). Espaco util = 31mm; 3 campos com line_h ~5.6mm
    # (multi_cell 4.8mm + ln 0.8mm) ocupam ~16.8mm. Sobram ~14.2mm
    # distribuidos igualmente — ~7.1mm em cima + ~7.1mm embaixo.
    pdf.set_y(25)
    _campo("Nome", nome_prova)
    _campo("Requerimento", nro_requerimento)
    _campo("Vendedor", vendedor_nome)

    # Data de criacao opcional (logo abaixo do bloco principal)
    if mostrar_data and created_at is not None:
        _campo("Data", _fmt_datetime(created_at))

    # ─── QR Code (lado direito) ──────────────────────────────────────────
    # Quadrado com cantos arredondados envolvendo o QR.
    # Posicionado em x=58 (em vez de 55) para liberar 3mm a mais para o
    # bloco esquerdo, permitindo que "Nome: ETIQ CAFE CAPRONI CLASSICO"
    # caiba em uma linha so com fonte 7.5pt.
    qr_box_x = 58
    qr_box_y = 15
    qr_box_size = 26  # Wave 2 v4.0: reduzido de 29 para abrir 3mm para
                       # o codigo_publico abaixo (RF-003 v4.0).
    pdf.set_line_width(0.4)
    pdf.set_draw_color(0, 0, 0)
    # `round_corners=True` exige fpdf2 >= 2.7 (ja temos 2.8.7)
    pdf.rect(
        qr_box_x,
        qr_box_y,
        qr_box_size,
        qr_box_size,
        style="D",
        round_corners=True,
        corner_radius=2.8,
    )
    # QR code centralizado dentro do quadrado, com pequena margem.
    qr_padding = 2.2
    qr_size = qr_box_size - 2 * qr_padding
    qr_io = io.BytesIO(qr_image_bytes)
    pdf.image(
        qr_io,
        x=qr_box_x + qr_padding,
        y=qr_box_y + qr_padding,
        w=qr_size,
        h=qr_size,
    )

    # ─── Codigo publico abaixo do QR (Wave 2 v4.0 — RF-003 v4.0) ─────────
    # Texto monospace centralizado no espaco do QR, em destaque para
    # permitir digitacao manual em caso de falha do scanner.
    if codigo_publico:
        pdf.set_font(_FONT_FAMILY, "B", 8.5)
        pdf.set_xy(qr_box_x - 1, qr_box_y + qr_box_size + 0.5)
        pdf.cell(qr_box_size + 2, 3.5, codigo_publico, align="C")

    # ─── Rodape: badge da rota (Wave 2 v4.0) + ano + texto direita ───────
    rodape_y = 49
    pdf.set_font(_FONT_FAMILY, "", 8.5)
    ano = _fmt_year(created_at) if created_at is not None else ""

    if rota is not None:
        # Badge preto filled com texto branco — destaca a rota da prova
        # (Lam. Matriz, Filial, etc.).
        badge_text = ROTA_BADGE_LABELS.get(rota, rota.value)
        pdf.set_font(_FONT_FAMILY, "B", 6.5)
        badge_w = pdf.get_string_width(badge_text) + 3.5
        pdf.set_fill_color(0, 0, 0)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(3, rodape_y)
        pdf.cell(badge_w, 4, badge_text, align="C", fill=True)
        # Restaura cor padrao para o ano.
        pdf.set_text_color(0, 0, 0)
        pdf.set_font(_FONT_FAMILY, "", 8.5)
        pdf.set_xy(3 + badge_w + 1.5, rodape_y)
        pdf.cell(15, 4, ano, align="L")
    else:
        # Provas legadas v3.0 com rota=NULL: so o ano (comportamento v3.0).
        pdf.set_xy(3, rodape_y)
        pdf.cell(40, 4, ano, align="L")

    pdf.set_xy(ETIQUETA_W - 50, rodape_y)
    pdf.cell(47, 4, "Etiqueta de rastreio", align="R")

    # ─── Linha horizontal inferior ────────────────────────────────────────
    pdf.set_line_width(0.4)
    pdf.line(3, ETIQUETA_H - 3, ETIQUETA_W - 3, ETIQUETA_H - 3)

    # fpdf2 retorna bytearray. Convertemos para bytes imutavel para
    # compatibilidade com quem espera bytes (base64, testes, etc).
    output = pdf.output()
    if isinstance(output, bytearray):
        return bytes(output)
    return output
