"""
🔐 Auth Endpoints — Login, Refresh, Logout, Me.

US-04: POST /api/auth/login   — email + password → tokens
US-05: POST /api/auth/refresh  — refresh rotativo con family revocation
US-06: POST /api/auth/logout   — revocar refresh token
US-07: GET  /api/auth/me       — perfil del usuario autenticado
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.config import settings
from app.core.dependencies import get_current_active_user
from app.core.rate_limit import get_rate_limiter
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token_value,
    hash_refresh_token,
    verify_password,
)
from app.models.user import RefreshToken, User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


# ═══════════════════════════════════════════════════════════════
# US-04: Login
# ═══════════════════════════════════════════════════════════════


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Autentica usuario con email + contraseña.

    Anti-enumeración: Mismo mensaje para email inexistente vs contraseña incorrecta.
    US-13: Rate limiting por IP (5/min).
    US-14: Rate limiting por email (5/min).
    US-15: Bloqueo de cuenta tras LOGIN_MAX_ATTEMPTS fallos consecutivos.
    """
    # ─── US-13: Rate Limit por IP ──────────────────────
    client_ip = request.client.host if request.client else "unknown"
    limiter = get_rate_limiter(redis_url=settings.redis_url if settings.redis_url else None)

    ip_result = await limiter.check(f"login:ip:{client_ip}", max_requests=5, window_seconds=60)
    if not ip_result.allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts from this IP. Try again later.",
            headers={"Retry-After": str(ip_result.retry_after_seconds)},
        )

    # ─── US-14: Rate Limit por Email ───────────────────
    email_result = await limiter.check(f"login:email:{data.email}", max_requests=5, window_seconds=60)
    if not email_result.allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts for this email. Try again later.",
            headers={"Retry-After": str(email_result.retry_after_seconds)},
        )

    # Buscar usuario
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    # ─── Cuenta bloqueada ──────────────────────────────────
    if user and user.locked_until and user.locked_until > datetime.now(UTC):
        retry_seconds = int((user.locked_until - datetime.now(UTC)).total_seconds())
        raise HTTPException(
            status_code=423,
            detail=f"Account temporarily locked. Try again in {retry_seconds // 60 + 1} minutes.",
            headers={"Retry-After": str(retry_seconds)},
        )

    # ─── Verificar contraseña ──────────────────────────────
    password_ok = False
    if user:
        password_ok = verify_password(data.password, user.hashed_password)

    # ─── Anti-enumeración: mismo mensaje siempre ───────────
    if not user or not password_ok:
        if user:
            user.failed_login_attempts += 1
            # Bloqueo tras N fallos consecutivos
            if user.failed_login_attempts >= settings.login_max_attempts:
                user.locked_until = datetime.now(UTC) + timedelta(
                    minutes=settings.login_lock_minutes
                )
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # ─── Cuenta inactiva ──────────────────────────────────
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # ─── Login exitoso ─────────────────────────────────────
    # Resetear contador de fallos
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(UTC)

    # Crear tokens
    access_token = create_access_token(
        {
            "sub": str(user.id),
            "company_id": user.company_id,
            "role": user.role,
            "email": user.email,
        }
    )

    refresh_value = generate_refresh_token_value()
    refresh_hash = hash_refresh_token(refresh_value)
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

    refresh_record = RefreshToken(
        user_id=user.id,
        company_id=user.company_id,
        token_hash=refresh_hash,
        expires_at=expires_at,
        created_by_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:512],
    )
    db.add(refresh_record)
    await db.commit()
    await db.refresh(user)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_value,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


# ═══════════════════════════════════════════════════════════════
# US-05: Refresh Token (rotativo con family revocation)
# ═══════════════════════════════════════════════════════════════


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Renueva access token usando refresh token.

    Rotación: el token viejo se revoca, se emite uno nuevo.
    Family revocation: si se detecta reuso de token ya revocado →
    se revocan TODOS los tokens del usuario (posible robo de refresh token).
    """
    token_hash = hash_refresh_token(data.refresh_token)

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    rt = result.scalar_one_or_none()

    # Token no encontrado → genérico
    if not rt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    # ─── Token expirado ────────────────────────────────────
    if rt.expires_at < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )

    # ─── Family revocation: token YA revocado → revocar TODOS ──
    if rt.revoked_at is not None:
        # Posible robo de refresh token → revocar toda la familia
        await db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == rt.user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revoked — all sessions invalidated. Please login again.",
        )

    # ─── Rotación: revocar viejo, crear nuevo ──────────────
    now = datetime.now(UTC)
    rt.revoked_at = now

    # Nuevo refresh token
    new_refresh_value = generate_refresh_token_value()
    new_hash = hash_refresh_token(new_refresh_value)
    new_expires = now + timedelta(days=settings.refresh_token_expire_days)

    new_rt = RefreshToken(
        user_id=rt.user_id,
        company_id=rt.company_id,
        token_hash=new_hash,
        expires_at=new_expires,
        created_by_ip=rt.created_by_ip,
        user_agent=rt.user_agent,
        replaced_by_id=None,  # Se asigna tras flush
    )
    db.add(new_rt)
    await db.flush()

    # Vincular viejo → nuevo
    rt.replaced_by_id = new_rt.id
    await db.commit()

    # Obtener usuario para el payload del JWT
    result = await db.execute(select(User).where(User.id == rt.user_id))
    user = result.scalar_one()

    access_token = create_access_token(
        {
            "sub": str(user.id),
            "company_id": user.company_id,
            "role": user.role,
            "email": user.email,
        }
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_value,
        expires_in=settings.access_token_expire_minutes * 60,
    )


# ═══════════════════════════════════════════════════════════════
# US-06: Logout
# ═══════════════════════════════════════════════════════════════


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    data: LogoutRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Revoca un refresh token. Idempotente.
    """
    token_hash = hash_refresh_token(data.refresh_token)

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    rt = result.scalar_one_or_none()

    if rt and rt.revoked_at is None:
        rt.revoked_at = datetime.now(UTC)
        await db.commit()

    # Siempre 200 — no revelar si el token existía
    return LogoutResponse(message="Successfully logged out")


# ═══════════════════════════════════════════════════════════════
# US-07: Me (Perfil)
# ═══════════════════════════════════════════════════════════════


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Retorna perfil del usuario autenticado.
    No incluye campos sensibles (hashed_password, failed_login_attempts, etc).
    """
    return UserResponse.model_validate(current_user)
