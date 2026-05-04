"""Geracao do codigo publico legivel da prova (DAT v3.0 §8.3 + RF-005 v4.0).

Wave 2 v4.0 — Componente 06.

Formato: PRV-AAAA-MM-NNNNNN
  PRV    = prefixo fixo (identifica o tipo de objeto)
  AAAA   = ano de criacao da prova
  MM     = mes de criacao (zero-padded)
  NNNNNN = sequencial alfanumerico de 6 caracteres
           Alfabeto: 31 chars sem ambiguos (sem 0/O, 1/I/L)

Caracteristicas:
  - Determinismo do prefixo dado o `criado_em`.
  - Nao-determinismo do sufixo via `secrets.choice` (CSPRNG).
  - Unicidade enforced pela coluna `provas_digitais.codigo_publico UNIQUE`
    e pelo trigger `trg_provas_rota_imutavel`.
  - Tamanho total fixo: 17 chars (`PRV-` + 4 + `-` + 2 + `-` + 6).
  - 31^6 ≈ 887 milhoes de combinacoes/mes — entropia adequada para o
    volume operacional + rate limiting do Componente 19 (Wave 3 v4.0).

Usado por:
  - `app/api/v1/provas.py:create_prova` na criacao da prova.
  - `app/services/qrcode_service.gerar_payload_qr` para embutir no QR.
  - Wave 3 v4.0 (Componente 19) para resolver `codigo_publico` digitado
    manualmente ao mesmo registro do banco.
"""
from __future__ import annotations

import secrets
from datetime import datetime

# Alfabeto sem caracteres ambiguos (DAT v3.0 §8.3): sem 0/O, 1/I/L.
# 23 letras + 8 digitos = 31 chars. 31^6 ≈ 887M combinacoes/mes.
CODIGO_PUBLICO_PREFIX = "PRV"
CODIGO_PUBLICO_NANO_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODIGO_PUBLICO_NANO_LEN = 6
# Total: 'PRV' + '-' + 'YYYY' + '-' + 'MM' + '-' + 6 = 3+1+4+1+2+1+6 = 18.
# Atencao: VARCHAR(20) na tabela tem folga de 2 chars; manter compatibilidade
# se algum dia o formato for estendido.
CODIGO_PUBLICO_TOTAL_LEN = 18


def gerar_codigo_publico(criado_em: datetime) -> str:
    """Gera codigo publico no formato `PRV-AAAA-MM-NNNNNN`.

    Args:
        criado_em: timestamp de criacao da prova. Apenas ano e mes sao usados.

    Returns:
        String de 18 caracteres (`PRV-2026-05-K3T9XB`, p. ex.).

    O sufixo aleatorio e gerado por `secrets.choice` (CSPRNG do Python).
    """
    sufixo = "".join(
        secrets.choice(CODIGO_PUBLICO_NANO_ALPHABET)
        for _ in range(CODIGO_PUBLICO_NANO_LEN)
    )
    return (
        f"{CODIGO_PUBLICO_PREFIX}-{criado_em.year:04d}-"
        f"{criado_em.month:02d}-{sufixo}"
    )


def validar_formato_codigo_publico(codigo: str) -> bool:
    """True se `codigo` segue exatamente o formato `PRV-AAAA-MM-NNNNNN`.

    Validacao estrutural pura — nao consulta banco. Usada pelo Componente
    19 (Wave 3 v4.0) para rejeitar input mal formado antes de qualquer
    SELECT, mitigando enumeracao via timing diferenciado.
    """
    if not isinstance(codigo, str):
        return False
    if len(codigo) != CODIGO_PUBLICO_TOTAL_LEN:
        return False
    parts = codigo.split("-")
    if len(parts) != 4:
        return False
    pref, ano, mes, sufixo = parts
    if pref != CODIGO_PUBLICO_PREFIX:
        return False
    if not (ano.isdigit() and len(ano) == 4):
        return False
    if not (mes.isdigit() and len(mes) == 2 and 1 <= int(mes) <= 12):
        return False
    if len(sufixo) != CODIGO_PUBLICO_NANO_LEN:
        return False
    if any(c not in CODIGO_PUBLICO_NANO_ALPHABET for c in sufixo):
        return False
    return True
