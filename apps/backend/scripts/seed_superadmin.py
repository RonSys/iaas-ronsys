#!/usr/bin/env python3
"""
Seed Superadmin — Crea el superadmin del sistema.

Crea:
  1. Superadmin: admin@iaas.com / Admin2026!
  2. Corrige password de demo@iaas.com -> Demo2026!

Uso:
  docker cp seed_superadmin.py iaas-backend-prod:/app/scripts/seed_superadmin.py
  docker exec iaas-backend-prod python /app/scripts/seed_superadmin.py
"""

import asyncio
import sys

SA_PASS = "Admin2026!"
DEMO_PASS = "Demo2026!"


async def main():
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy import select
    from pwdlib import PasswordHash
    from pwdlib.hashers.argon2 import Argon2Hasher
    from app.models.user import User

    database_url = "postgresql+asyncpg://ron:ron123@postgres:5432/iaas_ronsys"
    engine = create_async_engine(database_url, echo=False)
    ph = PasswordHash([Argon2Hasher()])

    async with AsyncSession(engine) as session:
        # 1. Crear/actualizar Superadmin
        superadmin = await session.execute(
            select(User).where(User.email == "admin@iaas.com")
        )
        existing = superadmin.scalar_one_or_none()

        if existing:
            print(f"Superadmin ya existe: {existing.email} (ID: {existing.id})")
            existing.hashed_password = ph.hash(SA_PASS)
            existing.role = "superadmin"
            existing.tenant_id = None
            existing.is_active = True
            existing.is_verified = True
            await session.commit()
            print("Password/role actualizados")
        else:
            user = User(
                email="admin@iaas.com",
                hashed_password=ph.hash(SA_PASS),
                full_name="Rony Supo",
                role="superadmin",
                tenant_id=None,
                is_active=True,
                is_verified=True,
                failed_login_attempts=0,
            )
            session.add(user)
            await session.commit()
            print("Superadmin creado: admin@iaas.com / " + SA_PASS)

        # 2. Corregir password de demo
        demo = await session.execute(
            select(User).where(User.email == "demo@iaas.com")
        )
        demo_user = demo.scalar_one_or_none()
        if demo_user:
            demo_user.hashed_password = ph.hash(DEMO_PASS)
            await session.commit()
            print("Password de demo@iaas.com corregida a: " + DEMO_PASS)

    await engine.dispose()
    print("Seed completado")


if __name__ == "__main__":
    asyncio.run(main())
