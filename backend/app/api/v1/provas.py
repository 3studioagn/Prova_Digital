"""Router de Provas Digitais — Componente 06 do Backlog.

Endpoints:
  - POST /api/v1/provas/upload-url  -> UploadUrlResponse
  - POST /api/v1/provas/            -> ProvaCreateResponse (201)

Fluxo completo de criacao (ADR-031 — upload direto frontend -> R2):

  1. Frontend chama POST /upload-url com (nro_requerimento, filename, content_type)
  2. Backend valida unicidade do nro_requerimento e content_type, gera object_key
     determinstico e retorna presigned URL com TTL 15min
  3. Frontend faz PUT direto no R2 usando a URL pre-assinada
  4. Frontend chama POST /provas/ com (nome, nro_requerimento, cliente,
     vendedor_id, object_key)
  5. Backend:
     a. Re-valida nro_requerimento unico (race window entre steps 1 e 4)
     b. Carrega vendedor (FOR UPDATE) e valida setor + ativo + localizacao
     c. HeadObject no R2 para confirmar upload + validar ContentLength <= 10MB
     d. Range GET 16 bytes para validar magic bytes (JPG/PNG) — ADR-032
     e. Gera UUID da prova no backend (para incluir no HMAC antes do INSERT)
     f. Gera qr_code_hash via HMAC-SHA256 (ADR-033)
     g. Renderiza PNG do QR Code (ADR-034)
     h. Determina rota projetada via state_machine (RN-007, Wave 2 nao persiste)
     i. INSERT em provas_digitais (rota=NULL) + etiquetas + audit_logs na mesma
        transacao
     j. Le template_etiqueta atual de configuracoes_sistema
     k. Renderiza PDF da etiqueta via etiqueta_service (ADR-035)
     l. Retorna 201 com prova + PDF base64

  Se qualquer passo entre (b) e (i) falhar apos o upload ter acontecido no R2,
  o backend chama r2_delete(object_key) best-effort para nao deixar orfao
  (ADR-041). Falha de cleanup loga "drift manual" para investigacao futura.
"""
import base64
import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from botocore.exceptions import ClientError
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    status,
)
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user, get_current_user
from app.core.r2 import r2_delete
from app.db.models import (
    AuditLog,  # noqa: F401
    ConfiguracaoSistema,
    Etiqueta,
    LocalizacaoEnum,
    Movimentacao,
    ProvaDigital,
    RotaEnum,
    SetorEnum,
    StatusProvaEnum,
    Usuario,
)
from app.db.session import get_db
from app.domain.schemas.prova import (
    ALLOWED_CONTENT_TYPES,
    MAX_UPLOAD_BYTES,
    CancelarRequest,
    ImagemUrlResponse,
    MovimentacaoListResponse,
    MovimentacaoResponse,
    ProvaCreateRequest,
    ProvaCreateResponse,
    ProvaListItem,
    ProvaListResponse,
    ProvaResponse,
    ScanRequest,
    ScanResponse,
    TransicaoRequest,
    TransicaoResponse,
    UploadUrlRequest,
    UploadUrlResponse,
    sanitize_filename,
)
from app.services import qrcode_service, r2_signed
from app.services.audit_service import log_audit
from app.services.etiqueta_service import TEMPLATE_PADRAO, gerar_pdf
from app.services.state_machine import (
    TRANSICOES,
    AtorNaoAutorizadoError,
    RotaIndeterminavelError,
    TransicaoInvalidaError,
    determinar_rota,
    executar_transicao,
    pode_cancelar,
    validar_transicao,
)

logger = logging.getLogger(__name__)
router = APIRouter()


PRESIGNED_URL_TTL_SECONDS = 900  # 15 minutos (DAT: URLs assinadas com TTL curto)

# F25 (auditoria externa): filtros de data da listagem sao interpretados no
# fuso horario da 3Studio (America/Sao_Paulo = UTC-3 fixo). Sem isso, uma
# prova criada em 2026-04-09 23:30 BRT (= 2026-04-10 02:30 UTC) nao aparece
# no filtro `periodo_inicio=2026-04-09 & periodo_fim=2026-04-09` porque a
# query usaria `created_at >= 2026-04-09 00:00 UTC` e `< 2026-04-10 00:00
# UTC` — a prova esta em 2026-04-10 UTC. Convertendo o input do usuario
# para UTC antes de filtrar, o comportamento passa a bater com o que o
# usuario ve na coluna "Criada em" da tabela.
#
# Usamos offset fixo -3 em vez de `zoneinfo.ZoneInfo("America/Sao_Paulo")`
# porque (a) o Brasil nao tem DST desde 2019 e a aplicacao so lida com datas
# atuais/futuras, e (b) `zoneinfo` no Windows precisa do pacote `tzdata`
# como dependencia extra, o que evitamos. Se eventualmente for necessario
# lidar com datas historicas pre-2019, trocar por ZoneInfo + tzdata.
BRT_TIMEZONE = timezone(timedelta(hours=-3))

# Magic bytes reconhecidos (ADR-032).
MAGIC_BYTES = {
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
}


def _detect_mime_from_bytes(head: bytes) -> str | None:
    """Inspeciona os primeiros bytes e retorna o MIME detectado ou None."""
    for mime, signature in MAGIC_BYTES.items():
        if head.startswith(signature):
            return mime
    return None


async def _cleanup_r2(object_key: str) -> None:
    """Best-effort delete de object_key no R2. Loga se falhar (ADR-041)."""
    try:
        await r2_delete(object_key)
        logger.info("R2 cleanup OK: %s", object_key)
    except Exception:
        logger.exception(
            "R2 cleanup FALHOU para %s — orfao possivel, investigar", object_key
        )


def parse_prova_id(
    prova_id: str = Path(..., description="UUID da prova digital"),
) -> uuid.UUID:
    """Converte o `prova_id` do path para UUID, retornando 404 se invalido.

    C08 M3 (auditoria externa Wave 2): antes, o FastAPI tipava o path como
    `uuid.UUID` diretamente, o que fazia o Pydantic retornar 422 com mensagem
    verbose do validator ("invalid character: expected an optional prefix of
    `urn:uuid:`...") quando um usuario digitava URL manualmente (ex:
    `/provas/abc123`). A mensagem vaza detalhes internos do validator e e
    inconsistente com o 404 retornado quando um UUID valido aponta para uma
    prova inexistente ou escondida por scoping.

    Esta dependency normaliza o comportamento: qualquer ID nao-UUID vira
    404 "Prova nao encontrada", igual ao caso de prova ausente. O openapi
    schema continua documentando o path como string simples (`{prova_id}`)
    — quem consumir o OpenAPI ve um 404 coerente.
    """
    try:
        return uuid.UUID(prova_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prova nao encontrada",
        )


# ───────────────────────────────────────────────────────────────────────
# POST /api/v1/provas/upload-url
# ───────────────────────────────────────────────────────────────────────


@router.post("/upload-url", response_model=UploadUrlResponse)
async def create_upload_url(
    body: UploadUrlRequest,
    db: AsyncSession = Depends(get_db),
    admin: Usuario = Depends(get_admin_user),
) -> UploadUrlResponse:
    """Gera uma URL pre-assinada para o frontend fazer PUT direto no R2.

    Valida unicidade do `nro_requerimento` em `public.provas_digitais` (racing
    entre cliques de "Criar Prova" no frontend) e MIME aceito (`image/jpeg` ou
    `image/png`).
    """
    # Unicidade do nro_requerimento — tambem re-validada em POST /
    existing = await db.execute(
        select(ProvaDigital.id).where(
            ProvaDigital.nro_requerimento == body.nro_requerimento
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Numero de requerimento ja cadastrado",
        )

    # Gera object_key particionado por ano/mes — facilita listagem/cleanup futuro.
    now = datetime.now(tz=timezone.utc)
    object_uuid = uuid.uuid4().hex
    safe_filename = sanitize_filename(body.filename)
    object_key = f"provas/{now.year:04d}/{now.month:02d}/{object_uuid}/{safe_filename}"

    try:
        upload_url = await r2_signed.generate_presigned_upload_url(
            key=object_key,
            content_type=body.content_type,
            expires_in=PRESIGNED_URL_TTL_SECONDS,
        )
    except Exception:
        logger.exception("Falha ao gerar presigned URL para %s", object_key)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao preparar upload",
        )

    expires_at = now + timedelta(seconds=PRESIGNED_URL_TTL_SECONDS)
    logger.info(
        "Presigned upload URL criada: admin=%s nro_req=%s key=%s",
        admin.id,
        body.nro_requerimento,
        object_key,
    )
    return UploadUrlResponse(
        upload_url=upload_url,
        object_key=object_key,
        expires_at=expires_at,
        max_bytes=MAX_UPLOAD_BYTES,
    )


# ───────────────────────────────────────────────────────────────────────
# POST /api/v1/provas/
# ───────────────────────────────────────────────────────────────────────


async def _carregar_vendedor(db: AsyncSession, vendedor_id) -> Usuario:
    """Carrega o vendedor validando setor, ativo e localizacao."""
    result = await db.execute(
        select(Usuario).where(Usuario.id == vendedor_id).with_for_update()
    )
    vendedor = result.scalar_one_or_none()
    if vendedor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendedor nao encontrado",
        )
    if not vendedor.ativo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Vendedor esta inativo",
        )
    if vendedor.setor != SetorEnum.VENDEDOR:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Usuario informado nao e do setor VENDEDOR",
        )
    if vendedor.localizacao is None:
        # Protegido por CHECK constraint tambem, mas garantimos antes de
        # chamar determinar_rota para dar mensagem mais clara.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Vendedor nao tem localizacao (Matriz ou Filial) cadastrada",
        )
    return vendedor


async def _validar_upload_no_r2(object_key: str) -> None:
    """Confirma HeadObject + ContentLength + magic bytes.

    A validacao de magic bytes (ADR-032) e a unica barreira contra upload
    com content-type spoofado — o `content_type` declarado no step 1
    (/upload-url) nao e persistido entre requests, entao aqui so olhamos
    o conteudo real do arquivo no R2.

    Pos-ADR-057: esta funcao nao retorna mais o MIME detectado porque
    nenhum caller usava o valor. A validacao em si continua igual — se
    os magic bytes nao baterem com JPG ou PNG, levanta 422 e o caller
    limpa o R2.

    Raises HTTPException se qualquer validacao falhar.
    """
    # HeadObject
    try:
        head = await r2_signed.head_object(object_key)
    except ClientError as exc:
        code = r2_signed.extract_error_code(exc)
        if code in ("404", "NoSuchKey", "NotFound"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arquivo nao encontrado no storage (upload nao completou)",
            )
        logger.exception("Falha no HeadObject R2 para %s", object_key)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao validar arquivo no storage",
        )

    content_length = int(head.get("ContentLength", 0))
    if content_length == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Arquivo vazio",
        )
    if content_length > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Arquivo excede o limite de {MAX_UPLOAD_BYTES // (1024 * 1024)} MB",
        )

    # Magic bytes (ADR-032) — nao confiar no ContentType do header.
    try:
        head_bytes = await r2_signed.get_object_head_bytes(object_key, n=16)
    except ClientError:
        logger.exception("Falha no Range GET para magic bytes: %s", object_key)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao validar conteudo do arquivo",
        )

    detected_mime = _detect_mime_from_bytes(head_bytes)
    if detected_mime is None or detected_mime not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Arquivo nao e JPG ou PNG valido (magic bytes)",
        )


async def _carregar_template_etiqueta(db: AsyncSession) -> dict:
    """Le o template atual de configuracoes_sistema. Fallback para padrao."""
    result = await db.execute(
        select(ConfiguracaoSistema.valor).where(
            ConfiguracaoSistema.chave == "template_etiqueta"
        )
    )
    valor = result.scalar_one_or_none()
    if not isinstance(valor, dict):
        # Se por qualquer razao o valor ainda for string (migration 009 nao
        # aplicada) ou ausente, usamos o default e logamos.
        logger.warning(
            "template_etiqueta ausente ou em formato legado (type=%s), usando TEMPLATE_PADRAO",
            type(valor).__name__,
        )
        return dict(TEMPLATE_PADRAO)
    return valor


@router.post(
    "/",
    response_model=ProvaCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prova(
    body: ProvaCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: Usuario = Depends(get_admin_user),
) -> ProvaCreateResponse:
    """Cria uma prova digital apos upload confirmado no R2."""
    # (a) Unicidade do nro_requerimento — race window entre /upload-url e aqui.
    existing = await db.execute(
        select(ProvaDigital.id).where(
            ProvaDigital.nro_requerimento == body.nro_requerimento
        )
    )
    if existing.scalar_one_or_none() is not None:
        await _cleanup_r2(body.object_key)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Numero de requerimento ja cadastrado",
        )

    # (b) Vendedor — carrega com FOR UPDATE para travar mudancas concorrentes.
    try:
        vendedor = await _carregar_vendedor(db, body.vendedor_id)
    except HTTPException:
        await _cleanup_r2(body.object_key)
        raise

    # (c, d) Valida upload no R2 — HeadObject + magic bytes.
    try:
        await _validar_upload_no_r2(body.object_key)
    except HTTPException:
        await _cleanup_r2(body.object_key)
        raise

    # (e) Gera UUID da prova no backend para incluir no HMAC antes do INSERT.
    prova_id = uuid.uuid4()

    # (f) Hash HMAC-SHA256 (ADR-033).
    qr_hash = qrcode_service.gerar_hash(prova_id, body.nro_requerimento)

    # (g) Payload escaneavel + PNG do QR Code.
    qr_payload = qrcode_service.gerar_payload_qr(body.nro_requerimento, qr_hash)
    qr_image_bytes = qrcode_service.gerar_imagem_qr(qr_payload, size_px=200)

    # (h) Rota projetada (Wave 2 NAO persiste — RN-007 + ADR-042).
    try:
        rota_projetada = determinar_rota(vendedor)
    except RotaIndeterminavelError as exc:
        await _cleanup_r2(body.object_key)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )

    # (i) Carrega template e gera o PDF ANTES do commit.
    #
    # Por que antes e nao depois:
    #   - gerar_pdf pode lancar (caracteres fora da fonte, template invalido,
    #     fontes faltando no deploy). Fazer isso antes do commit garante que
    #     uma falha de rendering NAO deixa uma prova orfa no banco sem PDF.
    #   - `created_at` renderizado no PDF (template "mostrar_data_criacao")
    #     e gerado no backend via datetime.now(UTC) e depois tambem usado no
    #     response — consistente com o `now()` que o banco vai escrever,
    #     dentro do proprio segundo.
    try:
        template = await _carregar_template_etiqueta(db)
        created_at = datetime.now(tz=timezone.utc)
        pdf_bytes = gerar_pdf(
            nome_prova=body.nome,
            nro_requerimento=body.nro_requerimento,
            vendedor_nome=vendedor.nome,
            qr_image_bytes=qr_image_bytes,
            template=template,
            created_at=created_at,
        )
    except Exception as exc:
        logger.exception(
            "Falha ao gerar PDF da etiqueta para nro_req=%s",
            body.nro_requerimento,
        )
        await _cleanup_r2(body.object_key)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Falha ao gerar etiqueta: {exc}",
        )

    # (j) INSERT atomico de prova + etiqueta + audit_log.
    #
    # IMPORTANTE: sem `relationship()` declarado entre ProvaDigital e Etiqueta,
    # o SQLAlchemy nao detecta a dependencia FK automaticamente e o flush
    # coletivo nao garante que `provas_digitais` seja inserida antes de
    # `etiquetas`. Reproducao do bug em scripts/reproduce_create_prova.py na
    # sessao de debug mostrou que o flush comecou pela etiqueta e violou
    # `etiquetas_prova_id_fkey`. Fix: dois flushes explicitos dentro da mesma
    # transacao — primeiro a prova, depois etiqueta + audit_log. A transacao
    # inteira ainda e atomica (commit/rollback no final).
    nova_prova = ProvaDigital(
        id=prova_id,
        nome=body.nome,
        nro_requerimento=body.nro_requerimento,
        cliente=body.cliente,
        vendedor_id=vendedor.id,
        imagem_url=body.object_key,
        qr_code_hash=qr_hash,
        status=StatusProvaEnum.CRIADA,
        rota=None,  # ADR-042: rota so e definida na aprovacao (Wave 3)
        ciclo_atual=1,
    )

    try:
        db.add(nova_prova)
        await db.flush()  # garante INSERT de provas_digitais ANTES da etiqueta

        nova_etiqueta = Etiqueta(
            prova_id=prova_id,
            nome_prova=body.nome,
            nro_requerimento=body.nro_requerimento,
            vendedor_nome=vendedor.nome,
            qr_code_image=qr_image_bytes,
        )
        db.add(nova_etiqueta)
        await db.flush()  # garante INSERT de etiquetas antes do audit_log

        await log_audit(
            db,
            acao="criar_prova",
            usuario_id=admin.id,
            prova_id=prova_id,
            detalhes={
                "vendedor_id": str(vendedor.id),
                "vendedor_nome": vendedor.nome,
                "nro_requerimento": body.nro_requerimento,
                "cliente": body.cliente,
                "rota_projetada": rota_projetada.value,
                "object_key": body.object_key,
            },
            request=request,
        )

        await db.commit()
    except IntegrityError:
        # A2 (auditoria Wave 2): race entre dois admins criando a mesma prova.
        #
        # Cenario: o check de unicidade do nro_requerimento no inicio do handler
        # (linhas 300-310) roda ANTES do INSERT, entao existe uma janela TOCTOU
        # em que outra requisicao paralela pode criar a mesma prova e commitar
        # primeiro. O constraint UNIQUE no banco detecta o conflito e levanta
        # IntegrityError no commit — mapeamos para 409 Conflict em vez de 500.
        #
        # Outros tipos de IntegrityError (FK quebrada, NOT NULL violado) tambem
        # caem aqui porque estruturalmente estao no mesmo caminho de escrita;
        # a mensagem e generica o suficiente para cobrir todos mas nao vaza
        # detalhes internos de schema.
        await db.rollback()
        logger.warning(
            "IntegrityError ao persistir prova nro_req=%s (provavel race de unicidade). "
            "Limpando R2.",
            body.nro_requerimento,
        )
        await _cleanup_r2(body.object_key)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Numero de requerimento ja cadastrado",
        )
    except Exception:
        # F01 (auditoria externa): DB errors transitorios no commit retornam
        # 502 para alinhar com ADR-074 (C07), ADR-076 (C08) e ADR-078 (C09).
        # 502 expressa "upstream indisponivel, cliente pode retentar com
        # back-off"; 500 seria "bug interno do backend" (nao e o caso aqui).
        await db.rollback()
        logger.exception(
            "Falha ao persistir prova %s (nro_req=%s). Limpando R2.",
            prova_id,
            body.nro_requerimento,
        )
        await _cleanup_r2(body.object_key)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao persistir prova",
        )

    # F02 (auditoria externa): db.refresh esta FORA do try/except do commit.
    # Se refresh falhar (conexao dropa entre commit e refresh, janela rara
    # mas possivel), a prova JA ESTA persistida no DB — retornar 500 para o
    # cliente seria enganoso porque o cliente retentaria e receberia 409 na
    # segunda tentativa. Em vez disso, se o refresh falhar, construimos o
    # response com os valores ja conhecidos em memoria e logamos warning.
    try:
        await db.refresh(nova_prova)
        created_at_response = nova_prova.created_at
        updated_at_response = nova_prova.updated_at
    except Exception:
        logger.warning(
            "db.refresh falhou apos commit da prova %s (nro_req=%s). "
            "Respondendo com dados em memoria. Investigar drift eventual.",
            nova_prova.id,
            nova_prova.nro_requerimento,
        )
        # `created_at` foi gerado no backend antes do INSERT (ver linha do
        # `datetime.now(tz=timezone.utc)` acima). Em `updated_at` usamos o
        # mesmo valor — na Wave 2 nenhum UPDATE subsequente acontece entre
        # INSERT e response.
        created_at_response = created_at
        updated_at_response = created_at

    pdf_base64 = base64.b64encode(pdf_bytes).decode("ascii")

    logger.info(
        "Prova criada: id=%s nro_req=%s vendedor=%s rota_projetada=%s admin=%s",
        nova_prova.id,
        nova_prova.nro_requerimento,
        vendedor.id,
        rota_projetada.value,
        admin.id,
    )

    # Monta o response com vendedor_nome e rota_projetada (nao estao no
    # model ORM, vem do contexto).
    prova_response = ProvaResponse(
        id=nova_prova.id,
        nome=nova_prova.nome,
        nro_requerimento=nova_prova.nro_requerimento,
        cliente=nova_prova.cliente,
        vendedor_id=nova_prova.vendedor_id,
        vendedor_nome=vendedor.nome,
        vendedor_localizacao=vendedor.localizacao,
        imagem_url=nova_prova.imagem_url,
        qr_code_hash=nova_prova.qr_code_hash,
        status=nova_prova.status,
        rota=nova_prova.rota,
        rota_projetada=rota_projetada,
        ciclo_atual=nova_prova.ciclo_atual,
        motivo_cancelamento=nova_prova.motivo_cancelamento,
        created_at=created_at_response,
        updated_at=updated_at_response,
    )

    return ProvaCreateResponse(
        prova=prova_response,
        etiqueta_pdf_base64=pdf_base64,
        qr_code_payload=qr_payload,
    )


# ───────────────────────────────────────────────────────────────────────
# GET /api/v1/provas/  — Listagem com filtros e paginacao (Componente 07)
# ───────────────────────────────────────────────────────────────────────
#
# Autorizacao (ADR-046): `get_current_user` (nao admin-only) + scoping por
# setor replicado no backend. O backend usa service_role (bypassa RLS),
# entao a semantica das policies RLS (pol_provas_select) e espelhada aqui:
#
#   is_admin=true              -> ve todas
#   setor=VENDEDOR             -> vendedor_id == user.id
#   setor=MOTORISTA            -> status == COM_MOTORISTA
#   setor=CLICHERIA            -> status IN (ENVIADA, ENCAMINHADA, RECEBIDA)
#   setor=STUDIO sem is_admin  -> nao retorna nada (combinacao invalida)
#
# Filtros explicitos do usuario sao aplicados em cima do filtro base (AND).


CLICHERIA_STATUSES = (
    StatusProvaEnum.ENVIADA_PARA_CLICHERIA,
    StatusProvaEnum.ENCAMINHADA_A_CLICHERIA,
    StatusProvaEnum.RECEBIDA_PELA_CLICHERIA,
)


# ─── Escape de wildcards para ILIKE (C1 da auditoria Wave 2) ──────────
#
# O ILIKE do Postgres trata `%` (qualquer sequencia) e `_` (1 char) como
# wildcards. Se o usuario digita esses chars nos filtros `busca` ou
# `cliente`, eles sao interpretados como pattern SQL em vez de literais
# — um admin que filtra por "100%" ve resultados errados, e "a_b" casa
# "axb" inesperadamente.
#
# Solucao canonica: escapar `\`, `%` e `_` com um escape char explicito,
# e passar esse mesmo escape char para o `.ilike(..., escape="\\")`. A
# ordem importa — `\` DEVE ser escapado primeiro para nao reescapar os
# chars escapados depois.
ILIKE_ESCAPE_CHAR = "\\"


def _escape_ilike(term: str) -> str:
    """Escapa wildcards (`\\`, `%`, `_`) para uso literal em ILIKE."""
    return (
        term.replace(ILIKE_ESCAPE_CHAR, ILIKE_ESCAPE_CHAR + ILIKE_ESCAPE_CHAR)
        .replace("%", ILIKE_ESCAPE_CHAR + "%")
        .replace("_", ILIKE_ESCAPE_CHAR + "_")
    )


def _scoping_filter(user: Usuario):
    """Retorna a clausula WHERE base que restringe provas por setor.

    Retorna `None` quando nao ha restricao (admin). Retorna uma clausula
    `false` explicita para combinacoes nao suportadas (scoping defensivo).
    """
    if user.is_admin:
        return None
    if user.setor == SetorEnum.VENDEDOR:
        return ProvaDigital.vendedor_id == user.id
    if user.setor == SetorEnum.MOTORISTA:
        return ProvaDigital.status == StatusProvaEnum.COM_MOTORISTA
    if user.setor == SetorEnum.CLICHERIA:
        return ProvaDigital.status.in_(CLICHERIA_STATUSES)
    # STUDIO sem is_admin — combinacao invalida pos-ADR-018.
    # Retorna clausula false para garantir zero resultados.
    return func.false()


@router.get("/", response_model=ProvaListResponse)
async def list_provas(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: StatusProvaEnum | None = Query(None, alias="status"),
    periodo_inicio: date | None = Query(None),
    periodo_fim: date | None = Query(None),
    vendedor_id: uuid.UUID | None = Query(None),
    cliente: str | None = Query(None, max_length=200),
    rota: RotaEnum | None = Query(None),
    busca: str | None = Query(None, max_length=200),
) -> ProvaListResponse:
    """Lista provas digitais com filtros combinaveis e paginacao offset-based.

    Autenticado (qualquer setor/perfil ativo). O scoping por setor e feito
    via `_scoping_filter` — replica a semantica das RLS policies porque o
    backend usa service_role e bypassa RLS. Filtros explicitos sao combinados
    com AND sobre o filtro base.

    Ordenacao: `created_at DESC` (mais recentes primeiro).

    Performance: indexes `idx_provas_status`, `idx_provas_status_created`,
    `idx_provas_vendedor`, `idx_provas_created_at` cobrem os filtros mais
    comuns. ILIKE em `cliente`/`nome`/`nro_requerimento` e seq scan no
    volume Wave 2 — aceitavel (ADR-038). Wildcards sao escapados (C1 da
    auditoria Wave 2 — ver `_escape_ilike`).
    """
    # A3 (auditoria Wave 2): validacao cruzada de periodo.
    # Se o usuario inverter as datas, retornamos 422 em vez de aceitar o
    # filtro e devolver lista vazia silenciosamente (UX confusa).
    if (
        periodo_inicio is not None
        and periodo_fim is not None
        and periodo_fim < periodo_inicio
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Data final do periodo nao pode ser anterior a inicial",
        )

    filters: list = []

    # Filtro base de scoping (ADR-046)
    base = _scoping_filter(current_user)
    if base is not None:
        filters.append(base)

    # Filtros explicitos
    if status_filter is not None:
        filters.append(ProvaDigital.status == status_filter)
    if vendedor_id is not None:
        filters.append(ProvaDigital.vendedor_id == vendedor_id)
    if rota is not None:
        filters.append(ProvaDigital.rota == rota)
    if cliente:
        # C1 (auditoria Wave 2): escape de wildcards antes de concatenar.
        cliente_pattern = f"%{_escape_ilike(cliente)}%"
        filters.append(
            ProvaDigital.cliente.ilike(cliente_pattern, escape=ILIKE_ESCAPE_CHAR)
        )
    if busca:
        # C1 (auditoria Wave 2): escape de wildcards antes de concatenar.
        busca_pattern = f"%{_escape_ilike(busca)}%"
        filters.append(
            or_(
                ProvaDigital.nome.ilike(busca_pattern, escape=ILIKE_ESCAPE_CHAR),
                ProvaDigital.nro_requerimento.ilike(
                    busca_pattern, escape=ILIKE_ESCAPE_CHAR
                ),
            )
        )

    # Periodo (ADR-048): fim inclusivo — adicionamos 1 dia e usamos `<`.
    #
    # F25 (auditoria externa): interpretamos o input do usuario no fuso BRT
    # (America/Sao_Paulo) antes de converter para UTC. Ver comentario em
    # BRT_ZONE acima. Antes desta mudanca, `periodo_inicio=2026-04-09` era
    # tratado como 2026-04-09 00:00 UTC (= 2026-04-08 21:00 BRT), o que
    # confundia o usuario que esperava ver provas criadas no dia 9 BRT.
    if periodo_inicio is not None:
        inicio_dt = datetime(
            periodo_inicio.year, periodo_inicio.month, periodo_inicio.day,
            tzinfo=BRT_TIMEZONE,
        ).astimezone(timezone.utc)
        filters.append(ProvaDigital.created_at >= inicio_dt)
    if periodo_fim is not None:
        fim_dt = (
            datetime(
                periodo_fim.year, periodo_fim.month, periodo_fim.day,
                tzinfo=BRT_TIMEZONE,
            )
            + timedelta(days=1)
        ).astimezone(timezone.utc)
        filters.append(ProvaDigital.created_at < fim_dt)

    # Count total (antes do offset/limit)
    count_stmt = select(func.count()).select_from(ProvaDigital)
    for f in filters:
        count_stmt = count_stmt.where(f)

    # Data query com JOIN em usuarios para trazer vendedor_nome
    data_stmt = (
        select(ProvaDigital, Usuario.nome.label("vendedor_nome"))
        .join(Usuario, Usuario.id == ProvaDigital.vendedor_id)
    )
    for f in filters:
        data_stmt = data_stmt.where(f)

    offset = (page - 1) * page_size
    data_stmt = (
        data_stmt.order_by(ProvaDigital.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    # A2 (auditoria Wave 2): try/except explicito em torno das queries de
    # listagem. Erros transitorios (DB timeout, pooler OFF, connection
    # reset) devolvem 502 com mensagem acionavel em vez de cair no
    # exception handler global do main.py que loga "Erro interno do
    # servidor" sem contexto util.
    try:
        total = (await db.execute(count_stmt)).scalar() or 0
        rows = (await db.execute(data_stmt)).all()
    except Exception:
        logger.exception(
            "Falha ao executar listagem de provas (user=%s, page=%d)",
            current_user.id,
            page,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao carregar provas",
        )

    items = [
        ProvaListItem(
            id=prova.id,
            nome=prova.nome,
            nro_requerimento=prova.nro_requerimento,
            cliente=prova.cliente,
            vendedor_id=prova.vendedor_id,
            vendedor_nome=vendedor_nome,
            status=prova.status,
            rota=prova.rota,
            ciclo_atual=prova.ciclo_atual,
            created_at=prova.created_at,
            updated_at=prova.updated_at,
        )
        for prova, vendedor_nome in rows
    ]

    pages = (total + page_size - 1) // page_size if total > 0 else 0
    return ProvaListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


# ───────────────────────────────────────────────────────────────────────
# GET /api/v1/provas/{prova_id}  — Detalhe (Componente 08)
# ───────────────────────────────────────────────────────────────────────
#
# Todos os endpoints de detalhe reutilizam `_scoping_filter` do Componente 07
# (ADR-049) para garantir visibilidade consistente. Se o scoping esconde a
# prova, retornamos 404 — nao 403 — para nao vazar existencia da prova para
# usuarios que nao deveriam saber dela.


async def _carregar_prova_com_scoping(
    db: AsyncSession,
    prova_id: uuid.UUID,
    user: Usuario,
    *,
    lock: bool = False,
) -> tuple[ProvaDigital, str, LocalizacaoEnum | None, SetorEnum] | None:
    """Carrega a prova + dados do vendedor respeitando o scoping por setor.

    Retorna `(prova, vendedor_nome, vendedor_localizacao, vendedor_setor)` ou
    `None` quando a prova nao existe ou o usuario nao tem permissao de ve-la.

    F05 (auditoria externa Wave 2): o `vendedor_setor` foi adicionado ao JOIN
    para que `get_prova_detail` possa calcular `rota_projetada` sem fazer uma
    segunda query por request. Os outros 4 endpoints de detalhe nao usam
    setor — fazem unpacking com `_` para o 4o elemento.

    Wave 3 Lote A (sub-bloco A.4): adicionado parametro keyword-only `lock`
    (default `False` — zero impacto nos callers de Wave 2). Quando `True`,
    aplica `.with_for_update(of=ProvaDigital)` para serializar transicoes
    concorrentes. Usado exclusivamente pelo handler
    `POST /api/v1/provas/{id}/transicoes` (ADR-084). Sem o lock, dois
    usuarios escaneando a mesma prova simultaneamente poderiam fazer dois
    INSERTs em `movimentacoes` e dois UPDATEs em `provas_digitais.status`,
    corrompendo o historico.
    """
    stmt = (
        select(
            ProvaDigital,
            Usuario.nome.label("vendedor_nome"),
            Usuario.localizacao.label("vendedor_localizacao"),
            Usuario.setor.label("vendedor_setor"),
        )
        .join(Usuario, Usuario.id == ProvaDigital.vendedor_id)
        .where(ProvaDigital.id == prova_id)
    )
    base = _scoping_filter(user)
    if base is not None:
        stmt = stmt.where(base)

    if lock:
        # FOR UPDATE apenas na `provas_digitais`. Nao travamos `usuarios`
        # (o JOIN) porque o vendedor nao precisa ser exclusivo para a
        # transicao — so a prova. Evita contencao cruzada desnecessaria.
        stmt = stmt.with_for_update(of=ProvaDigital)

    row = (await db.execute(stmt)).first()
    if row is None:
        return None
    prova, vendedor_nome, vendedor_localizacao, vendedor_setor = row
    return prova, vendedor_nome, vendedor_localizacao, vendedor_setor


def _determinar_rota_projetada(
    vendedor_setor: SetorEnum, vendedor_localizacao: LocalizacaoEnum | None
) -> RotaEnum | None:
    """Calcula `rota_projetada` a partir do setor e localizacao do vendedor.

    Retorna None em edge cases onde a rota nao pode ser determinada (setor
    != VENDEDOR, localizacao ausente). O frontend trata None exibindo
    apenas `prova.rota` ou placeholder.

    F05 (auditoria externa Wave 2): esta funcao substitui a chamada
    `determinar_rota(vendedor)` que exigia um Usuario completo — agora
    aceita os 2 campos escalares que ja vem no JOIN de
    `_carregar_prova_com_scoping`.
    """
    if vendedor_setor != SetorEnum.VENDEDOR:
        return None
    if vendedor_localizacao is None:
        return None
    if vendedor_localizacao == LocalizacaoEnum.MATRIZ:
        return RotaEnum.PADRAO
    if vendedor_localizacao == LocalizacaoEnum.FILIAL:
        return RotaEnum.DIRETA
    return None


def _build_prova_response(
    prova: ProvaDigital,
    vendedor_nome: str,
    vendedor_localizacao: LocalizacaoEnum | None,
    vendedor_setor: SetorEnum,
) -> ProvaResponse:
    """Monta o ProvaResponse calculando `rota_projetada` quando possivel.

    `rota_projetada` e None em edge cases onde o vendedor nao pode ter rota
    calculada (ex: mudou de setor apos a criacao da prova). O frontend trata
    None exibindo apenas `prova.rota` ou placeholder.
    """
    return ProvaResponse(
        id=prova.id,
        nome=prova.nome,
        nro_requerimento=prova.nro_requerimento,
        cliente=prova.cliente,
        vendedor_id=prova.vendedor_id,
        vendedor_nome=vendedor_nome,
        vendedor_localizacao=vendedor_localizacao,
        imagem_url=prova.imagem_url,
        qr_code_hash=prova.qr_code_hash,
        status=prova.status,
        rota=prova.rota,
        rota_projetada=_determinar_rota_projetada(vendedor_setor, vendedor_localizacao),
        ciclo_atual=prova.ciclo_atual,
        motivo_cancelamento=prova.motivo_cancelamento,
        created_at=prova.created_at,
        updated_at=prova.updated_at,
    )


@router.get("/{prova_id}", response_model=ProvaResponse)
async def get_prova_detail(
    prova_id: uuid.UUID = Depends(parse_prova_id),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> ProvaResponse:
    """Retorna os dados completos de uma prova (autenticado + scoping).

    A1 (auditoria Wave 2 — Sessao 20): envolve as queries em try/except
    para mapear erros transitorios de DB (pooler OFF, connection reset,
    timeout) para 502 com mensagem acionavel em vez do 500 generico do
    exception handler global. HTTPException (ex: 404 do scoping) e
    re-levantada para nao ser mascarada.

    F05 (auditoria externa Wave 2): eliminada a segunda query que buscava
    o objeto Usuario completo so para pegar o `setor` usado em
    `determinar_rota`. Agora o JOIN em `_carregar_prova_com_scoping` ja
    retorna `setor` e `localizacao`, que sao suficientes para calcular
    `rota_projetada` via `_determinar_rota_projetada`.
    """
    try:
        result = await _carregar_prova_com_scoping(db, prova_id, current_user)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prova nao encontrada",
            )
        prova, vendedor_nome, vendedor_localizacao, vendedor_setor = result
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Falha ao carregar detalhe da prova %s (user=%s)",
            prova_id,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao carregar prova",
        )

    return _build_prova_response(
        prova, vendedor_nome, vendedor_localizacao, vendedor_setor
    )


# ───────────────────────────────────────────────────────────────────────
# GET /api/v1/provas/{prova_id}/imagem-url  — Presigned GET URL (ADR-050)
# ───────────────────────────────────────────────────────────────────────


IMAGEM_URL_TTL_SECONDS = 900  # 15 minutos (ADR-050)


@router.get("/{prova_id}/imagem-url", response_model=ImagemUrlResponse)
async def get_imagem_url(
    prova_id: uuid.UUID = Depends(parse_prova_id),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> ImagemUrlResponse:
    """Retorna uma URL assinada GET (TTL 15min) da arte da prova no R2."""
    result = await _carregar_prova_com_scoping(db, prova_id, current_user)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prova nao encontrada",
        )
    prova, _vendedor_nome, _vendedor_localizacao, _vendedor_setor = result

    try:
        url = await r2_signed.generate_presigned_get_url(
            prova.imagem_url, expires_in=IMAGEM_URL_TTL_SECONDS
        )
    except Exception:
        logger.exception(
            "Falha ao gerar presigned GET URL para %s", prova.imagem_url
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao gerar URL da arte",
        )

    expires_at = datetime.now(tz=timezone.utc) + timedelta(
        seconds=IMAGEM_URL_TTL_SECONDS
    )
    return ImagemUrlResponse(url=url, expires_at=expires_at)


# ───────────────────────────────────────────────────────────────────────
# GET /api/v1/provas/{prova_id}/movimentacoes  — Historico (ADR-051)
# ───────────────────────────────────────────────────────────────────────


@router.get(
    "/{prova_id}/movimentacoes", response_model=MovimentacaoListResponse
)
async def list_movimentacoes(
    prova_id: uuid.UUID = Depends(parse_prova_id),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> MovimentacaoListResponse:
    """Lista o historico de movimentacoes da prova (ordem cronologica).

    Na Wave 2 retorna sempre `items=[]` porque nenhuma transicao aconteceu.
    A query e real — quando a Wave 3 inserir movimentacoes, o handler ja
    devolve sem mudanca de contrato.

    A1 (auditoria Wave 2 — Sessao 20): try/except em torno das queries
    mapeia erros transitorios de DB para 502 acionavel.
    """
    try:
        # (1) Verifica scoping da prova (404 se escondida/inexistente)
        scoped = await _carregar_prova_com_scoping(db, prova_id, current_user)
        if scoped is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prova nao encontrada",
            )

        # (2) Le movimentacoes com JOIN para pegar nome/setor do autor
        stmt = (
            select(
                Movimentacao,
                Usuario.nome.label("usuario_nome"),
                Usuario.setor.label("usuario_setor"),
            )
            .join(Usuario, Usuario.id == Movimentacao.usuario_id)
            .where(Movimentacao.prova_id == prova_id)
            .order_by(Movimentacao.created_at.asc())
        )
        rows = (await db.execute(stmt)).all()
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Falha ao carregar movimentacoes da prova %s (user=%s)",
            prova_id,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao carregar movimentacoes",
        )

    items = [
        MovimentacaoResponse(
            id=m.id,
            prova_id=m.prova_id,
            usuario_id=m.usuario_id,
            usuario_nome=usuario_nome,
            usuario_setor=usuario_setor,
            status_anterior=m.status_anterior,
            status_novo=m.status_novo,
            motivo_reprovacao=m.motivo_reprovacao,
            ciclo=m.ciclo,
            rota_no_momento=m.rota_no_momento,
            created_at=m.created_at,
        )
        for m, usuario_nome, usuario_setor in rows
    ]

    return MovimentacaoListResponse(items=items, total=len(items))


# ───────────────────────────────────────────────────────────────────────
# GET /api/v1/provas/{prova_id}/etiqueta.pdf  — Re-download PDF
# ───────────────────────────────────────────────────────────────────────


@router.get("/{prova_id}/etiqueta.pdf")
async def get_etiqueta_pdf(
    prova_id: uuid.UUID = Depends(parse_prova_id),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> Response:
    """Re-gera o PDF da etiqueta da prova e retorna como streaming binario.

    A1 + A2 (auditoria Wave 2 — Sessao 20): dois try/except em sequencia.
      - Primeiro bloco: queries de DB (scoped + SELECT etiqueta +
        _carregar_template_etiqueta). Erro transitorio → 502.
      - Segundo bloco: `gerar_pdf` isolado. Falha de rendering (Unicode,
        fonte ausente, template invalido) → 422 com mensagem acionavel,
        mesmo padrao do ADR-054 (create_prova).
    """
    try:
        scoped = await _carregar_prova_com_scoping(db, prova_id, current_user)
        if scoped is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prova nao encontrada",
            )
        prova, vendedor_nome, _vendedor_localizacao, _vendedor_setor = scoped

        # Busca a etiqueta (snapshot imutavel criado junto com a prova)
        etiqueta = (
            await db.execute(
                select(Etiqueta).where(Etiqueta.prova_id == prova_id)
            )
        ).scalar_one_or_none()
        if etiqueta is None:
            logger.error(
                "Prova %s sem etiqueta associada — defeito de integridade.",
                prova_id,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Etiqueta nao encontrada para esta prova",
            )

        template = await _carregar_template_etiqueta(db)
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Falha ao carregar dados da etiqueta da prova %s (user=%s)",
            prova_id,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao carregar dados da etiqueta",
        )

    # Bloco dedicado ao rendering do PDF. Separado do bloco de DB porque
    # a classe de erro e diferente (422 — input problematico — vs 502 —
    # upstream indisponivel). Mesma filosofia do ADR-054.
    try:
        pdf_bytes = gerar_pdf(
            nome_prova=etiqueta.nome_prova,
            nro_requerimento=etiqueta.nro_requerimento,
            vendedor_nome=etiqueta.vendedor_nome,
            qr_image_bytes=etiqueta.qr_code_image,
            template=template,
            created_at=prova.created_at,
        )
    except Exception as exc:
        logger.exception(
            "Falha ao gerar PDF da etiqueta para prova %s (nro_req=%s)",
            prova_id,
            prova.nro_requerimento,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Falha ao gerar etiqueta: {exc}",
        )

    # Sanitiza o nro_requerimento para uso no Content-Disposition
    safe_nro = "".join(
        c if c.isalnum() or c in "-_" else "_" for c in prova.nro_requerimento
    )
    filename = f"etiqueta-{safe_nro}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-cache",
        },
    )


# ───────────────────────────────────────────────────────────────────────
# GET /api/v1/provas/{prova_id}/qr-code.png  — QR isolado (ADR-052)
# ───────────────────────────────────────────────────────────────────────


@router.get("/{prova_id}/qr-code.png")
async def get_qr_code_png(
    prova_id: uuid.UUID = Depends(parse_prova_id),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> Response:
    """Retorna a imagem PNG do QR Code da prova (BYTEA da tabela etiquetas).

    Usado pelo modal "Visualizar etiqueta" do Componente 08 para exibir o
    QR code em tamanho grande lado a lado com o PDF da etiqueta — facilita
    leitura com celular sem imprimir.

    A1 (auditoria Wave 2 — Sessao 20): try/except em torno das 2 queries
    mapeia erros transitorios de DB para 502 acionavel.
    """
    try:
        scoped = await _carregar_prova_com_scoping(db, prova_id, current_user)
        if scoped is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prova nao encontrada",
            )

        etiqueta = (
            await db.execute(
                select(Etiqueta.qr_code_image).where(Etiqueta.prova_id == prova_id)
            )
        ).scalar_one_or_none()
        if etiqueta is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="QR Code nao encontrado para esta prova",
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Falha ao carregar QR code da prova %s (user=%s)",
            prova_id,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao carregar QR code",
        )

    return Response(
        content=etiqueta,
        media_type="image/png",
        headers={
            "Content-Disposition": 'inline; filename="qr-code.png"',
            # QR code e imutavel apos criacao (RN-001). Cache privado 5min.
            "Cache-Control": "private, max-age=300",
        },
    )


# ───────────────────────────────────────────────────────────────────────
# POST /api/v1/provas/scan  — Componente 10 (Wave 3 Lote A sub-bloco A.3)
# ───────────────────────────────────────────────────────────────────────
#
# Recebe um payload escaneado pelo frontend (html5-qrcode), resolve qual
# prova esse payload aponta, verifica a integridade via hash HMAC
# (qrcode_service.validar_payload_qr — constant-time), aplica scoping
# (mesmo helper usado pelo detalhe) e retorna os dados da prova + a lista
# de transicoes que o usuario corrente pode executar a partir do estado
# atual. A UI do `/escanear` (sub-bloco A.5) consome essa lista para
# renderizar os botoes de acao.
#
# Por que POST e nao GET:
#   1. Request body (payload) simplifica encoding de chars especiais.
#   2. O scan grava audit log — e uma acao, nao uma consulta pura.
#   3. Consistencia com POST /upload-url (outro "request de acao").
#
# Transicoes_permitidas e computada iterando TRANSICOES[prova.status] e
# testando cada destino candidato com `validar_transicao`, mais a regra
# extra RF-009 (rota por localizacao) espelhando o que `executar_transicao`
# faz no A.1. Isso garante que a UI nunca mostra um botao que seria
# rejeitado pelo endpoint de transicao.
#
# Cancelamento e Reinicio de ciclo sao **filtrados** da lista: o endpoint
# do sub-bloco A.4 vai rejeitar CANCELADA e CRIADA como destino (ganchos
# para C13/C14), entao e coerente nao sugerir via UI.
#
# Quando o usuario nao tem permissao para nenhuma transicao do estado
# atual (ex: vendedor escaneando uma prova em COM_MOTORISTA),
# `transicoes_permitidas` vem vazia e o frontend exibe "sem acoes
# disponiveis" — sem erro HTTP. O proprio scan e permitido (visibilidade
# via _scoping_filter) mesmo sem acao subsequente, para debugging e para
# que admin possa auditar estado.


def _computar_transicoes_permitidas(
    prova: ProvaDigital, usuario: Usuario
) -> tuple[list[StatusProvaEnum], list[StatusProvaEnum]]:
    """Determina quais transicoes o `usuario` pode executar na `prova`.

    Retorna `(transicoes_permitidas, motivo_obrigatorio_em)`. Itera os
    destinos candidatos de `TRANSICOES[prova.status]`, testa cada um com
    `validar_transicao` (captura exceptions) e aplica as mesmas regras
    extras que `executar_transicao` do sub-bloco A.1:

      - Filtra `CANCELADA` (gancho C13, sera endpoint admin dedicado).
      - Filtra `CRIADA` quando origem e REPROVADA_PELO_VENDEDOR (gancho
        C14 — reinicio de ciclo via endpoint admin).
      - Em `APROVADA_PELO_VENDEDOR`, filtra destinos conforme localizacao
        do vendedor (RF-009):
          - MATRIZ → so `DE_VOLTA_3STUDIO`
          - FILIAL → so `ENCAMINHADA_A_CLICHERIA`
        Admin bypassa essa regra (consistente com `executar_transicao`).

    `motivo_obrigatorio_em` contem a subset de `transicoes_permitidas`
    onde o usuario vai precisar informar motivo no submit — Wave 3 Lote
    A: apenas `REPROVADA_PELO_VENDEDOR` (RF-007). Cancelamento tambem
    exige motivo mas esta filtrado.
    """
    permitidas: list[StatusProvaEnum] = []
    destinos_candidatos = TRANSICOES.get(prova.status, set())

    for destino in destinos_candidatos:
        # Filtro de escopo do Lote A — CANCELADA e CRIADA nao sao expostos
        # pelo endpoint de transicao (ganchos C13 / C14).
        if destino == StatusProvaEnum.CANCELADA:
            continue
        if (
            destino == StatusProvaEnum.CRIADA
            and prova.status == StatusProvaEnum.REPROVADA_PELO_VENDEDOR
        ):
            continue

        # Teste de autorizacao via state_machine.
        try:
            validar_transicao(prova.status, destino, usuario)
        except (TransicaoInvalidaError, AtorNaoAutorizadoError):
            continue

        # Regra extra RF-009 para APROVADA_PELO_VENDEDOR.
        if (
            prova.status == StatusProvaEnum.APROVADA_PELO_VENDEDOR
            and not usuario.is_admin
        ):
            if destino == StatusProvaEnum.DE_VOLTA_3STUDIO:
                if usuario.localizacao != LocalizacaoEnum.MATRIZ:
                    continue
            elif destino == StatusProvaEnum.ENCAMINHADA_A_CLICHERIA:
                if usuario.localizacao != LocalizacaoEnum.FILIAL:
                    continue

        permitidas.append(destino)

    # Ordenacao estavel e previsivel para facilitar testes e UI.
    permitidas.sort(key=lambda s: s.value)

    motivo_obrigatorio_em = [
        s for s in permitidas if s == StatusProvaEnum.REPROVADA_PELO_VENDEDOR
    ]
    return permitidas, motivo_obrigatorio_em


async def _carregar_prova_por_nro_req_com_scoping(
    db: AsyncSession, nro_requerimento: str, user: Usuario
) -> tuple[ProvaDigital, str, LocalizacaoEnum | None, SetorEnum] | None:
    """Carrega prova por `nro_requerimento` aplicando scoping por setor.

    Versao do scan do `_carregar_prova_com_scoping` que e por `prova_id`:
    aqui o seletor e `nro_requerimento` (UNIQUE). Mesma semantica de
    retorno 4-tupla ou None.

    Nao e feito FOR UPDATE — o scan e apenas leitura. O FOR UPDATE vira
    no sub-bloco A.4 (endpoint de transicao) quando for efetivar a
    mudanca de estado.
    """
    stmt = (
        select(
            ProvaDigital,
            Usuario.nome.label("vendedor_nome"),
            Usuario.localizacao.label("vendedor_localizacao"),
            Usuario.setor.label("vendedor_setor"),
        )
        .join(Usuario, Usuario.id == ProvaDigital.vendedor_id)
        .where(ProvaDigital.nro_requerimento == nro_requerimento)
    )
    base = _scoping_filter(user)
    if base is not None:
        stmt = stmt.where(base)

    row = (await db.execute(stmt)).first()
    if row is None:
        return None
    prova, vendedor_nome, vendedor_localizacao, vendedor_setor = row
    return prova, vendedor_nome, vendedor_localizacao, vendedor_setor


@router.post("/scan", response_model=ScanResponse)
async def scan_prova(
    body: ScanRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> ScanResponse:
    """Resolve um payload de QR Code escaneado (Componente 10).

    Fluxo:
      1. Pydantic valida formato estrutural do payload (prefixo `3SD|`,
         3 campos, hash com 16 chars). Rejeita 422 se malformado.
      2. Parseia `nro_requerimento` e `hash_truncado` do payload.
      3. SELECT prova por `nro_requerimento` com scoping aplicado. Se
         nao encontra OU o scoping esconde, retorna 404 "Prova nao
         encontrada" (mesma mensagem para nao vazar existencia — padrao
         ADR-049).
      4. Verifica o hash via `qrcode_service.validar_payload_qr` —
         constant-time. Se nao bate, 422 "QR Code nao corresponde a
         prova esperada". Essa checagem e **apos** o SELECT porque
         precisamos do `qr_code_hash` armazenado para comparar.
      5. Calcula `transicoes_permitidas` via
         `_computar_transicoes_permitidas` (iterando TRANSICOES +
         validar_transicao + regra RF-009).
      6. Log audit `acao="escanear_prova"` com detalhes basicos
         (nro_requerimento, status_atual). Commit.
      7. Retorna 200 com `ScanResponse`.

    Codigos HTTP:
      200: happy path. `transicoes_permitidas` pode ser `[]` se a prova
           esta em estado terminal ou se o usuario nao tem nenhuma
           transicao permitida a partir do estado atual.
      401: token ausente/invalido (herdado de `get_current_user`).
      403: usuario desativado.
      404: prova nao encontrada OU escondida por scoping.
      422: formato de payload invalido OR hash nao bate (integridade).
      502: erro transitorio de DB (padrao ADR-074).
    """
    # Parseia nro_requerimento do payload ja validado pelo Pydantic.
    _prefix, nro_requerimento, _hash_trunc = body.payload.split(
        qrcode_service.QR_PAYLOAD_SEPARATOR
    )

    try:
        scoped = await _carregar_prova_por_nro_req_com_scoping(
            db, nro_requerimento, current_user
        )
    except Exception:
        logger.exception(
            "Falha ao resolver scan (user=%s, nro_req=%s)",
            current_user.id,
            nro_requerimento,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao carregar prova",
        )

    if scoped is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prova nao encontrada",
        )
    prova, vendedor_nome, vendedor_localizacao, vendedor_setor = scoped

    # Verificacao do hash (constant-time). Feita APOS o scoping para nao
    # dar pistas sobre existencia da prova via timing.
    if not qrcode_service.validar_payload_qr(body.payload, prova.qr_code_hash):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="QR Code nao corresponde a prova esperada",
        )

    # Calcula transicoes permitidas para este usuario neste estado.
    transicoes_permitidas, motivo_obrigatorio_em = _computar_transicoes_permitidas(
        prova, current_user
    )

    # Audit log: scan e uma acao auditada (RNF-005 + rastreabilidade de
    # quem olhou qual prova). Mesmo que o scan nao mude estado, saber
    # quem escaneou o que e util para investigacao.
    try:
        await log_audit(
            db,
            acao="escanear_prova",
            usuario_id=current_user.id,
            prova_id=prova.id,
            detalhes={
                "nro_requerimento": prova.nro_requerimento,
                "status_atual": prova.status.value,
                "transicoes_permitidas": [s.value for s in transicoes_permitidas],
            },
            request=request,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception(
            "Falha ao persistir audit do scan (user=%s, prova=%s)",
            current_user.id,
            prova.id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao registrar scan",
        )

    logger.info(
        "Scan OK: user=%s prova=%s status=%s transicoes=%d",
        current_user.id,
        prova.id,
        prova.status.value,
        len(transicoes_permitidas),
    )

    return ScanResponse(
        prova=_build_prova_response(
            prova, vendedor_nome, vendedor_localizacao, vendedor_setor
        ),
        transicoes_permitidas=transicoes_permitidas,
        motivo_obrigatorio_em=motivo_obrigatorio_em,
    )


# ───────────────────────────────────────────────────────────────────────
# POST /api/v1/provas/{prova_id}/transicoes  — Componente 11 (sub-bloco A.4)
# ───────────────────────────────────────────────────────────────────────
#
# Executa uma transicao de status end-to-end — o endpoint espelha o que o
# sub-bloco A.5 (frontend `/escanear`) vai chamar apos o usuario:
#   1. escanear o QR (POST /scan, sub-bloco A.3),
#   2. escolher uma das `transicoes_permitidas`,
#   3. assinar digitalmente no canvas.
#
# Fluxo do handler:
#   a. Pydantic valida: formato do payload, status_novo not in
#      {CANCELADA, CRIADA} (ganchos C13/C14), assinatura nao vazia,
#      tamanho <= 700 KB.
#   b. Decode base64 da assinatura — 422 se malformado.
#   c. Carrega a prova com `_carregar_prova_com_scoping(..., lock=True)`.
#      FOR UPDATE serializa transicoes concorrentes (R3 do plano).
#   d. 404 se scoping esconde ou ausente.
#   e. Chama `state_machine.executar_transicao(...)` (sub-bloco A.1).
#   f. Traduz excecoes de dominio para HTTP (ADR-084):
#      - TransicaoInvalidaError → 409 (status da prova mudou — race ou
#        cliente enviou destino invalido). Mensagem "Status da prova mudou.
#        Recarregue e tente novamente."
#      - AtorNaoAutorizadoError → 422 (setor/localizacao nao bate)
#      - ValueError → 422 (motivo ausente / assinatura vazia pos-decode)
#      - RotaIndeterminavelError → 422 (aprovacao sem localizacao)
#   g. Commit — se falhar, rollback + 502.
#   h. Retorna 201 com `TransicaoResponse` contendo a prova atualizada
#      e a movimentacao criada.


def _decode_assinatura(assinatura_base64: str) -> bytes:
    """Decodifica o base64 da assinatura, levantando HTTPException(422)
    se o input nao e base64 valido ou resulta em zero bytes apos decode."""
    try:
        decoded = base64.b64decode(assinatura_base64, validate=True)
    except (base64.binascii.Error, ValueError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Assinatura base64 invalida",
        )
    if not decoded:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Assinatura vazia apos decode",
        )
    return decoded


@router.post(
    "/{prova_id}/transicoes",
    response_model=TransicaoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def executar_transicao_prova(
    body: TransicaoRequest,
    request: Request,
    prova_id: uuid.UUID = Depends(parse_prova_id),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> TransicaoResponse:
    """Executa uma transicao de status para a prova indicada (Componente 11).

    O grosso da logica vive em `state_machine.executar_transicao` (sub-bloco
    A.1 / ADR-081). Este handler e uma camada fina de:
      - orquestracao de transacao (load com FOR UPDATE, commit, rollback),
      - traducao de exceptions de dominio para HTTP,
      - montagem do response com `MovimentacaoResponse`.

    Ver ADR-084 para as decisoes de desenho (409 para race, separacao de
    bloco de rendering vs bloco de DB, mapeamento de excecoes).
    """
    # (a) Decode base64 da assinatura (422 se malformado).
    assinatura_bytes = _decode_assinatura(body.assinatura_base64)

    # (b) Carrega a prova com FOR UPDATE + scoping (ADR-084).
    try:
        scoped = await _carregar_prova_com_scoping(
            db, prova_id, current_user, lock=True
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Falha ao carregar prova %s com FOR UPDATE (user=%s)",
            prova_id,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao carregar prova",
        )

    if scoped is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prova nao encontrada",
        )
    prova, vendedor_nome, vendedor_localizacao, vendedor_setor = scoped

    # (c) Executa transicao via state_machine. Traduz exceptions para HTTP.
    try:
        movimentacao = await executar_transicao(
            db,
            prova=prova,
            status_novo=body.status_novo,
            usuario=current_user,
            assinatura_digital=assinatura_bytes,
            motivo_reprovacao=body.motivo_reprovacao,
            request=request,
        )
    except TransicaoInvalidaError as exc:
        # ADR-084: toda TransicaoInvalidaError apos FOR UPDATE vira 409.
        # Pode ser race (outro usuario ja transicionou) ou cliente enviando
        # destino invalido — em ambos os casos, o cliente deve recarregar e
        # tentar de novo a partir do estado atual.
        logger.info(
            "Transicao invalida apos FOR UPDATE para prova %s (user=%s): %s",
            prova.id,
            current_user.id,
            exc,
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Status da prova mudou. Recarregue e tente novamente. "
                f"(detalhe: {exc})"
            ),
        )
    except AtorNaoAutorizadoError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
    except RotaIndeterminavelError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
    except ValueError as exc:
        # Motivo ausente na reprovacao, assinatura vazia (pre-decode).
        # Nota: TransicaoInvalidaError herda de ValueError, mas por estar
        # em except mais cedo na cadeia, nao cai aqui. Esse except pega
        # apenas ValueError "puro" (motivo, assinatura) levantado pelo
        # `executar_transicao`.
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
    except HTTPException:
        # Possivel raise do proprio log_audit (fora de escopo, mas evita
        # que vire 500 silencioso).
        raise
    except Exception:
        logger.exception(
            "Falha inesperada em executar_transicao para prova %s (user=%s)",
            prova.id,
            current_user.id,
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao executar transicao",
        )

    # (d) Commit — erro aqui tambem e 502 + rollback.
    try:
        await db.commit()
    except Exception:
        logger.exception(
            "Falha ao commitar transicao da prova %s (user=%s)",
            prova.id,
            current_user.id,
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao persistir transicao",
        )

    logger.info(
        "Transicao OK: prova=%s de=%s para=%s user=%s ciclo=%d rota=%s",
        prova.id,
        movimentacao.status_anterior.value,
        movimentacao.status_novo.value,
        current_user.id,
        movimentacao.ciclo,
        prova.rota.value if prova.rota else None,
    )

    # (e) Monta response. `prova` esta mutado in-place (status/rota/ciclo
    # ja atualizados). `movimentacao.id` pode vir None se o driver nao
    # retornou RETURNING — mas como fizemos flush antes do commit, o
    # SQLAlchemy preenche o id automaticamente via server_default.
    return TransicaoResponse(
        prova=_build_prova_response(
            prova, vendedor_nome, vendedor_localizacao, vendedor_setor
        ),
        movimentacao=MovimentacaoResponse(
            id=movimentacao.id,
            prova_id=movimentacao.prova_id,
            usuario_id=movimentacao.usuario_id,
            usuario_nome=current_user.nome,
            usuario_setor=current_user.setor,
            status_anterior=movimentacao.status_anterior,
            status_novo=movimentacao.status_novo,
            motivo_reprovacao=movimentacao.motivo_reprovacao,
            ciclo=movimentacao.ciclo,
            rota_no_momento=movimentacao.rota_no_momento,
            created_at=movimentacao.created_at or datetime.now(tz=timezone.utc),
        ),
    )


# ───────────────────────────────────────────────────────────────────────
# POST /api/v1/provas/{id}/cancelar  — Componente 13 (Wave 3 Lote C)
# ───────────────────────────────────────────────────────────────────────


def _assinatura_administrativa(acao: str, usuario: Usuario) -> bytes:
    """Gera um marcador nao-vazio para acoes admin sem canvas de assinatura.

    `movimentacoes.assinatura_digital` e NOT NULL. Acoes administrativas
    (cancelamento, reinicio de ciclo) nao passam pelo fluxo de scan +
    signature canvas do Componente 11, mas precisam gravar algo no campo.

    O marcador identifica a natureza da acao e quem a executou, servindo
    como trilha de auditoria complementar ao `audit_log.detalhes_json`.
    """
    return f"ACAO_ADMINISTRATIVA:{acao}:{usuario.nome}".encode("utf-8")


@router.post(
    "/{prova_id}/cancelar",
    response_model=TransicaoResponse,
    summary="Cancelar prova digital (Componente 13)",
    description="Cancela uma prova em qualquer estado ativo. Restrito a admin.",
)
async def cancelar_prova(
    body: CancelarRequest,
    request: Request,
    prova_id: uuid.UUID = Depends(parse_prova_id),
    db: AsyncSession = Depends(get_db),
    admin: Usuario = Depends(get_admin_user),
) -> TransicaoResponse:
    """RF-010 + RN-005: cancelamento com motivo obrigatorio, admin-only."""
    # (a) Carrega a prova com FOR UPDATE.
    try:
        scoped = await _carregar_prova_com_scoping(
            db, prova_id, admin, lock=True
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Falha ao carregar prova %s para cancelamento (admin=%s)",
            prova_id, admin.id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao carregar prova",
        )

    if scoped is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prova nao encontrada",
        )
    prova, vendedor_nome, vendedor_localizacao, vendedor_setor = scoped

    # (b) Validacao rapida antes de chamar executar_transicao.
    if not pode_cancelar(prova.status):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Prova em estado {prova.status.value} nao pode ser cancelada"
            ),
        )

    # (c) Executa transicao via state_machine.
    sig = _assinatura_administrativa("cancelamento", admin)
    try:
        movimentacao = await executar_transicao(
            db,
            prova=prova,
            status_novo=StatusProvaEnum.CANCELADA,
            usuario=admin,
            assinatura_digital=sig,
            motivo_cancelamento=body.motivo_cancelamento,
            request=request,
        )
    except TransicaoInvalidaError as exc:
        logger.info("Cancelamento invalido prova %s: %s", prova.id, exc)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Status da prova mudou. Recarregue e tente novamente. (detalhe: {exc})",
        )
    except (AtorNaoAutorizadoError, ValueError) as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Falha inesperada ao cancelar prova %s (admin=%s)",
            prova.id, admin.id,
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao cancelar prova",
        )

    # (d) Commit.
    try:
        await db.commit()
    except Exception:
        logger.exception("Falha ao commitar cancelamento da prova %s", prova.id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao persistir cancelamento",
        )

    logger.info(
        "Prova cancelada: id=%s admin=%s motivo=%s",
        prova.id, admin.id, body.motivo_cancelamento[:50],
    )

    return TransicaoResponse(
        prova=_build_prova_response(
            prova, vendedor_nome, vendedor_localizacao, vendedor_setor
        ),
        movimentacao=MovimentacaoResponse(
            id=movimentacao.id,
            prova_id=movimentacao.prova_id,
            usuario_id=movimentacao.usuario_id,
            usuario_nome=admin.nome,
            usuario_setor=admin.setor,
            status_anterior=movimentacao.status_anterior,
            status_novo=movimentacao.status_novo,
            motivo_reprovacao=movimentacao.motivo_reprovacao,
            ciclo=movimentacao.ciclo,
            rota_no_momento=movimentacao.rota_no_momento,
            created_at=movimentacao.created_at or datetime.now(tz=timezone.utc),
        ),
    )


# ───────────────────────────────────────────────────────────────────────
# POST /api/v1/provas/{id}/reiniciar-ciclo — Componente 14 (Wave 3 Lote C)
# ───────────────────────────────────────────────────────────────────────


@router.post(
    "/{prova_id}/reiniciar-ciclo",
    response_model=TransicaoResponse,
    summary="Reiniciar ciclo de prova reprovada (Componente 14)",
    description="Reinicia o ciclo de uma prova REPROVADA. Restrito a admin.",
)
async def reiniciar_ciclo_prova(
    request: Request,
    prova_id: uuid.UUID = Depends(parse_prova_id),
    db: AsyncSession = Depends(get_db),
    admin: Usuario = Depends(get_admin_user),
) -> TransicaoResponse:
    """RF-008 + RN-006: reinicio de ciclo admin-only, preserva historico."""
    # (a) Carrega a prova com FOR UPDATE.
    try:
        scoped = await _carregar_prova_com_scoping(
            db, prova_id, admin, lock=True
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Falha ao carregar prova %s para reinicio (admin=%s)",
            prova_id, admin.id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao carregar prova",
        )

    if scoped is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prova nao encontrada",
        )
    prova, vendedor_nome, vendedor_localizacao, vendedor_setor = scoped

    # (b) Validacao rapida: so pode reiniciar de REPROVADA.
    if prova.status != StatusProvaEnum.REPROVADA_PELO_VENDEDOR:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Reinicio de ciclo so permitido para provas reprovadas. "
                f"Status atual: {prova.status.value}"
            ),
        )

    # (c) Executa transicao via state_machine.
    sig = _assinatura_administrativa("reiniciar_ciclo", admin)
    try:
        movimentacao = await executar_transicao(
            db,
            prova=prova,
            status_novo=StatusProvaEnum.CRIADA,
            usuario=admin,
            assinatura_digital=sig,
            request=request,
        )
    except TransicaoInvalidaError as exc:
        logger.info("Reinicio invalido prova %s: %s", prova.id, exc)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Status da prova mudou. Recarregue e tente novamente. (detalhe: {exc})",
        )
    except (AtorNaoAutorizadoError, RotaIndeterminavelError, ValueError) as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Falha inesperada ao reiniciar ciclo da prova %s (admin=%s)",
            prova.id, admin.id,
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao reiniciar ciclo",
        )

    # (d) Commit.
    try:
        await db.commit()
    except Exception:
        logger.exception("Falha ao commitar reinicio da prova %s", prova.id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao persistir reinicio de ciclo",
        )

    logger.info(
        "Ciclo reiniciado: prova=%s ciclo_novo=%d admin=%s",
        prova.id, prova.ciclo_atual, admin.id,
    )

    return TransicaoResponse(
        prova=_build_prova_response(
            prova, vendedor_nome, vendedor_localizacao, vendedor_setor
        ),
        movimentacao=MovimentacaoResponse(
            id=movimentacao.id,
            prova_id=movimentacao.prova_id,
            usuario_id=movimentacao.usuario_id,
            usuario_nome=admin.nome,
            usuario_setor=admin.setor,
            status_anterior=movimentacao.status_anterior,
            status_novo=movimentacao.status_novo,
            motivo_reprovacao=movimentacao.motivo_reprovacao,
            ciclo=movimentacao.ciclo,
            rota_no_momento=movimentacao.rota_no_momento,
            created_at=movimentacao.created_at or datetime.now(tz=timezone.utc),
        ),
    )
