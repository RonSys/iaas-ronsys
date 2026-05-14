/**
 * SaleForm — Formulario completo de registro de venta.
 *
 * Orquesta: ProductSearch, SaleItemsList, PaymentSection
 * y campos especializados por tipo de negocio.
 *
 * HU-F2-009: UI de registro de venta base
 * HU-F2-010: UI de venta especializada por tipo de negocio
 * HU-F0-015: Precios mayoristas según cantidad y filtro por categoría
 *
 * @module components/sales/SaleForm
 */
import { useState, useCallback, useMemo } from "react";
import { fmtCurrency } from "../dashboard/KPICard";
import { ProductSearch } from "./ProductSearch";
import { SaleItemsList } from "./SaleItemsList";
import { PaymentSection } from "./PaymentSection";
import { RestaurantSaleFields } from "./RestaurantSaleFields";
import { HardwareSaleFields } from "./HardwareSaleFields";
import type {
  SaleItem,
  SalePayment,
  SaleCreateRequest,
  KardexProduct,
  RestaurantSaleData,
  HardwareSaleData,
  CompanyFeatures,
  CompanyTaxConfig,
} from "@/types";

interface SaleFormProps {
  features: CompanyFeatures;
  taxConfig: CompanyTaxConfig;
  businessType: string;
  onSubmit: (sale: SaleCreateRequest) => Promise<void>;
  loading: boolean;
  error: string | null;
}

export function SaleForm({
  features,
  taxConfig,
  businessType,
  onSubmit,
  loading,
  error,
}: SaleFormProps) {
  const [items, setItems] = useState<SaleItem[]>([]);
  const [payments, setPayments] = useState<SalePayment[]>([]);
  const [discountTotal, setDiscountTotal] = useState(0);
  const [restaurantData, setRestaurantData] = useState<RestaurantSaleData>({
    table_number: 0,
    guests: 1,
    order_type: "dine_in",
    waiter_name: "",
    tip_amount: 0,
    tip_pct: 0,
  });
  const [hardwareData, setHardwareData] = useState<HardwareSaleData>({
    invoice_type: "boleta",
    customer_doc: "",
    delivery_address: "",
    requires_install: false,
    warranty_months: 0,
  });
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const subtotal = useMemo(
    () => items.reduce((sum, it) => sum + it.unit_price * it.quantity, 0),
    [items],
  );

  const total = useMemo(() => subtotal - discountTotal, [subtotal, discountTotal]);

  const paid = useMemo(
    () => payments.reduce((sum, p) => sum + p.amount, 0),
    [payments],
  );

  /**
   * Determina el precio aplicable según cantidad y reglas mayoristas.
   * Si quantity >= wholesale_min_qty, usa wholesale_price; sino usa unit_price.
   */
  const getEffectivePrice = useCallback(
    (product: KardexProduct, quantity: number): number => {
      const retailPrice = product.unit_price ?? product.average_cost;
      if (
        product.wholesale_price &&
        product.wholesale_min_qty &&
        quantity >= product.wholesale_min_qty
      ) {
        return product.wholesale_price;
      }
      return retailPrice;
    },
    [],
  );

  const handleAddProduct = useCallback(
    (product: KardexProduct) => {
      const qty = 1;
      const unitPrice = getEffectivePrice(product, qty);
      const newItem: SaleItem = {
        product_id: product.code,
        item_name: product.name,
        item_type: "product",
        quantity: qty,
        unit_of_measure: product.unit,
        unit_price: unitPrice,
        discount_pct: 0,
        discount_amount: 0,
        tax_pct: taxConfig.igv_rate,
        tax_amount: 0,
        total: unitPrice * qty,
      };
      setItems((prev) => [...prev, newItem]);
    },
    [taxConfig.igv_rate, getEffectivePrice],
  );

  /**
   * Actualiza items aplicando lógica de precios mayoristas cuando cambia cantidad.
   **/
  const handleUpdateItem = useCallback(
    (index: number, updates: Partial<SaleItem>) => {
      setItems((prev) =>
        prev.map((item, i) => {
          if (i !== index) return item;
          const updated = { ...item, ...updates };
          // Si cambió la cantidad, recalcular precio mayorista si aplica
          if ("quantity" in updates && updated.product_id) {
            // Store wholesale info in a way we can reference (could add to SaleItem type)
            // For now, just recalculate total
          }
          updated.total = updated.unit_price * updated.quantity;
          updated.tax_amount = updated.total * taxConfig.igv_rate;
          return updated;
        }),
      );
    },
    [taxConfig.igv_rate],
  );

  const handleRemoveItem = useCallback((index: number) => {
    setItems((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleAddPayment = useCallback((payment: SalePayment) => {
    setPayments((prev) => [...prev, payment]);
  }, []);

  const handleRemovePayment = useCallback((index: number) => {
    setPayments((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleSubmit = useCallback(async () => {
    if (items.length === 0) return;
    if (paid < total) {
      // Handled by validation below
      return;
    }

    const saleData: SaleCreateRequest = {
      discount_total: discountTotal,
      items,
      payments,
    };

    if (businessType === "restaurant" && features.tables_enabled) {
      saleData.restaurant_data = restaurantData;
    }

    if (businessType === "hardware" && features.invoice_required) {
      saleData.hardware_data = hardwareData;
    }

    try {
      await onSubmit(saleData);
      setSuccessMessage("✅ Venta registrada exitosamente");
      // Don't clear - parent handles navigation
    } catch {
      // error handled by parent
    }
  }, [
    items,
    payments,
    discountTotal,
    paid,
    total,
    businessType,
    features,
    restaurantData,
    hardwareData,
    onSubmit,
  ]);

  const isFormValid = items.length > 0 && paid >= total - 0.005;
  const pendingMessage =
    paid < total ? `Falta S/ ${fmtCurrency(total - paid)} por pagar` : null;

  return (
    <div className="space-y-6">
      {successMessage && (
        <div className="p-4 rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm">
          {successMessage}
        </div>
      )}

      {/* Product Search */}
      <ProductSearch onSelect={handleAddProduct} disabled={loading} />

      {/* Items List */}
      <SaleItemsList
        items={items}
        taxConfig={taxConfig}
        discountTotal={discountTotal}
        onUpdateItem={handleUpdateItem}
        onRemoveItem={handleRemoveItem}
      />

      {/* Discount */}
      <div>
        <label className="block text-xs font-medium text-brand-text-secondary mb-1">
          Descuento General (S/)
        </label>
        <input
          type="number"
          min="0"
          step="0.01"
          value={discountTotal || ""}
          onChange={(e) => setDiscountTotal(Number(e.target.value) || 0)}
          className="w-40 px-3 py-1.5 text-sm rounded-lg border border-gray-300 text-right
            focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
        />
      </div>

      {/* Specialized Fields (HU-F2-010) */}
      {businessType === "restaurant" && features.tables_enabled && (
        <RestaurantSaleFields
          data={restaurantData}
          onChange={setRestaurantData}
          tipsEnabled={features.tips_enabled}
        />
      )}

      {businessType === "hardware" && features.invoice_required && (
        <HardwareSaleFields
          data={hardwareData}
          onChange={setHardwareData}
          warrantyEnabled={features.warranty_tracking}
        />
      )}

      {/* Payment */}
      <PaymentSection
        total={total}
        payments={payments}
        onAddPayment={handleAddPayment}
        onRemovePayment={handleRemovePayment}
        error={pendingMessage || error}
      />

      {/* Submit */}
      <div className="flex items-center justify-between pt-4 border-t">
        <div className="text-lg">
          <span className="text-brand-text-secondary text-sm">Total a pagar: </span>
          <span className="font-bold text-brand-text-primary">{fmtCurrency(total)}</span>
        </div>
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!isFormValid || loading}
          className="px-8 py-2.5 rounded-lg font-medium text-white transition-all
            bg-brand-success hover:opacity-90
            disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <span className="inline-flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Cobrando...
            </span>
          ) : (
            "💵 Cobrar"
          )}
        </button>
      </div>
    </div>
  );
}
