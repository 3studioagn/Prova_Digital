"""SQLAlchemy ORM models for domain tables.

These models map to tables created by Alembic migrations.
They do NOT drive auto-generation (target_metadata = None in env.py).
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SetorEnum(str, enum.Enum):
    STUDIO = "STUDIO"
    VENDEDOR = "VENDEDOR"
    MOTORISTA = "MOTORISTA"
    CLICHERIA = "CLICHERIA"


class LocalizacaoEnum(str, enum.Enum):
    MATRIZ = "MATRIZ"
    FILIAL = "FILIAL"


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    auth_uid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False
    )
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    setor: Mapped[SetorEnum] = mapped_column(
        Enum(SetorEnum, name="setor_enum", create_type=False), nullable=False
    )
    localizacao: Mapped[LocalizacaoEnum | None] = mapped_column(
        Enum(LocalizacaoEnum, name="localizacao_enum", create_type=False), nullable=True
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    ativo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True
    )
