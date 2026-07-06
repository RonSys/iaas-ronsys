/**
 * SaleForm — Formulario completo de registro de venta.
 *
 * Orquesta: ProductSearch, SaleItemsList, PaymentSection
 * y campos especializados por tipo de negocio.
 *
 * HU-F2-009: UI de registro de venta base
 * HU-F2-010: UI de venta especializada por tipo de negocio
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
import { SerialSelectorModal } from "./SerialSelectorModal";
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

  // Serial selection state (DT-F0-009)
  const [serialModalOpen, setSerialModalOpen] = useState(false);
  const [serialModalProductId, setSerialModalProductId] = useState<number>(0);
  const [serialModalProductName, setSerialModalProductName] = useState("");
  const [serialModalQuantity, setSerialModalQuantity] = useState(1);
  const [pendingProduct, setPendingProduct] = useState<KardexProduct | null>(null);

  // Track all serials already selected in current ticket
  const alreadySelectedSerials = useMemo(
    () => items.flatMap((item) => item.serials ?? []),
    [items],
  );

  const subtotal = useMemo(
    () => items.reduce((sum, it) => sum + it.unit_price * it.quantity, 0),
    [items],
  );

  const total = useMemo(() => {
    const neto = subtotal - discountTotal;
    if (taxConfig.igv_included_in_price) return neto;
    return neto * (1 + taxConfig.igv_rate / 100);
  }, [subtotal, discountTotal, taxConfig.igv_rate, taxConfig.igv_included_in_price]);

  const paid = useMemo(
    () => payments.reduce((sum, p) => sum + p.amount, 0),
    [payments],
  );

  const handleAddProduct = useCallback(
    (product: KardexProduct) => {
      // If product has serials, open serial selector modal
      if (product.has_serial && product.id) {
        setPendingProduct(product);
        setSerialModalProductId(product.id);
        setSerialModalProductName(product.name);
        setSerialModalQuantity(1);
        setSerialModalOpen(true);
        return;
      }

      // Determine price — check wholesale threshold
      const retailPrice = product.unit_price ?? product.average_cost;
      let unitPrice = retailPrice;
      if (product.wholesale_price && product.wholesale_min_qty && 1 >= product.wholesale_min_qty) {
        unitPrice = product.wholesale_price;
      }

      const newItem: SaleItem = {
        product_id: String(product.id ?? product.code),
        product_numeric_id: product.id,
        item_name: product.name,
        item_type: "product",
        quantity: 1,
        unit_of_measure: product.unit,
        unit_price: unitPrice,
        retail_price: retailPrice,
        wholesale_price: product.wholesale_price,
        wholesale_min_qty: product.wholesale_min_qty,
        discount_pct: 0,
        discount_amount: 0,
        tax_pct: taxConfig.igv_rate,
        tax_amount: 0,
        total: unitPrice,
      };
      setItems((prev) => [...prev, newItem]);
    },
    [taxConfig.igv_rate],
  );

  /** Called when serials are confirmed in the SerialSelectorModal */
  const handleSerialConfirm = useCallback(
    (serials: string[]) => {
      if (!pendingProduct) return;
      const retailPrice = pendingProduct.unit_price ?? pendingProduct.average_cost;
      let unitPrice = retailPrice;
      if (pendingProduct.wholesale_price && pendingProduct.wholesale_min_qty && serials.length >= pendingProduct.wholesale_min_qty) {
        unitPrice = pendingProduct.wholesale_price;
      }

      const newItem: SaleItem = {
        product_id: String(pendingProduct.id ?? pendingProduct.code),
        product_numeric_id: pendingProduct.id,
        item_name: pendingProduct.name,
        item_type: "product",
        quantity: serials.length,
        unit_of_measure: pendingProduct.unit,
        unit_price: unitPrice,
        retail_price: retailPrice,
        wholesale_price: pendingProduct.wholesale_price,
        wholesale_min_qty: pendingProduct.wholesale_min_qty,
        discount_pct: 0,
        discount_amount: 0,
        tax_pct: taxConfig.igv_rate,
        tax_amount: 0,
        total: unitPrice * serials.length,
        serials,
      };
      setItems((prev) => [...prev, newItem]);
      setSerialModalOpen(false);
      setPendingProduct(null);
    },
    [pendingProduct, taxConfig.igv_rate],
  );

  /** Cancel serial selection */
  const handleSerialCancel = useCallback(() => {
    setSerialModalOpen(false);
    setPendingProduct(null);
  }, []);

  const handleUpdateItem = useCallback(
    (index: number, updates: Partial<SaleItem>) => {
      setItems((prev) =>
        prev.map((item, i) => {
          if (i !== index) return item;
          const updated = { ...item, ...updates };
          // Recalculate unit_price based on wholesale threshold when quantity changes
          if (updates.quantity !== undefined) {
            const newQty = updates.quantity;
            if (item.wholesale_price && item.wholesale_min_qty && newQty >= item.wholesale_min_qty) {
              updated.unit_price = item.wholesale_price;
            } else {
              updated.unit_price = item.retail_price ?? item.unit_price;
            }
          }
          updated.total = updated.unit_price * (updates.quantity ?? item.quantity);
          updated.tax_amount = updated.total * (taxConfig.igv_rate / 100);
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

      {/* Serial Selector Modal (DT-F0-009) */}
      <SerialSelectorModal
        isOpen={serialModalOpen}
        productId={serialModalProductId}
        productName={serialModalProductName}
        quantity={serialModalQuantity}
        alreadySelectedSerials={alreadySelectedSerials}
        onConfirm={handleSerialConfirm}
        onCancel={handleSerialCancel}
      />
    </div>
  );
}
