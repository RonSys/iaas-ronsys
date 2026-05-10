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
from datetime import date

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

    # ─── Productos y Kárdex ────────────────────────
    async with AsyncSession(engine) as session:
        existing_products = await session.execute(
            select(Product).where(Product.company_id == company_id).limit(1)
        )
        if existing_products.scalar_one_or_none():
            print("📦 Productos ya existen — omitiendo")
        else:
            products_data = [
                {"code": "INS-001", "name": "Pollo (pechuga)", "unit": "kg", "stock": 30, "cost": 12.50},
                {"code": "INS-002", "name": "Cerdo (lomo)", "unit": "kg", "stock": 15, "cost": 14.00},
                {"code": "INS-003", "name": "Papa amarilla", "unit": "kg", "stock": 50, "cost": 3.00},
                {"code": "INS-004", "name": "Aceite vegetal", "unit": "litro", "stock": 20, "cost": 8.50},
                {"code": "INS-005", "name": "Arroz", "unit": "kg", "stock": 100, "cost": 3.50},
            ]

            # Store product info before commit to avoid detached instance errors
            product_info = []
            for pdata in products_data:
                p = Product(
                    company_id=company_id,
                    code=pdata["code"],
                    name=pdata["name"],
                    unit_of_measure=pdata["unit"],
                    current_stock=pdata["stock"],
                    average_cost=pdata["cost"],
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
        company_count = (await session.execute(select(Company))).scalars().all()
        accounts_count = (await session.execute(select(Account))).scalars().all()
        entries_count = (await session.execute(select(JournalEntry))).scalars().all()
        products_count = (await session.execute(select(Product))).scalars().all()
        km_count = (await session.execute(select(KardexMovement))).scalars().all()

    await engine.dispose()

    print("\n" + "=" * 70)
    print("  ✅ Seed Data completado")
    print(f"  🏢 Empresas:       {len(company_count)}")
    print(f"  📋 Cuentas:        {len(accounts_count)}")
    print(f"  📝 Asientos:       {len(entries_count)}")
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
