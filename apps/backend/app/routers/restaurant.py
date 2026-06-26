"""
🍽️ Restaurant Router — Endpoints Restaurante (F0-004 a F0-008, Caso 6).

Endpoints:
  Tables:  GET /tables, GET /tables/{id}, POST /tables/{id}/open
  Menu:    GET /menu, POST /menu, PATCH /menu/{id}
  Recipes: GET /menu/{id}/recipe, PUT /menu/{id}/recipe, GET /products
  Orders:  POST /tables/{id}/order, GET /orders/{id}
           POST /orders/{id}/send-to-kitchen, PATCH /orders/{id}/status
           GET /orders/active
  Close:   POST /tables/{id}/close-order, POST /tables/{id}/pay
  Takeaway: POST /takeaway, GET /takeaway, PATCH /takeaway/{id}/pickup
  Promos:  POST /promotions, GET /promotions, PATCH /promotions/{id}
           POST /orders/{id}/apply-promotion/{promo_id}
  WebSocket: /ws/kitchen/{tenant_id}, /ws/waiter/{tenant_id}
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.database import get_db
from app.core.dependencies import get_current_active_user, require_role
from app.core.ws_manager import manager
from app.models.user import User
from app.services.restaurant_service import (
    ClosePayService,
    KitchenOrdersService,
    MenuService,
    PromotionsService,
    RecipesService,
    SectionsService,
    TablesService,
    TakeawayService,
)

router = APIRouter(prefix="/api/v1/restaurant", tags=["Restaurante"])

# ─── Tenant depende de get_current_active_user ────────────
from app.core.tenant import get_tenant_id  # noqa: E402


# ═══════════════════════════════════════════════════════════════
# TABLES (F0-004)
# ═══════════════════════════════════════════════════════════════

@router.post("/tables", status_code=201)
async def create_table(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    """Crea una nueva mesa."""
    number = body.get("number")
    if not number:
        raise HTTPException(status_code=400, detail="'number' es requerido")
    return await TablesService.create_table(
        db, tenant_id,
        number=str(number),
        capacity=body.get("capacity", 4),
        section=body.get("section"),
        section_id=body.get("section_id"),
    )


@router.patch("/tables/{table_id}")
async def update_table(
    table_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    """Actualiza una mesa (número, capacidad, sección)."""
    return await TablesService.update_table(db, table_id, tenant_id, body)


@router.delete("/tables/{table_id}", status_code=204)
async def delete_table(
    table_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Elimina una mesa (solo si está libre)."""
    await TablesService.delete_table(db, table_id, tenant_id)


@router.get("/tables")
async def list_tables(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = Query(None, description="Filtrar por estado"),
    section_id: int | None = Query(None, description="Filtrar por sección"),
):
    return await TablesService.list_tables(db, tenant_id, status, section_id)


@router.get("/tables/{table_id}")
async def get_table(
    table_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    table = await TablesService.get_table(db, table_id, tenant_id)
    section_name = TablesService._get_section_name(table)
    return {
        "id": table.id, "number": table.number,
        "capacity": table.capacity, "status": table.status,
        "section": section_name, "section_id": table.section_id,
        "guests": table.guests, "waiter_name": table.waiter_name,
        "opened_at": table.opened_at.isoformat() if table.opened_at else None,
    }


@router.post("/tables/{table_id}/reserve")
async def reserve_table(
    table_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Reserva una mesa (available → reserved)."""
    return await TablesService.update_table_status(db, table_id, tenant_id, "reserved")


@router.post("/tables/{table_id}/free")
async def free_table(
    table_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Libera una mesa (reserved/occupied → available)."""
    return await TablesService.update_table_status(db, table_id, tenant_id, "available")


@router.post("/tables/{table_id}/open")
async def open_table(
    table_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    import logging
    logger = logging.getLogger(__name__)

    waiter_name = body.get("waiter_name") or current_user.full_name

    # Security audit: log if waiter_name differs from authenticated user
    if waiter_name != current_user.full_name:
        logger.warning(
            "Waiter_name override: user '%s' (id=%d) opened table %d with waiter_name='%s'",
            current_user.full_name, current_user.id, table_id, waiter_name,
        )

    return await TablesService.open_table(
        db, table_id, tenant_id,
        guests=body.get("guests", 1),
        waiter_name=waiter_name,
    )


# ═══════════════════════════════════════════════════════════════
# MENU (F0-005)
# ═══════════════════════════════════════════════════════════════

@router.get("/menu")
async def list_menu(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: str | None = Query(None),
    active_only: bool = Query(False, alias="available"),
):
    return await MenuService.list_items(db, tenant_id, category, active_only)


@router.post("/menu")
async def create_menu_item(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    return await MenuService.create_item(db, tenant_id, body)


# ═══════════════════════════════════════════════════════════════
# RECIPES (Caso 6: Recetas e Insumos)
# ═══════════════════════════════════════════════════════════════

@router.get("/menu/{item_id}/recipe")
async def get_recipe(
    item_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    GET /api/v1/restaurant/menu/{id}/recipe

    Obtener la receta de un plato del menú.
    Retorna ingredientes, costo estimado y margen.
    Solo platos con preparation_area="cocina" pueden tener receta.
    """
    return await RecipesService.get_recipe(db, item_id, tenant_id)


@router.put("/menu/{item_id}/recipe")
async def save_recipe(
    item_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    """
    PUT /api/v1/restaurant/menu/{id}/recipe

    Guardar/actualizar receta completa de un plato.
    Reemplaza todos los ingredientes.
    Solo platos con preparation_area="cocina" pueden tener receta.
    """
    ingredients = body.get("ingredients", [])
    return await RecipesService.save_recipe(db, item_id, tenant_id, ingredients)


@router.get("/products")
async def list_products_for_recipe(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    GET /api/v1/restaurant/products

    Listar productos del inventario (activos) para selector de insumos en receta.
    Retorna id, name, unit_of_measure, average_cost, current_stock.
    """
    return await RecipesService.list_products_for_recipe(db, tenant_id)


@router.patch("/menu/{item_id}")
async def update_menu_item(
    item_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    return await MenuService.update_item(db, item_id, tenant_id, body)


# ═══════════════════════════════════════════════════════════════
# ORDERS (F0-005, F0-006)
# ═══════════════════════════════════════════════════════════════

@router.post("/tables/{table_id}/order")
async def take_order(
    table_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    items = body.get("items", [])
    if not items:
        raise HTTPException(status_code=400, detail="Se requiere al menos un ítem")
    return await KitchenOrdersService.create_order(db, tenant_id, table_id, items)


@router.get("/orders/active")
async def list_active_orders(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = Query(None),
):
    return await KitchenOrdersService.list_active_orders(db, tenant_id, status)


@router.get("/orders/{order_id}")
async def get_order_detail(
    order_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await KitchenOrdersService.get_order_detail(db, order_id, tenant_id)


@router.post("/orders/{order_id}/send-to-kitchen")
async def send_to_kitchen(
    order_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await KitchenOrdersService.send_to_kitchen(db, order_id, tenant_id)


@router.patch("/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    new_status = body.get("status", "")
    if not new_status:
        raise HTTPException(status_code=400, detail="Se requiere 'status'")
    return await KitchenOrdersService.update_status(db, order_id, tenant_id, new_status)


@router.delete("/orders/{order_id}/items/{menu_item_id}")
async def remove_order_item(
    order_id: int,
    menu_item_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Resta 1 unidad de un item (o lo elimina si quantity=1)."""
    return await KitchenOrdersService.remove_item(db, order_id, menu_item_id, tenant_id)


# ═══════════════════════════════════════════════════════════════
# CLOSE & PAY (F0-007)
# ═══════════════════════════════════════════════════════════════

@router.post("/tables/{table_id}/close-order")
async def close_order(
    table_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await ClosePayService().close_order(db, table_id, tenant_id)


@router.get("/tables/{table_id}/orders/status")
async def get_table_orders_status(
    table_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Retorna si todas las comandas de una mesa están entregadas
    (para que el frontend sepa si habilitar el botón Pagar).
    """
    return await ClosePayService().get_table_orders_status(db, table_id, tenant_id)


@router.post("/tables/{table_id}/pay")
async def pay_table(
    table_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    body["user_id"] = current_user.id
    return await ClosePayService().pay_table(db, table_id, tenant_id, body)


# ═══════════════════════════════════════════════════════════════
# TAKEAWAY (F0-009)
# ═══════════════════════════════════════════════════════════════

@router.post("/takeaway")
async def create_takeaway(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    return await TakeawayService.create(db, tenant_id, body)


@router.get("/takeaway")
async def list_takeaway(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = Query(None),
):
    return await TakeawayService.list_orders(db, tenant_id, status)


@router.patch("/takeaway/{order_id}/status")
async def update_takeaway_status(
    order_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    """Actualiza el estado de un pedido takeaway desde cocina (HU-F0-016).

    Transiciones válidas:
      pending → preparing | cancelled
      preparing → ready | cancelled
      ready → picked_up
    """
    new_status = body.get("status", "")
    if not new_status:
        raise HTTPException(status_code=400, detail="Se requiere 'status'")
    return await TakeawayService.update_status(db, order_id, tenant_id, new_status)


@router.patch("/takeaway/{order_id}/pickup")
async def mark_takeaway_pickup(
    order_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await TakeawayService.mark_pickup(db, order_id, tenant_id)


# ═══════════════════════════════════════════════════════════════
# PROMOTIONS (F0-008)
# ═══════════════════════════════════════════════════════════════

@router.post("/promotions")
async def create_promotion(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    return await PromotionsService.create_promotion(db, tenant_id, body)


@router.get("/promotions")
async def list_promotions(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    active_only: bool = Query(True, alias="active"),
):
    return await PromotionsService.list_promotions(db, tenant_id, active_only)


@router.patch("/promotions/{promotion_id}")
async def update_promotion(
    promotion_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    return await PromotionsService.update_promotion(db, promotion_id, tenant_id, body)


@router.post("/orders/{order_id}/apply-promotion/{promotion_id}")
async def apply_promotion(
    order_id: int,
    promotion_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await PromotionsService.apply_promotion(db, order_id, promotion_id, tenant_id)


# ═══════════════════════════════════════════════════════════════
# SECTIONS (Caso 2: Mantenimiento de Secciones)
# ═══════════════════════════════════════════════════════════════

@router.post("/sections", status_code=201)
async def create_section(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    """Crea una nueva sección del salón."""
    if not body.get("name"):
        raise HTTPException(status_code=400, detail="'name' es requerido")
    return await SectionsService.create_section(db, tenant_id, body)


@router.get("/sections")
async def list_sections(
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Lista todas las secciones ordenadas por sort_order, name."""
    return await SectionsService.list_sections(db, tenant_id)


@router.get("/sections/{section_id}")
async def get_section(
    section_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Obtiene una sección por ID."""
    return await SectionsService.get_section(db, section_id, tenant_id)


@router.patch("/sections/{section_id}")
async def update_section(
    section_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: dict,
):
    """Actualiza una sección (nombre, descripción, orden)."""
    return await SectionsService.update_section(db, section_id, tenant_id, body)


@router.delete("/sections/{section_id}", status_code=204)
async def delete_section(
    section_id: int,
    tenant_id: Annotated[int, Depends(get_tenant_id)],
    current_user: Annotated[User, Depends(require_role("admin", "manager"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Elimina una sección (solo si no tiene mesas asociadas).

    Si tiene mesas asociadas devuelve 409 Conflict.
    """
    await SectionsService.delete_section(db, section_id, tenant_id)


# ═══════════════════════════════════════════════════════════════
# WEBSOCKET (F0-006)
# ═══════════════════════════════════════════════════════════════

@router.websocket("/ws/kitchen/{tenant_id}")
async def kitchen_websocket(ws: WebSocket, tenant_id: int):
    await manager.connect_kitchen(tenant_id, ws)
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text('{"event": "pong"}')
    except WebSocketDisconnect:
        manager.disconnect_kitchen(tenant_id, ws)
    except Exception:
        manager.disconnect_kitchen(tenant_id, ws)


@router.websocket("/ws/waiter/{tenant_id}")
async def waiter_websocket(ws: WebSocket, tenant_id: int):
    await manager.connect_waiter(tenant_id, ws)
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text('{"event": "pong"}')
    except WebSocketDisconnect:
        manager.disconnect_waiter(tenant_id, ws)
    except Exception:
        manager.disconnect_waiter(tenant_id, ws)
