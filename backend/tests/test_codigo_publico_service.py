"""Testes do codigo_publico_service (Wave 2 v4.0 — Componente 06).

Cobertura alvo: ≥95% (cobre todas as branches do modulo).
"""
import re
from datetime import datetime

from app.services.codigo_publico_service import (
    CODIGO_PUBLICO_NANO_ALPHABET,
    CODIGO_PUBLICO_NANO_LEN,
    CODIGO_PUBLICO_PREFIX,
    CODIGO_PUBLICO_TOTAL_LEN,
    gerar_codigo_publico,
    validar_formato_codigo_publico,
)


# ─── Constantes ───────────────────────────────────────────────────────────

def test_alfabeto_tem_31_chars_sem_ambiguos():
    assert len(CODIGO_PUBLICO_NANO_ALPHABET) == 31
    # DAT v3.0 §8.3: sem chars ambiguos 0/O, 1/I/L.
    for c in "01ILO":
        assert c not in CODIGO_PUBLICO_NANO_ALPHABET, (
            f"Char ambiguo '{c}' nao deveria estar no alfabeto"
        )


def test_constantes_basicas():
    assert CODIGO_PUBLICO_PREFIX == "PRV"
    assert CODIGO_PUBLICO_NANO_LEN == 6
    assert CODIGO_PUBLICO_TOTAL_LEN == 18  # 3+1+4+1+2+1+6


# ─── gerar_codigo_publico ──────────────────────────────────────────────────

def test_gerar_codigo_publico_formato_basico():
    codigo = gerar_codigo_publico(datetime(2026, 5, 4))
    assert codigo.startswith("PRV-2026-05-")
    assert len(codigo) == CODIGO_PUBLICO_TOTAL_LEN


def test_gerar_codigo_publico_regex_completo():
    codigo = gerar_codigo_publico(datetime(2026, 5, 4))
    pattern = re.compile(
        rf"^PRV-\d{{4}}-\d{{2}}-[{re.escape(CODIGO_PUBLICO_NANO_ALPHABET)}]{{6}}$"
    )
    assert pattern.match(codigo), f"Codigo {codigo!r} nao bate com regex"


def test_gerar_codigo_publico_mes_zero_padded():
    # Janeiro vira "01", nao "1".
    codigo = gerar_codigo_publico(datetime(2026, 1, 15))
    assert codigo.startswith("PRV-2026-01-"), codigo
    # Setembro vira "09", nao "9".
    codigo = gerar_codigo_publico(datetime(2026, 9, 1))
    assert codigo.startswith("PRV-2026-09-"), codigo


def test_gerar_codigo_publico_dezembro():
    codigo = gerar_codigo_publico(datetime(2026, 12, 31))
    assert codigo.startswith("PRV-2026-12-"), codigo


def test_gerar_codigo_publico_alfabeto_restrito():
    # Geramos 200 codigos e validamos que NENHUM contem char ambiguo.
    for _ in range(200):
        codigo = gerar_codigo_publico(datetime(2026, 5, 4))
        sufixo = codigo[-6:]
        for c in sufixo:
            assert c in CODIGO_PUBLICO_NANO_ALPHABET, (
                f"Char {c!r} fora do alfabeto em sufixo {sufixo!r}"
            )
            assert c not in "01ILO", f"Char ambiguo {c!r} em {codigo}"


def test_gerar_codigo_publico_determinismo_prefixo():
    # Mesma data -> mesmo prefixo (ate antes do sufixo).
    base = datetime(2026, 5, 4)
    codigos = [gerar_codigo_publico(base) for _ in range(50)]
    prefixos = {c[:12] for c in codigos}  # 'PRV-2026-05-' = 12 chars
    assert prefixos == {"PRV-2026-05-"}


def test_gerar_codigo_publico_nao_determinismo_sufixo():
    # 200 chamadas seguidas com mesma data devem produzir sufixos distintos.
    # Probabilidade de colisao em 200 chamadas: ~200^2 / (2 * 31^6) ≈ 2.3e-5.
    # Aceitavel para teste — flake rate <0.001%.
    base = datetime(2026, 5, 4)
    codigos = [gerar_codigo_publico(base) for _ in range(200)]
    distintos = len(set(codigos))
    assert distintos >= 199, (
        f"Esperado ~200 codigos distintos, obtive {distintos} "
        f"(nao-determinismo do sufixo nao funciona ou colisao alta)"
    )


def test_gerar_codigo_publico_ano_4_digitos():
    # Anos < 1000 sao zero-padded (cenario hipotetico).
    codigo = gerar_codigo_publico(datetime(999, 1, 1))
    assert codigo.startswith("PRV-0999-01-"), codigo


# ─── validar_formato_codigo_publico ────────────────────────────────────────

def test_validar_aceita_codigos_validos():
    codigos_validos = [
        "PRV-2026-05-K3T9XB",
        "PRV-2026-12-AAAAAA",
        "PRV-9999-01-ZZZZZZ",
        "PRV-0001-12-2345AB",
    ]
    for c in codigos_validos:
        assert validar_formato_codigo_publico(c), f"Deveria aceitar {c!r}"


def test_validar_rejeita_lowercase():
    assert validar_formato_codigo_publico("PRV-2026-05-k3t9xb") is False
    assert validar_formato_codigo_publico("prv-2026-05-K3T9XB") is False


def test_validar_rejeita_prefixo_errado():
    assert validar_formato_codigo_publico("XYZ-2026-05-K3T9XB") is False
    assert validar_formato_codigo_publico("PR-2026-05-K3T9XBA") is False


def test_validar_rejeita_ano_invalido():
    # Ano com 2 digitos:
    assert validar_formato_codigo_publico("PRV-26-05-K3T9XBAB") is False
    # Ano com letras:
    assert validar_formato_codigo_publico("PRV-ABCD-05-K3T9XB") is False


def test_validar_rejeita_mes_invalido():
    assert validar_formato_codigo_publico("PRV-2026-13-K3T9XB") is False
    assert validar_formato_codigo_publico("PRV-2026-00-K3T9XB") is False
    assert validar_formato_codigo_publico("PRV-2026-AB-K3T9XB") is False
    # Mes de 1 digito (sem zero padding):
    assert validar_formato_codigo_publico("PRV-2026-5-K3T9XBA") is False


def test_validar_rejeita_sufixo_invalido():
    # Sufixo curto:
    assert validar_formato_codigo_publico("PRV-2026-05-K3T9X") is False
    # Sufixo longo:
    assert validar_formato_codigo_publico("PRV-2026-05-K3T9XBC") is False
    # Char ambiguo no sufixo:
    assert validar_formato_codigo_publico("PRV-2026-05-K3T9X0") is False  # 0
    assert validar_formato_codigo_publico("PRV-2026-05-K3T9X1") is False  # 1
    assert validar_formato_codigo_publico("PRV-2026-05-K3T9XI") is False  # I
    assert validar_formato_codigo_publico("PRV-2026-05-K3T9XL") is False  # L
    assert validar_formato_codigo_publico("PRV-2026-05-K3T9XO") is False  # O
    # Char fora do range:
    assert validar_formato_codigo_publico("PRV-2026-05-K3T9X@") is False


def test_validar_rejeita_tamanho_errado():
    assert validar_formato_codigo_publico("") is False
    assert validar_formato_codigo_publico("PRV-2026") is False
    assert validar_formato_codigo_publico("PRV-2026-05-K3T9XB-EXTRA") is False


def test_validar_rejeita_separadores_errados():
    assert validar_formato_codigo_publico("PRV/2026/05/K3T9XB") is False
    assert validar_formato_codigo_publico("PRV.2026.05.K3T9XB") is False
    # Sem separadores:
    assert validar_formato_codigo_publico("PRV202605K3T9XB89") is False


def test_validar_rejeita_nao_string():
    assert validar_formato_codigo_publico(None) is False  # type: ignore[arg-type]
    assert validar_formato_codigo_publico(123456) is False  # type: ignore[arg-type]


# ─── Round-trip: gerar -> validar ─────────────────────────────────────────

def test_round_trip_gera_e_valida():
    """Todo codigo gerado deve passar pelo validador (sanity check)."""
    for _ in range(100):
        codigo = gerar_codigo_publico(datetime(2026, 5, 4))
        assert validar_formato_codigo_publico(codigo), (
            f"Codigo gerado {codigo!r} nao passa no validador — drift entre "
            f"gerar e validar"
        )
