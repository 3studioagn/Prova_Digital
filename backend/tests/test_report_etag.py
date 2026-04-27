"""Unit tests para app/services/report_etag.py (Wave 5, Componente 16).

Cobre:
  - compute_etag: determinismo, sensibilidade a mudancas, formato com aspas.
  - matches_if_none_match: match exato, lista comma-separated, wildcard.
  - Aceita BaseModel e dict.
  - Rejeita tipos invalidos.
"""
import pytest
from pydantic import BaseModel

from app.services.report_etag import compute_etag, matches_if_none_match

# ─── Helpers ──────────────────────────────────────────────────────────────


class _SimplePayload(BaseModel):
    chave: str
    valor: int


# ─── compute_etag — basico ────────────────────────────────────────────────


class TestComputeEtagBasico:
    def test_formato_quoted_sha256(self):
        etag = compute_etag(_SimplePayload(chave="x", valor=1))
        # '"<64-hex>"' = 66 chars total
        assert len(etag) == 66
        assert etag.startswith('"')
        assert etag.endswith('"')

    def test_aceita_dict(self):
        etag = compute_etag({"a": 1, "b": 2})
        assert len(etag) == 66

    def test_rejeita_tipo_invalido(self):
        with pytest.raises(TypeError):
            compute_etag("not a model or dict")  # type: ignore[arg-type]

    def test_rejeita_lista(self):
        with pytest.raises(TypeError):
            compute_etag([1, 2, 3])  # type: ignore[arg-type]


# ─── compute_etag — determinismo ──────────────────────────────────────────


class TestComputeEtagDeterminismo:
    def test_payload_identico_etag_identico(self):
        a = _SimplePayload(chave="x", valor=1)
        b = _SimplePayload(chave="x", valor=1)
        assert compute_etag(a) == compute_etag(b)

    def test_dict_identico_etag_identico(self):
        a = {"chave": "x", "valor": 1}
        b = {"chave": "x", "valor": 1}
        assert compute_etag(a) == compute_etag(b)

    def test_dict_e_basemodel_equivalentes(self):
        """O mesmo conteudo via BaseModel ou dict produz o mesmo ETag."""
        bm = _SimplePayload(chave="x", valor=1)
        d = {"chave": "x", "valor": 1}
        assert compute_etag(bm) == compute_etag(d)

    def test_ordem_de_chaves_no_dict_irrelevante(self):
        """sort_keys=True garante invariancia a ordem."""
        a = {"a": 1, "b": 2}
        b = {"b": 2, "a": 1}
        assert compute_etag(a) == compute_etag(b)


# ─── compute_etag — sensibilidade ─────────────────────────────────────────


class TestComputeEtagSensibilidade:
    def test_mudanca_em_campo_muda_etag(self):
        a = _SimplePayload(chave="x", valor=1)
        b = _SimplePayload(chave="x", valor=2)
        assert compute_etag(a) != compute_etag(b)

    def test_mudanca_em_outro_campo_muda_etag(self):
        a = _SimplePayload(chave="a", valor=1)
        b = _SimplePayload(chave="b", valor=1)
        assert compute_etag(a) != compute_etag(b)

    def test_dicts_com_chaves_diferentes(self):
        assert compute_etag({"a": 1}) != compute_etag({"b": 1})

    def test_string_vazia_vs_none_diferentes(self):
        assert compute_etag({"x": ""}) != compute_etag({"x": None})


# ─── matches_if_none_match ────────────────────────────────────────────────


class TestMatchesIfNoneMatch:
    def test_header_none_retorna_false(self):
        assert matches_if_none_match(None, '"abc"') is False

    def test_header_vazio_retorna_false(self):
        assert matches_if_none_match("", '"abc"') is False
        assert matches_if_none_match("   ", '"abc"') is False

    def test_match_exato(self):
        assert matches_if_none_match('"abc"', '"abc"') is True

    def test_no_match(self):
        assert matches_if_none_match('"xyz"', '"abc"') is False

    def test_wildcard(self):
        """`*` faz match com qualquer recurso (RFC 7232)."""
        assert matches_if_none_match("*", '"abc"') is True
        assert matches_if_none_match("*", '"different"') is True

    def test_lista_comma_separated_match(self):
        assert matches_if_none_match('"abc", "def", "xyz"', '"def"') is True

    def test_lista_comma_separated_no_match(self):
        assert matches_if_none_match('"abc", "def"', '"xyz"') is False

    def test_lista_com_espacos_extras(self):
        assert matches_if_none_match('"a" , "b"  ,  "c"', '"b"') is True

    def test_aspas_importam(self):
        """ETag sem aspas nao deve matchar ETag com aspas."""
        assert matches_if_none_match("abc", '"abc"') is False
        assert matches_if_none_match('"abc"', "abc") is False

    def test_round_trip_com_compute_etag(self):
        """Cenario real: backend gera ETag, cliente devolve em If-None-Match."""
        payload = _SimplePayload(chave="x", valor=1)
        etag = compute_etag(payload)
        # Cliente envia exatamente o que recebeu
        assert matches_if_none_match(etag, etag) is True
