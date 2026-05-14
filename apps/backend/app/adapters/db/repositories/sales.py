"""
SqlAlchemySaleRepository — Implementación DB del puerto SalesRepository.

HU-F1-009: Adaptador concreto para persistencia de ventas usando SQLAlchemy async.

NO refactoriza sales_service.py — Fase 1 solo crea el repositorio.
La migración del servicio al puerto ocurre en Fase 2.
"""

from datetime import date, datetime, UTC
from typing import Optional

from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models.sales import (
    HardwareSale,
    PosSession,
    RestaurantSale as RestaurantSaleModel,
    Sale,
    SaleItem,
    SalePayment,
)
from app.core.sales.ports import (
    SalesRepository,
    PosSessionRecord,
    SaleRecord,
    SaleItemRecord,
    SalePaymentRecord,
    RestaurantSaleRecord,
    HardwareSaleRecord,
)


class SqlAlchemySaleRepository(SalesRepository):
    """Implementación SQLAlchemy del puerto de ventas."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ─── Sesiones POS ──────────────────────────────────────

    async def create_session(self, record: PosSessionRecord) -> PosSessionRecord:
        session = PosSession(
            tenant_id=record.tenant_id,
            user_id=record.user_id,
            opening_cash=record.opening_cash,
            notes=record.notes,
            opened_at=record.opened_at or datetime.now(UTC),
            status="open",
        )
        self.session.add(session)
        await self.session.flush()
        await self.session.refresh(session)
        return _to_pos_session_record(session)

    async def get_current_session(self, tenant_id: int) -> Optional[PosSessionRecord]:
        stmt = select(PosSession).where(
            PosSession.tenant_id == tenant_id,
            PosSession.status == "open",
        )
        result = await self.session.execute(stmt)
        s = result.scalar_one_or_none()
        return _to_pos_session_record(s) if s else None

    async def get_session(
        self, session_id: int, tenant_id: int,
    ) -> Optional[PosSessionRecord]:
        stmt = select(PosSession).where(
            PosSession.id == session_id,
            PosSession.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        s = result.scalar_one_or_none()
        return _to_pos_session_record(s) if s else None

    async def close_session(
        self, session_id: int, tenant_id: int, closing_cash: float,
        expected_cash: float, difference: float, notes: str | None = None,
    ) -> PosSessionRecord:
        stmt = select(PosSession).where(
            PosSession.id == session_id,
            PosSession.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        s = result.scalar_one()
        s.closing_cash = closing_cash
        s.expected_cash = expected_cash
        s.difference = difference
        s.notes = notes
        s.status = "closed"
        s.closed_at = datetime.now(UTC)
        await self.session.flush()
        return _to_pos_session_record(s)

    # ─── Ventas ────────────────────────────────────────────

    async def create_sale(self, record: SaleRecord) -> SaleRecord:
        sale = Sale(
            tenant_id=record.tenant_id,
            session_id=record.session_id,
            user_id=record.user_id,
            sale_number=record.sale_number,
            sale_date=record.sale_date or date.today(),
            sale_time=record.sale_time or datetime.now(UTC).time(),
            customer_name=record.customer_name,
            customer_doc=record.customer_doc,
            subtotal=record.subtotal,
            discount_total=record.discount_total,
            tax_total=record.tax_total,
            tip_amount=record.tip_amount,
            total=record.total,
            business_type=record.business_type,
        )
        self.session.add(sale)
        await self.session.flush()

        # Crear SaleItems
        for item in record.items:
            si = SaleItem(
                sale_id=sale.id,
                product_id=item.product_id,
                item_name=item.item_name,
                item_type=item.item_type,
                quantity=item.quantity,
                unit_of_measure=item.unit_of_measure,
                unit_price=item.unit_price,
                discount_pct=item.discount_pct,
                discount_amount=item.discount_amount,
                tax_pct=item.tax_pct,
                tax_amount=item.tax_amount,
                total=item.total,
                kardex_movement_id=item.kardex_movement_id,
            )
            self.session.add(si)

        # Crear SalePayments
        for payment in record.payments:
            sp = SalePayment(
                sale_id=sale.id,
                payment_method=payment.payment_method,
                amount=payment.amount,
                reference=payment.reference,
            )
            self.session.add(sp)

        await self.session.flush()
        await self.session.refresh(sale)
        return await self.get_sale(sale.id, record.tenant_id) or record

    async def get_sale(self, sale_id: int, tenant_id: int) -> Optional[SaleRecord]:
        stmt = select(Sale).where(
            Sale.id == sale_id,
            Sale.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        s = result.scalar_one_or_none()
        return _to_sale_record(s) if s else None

    async def list_sales(
        self, tenant_id: int,
        page: int = 1, limit: int = 20,
        from_date: date | None = None,
        to_date: date | None = None,
        business_type: str | None = None,
        session_id: int | None = None,
        is_voided: bool | None = None,
    ) -> tuple[list[SaleRecord], int]:
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

        count_stmt = select(func.count(Sale.id)).where(*conditions)
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = (
            select(Sale)
            .where(*conditions)
            .order_by(Sale.sale_date.desc(), Sale.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        sales = result.scalars().all()

        return [_to_sale_record(s) for s in sales], total

    async def void_sale(
        self, sale_id: int, tenant_id: int, reason: str,
    ) -> SaleRecord:
        stmt = select(Sale).where(
            Sale.id == sale_id,
            Sale.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        s = result.scalar_one()
        s.is_voided = True
        s.void_reason = reason
        await self.session.flush()
        return _to_sale_record(s)

    # ─── Especializaciones ─────────────────────────────────

    async def create_restaurant_sale(
        self, record: RestaurantSaleRecord,
    ) -> RestaurantSaleRecord:
        rs = RestaurantSaleModel(
            sale_id=record.sale_id,
            table_number=record.table_number,
            guests=record.guests,
            order_type=record.order_type,
            waiter_name=record.waiter_name,
            tip_amount=record.tip_amount,
            tip_pct=record.tip_pct,
            kitchen_notes=record.kitchen_notes,
        )
        self.session.add(rs)
        await self.session.flush()
        await self.session.refresh(rs)
        return _to_restaurant_sale_record(rs)

    async def create_hardware_sale(
        self, record: HardwareSaleRecord,
    ) -> HardwareSaleRecord:
        hs = HardwareSale(
            sale_id=record.sale_id,
            invoice_type=record.invoice_type,
            delivery_address=record.delivery_address,
            requires_install=record.requires_install,
            warranty_months=record.warranty_months,
        )
        self.session.add(hs)
        await self.session.flush()
        await self.session.refresh(hs)
        return _to_hardware_sale_record(hs)

    async def get_restaurant_sale(
        self, sale_id: int,
    ) -> Optional[RestaurantSaleRecord]:
        stmt = select(RestaurantSaleModel).where(
            RestaurantSaleModel.sale_id == sale_id,
        )
        result = await self.session.execute(stmt)
        rs = result.scalar_one_or_none()
        return _to_restaurant_sale_record(rs) if rs else None

    async def get_hardware_sale(
        self, sale_id: int,
    ) -> Optional[HardwareSaleRecord]:
        stmt = select(HardwareSale).where(
            HardwareSale.sale_id == sale_id,
        )
        result = await self.session.execute(stmt)
        hs = result.scalar_one_or_none()
        return _to_hardware_sale_record(hs) if hs else None


# ═══════════════════════════════════════════════════════════════
# Helpers de conversión ORM → Record
# ═══════════════════════════════════════════════════════════════


def _to_pos_session_record(s: PosSession) -> PosSessionRecord:
    return PosSessionRecord(
        id=s.id,
        tenant_id=s.tenant_id,
        user_id=s.user_id,
        opened_at=s.opened_at,
        closed_at=s.closed_at,
        opening_cash=float(s.opening_cash),
        closing_cash=float(s.closing_cash) if s.closing_cash is not None else None,
        expected_cash=float(s.expected_cash) if s.expected_cash is not None else None,
        difference=float(s.difference) if s.difference is not None else None,
        status=s.status,
        notes=s.notes,
    )


def _to_sale_record(s: Sale) -> SaleRecord:
    return SaleRecord(
        id=s.id,
        tenant_id=s.tenant_id,
        session_id=s.session_id,
        user_id=s.user_id,
        sale_number=s.sale_number,
        sale_date=s.sale_date,
        sale_time=s.sale_time,
        customer_name=s.customer_name,
        customer_doc=s.customer_doc,
        subtotal=float(s.subtotal),
        discount_total=float(s.discount_total),
        tax_total=float(s.tax_total),
        tip_amount=float(s.tip_amount),
        total=float(s.total),
        business_type=s.business_type,
        is_voided=s.is_voided,
        void_reason=s.void_reason,
        journal_entry_id=s.journal_entry_id,
        items=[
            SaleItemRecord(
                id=item.id,
                product_id=item.product_id,
                item_name=item.item_name,
                item_type=item.item_type,
                quantity=float(item.quantity),
                unit_of_measure=item.unit_of_measure,
                unit_price=float(item.unit_price),
                discount_pct=float(item.discount_pct),
                discount_amount=float(item.discount_amount),
                tax_pct=float(item.tax_pct),
                tax_amount=float(item.tax_amount),
                total=float(item.total),
                kardex_movement_id=item.kardex_movement_id,
            )
            for item in (s.items or [])
        ],
        payments=[
            SalePaymentRecord(
                id=p.id,
                payment_method=p.payment_method,
                amount=float(p.amount),
                reference=p.reference,
            )
            for p in (s.payments or [])
        ],
    )


def _to_restaurant_sale_record(rs: RestaurantSaleModel) -> RestaurantSaleRecord:
    return RestaurantSaleRecord(
        id=rs.id,
        sale_id=rs.sale_id,
        table_number=rs.table_number,
        guests=rs.guests,
        order_type=rs.order_type,
        waiter_name=rs.waiter_name,
        tip_amount=float(rs.tip_amount),
        tip_pct=float(rs.tip_pct),
        kitchen_notes=rs.kitchen_notes,
    )


def _to_hardware_sale_record(hs: HardwareSale) -> HardwareSaleRecord:
    return HardwareSaleRecord(
        id=hs.id,
        sale_id=hs.sale_id,
        invoice_type=hs.invoice_type,
        delivery_address=hs.delivery_address,
        requires_install=hs.requires_install,
        warranty_months=hs.warranty_months,
    )


# ═══════════════════════════════════════════════════════════════
# Dependencia FastAPI
# ═══════════════════════════════════════════════════════════════


async def get_sales_repo(db: AsyncSession) -> SqlAlchemySaleRepository:
    """
    FastAPI Depends: inyecta el repositorio de ventas.

    Uso en Fase 2:
        @router.post("/sales/sale")
        async def create_sale(repo: SqlAlchemySaleRepository = Depends(get_sales_repo)):
            ...
    """
    return SqlAlchemySaleRepository(db)
