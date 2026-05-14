/**
 * PosPage — Página de gestión de caja (POS Session + Quick Sale).
 *
 * Muestra:
 * - Si no hay sesión: PosSessionOpen
 * - Si hay sesión: PosSessionStatus + búsqueda de producto + quick sale
 * - Botón cerrar → PosSessionClose modal
 *
 * HU-F2-008: UI de apertura y cierre de caja
 * HU-F0-016: Búsqueda de producto en venta mostrador
 *
 * @module pages/Pos
 */
import { useState, useCallback, useMemo } from "react";
import { usePosSession } from "@/hooks/usePosSession";
import { useCompanySettings } from "@/hooks/useCompanySettings";
import { PosSessionOpen } from "@/components/pos/PosSessionOpen";
import { PosSessionStatus } from "@/components/pos/PosSessionStatus";
import { PosSessionClose } from "@/components/pos/PosSessionClose";
import { ProductSearch } from "@/components/sales/ProductSearch";
import { Skeleton, fmtCurrency } from "@/components/dashboard/KPICard";
import type { KardexProduct } from "@/types";

interface QuickSaleItem {
  product: KardexProduct;
  quantity: number;
}

export function PosPage() {
  const {
    session,
    isOpen,
    loading,
    actionLoading,
    error,
    open,
    close,
  } = usePosSession();
  const { taxConfig } = useCompanySettings();

  const [showCloseModal, setShowCloseModal] = useState(false);
  const [quickSaleItems, setQuickSaleItems] = useState<QuickSaleItem[]>([]);
  const [quickSaleMessage, setQuickSaleMessage] = useState<string | null>(null);
  const [quickSaleSubmitting, setQuickSaleSubmitting] = useState(false);

  const quickSaleTotal = useMemo(
    () =>
      quickSaleItems.reduce(
        (sum, item) => sum + (item.product.unit_price ?? item.product.average_cost) * item.quantity,
        0,
      ),
    [quickSaleItems],
  );

  const handleAddProduct = useCallback((product: KardexProduct) => {
    setQuickSaleItems((prev) => {
      const existing = prev.find((it) => it.product.code === product.code);
      if (existing) {
        return prev.map((it) =>
          it.product.code === product.code
            ? { ...it, quantity: it.quantity + 1 }
            : it,
        );
      }
      return [...prev, { product, quantity: 1 }];
    });
  }, []);

  const handleUpdateQuantity = useCallback((index: number, qty: number) => {
    setQuickSaleItems((prev) =>
      prev.map((it, i) => (i === index ? { ...it, quantity: Math.max(1, qty) } : it)),
    );
  }, []);

  const handleRemoveItem = useCallback((index: number) => {
    setQuickSaleItems((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleQuickSale = useCallback(async () => {
    if (quickSaleItems.length === 0) return;
    setQuickSaleSubmitting(true);
    setQuickSaleMessage(null);
    try {
      const items = quickSaleItems.map((item) => {
        const unitPrice = item.product.unit_price ?? item.product.average_cost;
        return {
          product_id: item.product.code,
          item_name: item.product.name,
          item_type: "product" as const,
          quantity: item.quantity,
          unit_of_measure: item.product.unit,
          unit_price: unitPrice,
          discount_pct: 0,
          discount_amount: 0,
          tax_pct: taxConfig.igv_rate,
          tax_amount: 0,
          total: unitPrice * item.quantity,
        };
      });
      const saleData = {
        discount_total: 0,
        items,
        payments: [
          {
            payment_method: "cash" as const,
            amount: quickSaleTotal,
            reference: null,
          },
        ],
      };
      const res = await fetch("/api/sales/sale", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(saleData),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Error al registrar venta");
      }
      setQuickSaleItems([]);
      setQuickSaleMessage(`✅ Venta registrada — Total: ${fmtCurrency(quickSaleTotal)}`);
      setTimeout(() => setQuickSaleMessage(null), 4000);
    } catch (err: unknown) {
      setQuickSaleMessage(
        `❌ ${err instanceof Error ? err.message : "Error al registrar"}`,
      );
    } finally {
      setQuickSaleSubmitting(false);
    }
  }, [quickSaleItems, quickSaleTotal, taxConfig.igv_rate]);

  const handleOpen = useCallback(
    async (openingCash: number) => {
      await open({ opening_cash: openingCash });
    },
    [open],
  );

  const handleClose = useCallback(
    async (closingCash: number, notes: string) => {
      const result = await close({ closing_cash: closingCash, notes });
      return result;
    },
    [close],
  );

  const handleCloseRequest = () => {
    setShowCloseModal(true);
  };

  const handleCloseCancel = () => {
    setShowCloseModal(false);
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full max-w-md" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-brand-text-primary">
            💰 Caja
          </h2>
          <p className="text-sm text-brand-text-secondary">
            {isOpen ? "Sesión de caja activa" : "Abrí una nueva sesión de caja"}
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
          {error}
        </div>
      )}

      {isOpen && session ? (
        <div className="space-y-6">
          <PosSessionStatus
            session={session}
            onCloseRequest={handleCloseRequest}
          />

          {/* ─── Quick Sale / Venta Mostrador (F0-016) ─── */}
          <div className="card">
            <h3 className="font-bold text-brand-text-primary mb-4">
              🛒 Venta Rápida Mostrador
            </h3>

            <ProductSearch onSelect={handleAddProduct} disabled={quickSaleSubmitting} />

            {/* Items list */}
            {quickSaleItems.length > 0 && (
              <div className="mt-4 space-y-2">
                {quickSaleItems.map((item, idx) => {
                  const unitPrice =
                    item.product.unit_price ?? item.product.average_cost;
                  return (
                    <div
                      key={item.product.code}
                      className="flex items-center gap-3 py-2 border-b border-gray-100"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-brand-text-primary truncate">
                          {item.product.name}
                        </div>
                        <div className="text-xs text-brand-text-secondary">
                          {fmtCurrency(unitPrice)} / {item.product.unit}
                          {item.product.barcode && (
                            <span className="ml-2 text-[10px] font-mono">
                              [{item.product.barcode}]
                            </span>
                          )}
                        </div>
                      </div>
                      <input
                        type="number"
                        min={1}
                        value={item.quantity}
                        onChange={(e) =>
                          handleUpdateQuantity(idx, Number(e.target.value) || 1)
                        }
                        className="w-16 px-2 py-1 border rounded text-center text-sm"
                      />
                      <span className="text-sm font-semibold w-20 text-right">
                        {fmtCurrency(unitPrice * item.quantity)}
                      </span>
                      <button
                        onClick={() => handleRemoveItem(idx)}
                        className="text-xs text-red-500 hover:underline"
                      >
                        ✕
                      </button>
                    </div>
                  );
                })}

                {/* Total + Quick pay */}
                <div className="flex items-center justify-between pt-3 mt-2">
                  <div className="text-lg">
                    <span className="text-sm text-brand-text-secondary">Total: </span>
                    <span className="font-bold text-brand-text-primary">
                      {fmtCurrency(quickSaleTotal)}
                    </span>
                  </div>
                  <button
                    onClick={handleQuickSale}
                    disabled={quickSaleSubmitting || quickSaleItems.length === 0}
                    className="px-6 py-2 bg-brand-success text-white rounded-lg text-sm
                      hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {quickSaleSubmitting ? (
                      <span className="inline-flex items-center gap-2">
                        <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Cobrando...
                      </span>
                    ) : (
                      "💵 Cobrar (Efectivo)"
                    )}
                  </button>
                </div>
              </div>
            )}

            {quickSaleMessage && (
              <div
                className={`mt-3 p-3 rounded-lg text-sm ${
                  quickSaleMessage.startsWith("✅")
                    ? "bg-green-50 border border-green-200 text-green-700"
                    : "bg-red-50 border border-red-200 text-red-600"
                }`}
              >
                {quickSaleMessage}
              </div>
            )}
          </div>
        </div>
      ) : (
        <PosSessionOpen
          onSubmit={handleOpen}
          loading={actionLoading}
          error={error}
        />
      )}

      {/* Close Modal */}
      {showCloseModal && session && (
        <PosSessionClose
          expectedCash={(session.cash_sales ?? 0) + session.opening_cash}
          totalSales={session.total_sales ?? 0}
          onSubmit={handleClose}
          loading={actionLoading}
          error={error}
          onCancel={handleCloseCancel}
        />
      )}
    </div>
  );
}
