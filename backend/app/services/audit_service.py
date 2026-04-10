"""Helper de auditoria estruturada (ADR-039).

Centraliza o INSERT em `audit_logs` para garantir:
  1. IP e User-Agent lidos do `Request` do FastAPI quando disponiveis
  2. JSON de detalhes com campos coerentes (usando dict simples)
  3. Contrato pronto para ser chamado intensivamente pelas Waves 3+ em cada
     transicao de status, mudanca de configuracao e acao admin

A insercao acontece dentro da mesma sessao do caller — NAO faz commit. Se o
caller fizer rollback, o audit log e descartado junto. Isso e intencional:
log de uma acao que nao aconteceu seria informacao enganosa.

UPDATE/DELETE em audit_logs estao bloqueados pelo trigger trg_audit_logs_imutavel.
"""
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog


def _extract_client_ip(request: Request) -> str | None:
    """Extrai o IP real do cliente respeitando X-Forwarded-For.

    F04 (auditoria externa Wave 2): em producao no Railway (atras de proxy),
    `request.client.host` retorna o IP do gateway do Railway, nao o IP real
    do usuario. RNF-005 exige log "completo e imutavel" — sem o IP real,
    investigacoes de incidente ficam cegas.

    Estrategia:
      1. Tenta ler `X-Forwarded-For` e pega o PRIMEIRO IP da cadeia (o client
         original). O formato e `client, proxy1, proxy2, ...`.
      2. Se ausente, tenta `X-Real-IP` (alguns proxies usam esse header).
      3. Fallback: `request.client.host` (correto em dev local e testes).

    IMPORTANTE (seguranca): confiamos nesses headers porque o Railway e um
    proxy confiavel que reescreve X-Forwarded-For no ingress. Se o projeto
    migrar para uma infra onde o cliente possa injetar headers direto, essa
    logica precisa ser endurecida para:
      - Validar que o request vem de um proxy na whitelist
      - Usar o PENULTIMO IP da cadeia (o ultimo e sempre o proxy)
    Por ora, Railway single-proxy -> primeiro IP esta correto.
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Pode ter multiplos IPs separados por virgula — pegar o primeiro.
        first = forwarded_for.split(",")[0].strip()
        if first:
            return first

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    # Fallback: request.client pode ser None em testes sem cliente HTTP real.
    if request.client is not None:
        return request.client.host

    return None


async def log_audit(
    db: AsyncSession,
    *,
    acao: str,
    usuario_id: UUID,
    prova_id: UUID | None = None,
    detalhes: dict[str, Any] | None = None,
    request: Request | None = None,
) -> AuditLog:
    """Insere uma linha em `audit_logs`. Nao faz commit.

    Args:
        db: Sessao SQLAlchemy ativa. O caller e responsavel pelo commit.
        acao: String curta identificando a acao (e.g. "criar_prova",
              "atualizar_configuracao", "transitar_status"). Maximo 100 chars.
        usuario_id: UUID do usuario que executou a acao.
        prova_id: UUID da prova relacionada (None quando nao aplicavel,
                  como em mudanca de configuracao do sistema).
        detalhes: Dict serializavel em JSON com informacoes da acao. Evitar
                  dados sensiveis (senhas, tokens). Salvo em `detalhes_json`.
        request: FastAPI Request para extrair IP e User-Agent. Opcional — em
                 contexto de teste ou job sem request, passar None.

    Returns:
        A instancia AuditLog persistida (apos flush).
    """
    ip_address: str | None = None
    user_agent: str | None = None

    if request is not None:
        ip_address = _extract_client_ip(request)
        ua = request.headers.get("user-agent")
        if ua:
            # Trunca para evitar logs gigantes (navegadores modernos tem UAs longos).
            user_agent = ua[:2000]

    entry = AuditLog(
        prova_id=prova_id,
        usuario_id=usuario_id,
        acao=acao,
        detalhes_json=detalhes,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(entry)
    # Flush envia o INSERT sem commit — o caller orquestra a transacao.
    await db.flush()
    return entry
