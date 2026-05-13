"""
💵 Flujo de Caja — Servicio de proyección, real y comparativa.

HU-F1-004: Vista proyectada (12 meses con conceptos)
HU-F1-005: Vista real (basada en journal_entries cuenta 10)
HU-F1-006: Comparativa proyectado vs real + alertas

Basado en:
  - analysis-2026-05-12.md §9.2-9.4
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from app.core.accounting.engine import InvestmentVariables


# ═══════════════════════════════════════════════════════════════
# Modelos de datos
# ═══════════════════════════════════════════════════════════════


@dataclass
class CashflowLine:
    """Una línea del flujo de caja (un concepto en un mes)."""
    month: int
    year: int
    concept: str
    category: str  # income | expense
    projected: float = 0.0
    actual: float = 0.0
    difference: float = 0.0

    @property
    def difference_pct(self) -> float:
        """Diferencia porcentual (actual vs projected)."""
        if self.projected == 0:
            return 0.0
        return round((self.actual - self.projected) / abs(self.projected) * 100, 1)


@dataclass
class CashflowAlert:
    """Alerta financiera por desviación."""
    severity: str  # info | yellow | red
    category: str  # sales | costs | cashflow | liquidity
    message: str
    month: int | None = None


@dataclass
class CashflowReport:
    """Reporte completo de flujo de caja."""
    company_id: int
    from_date: date
    to_date: date
    lines: list[CashflowLine] = field(default_factory=list)
    opening_balance: float = 0.0
    total_income: float = 0.0
    total_expenses: float = 0.0
    net_cashflow: float = 0.0
    closing_balance: float = 0.0
    alerts: list[CashflowAlert] = field(default_factory=list)
    view: str = "projected"  # projected | actual | comparison

    @property
    def is_balanced(self) -> bool:
        return abs(self.closing_balance - (self.opening_balance + self.net_cashflow)) < 0.01


# ═══════════════════════════════════════════════════════════════
# Conceptos de Flujo de Caja
# ═══════════════════════════════════════════════════════════════

INCOME_CONCEPTS = ["Ventas", "Otros Ingresos"]

EXPENSE_CONCEPTS = [
    "Costo de Ventas",
    "Alquiler",
    "Servicios",
    "Salarios",
    "Marketing",
    "Administración",
    "Mantenimiento",
    "Impuestos",
    "Intereses",
    "Depreciación",
]


# ═══════════════════════════════════════════════════════════════
# CashflowService
# ═══════════════════════════════════════════════════════════════


class CashflowService:
    """
    Servicio de flujo de caja.

    Genera proyecciones desde InvestmentVariables,
    calcula datos reales desde journal_entries (cuenta 10),
    y produce comparativas con alertas.
    """

    @staticmethod
    def generate_projection(
        vars_: InvestmentVariables,
        year: int,
        months: int = 12,
    ) -> CashflowReport:
        """
        HU-F1-004: Genera proyección de flujo de caja a 12 meses.

        Args:
            vars_: Variables de inversión del setup contable.
            year: Año de proyección.
            months: Número de meses (default 12).

        Returns:
            CashflowReport con líneas proyectadas por mes y concepto.
        """
        lines: list[CashflowLine] = []

        for m in range(1, months + 1):
            idx = min(m - 1, len(vars_.monthly_sales) - 1) if vars_.monthly_sales else 0
            monthly_sale = vars_.monthly_sales[idx] if vars_.monthly_sales else 0.0
            cost_pct = vars_.monthly_cost_pct

            # Income concepts
            lines.append(CashflowLine(
                month=m, year=year,
                concept="Ventas", category="income",
                projected=round(monthly_sale, 2),
            ))

            # Expense concepts
            lines.append(CashflowLine(
                month=m, year=year,
                concept="Costo de Ventas", category="expense",
                projected=round(monthly_sale * cost_pct, 2),
            ))
            lines.append(CashflowLine(
                month=m, year=year,
                concept="Alquiler", category="expense",
                projected=round(vars_.monthly_rent, 2),
            ))
            lines.append(CashflowLine(
                month=m, year=year,
                concept="Servicios", category="expense",
                projected=round(vars_.monthly_utilities, 2),
            ))
            lines.append(CashflowLine(
                month=m, year=year,
                concept="Salarios", category="expense",
                projected=round(vars_.monthly_salaries, 2),
            ))
            lines.append(CashflowLine(
                month=m, year=year,
                concept="Marketing", category="expense",
                projected=round(vars_.monthly_marketing, 2),
            ))
            lines.append(CashflowLine(
                month=m, year=year,
                concept="Administración", category="expense",
                projected=round(vars_.monthly_admin, 2),
            ))
            lines.append(CashflowLine(
                month=m, year=year,
                concept="Mantenimiento", category="expense",
                projected=round(vars_.monthly_maintenance, 2),
            ))

        # Totales
        total_income = sum(l.projected for l in lines if l.category == "income")
        total_expenses = sum(l.projected for l in lines if l.category == "expense")
        net_cf = round(total_income - total_expenses, 2)

        report = CashflowReport(
            company_id=0,
            from_date=date(year, 1, 1),
            to_date=date(year, months, 28),
            lines=lines,
            opening_balance=0.0,
            total_income=total_income,
            total_expenses=total_expenses,
            net_cashflow=net_cf,
            closing_balance=round(0.0 + net_cf, 2),
            view="projected",
        )
        return report

    @staticmethod
    def calculate_real(
        journal_entries: list,  # JournalEntry domain objects
        company_id: int,
        from_date: date,
        to_date: date,
    ) -> CashflowReport:
        """
        HU-F1-005: Calcula flujo de caja real desde journal_entries.

        Lee asientos con movimientos en cuenta 10 (Efectivo) y categoriza
        ingresos y egresos reales del período.

        Args:
            journal_entries: Lista de JournalEntry (dominio).
            company_id: ID de la empresa.
            from_date: Fecha inicio del período.
            to_date: Fecha fin del período.

        Returns:
            CashflowReport con líneas con actual poblado.
        """
        # Inicializar líneas por mes
        lines: dict[tuple[int, int, str], CashflowLine] = {}

        for m in range(from_date.month, to_date.month + 1):
            year = from_date.year if m >= from_date.month else from_date.year + 1
            for concept in INCOME_CONCEPTS + EXPENSE_CONCEPTS:
                cat = "income" if concept in INCOME_CONCEPTS else "expense"
                key = (year, m, concept)
                lines[key] = CashflowLine(
                    month=m, year=year, concept=concept, category=cat
                )

        # Acumular montos reales desde journal entries
        for entry in journal_entries:
            entry_date = entry.date_
            if not isinstance(entry_date, date):
                continue
            if entry_date < from_date or entry_date > to_date:
                continue

            for line in entry.lines:
                # Cuenta 10 = Efectivo
                if line.account_code == "10":
                    month = entry_date.month
                    year = entry_date.year

                    if line.debit > 0:
                        # Ingreso de efectivo → Ventas
                        key = (year, month, "Ventas")
                        if key in lines:
                            lines[key].actual += line.debit
                    if line.credit > 0:
                        # Egreso de efectivo → clasificar por descripción
                        # Preferir entry.description si line es genérica
                        line_desc = (line.description or "").lower()
                        entry_desc = (entry.description or "").lower()
                        generic_words = ("efectivo", "caja", "banco", "pago")
                        if any(line_desc.startswith(w) or line_desc == w for w in generic_words) and entry_desc:
                            desc = entry_desc
                        else:
                            desc = line_desc or entry_desc
                        concept = CashflowService._classify_expense(desc)
                        key = (year, month, concept)
                        if key in lines:
                            lines[key].actual += line.credit
                        elif concept not in EXPENSE_CONCEPTS and concept not in INCOME_CONCEPTS:
                            # Catch-all
                            key2 = (year, month, "Costo de Ventas")
                            if key2 in lines:
                                lines[key2].actual += line.credit

        # Calcular opening_balance desde saldo cuenta 10 al cierre del período anterior
        opening = 0.0
        for entry in journal_entries:
            if entry.date_ and entry.date_ < from_date:
                for line in entry.lines:
                    if line.account_code == "10":
                        opening += line.debit - line.credit

        sorted_lines = sorted(lines.values(), key=lambda l: (l.year, l.month, l.category, l.concept))

        total_inc = sum(l.actual for l in sorted_lines if l.category == "income")
        total_exp = sum(l.actual for l in sorted_lines if l.category == "expense")
        net_cf = round(total_inc - total_exp, 2)

        return CashflowReport(
            company_id=company_id,
            from_date=from_date,
            to_date=to_date,
            lines=sorted_lines,
            opening_balance=round(opening, 2),
            total_income=round(total_inc, 2),
            total_expenses=round(total_exp, 2),
            net_cashflow=round(net_cf, 2),
            closing_balance=round(opening + net_cf, 2),
            view="actual",
        )

    @staticmethod
    def compare(
        projected: CashflowReport,
        actual: CashflowReport,
    ) -> CashflowReport:
        """
        HU-F1-006: Comparativa proyectado vs real con alertas.

        Umbrales:
          - ±5%:  info
          - ±20%: yellow
          - ±30%+: red

        Args:
            projected: Reporte proyectado.
            actual: Reporte real.

        Returns:
            CashflowReport con líneas comparativas y alertas.
        """
        # Indexar líneas
        proj_map: dict[tuple[int, int, str], CashflowLine] = {}
        for l in projected.lines:
            proj_map[(l.year, l.month, l.concept)] = l

        actual_map: dict[tuple[int, int, str], CashflowLine] = {}
        for l in actual.lines:
            actual_map[(l.year, l.month, l.concept)] = l

        # Construir líneas comparativas
        all_keys = set(proj_map.keys()) | set(actual_map.keys())
        cmp_lines: list[CashflowLine] = []

        for key in sorted(all_keys):
            p = proj_map.get(key)
            a = actual_map.get(key)
            year, month, concept = key
            cat = (p or a).category

            projected_val = p.projected if p else 0.0
            actual_val = a.actual if a else 0.0
            diff = round(actual_val - projected_val, 2)

            cmp_lines.append(CashflowLine(
                month=month, year=year,
                concept=concept, category=cat,
                projected=projected_val,
                actual=actual_val,
                difference=diff,
            ))

        # Generar alertas
        alerts: list[CashflowAlert] = []
        for line in cmp_lines:
            pct = line.difference_pct
            abs_pct = abs(pct)

            if abs_pct < 5:
                continue

            severity = "red" if abs_pct >= 30 else ("yellow" if abs_pct >= 20 else "info")

            if line.category == "income" and line.actual < line.projected:
                alerts.append(CashflowAlert(
                    severity=severity,
                    category="sales",
                    message=(
                        f"Ventas reales {line.actual:.2f} están {abs_pct:.0f}% "
                        f"bajo lo proyectado {line.projected:.2f} "
                        f"en mes {line.month}/{line.year}"
                    ),
                    month=line.month,
                ))

            if line.category == "expense" and line.actual > line.projected:
                alerts.append(CashflowAlert(
                    severity=severity,
                    category="costs",
                    message=(
                        f"{line.concept} real {line.actual:.2f} excede "
                        f"proyección {line.projected:.2f} en {abs_pct:.0f}% "
                        f"(mes {line.month}/{line.year})"
                    ),
                    month=line.month,
                ))

        # Alertas de deterioro de liquidez
        if actual.net_cashflow < 0 and projected.net_cashflow > 0:
            alerts.append(CashflowAlert(
                severity="red",
                category="liquidity",
                message=(
                    f"Deterioro de liquidez: flujo neto real ({actual.net_cashflow:.2f}) "
                    f"es negativo mientras el proyectado era positivo "
                    f"({projected.net_cashflow:.2f})"
                ),
            ))

        # Alertas de cashflow negativo vs positivo
        for key in proj_map:
            p_line = proj_map.get(key)
            month_lines = [l for l in cmp_lines if l.month == key[1] and l.year == key[0]]
            actual_month_net = sum(l.actual for l in month_lines if l.category == "income") - \
                sum(l.actual for l in month_lines if l.category == "expense")
            proj_month_net = sum(l.projected for l in month_lines if l.category == "income") - \
                sum(l.projected for l in month_lines if l.category == "expense")

            if actual_month_net < 0 and proj_month_net > 0:
                # Solo si no existe ya una alerta de liquidez para ese mes
                if not any(a.month == key[1] and a.category == "cashflow" for a in alerts):
                    alerts.append(CashflowAlert(
                        severity="red",
                        category="cashflow",
                        message=(
                            f"Cashflow real negativo ({actual_month_net:.2f}) vs "
                            f"positivo proyectado ({proj_month_net:.2f}) "
                            f"en mes {key[1]}/{key[0]}"
                        ),
                        month=key[1],
                    ))

        total_inc = sum(l.actual for l in cmp_lines if l.category == "income")
        total_exp = sum(l.actual for l in cmp_lines if l.category == "expense")
        net_cf = round(total_inc - total_exp, 2)

        return CashflowReport(
            company_id=projected.company_id,
            from_date=projected.from_date,
            to_date=projected.to_date,
            lines=cmp_lines,
            opening_balance=actual.opening_balance,
            total_income=round(total_inc, 2),
            total_expenses=round(total_exp, 2),
            net_cashflow=net_cf,
            closing_balance=round(actual.opening_balance + net_cf, 2),
            alerts=alerts,
            view="comparison",
        )

    @staticmethod
    def _classify_expense(description: str) -> str:
        """Clasifica un egreso por su descripción."""
        d = description.lower()
        if any(w in d for w in ("alquiler", "renta", "arriendo")):
            return "Alquiler"
        if any(w in d for w in ("luz", "agua", "internet", "teléfono", "servicio")):
            return "Servicios"
        if any(w in d for w in ("salario", "sueldo", "planilla", "nómina")):
            return "Salarios"
        if any(w in d for w in ("marketing", "publicidad", "anuncio")):
            return "Marketing"
        if any(w in d for w in ("administra", "oficina", "papelería")):
            return "Administración"
        if any(w in d for w in ("mantenimiento", "reparación", "reparacion")):
            return "Mantenimiento"
        if any(w in d for w in ("impuesto", "igv", "tributo", "sunat")):
            return "Impuestos"
        if any(w in d for w in ("interés", "interes", "préstamo", "prestamo")):
            return "Intereses"
        if any(w in d for w in ("depreciación", "depreciacion")):
            return "Depreciación"
        if any(w in d for w in ("costo", "compra", "inventario")):
            return "Costo de Ventas"
        return "Costo de Ventas"  # fallback

    # ─── Persistencia (HU-F1-008) ─────────────────────────────

    @staticmethod
    async def save_projection(
        db,  # AsyncSession
        company_id: int,
        report: CashflowReport,
    ) -> int:
        """
        HU-F1-008: Persiste proyección de flujo de caja en DB con UPSERT.

        Args:
            db: AsyncSession de SQLAlchemy.
            company_id: ID de la empresa.
            report: CashflowReport proyectado.

        Returns:
            Número de líneas persistidas.
        """
        from app.adapters.db.models.accounting import CashflowProjection
        from sqlalchemy import select
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        saved = 0
        for line in report.lines:
            stmt = pg_insert(CashflowProjection).values(
                company_id=company_id,
                year=line.year,
                month=line.month,
                concept=line.concept,
                category=line.category,
                amount=line.projected,
            ).on_conflict_do_update(
                constraint="uq_cashflow_projection",
                set_=dict(amount=line.projected),
            )
            await db.execute(stmt)
            saved += 1

        await db.flush()
        return saved

    @staticmethod
    async def load_projection(
        db,  # AsyncSession
        company_id: int,
        year: int,
    ) -> list[CashflowLine]:
        """
        Carga proyección persistida desde DB.

        Args:
            db: AsyncSession.
            company_id: ID de empresa.
            year: Año.

        Returns:
            Lista de CashflowLine cargadas.
        """
        from app.adapters.db.models.accounting import CashflowProjection
        from sqlalchemy import select

        result = await db.execute(
            select(CashflowProjection)
            .where(
                CashflowProjection.company_id == company_id,
                CashflowProjection.year == year,
            )
            .order_by(CashflowProjection.month, CashflowProjection.concept)
        )
        rows = result.scalars().all()

        return [
            CashflowLine(
                month=r.month, year=r.year,
                concept=r.concept, category=r.category,
                projected=float(r.amount),
            )
            for r in rows
        ]