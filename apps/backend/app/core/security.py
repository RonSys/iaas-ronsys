"""
🔐 Core Security — JWT + Password Hashing.

US-01: Funciones de seguridad base para autenticación.

Librerías:
  - PyJWT[crypto] (no python-jose — sin mantenimiento)
  - pwdlib[argon2] (no passlib — sin mantenimiento)
  - Argon2id por defecto (ganador Password Hashing Competition, recomendado OWASP)

Timing: pwdlib.verify() es constant-time por defecto.
"""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.config import settings

# ─── Password Hashing ────────────────────────────────────────

_password_hash = PasswordHash([Argon2Hasher()])


def hash_password(password: str) -> str:
    """
    Hashea contraseña con Argon2id (salt aleatorio en cada llamada).
    """
    return _password_hash.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verifica contraseña contra hash.
    Constant-time por defecto (pwdlib usa Argon2id nativo).
    """
    return _password_hash.verify(plain, hashed)


def verify_and_update_password(plain: str, hashed: str) -> tuple[bool, str]:
    """
    Verifica contraseña y actualiza el hash si es necesario (ej: si cambió
    la configuración de Argon2 entre versiones). Retorna (ok, hash_actualizado).
    """
    should_update = _password_hash.check_needs_rehash(hashed)
    ok = _password_hash.verify(plain, hashed)
    if ok and should_update:
        return True, _password_hash.hash(plain)
    return ok, hashed


# ─── JWT ────────────────────────────────────────────────────


def create_access_token(data: dict[str, Any]) -> str:
    """
    Crea JWT HS256 con payload extendido.

    data debe contener 'sub' (user_id como string).
    Se agregan automáticamente: exp, iat, jti.
    """
    now = datetime.now(UTC)
    payload = {
        **data,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "iat": now,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decodifica y valida un JWT.

    Raises:
      jwt.ExpiredSignatureError: token expirado
      jwt.InvalidTokenError: firma inválida, malformado, etc.
    """
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=["HS256"],
        options={"require": ["exp", "iat", "sub", "jti"]},
    )


# ─── Refresh Tokens ─────────────────────────────────────────


def generate_refresh_token_value() -> str:
    """Genera un refresh token opaco (UUID v4)."""
    return uuid.uuid4().hex


def hash_refresh_token(token: str) -> str:
    """
    Hashea el refresh token con SHA-256 para almacenar en BD.
    No se guarda el token en texto plano.
    """
    return hashlib.sha256(token.encode()).hexdigest()
