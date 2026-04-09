"""Users CRUD router — Componente 04 do Backlog.

All endpoints under /api/v1/users.
Admin-only unless specified otherwise.
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user, get_current_user
from app.core.supabase_admin import (
    create_auth_user,
    delete_auth_user,
    disable_auth_user,
    enable_auth_user,
)
from app.db.models import LocalizacaoEnum, SetorEnum, Usuario
from app.db.session import get_db
from app.domain.schemas.user import (
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()


async def _count_other_active_admins(db: AsyncSession, exclude_user_id: UUID) -> int:
    """Count active admins (is_admin=true AND ativo=true), excluding one user_id.

    Used to enforce the system invariant: there must always be at least one
    active admin. Returning 0 means the excluded user is the last one — and the
    operation that prompted this check must be blocked.
    """
    result = await db.execute(
        select(func.count())
        .select_from(Usuario)
        .where(
            Usuario.is_admin.is_(True),
            Usuario.ativo.is_(True),
            Usuario.id != exclude_user_id,
        )
    )
    return result.scalar() or 0


# ── GET /me (before /{id} to avoid route conflict) ──────────────────────────

@router.get("/me", response_model=UserResponse)
async def get_me(user: Usuario = Depends(get_current_user)):
    """Return the currently authenticated user. Any logged-in profile."""
    return user


# ── POST / ──────────────────────────────────────────────────────────────────

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    admin: Usuario = Depends(get_admin_user),
):
    """Create a new user (admin only).

    1. Validate input (Pydantic)
    2. Check email uniqueness in app DB
    3. Create in Supabase Auth (Service Role)
    4. Insert in app DB
    5. Rollback Supabase Auth if DB insert fails
    """
    # Check email uniqueness
    existing = await db.execute(
        select(Usuario).where(func.lower(Usuario.email) == body.email.lower())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email ja cadastrado",
        )

    # Create in Supabase Auth
    try:
        auth_uid = await create_auth_user(body.email, body.senha)
    except Exception:
        logger.exception("Falha ao criar usuario no Supabase Auth")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao criar usuario na autenticacao",
        )

    # Insert in app DB — rollback Auth on failure
    try:
        new_user = Usuario(
            auth_uid=auth_uid,
            nome=body.nome,
            email=body.email.lower(),
            setor=body.setor,
            localizacao=body.localizacao,
            is_admin=body.is_admin,
            created_by=admin.id,
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        logger.info(
            "Usuario criado: id=%s email=%s setor=%s por admin=%s",
            new_user.id,
            new_user.email,
            new_user.setor.value,
            admin.id,
        )
        return new_user
    except Exception:
        await db.rollback()
        logger.exception("Falha no DB, rollback Auth user %s", auth_uid)
        await delete_auth_user(auth_uid)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao criar usuario",
        )


# ── GET / (list) ────────────────────────────────────────────────────────────

@router.get("/", response_model=UserListResponse)
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin: Usuario = Depends(get_admin_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    setor: SetorEnum | None = Query(None),
    localizacao: LocalizacaoEnum | None = Query(None),
    ativo: bool | None = Query(None),
    busca: str | None = Query(None, max_length=200),
):
    """List users with pagination and filters (admin only)."""
    base = select(Usuario)
    count_base = select(func.count()).select_from(Usuario)

    filters = []
    if setor is not None:
        filters.append(Usuario.setor == setor)
    if localizacao is not None:
        filters.append(Usuario.localizacao == localizacao)
    if ativo is not None:
        filters.append(Usuario.ativo == ativo)
    if busca:
        pattern = f"%{busca}%"
        filters.append(or_(Usuario.nome.ilike(pattern), Usuario.email.ilike(pattern)))

    for f in filters:
        base = base.where(f)
        count_base = count_base.where(f)

    total = (await db.execute(count_base)).scalar() or 0
    offset = (page - 1) * page_size
    rows = (
        await db.execute(
            base.order_by(Usuario.created_at.desc()).offset(offset).limit(page_size)
        )
    ).scalars().all()

    pages = (total + page_size - 1) // page_size if total > 0 else 0
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


# ── GET /{id} ───────────────────────────────────────────────────────────────

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Get user detail. Admin sees any; non-admin sees only self."""
    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")

    if not current_user.is_admin and current_user.id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")

    return user


# ── PATCH /{id} ─────────────────────────────────────────────────────────────

@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: Usuario = Depends(get_admin_user),
):
    """Update user fields (admin only). Enforces RN-010."""
    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Nenhum campo para atualizar",
        )

    # RN-010: admin cannot remove own is_admin or deactivate self
    if user.id == admin.id:
        if "is_admin" in update_data and not update_data["is_admin"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Administrador nao pode remover seu proprio acesso de admin",
            )
        if "ativo" in update_data and not update_data["ativo"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Administrador nao pode desativar a si mesmo",
            )
    else:
        # System invariant: the system must always have >= 1 active admin.
        # If the target is currently an active admin and we are about to demote
        # or deactivate them, ensure at least one OTHER active admin exists.
        if user.is_admin and user.ativo:
            demoting = "is_admin" in update_data and not update_data["is_admin"]
            deactivating = "ativo" in update_data and not update_data["ativo"]
            if demoting or deactivating:
                if await _count_other_active_admins(db, user.id) == 0:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Nao e possivel remover o ultimo administrador ativo do sistema",
                    )

    # Cross-validate setor + localizacao (CHECK constraint chk_vendedor_localizacao)
    if "setor" in update_data:
        new_setor = update_data["setor"]
        if new_setor == SetorEnum.VENDEDOR:
            new_loc = update_data.get("localizacao", user.localizacao)
            if new_loc is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Vendedor deve ter localizacao (MATRIZ ou FILIAL)",
                )
        else:
            # Non-vendedor: force clear localizacao
            update_data["localizacao"] = None
    elif "localizacao" in update_data:
        current_setor = user.setor
        if current_setor != SetorEnum.VENDEDOR and update_data["localizacao"] is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Apenas vendedores podem ter localizacao",
            )
        if current_setor == SetorEnum.VENDEDOR and update_data["localizacao"] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Vendedor deve ter localizacao",
            )

    # Detect ativo transition BEFORE we mutate the object so the snapshot is reliable.
    was_active = user.ativo
    will_be_active = update_data.get("ativo", was_active)
    needs_ban = was_active and not will_be_active
    needs_unban = (not was_active) and will_be_active

    # Apply in-memory changes (persisted on commit below).
    for field, value in update_data.items():
        setattr(user, field, value)

    # Sync Supabase Auth FIRST. If the auth call fails, abort the operation
    # WITHOUT touching the DB so we never end up with auth/app drift.
    if needs_ban:
        try:
            await disable_auth_user(str(user.auth_uid))
        except Exception:
            await db.rollback()
            logger.exception(
                "Falha ao desabilitar usuario no Supabase Auth: %s", user.auth_uid
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Falha ao desativar usuario na autenticacao",
            )
    elif needs_unban:
        try:
            await enable_auth_user(str(user.auth_uid))
        except Exception:
            await db.rollback()
            logger.exception(
                "Falha ao reabilitar usuario no Supabase Auth: %s", user.auth_uid
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Falha ao reativar usuario na autenticacao",
            )

    # Persist DB changes. If commit fails after we already changed auth state,
    # compensate the auth call so the two systems stay in sync.
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Falha ao persistir update do usuario %s", user.id)
        if needs_ban:
            try:
                await enable_auth_user(str(user.auth_uid))
            except Exception:
                logger.exception(
                    "Compensacao auth (enable) FALHOU para %s — drift manual",
                    user.auth_uid,
                )
        elif needs_unban:
            try:
                await disable_auth_user(str(user.auth_uid))
            except Exception:
                logger.exception(
                    "Compensacao auth (disable) FALHOU para %s — drift manual",
                    user.auth_uid,
                )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao atualizar usuario",
        )

    await db.refresh(user)
    logger.info(
        "Usuario atualizado: id=%s campos=%s por admin=%s",
        user.id,
        list(update_data.keys()),
        admin.id,
    )
    return user


# ── DELETE /{id} (soft delete) ──────────────────────────────────────────────

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: Usuario = Depends(get_admin_user),
):
    """Soft delete: set ativo=false (admin only). Enforces RN-010.

    Also disables the user in Supabase Auth to prevent token refresh.
    """
    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")

    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Administrador nao pode desativar a si mesmo",
        )

    if not user.ativo:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Usuario ja esta desativado",
        )

    # System invariant: cannot deactivate the last active admin in the system.
    if user.is_admin and await _count_other_active_admins(db, user.id) == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nao e possivel desativar o ultimo administrador ativo do sistema",
        )

    # Disable in Supabase Auth FIRST. If the ban fails we abort BEFORE touching
    # the DB so the two systems can never end up out of sync (was a real
    # production drift before — see ADR-019).
    try:
        await disable_auth_user(str(user.auth_uid))
    except Exception:
        logger.exception(
            "Falha ao desabilitar usuario no Supabase Auth: %s", user.auth_uid
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao desativar usuario na autenticacao",
        )

    user.ativo = False
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        # Compensation: re-enable auth user so we don't end up with the user
        # banned in auth.users but still ativo=true in public.usuarios.
        try:
            await enable_auth_user(str(user.auth_uid))
        except Exception:
            logger.exception(
                "Compensacao auth (enable) FALHOU para %s — drift manual",
                user.auth_uid,
            )
        logger.exception("Falha ao soft-delete usuario %s", user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao desativar usuario",
        )

    logger.info("Usuario desativado: id=%s por admin=%s", user.id, admin.id)
