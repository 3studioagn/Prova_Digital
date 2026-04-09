"""Unit tests for Pydantic schemas (domain/schemas/user.py + prova.py + configuracao.py)."""
import uuid

import pytest
from pydantic import ValidationError

from app.db.models import LocalizacaoEnum, SetorEnum
from app.domain.schemas.configuracao import (
    ConfiguracaoValidationError,
    validar_template_etiqueta,
)
from app.domain.schemas.prova import (
    ProvaCreateRequest,
    UploadUrlRequest,
    _normalize_nro_requerimento,
    sanitize_filename,
)
from app.domain.schemas.user import UserCreate, UserUpdate


class TestUserCreate:
    def test_valid_studio(self):
        u = UserCreate(
            nome="Test", email="test@example.com", senha="Pass1234",
            setor=SetorEnum.STUDIO,
        )
        assert u.setor == SetorEnum.STUDIO
        assert u.localizacao is None
        assert u.is_admin is False

    def test_valid_vendedor_with_loc(self):
        u = UserCreate(
            nome="Test", email="test@example.com", senha="Pass1234",
            setor=SetorEnum.VENDEDOR, localizacao=LocalizacaoEnum.MATRIZ,
        )
        assert u.localizacao == LocalizacaoEnum.MATRIZ

    def test_email_normalized(self):
        u = UserCreate(
            nome="T", email="  Test@Example.COM  ", senha="Pass1234",
            setor=SetorEnum.STUDIO,
        )
        assert u.email == "test@example.com"

    def test_invalid_email(self):
        with pytest.raises(ValidationError, match="Email em formato invalido"):
            UserCreate(
                nome="T", email="not-an-email", senha="Pass1234",
                setor=SetorEnum.STUDIO,
            )

    def test_senha_no_letter(self):
        with pytest.raises(ValidationError, match="letra"):
            UserCreate(
                nome="T", email="t@e.com", senha="12345678",
                setor=SetorEnum.STUDIO,
            )

    def test_senha_no_digit(self):
        with pytest.raises(ValidationError, match="numero"):
            UserCreate(
                nome="T", email="t@e.com", senha="abcdefgh",
                setor=SetorEnum.STUDIO,
            )

    def test_senha_too_short(self):
        with pytest.raises(ValidationError):
            UserCreate(
                nome="T", email="t@e.com", senha="Ab1",
                setor=SetorEnum.STUDIO,
            )

    def test_vendedor_without_loc(self):
        with pytest.raises(ValidationError, match="localizacao"):
            UserCreate(
                nome="T", email="t@e.com", senha="Pass1234",
                setor=SetorEnum.VENDEDOR,
            )

    def test_non_vendedor_with_loc(self):
        with pytest.raises(ValidationError, match="vendedores"):
            UserCreate(
                nome="T", email="t@e.com", senha="Pass1234",
                setor=SetorEnum.STUDIO, localizacao=LocalizacaoEnum.FILIAL,
            )

    def test_is_admin_flag(self):
        u = UserCreate(
            nome="T", email="t@e.com", senha="Pass1234",
            setor=SetorEnum.STUDIO, is_admin=True,
        )
        assert u.is_admin is True


class TestUserUpdate:
    def test_partial_fields(self):
        u = UserUpdate(nome="New Name")
        data = u.model_dump(exclude_unset=True)
        assert data == {"nome": "New Name"}

    def test_empty_update(self):
        u = UserUpdate()
        data = u.model_dump(exclude_unset=True)
        assert data == {}

    def test_multiple_fields(self):
        u = UserUpdate(nome="X", setor=SetorEnum.MOTORISTA, is_admin=True)
        data = u.model_dump(exclude_unset=True)
        assert set(data.keys()) == {"nome", "setor", "is_admin"}


# ─── Wave 2 — prova.py ──────────────────────────────────────────────────────


class TestNormalizeNroRequerimento:
    """A5 — normalizacao case-insensitive do nro_requerimento."""

    def test_uppercase(self):
        assert _normalize_nro_requerimento("req-001") == "REQ-001"

    def test_already_uppercase(self):
        assert _normalize_nro_requerimento("REQ-001") == "REQ-001"

    def test_mixed_case(self):
        assert _normalize_nro_requerimento("Req-2026/01") == "REQ-2026/01"

    def test_strip_whitespace(self):
        assert _normalize_nro_requerimento("  req-001  ") == "REQ-001"

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="nao pode ser vazio"):
            _normalize_nro_requerimento("   ")

    def test_invalid_chars_rejected(self):
        with pytest.raises(ValueError, match="apenas letras"):
            _normalize_nro_requerimento("req-001!@#")


class TestUploadUrlRequestNormalization:
    def test_upload_url_normalizes_nro_req(self):
        req = UploadUrlRequest(
            nro_requerimento="req-2026-001",
            filename="arte.jpg",
            content_type="image/jpeg",
        )
        assert req.nro_requerimento == "REQ-2026-001"


class TestProvaCreateRequestNormalization:
    def test_create_normalizes_nro_req(self):
        req = ProvaCreateRequest(
            nome="Prova",
            nro_requerimento="req-001",
            cliente="ACME",
            vendedor_id=uuid.uuid4(),
            object_key="provas/2026/04/abc/arte.jpg",
        )
        assert req.nro_requerimento == "REQ-001"


class TestSanitizeFilename:
    """M1 + M2 — preservar extensao + strip de pontos."""

    def test_plain_filename(self):
        assert sanitize_filename("arte.jpg") == "arte.jpg"

    def test_empty(self):
        assert sanitize_filename("") == "arquivo"

    def test_whitespace_only(self):
        assert sanitize_filename("   ") == "arquivo"

    def test_dots_only(self):
        assert sanitize_filename("...") == "arquivo"

    def test_path_traversal_neutralized(self):
        # "../etc/passwd" -> separadores viram _, pontos de path perdem especificidade
        result = sanitize_filename("../etc/passwd")
        assert ".." not in result
        assert "/" not in result
        assert "arquivo" in result or "etc" in result  # nome semantico preservado

    def test_long_name_preserves_extension(self):
        long_name = "a" * 200 + ".jpg"
        result = sanitize_filename(long_name)
        assert result.endswith(".jpg"), f"extensao perdida: {result}"
        assert len(result) <= 100

    def test_null_byte_stripped(self):
        result = sanitize_filename("\x00evil.jpg")
        assert "evil" in result
        assert result.endswith(".jpg")

    def test_special_chars_replaced(self):
        result = sanitize_filename("arte espaco & simbolo.png")
        assert " " not in result
        assert "&" not in result
        assert result.endswith(".png")

    def test_hidden_file_style_gets_fallback_stem(self):
        # ".hidden" -> stem vazio apos strip, fallback para "arquivo"
        result = sanitize_filename(".hidden")
        assert "arquivo" in result or "hidden" in result


# ─── Wave 2 — configuracao.py ───────────────────────────────────────────────


class TestValidarTemplateEtiquetaNomeWhitelist:
    """M3 — whitelist do campo `nome` do template."""

    BASE = {
        "nome": "padrao",
        "formato": "A4",
        "logo_enabled": True,
        "mostrar_data_criacao": False,
    }

    def test_nome_padrao_aceito(self):
        r = validar_template_etiqueta(self.BASE)
        assert r["nome"] == "padrao"

    def test_nome_invalido_rejeitado(self):
        with pytest.raises(ConfiguracaoValidationError, match="nome"):
            validar_template_etiqueta({**self.BASE, "nome": "custom"})

    def test_nome_vazio_rejeitado(self):
        with pytest.raises(ConfiguracaoValidationError):
            validar_template_etiqueta({**self.BASE, "nome": ""})

    def test_nome_script_rejeitado(self):
        """Nao deve aceitar string arbitraria (mitigacao defensiva)."""
        with pytest.raises(ConfiguracaoValidationError):
            validar_template_etiqueta(
                {**self.BASE, "nome": "<script>alert(1)</script>"}
            )

    def test_nome_nao_string_rejeitado(self):
        with pytest.raises(ConfiguracaoValidationError):
            validar_template_etiqueta({**self.BASE, "nome": 123})
