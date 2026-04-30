"""Guard primario do RBAC backend — Wave 1 v4.0, Componente 05.

Substitui `Depends(get_admin_user)` em endpoints novos por consultas a
ACCESS_MATRIX (shared/access-matrix.json). `get_admin_user` continua
disponivel como helper legacy onde a checagem nao e ligada a uma celula
da Matriz (ex.: invariantes de RN-010 em users.py).

Uso tipico em endpoints:

    from app.access import enforce_access_for

    @router.get("/")
    async def list_things(
        user: Usuario = Depends(get_current_user),
    ):
        enforce_access_for("auditoria", user)
        ...

Lanca HTTPException(403) quando acesso e NEGADO. Endpoints com escopo
PARCIAL precisam combinar com `scope_filter_for(rule_key, user)` na
clausula WHERE da query.
"""
from __future__ import annotations

import logging

from fastapi import HTTPException, status

from app.access.matrix import (
    Acesso,
    evaluate,
    get_rule_for_key,
    resolve_profile,
)
from app.db.models import Usuario

logger = logging.getLogger(__name__)


def enforce_access_for(rule_key: str, user: Usuario) -> None:
    """Levanta HTTPException(403) se o user nao tem acesso a rule_key.

    Acesso FULL ou PARCIAL passa silenciosamente. NEGADO levanta 403 com
    mensagem que NAO vaza qual perfil seria autorizado (apenas "Acesso
    nao autorizado") — alinhado com pratica de Wave 6 audit_log.
    """
    rule = get_rule_for_key(rule_key)
    if rule is None:
        # Regra nao mapeada na Matriz e bug de configuracao — nao silenciar.
        # Erro 500 e correto: a aplicacao pediu uma chave que nao existe.
        logger.error(
            "enforce_access_for: rule_key '%s' nao existe em ACCESS_MATRIX. "
            "Verifique shared/access-matrix.json.",
            rule_key,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuracao de RBAC inconsistente",
        )

    decision = evaluate(rule, user)
    if decision.acesso == Acesso.NEGADO:
        profile = resolve_profile(user)
        logger.info(
            "rbac.deny user_id=%s profile=%s rule=%s",
            user.id,
            profile.value if profile else "<unmapped>",
            rule_key,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso nao autorizado para seu perfil",
        )

    # FULL ou PARCIAL: passa. Quem precisa do escopo chama scope_filter_for.
    return None
