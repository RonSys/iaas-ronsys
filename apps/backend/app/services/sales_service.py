"""
💰 Sales Service — Servicio de ventas POS + integración contable.

HU-F2-003: Sesiones POS (abrir, consultar, cerrar)
HU-F2-004: Ventas CRUD (crear, listar, detalle, anular)
HU-F2-005: Integración Kárdex (salida/inventario automática)
HU-F2-006: Asiento contable automático
HU-F2-007: Ticket formateado + payment methods

Arquitectura: Puertos abstractos → Adaptadores concretos (DB).
"""

from datetime import date, datetime, time, UTC
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models.sales import (
    HardwareSale,
    PosSession,
    RestaurantSale,
    Sale,
    SaleItem,
    SalePayment,
)
from app.adapters.db.models.accounting import (
    Company,
    JournalEntry,
    JournalEntryLine,
    KardexMovement,
    Product,
    ProductUnit,
)
from app.core.accounting.kardex import KardexEngine


# ═══════════════════════════════════════════════════════════════
# Sesiones POS
# ═══════════════════════════════════════════════════════════════


class PosSessionService:
    """Servicio de gestión de turnos de caja."""

    @staticmethod
    async def open_session(
        db: AsyncSession,
        tenant_id: int,
        user_id: int,
        opening_cash: float,
        notes: str | None = None,
    ) -> PosSession:
        """
        HU-F2-003: Abre una nueva sesión POS.

        Valida que no haya otra sesión abierta (409 si existe).
        """
        # Validar: no haya sesión abierta
        existing = await db.execute(
            select(PosSession).where(
                PosSession.tenant_id == tenant_id,
                PosSession.status == "open",
            )
        )
        if existing.scalar_one_or_none():
            from fastapi import HTTPException
            raise HTTPException(
                status_code=409,
                detail="Ya existe una sesión POS abierta. Ciérrela primero.",
            )

        session = PosSession(
            tenant_id=tenant_id,
            user_id=user_id,
            opening_cash=opening_cash,
            notes=notes,
            status="open",
            opened_at=datetime.now(UTC),
        )
        db.add(session)
        await db.flush()
        await db.refresh(session)
        return session

    @staticmethod
    async def get_current_session(
        db: AsyncSession,
        tenant_id: int,
    ) -> PosSession | None:
        """Obtiene la sesión POS abierta actual."""
        result = await db.execute(
            select(PosSession).where(
                PosSession.tenant_id == tenant_id,
                PosSession.status == "open",
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_session_with_sales(
        db: AsyncSession,
        session_id: int,
        tenant_id: int,
    ) -> dict:
        """
        HU-F2-003: Obtiene sesión activa con ventas del turno + totales.
        Retorna 404 si no hay sesión.
        """
        result = await db.execute(
            select(PosSession).where(
                PosSession.id == session_id,
                PosSession.tenant_id == tenant_id,
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Sesión POS no encontrada")

        # Ventas del turno
        sales_result = await db.execute(
            select(Sale).where(
                Sale.session_id == session_id,
                Sale.is_voided == False,  # noqa: E712
            )
        )
        sales = sales_result.scalars().all()

        total_sales = sum(float(s.total) for s in sales)
        total_cash = sum(
            float(p.amount) for s in sales
            for p in s.payments if p.payment_method == "cash"
        )
        total_card = sum(
            float(p.amount) for s in sales
            for p in s.payments if p.payment_method == "card"
        )
        total_yape_plin = sum(
            float(p.amount) for s in sales
            for p in s.payments if p.payment_method in ("yape", "plin")
        )
        total_transfer = sum(
            float(p.amount) for s in sales
            for p in s.payments if p.payment_method == "transfer"
        )

        return {
            "id": session.id,
            "company_id": session.company_id,
            "user_id": session.user_id,
            "opened_at": session.opened_at,
            "closed_at": session.closed_at,
            "opening_cash": float(session.opening_cash),
            "closing_cash": float(session.closing_cash) if session.closing_cash else None,
            "expected_cash": float(session.expected_cash) if session.expected_cash else None,
            "difference": float(session.difference) if session.difference else None,
            "status": session.status,
            "notes": session.notes,
            "sales_count": len(sales),
            "total_sales": round(total_sales, 2),
            "totals_by_payment": {
                "cash": round(total_cash, 2),
                "card": round(total_card, 2),
                "yape_plin": round(total_yape_plin, 2),
                "transfer": round(total_transfer, 2),
            },
        }

    @staticmethod
    async def close_session(
        db: AsyncSession,
        session_id: int,
        tenant_id: int,
        closing_cash: float,
        notes: str | None = None,
    ) -> dict:
        """
        HU-F2-003: Cierra sesión POS.

        Calcula expected_cash = opening + ventas_efectivo.
        Compara con closing_cash → difference.
        status → closed. 409 si ya cerrada.
        """
        result = await db.execute(
            select(PosSession).where(
                PosSession.id == session_id,
                PosSession.tenant_id == tenant_id,
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Sesión POS no encontrada")
        if session.status == "closed":
            from fastapi import HTTPException
            raise HTTPException(status_code=409, detail="La sesión ya está cerrada")

        # Calcular ventas en efectivo del turno
        from sqlalchemy.orm import selectinload

        sales_result = await db.execute(
            select(Sale)
            .options(selectinload(Sale.payments))
            .where(
                Sale.session_id == session_id,
                Sale.is_voided == False,  # noqa: E712
            )
        )
        sales = sales_result.scalars().all()

        cash_sales = sum(
            float(p.amount) for s in sales
            for p in s.payments if p.payment_method == "cash"
        )

        expected = float(session.opening_cash) + cash_sales
        difference = round(closing_cash - expected, 2)

        session.closing_cash = closing_cash
        session.expected_cash = expected
        session.difference = difference
        session.status = "closed"
        session.closed_at = datetime.now(UTC)
        if notes:
            session.notes = notes

        await db.flush()

        return {
            "id": session.id,
            "opening_cash": float(session.opening_cash),
            "closing_cash": closing_cash,
            "expected_cash": round(expected, 2),
            "difference": difference,
            "status": "closed",
            "cash_sales": round(cash_sales, 2),
            "sales_count": len(sales),
        }


# ═══════════════════════════════════════════════════════════════
# Ventas CRUD
# ═══════════════════════════════════════════════════════════════


class SaleService:
    """Servicio de ventas con integración completa."""

    @staticmethod
    def _resolve_unit_price(product: Product, quantity: float) -> float:
        """
        HU-F0-009-03: Resuelve precio unitario según reglas mayorista/detal.

        Si wholesale_price y wholesale_min_qty están definidos y
        quantity >= wholesale_min_qty, se usa wholesale_price.
        De lo contrario, retail_price.
        """
        retail = float(product.retail_price) if product.retail_price else 0.0
        wholesale = float(product.wholesale_price) if product.wholesale_price else None
        min_qty = float(product.wholesale_min_qty) if product.wholesale_min_qty else None

        if wholesale is not None and wholesale > 0 and min_qty is not None and quantity >= min_qty:
            return wholesale
        return retail

    @staticmethod
    async def create_sale(
        db: AsyncSession,
        tenant_id: int,
        user_id: int,
        data: dict,  # SaleCreate dict
    ) -> dict:
        """
        HU-F2-004: Crea venta con items + payments.
        HU-F2-005: Integración kárdex automática.
        HU-F2-006: Asiento contable automático.

        Valida sesión abierta, payments cubren total, stock suficiente.
        """
        from fastapi import HTTPException

        # 1. Validar sesión abierta (opcional en Fase 1)
        session = await PosSessionService.get_current_session(db, tenant_id)

        # 2. Cargar empresa (business_type + tax + defaults)
        company_result = await db.execute(
            select(Company).where(Company.id == tenant_id)
        )
        company = company_result.scalar_one_or_none()

        items_data = data.get("items", [])
        payments_data = data.get("payments", [])
        # Usar business_type de la compañía; fallback al request o "retail"
        business_type = (
            company.business_type if company
            else data.get("business_type", "retail")
        )

        if not items_data:
            raise HTTPException(status_code=400, detail="La venta debe tener al menos un ítem")
        if not payments_data:
            raise HTTPException(status_code=400, detail="La venta debe tener al menos un pago")

        # 3. Calcular totales + validar stock (kárdex)
        subtotal = 0.0
        discount_total = 0.0
        tax_total = 0.0
        total_items = 0.0

        for item_data in items_data:
            item_total = float(item_data.get("total", 0))
            item_qty = float(item_data.get("quantity", 0))
            item_price = float(item_data.get("unit_price", 0))
            item_disc_pct = float(item_data.get("discount_pct", 0))
            item_disc_amt = float(item_data.get("discount_amount", 0))
            product_id_raw = item_data.get("product_id")
            try:
                product_id = int(product_id_raw) if product_id_raw is not None else None
            except (ValueError, TypeError):
                product_id = None
            # QA-F2-01: soportar igv_included (precio ya incluye IGV)
            igv_included = item_data.get("igv_included", False)
            if isinstance(igv_included, str):
                igv_included = igv_included.lower() in ("true", "1", "yes")

            # Calcular tax_base y tax_amt según igv_included
            if igv_included and item_price > 0:
                tax_pct = float(item_data.get("tax_pct", 18))
                tax_rate = tax_pct / 100
                base_price = round(item_price / (1 + tax_rate), 4)
                tax_amt_per_unit = round(item_price - base_price, 4)
            else:
                tax_pct = float(item_data.get("tax_pct", 18))
                base_price = item_price
                tax_amt_per_unit = 0

            # Calcular si no viene total
            if item_price > 0 and item_qty > 0 and item_total == 0:
                line_total = item_qty * base_price
                item_disc = 0.0
                if item_disc_pct > 0:
                    item_disc = round(line_total * item_disc_pct / 100, 2)
                    item_disc_amt = item_disc
                taxed = round(line_total - item_disc, 2)
                tax_amt = round(taxed * tax_pct / 100, 2)
                item_total = round(taxed + tax_amt, 2)
            else:
                # Total viene del cliente; calcular tax_amt
                if igv_included and item_total > 0:
                    tax_rate = tax_pct / 100
                    base = round(item_total / (1 + tax_rate), 2)
                    tax_amt = round(item_total - base, 2)
                elif item_total > 0 and item_qty > 0:
                    tax_amt = round((item_total * tax_pct / 100), 2)
                else:
                    tax_amt = 0

            # Validar stock si tiene product_id
            if product_id:
                product_result = await db.execute(
                    select(Product).where(Product.id == product_id)
                )
                product = product_result.scalar_one_or_none()

                if product:
                    # HU-F0-009-03: Aplicar wholesale pricing automáticamente
                    resolved_price = SaleService._resolve_unit_price(product, item_qty)
                    if resolved_price != item_price:
                        item_data["unit_price"] = resolved_price
                        item_price = resolved_price
                        item_data["applied_wholesale"] = True

                    # HU-F0-009-05: Validar seriales si has_serial
                    if product.has_serial:
                        item_serials = item_data.get("serials")
                        if not item_serials or len(item_serials) != int(item_qty):
                            raise HTTPException(
                                status_code=422,
                                detail=f"El producto '{product.name}' requiere seriales. "
                                       f"Debe seleccionar exactamente {int(item_qty)} serial(es)."
                            )
                        # Validar que los seriales existen y están disponibles
                        serials_result = await db.execute(
                            select(ProductUnit).where(
                                ProductUnit.serial_number.in_(item_serials),
                                ProductUnit.product_id == product_id,
                                ProductUnit.status == "available",
                            ).with_for_update()
                        )
                        available_units = serials_result.scalars().all()
                        available_serials = {u.serial_number for u in available_units}

                        missing = set(item_serials) - available_serials
                        if missing:
                            raise HTTPException(
                                status_code=409,
                                detail=f"Seriales no disponibles para '{product.name}': "
                                       f"{', '.join(sorted(missing))}"
                            )

                        # Stock para seriales = count de available
                        serial_stock = len(available_units)
                        if serial_stock < item_qty:
                            raise HTTPException(
                                status_code=409,
                                detail=f"Stock insuficiente de '{product.name}': "
                                       f"solo {serial_stock} seriales disponibles, "
                                       f"solicitado {item_qty}"
                            )
                    else:
                        # Producto sin serial: validar stock numérico tradicional
                        if product and float(product.current_stock) < item_qty:
                            raise HTTPException(
                                status_code=409,
                                detail=f"Stock insuficiente de '{product.name}': "
                                      f"disponible {float(product.current_stock)}, "
                                      f"solicitado {item_qty}"
                            )

            subtotal += round(item_qty * base_price, 2)
            discount_total += item_disc_amt
            tax_total += tax_amt
            total_items += item_total

        # Tip amount
        tip_amount = 0.0
        # QA-F2-02: aceptar tanto "restaurant" como "restaurant_data"
        restaurant_data = data.get("restaurant_data") or data.get("restaurant")
        hardware_data = data.get("hardware_data") or data.get("hardware")
        if restaurant_data and business_type == "restaurant":
            tip_amount = float(restaurant_data.get("tip_amount", 0))

        total_sale = round(total_items + tip_amount, 2)

        # 4. Validar pagos cubren total
        total_payments = sum(float(p.get("amount", 0)) for p in payments_data)
        if total_payments < total_sale - 0.01:
            raise HTTPException(
                status_code=400,
                detail=f"Pagos ({total_payments:.2f}) no cubren total ({total_sale:.2f})"
            )

        # 5. Generar sale_number: VEN-YYYY-NNNNN
        today = date.today()
        year = today.year

        count_result = await db.execute(
            select(func.count(Sale.id)).where(
                Sale.tenant_id == tenant_id,
                Sale.sale_date >= date(year, 1, 1),
            )
        )
        count = count_result.scalar() or 0
        import time as _time
        sale_number = f"VEN-{year}-{count + 1:05d}-{int(_time.time()) % 1000:03d}"

        # 6. Crear Sale
        sale = Sale(
            tenant_id=tenant_id,
            session_id=session.id if session else None,
            user_id=user_id,
            sale_number=sale_number,
            sale_date=today,
            sale_time=datetime.now(UTC).time(),
            customer_name=data.get("customer_name"),
            customer_doc=data.get("customer_doc"),
            subtotal=round(subtotal, 2),
            discount_total=round(discount_total, 2),
            tax_total=round(tax_total, 2),
            tip_amount=round(tip_amount, 2),
            total=round(total_sale, 2),
            business_type=business_type,
        )
        db.add(sale)
        await db.flush()
        await db.refresh(sale)

        # 7. Crear SaleItems + movimientos kárdex
        sale_items_list = []
        for item_data in items_data:
            product_id_raw = item_data.get("product_id")
            try:
                product_id = int(product_id_raw) if product_id_raw is not None else None
            except (ValueError, TypeError):
                product_id = None
            item_qty = float(item_data.get("quantity", 0))
            item_price = float(item_data.get("unit_price", 0))
            item_total = float(item_data.get("total", 0))
            item_disc_pct = float(item_data.get("discount_pct", 0))
            item_disc_amt = float(item_data.get("discount_amount", 0))
            tax_pct = float(item_data.get("tax_pct", 18))
            tax_amt = float(item_data.get("tax_amount", 0))
            # QA-F2-01: recalcular si igv_included
            igv_included = item_data.get("igv_included", False)
            if isinstance(igv_included, str):
                igv_included = igv_included.lower() in ("true", "1", "yes")

            if item_price > 0 and item_qty > 0 and item_total == 0:
                tax_rate = tax_pct / 100
                if igv_included:
                    base = round(item_price / (1 + tax_rate), 4)
                    line_total = item_qty * base
                else:
                    line_total = item_qty * item_price
                if item_disc_pct > 0:
                    item_disc_amt = round(line_total * item_disc_pct / 100, 2)
                taxed = round(line_total - item_disc_amt, 2)
                tax_amt = round(taxed * tax_pct / 100, 2)
                item_total = round(taxed + tax_amt, 2)
                if item_disc_pct > 0:
                    item_disc_amt = round(line_total * item_disc_pct / 100, 2)
                item_total = round(line_total - item_disc_amt, 2)
                tax_amt = round(item_total * tax_pct / 100, 2)
                item_total = round(item_total + tax_amt, 2)

            kardex_movement_id = None

            # HU-F2-005: Registrar salida en kárdex si tiene product_id
            if product_id:
                product = (await db.execute(
                    select(Product).where(Product.id == product_id)
                )).scalar_one_or_none()

                if product:
                    if product.has_serial:
                        # HU-F0-009-05: Para seriales, el costo es el promedio de los seriales vendidos
                        item_serials = item_data.get("serials", [])
                        serial_units = (await db.execute(
                            select(ProductUnit).where(
                                ProductUnit.serial_number.in_(item_serials),
                                ProductUnit.product_id == product_id,
                            )
                        )).scalars().all()

                        # Calcular costo promedio de los seriales vendidos
                        costs = [
                            float(u.cost_price) if u.cost_price else float(product.average_cost)
                            for u in serial_units
                        ]
                        avg_serial_cost = round(sum(costs) / len(costs), 4) if costs else float(product.average_cost)
                        exit_total = round(item_qty * avg_serial_cost, 2)

                        # Actualizar average_cost del producto con el costo real de venta
                        new_avg_cost = avg_serial_cost
                    else:
                        avg_cost = float(product.average_cost)
                        exit_total = round(item_qty * avg_cost, 2)
                        new_avg_cost = avg_cost

                    # Calcular balance para kárdex
                    if product.has_serial:
                        # Stock para seriales = count de available restantes después de la venta
                        available_after = await db.execute(
                            select(func.count(ProductUnit.id)).where(
                                ProductUnit.product_id == product_id,
                                ProductUnit.status == "available",
                            )
                        )
                        new_qty = float(available_after.scalar() or 0)
                    else:
                        new_qty = float(product.current_stock) - item_qty

                    new_total = round(new_qty * new_avg_cost, 2)

                    kardex_move = KardexMovement(
                        product_id=product_id,
                        movement_type="salida",
                        concept=f"Venta #{sale_number}",
                        reference_type="venta",
                        reference_id=sale.id,
                        quantity=item_qty,
                        unit_cost=new_avg_cost,
                        total=exit_total,
                        balance_quantity=new_qty,
                        balance_avg_cost=new_avg_cost,
                        balance_total=new_total,
                        date=today,
                    )
                    db.add(kardex_move)
                    await db.flush()
                    await db.refresh(kardex_move)
                    kardex_movement_id = kardex_move.id

                    # Actualizar stock del producto
                    if not product.has_serial:
                        product.current_stock = new_qty
                    product.average_cost = new_avg_cost

            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=product_id,
                item_name=item_data.get("item_name", ""),
                item_type=item_data.get("item_type", "product"),
                quantity=item_qty,
                unit_of_measure=item_data.get("unit_of_measure", "unidad"),
                unit_price=item_price,
                discount_pct=item_disc_pct,
                discount_amount=item_disc_amt,
                tax_pct=tax_pct,
                tax_amount=tax_amt,
                total=item_total,
                kardex_movement_id=kardex_movement_id,
            )
            db.add(sale_item)
            sale_items_list.append(sale_item)

        await db.flush()

        # 7b. HU-F0-009-05: Asignar seriales a sale_items
        for item_data in items_data:
            if item_data.get("product_id") and item_data.get("serials"):
                # Encontrar el SaleItem recién creado
                matching_item = next(
                    (si for si in sale_items_list
                     if si.product_id == item_data.get("product_id")
                     and si.item_name == item_data.get("item_name", "")
                     and float(si.quantity) == float(item_data.get("quantity", 0))),
                    None
                )
                if matching_item:
                    serial_numbers = item_data.get("serials", [])
                    await db.execute(
                        update(ProductUnit)
                        .where(ProductUnit.serial_number.in_(serial_numbers))
                        .values(
                            status="sold",
                            sale_id=sale.id,
                            sale_item_id=matching_item.id,
                        )
                    )
                    # Store serials on item for response
                    matching_item._serials = serial_numbers

        await db.flush()

        # 8. Crear SalePayments
        sale_payments_list = []
        for p_data in payments_data:
            payment = SalePayment(
                sale_id=sale.id,
                payment_method=p_data.get("payment_method", "cash"),
                amount=float(p_data.get("amount", 0)),
                reference=p_data.get("reference"),
            )
            db.add(payment)
            sale_payments_list.append(payment)

        await db.flush()

        # 9. Crear especialización
        if restaurant_data and business_type == "restaurant":
            r = RestaurantSale(
                sale_id=sale.id,
                table_number=restaurant_data.get("table_number"),
                guests=int(restaurant_data.get("guests", 1)),
                order_type=restaurant_data.get("order_type", "dine_in"),
                waiter_name=restaurant_data.get("waiter_name"),
                tip_amount=float(restaurant_data.get("tip_amount", 0)),
                tip_pct=float(restaurant_data.get("tip_pct", 0)),
                kitchen_notes=restaurant_data.get("kitchen_notes"),
            )
            db.add(r)

        hardware_data = data.get("hardware_data") or data.get("hardware")
        if hardware_data and business_type == "hardware":
            h = HardwareSale(
                sale_id=sale.id,
                invoice_type=hardware_data.get("invoice_type", "boleta"),
                delivery_address=hardware_data.get("delivery_address"),
                requires_install=bool(hardware_data.get("requires_install", False)),
                warranty_months=int(hardware_data.get("warranty_months", 0)),
            )
            db.add(h)

        await db.flush()

        # 10. HU-F2-006: Generar asiento contable automático
        entry = await SaleService._generate_journal_entry(
            db, sale, sale_items_list, sale_payments_list, business_type
        )

        if entry:
            sale.journal_entry_id = entry.id

        await db.flush()
        await db.refresh(sale)

        # Return sale detail with post-sale message
        sale_detail = await SaleService.get_sale_detail(db, sale.id, tenant_id)
        return {
            "sale": sale_detail,
            "message": "✅ Venta registrada. Inventario actualizado.",
            "warning": "📋 Guía de remisión pendiente",
        }

    @staticmethod
    async def _generate_journal_entry(
        db: AsyncSession,
        sale: Sale,
        items: list[SaleItem],
        payments: list[SalePayment],
        business_type: str,
    ) -> JournalEntry | None:
        """
        HU-F2-006: Genera asiento contable automático por venta.

        Restaurant:
          Debe: 10 Caja (cash) / 121 Cuentas por cobrar (card) / 10 (yape/plin) / 104 (transfer)
          Haber: 40 Ventas / 201 IGV por pagar
          Si hay propina: Haber: 24 Propinas por pagar

        Hardware:
          Debe: 10 Caja (cash) / 121 Cuentas por cobrar (card)
          Haber: 40 Ventas / 201 IGV por pagar
          Debe: 50 Costo de Ventas / Haber: 12 Inventarios
        """
        today = date.today()
        year = today.year

        # Contar asientos del año para entry_number
        count_result = await db.execute(
            select(func.count(JournalEntry.id)).where(
                JournalEntry.tenant_id == sale.company_id,
                JournalEntry.date >= date(year, 1, 1),
            )
        )
        count = count_result.scalar() or 0
        entry_number = f"AS-{year}-{count + 1:05d}"

        lines: list[dict] = []

        # ─── Pagos → Debe (ingreso de efectivo/cuenta) ───
        for p in payments:
            method = p.payment_method
            amt = float(p.amount)

            if method == "cash":
                lines.append({"account": "10", "debit": amt, "credit": 0, "desc": f"Caja — {method}"})
            elif method == "card":
                lines.append({"account": "121", "debit": amt, "credit": 0, "desc": f"Cuentas por cobrar tarjeta — {method}"})
            elif method == "yape" or method == "plin":
                lines.append({"account": "10", "debit": amt, "credit": 0, "desc": f"Caja — {method}"})
            elif method == "transfer":
                lines.append({"account": "104", "debit": amt, "credit": 0, "desc": f"Transferencia bancaria — {method}"})

        # ─── Ingresos → Haber ───
        # Ventas (neto de impuestos)
        sale_total_no_tax = round(float(sale.subtotal) - float(sale.discount_total), 2)
        tax_amount = float(sale.tax_total)

        lines.append({
            "account": "40", "debit": 0, "credit": sale_total_no_tax,
            "desc": f"Ingresos por ventas — {sale.sale_number}"
        })

        if tax_amount > 0:
            lines.append({
                "account": "201", "debit": 0, "credit": tax_amount,
                "desc": f"IGV por pagar — {sale.sale_number}"
            })

        # Propina (restaurante)
        if business_type == "restaurant" and float(sale.tip_amount) > 0:
            lines.append({
                "account": "24", "debit": 0, "credit": float(sale.tip_amount),
                "desc": f"Propinas por pagar — {sale.sale_number}"
            })

        # ─── Costo de Ventas (hardware) ───
        if business_type == "hardware":
            items_with_kardex = [i for i in items if i.kardex_movement_id]
            if items_with_kardex:
                # Sumar costos de las salidas de kárdex
                total_cost = 0.0
                for item in items_with_kardex:
                    move = (await db.execute(
                        select(KardexMovement).where(KardexMovement.id == item.kardex_movement_id)
                    )).scalar_one_or_none()
                    if move:
                        total_cost += float(move.total)

                if total_cost > 0:
                    lines.append({
                        "account": "50", "debit": total_cost, "credit": 0,
                        "desc": f"Costo de ventas — {sale.sale_number}"
                    })
                    lines.append({
                        "account": "12", "debit": 0, "credit": total_cost,
                        "desc": f"Inventarios salida — {sale.sale_number}"
                    })

        # Validar partida doble
        total_debit = sum(l["debit"] for l in lines)
        total_credit = sum(l["credit"] for l in lines)

        # Ajustar diferencia si hay redondeo
        diff = round(total_debit - total_credit, 2)
        if abs(diff) > 0.001:
            if diff > 0:
                # Hay más débito, ajustar con un crédito extra
                lines.append({
                    "account": "40", "debit": 0, "credit": abs(diff),
                    "desc": f"Ajuste redondeo — {sale.sale_number}"
                })
            else:
                lines.append({
                    "account": "40", "debit": abs(diff), "credit": 0,
                    "desc": f"Ajuste redondeo — {sale.sale_number}"
                })

        # Crear asiento
        entry = JournalEntry(
            tenant_id=sale.company_id,
            entry_number=entry_number,
            date=today,
            description=f"Venta {sale.sale_number} — {sale.business_type}",
            entry_type="venta",
            reference=sale.sale_number,
        )
        db.add(entry)
        await db.flush()
        await db.refresh(entry)

        for line_data in lines:
            jl = JournalEntryLine(
                entry_id=entry.id,
                account_code=line_data["account"],
                debit=line_data["debit"],
                credit=line_data["credit"],
                description=line_data["desc"],
            )
            db.add(jl)

        await db.flush()
        return entry

    @staticmethod
    async def list_sales(
        db: AsyncSession,
        tenant_id: int,
        page: int = 1,
        limit: int = 20,
        from_date: date | None = None,
        to_date: date | None = None,
        business_type: str | None = None,
        session_id: int | None = None,
        is_voided: bool | None = None,
    ) -> dict:
        """HU-F2-004: Lista ventas paginado con filtros."""
        conditions = [Sale.tenant_id == tenant_id]

        if from_date:
            conditions.append(Sale.sale_date >= from_date)
        if to_date:
            conditions.append(Sale.sale_date <= to_date)
        if business_type:
            conditions.append(Sale.business_type == business_type)
        if session_id is not None:
            conditions.append(Sale.session_id == session_id)
        if is_voided is not None:
            conditions.append(Sale.is_voided == is_voided)

        # Count
        count_result = await db.execute(
            select(func.count(Sale.id)).where(*conditions)
        )
        total = count_result.scalar() or 0

        pages = max(1, (total + limit - 1) // limit)

        # Query with pagination
        from sqlalchemy.orm import selectinload

        result = await db.execute(
            select(Sale)
            .options(selectinload(Sale.payments))
            .where(*conditions)
            .order_by(Sale.sale_date.desc(), Sale.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        sales = result.scalars().all()

        items = []
        for s in sales:
            items.append({
                "id": s.id,
                "sale_number": s.sale_number,
                "sale_date": s.sale_date,
                "sale_time": s.sale_time,
                "customer_name": s.customer_name,
                "business_type": s.business_type,
                "subtotal": float(s.subtotal),
                "discount_total": float(s.discount_total),
                "tax_total": float(s.tax_total),
                "tip_amount": float(s.tip_amount),
                "total": float(s.total),
                "is_voided": s.is_voided,
                "void_reason": s.void_reason,
                "payments": [
                    {
                        "id": p.id,
                        "payment_method": p.payment_method,
                        "amount": float(p.amount),
                        "reference": p.reference,
                    }
                    for p in s.payments
                ],
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
        }

    @staticmethod
    async def get_sale_detail(
        db: AsyncSession,
        sale_id: int,
        tenant_id: int,
    ) -> dict:
        """HU-F2-004: Detalle de venta con items, payments, especialización."""
        from sqlalchemy.orm import selectinload

        result = await db.execute(
            select(Sale)
            .options(
                selectinload(Sale.items),
                selectinload(Sale.payments),
                selectinload(Sale.restaurant_sale),
                selectinload(Sale.hardware_sale),
            )
            .where(Sale.id == sale_id, Sale.tenant_id == tenant_id)
        )
        sale = result.scalar_one_or_none()
        if not sale:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Venta no encontrada")

        detail = {
            "id": sale.id,
            "sale_number": sale.sale_number,
            "sale_date": sale.sale_date,
            "sale_time": sale.sale_time,
            "customer_name": sale.customer_name,
            "customer_doc": sale.customer_doc,
            "business_type": sale.business_type,
            "subtotal": float(sale.subtotal),
            "discount_total": float(sale.discount_total),
            "tax_total": float(sale.tax_total),
            "tip_amount": float(sale.tip_amount),
            "total": float(sale.total),
            "is_voided": sale.is_voided,
            "void_reason": sale.void_reason,
            "session_id": sale.session_id,
            "user_id": sale.user_id,
            "journal_entry_id": sale.journal_entry_id,
            "items": [
                {
                    "id": i.id,
                    "product_id": i.product_id,
                    "item_name": i.item_name,
                    "item_type": i.item_type,
                    "quantity": float(i.quantity),
                    "unit_of_measure": i.unit_of_measure,
                    "unit_price": float(i.unit_price),
                    "discount_pct": float(i.discount_pct),
                    "discount_amount": float(i.discount_amount),
                    "tax_pct": float(i.tax_pct),
                    "tax_amount": float(i.tax_amount),
                    "total": float(i.total),
                    "kardex_movement_id": i.kardex_movement_id,
                    # HU-F0-009-06: Seriales vendidos en este item
                    "serials": (
                        list(getattr(i, '_serials', [])) or None
                    ),
                }
                for i in sale.items
            ],
            "payments": [
                {
                    "id": p.id,
                    "payment_method": p.payment_method,
                    "amount": float(p.amount),
                    "reference": p.reference,
                }
                for p in sale.payments
            ],
        }

        # Especialización
        # QA-F2-02b: fallback si selectinload no carga la relación
        if sale.business_type == "restaurant" and not sale.restaurant_sale:
            from app.adapters.db.models.sales import RestaurantSale as RS
            rs_result = await db.execute(
                select(RS).where(RS.sale_id == sale_id)
            )
            sale.restaurant_sale = rs_result.scalar_one_or_none()

        if sale.restaurant_sale:
            detail["restaurant_data"] = {
                "id": sale.restaurant_sale.id,
                "table_number": sale.restaurant_sale.table_number,
                "guests": sale.restaurant_sale.guests,
                "order_type": sale.restaurant_sale.order_type,
                "waiter_name": sale.restaurant_sale.waiter_name,
                "tip_amount": float(sale.restaurant_sale.tip_amount),
                "tip_pct": float(sale.restaurant_sale.tip_pct),
                "kitchen_notes": sale.restaurant_sale.kitchen_notes,
            }

        if sale.business_type == "hardware" and not sale.hardware_sale:
            from app.adapters.db.models.sales import HardwareSale as HS
            hs_result = await db.execute(
                select(HS).where(HS.sale_id == sale_id)
            )
            sale.hardware_sale = hs_result.scalar_one_or_none()

        if sale.hardware_sale:
            detail["hardware_data"] = {
                "id": sale.hardware_sale.id,
                "invoice_type": sale.hardware_sale.invoice_type,
                "delivery_address": sale.hardware_sale.delivery_address,
                "requires_install": sale.hardware_sale.requires_install,
                "warranty_months": sale.hardware_sale.warranty_months,
            }

        return detail

    @staticmethod
    async def void_sale(
        db: AsyncSession,
        sale_id: int,
        tenant_id: int,
        reason: str,
    ) -> dict:
        """
        HU-F2-004: Anula venta.

        - is_voided = true
        - Reversa movimientos kárdex (entrada de devolución)
        - 409 si ya anulada
        """
        from sqlalchemy.orm import selectinload
        from fastapi import HTTPException

        result = await db.execute(
            select(Sale)
            .options(selectinload(Sale.items))
            .where(Sale.id == sale_id, Sale.tenant_id == tenant_id)
        )
        sale = result.scalar_one_or_none()
        if not sale:
            raise HTTPException(status_code=404, detail="Venta no encontrada")
        if sale.is_voided:
            raise HTTPException(status_code=409, detail="La venta ya está anulada")

        # Revertir kárdex (HU-F2-005) y seriales (HU-F0-009-06)
        for item in sale.items:
            if item.product_id:
                # HU-F0-009-06: Revertir seriales a 'available'
                serials_result = await db.execute(
                    select(ProductUnit).where(
                        ProductUnit.sale_item_id == item.id,
                        ProductUnit.status == "sold",
                    )
                )
                sold_units = serials_result.scalars().all()
                for unit in sold_units:
                    unit.status = "available"
                    unit.sale_id = None
                    unit.sale_item_id = None

            if item.product_id and item.kardex_movement_id:
                product_result = await db.execute(
                    select(Product).where(Product.id == item.product_id)
                )
                product = product_result.scalar_one_or_none()

                if product:
                    qty = float(item.quantity)
                    avg_cost = float(product.average_cost)

                    # Devolución: entrada al kárdex
                    if product.current_stock is not None:
                        new_qty = float(product.current_stock) + qty
                        new_total = round(new_qty * avg_cost, 2)

                        reversal = KardexMovement(
                            product_id=item.product_id,
                            movement_type="entrada",
                            concept=f"Anulación venta #{sale.sale_number}",
                            reference_type="venta_anulada",
                            reference_id=sale.id,
                            quantity=qty,
                            unit_cost=avg_cost,
                            total=round(qty * avg_cost, 2),
                            balance_quantity=new_qty,
                            balance_avg_cost=avg_cost,
                            balance_total=new_total,
                            date=date.today(),
                        )
                        db.add(reversal)

                        product.current_stock = new_qty

        # Contra-asiento contable (HU-F2-006)
        if sale.journal_entry_id:
            # Crear contra-asiento que revierte
            year = date.today().year
            count_result = await db.execute(
                select(func.count(JournalEntry.id)).where(
                    JournalEntry.tenant_id == tenant_id,
                    JournalEntry.date >= date(year, 1, 1),
                )
            )
            count = count_result.scalar() or 0
            entry_number = f"AS-{year}-{count + 1:05d}"

            reversal_entry = JournalEntry(
                tenant_id=tenant_id,
                entry_number=entry_number,
                date=date.today(),
                description=f"Anulación venta {sale.sale_number} — {reason}",
                entry_type="venta",
                reference=sale.sale_number,
            )
            db.add(reversal_entry)
            await db.flush()
            await db.refresh(reversal_entry)

            # Revertir cada línea del asiento original
            original_lines = (await db.execute(
                select(JournalEntryLine).where(
                    JournalEntryLine.entry_id == sale.journal_entry_id
                )
            )).scalars().all()

            for ol in original_lines:
                jl = JournalEntryLine(
                    entry_id=reversal_entry.id,
                    account_code=ol.account_code,
                    debit=float(ol.credit),  # Invertido
                    credit=float(ol.debit),  # Invertido
                    description=f"Reversión: {ol.description}",
                )
                db.add(jl)

        sale.is_voided = True
        sale.void_reason = reason
        await db.flush()
        await db.refresh(sale)

        return await SaleService.get_sale_detail(db, sale_id, tenant_id)

    @staticmethod
    def format_ticket(sale_detail: dict, format_type: str = "json") -> dict:
        """
        HU-F2-007: Formatea ticket de venta.

        Args:
            sale_detail: Dict con detalle de venta.
            format_type: 'json' o 'text'.

        Returns:
            Dict con formato solicitado.
        """
        lines = []
        for item in sale_detail.get("items", []):
            lines.append({
                "name": item["item_name"],
                "qty": item["quantity"],
                "unit": item.get("unit_of_measure", "unidad"),
                "unit_price": item["unit_price"],
                "total": item["total"],
            })

        payments = [
            {"method": p["payment_method"], "amount": p["amount"]}
            for p in sale_detail.get("payments", [])
        ]

        ticket = {
            "sale_number": sale_detail["sale_number"],
            "sale_date": str(sale_detail["sale_date"]),
            "sale_time": str(sale_detail["sale_time"]),
            "customer_name": sale_detail.get("customer_name"),
            "customer_doc": sale_detail.get("customer_doc"),
            "business_type": sale_detail.get("business_type"),
            "items": lines,
            "payments": payments,
            "subtotal": sale_detail["subtotal"],
            "discount_total": sale_detail["discount_total"],
            "tax_total": sale_detail["tax_total"],
            "tip_amount": sale_detail["tip_amount"],
            "total": sale_detail["total"],
            # Especialización
            "table_number": sale_detail.get("restaurant_data", {}).get("table_number") if sale_detail.get("restaurant_data") else None,
            "waiter_name": sale_detail.get("restaurant_data", {}).get("waiter_name") if sale_detail.get("restaurant_data") else None,
            "order_type": sale_detail.get("restaurant_data", {}).get("order_type") if sale_detail.get("restaurant_data") else None,
            "invoice_type": sale_detail.get("hardware_data", {}).get("invoice_type") if sale_detail.get("hardware_data") else None,
        }

        if format_type == "text":
            text_lines = []
            text_lines.append("=" * 42)
            text_lines.append("         COMPROBANTE DE VENTA")
            text_lines.append("=" * 42)
            text_lines.append(f"N°: {ticket['sale_number']}")
            text_lines.append(f"Fecha: {ticket['sale_date']} {ticket['sale_time']}")
            if ticket["customer_name"]:
                text_lines.append(f"Cliente: {ticket['customer_name']}")
            if ticket.get("table_number"):
                text_lines.append(f"Mesa: {ticket['table_number']}")
            text_lines.append("-" * 42)
            text_lines.append(f"{'Producto':<20} {'Cant':>5} {'P.U.':>8} {'Total':>8}")
            text_lines.append("-" * 42)
            for item in ticket["items"]:
                name = item["name"][:19]
                text_lines.append(
                    f"{name:<20} {item['qty']:>5.1f} {item['unit_price']:>8.2f} {item['total']:>8.2f}"
                )
            text_lines.append("-" * 42)
            text_lines.append(f"{'Subtotal:':<30} {ticket['subtotal']:>10.2f}")
            if ticket["discount_total"] > 0:
                text_lines.append(f"{'Descuento:':<30} {ticket['discount_total']:>10.2f}")
            if ticket["tax_total"] > 0:
                text_lines.append(f"{'IGV:':<30} {ticket['tax_total']:>10.2f}")
            if ticket["tip_amount"] > 0:
                text_lines.append(f"{'Propina:':<30} {ticket['tip_amount']:>10.2f}")
            text_lines.append(f"{'TOTAL:':<30} {ticket['total']:>10.2f}")
            text_lines.append("-" * 42)
            for p in ticket["payments"]:
                text_lines.append(f"{p['method']:<30} {p['amount']:>10.2f}")
            text_lines.append("=" * 42)
            text_lines.append("        ¡Gracias por su compra!")
            text_lines.append("=" * 42)

            ticket["text"] = "\n".join(text_lines)

        return ticket

    @staticmethod
    def get_payment_methods(business_type: str) -> dict:
        """
        HU-F2-007: Devuelve métodos de pago habilitados según business_type.

        Todos los negocios comparten los mismos métodos de pago.
        Feature flags pueden deshabilitar algunos.
        """
        all_methods = [
            {"method": "cash", "label": "Efectivo", "enabled": True},
            {"method": "card", "label": "Tarjeta", "enabled": True},
            {"method": "yape", "label": "Yape", "enabled": True},
            {"method": "plin", "label": "Plin", "enabled": True},
            {"method": "transfer", "label": "Transferencia", "enabled": True},
        ]

        return {"methods": all_methods}