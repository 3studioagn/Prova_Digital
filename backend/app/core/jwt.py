"""
Esqueleto do middleware de verificacao JWT do Supabase.

O Supabase Auth EMITE os tokens JWT.
Este modulo apenas VERIFICA a assinatura usando PyJWT.
Nunca emitimos tokens aqui.

Sera plugado em rotas protegidas na Wave 1 (Autenticacao).
"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

security = HTTPBearer()


def verify_supabase_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Verifica e decodifica o JWT emitido pelo Supabase Auth.

    Retorna o payload decodificado se valido.
    Levanta HTTPException 401 se invalido ou expirado.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
        )
