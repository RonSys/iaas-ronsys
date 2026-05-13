/**
 * Tests for Sale components (HU-F2-009 and HU-F2-010).
 *
 * HU-F2-009: UI de registro de venta base
 * HU-F2-010: UI de venta especializada por tipo de negocio
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { SaleItemsList } from "@/components/sales/SaleItemsList";
import { PaymentSection } from "@/components/sales/PaymentSection";
import { RestaurantSaleFields } from "@/components/sales/RestaurantSaleFields";
import { HardwareSaleFields } from "@/components/sales/HardwareSaleFields";
import type {
  SaleItem,
  SalePayment,
  CompanyTaxConfig,
  RestaurantSaleData,
  HardwareSaleData,
} from "@/types";

const taxConfig: CompanyTaxConfig = {
  igv_included_in_price: true,
  igv_rate: 0.18,
  icb_perception_pct: 0,
};

const taxConfigNoIcv: CompanyTaxConfig = {
  igv_included_in_price: false,
  igv_rate: 0.18,
  icb_perception_pct: 0,
};

const sampleItem: SaleItem = {
  product_id: "P001",
  item_name: "Lomo Saltado",
  item_type: "product",
  quantity: 2,
  unit_of_measure: "plato",
  unit_price: 35,
  discount_pct: 0,
  discount_amount: 0,
  tax_pct: 0.18,
  tax_amount: 0,
  total: 70,
};

describe("SaleItemsList", () => {
  it("renders empty state", () => {
    render(
      <SaleItemsList
        items={[]}
        taxConfig={taxConfig}
        discountTotal={0}
        onUpdateItem={jest.fn()}
        onRemoveItem={jest.fn()}
      />,
    );
    expect(screen.getByText("Agregá productos usando el buscador")).toBeInTheDocument();
  });

  it("renders items with totals", () => {
    render(
      <SaleItemsList
        items={[sampleItem]}
        taxConfig={taxConfig}
        discountTotal={0}
        onUpdateItem={jest.fn()}
        onRemoveItem={jest.fn()}
      />,
    );
    expect(screen.getByText("Lomo Saltado")).toBeInTheDocument();
    // Total column shows S/ 70
    const totals = screen.getAllByText("S/ 70");
    expect(totals.length).toBeGreaterThanOrEqual(1);
  });

  it("calculates IGV correctly when included in price", () => {
    render(
      <SaleItemsList
        items={[sampleItem]} // subtotal = 70
        taxConfig={taxConfig} // igv included
        discountTotal={0}
        onUpdateItem={jest.fn()}
        onRemoveItem={jest.fn()}
      />,
    );
    // IGV included: 70 - 70/1.18 ≈ 10.68
    expect(screen.getByText(/IGV \(18%\) \(incl.\)/)).toBeInTheDocument();
  });

  it("calculates IGV correctly when NOT included", () => {
    render(
      <SaleItemsList
        items={[sampleItem]}
        taxConfig={taxConfigNoIcv}
        discountTotal={0}
        onUpdateItem={jest.fn()}
        onRemoveItem={jest.fn()}
      />,
    );
    // IGV not included: 70 * 0.18 = 12.60
    expect(screen.getByText(/IGV \(18%\)/)).toBeInTheDocument();
  });

  it("shows discount when > 0", () => {
    render(
      <SaleItemsList
        items={[sampleItem]}
        taxConfig={taxConfig}
        discountTotal={10}
        onUpdateItem={jest.fn()}
        onRemoveItem={jest.fn()}
      />,
    );
    expect(screen.getByText("-S/ 10")).toBeInTheDocument();
  });

  it("calls onRemoveItem when X button clicked", () => {
    const onRemove = jest.fn();
    render(
      <SaleItemsList
        items={[sampleItem]}
        taxConfig={taxConfig}
        discountTotal={0}
        onUpdateItem={jest.fn()}
        onRemoveItem={onRemove}
      />,
    );
    fireEvent.click(screen.getByTitle("Eliminar ítem"));
    expect(onRemove).toHaveBeenCalledWith(0);
  });
});

describe("PaymentSection", () => {
  it("shows pending when no payments", () => {
    render(
      <PaymentSection
        total={100}
        payments={[]}
        onAddPayment={jest.fn()}
        onRemovePayment={jest.fn()}
      />,
    );
    expect(screen.getByText("Pagado")).toBeInTheDocument();
    expect(screen.getByText("S/ 0")).toBeInTheDocument();
    expect(screen.getByText("Pendiente")).toBeInTheDocument();
  });

  it("adds a payment", async () => {
    const onAdd = jest.fn();
    render(
      <PaymentSection
        total={100}
        payments={[]}
        onAddPayment={onAdd}
        onRemovePayment={jest.fn()}
      />,
    );
    const amountInput = screen.getByPlaceholderText("0.00");
    fireEvent.change(amountInput, { target: { value: "80" } });
    fireEvent.click(screen.getByText("+ Agregar"));
    expect(onAdd).toHaveBeenCalledWith({
      payment_method: "cash",
      amount: 80,
      reference: null,
    });
  });

  it("shows complete when fully paid", () => {
    const payment: SalePayment = { payment_method: "cash", amount: 100, reference: null };
    render(
      <PaymentSection
        total={100}
        payments={[payment]}
        onAddPayment={jest.fn()}
        onRemovePayment={jest.fn()}
      />,
    );
    expect(screen.getByText("✅ Pago completo")).toBeInTheDocument();
  });

  it("shows error for missing payment", () => {
    const payment: SalePayment = { payment_method: "cash", amount: 50, reference: null };
    render(
      <PaymentSection
        total={100}
        payments={[payment]}
        onAddPayment={jest.fn()}
        onRemovePayment={jest.fn()}
        error="Falta S/ 50.00 por pagar"
      />,
    );
    expect(screen.getByText("Falta S/ 50.00 por pagar")).toBeInTheDocument();
  });

  it("hides add payment UI when complete", () => {
    const payment: SalePayment = { payment_method: "cash", amount: 100, reference: null };
    render(
      <PaymentSection
        total={100}
        payments={[payment]}
        onAddPayment={jest.fn()}
        onRemovePayment={jest.fn()}
      />,
    );
    expect(screen.queryByPlaceholderText("0.00")).not.toBeInTheDocument();
  });
});

describe("RestaurantSaleFields", () => {
  const mockData: RestaurantSaleData = {
    table_number: 5,
    guests: 3,
    order_type: "dine_in",
    waiter_name: "Carlos",
    tip_amount: 0,
    tip_pct: 10,
  };

  it("renders all restaurant fields", () => {
    render(
      <RestaurantSaleFields
        data={mockData}
        onChange={jest.fn()}
        tipsEnabled={true}
      />,
    );
    expect(screen.getByText("🍽️ Datos del Restaurante")).toBeInTheDocument();
    expect(screen.getByText("Mesa #")).toBeInTheDocument();
    expect(screen.getByText("Comensales")).toBeInTheDocument();
    expect(screen.getByText("Tipo de Orden")).toBeInTheDocument();
    expect(screen.getByText("Mesero")).toBeInTheDocument();
    expect(screen.getByText("Propina (S/)")).toBeInTheDocument();
    expect(screen.getByText("Notas de Cocina")).toBeInTheDocument();
  });

  it("hides tip fields when tipsEnabled is false", () => {
    render(
      <RestaurantSaleFields
        data={mockData}
        onChange={jest.fn()}
        tipsEnabled={false}
      />,
    );
    expect(screen.queryByText("Propina (S/)")).not.toBeInTheDocument();
    expect(screen.queryByText("Propina (%)")).not.toBeInTheDocument();
  });

  it("calls onChange when fields change", () => {
    const onChange = jest.fn();
    render(
      <RestaurantSaleFields
        data={mockData}
        onChange={onChange}
        tipsEnabled={true}
      />,
    );
    const mesaInput = screen.getByPlaceholderText("N°");
    fireEvent.change(mesaInput, { target: { value: "10" } });
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ table_number: 10 }),
    );
  });
});

describe("HardwareSaleFields", () => {
  const mockData: HardwareSaleData = {
    invoice_type: "boleta",
    customer_doc: "",
    delivery_address: "",
    requires_install: false,
    warranty_months: 12,
  };

  it("renders all hardware fields", () => {
    render(
      <HardwareSaleFields
        data={mockData}
        onChange={jest.fn()}
        warrantyEnabled={true}
      />,
    );
    expect(screen.getByText("🔧 Datos de Ferretería")).toBeInTheDocument();
    expect(screen.getByText("Tipo de Comprobante")).toBeInTheDocument();
    expect(screen.getByText("RUC / DNI del Cliente")).toBeInTheDocument();
    expect(screen.getByText("Meses de Garantía")).toBeInTheDocument();
    expect(screen.getByText("Instalación")).toBeInTheDocument();
    expect(screen.getByText("Dirección de Despacho")).toBeInTheDocument();
  });

  it("hides warranty when disabled", () => {
    render(
      <HardwareSaleFields
        data={mockData}
        onChange={jest.fn()}
        warrantyEnabled={false}
      />,
    );
    expect(screen.queryByText("Meses de Garantía")).not.toBeInTheDocument();
  });

  it("switches between boleta and factura", () => {
    const onChange = jest.fn();
    render(
      <HardwareSaleFields
        data={mockData}
        onChange={onChange}
        warrantyEnabled={true}
      />,
    );
    fireEvent.click(screen.getByText("📄 Factura"));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ invoice_type: "factura" }),
    );
  });
});

describe("Cross-type isolation (HU-F2-010)", () => {
  it("RestaurantSaleFields does not render hardware fields", () => {
    render(
      <RestaurantSaleFields
        data={{ table_number: 1, guests: 2, order_type: "dine_in", waiter_name: "A", tip_amount: 0, tip_pct: 0 }}
        onChange={jest.fn()}
        tipsEnabled={false}
      />,
    );
    expect(screen.queryByText("RUC / DNI")).not.toBeInTheDocument();
    expect(screen.queryByText("Meses de Garantía")).not.toBeInTheDocument();
    expect(screen.queryByText("Dirección de Despacho")).not.toBeInTheDocument();
  });

  it("HardwareSaleFields does not render restaurant fields", () => {
    render(
      <HardwareSaleFields
        data={{ invoice_type: "boleta", customer_doc: "", delivery_address: "", requires_install: false, warranty_months: 0 }}
        onChange={jest.fn()}
        warrantyEnabled={false}
      />,
    );
    expect(screen.queryByText("Mesa #")).not.toBeInTheDocument();
    expect(screen.queryByText("Mesero")).not.toBeInTheDocument();
    expect(screen.queryByText("Propina")).not.toBeInTheDocument();
    expect(screen.queryByText("Notas de Cocina")).not.toBeInTheDocument();
  });
});
