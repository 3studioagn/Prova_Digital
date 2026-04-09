"""Schemas Pydantic v2 para o dominio de Provas Digitais (Componente 06)."""
import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models import LocalizacaoEnum, RotaEnum, SetorEnum, StatusProvaEnum

# ─── MIME types aceitos na Wave 2 ─────────────────────────────────────────
# RF-001: arquivo deve ser JPG ou PNG, maximo 10 MB.
ALLOWED_CONTENT_TYPES = frozenset({"image/jpeg", "image/png"})
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

# Regex para sanitizar filename — permite letras, digitos, ponto, hifen, underscore.
# Qualquer outro caractere vira `_` antes de entrar no object key do R2.
FILENAME_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]")

# Formato do numero de requerimento: livre, apenas tamanho + charset basico.
NRO_REQ_RE = re.compile(r"^[A-Za-z0-9._\-/ ]+$")


def _normalize_nro_requerimento(v: str) -> str:
    """Normaliza o numero de requerimento: strip + uppercase.

    Por que uppercase: o constraint UNIQUE em `provas_digitais.nro_requerimento`
    e case-sensitive no Postgres. Sem normalizacao, `REQ-001` e `req-001`
    passariam como linhas distintas — operacionalmente eh bug, numero de
    requerimento eh identificador humano case-insensitive.

    Validacao de charset permanece em NRO_REQ_RE; qualquer caractere fora do
    conjunto permitido (letras, digitos, `. _ - /` e espaco) dispara ValueError.
    """
    v = v.strip().upper()
    if not v:
        raise ValueError("Numero de requerimento nao pode ser vazio")
    if not NRO_REQ_RE.match(v):
        raise ValueError(
            "Numero de requerimento aceita apenas letras, digitos, espaco e . _ - /"
        )
    return v


# ─── Step 1: solicitar URL pre-assinada ──────────────────────────────────


class UploadUrlRequest(BaseModel):
    """Pedido do frontend para obter a URL pre-assinada de upload."""

    nro_requerimento: str = Field(..., min_length=1, max_length=50)
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., max_length=100)

    @field_validator("nro_requerimento")
    @classmethod
    def _valida_nro_req(cls, v: str) -> str:
        return _normalize_nro_requerimento(v)

    @field_validator("content_type")
    @classmethod
    def _valida_content_type(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ALLOWED_CONTENT_TYPES:
            raise ValueError(
                f"Tipo de arquivo nao permitido: {v}. "
                f"Aceitos: {sorted(ALLOWED_CONTENT_TYPES)}"
            )
        return v

    @field_validator("filename")
    @classmethod
    def _valida_filename(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nome do arquivo nao pode ser vazio")
        return v


class UploadUrlResponse(BaseModel):
    """Resposta com a URL pre-assinada que o frontend usa no PUT direto."""

    upload_url: str
    object_key: str
    expires_at: datetime
    max_bytes: int = MAX_UPLOAD_BYTES


# ─── Step 2: criar a prova apos upload ───────────────────────────────────


class ProvaCreateRequest(BaseModel):
    """Payload enviado pelo frontend apos o PUT no R2 ter acontecido."""

    nome: str = Field(..., min_length=1, max_length=200)
    nro_requerimento: str = Field(..., min_length=1, max_length=50)
    cliente: str = Field(..., min_length=1, max_length=200)
    vendedor_id: UUID
    object_key: str = Field(..., min_length=1, max_length=500)

    @field_validator("nome", "cliente")
    @classmethod
    def _strip_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Campo nao pode ser vazio")
        return v

    @field_validator("nro_requerimento")
    @classmethod
    def _valida_nro_req(cls, v: str) -> str:
        return _normalize_nro_requerimento(v)

    @field_validator("object_key")
    @classmethod
    def _valida_object_key(cls, v: str) -> str:
        v = v.strip()
        # O object_key e sempre gerado pelo backend em /upload-url no formato
        # "provas/{uuid}/{filename}". Rejeitamos qualquer coisa que nao comece
        # com "provas/" para evitar path traversal ou referencia a objetos
        # fora da pasta do dominio.
        if not v.startswith("provas/"):
            raise ValueError("object_key invalido (deve comecar com 'provas/')")
        if ".." in v:
            raise ValueError("object_key nao pode conter '..'")
        return v


class ProvaResponse(BaseModel):
    """Representacao publica de uma prova digital.

    `rota_projetada` e Optional desde o Componente 08 (Wave 2): no POST
    /provas/ ela sempre vem populada (o endpoint valida vendedor), mas no
    GET /{id} pode ser None em edge cases — por exemplo, se o vendedor
    original foi desativado ou mudou de setor depois da criacao da prova.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    nro_requerimento: str
    cliente: str
    vendedor_id: UUID
    vendedor_nome: str
    vendedor_localizacao: LocalizacaoEnum | None
    imagem_url: str
    qr_code_hash: str
    status: StatusProvaEnum
    rota: RotaEnum | None
    rota_projetada: RotaEnum | None
    ciclo_atual: int
    motivo_cancelamento: str | None
    created_at: datetime
    updated_at: datetime


class ProvaCreateResponse(BaseModel):
    """Resposta do POST /api/v1/provas/ — inclui o PDF da etiqueta em base64."""

    prova: ProvaResponse
    etiqueta_pdf_base64: str
    qr_code_payload: str


# ─── Listagem (Componente 07) ────────────────────────────────────────────


class ProvaListItem(BaseModel):
    """Item slim da listagem paginada de provas.

    NAO inclui `imagem_url`, `qr_code_hash`, `rota_projetada` nem
    `motivo_cancelamento`. Esses campos ficam restritos a ProvaResponse
    (detalhe, Componente 08) para reduzir payload e evitar vazamento de
    storage keys em listas publicas.

    `vendedor_nome` vem via JOIN no endpoint — nao existe em ProvaDigital.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    nro_requerimento: str
    cliente: str
    vendedor_id: UUID
    vendedor_nome: str
    status: StatusProvaEnum
    rota: RotaEnum | None
    ciclo_atual: int
    created_at: datetime
    updated_at: datetime


class ProvaListResponse(BaseModel):
    """Resposta paginada (mesmo shape de UserListResponse — ADR-037)."""

    items: list[ProvaListItem]
    total: int
    page: int
    page_size: int
    pages: int


# ─── Detalhe (Componente 08) ────────────────────────────────────────────


class MovimentacaoResponse(BaseModel):
    """Item da timeline de movimentacoes de uma prova.

    Contrato pronto desde a Wave 2 (Componente 08) mas so populado de
    verdade na Wave 3 quando transicoes de status comecarem a acontecer.
    `usuario_nome` e `usuario_setor` vem via JOIN com `usuarios`.
    `assinatura_digital` NAO e exposta na API — fica como prova server-side
    apenas.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    prova_id: UUID
    usuario_id: UUID
    usuario_nome: str
    usuario_setor: SetorEnum
    status_anterior: StatusProvaEnum
    status_novo: StatusProvaEnum
    motivo_reprovacao: str | None
    ciclo: int
    rota_no_momento: RotaEnum | None
    created_at: datetime


class MovimentacaoListResponse(BaseModel):
    """Lista do historico de movimentacoes de uma prova.

    Na Wave 2 retorna sempre `items=[]` porque nenhuma prova teve
    transicao ainda. Wave 3 popula sem mudanca de contrato.
    """

    items: list[MovimentacaoResponse]
    total: int


class ImagemUrlResponse(BaseModel):
    """Resposta do endpoint que gera uma URL assinada GET para a arte no R2.

    TTL fixo de 15 minutos (ADR-050). Se expirar antes do usuario recarregar,
    o frontend trata o erro do <img> onError com mensagem amigavel.
    """

    url: str
    expires_at: datetime


# ─── Helpers publicos ────────────────────────────────────────────────────


def sanitize_filename(filename: str) -> str:
    """Substitui qualquer caractere fora de [A-Za-z0-9._-] por underscore.

    Preserva a extensao quando possivel, mesmo apos truncar para 100 chars.
    Remove pontos penduras no inicio/fim do stem para evitar nomes patologicos
    tipo `"...\"` (stem so-de-pontos).

    Examples:
        >>> sanitize_filename("arte.jpg")
        'arte.jpg'
        >>> sanitize_filename("../etc/passwd")
        '_etc_passwd'
        >>> sanitize_filename("a" * 200 + ".jpg")  # truncado mas preserva .jpg
        'aaaa...a.jpg'  # (96 chars no stem + '.jpg')
        >>> sanitize_filename("...")
        'arquivo'
    """
    cleaned = FILENAME_SAFE_RE.sub("_", filename.strip())
    if not cleaned:
        return "arquivo"

    # Separa stem e extensao (ultima ocorrencia de `.`).
    if "." in cleaned:
        stem, _, ext = cleaned.rpartition(".")
    else:
        stem, ext = cleaned, ""

    # Remove pontos soltos no inicio/fim do stem — evita nomes tipo "...".
    stem = stem.strip("._")
    if not stem:
        stem = "arquivo"

    # Sanitiza a extensao: se depois de limpar pontos sobrou so lixo, descarta.
    ext = ext.strip("._")

    # Trunca mantendo a extensao dentro do limite total de 100 chars.
    max_total = 100
    if ext:
        # reserva 1 char para o `.` + tamanho da extensao
        max_stem = max(1, max_total - len(ext) - 1)
        stem = stem[:max_stem]
        return f"{stem}.{ext}"
    return stem[:max_total]
