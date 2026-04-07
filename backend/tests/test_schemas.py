"""Unit tests for Pydantic schemas (domain/schemas/user.py)."""
import pytest
from pydantic import ValidationError

from app.db.models import LocalizacaoEnum, SetorEnum
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
