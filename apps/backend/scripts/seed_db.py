#!/usr/bin/env python3
"""
Seed Data Script — Carga datos de prueba en PostgreSQL.

Crea datos reales para el MVP de IaaS-RonSys:
  - Empresa "El Segoviano"
  - Plan de cuentas PCGE (60+ cuentas)
  - Simulación financiera 12 meses con asientos persistidos
  - 5 productos de ejemplo
  - Movimientos de kárdex (entradas y salidas)

Uso:
  cd apps/backend
  python scripts/seed_db.py

Requisitos:
  - PostgreSQL corriendo (localhost:5432 o configurado en .env)
  - Variables en .env: DATABASE_URL
  - Python 3.12.x (⚠️ asyncpg NO compila en 3.13+)
"""

import asyncio
import sys
from datetime import date, datetime, UTC

# Verificar Python 3.12
_py_version = sys.version_info
if _py_version.major == 3 and _py_version.minor > 12:
    print("=" * 60)
    print("⚠️  ERROR: Se requiere Python 3.12.x exactamente")
    print(f"   Versión detectada: {_py_version.major}.{_py_version.minor}")
    print("   asyncpg/pydantic-core no compilan en Python 3.13+")
    print()
    print("   Usar Docker:  docker-compose up -d backend")
    print("=" * 60)
    sys.exit(1)


async def main():
    from app.config import settings
    from app.adapters.db.models.accounting import (
        Account,
        Base,
        Company,
        JournalEntry,
        JournalEntryLine,
        KardexMovement,
        Product,
    )
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy import text, select

    print("=" * 70)
    print("  🌱 IaaS-RonSys — Seed Data Script")
    print("=" * 70)

    # ─── Conexión ───────────────────────────────────
    print(f"\n🔌 Conectando a PostgreSQL: {settings.database_url[:60]}...")

    try:
        engine = create_async_engine(
            settings.database_url,
            echo=False,
        )
        async with engine.begin() as conn:
            # Verificar conexión
            await conn.execute(text("SELECT 1"))
        print("   ✅ Conexión exitosa")
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
        print("\n   Asegúrate de que PostgreSQL esté corriendo:")
        print("     docker-compose up -d postgres")
        await engine.dispose()
        sys.exit(1)

    # ─── Crear tablas (si no existen) ───────────────
    print("\n📦 Creando tablas...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("   ✅ Tablas listas")

    # ─── Crear Empresa ──────────────────────────────
    async with AsyncSession(engine) as session:
        # Verificar si ya existe
        existing = await session.execute(
            select(Company).where(Company.ruc == "10777555551")
        )
        company = existing.scalar_one_or_none()

        if company:
            print(f"\n🏢 Empresa ya existe: {company.name}")
            company_id = company.id
        else:
            company = Company(
                name="El Segoviano",
                ruc="10777555551",
                address="Av. Los Olivos 123, Lima",
                economic_activity="Restaurante - Venta de comidas y bebidas",
                setup_complete=False,
            )
            session.add(company)
            await session.flush()
            company_id = company.id
            print(f"\n🏢 Empresa creada: {company.name} (ID: {company_id})")

        # ─── Sembrar Plan de Cuentas ───────────────
        existing_accounts = await session.execute(
            select(Account).limit(1)
        )
        if existing_accounts.scalar_one_or_none():
            print("📋 Plan de cuentas ya existe")
        else:
            accounts_data = _get_chart_of_accounts()
            for acct in accounts_data:
                session.add(Account(**acct))
            await session.flush()
            print(f"📋 Plan de cuentas sembrado: {len(accounts_data)} cuentas")

        # ─── Ejecutar Simulación Financiera ─────────
        from app.core.accounting import (
            FinancialStatementService,
            InvestmentVariables,
        )

        # Verificar si ya hay asientos
        existing_entries = await session.execute(
            select(JournalEntry).where(JournalEntry.company_id == company_id).limit(1)
        )
        if existing_entries.scalar_one_or_none():
            print("📊 Asientos ya existen — omitiendo simulación")
        else:
            vars_ = InvestmentVariables(
                capital=50000.0,
                loan_amount=30000.0,
                loan_rate_annual=0.12,
                loan_term_months=12,
                equipment_cost=20000.0,
                furniture_cost=5000.0,
                computer_cost=3000.0,
                software_cost=1000.0,
                guarantee_deposit=3000.0,
                initial_inventory=5000.0,
                monthly_sales=[25000.0] * 12,
                monthly_cost_pct=0.40,
                monthly_rent=1500.0,
                monthly_utilities=800.0,
                monthly_salaries=5000.0,
                monthly_marketing=500.0,
                monthly_admin=300.0,
                monthly_maintenance=200.0,
                equipment_life_years=8,
                furniture_life_years=10,
                computer_life_years=5,
                software_life_years=3,
            )

            report = FinancialStatementService.run_simulation(
                vars_, months=12, start_date=date(2026, 1, 1)
            )

            # Persistir asientos
            for entry in report.journal:
                je = JournalEntry(
                    company_id=company_id,
                    entry_number=entry.entry_number,
                    date=entry.date_,
                    description=entry.description,
                    entry_type=entry.entry_type.value
                    if hasattr(entry.entry_type, "value")
                    else str(entry.entry_type),
                    reference=entry.reference,
                )
                for line in entry.lines:
                    je.lines.append(
                        JournalEntryLine(
                            account_code=line.account_code,
                            debit=line.debit,
                            credit=line.credit,
                            description=line.description,
                        )
                    )
                session.add(je)

            await session.flush()

            pyg = report.income_statement
            print(f"📊 Simulación completada: {len(report.journal)} asientos")
            print(f"   Ventas: S/ {pyg.revenue:,.2f}")
            print(f"   Utilidad Neta: S/ {pyg.net_income:,.2f}")
            print(
                f"   Balance: {'✅ Cuadra' if report.validations.get('balance_sheet_balanced') else '❌ No cuadra'}"
            )

        await session.commit()

    # ─── Segunda Empresa: Ferretería ───────────────
    async with AsyncSession(engine) as session:
        existing_ferreteria = await session.execute(
            select(Company).where(Company.ruc == "20777555552")
        )
        ferreteria = existing_ferreteria.scalar_one_or_none()
        if ferreteria:
            print(f"\n🏢 Ferretería ya existe: {ferreteria.name} (ID: {ferreteria.id})")
            company_id_hardware = ferreteria.id
        else:
            ferreteria = Company(
                name="Ferretería El Segoviano",
                ruc="20777555552",
                address="Av. Los Industriales 456, Lima",
                economic_activity="Venta de materiales de construcción y ferretería",
                business_type="hardware",
                setup_complete=False,
            )
            session.add(ferreteria)
            await session.flush()
            company_id_hardware = ferreteria.id
            print(f"\n🏢 Ferretería creada: {ferreteria.name} (ID: {company_id_hardware})")
        await session.commit()

    # ─── Usuarios Demo ──────────────────────────────
    async with AsyncSession(engine) as session:
        from app.models.user import User
        from pwdlib import PasswordHash
        from pwdlib.hashers.argon2 import Argon2Hasher

        # Verificar si ya existen usuarios
        existing_users = await session.execute(
            select(User).where(User.email.in_([
                "admin@elsegoviano.pe",
                "ferretero@elsegoviano.pe",
                "mesero1@elsegoviano.pe",
                "cocinero1@elsegoviano.pe",
            ]))
        )
        existing_emails = {u.email for u in existing_users.scalars().all()}

        if len(existing_emails) == 4:
            print("👤 Usuarios demo ya existen — omitiendo")
        else:
            ph = PasswordHash([Argon2Hasher()])
            now_utc = datetime.now(UTC)

            users_to_create = [
                {
                    "email": "admin@elsegoviano.pe",
                    "password": "admin123",
                    "full_name": "Admin Restaurante",
                    "role": "admin",
                    "tenant_id": company_id,
                },
                {
                    "email": "ferretero@elsegoviano.pe",
                    "password": "ferreteria123",
                    "full_name": "Admin Ferretería",
                    "role": "admin",
                    "tenant_id": company_id_hardware,
                },
                {
                    "email": "mesero1@elsegoviano.pe",
                    "password": "mesero123",
                    "full_name": "Mesero 1",
                    "role": "operator",
                    "tenant_id": company_id,
                },
                {
                    "email": "cocinero1@elsegoviano.pe",
                    "password": "cocinero123",
                    "full_name": "Cocinero 1",
                    "role": "operator",
                    "tenant_id": company_id,
                },
            ]

            created = 0
            skipped = 0
            for u in users_to_create:
                if u["email"] in existing_emails:
                    skipped += 1
                    continue
                user = User(
                    email=u["email"],
                    hashed_password=ph.hash(u["password"]),
                    full_name=u["full_name"],
                    role=u["role"],
                    tenant_id=u["tenant_id"],
                    is_active=True,
                    is_verified=True,
                    failed_login_attempts=0,
                )
                session.add(user)
                created += 1

            await session.commit()
            print(f"👤 Usuarios demo: {created} creados, {skipped} ya existían")
            for u in users_to_create:
                if u["email"] not in existing_emails:
                    print(f"   ✅ {u['email']} ({u['role']}) → {u['password']}")

    # ─── Categorías de Producto (datos maestros) ────
    # Usamos SQL directo para evitar dependencias del ORM con columnas
    # que la migración 0008 puede o no haber creado aún.
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT COUNT(*) FROM product_categories WHERE tenant_id = :tid"),
            {"tid": company_id}
        )
        count = result.scalar()
        if count and count > 0:
            print(f"📂 Categorías ya existen ({count}) — omitiendo")
        else:
            # Categorías para Restaurante
            restaurant_cats = [
                (company_id, "Carnes"),
                (company_id, "Abarrotes"),
                (company_id, "Lácteos"),
                (company_id, "Bebidas"),
                (company_id, "Frutas y Verduras"),
                (company_id, "Condimentos"),
            ]
            # Categorías para Ferretería
            hardware_cats = [
                (company_id_hardware, "Materiales de Construcción"),
                (company_id_hardware, "Ferretería General"),
                (company_id_hardware, "Pinturas"),
                (company_id_hardware, "Electricidad"),
                (company_id_hardware, "Gasfitería"),
            ]
            all_cats = restaurant_cats + hardware_cats
            for tid, name in all_cats:
                await conn.execute(
                    text("INSERT INTO product_categories (tenant_id, name) VALUES (:tid, :name)"),
                    {"tid": tid, "name": name}
                )
            print(f"📂 Categorías sembradas: {len(restaurant_cats)} (restaurante) + {len(hardware_cats)} (ferretería)")

    # ─── Secciones demo (Restaurante) ──────────────
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT COUNT(*) FROM restaurant_sections WHERE tenant_id = :tid"),
            {"tid": company_id},
        )
        count = result.scalar()
        if count and count > 0:
            print(f"🍽️ Secciones ya existen ({count}) — omitiendo")
        else:
            sections = [
                (company_id, "Sala Principal", 1),
                (company_id, "Terraza", 2),
                (company_id, "Segundo Nivel", 3),
            ]
            for tid, name, sort_order in sections:
                await conn.execute(
                    text(
                        "INSERT INTO restaurant_sections (tenant_id, name, sort_order, created_at, updated_at) "
                        "VALUES (:tid, :name, :sort_order, NOW(), NOW())"
                    ),
                    {"tid": tid, "name": name, "sort_order": sort_order},
                )
            print(f"🍽️ Secciones sembradas: {len(sections)} para El Segoviano")

    # ─── Productos y Kárdex ────────────────────────
    async with AsyncSession(engine) as session:
        # Buscar categorías por nombre para asignarlas a los productos (SQL directo)
        cat_map = {}
        result = await session.execute(
            text("SELECT id, name FROM product_categories WHERE tenant_id = :tid"),
            {"tid": company_id}
        )
        for row in result.all():
            cat_map[row[1]] = row[0]

        existing_products = await session.execute(
            select(Product).where(Product.tenant_id == company_id).limit(1)
        )
        if existing_products.scalar_one_or_none():
            print("📦 Productos ya existen — omitiendo")
        else:
            products_data = [
                {"code": "INS-001", "name": "Pollo (pechuga)", "unit": "kg", "stock": 30, "cost": 12.50, "category": "Carnes"},
                {"code": "INS-002", "name": "Cerdo (lomo)", "unit": "kg", "stock": 15, "cost": 14.00, "category": "Carnes"},
                {"code": "INS-003", "name": "Papa amarilla", "unit": "kg", "stock": 50, "cost": 3.00, "category": "Frutas y Verduras"},
                {"code": "INS-004", "name": "Aceite vegetal", "unit": "litro", "stock": 20, "cost": 8.50, "category": "Condimentos"},
                {"code": "INS-005", "name": "Arroz", "unit": "kg", "stock": 100, "cost": 3.50, "category": "Abarrotes"},
            ]

            # Store product info before commit to avoid detached instance errors
            product_info = []
            for pdata in products_data:
                p = Product(
                    tenant_id=company_id,
                    code=pdata["code"],
                    name=pdata["name"],
                    unit_of_measure=pdata["unit"],
                    current_stock=pdata["stock"],
                    average_cost=pdata["cost"],
                    category_id=cat_map.get(pdata["category"]),
                )
                session.add(p)
                product_info.append((pdata["code"], pdata["name"], pdata["stock"], pdata["unit"], pdata["cost"]))
            await session.flush()

            # Get product IDs after flush
            created_products = []
            for pdata in products_data:
                result = await session.execute(
                    select(Product).where(Product.code == pdata["code"])
                )
                p = result.scalar_one()
                created_products.append((p, pdata["cost"]))

            # Generar movimientos de kárdex (entradas iniciales)
            for p, cost in created_products:
                qty = float(p.current_stock)
                km = KardexMovement(
                    product_id=p.id,
                    movement_type="entrada",
                    concept="Inventario inicial",
                    reference_type="inventario_inicial",
                    quantity=qty,
                    unit_cost=cost,
                    total=round(qty * cost, 2),
                    balance_quantity=qty,
                    balance_avg_cost=cost,
                    balance_total=round(qty * cost, 2),
                    date=date(2026, 1, 1),
                )
                session.add(km)

            await session.commit()

            print(f"📦 {len(product_info)} productos registrados:")
            for code, name, stock, unit, cost in product_info:
                print(f"   {code} — {name}: {stock} {unit} × S/ {cost}")

    # ─── Resumen Final ──────────────────────────────
    async with AsyncSession(engine) as session:
        from app.models.user import User
        company_count = (await session.execute(select(Company))).scalars().all()
        accounts_count = (await session.execute(select(Account))).scalars().all()
        entries_count = (await session.execute(select(JournalEntry))).scalars().all()
        products_count = (await session.execute(select(Product))).scalars().all()
        km_count = (await session.execute(select(KardexMovement))).scalars().all()
        users_count = (await session.execute(select(User))).scalars().all()
        categories_count = (await session.execute(text("SELECT COUNT(*) FROM product_categories"))).scalar() or 0

    await engine.dispose()

    print("\n" + "=" * 70)
    print("  ✅ Seed Data completado")
    print(f"  🏢 Empresas:       {len(company_count)}")
    print(f"  👤 Usuarios:       {len(users_count)}")
    print(f"  📋 Cuentas:        {len(accounts_count)}")
    print(f"  📝 Asientos:       {len(entries_count)}")
    print(f"  📂 Categorías:     {categories_count}")
    print(f"  📦 Productos:      {len(products_count)}")
    print(f"  📊 Mov. Kárdex:    {len(km_count)}")
    print("=" * 70)


def _get_chart_of_accounts() -> list[dict]:
    """Plan de cuentas PCGE peruano adaptado."""
    return [
        # Activo
        {"code": "10", "name": "Efectivo y Equivalentes", "nature": "D", "category": "asset", "is_balance_sheet": True},
        {"code": "101", "name": "Caja", "parent_code": "10", "nature": "D", "category": "asset", "is_balance_sheet": True},
        {"code": "102", "name": "Bancos", "parent_code": "10", "nature": "D", "category": "asset", "is_balance_sheet": True},
        {"code": "11", "name": "Cuentas por Cobrar", "nature": "D", "category": "asset", "is_balance_sheet": True},
        {"code": "12", "name": "Inventarios", "nature": "D", "category": "asset", "is_balance_sheet": True},
        {"code": "121", "name": "Insumos de cocina", "parent_code": "12", "nature": "D", "category": "asset", "is_balance_sheet": True},
        {"code": "13", "name": "Inmuebles, Maquinaria y Equipo", "nature": "D", "category": "asset", "is_balance_sheet": True},
        {"code": "131", "name": "Equipamiento de cocina", "parent_code": "13", "nature": "D", "category": "asset", "is_balance_sheet": True},
        {"code": "132", "name": "Mobiliario del local", "parent_code": "13", "nature": "D", "category": "asset", "is_balance_sheet": True},
        {"code": "133", "name": "Equipos de cómputo", "parent_code": "13", "nature": "D", "category": "asset", "is_balance_sheet": True},
        {"code": "14", "name": "Activos Intangibles", "nature": "D", "category": "asset", "is_balance_sheet": True},
        {"code": "141", "name": "Software (ERP, licencias)", "parent_code": "14", "nature": "D", "category": "asset", "is_balance_sheet": True},
        {"code": "15", "name": "Depósitos en Garantía", "nature": "D", "category": "asset", "is_balance_sheet": True},
        {"code": "151", "name": "Garantía de alquiler", "parent_code": "15", "nature": "D", "category": "asset", "is_balance_sheet": True},
        {"code": "19", "name": "Depreciación Acumulada", "nature": "A", "category": "contra_asset", "is_balance_sheet": True},
        {"code": "191", "name": "Dep. Acum. Equipamiento", "parent_code": "19", "nature": "A", "category": "contra_asset", "is_balance_sheet": True},
        {"code": "192", "name": "Dep. Acum. Mobiliario", "parent_code": "19", "nature": "A", "category": "contra_asset", "is_balance_sheet": True},
        {"code": "193", "name": "Dep. Acum. Cómputo", "parent_code": "19", "nature": "A", "category": "contra_asset", "is_balance_sheet": True},
        # Pasivo
        {"code": "20", "name": "Tributos por Pagar", "nature": "A", "category": "liability", "is_balance_sheet": True},
        {"code": "202", "name": "Impuesto a la Renta por pagar", "parent_code": "20", "nature": "A", "category": "liability", "is_balance_sheet": True},
        {"code": "21", "name": "Cuentas por Pagar Comerciales", "nature": "A", "category": "liability", "is_balance_sheet": True},
        {"code": "22", "name": "Préstamos Bancarios", "nature": "A", "category": "liability", "is_balance_sheet": True},
        {"code": "221", "name": "Préstamo CP", "parent_code": "22", "nature": "A", "category": "liability", "is_balance_sheet": True},
        {"code": "222", "name": "Préstamo LP", "parent_code": "22", "nature": "A", "category": "liability", "is_balance_sheet": True},
        {"code": "23", "name": "Remuneraciones por Pagar", "nature": "A", "category": "liability", "is_balance_sheet": True},
        {"code": "24", "name": "Cuentas por Pagar Varias", "nature": "A", "category": "liability", "is_balance_sheet": True},
        # Patrimonio
        {"code": "30", "name": "Capital", "nature": "A", "category": "equity", "is_balance_sheet": True},
        {"code": "301", "name": "Aporte de socios", "parent_code": "30", "nature": "A", "category": "equity", "is_balance_sheet": True},
        {"code": "31", "name": "Resultados Acumulados", "nature": "A", "category": "equity", "is_balance_sheet": True},
        {"code": "32", "name": "Resultado del Ejercicio", "nature": "A", "category": "equity", "is_balance_sheet": True},
        # Ingresos
        {"code": "40", "name": "Ventas", "nature": "A", "category": "income", "is_balance_sheet": False},
        {"code": "401", "name": "Venta de platos y bebidas", "parent_code": "40", "nature": "A", "category": "income", "is_balance_sheet": False},
        # Costos
        {"code": "50", "name": "Costo de Ventas", "nature": "D", "category": "cost", "is_balance_sheet": False},
        {"code": "501", "name": "Materia prima e insumos", "parent_code": "50", "nature": "D", "category": "cost", "is_balance_sheet": False},
        # Gastos
        {"code": "60", "name": "Gastos de Personal", "nature": "D", "category": "expense", "is_balance_sheet": False},
        {"code": "601", "name": "Sueldos y salarios", "parent_code": "60", "nature": "D", "category": "expense", "is_balance_sheet": False},
        {"code": "61", "name": "Gastos de Operación", "nature": "D", "category": "expense", "is_balance_sheet": False},
        {"code": "611", "name": "Alquiler del local", "parent_code": "61", "nature": "D", "category": "expense", "is_balance_sheet": False},
        {"code": "612", "name": "Servicios públicos", "parent_code": "61", "nature": "D", "category": "expense", "is_balance_sheet": False},
        {"code": "613", "name": "Mantenimiento", "parent_code": "61", "nature": "D", "category": "expense", "is_balance_sheet": False},
        {"code": "62", "name": "Gastos de Ventas y Marketing", "nature": "D", "category": "expense", "is_balance_sheet": False},
        {"code": "621", "name": "Publicidad y redes", "parent_code": "62", "nature": "D", "category": "expense", "is_balance_sheet": False},
        {"code": "63", "name": "Gastos Administrativos", "nature": "D", "category": "expense", "is_balance_sheet": False},
        {"code": "631", "name": "Útiles de oficina", "parent_code": "63", "nature": "D", "category": "expense", "is_balance_sheet": False},
        {"code": "64", "name": "Gastos Financieros", "nature": "D", "category": "expense", "is_balance_sheet": False},
        {"code": "641", "name": "Intereses de préstamo", "parent_code": "64", "nature": "D", "category": "expense", "is_balance_sheet": False},
        {"code": "65", "name": "Depreciación", "nature": "D", "category": "expense", "is_balance_sheet": False},
        {"code": "66", "name": "Otros Gastos", "nature": "D", "category": "expense", "is_balance_sheet": False},
        # Cierre
        {"code": "80", "name": "Resumen de Resultados", "nature": "A", "category": "closing", "is_balance_sheet": False},
        {"code": "81", "name": "Pérdidas y Ganancias", "nature": "A", "category": "closing", "is_balance_sheet": False},
    ]


if __name__ == "__main__":
    asyncio.run(main())
