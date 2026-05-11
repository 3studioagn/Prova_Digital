"""Schemas Pydantic v2 para o dominio de Provas Digitais (Componente 06)."""
import enum
import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.db.models import LocalizacaoEnum, RotaEnum, SetorEnum, StatusProvaEnum


class RotaCriacaoEnum(str, enum.Enum):
    """Sub-enum de `RotaEnum` aceito apenas no payload de criacao da prova.

    Wave 2 v4.0 (Componente 06): admin escolhe manualmente entre as 4 rotas
    da v4.0. Os valores legacy `PADRAO`/`DIRETA` (Wave 0/v3.0) NAO sao
    aceitos aqui — ja existem provas com esses valores em producao mas
    ninguem mais cria com eles. A Wave 7 (Componente 21) fara o backfill
    final para os 4 novos valores.

    `RotaEnum` (em `app/db/models.py`) continua tendo os 6 valores no
    nivel ORM/banco para suportar leitura das provas legadas.
    """

    MATRIZ = "MATRIZ"
    LAM_MATRIZ = "LAM_MATRIZ"
    FILIAL = "FILIAL"
    LAM_FILIAL = "LAM_FILIAL"

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
    """Payload enviado pelo frontend apos o PUT no R2 ter acontecido.

    Wave 2 v4.0 (Componente 06): adiciona campo `rota` obrigatorio
    (RotaCriacaoEnum — bloqueia legacy v3.0). Removeu `rota_projetada`
    (era derivado da localizacao do vendedor — agora a rota e escolha
    manual do admin).
    """

    nome: str = Field(..., min_length=1, max_length=200)
    nro_requerimento: str = Field(..., min_length=1, max_length=50)
    cliente: str = Field(..., min_length=1, max_length=200)
    vendedor_id: UUID
    rota: RotaCriacaoEnum  # Wave 2 v4.0 — obrigatorio, sem default
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

    Wave 2 v4.0 (Componente 06):
      - `codigo_publico` (NOVO): identificador alfanumerico humano-legivel
        (`PRV-AAAA-MM-NNNNNN`). Sempre presente para provas criadas
        v4.0 + provas v3.0 backfilled pela migration 012.
      - `rota_projetada` REMOVIDO: nao faz mais sentido na v4.0 (a rota
        e escolha manual do admin, nao mais derivada da localizacao do
        vendedor). Frontend deve consumir `prova.rota` diretamente.
      - `rota` continua Optional para suportar provas legadas v3.0 com
        `rota = NULL` (sera backfilled pela Wave 7 / Componente 21).
        Provas legadas tambem podem ter `rota = PADRAO` ou `DIRETA`
        (5 provas em producao no momento da Wave 2 v4.0).

    `vendedor_localizacao` continua sendo exposto como informacao
    AUXILIAR (RN-009 v4.0: "informativa, nao restringe rota").
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    nro_requerimento: str
    codigo_publico: str  # Wave 2 v4.0
    cliente: str
    vendedor_id: UUID
    vendedor_nome: str
    vendedor_localizacao: LocalizacaoEnum | None
    imagem_url: str
    qr_code_hash: str
    status: StatusProvaEnum
    rota: RotaEnum | None
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

    NAO inclui `imagem_url`, `qr_code_hash` nem `motivo_cancelamento` —
    ficam restritos a `ProvaResponse` (detalhe) para reduzir payload e
    evitar vazamento de storage keys em listas publicas.

    Wave 2 v4.0 (Componente 06): incluiu `codigo_publico` para permitir
    busca rapida + display do codigo legivel direto na listagem.

    `vendedor_nome` vem via JOIN no endpoint — nao existe em ProvaDigital.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    nro_requerimento: str
    codigo_publico: str  # Wave 2 v4.0
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


# ─── Scan + Transicao (Componentes 10 e 11 — Wave 3 Lote A) ──────────────
#
# O payload do QR Code tem formato fixo definido em `qrcode_service.py`:
#   "3SD|{nro_requerimento}|{hash_truncado}"
# onde `hash_truncado = qr_code_hash_completo[:16]` (16 chars hex).
#
# `validar_payload_qr` (ja existente desde Wave 2) faz a comparacao
# constant-time do hash. Aqui no schema validamos apenas o formato
# estrutural (prefixo + separadores + 3 partes) — a verificacao real
# contra o hash armazenado acontece no handler depois do SELECT por
# nro_requerimento.


class ScanRequest(BaseModel):
    """Payload recebido de `POST /api/v1/provas/scan` (Componente 10 v4.0).

    Aceita **EXATAMENTE UM** dos 2 caminhos de identificacao:

      1. `payload`: string completa do QR Code (ex: `3SD|PRV-...|hash[:16]`).
         Caminho da camera (Componente 10 v4.0).
      2. `codigo`: codigo publico legivel (ex: `PRV-2026-05-K3T9XB`).
         Caminho da digitacao manual (Componente 19 — fallback).

    Wave 3 v4.0 (Componente 10): a Wave 2 v4.0 / ADR-116 introduziu o
    `codigo_publico` como segundo campo do payload do QR. Esta sessao
    estende `ScanRequest` para aceitar tanto o `payload` completo quanto
    o `codigo` isolado, preparando o contrato compartilhado camera ↔
    digitacao manual exigido por DAT v3.0 §8.1 (idempotencia).

    Validacao:
      - Pydantic verifica formato estrutural do `payload` quando presente.
      - Pydantic verifica `codigo` nao-vazio quando presente.
      - `model_validator` exige XOR (exatamente um dos dois).
      - Verificacao final do hash (caminho `payload`) acontece no handler
        via `qrcode_service.validar_payload_qr` (constant-time).
      - Validacao do formato do `codigo` (regex `PRV-AAAA-MM-NNNNNN`)
        acontece no handler via `validar_formato_codigo_publico` apos
        SELECT, mesma estrategia que o hash do payload — evita timing
        attacks que distinguam "formato invalido" de "fora do scope".

    A camada de servico do frontend (`identificarProvaPorPayload` ou
    `identificarProvaPorCodigo`) escolhe qual campo enviar.
    """

    payload: str | None = Field(None, min_length=1, max_length=256)
    # AUD-W3C10-012: max_length=32 (era 64). Formato canonico
    # PRV-AAAA-MM-NNNNNN tem 18 chars; folga ate 32 cobre typos sem
    # inflar superficie de ataque. Codigos com mais de 32 chars retornam
    # 422 Pydantic; codigos <= 32 mas formato invalido caem em
    # validar_formato_codigo_publico no handler e retornam 404 generico
    # (DAT §8.2 — protecao contra enumeracao preservada para a faixa
    # plausivel de input).
    codigo: str | None = Field(None, min_length=1, max_length=32)

    @field_validator("payload")
    @classmethod
    def _valida_payload(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("Payload vazio")
        # Import local para evitar ciclo (qrcode_service nao importa schemas).
        from app.services.qrcode_service import (
            HASH_TRUNCADO_LEN,
            QR_PAYLOAD_PREFIX,
            QR_PAYLOAD_SEPARATOR,
        )

        prefixo_esperado = f"{QR_PAYLOAD_PREFIX}{QR_PAYLOAD_SEPARATOR}"
        if not v.startswith(prefixo_esperado):
            raise ValueError(
                f"Formato de QR Code invalido "
                f"(esperado prefixo '{QR_PAYLOAD_PREFIX}')"
            )
        parts = v.split(QR_PAYLOAD_SEPARATOR)
        if len(parts) != 3:
            raise ValueError(
                "QR Code mal formado (esperado 3 campos separados por '|')"
            )
        _prefix, identificador, hash_trunc = parts
        if not identificador.strip():
            raise ValueError("Identificador vazio no QR Code")
        if len(hash_trunc) != HASH_TRUNCADO_LEN:
            raise ValueError(
                f"Hash truncado com tamanho invalido "
                f"(esperado {HASH_TRUNCADO_LEN} chars)"
            )
        return v

    @field_validator("codigo")
    @classmethod
    def _valida_codigo(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("Codigo vazio")
        return v

    @model_validator(mode="after")
    def _exige_exatamente_um(self) -> "ScanRequest":
        """Wave 3 v4.0: exige XOR entre `payload` (camera) e `codigo` (manual).

        Aceitar ambos seria ambiguo (qual o campo autoritativo?). Aceitar
        nenhum nao identifica nada. A camera SO envia `payload`; a
        digitacao manual SO envia `codigo`. O handler decide o lookup
        com base em qual campo veio preenchido.
        """
        tem_payload = self.payload is not None
        tem_codigo = self.codigo is not None
        if tem_payload == tem_codigo:
            raise ValueError(
                "Forneca exatamente um de: 'payload' (camera) ou 'codigo' "
                "(digitacao manual)."
            )
        return self


class ScanResponse(BaseModel):
    """Resposta de `POST /api/v1/provas/scan`.

    Contem:
      - `prova`: dados completos da prova (mesmo schema do detalhe).
      - `transicoes_permitidas`: lista de estados destino validos PARA
        ESTE usuario corrente executar a partir do status atual da prova.
        Calculada via iteracao sobre `TRANSICOES[prova.status]` +
        `validar_transicao` (captura exceptions) + aplicacao da regra extra
        de rota por localizacao em `APROVADA_PELO_VENDEDOR -> *`.
      - `motivo_obrigatorio_em`: subset de `transicoes_permitidas` onde o
        usuario deve informar motivo no submit da transicao (apenas
        REPROVADA_PELO_VENDEDOR na Wave 3 Lote A — RF-007).

    Se a prova esta em estado terminal (CANCELADA, RECEBIDA_PELA_CLICHERIA)
    ou o usuario nao tem permissao para nenhuma transicao do estado atual,
    `transicoes_permitidas` retorna `[]` e o frontend exibe mensagem
    "Voce nao tem permissao para movimentar esta prova no estado atual".
    """

    prova: ProvaResponse
    transicoes_permitidas: list[StatusProvaEnum]
    motivo_obrigatorio_em: list[StatusProvaEnum]


# ─── Transicao (Componente 11 — Wave 3 Lote A sub-bloco A.4) ─────────────
#
# Limite do base64 da assinatura: ~700 KB ≈ 500 KB de PNG decodificado
# (base64 adiciona ~33% de overhead). Generoso para um signature-pad
# tipico em celular (stroke medio gera 30-100 KB). Se device de alto DPI
# com stroke grosso estourar, o frontend deve comprimir via
# `toDataURL("image/png")` em canvas menor antes de enviar.
ASSINATURA_BASE64_MAX_BYTES = 700_000


class TransicaoRequest(BaseModel):
    """Payload de `POST /api/v1/provas/{prova_id}/transicoes` (Componente 11).

    Enviado pelo frontend `/escanear` apos o usuario escolher uma das
    `transicoes_permitidas` retornadas pelo `/scan` e assinar no canvas.

    Campos:
      - `status_novo`: destino da transicao. Rejeita `CANCELADA` e `CRIADA`
        via validator — sao ganchos para os endpoints admin dedicados dos
        Componentes 13 (cancelamento) e 14 (reinicio de ciclo). Ver
        `state_machine.executar_transicao` que suporta ambos, apenas este
        endpoint nao os expoe.
      - `assinatura_base64`: PNG do canvas do `react-signature-canvas`
        codificado em base64 (sem o prefixo `data:image/png;base64,` — o
        frontend deve fazer `toDataURL("image/png").split(",")[1]`).
      - `motivo_reprovacao`: obrigatorio sse `status_novo =
        REPROVADA_PELO_VENDEDOR` (RF-007). A validacao cruzada motivo x
        destino e feita no handler, nao aqui, porque envolve dois campos
        e fica mais coeso junto do try/except de dominio.
    """

    status_novo: StatusProvaEnum
    assinatura_base64: str = Field(
        ..., min_length=1, max_length=ASSINATURA_BASE64_MAX_BYTES
    )
    motivo_reprovacao: str | None = Field(None, max_length=1000)

    @field_validator("status_novo")
    @classmethod
    def _rejeita_cancelada_e_criada(
        cls, v: StatusProvaEnum
    ) -> StatusProvaEnum:
        if v == StatusProvaEnum.CANCELADA:
            raise ValueError(
                "Cancelamento nao e permitido por este endpoint "
                "(sera endpoint admin dedicado — Componente 13, Lote C)"
            )
        if v == StatusProvaEnum.CRIADA:
            raise ValueError(
                "Reinicio de ciclo nao e permitido por este endpoint "
                "(sera endpoint admin dedicado — Componente 14, Lote C)"
            )
        return v

    @field_validator("motivo_reprovacao")
    @classmethod
    def _strip_motivo(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None  # string so de whitespace vira None


class TransicaoResponse(BaseModel):
    """Resposta de `POST /api/v1/provas/{prova_id}/transicoes`.

    Retornada com HTTP 201 apos a transicao ser efetivada e commitada.
    Contem:
      - `prova`: dados completos da prova com o NOVO status/rota/ciclo
        aplicados.
      - `movimentacao`: a linha recem-inserida em `movimentacoes`, com
        todos os campos populados (exceto `assinatura_digital` que fica
        server-side, conforme `MovimentacaoResponse`).

    O frontend usa a `movimentacao` para atualizar a timeline localmente
    sem precisar fazer refetch, e a `prova` para atualizar o card da tela
    atual.
    """

    prova: ProvaResponse
    movimentacao: MovimentacaoResponse


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


# ─── Cancelamento + Reinicio de Ciclo (Componentes 13 e 14 — Wave 3 Lote C) ─


class CancelarRequest(BaseModel):
    """Payload de POST /api/v1/provas/{id}/cancelar (Componente 13).

    Apenas o motivo e obrigatorio (RF-010). A assinatura e gerada como
    marcador administrativo pelo endpoint — sem canvas de assinatura.
    """

    motivo_cancelamento: str = Field(
        ..., min_length=1, max_length=500, description="Motivo do cancelamento (RF-010)"
    )

    @field_validator("motivo_cancelamento")
    @classmethod
    def _strip_motivo(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Motivo do cancelamento nao pode ser vazio")
        return v
