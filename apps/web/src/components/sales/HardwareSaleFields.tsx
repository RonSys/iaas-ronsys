/**
 * HardwareSaleFields — Campos especializados para ventas de ferretería.
 *
 * Se renderizan SOLO si business_type = "hardware" y features.invoice_required.
 *
 * Campos: selector boleta/factura, RUC/DNI cliente, meses garantía, dirección despacho.
 *
 * HU-F2-010: UI de venta especializada por tipo de negocio
 *
 * @module components/sales/HardwareSaleFields
 */
import type { HardwareSaleData, InvoiceType } from "@/types";

interface HardwareSaleFieldsProps {
  data: HardwareSaleData;
  onChange: (data: HardwareSaleData) => void;
  warrantyEnabled: boolean;
}

export function HardwareSaleFields({
  data,
  onChange,
  warrantyEnabled,
}: HardwareSaleFieldsProps) {
  const update = (partial: Partial<HardwareSaleData>) => {
    onChange({ ...data, ...partial });
  };

  return (
    <div className="border-2 border-blue-200 bg-blue-50/30 rounded-lg p-4">
      <h4 className="text-sm font-semibold text-blue-800 mb-3 flex items-center gap-2">
        🔧 Datos de Ferretería
      </h4>

      <div className="grid grid-cols-2 gap-3">
        {/* Tipo de comprobante */}
        <div className="col-span-2">
          <label className="block text-xs font-medium text-brand-text-secondary mb-1">
            Tipo de Comprobante
          </label>
          <div className="flex gap-2">
            {(["boleta", "factura"] as InvoiceType[]).map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => update({ invoice_type: type })}
                className={`flex-1 py-1.5 px-3 text-xs rounded-lg border transition-colors ${
                  data.invoice_type === type
                    ? "bg-blue-100 border-blue-300 text-blue-800 font-medium"
                    : "bg-white border-gray-200 text-brand-text-secondary hover:bg-gray-50"
                }`}
              >
                {type === "boleta" ? "🧾 Boleta" : "📄 Factura"}
              </button>
            ))}
          </div>
        </div>

        {/* RUC/DNI */}
        <div className="col-span-2">
          <label className="block text-xs font-medium text-brand-text-secondary mb-1">
            RUC / DNI del Cliente
          </label>
          <input
            type="text"
            value={data.customer_doc}
            onChange={(e) => update({ customer_doc: e.target.value })}
            placeholder={
              data.invoice_type === "factura"
                ? "20123456789"
                : "12345678"
            }
            className="w-full px-3 py-1.5 text-sm rounded-lg border border-gray-300
              focus:outline-none focus:ring-2 focus:ring-blue-300/30"
          />
          {data.invoice_type === "factura" && (
            <p className="text-xs text-brand-text-secondary mt-0.5">
              Requerido para emitir factura
            </p>
          )}
        </div>

        {/* Garantía (condicional) */}
        {warrantyEnabled && (
          <div>
            <label className="block text-xs font-medium text-brand-text-secondary mb-1">
              Meses de Garantía
            </label>
            <select
              value={data.warranty_months}
              onChange={(e) => update({ warranty_months: Number(e.target.value) })}
              className="w-full px-3 py-1.5 text-sm rounded-lg border border-gray-300
                focus:outline-none focus:ring-2 focus:ring-blue-300/30"
            >
              <option value={0}>Sin garantía</option>
              <option value={3}>3 meses</option>
              <option value={6}>6 meses</option>
              <option value={12}>12 meses</option>
              <option value={24}>24 meses</option>
              <option value={36}>36 meses</option>
            </select>
          </div>
        )}

        {/* Requiere instalación */}
        <div>
          <label className="block text-xs font-medium text-brand-text-secondary mb-1">
            Instalación
          </label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => update({ requires_install: false })}
              className={`flex-1 py-1.5 px-3 text-xs rounded-lg border transition-colors ${
                !data.requires_install
                  ? "bg-blue-100 border-blue-300 text-blue-800 font-medium"
                  : "bg-white border-gray-200 text-brand-text-secondary"
              }`}
            >
              No
            </button>
            <button
              type="button"
              onClick={() => update({ requires_install: true })}
              className={`flex-1 py-1.5 px-3 text-xs rounded-lg border transition-colors ${
                data.requires_install
                  ? "bg-blue-100 border-blue-300 text-blue-800 font-medium"
                  : "bg-white border-gray-200 text-brand-text-secondary"
              }`}
            >
              Sí
            </button>
          </div>
        </div>

        {/* Dirección de despacho */}
        <div className="col-span-2">
          <label className="block text-xs font-medium text-brand-text-secondary mb-1">
            Dirección de Despacho
          </label>
          <input
            type="text"
            value={data.delivery_address ?? ""}
            onChange={(e) => update({ delivery_address: e.target.value })}
            placeholder="Av. Principal 123, Lima"
            className="w-full px-3 py-1.5 text-sm rounded-lg border border-gray-300
              focus:outline-none focus:ring-2 focus:ring-blue-300/30"
          />
        </div>
      </div>
    </div>
  );
}
