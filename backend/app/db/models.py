"""SQLAlchemy ORM models for domain tables.

These models map to tables created by Alembic migrations.
They do NOT drive auto-generation (target_metadata = None in env.py).
"""
import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, LargeBinary, String, Text, text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
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


class StatusProvaEnum(str, enum.Enum):
    """Estados possiveis de uma prova digital (Secao 5 dos Requisitos).

    Transicoes validas vivem em app/services/state_machine.py (ADR-040).
    """

    CRIADA = "CRIADA"
    RETIRADA_PELO_VENDEDOR = "RETIRADA_PELO_VENDEDOR"
    APROVADA_PELO_VENDEDOR = "APROVADA_PELO_VENDEDOR"
    DE_VOLTA_3STUDIO = "DE_VOLTA_3STUDIO"
    COM_MOTORISTA = "COM_MOTORISTA"
    ENVIADA_PARA_CLICHERIA = "ENVIADA_PARA_CLICHERIA"
    ENCAMINHADA_A_CLICHERIA = "ENCAMINHADA_A_CLICHERIA"
    RECEBIDA_PELA_CLICHERIA = "RECEBIDA_PELA_CLICHERIA"
    REPROVADA_PELO_VENDEDOR = "REPROVADA_PELO_VENDEDOR"
    CANCELADA = "CANCELADA"


class RotaEnum(str, enum.Enum):
    """Rota de encaminhamento (RN-007 v4.0).

    Quatro valores na v4.0 (Wave 2 v4.0 — Componente 06):
      MATRIZ      — vendedor Matriz, sem laminacao.
      LAM_MATRIZ  — vendedor Matriz com etapa de laminacao na Clicheria.
      FILIAL      — vendedor Filial, sem laminacao.
      LAM_FILIAL  — vendedor Filial com etapa de laminacao na Clicheria.

    Os valores PADRAO e DIRETA sao LEGACY da v3.0 e permanecem no enum
    PostgreSQL ate a Wave 7 (Componente 21) fazer o backfill final
    (PADRAO -> MATRIZ, DIRETA -> FILIAL). Sao expostos por
    `ProvaResponse`/`ProvaListItem` para nao quebrar a renderizacao das
    provas v3.0 ate la, mas SAO BLOQUEADOS na criacao via
    `RotaCriacaoEnum` (em `domain/schemas/prova.py`).
    """

    # v4.0 (Wave 2 v4.0 — Componente 06)
    MATRIZ = "MATRIZ"
    LAM_MATRIZ = "LAM_MATRIZ"
    FILIAL = "FILIAL"
    LAM_FILIAL = "LAM_FILIAL"

    # Legacy v3.0 — backfill na Wave 7 (Componente 21)
    PADRAO = "PADRAO"
    DIRETA = "DIRETA"


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


class ProvaDigital(Base):
    """Prova digital (objeto central do sistema — RF-001, RN-001).

    Criada pelo perfil 3Studio com upload da arte (JPG/PNG ate 10MB) para R2.

    Wave 2 v4.0 (Componente 06):
      - `rota` e PERSISTIDA na criacao com a escolha do Administrador
        entre as 4 opcoes da v4.0 (MATRIZ, LAM_MATRIZ, FILIAL, LAM_FILIAL).
        Imutavel apos definicao (RN-002 v4.0) — bloqueado pelo trigger
        `trg_provas_rota_imutavel` (BEFORE UPDATE) e pelo Pydantic.
        Continua NULLABLE no banco APENAS para suportar provas v3.0
        legadas (rota=NULL) ate a Wave 7 (Componente 21) fazer o backfill.
      - `codigo_publico` (NOVO Wave 2 v4.0) e o identificador alfanumerico
        humano-legivel (`PRV-AAAA-MM-NNNNNN`). UNIQUE. Embutido no QR Code
        (DAT v3.0 §8.1: idempotencia camera↔digitacao manual). Usado pelo
        Componente 19 (Wave 3 v4.0) como fallback de scanner.

    `qr_code_hash` continua sendo HMAC-SHA256 opaco (ADR-033) — coexiste
    com `codigo_publico`. Nao confundir: `qr_code_hash` valida autenticidade,
    `codigo_publico` resolve identificacao humana.
    """

    __tablename__ = "provas_digitais"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    nro_requerimento: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    cliente: Mapped[str] = mapped_column(String(200), nullable=False)
    vendedor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False
    )
    imagem_url: Mapped[str] = mapped_column(Text, nullable=False)
    qr_code_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    codigo_publico: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    status: Mapped[StatusProvaEnum] = mapped_column(
        Enum(StatusProvaEnum, name="status_prova_enum", create_type=False),
        nullable=False,
        server_default=text("'CRIADA'"),
    )
    rota: Mapped[RotaEnum | None] = mapped_column(
        Enum(RotaEnum, name="rota_enum", create_type=False), nullable=True
    )
    ciclo_atual: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    motivo_cancelamento: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class Movimentacao(Base):
    """Log IMUTAVEL de transicoes de status (RNF-005).

    Wave 2 NAO escreve aqui — a criacao de prova nao gera movimentacao porque
    criar != transitar (RN-002). A primeira linha nasce na Wave 3 quando o
    vendedor escaneia o QR Code pela primeira vez.

    Modelo criado nesta Wave apenas para estabilizar o contrato ORM e permitir
    que o Componente 08 (detalhe) leia o historico (mesmo que vazio).

    UPDATE/DELETE bloqueados pelo trigger trg_movimentacoes_imutavel.
    """

    __tablename__ = "movimentacoes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    prova_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provas_digitais.id"), nullable=False
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False
    )
    status_anterior: Mapped[StatusProvaEnum] = mapped_column(
        Enum(StatusProvaEnum, name="status_prova_enum", create_type=False),
        nullable=False,
    )
    status_novo: Mapped[StatusProvaEnum] = mapped_column(
        Enum(StatusProvaEnum, name="status_prova_enum", create_type=False),
        nullable=False,
    )
    assinatura_digital: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    motivo_reprovacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    ciclo: Mapped[int] = mapped_column(Integer, nullable=False)
    rota_no_momento: Mapped[RotaEnum | None] = mapped_column(
        Enum(RotaEnum, name="rota_enum", create_type=False), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class Etiqueta(Base):
    """Snapshot imutavel dos dados impressos na etiqueta fisica (RF-003, RN-011).

    Criada junto com a ProvaDigital no mesmo POST. Armazena o QR Code como PNG
    em `qr_code_image` para permitir re-gerar o PDF da etiqueta sem depender do
    hash (que seria um detalhe de implementacao privado do backend).

    UPDATE/DELETE bloqueados pelo trigger trg_etiquetas_imutavel (RNF-005).
    """

    __tablename__ = "etiquetas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    prova_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provas_digitais.id"), nullable=False
    )
    nome_prova: Mapped[str] = mapped_column(String(200), nullable=False)
    nro_requerimento: Mapped[str] = mapped_column(String(50), nullable=False)
    vendedor_nome: Mapped[str] = mapped_column(String(150), nullable=False)
    qr_code_image: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class AuditLog(Base):
    """Log IMUTAVEL de auditoria geral (RNF-005).

    Wave 2 grava aqui na criacao de prova digital e em mudancas de
    configuracao. Waves 3+ gravam em cada transicao de status. Acesso via
    RLS restrito a is_admin = true.

    UPDATE/DELETE bloqueados pelo trigger trg_audit_logs_imutavel.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    prova_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provas_digitais.id"), nullable=True
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False
    )
    acao: Mapped[str] = mapped_column(String(100), nullable=False)
    detalhes_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ConfiguracaoSistema(Base):
    """Parametros configuraveis pelo perfil 3Studio (RF-021).

    Wave 2 usa duas chaves: `tempo_atraso_horas_uteis` (RN-008) e
    `template_etiqueta` (RN-011, estrutura evoluida em migration 009 — ADR-036).
    """

    __tablename__ = "configuracoes_sistema"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    chave: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    valor: Mapped[dict[str, Any] | list[Any] | str | int | float | bool | None] = mapped_column(
        JSONB, nullable=False
    )
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
