#!/usr/bin/env python3
"""
Seed Clean v1.0 — Restaura BD y carga datos demo limpios.
"""

import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession


async def main():
    from app.config import settings
    from app.core.security import hash_password

    print("=" * 70)
    print("  IaaS-RonSys --- Seed Clean v1.0")
    print("=" * 70)

    engine = create_async_engine(settings.database_url, echo=False)

    # --- 1. Limpiar tablas ---
    async with engine.begin() as conn:
        print("\nLimpiando datos existentes...")
        tables = [
            "recipe_ingredients", "recipes", "menu_modifiers", "kitchen_orders",
            "takeaway_orders", "sale_payments", "sale_items", "restaurant_sales",
            "pos_sessions", "tables", "restaurant_sections", "menu_items",
            "kardex_movements", "journal_entry_lines", "journal_entries",
            "hardware_sales", "sales", "scenarios", "accounts",
            "product_units", "product_categories", "products",
            "cashflow_projections", "refresh_tokens", "users", "companies",
        ]
        for tbl in tables:
            try:
                await conn.execute(text(f"DELETE FROM {tbl} CASCADE"))
            except Exception:
                pass
        print("  Datos limpiados")

    # --- 2. Insertar datos demo ---
    async with AsyncSession(engine) as session:
        # Companies
        print("\nCreando empresas...")
        await session.execute(text("""
            INSERT INTO companies (id, name, ruc, address, business_type, setup_complete, settings)
            VALUES
              (2, 'El Segoviano', '10777555551', 'Av. Los Olivos 123, Lima',
               'restaurant', true, '{"color_scheme": "blue", "language": "es"}'),
              (4, 'Ferreteria El Segoviano', '20777555552', 'Av. Los Industriales 456, Lima',
               'hardware', true, '{"color_scheme": "green", "language": "es"}')
        """))
        await session.commit()

        # PCGE Chart of Accounts
        print("Creando plan de cuentas contables (PCGE)...")
        accounts_data = [
            {"code": "10", "name": "Efectivo y Equivalentes", "nature": "D", "category": "asset", "is_balance_sheet": True, "active": True },
            {"code": "101", "name": "Caja", "parent_code": "10", "nature": "D", "category": "asset", "is_balance_sheet": True, "active": True },
            {"code": "102", "name": "Bancos", "parent_code": "10", "nature": "D", "category": "asset", "is_balance_sheet": True, "active": True },
            {"code": "11", "name": "Cuentas por Cobrar", "nature": "D", "category": "asset", "is_balance_sheet": True, "active": True },
            {"code": "12", "name": "Inventarios", "nature": "D", "category": "asset", "is_balance_sheet": True, "active": True },
            {"code": "121", "name": "Insumos de cocina", "parent_code": "12", "nature": "D", "category": "asset", "is_balance_sheet": True, "active": True },
            {"code": "13", "name": "Inmuebles, Maquinaria y Equipo", "nature": "D", "category": "asset", "is_balance_sheet": True, "active": True },
            {"code": "131", "name": "Equipamiento de cocina", "parent_code": "13", "nature": "D", "category": "asset", "is_balance_sheet": True, "active": True },
            {"code": "132", "name": "Mobiliario del local", "parent_code": "13", "nature": "D", "category": "asset", "is_balance_sheet": True, "active": True },
            {"code": "133", "name": "Equipos de computo", "parent_code": "13", "nature": "D", "category": "asset", "is_balance_sheet": True, "active": True },
            {"code": "14", "name": "Activos Intangibles", "nature": "D", "category": "asset", "is_balance_sheet": True, "active": True },
            {"code": "141", "name": "Software (ERP, licencias)", "parent_code": "14", "nature": "D", "category": "asset", "is_balance_sheet": True, "active": True },
            {"code": "15", "name": "Depositos en Garantia", "nature": "D", "category": "asset", "is_balance_sheet": True, "active": True },
            {"code": "151", "name": "Garantia de alquiler", "parent_code": "15", "nature": "D", "category": "asset", "is_balance_sheet": True, "active": True },
            {"code": "19", "name": "Depreciacion Acumulada", "nature": "A", "category": "contra_asset", "is_balance_sheet": True, "active": True },
            {"code": "191", "name": "Dep. Acum. Equipamiento", "parent_code": "19", "nature": "A", "category": "contra_asset", "is_balance_sheet": True, "active": True },
            {"code": "192", "name": "Dep. Acum. Mobiliario", "parent_code": "19", "nature": "A", "category": "contra_asset", "is_balance_sheet": True, "active": True },
            {"code": "193", "name": "Dep. Acum. Computo", "parent_code": "19", "nature": "A", "category": "contra_asset", "is_balance_sheet": True, "active": True },
            {"code": "20", "name": "Tributos por Pagar", "nature": "A", "category": "liability", "is_balance_sheet": True, "active": True },
            {"code": "202", "name": "Impuesto a la Renta por pagar", "parent_code": "20", "nature": "A", "category": "liability", "is_balance_sheet": True, "active": True },
            {"code": "21", "name": "Cuentas por Pagar Comerciales", "nature": "A", "category": "liability", "is_balance_sheet": True, "active": True },
            {"code": "22", "name": "Prestamos Bancarios", "nature": "A", "category": "liability", "is_balance_sheet": True, "active": True },
            {"code": "221", "name": "Prestamo CP", "parent_code": "22", "nature": "A", "category": "liability", "is_balance_sheet": True, "active": True },
            {"code": "222", "name": "Prestamo LP", "parent_code": "22", "nature": "A", "category": "liability", "is_balance_sheet": True, "active": True },
            {"code": "23", "name": "Remuneraciones por Pagar", "nature": "A", "category": "liability", "is_balance_sheet": True, "active": True },
            {"code": "24", "name": "Cuentas por Pagar Varias", "nature": "A", "category": "liability", "is_balance_sheet": True, "active": True },
            {"code": "30", "name": "Capital", "nature": "A", "category": "equity", "is_balance_sheet": True, "active": True },
            {"code": "301", "name": "Aporte de socios", "parent_code": "30", "nature": "A", "category": "equity", "is_balance_sheet": True, "active": True },
            {"code": "31", "name": "Resultados Acumulados", "nature": "A", "category": "equity", "is_balance_sheet": True, "active": True },
            {"code": "32", "name": "Resultado del Ejercicio", "nature": "A", "category": "equity", "is_balance_sheet": True, "active": True },
            {"code": "40", "name": "Ventas", "nature": "A", "category": "income", "is_balance_sheet": False, "active": True },
            {"code": "401", "name": "Venta de platos y bebidas", "parent_code": "40", "nature": "A", "category": "income", "is_balance_sheet": False, "active": True },
            {"code": "50", "name": "Costo de Ventas", "nature": "D", "category": "cost", "is_balance_sheet": False, "active": True },
            {"code": "501", "name": "Materia prima e insumos", "parent_code": "50", "nature": "D", "category": "cost", "is_balance_sheet": False, "active": True },
            {"code": "60", "name": "Gastos de Personal", "nature": "D", "category": "expense", "is_balance_sheet": False, "active": True },
            {"code": "601", "name": "Sueldos y salarios", "parent_code": "60", "nature": "D", "category": "expense", "is_balance_sheet": False, "active": True },
            {"code": "61", "name": "Gastos de Operacion", "nature": "D", "category": "expense", "is_balance_sheet": False, "active": True },
            {"code": "611", "name": "Alquiler del local", "parent_code": "61", "nature": "D", "category": "expense", "is_balance_sheet": False, "active": True },
            {"code": "612", "name": "Servicios publicos", "parent_code": "61", "nature": "D", "category": "expense", "is_balance_sheet": False, "active": True },
            {"code": "613", "name": "Mantenimiento", "parent_code": "61", "nature": "D", "category": "expense", "is_balance_sheet": False, "active": True },
            {"code": "62", "name": "Gastos de Ventas y Marketing", "nature": "D", "category": "expense", "is_balance_sheet": False, "active": True },
            {"code": "621", "name": "Publicidad y redes", "parent_code": "62", "nature": "D", "category": "expense", "is_balance_sheet": False, "active": True },
            {"code": "63", "name": "Gastos Administrativos", "nature": "D", "category": "expense", "is_balance_sheet": False, "active": True },
            {"code": "631", "name": "Utiles de oficina", "parent_code": "63", "nature": "D", "category": "expense", "is_balance_sheet": False, "active": True },
            {"code": "64", "name": "Gastos Financieros", "nature": "D", "category": "expense", "is_balance_sheet": False, "active": True },
            {"code": "641", "name": "Intereses de prestamo", "parent_code": "64", "nature": "D", "category": "expense", "is_balance_sheet": False, "active": True },
            {"code": "65", "name": "Depreciacion", "nature": "D", "category": "expense", "is_balance_sheet": False, "active": True },
            {"code": "66", "name": "Otros Gastos", "nature": "D", "category": "expense", "is_balance_sheet": False, "active": True },
            {"code": "80", "name": "Resumen de Resultados", "nature": "A", "category": "closing", "is_balance_sheet": False, "active": True },
            {"code": "81", "name": "Perdidas y Ganancias", "nature": "A", "category": "closing", "is_balance_sheet": False, "active": True },
        ]
        for acct in accounts_data:
            await session.execute(text(
                f"INSERT INTO accounts (code, name, nature, category, is_balance_sheet, active) "
                f"VALUES ('{acct['code']}', '{acct['name']}', '{acct['nature']}', '{acct['category']}', {str(acct['is_balance_sheet']).lower()}, true)"
            ))
        print(f"  {len(accounts_data)} cuentas contables creadas")
        await session.commit()

        # Users
        print("Creando usuarios demo...")
        users_data = [
            (5,  "admin@elsegoviano.pe", "admin123", "Admin Restaurante",  "admin",    2),
            (6,  "demo@iaas.com",        "demo123",  "Usuario Demo",       "operator", 2),
            (9,  "ferretero@elsegoviano.pe", "ferreteria123", "Admin Ferreteria", "admin", 4),
            (10, "mesero1@elsegoviano.pe",   "mesero123",   "Mesero 1",          "operator", 2),
            (11, "cocinero1@elsegoviano.pe", "cocinero123", "Cocinero 1",        "operator", 2),
        ]
        for uid, email, pwd, full_name, role, tenant_id in users_data:
            hashed = hash_password(pwd)
            await session.execute(text(
                f"INSERT INTO users (id, email, hashed_password, full_name, role, tenant_id, is_active, is_verified, failed_login_attempts) "
                f"VALUES ({uid}, '{email}', '{hashed}', '{full_name}', '{role}', {tenant_id}, true, true, 0)"
            ))
        await session.commit()

        # Restaurant Sections
        print("Creando secciones...")
        for sid, tid, name, desc, sort in [
            (20, 2, "SALA",    "Mesas interiores",     0),
            (21, 2, "AFUERA",  "Mesas exteriores",     1),
            (22, 2, "TERRAZA", "Zona terraza",         2),
        ]:
            await session.execute(text(
                f"INSERT INTO restaurant_sections (id, tenant_id, name, description, sort_order) "
                f"VALUES ({sid}, {tid}, '{name}', '{desc}', {sort})"
            ))
        await session.commit()

        # Tables
        print("Creando mesas...")
        for tid, ten_id, num, sec_id, sec, cap, status in [
            (1,  2, "Mesa 1",  20, "SALA",    4, "available"),
            (2,  2, "Mesa 2",  20, "SALA",    4, "available"),
            (3,  2, "Mesa 3",  20, "SALA",    6, "available"),
            (4,  2, "Mesa 4",  20, "SALA",    6, "available"),
            (5,  2, "Mesa 5",  20, "SALA",    8, "available"),
            (6,  2, "Mesa 6",  20, "SALA",    2, "available"),
            (7,  2, "Mesa 7",  21, "AFUERA",  4, "available"),
            (8,  2, "Mesa 8",  21, "AFUERA",  4, "available"),
            (9,  2, "Mesa 9",  21, "AFUERA",  6, "available"),
            (10, 2, "Mesa 10", 22, "TERRAZA", 4, "available"),
            (11, 2, "Mesa 11", 22, "TERRAZA", 2, "available"),
            (12, 2, "Mesa 12", 22, "TERRAZA", 6, "available"),
        ]:
            await session.execute(text(
                f"INSERT INTO tables (id, tenant_id, number, section_id, section, capacity, status) "
                f"VALUES ({tid}, {ten_id}, '{num}', {sec_id}, '{sec}', {cap}, '{status}')"
            ))
        await session.commit()

        # Menu Items
        print("Creando menu...")
        for iid, tid, name, price, cat, itype, parea, active in [
            (1,  2, "Ceviche Mixto",      28.00, "Entradas",        "food", "cocina", True),
            (2,  2, "Lomo Saltado",       32.00, "Platos de Fondo", "food", "cocina", True),
            (3,  2, "Arroz con Mariscos", 35.00, "Platos de Fondo", "food", "cocina", True),
            (4,  2, "Jugo de Maracuya",    8.00, "Bebidas",         "beverage", "cocina", True),
            (5,  2, "Chicha Morada",       6.00, "Bebidas",         "beverage", "cocina", True),
            (6,  2, "Coca Cola",           5.00, "Bebidas",         "beverage", "barra", True),
            (7,  2, "Inca Kola",           5.00, "Bebidas",         "beverage", "barra", True),
            (8,  2, "Agua Mineral",        4.00, "Bebidas",         "beverage", "barra", True),
            (9,  2, "Galleta",             2.00, "Snacks",          "food", "none", True),
            (10, 2, "Papas Fritas",        5.00, "Snacks",          "food", "none", True),
        ]:
            await session.execute(text(
                f"INSERT INTO menu_items (id, tenant_id, name, price, category, item_type, preparation_area, active) "
                f"VALUES ({iid}, {tid}, '{name}', {price}, '{cat}', '{itype}', '{parea}', {str(active).lower()})"
            ))
        await session.commit()

        # Modifiers
        print("Creando modificadores...")
        for mid, item_id, name, adj, max_sel in [
            (1,  1, "Conchas negras",  5.00, 3),
            (2,  1, "Sin cebolla",     0.00, 1),
            (3,  2, "Huevo frito",     3.00, 2),
            (4,  2, "Papas extra",     4.00, 1),
        ]:
            await session.execute(text(
                f"INSERT INTO menu_modifiers (id, menu_item_id, name, price_adjustment, max_select) "
                f"VALUES ({mid}, {item_id}, '{name}', {adj}, {max_sel})"
            ))
        await session.commit()

        # Product Categories
        print("Creando categorias de productos...")
        for cid, tid, name, desc, active, sort in [
            (1, 2, "Insumos Cocina",    "Materia prima", True, 0),
            (2, 2, "Insumos Barra",     "Bebidas", True, 1),
            (3, 2, "Empaques",          "Envases", True, 2),
        ]:
            await session.execute(text(
                f"INSERT INTO product_categories (id, tenant_id, name, description, active, sort_order) "
                f"VALUES ({cid}, {tid}, '{name}', '{desc}', {str(active).lower()}, {sort})"
            ))
        await session.commit()

        # Products
        print("Creando productos de inventario...")
        for pid, tid, name, uom, stock, cost, price, cat in [
            (1,  2, "Pescado",       "kg",        10.00, 15.00, 25.00, 1),
            (2,  2, "Limon",         "unidades",  50.00,  0.50,  1.00, 1),
            (3,  2, "Cebolla",       "unidades",  30.00,  1.00,  1.50, 1),
            (4,  2, "Camote",        "kg",        15.00,  3.00,  5.00, 1),
            (5,  2, "Lechuga",       "unidades",  20.00,  1.50,  2.50, 1),
            (6,  2, "Coca Cola Lata","unidades",  48.00,  2.00,  4.00, 2),
            (7,  2, "Inca Kola Lata","unidades",  48.00,  2.00,  4.00, 2),
        ]:
            code = name.upper().replace(" ", "_").replace("Ñ", "N")
            await session.execute(text(
                f"INSERT INTO products (id, tenant_id, code, name, unit_of_measure, current_stock, average_cost, retail_price, category_id, active, has_serial, warranty_months) "
                f"VALUES ({pid}, {tid}, '{code}', '{name}', '{uom}', {stock}, {cost}, {price}, {cat}, true, false, 0)"
            ))
        await session.commit()

    await engine.dispose()

    print("\n=== Seed Clean v1.0 completado ===")
    print()
    print("  Credenciales:")
    print("  admin@elsegoviano.pe     / admin123       (dueno)")
    print("  mesero1@elsegoviano.pe   / mesero123      (mesero)")
    print("  cocinero1@elsegoviano.pe / cocinero123     (cocinero)")
    print("  demo@iaas.com            / demo123         (demo)")
    print("  ferretero@elsegoviano.pe / ferreteria123   (ferreteria)")
    print()


if __name__ == "__main__":
    asyncio.run(main())
