"""
🍽️ Explosión de Recetas — Spec 01 v0.2 (decisiones D1-D9).

Responsabilidad:
  - Gate por feature flag `features.recipe_explosion` (companies.settings JSONB).
  - Pre-check atómico de stock de TODOS los ingredientes (409 si falta).
  - Registro de salidas de kárdex por ingrediente (reference_type='receta',
    concept='Consumo por receta', reference_id=sale_id) + decremento de stock.
  - Validaciones: solo platos (menu_items) con preparation_area='cocina',
    ingrediente del mismo tenant (D1), sin doble descuento (D2),
    sin serializados (D5), unidad del ingrediente == unidad del producto (D4).

Todo se ejecuta dentro de la MISMA transacción de la venta (el session
committea/rollea en el dependency `get_db`).
"""

import json

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.db.models.accounting import Company, KardexMovement, Product
from app.adapters.db.models.restaurant import MenuItem, Recipe, RecipeIngredient


# ─── Normalización de unidades (D4) ───────────────────────────────
UNIT_NORMALIZATION: dict[str, str] = {
    "kg": "kg", "kilo": "kg", "kilogramo": "kg", "kilogramos": "kg",
    "g": "g", "gramo": "g", "gramos": "g",
    "l": "L", "litro": "L", "litros": "L",
    "ml": "mL", "mililitro": "mL", "mililitros": "mL",
    "und": "und", "unidad": "und", "unidades": "und", "unid": "und",
    "caja": "caja", "cajas": "caja",
    "paquete": "paquete", "paquetes": "paquete",
    "docena": "docena", "docenas": "docena",
    "botella": "botella", "botellas": "botella",
}


def normalize_unit(unit: str | None) -> str:
    """Normaliza abreviaturas de unidades para comparación D4."""
    if not unit:
        return ""
    return UNIT_NORMALIZATION.get(unit.strip().lower(), unit.strip())


class RecipeExplosionService:
    """Servicio de explosión de recetas al vender platos."""

    @staticmethod
    async def is_enabled(db: AsyncSession, tenant_id: int) -> bool:
        """Lee companies.settings → features.recipe_explosion (default False)."""
        result = await db.execute(
            select(Company.settings).where(Company.id == tenant_id)
        )
        raw = result.scalar_one_or_none()
        if not raw:
            return False
        try:
            if isinstance(raw, str):
                raw = json.loads(raw)
            features = (raw or {}).get("features", {}) if isinstance(raw, dict) else {}
            return bool(features.get("recipe_explosion", False))
        except Exception:
            return False

    @staticmethod
    async def _resolve_menu_item_and_recipe(
        db: AsyncSession, menu_item_id: int, tenant_id: int,
    ) -> tuple[MenuItem, Recipe | None]:
        """Valida tenant del plato; retorna (menu_item, recipe | None)."""
        item = (await db.execute(
            select(MenuItem).where(
                MenuItem.id == menu_item_id,
                MenuItem.tenant_id == tenant_id,
            )
        )).scalar_one_or_none()
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ítem de menú no encontrado para este tenant",
            )
        if item.preparation_area != "cocina":
            return item, None  # solo platos de cocina tienen receta (D1)

        recipe = (await db.execute(
            select(Recipe)
            .options(
                selectinload(Recipe.ingredients)
                .selectinload(RecipeIngredient.product)
            )
            .where(Recipe.menu_item_id == menu_item_id)
        )).scalar_one_or_none()
        return item, recipe

    @staticmethod
    async def precheck_and_compute_demands(
        db: AsyncSession, tenant_id: int, items_data: list[dict],
    ) -> list[dict]:
        """
        Pre-check: valida reglas (D1/D4/D5/tenant) y que haya stock de TODOS
        los ingredientes antes de mutar nada. Retorna demandas agregadas:
        [{"product_id": int, "quantity": float}, ...]
        """
        demands: dict[int, float] = {}
        for item_data in items_data:
            menu_item_id = item_data.get("menu_item_id")
            if not menu_item_id:
                continue
            qty_sold = float(item_data.get("quantity", 0) or 0)
            _, recipe = await RecipeExplosionService._resolve_menu_item_and_recipe(
                db, int(menu_item_id), tenant_id,
            )
            if not recipe:
                continue
            for ing in recipe.ingredients:
                product = ing.product
                if product is None:
                    continue
                if product.tenant_id != tenant_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Ingrediente '{product.name}' no pertenece al tenant (aislamiento)",
                    )
                if product.has_serial:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Ingrediente '{product.name}' es serializado — no permitido (D5)",
                    )
                if normalize_unit(product.unit_of_measure) != normalize_unit(ing.unit_of_measure):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Ingrediente '{product.name}': unidad '{ing.unit_of_measure}' "
                            f"no coincide con la del producto '{product.unit_of_measure}' (D4)"
                        ),
                    )
                demands[product.id] = demands.get(product.id, 0.0) + (
                    float(ing.quantity) * qty_sold
                )

        # Validación de stock agregada (antes de cualquier mutación)
        for product_id, need in demands.items():
            product = (await db.execute(
                select(Product).where(Product.id == product_id)
            )).scalar_one_or_none()
            if product is None:
                continue
            available = float(product.current_stock or 0)
            if available + 1e-9 < need:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Stock insuficiente de '{product.name}': se necesitan "
                        f"{need} {product.unit_of_measure}, disponible {available}"
                    ),
                )

        return [{"product_id": pid, "quantity": qty} for pid, qty in demands.items()]

    @staticmethod
    async def explode(
        db: AsyncSession,
        tenant_id: int,
        sale_id: int,
        sale_number: str,
        items_data: list[dict],
        today,
    ) -> list[KardexMovement]:
        """
        Ejecuta la explosión: kárdex 'salida' por ingrediente + decremento de
        stock. Debe llamarse SOLO tras precheck_and_compute_demands y dentro de
        la transacción de la venta. Retorna los movimientos generados.
        """
        movements: list[KardexMovement] = []
        for item_data in items_data:
            menu_item_id = item_data.get("menu_item_id")
            if not menu_item_id:
                continue
            qty_sold = float(item_data.get("quantity", 0) or 0)
            _, recipe = await RecipeExplosionService._resolve_menu_item_and_recipe(
                db, int(menu_item_id), tenant_id,
            )
            if not recipe:
                continue
            for ing in recipe.ingredients:
                product = ing.product
                if product is None:
                    continue
                qty = round(float(ing.quantity) * qty_sold, 4)
                unit_cost = float(product.average_cost or 0)
                new_qty = float(product.current_stock or 0) - qty
                move = KardexMovement(
                    product_id=product.id,
                    movement_type="salida",
                    concept="Consumo por receta",
                    reference_type="receta",
                    reference_id=sale_id,
                    quantity=qty,
                    unit_cost=unit_cost,
                    total=round(qty * unit_cost, 2),
                    balance_quantity=new_qty,
                    balance_avg_cost=unit_cost,
                    balance_total=round(new_qty * unit_cost, 2),
                    date=today,
                )
                db.add(move)
                await db.flush()
                await db.refresh(move)
                product.current_stock = new_qty
                movements.append(move)
        return movements
