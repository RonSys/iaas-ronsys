"""
📦 Inventory Service — Categorías + Productos + Seriales (F0-009).

Cubre:
  - HU-F0-009-01: Categorías CRUD, jerarquía tree=true, contador, anti-ciclos
  - HU-F0-009-02: Productos CRUD, barcode search, server-side sort
  - HU-F0-009-04: Seriales CRUD, registro masivo, stock calculado
"""

from datetime import date

from fastapi import HTTPException
from sqlalchemy import func, select, text, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models.accounting import (
    Product,
    ProductCategory,
    ProductUnit,
)
from app.schemas.inventory import (
    ProductCategoryCreate,
    ProductCategoryUpdate,
    ProductCreate,
    ProductUpdate,
    SerialCreate,
    SerialBatchCreate,
)


# ═══════════════════════════════════════════════════════════════
# Categorías (HU-F0-009-01)
# ═══════════════════════════════════════════════════════════════


class InventoryCategoriesService:
    """Servicio de categorías con jerarquía, contador y anti-ciclos."""

    @staticmethod
    async def create_category(
        db: AsyncSession, tenant_id: int, data: ProductCategoryCreate,
    ) -> dict:
        """Crear categoría con soporte para parent_id, description, sort_order."""
        name = data.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="'name' es requerido")

        # Validar unicidad de nombre dentro del tenant
        dup = await db.execute(
            select(ProductCategory.id).where(
                ProductCategory.tenant_id == tenant_id,
                ProductCategory.name == name,
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Categoría ya existe")

        # Validar parent_id: debe existir y pertenecer al tenant
        if data.parent_id is not None:
            parent = await db.execute(
                select(ProductCategory).where(
                    ProductCategory.id == data.parent_id,
                    ProductCategory.tenant_id == tenant_id,
                )
            )
            if not parent.scalar_one_or_none():
                raise HTTPException(
                    status_code=404, detail="Categoría padre no encontrada"
                )

        cat = ProductCategory(
            tenant_id=tenant_id,
            name=name,
            description=data.description,
            parent_id=data.parent_id,
            sort_order=data.sort_order,
            active=data.active,
        )
        db.add(cat)
        await db.flush()
        await db.refresh(cat)

        return {
            "id": cat.id,
            "tenant_id": cat.tenant_id,
            "name": cat.name,
            "description": cat.description,
            "parent_id": cat.parent_id,
            "sort_order": cat.sort_order,
            "active": cat.active,
            "product_count": 0,
            "created_at": cat.created_at.isoformat() if cat.created_at else None,
            "updated_at": cat.updated_at.isoformat() if cat.updated_at else None,
        }

    @staticmethod
    async def list_categories(
        db: AsyncSession,
        tenant_id: int,
        tree: bool = False,
    ) -> list[dict]:
        """
        Listar categorías con product_count.
        Si tree=true, devuelve estructura jerárquica anidada.
        """
        # Subquery para contar solo productos activos
        active_product_count = (
            select(func.count(Product.id))
            .where(
                Product.category_id == ProductCategory.id,
                Product.active == True,  # noqa: E712
            )
            .correlate(ProductCategory)
            .scalar_subquery()
        )

        result = await db.execute(
            select(
                ProductCategory.id,
                ProductCategory.tenant_id,
                ProductCategory.name,
                ProductCategory.description,
                ProductCategory.parent_id,
                ProductCategory.sort_order,
                ProductCategory.active,
                ProductCategory.created_at,
                ProductCategory.updated_at,
                active_product_count.label("product_count"),
            )
            .where(ProductCategory.tenant_id == tenant_id)
            .order_by(ProductCategory.sort_order, ProductCategory.name)
        )
        rows = result.all()

        flat_list = [
            {
                "id": r[0],
                "tenant_id": r[1],
                "name": r[2],
                "description": r[3],
                "parent_id": r[4],
                "sort_order": r[5],
                "active": r[6],
                "product_count": int(r[9]) if r[9] is not None else 0,
                "created_at": r[7].isoformat() if r[7] else None,
                "updated_at": r[8].isoformat() if r[8] else None,
            }
            for r in rows
        ]

        if tree:
            return InventoryCategoriesService._build_tree(flat_list)

        return flat_list

    @staticmethod
    def _build_tree(categories: list[dict]) -> list[dict]:
        """Construye árbol jerárquico a partir de lista plana."""
        lookup: dict[int, dict] = {}
        roots: list[dict] = []

        # Indexar por id
        for cat in categories:
            cat["children"] = []
            lookup[cat["id"]] = cat

        # Ensamblar árbol
        for cat in categories:
            parent_id = cat.get("parent_id")
            if parent_id and parent_id in lookup:
                lookup[parent_id]["children"].append(cat)
            else:
                roots.append(cat)

        return roots

    @staticmethod
    async def _validate_no_cycle(
        db: AsyncSession, category_id: int, new_parent_id: int,
    ) -> None:
        """
        Validar que asignar new_parent_id no cree un ciclo.
        new_parent_id no puede ser descendiente de category_id.
        """
        if new_parent_id == category_id:
            raise HTTPException(
                status_code=422, detail="Una categoría no puede ser su propio padre"
            )

        # Recolectar todos los descendientes de category_id
        descendants: set[int] = set()
        to_check = [category_id]
        while to_check:
            current = to_check.pop()
            result = await db.execute(
                select(ProductCategory.id).where(
                    ProductCategory.parent_id == current
                )
            )
            children = [r[0] for r in result.all()]
            for child_id in children:
                if child_id not in descendants:
                    descendants.add(child_id)
                    to_check.append(child_id)

        if new_parent_id in descendants:
            raise HTTPException(
                status_code=422,
                detail="Asignación inválida: crearía un ciclo jerárquico",
            )

    @staticmethod
    async def update_category(
        db: AsyncSession,
        category_id: int,
        tenant_id: int,
        data: ProductCategoryUpdate,
    ) -> dict:
        """Actualizar categoría — soporta todos los campos (HU-F0-009-01)."""
        result = await db.execute(
            select(ProductCategory).where(
                ProductCategory.id == category_id,
                ProductCategory.tenant_id == tenant_id,
            )
        )
        cat = result.scalar_one_or_none()
        if not cat:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")

        # Validar unicidad de nombre
        if data.name is not None:
            name = data.name.strip()
            if not name:
                raise HTTPException(status_code=400, detail="'name' no puede estar vacío")
            dup = await db.execute(
                select(ProductCategory.id).where(
                    ProductCategory.tenant_id == tenant_id,
                    ProductCategory.name == name,
                    ProductCategory.id != category_id,
                )
            )
            if dup.scalar_one_or_none():
                raise HTTPException(
                    status_code=409, detail="Ya existe una categoría con ese nombre"
                )
            cat.name = name

        # Validar parent_id sin ciclos
        if data.parent_id is not None:
            if data.parent_id != 0:  # 0 = sin padre (root)
                # Verificar que el padre existe
                parent = await db.execute(
                    select(ProductCategory).where(
                        ProductCategory.id == data.parent_id,
                        ProductCategory.tenant_id == tenant_id,
                    )
                )
                if not parent.scalar_one_or_none():
                    raise HTTPException(
                        status_code=404, detail="Categoría padre no encontrada"
                    )
                # Validar anti-ciclos
                await InventoryCategoriesService._validate_no_cycle(
                    db, category_id, data.parent_id
                )
                cat.parent_id = data.parent_id
            else:
                cat.parent_id = None

        if data.description is not None:
            cat.description = data.description
        if data.sort_order is not None:
            cat.sort_order = data.sort_order
        if data.active is not None:
            cat.active = data.active

        await db.flush()
        await db.refresh(cat)

        # Obtener product_count actualizado
        count_result = await db.execute(
            select(func.count(Product.id)).where(
                Product.category_id == cat.id,
                Product.active == True,  # noqa: E712
            )
        )
        product_count = count_result.scalar() or 0

        return {
            "id": cat.id,
            "tenant_id": cat.tenant_id,
            "name": cat.name,
            "description": cat.description,
            "parent_id": cat.parent_id,
            "sort_order": cat.sort_order,
            "active": cat.active,
            "product_count": int(product_count),
            "created_at": cat.created_at.isoformat() if cat.created_at else None,
            "updated_at": cat.updated_at.isoformat() if cat.updated_at else None,
        }

    @staticmethod
    async def delete_category(
        db: AsyncSession, category_id: int, tenant_id: int,
    ) -> None:
        """
        Eliminar categoría con validación 409 si tiene productos activos (HU-F0-009-01).
        Solo cuenta productos active=true.
        """
        # Verificar existencia
        result = await db.execute(
            select(ProductCategory).where(
                ProductCategory.id == category_id,
                ProductCategory.tenant_id == tenant_id,
            )
        )
        cat = result.scalar_one_or_none()
        if not cat:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")

        # Contar productos activos en esta categoría
        count_result = await db.execute(
            select(func.count(Product.id)).where(
                Product.category_id == category_id,
                Product.active == True,  # noqa: E712
            )
        )
        active_count = count_result.scalar() or 0

        if active_count > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Categoría tiene {active_count} producto(s) activo(s). Reasígneos primero.",
            )

        # Reasignar subcategorías a la categoría padre (o null si es root)
        parent_id = cat.parent_id
        await db.execute(
            update(ProductCategory)
            .where(ProductCategory.parent_id == category_id)
            .values(parent_id=parent_id)
        )

        # Soft-delete: marcar como inactive
        cat.active = False
        await db.flush()


# ═══════════════════════════════════════════════════════════════
# Productos (HU-F0-009-02)
# ═══════════════════════════════════════════════════════════════


class InventoryProductsService:
    """Servicio CRUD de productos con búsqueda, sort y seriales."""

    @staticmethod
    async def create_product(
        db: AsyncSession, tenant_id: int, data: ProductCreate,
    ) -> dict:
        """Crear producto con todos los campos F0-009."""
        # Validar unicidad de code
        dup_code = await db.execute(
            select(Product.id).where(
                Product.tenant_id == tenant_id,
                Product.code == data.code,
            )
        )
        if dup_code.scalar_one_or_none():
            raise HTTPException(
                status_code=409, detail=f"El código '{data.code}' ya existe"
            )

        # Validar unicidad de barcode
        if data.barcode:
            dup_barcode = await db.execute(
                select(Product.id).where(
                    Product.tenant_id == tenant_id,
                    Product.barcode == data.barcode,
                )
            )
            if dup_barcode.scalar_one_or_none():
                raise HTTPException(
                    status_code=409, detail=f"El código de barras '{data.barcode}' ya existe"
                )

        # Validar categoría si se especifica
        if data.category_id is not None:
            cat = await db.execute(
                select(ProductCategory.id).where(
                    ProductCategory.id == data.category_id,
                    ProductCategory.tenant_id == tenant_id,
                    ProductCategory.active == True,  # noqa: E712
                )
            )
            if not cat.scalar_one_or_none():
                raise HTTPException(
                    status_code=404, detail="Categoría no encontrada o inactiva"
                )

        # Si has_serial, el stock se gestiona vía seriales
        stock = 0.0 if data.has_serial else data.current_stock

        product = Product(
            tenant_id=tenant_id,
            code=data.code,
            name=data.name,
            description=data.description,
            unit_of_measure=data.unit_of_measure,
            current_stock=stock,
            average_cost=data.average_cost,
            category_id=data.category_id,
            retail_price=data.retail_price,
            wholesale_price=data.wholesale_price,
            wholesale_min_qty=data.wholesale_min_qty,
            barcode=data.barcode,
            active=data.active,
            has_serial=data.has_serial,
            warranty_months=data.warranty_months,
            manufacturer=data.manufacturer,
        )
        db.add(product)
        await db.flush()
        await db.refresh(product)

        return await InventoryProductsService._product_to_dict(product, db_session=db)

    @staticmethod
    async def update_product(
        db: AsyncSession, product_id: int, tenant_id: int, data: ProductUpdate,
    ) -> dict:
        """Actualizar producto con validaciones F0-009."""
        result = await db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.tenant_id == tenant_id,
            )
        )
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        # Validar unicidad de code
        if data.code is not None:
            dup = await db.execute(
                select(Product.id).where(
                    Product.tenant_id == tenant_id,
                    Product.code == data.code,
                    Product.id != product_id,
                )
            )
            if dup.scalar_one_or_none():
                raise HTTPException(
                    status_code=409, detail=f"El código '{data.code}' ya existe"
                )
            product.code = data.code

        # Validar unicidad de barcode
        if data.barcode is not None:
            dup = await db.execute(
                select(Product.id).where(
                    Product.tenant_id == tenant_id,
                    Product.barcode == data.barcode,
                    Product.id != product_id,
                )
            )
            if dup.scalar_one_or_none():
                raise HTTPException(
                    status_code=409, detail=f"El código de barras '{data.barcode}' ya existe"
                )
            product.barcode = data.barcode

        # Validar categoría
        if data.category_id is not None:
            cat = await db.execute(
                select(ProductCategory.id).where(
                    ProductCategory.id == data.category_id,
                    ProductCategory.tenant_id == tenant_id,
                    ProductCategory.active == True,  # noqa: E712
                )
            )
            if not cat.scalar_one_or_none():
                raise HTTPException(
                    status_code=404, detail="Categoría no encontrada o inactiva"
                )
            product.category_id = data.category_id

        # HU-F0-009-07: Validar transiciones has_serial
        if data.has_serial is not None and data.has_serial != product.has_serial:
            if data.has_serial is False and product.has_serial:
                # true → false: verificar que no tenga seriales registrados
                count = await db.execute(
                    select(func.count(ProductUnit.id)).where(
                        ProductUnit.product_id == product_id
                    )
                )
                serial_count = count.scalar() or 0
                if serial_count > 0:
                    raise HTTPException(
                        status_code=422,
                        detail=f"No puede desactivar seriales. Elimine primero los {serial_count} seriales registrados.",
                    )
                product.has_serial = False
            elif data.has_serial is True and not product.has_serial:
                # false → true: advertir si hay stock numérico
                if float(product.current_stock) > 0:
                    # Permitir pero advertir — el stock numérico se ignora
                    pass
                product.has_serial = True
                product.current_stock = 0  # Reset al activar seriales
        elif data.has_serial is not None:
            product.has_serial = data.has_serial

        # Actualizar campos simples
        if data.name is not None:
            product.name = data.name
        if data.description is not None:
            product.description = data.description
        if data.unit_of_measure is not None:
            product.unit_of_measure = data.unit_of_measure
        if data.current_stock is not None:
            product.current_stock = data.current_stock
        if data.average_cost is not None:
            product.average_cost = data.average_cost
        if data.retail_price is not None:
            product.retail_price = data.retail_price
        if data.wholesale_price is not None:
            product.wholesale_price = data.wholesale_price
        if data.wholesale_min_qty is not None:
            product.wholesale_min_qty = data.wholesale_min_qty
        if data.active is not None:
            product.active = data.active
        if data.warranty_months is not None:
            product.warranty_months = data.warranty_months
        if data.manufacturer is not None:
            product.manufacturer = data.manufacturer

        await db.flush()
        await db.refresh(product)

        return await InventoryProductsService._product_to_dict(product, db_session=db)

    @staticmethod
    async def delete_product(
        db: AsyncSession, product_id: int, tenant_id: int,
    ) -> dict:
        """Soft-delete de producto (HU-F0-009-02)."""
        result = await db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.tenant_id == tenant_id,
            )
        )
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        warnings = []

        # Verificar seriales vendidos
        if product.has_serial:
            sold_count = await db.execute(
                select(func.count(ProductUnit.id)).where(
                    ProductUnit.product_id == product_id,
                    ProductUnit.status == "sold",
                )
            )
            sold = sold_count.scalar() or 0
            if sold > 0:
                warnings.append(
                    f"Producto tiene {sold} seriales vendidos. "
                    "Se desactivará pero no se eliminará físicamente."
                )

        product.active = False
        await db.flush()

        result_dict = await InventoryProductsService._product_to_dict(product, db_session=db)
        if warnings:
            result_dict["warnings"] = warnings

        return result_dict

    @staticmethod
    async def list_products(
        db: AsyncSession,
        tenant_id: int,
        category: str | None = None,
        category_id: int | None = None,
        search: str | None = None,
        barcode: str | None = None,
        active: bool | None = None,
        has_serial: bool | None = None,
        sort_by: str = "name",
        order: str = "asc",
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """
        Listar productos con filtros avanzados y server-side sort (HU-F0-009-02).

        Soporta:
          - Búsqueda por nombre, código, código de barras
          - Filtro por categoría, active, has_serial
          - Ordenación server-side (name, retail_price, current_stock, code)
        """
        conditions = [Product.tenant_id == tenant_id]

        if category:
            # Join implícito: filtrar por nombre de categoría
            cat_condition = ProductCategory.name == category
            conditions.append(Product.category.has(
                ProductCategory.name == category
            ))
        if category_id is not None:
            conditions.append(Product.category_id == category_id)
        if active is not None:
            conditions.append(Product.active == active)
        if has_serial is not None:
            conditions.append(Product.has_serial == has_serial)
        if search:
            conditions.append(
                or_(
                    Product.name.ilike(f"%{search}%"),
                    Product.code.ilike(f"%{search}%"),
                )
            )
        if barcode:
            conditions.append(Product.barcode == barcode)

        # Ordenación server-side
        sort_col_map = {
            "name": Product.name,
            "retail_price": Product.retail_price,
            "current_stock": Product.current_stock,
            "code": Product.code,
            "created_at": Product.created_at,
        }
        sort_column = sort_col_map.get(sort_by, Product.name)
        if order.lower() == "desc":
            sort_column = sort_column.desc()
        else:
            sort_column = sort_column.asc()

        # Ejecutar query
        result = await db.execute(
            select(Product)
            .where(and_(*conditions))
            .order_by(sort_column)
            .offset(offset)
            .limit(limit)
        )
        products = result.scalars().all()

        # Convertir a dicts con conteo de seriales
        product_dicts = []
        for p in products:
            d = await InventoryProductsService._product_to_dict(p, db_session=db)
            product_dicts.append(d)

        # Contar total (sin paginación)
        count_result = await db.execute(
            select(func.count(Product.id)).where(and_(*conditions))
        )
        total = count_result.scalar() or 0

        return {
            "products": product_dicts,
            "total": total,
            "page": (offset // limit) + 1 if limit > 0 else 1,
            "limit": limit,
        }

    @staticmethod
    async def get_product(
        db: AsyncSession, product_id: int, tenant_id: int,
    ) -> dict:
        """Obtener un producto con detalle completo."""
        result = await db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.tenant_id == tenant_id,
            )
        )
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        return await InventoryProductsService._product_to_dict(product, db_session=db)

    @staticmethod
    async def _product_to_dict(
        product: Product, db_session: AsyncSession | None = None,
    ) -> dict:
        """Convierte Product a dict con conteos de seriales y nombre de categoría."""
        # Obtener nombre de categoría
        category_name = None
        if product.category_id and db_session:
            cat_result = await db_session.execute(
                select(ProductCategory.name).where(
                    ProductCategory.id == product.category_id
                )
            )
            row = cat_result.fetchone()
            if row:
                category_name = row[0]

        # Conteo de seriales disponibles y totales
        serial_available = 0
        serial_total = 0
        if product.has_serial and db_session:
            available_result = await db_session.execute(
                select(func.count(ProductUnit.id)).where(
                    ProductUnit.product_id == product.id,
                    ProductUnit.status == "available",
                )
            )
            serial_available = available_result.scalar() or 0

            total_result = await db_session.execute(
                select(func.count(ProductUnit.id)).where(
                    ProductUnit.product_id == product.id,
                )
            )
            serial_total = total_result.scalar() or 0

        return {
            "id": product.id,
            "tenant_id": product.tenant_id,
            "code": product.code,
            "name": product.name,
            "description": product.description,
            "unit_of_measure": product.unit_of_measure,
            "current_stock": float(product.current_stock),
            "average_cost": float(product.average_cost),
            "category_id": product.category_id,
            "category_name": category_name,
            "retail_price": float(product.retail_price) if product.retail_price else None,
            "wholesale_price": float(product.wholesale_price) if product.wholesale_price else None,
            "wholesale_min_qty": float(product.wholesale_min_qty) if product.wholesale_min_qty else None,
            "barcode": product.barcode,
            "active": product.active,
            "has_serial": product.has_serial,
            "warranty_months": product.warranty_months,
            "manufacturer": product.manufacturer,
            "serial_available_count": int(serial_available),
            "serial_total_count": int(serial_total),
        }


# ═══════════════════════════════════════════════════════════════
# Seriales (HU-F0-009-04)
# ═══════════════════════════════════════════════════════════════


class SerialService:
    """Servicio de gestión de seriales con trazabilidad."""

    @staticmethod
    async def register_serial(
        db: AsyncSession,
        product_id: int,
        tenant_id: int,
        data: SerialCreate,
    ) -> dict:
        """Registrar un serial individual."""
        product = await _get_product_with_serial_check(db, product_id, tenant_id)

        # Validar unicidad de serial_number
        dup = await db.execute(
            select(ProductUnit.id).where(
                ProductUnit.serial_number == data.serial_number,
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail=f"Número de serie '{data.serial_number}' ya existe",
            )

        # Calcular warranty_expiry
        from dateutil.relativedelta import relativedelta

        warranty_expiry = None
        if data.purchase_date and product.warranty_months > 0:
            warranty_expiry = data.purchase_date + relativedelta(
                months=product.warranty_months
            )

        unit = ProductUnit(
            product_id=product_id,
            serial_number=data.serial_number,
            status="available",
            purchase_date=data.purchase_date,
            cost_price=data.cost_price,
            warranty_expiry=warranty_expiry,
            notes=data.notes,
        )
        db.add(unit)
        await db.flush()
        await db.refresh(unit)

        return {
            "id": unit.id,
            "product_id": unit.product_id,
            "serial_number": unit.serial_number,
            "status": unit.status,
            "purchase_date": unit.purchase_date.isoformat() if unit.purchase_date else None,
            "cost_price": float(unit.cost_price) if unit.cost_price is not None else None,
            "warranty_expiry": unit.warranty_expiry.isoformat() if unit.warranty_expiry is not None else None,
            "sale_id": unit.sale_id,
            "sale_item_id": unit.sale_item_id,
            "notes": unit.notes,
            "created_at": unit.created_at.isoformat() if unit.created_at else None,
        }

    @staticmethod
    async def register_serial_batch(
        db: AsyncSession,
        product_id: int,
        tenant_id: int,
        data: SerialBatchCreate,
    ) -> list[dict]:
        """Registro masivo de seriales en una transacción."""
        product = await _get_product_with_serial_check(db, product_id, tenant_id)

        from dateutil.relativedelta import relativedelta

        # Verificar duplicados primero
        serial_numbers = [s.serial_number for s in data.serials]
        existing = await db.execute(
            select(ProductUnit.serial_number).where(
                ProductUnit.serial_number.in_(serial_numbers)
            )
        )
        existing_set = {r[0] for r in existing.all()}
        if existing_set:
            raise HTTPException(
                status_code=409,
                detail=f"Serial(es) ya existen: {', '.join(sorted(existing_set))}",
            )

        results = []
        for s_data in data.serials:
            warranty_expiry = None
            if s_data.purchase_date and product.warranty_months > 0:
                warranty_expiry = s_data.purchase_date + relativedelta(
                    months=product.warranty_months
                )

            unit = ProductUnit(
                product_id=product_id,
                serial_number=s_data.serial_number,
                status="available",
                purchase_date=s_data.purchase_date,
                cost_price=s_data.cost_price,
                warranty_expiry=warranty_expiry,
                notes=s_data.notes,
            )
            db.add(unit)
            results.append(unit)

        await db.flush()
        for u in results:
            await db.refresh(u)

        return [
            {
                "id": u.id,
                "product_id": u.product_id,
                "serial_number": u.serial_number,
                "status": u.status,
                "purchase_date": u.purchase_date.isoformat() if u.purchase_date else None,
                "cost_price": float(u.cost_price) if u.cost_price is not None else None,
                "warranty_expiry": u.warranty_expiry.isoformat() if u.warranty_expiry is not None else None,
                "sale_id": u.sale_id,
                "sale_item_id": u.sale_item_id,
                "notes": u.notes,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in results
        ]

    @staticmethod
    async def list_serials(
        db: AsyncSession,
        product_id: int,
        tenant_id: int,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """Listar seriales de un producto con filtro por status."""
        # Verificar que el producto pertenece al tenant
        prod = await db.execute(
            select(Product.id).where(
                Product.id == product_id,
                Product.tenant_id == tenant_id,
            )
        )
        if not prod.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        conditions = [ProductUnit.product_id == product_id]
        if status:
            conditions.append(ProductUnit.status == status)

        # Conteos
        total_result = await db.execute(
            select(func.count(ProductUnit.id)).where(and_(*conditions))
        )
        total = total_result.scalar() or 0

        available_result = await db.execute(
            select(func.count(ProductUnit.id)).where(
                ProductUnit.product_id == product_id,
                ProductUnit.status == "available",
            )
        )
        available = available_result.scalar() or 0

        sold_result = await db.execute(
            select(func.count(ProductUnit.id)).where(
                ProductUnit.product_id == product_id,
                ProductUnit.status == "sold",
            )
        )
        sold = sold_result.scalar() or 0

        # Query principal
        result = await db.execute(
            select(ProductUnit)
            .where(and_(*conditions))
            .order_by(ProductUnit.serial_number)
            .offset(offset)
            .limit(limit)
        )
        units = result.scalars().all()

        items = [
            {
                "id": u.id,
                "product_id": u.product_id,
                "serial_number": u.serial_number,
                "status": u.status,
                "purchase_date": u.purchase_date.isoformat() if u.purchase_date else None,
                "cost_price": float(u.cost_price) if u.cost_price is not None else None,
                "warranty_expiry": u.warranty_expiry.isoformat() if u.warranty_expiry is not None else None,
                "sale_id": u.sale_id,
                "sale_item_id": u.sale_item_id,
                "notes": u.notes,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in units
        ]

        return {
            "items": items,
            "total": int(total),
            "available": int(available),
            "sold": int(sold),
        }


    @staticmethod
    async def get_traceability(
        db: AsyncSession,
        serial_number: str,
        tenant_id: int,
    ) -> dict:
        """
        HU-F0-009-06: Trazabilidad completa de un serial.
        Timeline de eventos: registered -> sold -> voided.
        """
        from app.adapters.db.models.sales import Sale

        result = await db.execute(
            select(ProductUnit).where(
                ProductUnit.serial_number == serial_number,
            )
        )
        unit = result.scalar_one_or_none()
        if not unit:
            raise HTTPException(
                status_code=404, detail=f"Serial '{serial_number}' no encontrado"
            )

        prod = await db.execute(
            select(Product).where(
                Product.id == unit.product_id,
                Product.tenant_id == tenant_id,
            )
        )
        product = prod.scalar_one_or_none()
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Serial '{serial_number}' no pertenece a esta empresa"
            )

        today = date.today()

        warranty_status = "sin_garantia"
        warranty_days = None
        if unit.warranty_expiry:
            remaining = (unit.warranty_expiry - today).days
            warranty_days = remaining
            warranty_status = "vigente" if remaining > 0 else "vencida"

        timeline: list[dict] = []
        timeline.append({
            "event_type": "registered",
            "timestamp": (unit.created_at or unit.purchase_date or today).isoformat(),
            "description": f"Registrado en producto '{product.name}'",
            "reference": None,
            "details": {
                "cost_price": float(unit.cost_price) if unit.cost_price is not None else None,
                "purchase_date": unit.purchase_date.isoformat() if unit.purchase_date else None,
                "warranty_expiry": unit.warranty_expiry.isoformat() if unit.warranty_expiry is not None else None,
            },
        })

        current_sale = None
        if unit.sale_id and unit.status == "sold":
            sale_result = await db.execute(
                select(Sale).where(Sale.id == unit.sale_id)
            )
            sale = sale_result.scalar_one_or_none()
            if sale:
                timeline.append({
                    "event_type": "sold",
                    "timestamp": sale.sale_date.isoformat(),
                    "description": f"Vendido en {sale.sale_number}",
                    "reference": sale.sale_number,
                    "details": {
                        "customer_name": sale.customer_name,
                        "sale_total": float(sale.total),
                        "is_voided": sale.is_voided,
                    },
                })
                current_sale = {
                    "sale_id": sale.id,
                    "sale_number": sale.sale_number,
                    "sale_date": sale.sale_date.isoformat() if sale.sale_date else None,
                    "customer_name": sale.customer_name,
                }
                if sale.is_voided:
                    timeline.append({
                        "event_type": "voided",
                        "timestamp": sale.sale_date.isoformat(),
                        "description": f"Venta {sale.sale_number} anulada: {sale.void_reason or 'Sin motivo'}",
                        "reference": sale.sale_number,
                        "details": {"void_reason": sale.void_reason},
                    })

        timeline.sort(key=lambda e: str(e["timestamp"]))

        return {
            "serial_number": serial_number,
            "product_name": product.name,
            "product_id": product.id,
            "warranty_expiry": unit.warranty_expiry.isoformat() if unit.warranty_expiry is not None else None,
            "warranty_status": warranty_status,
            "warranty_days_remaining": warranty_days,
            "current_status": unit.status,
            "cost_price": float(unit.cost_price) if unit.cost_price is not None else None,
            "timeline": timeline,
            "current_sale": current_sale,
        }

    @staticmethod
    async def get_expiring_warranties(
        db: AsyncSession, tenant_id: int, days: int = 30,
    ) -> list[dict]:
        """HU-F0-009-06: Alertas de garantia por vencer."""
        from datetime import timedelta

        today = date.today()
        deadline = today + timedelta(days=days)

        result = await db.execute(
            select(ProductUnit, Product.name)
            .join(Product, Product.id == ProductUnit.product_id)
            .where(
                Product.tenant_id == tenant_id,
                ProductUnit.status == "sold",
                ProductUnit.warranty_expiry.isnot(None),
                ProductUnit.warranty_expiry >= today,
                ProductUnit.warranty_expiry <= deadline,
            )
            .order_by(ProductUnit.warranty_expiry)
        )
        rows = result.all()

        return [
            {
                "serial_number": row[0].serial_number,
                "product_name": row[1],
                "product_id": row[0].product_id,
                "warranty_expiry": row[0].warranty_expiry.isoformat() if row[0].warranty_expiry else None,
                "days_remaining": (row[0].warranty_expiry - today).days if row[0].warranty_expiry else None,
                "sale_id": row[0].sale_id,
            }
            for row in rows
        ]


# ═══════════════════════════════════════════════════════════════
# Helpers privados
# ═══════════════════════════════════════════════════════════════


async def _get_product_with_serial_check(
    db: AsyncSession, product_id: int, tenant_id: int,
) -> Product:
    """Verifica que el producto existe y tiene has_serial=True."""
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if not product.has_serial:
        raise HTTPException(
            status_code=422,
            detail="Este producto no usa control por seriales",
        )
    return product
