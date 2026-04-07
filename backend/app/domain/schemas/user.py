"""Pydantic v2 schemas for the Users domain."""
import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.db.models import LocalizacaoEnum, SetorEnum

EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class UserCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=150)
    email: str = Field(..., max_length=255)
    senha: str = Field(..., min_length=8, max_length=128)
    setor: SetorEnum
    localizacao: LocalizacaoEnum | None = None
    is_admin: bool = False

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_PATTERN.match(v):
            raise ValueError("Email em formato invalido")
        return v

    @field_validator("senha")
    @classmethod
    def validate_senha(cls, v: str) -> str:
        if not any(c.isalpha() for c in v):
            raise ValueError("Senha deve conter pelo menos 1 letra")
        if not any(c.isdigit() for c in v):
            raise ValueError("Senha deve conter pelo menos 1 numero")
        return v

    @model_validator(mode="after")
    def validate_localizacao_setor(self) -> "UserCreate":
        if self.setor == SetorEnum.VENDEDOR and self.localizacao is None:
            raise ValueError("Vendedor deve ter localizacao (MATRIZ ou FILIAL)")
        if self.setor != SetorEnum.VENDEDOR and self.localizacao is not None:
            raise ValueError("Apenas vendedores podem ter localizacao")
        return self


class UserUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=150)
    setor: SetorEnum | None = None
    localizacao: LocalizacaoEnum | None = None
    is_admin: bool | None = None
    ativo: bool | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    auth_uid: UUID
    nome: str
    email: str
    setor: SetorEnum
    localizacao: LocalizacaoEnum | None
    is_admin: bool
    ativo: bool
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int
    pages: int
