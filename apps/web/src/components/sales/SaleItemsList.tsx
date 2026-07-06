/**
 * SaleItemsList — Lista de ítems con subtotales, IGV y descuento.
 *
 * HU-F2-009: UI de registro de venta base
 *
 * @module components/sales/SaleItemsList
 */
import { useMemo } from "react";
import { fmtCurrency } from "../dashboard/KPICard";
import type { SaleItem, CompanyTaxConfig } from "@/types";

interface SaleItemsListProps {
  items: SaleItem[];
  taxConfig: CompanyTaxConfig;
  discountTotal: number;
  onUpdateItem: (index: number, updates: Partial<SaleItem>) => void;
  onRemoveItem: (index: number) => void;
}

export function SaleItemsList({
  items,
  taxConfig,
  discountTotal,
  onUpdateItem,
  onRemoveItem,
}: SaleItemsListProps) {
  const subtotal = useMemo(
    () => items.reduce((sum, it) => sum + it.unit_price * it.quantity, 0),
    [items],
  );

  const rate = taxConfig.igv_rate / 100;

  /** Per-item savings including IGV: (retail - wholesale) × qty × (1 + rate) */
  const itemSavings = useMemo(
    () =>
      items.map((it) => {
        if (
          it.wholesale_price != null &&
          it.wholesale_min_qty != null &&
          it.quantity >= it.wholesale_min_qty &&
          it.retail_price != null &&
          it.retail_price > it.wholesale_price
        ) {
          return (
            (it.retail_price - it.wholesale_price) *
            it.quantity *
            (1 + rate)
          );
        }
        return 0;
      }),
    [items, rate],
  );

  const wholesaleDiscount = useMemo(
    () => itemSavings.reduce((sum, s) => sum + s, 0),
    [itemSavings],
  );

  const taxAmount = useMemo(() => {
    if (taxConfig.igv_included_in_price) {
      return subtotal - subtotal / (1 + rate);
    }
    return subtotal * rate;
  }, [subtotal, taxConfig, rate]);

  const total = taxConfig.igv_included_in_price
    ? subtotal - discountTotal
    : subtotal + taxAmount - discountTotal;

  if (items.length === 0) {
    return (
      <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 text-center text-sm text-brand-text-secondary">
        Agregá productos usando el buscador
      </div>
    );
  }

  return (
    <div>
      <h4 className="text-sm font-semibold text-brand-text-primary mb-2">
        Ítems ({items.length})
      </h4>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-xs text-brand-text-secondary uppercase tracking-wider">
              <th className="py-2 text-left">Producto</th>
              <th className="py-2 text-right">Precio</th>
              <th className="py-2 text-right">Ahorro</th>
              <th className="py-2 text-right">Cant.</th>
              <th className="py-2 text-right">Total</th>
              <th className="py-2 w-8"></th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, i) => (
              <tr key={i} className="border-b border-gray-50">
                <td className="py-2">
                  <span className="font-medium text-brand-text-primary">
                    {item.item_name}
                  </span>
                </td>
                <td className="py-2 text-right text-brand-text-secondary">
                  {fmtCurrency(item.unit_price)}
                </td>
                <td className="py-2 text-right">
                  {itemSavings[i] > 0 ? (
                    <span
                      className="text-brand-success font-medium"
                      title={`Ahorro S/${((item.retail_price ?? 0) - (item.wholesale_price ?? 0)) * item.quantity} + IGV S/${(itemSavings[i] - ((item.retail_price ?? 0) - (item.wholesale_price ?? 0)) * item.quantity).toFixed(2)}`}
                    >
                      {fmtCurrency(itemSavings[i])}
                    </span>
                  ) : (
                    <span className="text-brand-text-secondary">—</span>
                  )}
                </td>
                <td className="py-2 text-right">
                  <input
                    type="number"
                    min="1"
                    value={item.quantity}
                    onChange={(e) =>
                      onUpdateItem(i, { quantity: Number(e.target.value) || 1 })
                    }
                    className="w-16 text-center px-1 py-0.5 rounded border border-gray-200 text-sm
                      focus:outline-none focus:ring-1 focus:ring-brand-primary/20"
                  />
                </td>
                <td className="py-2 text-right font-medium">
                  {fmtCurrency(item.unit_price * item.quantity)}
                </td>
                <td className="py-2">
                  <button
                    type="button"
                    onClick={() => onRemoveItem(i)}
                    className="text-red-400 hover:text-red-600 text-lg leading-none"
                    title="Eliminar ítem"
                  >
                    ×
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Totals */}
      <div className="border-t mt-2 pt-2 space-y-1 text-sm">
        {wholesaleDiscount > 0 && (
          <div className="flex justify-between text-brand-warning">
            <span>Dto. Mayorista</span>
            <span>-{fmtCurrency(wholesaleDiscount)}</span>
          </div>
        )}
        <div className="flex justify-between">
          <span className="text-brand-text-secondary">Subtotal</span>
          <span>{fmtCurrency(subtotal)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-brand-text-secondary">
            IGV ({Math.round(taxConfig.igv_rate)}%)
            {taxConfig.igv_included_in_price ? " (incl.)" : ""}
          </span>
          <span>{fmtCurrency(taxAmount)}</span>
        </div>
        {discountTotal > 0 && (
          <div className="flex justify-between text-brand-error">
            <span>Descuento</span>
            <span>-{fmtCurrency(discountTotal)}</span>
          </div>
        )}
        <div className="flex justify-between font-bold text-lg pt-1 border-t">
          <span>Total</span>
          <span>{fmtCurrency(total)}</span>
        </div>
      </div>
    </div>
  );
}
