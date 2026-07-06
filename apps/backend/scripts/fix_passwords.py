#!/usr/bin/env python3
"""Fix all user passwords with correct values."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASSWORDS = {
    "admin@iaas.com": "Admin2026!",
    "demo@iaas.com": "Demo2026!",
    "admin@elsegoviano.pe": "admin123",
    "ferretero@elsegoviano.pe": "ferreteria123",
    "mesero1@elsegoviano.pe": "mesero123",
    "cocinero1@elsegoviano.pe": "cocinero123",
    "mesero2@elsegoviano.pe": "mesero2026",
    "gestor@elsegoviano.pe": "Gestor2026!",
}


async def main():
    from pwdlib import PasswordHash
    from pwdlib.hashers.argon2 import Argon2Hasher
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    ph = PasswordHash([Argon2Hasher()])
    engine = create_async_engine("postgresql+asyncpg://ron:ron123@postgres:5432/iaas_ronsys")

    async with engine.begin() as conn:
        for email, pw in PASSWORDS.items():
            hashed = ph.hash(pw)
            await conn.execute(
                text("UPDATE users SET hashed_password = :pw, failed_login_attempts = 0, locked_until = NULL WHERE email = :email"),
                {"pw": hashed, "email": email},
            )
            print(f"  OK {email}")

    await engine.dispose()
    print("All passwords fixed!")


if __name__ == "__main__":
    asyncio.run(main())
