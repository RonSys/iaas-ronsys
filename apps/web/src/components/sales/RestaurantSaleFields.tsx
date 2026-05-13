/**
 * RestaurantSaleFields — Campos especializados para ventas de restaurante.
 *
 * Se renderizan SOLO si business_type = "restaurant" y features.tables_enabled.
 *
 * Campos: mesa, comensales, tipo de orden, mesero, propina, notas de cocina.
 *
 * HU-F2-010: UI de venta especializada por tipo de negocio
 *
 * @module components/sales/RestaurantSaleFields
 */
import type { RestaurantSaleData, OrderType } from "@/types";

interface RestaurantSaleFieldsProps {
  data: RestaurantSaleData;
  onChange: (data: RestaurantSaleData) => void;
  tipsEnabled: boolean;
}

const ORDER_TYPES: { value: OrderType; label: string }[] = [
  { value: "dine_in", label: "🍽️ En Mesa" },
  { value: "takeout", label: "🥡 Para Llevar" },
  { value: "delivery", label: "🛵 Delivery" },
];

export function RestaurantSaleFields({
  data,
  onChange,
  tipsEnabled,
}: RestaurantSaleFieldsProps) {
  const update = (partial: Partial<RestaurantSaleData>) => {
    onChange({ ...data, ...partial });
  };

  return (
    <div className="border-2 border-orange-200 bg-orange-50/30 rounded-lg p-4">
      <h4 className="text-sm font-semibold text-orange-800 mb-3 flex items-center gap-2">
        🍽️ Datos del Restaurante
      </h4>

      <div className="grid grid-cols-2 gap-3">
        {/* Mesa */}
        <div>
          <label className="block text-xs font-medium text-brand-text-secondary mb-1">
            Mesa #
          </label>
          <input
            type="number"
            min="1"
            value={data.table_number || ""}
            onChange={(e) => update({ table_number: Number(e.target.value) || 0 })}
            className="w-full px-3 py-1.5 text-sm rounded-lg border border-gray-300
              focus:outline-none focus:ring-2 focus:ring-orange-300/30"
            placeholder="N°"
          />
        </div>

        {/* Comensales */}
        <div>
          <label className="block text-xs font-medium text-brand-text-secondary mb-1">
            Comensales
          </label>
          <input
            type="number"
            min="1"
            value={data.guests}
            onChange={(e) => update({ guests: Number(e.target.value) || 1 })}
            className="w-full px-3 py-1.5 text-sm rounded-lg border border-gray-300
              focus:outline-none focus:ring-2 focus:ring-orange-300/30"
          />
        </div>

        {/* Tipo de orden */}
        <div className="col-span-2">
          <label className="block text-xs font-medium text-brand-text-secondary mb-1">
            Tipo de Orden
          </label>
          <div className="flex gap-2">
            {ORDER_TYPES.map((ot) => (
              <button
                key={ot.value}
                type="button"
                onClick={() => update({ order_type: ot.value })}
                className={`flex-1 py-1.5 px-2 text-xs rounded-lg border transition-colors ${
                  data.order_type === ot.value
                    ? "bg-orange-100 border-orange-300 text-orange-800 font-medium"
                    : "bg-white border-gray-200 text-brand-text-secondary hover:bg-gray-50"
                }`}
              >
                {ot.label}
              </button>
            ))}
          </div>
        </div>

        {/* Mesero */}
        <div className="col-span-2">
          <label className="block text-xs font-medium text-brand-text-secondary mb-1">
            Mesero
          </label>
          <input
            type="text"
            value={data.waiter_name}
            onChange={(e) => update({ waiter_name: e.target.value })}
            placeholder="Nombre del mesero"
            className="w-full px-3 py-1.5 text-sm rounded-lg border border-gray-300
              focus:outline-none focus:ring-2 focus:ring-orange-300/30"
          />
        </div>

        {/* Propina (condicional) */}
        {tipsEnabled && (
          <>
            <div>
              <label className="block text-xs font-medium text-brand-text-secondary mb-1">
                Propina (S/)
              </label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={data.tip_amount || ""}
                onChange={(e) => {
                  update({
                    tip_amount: Number(e.target.value) || 0,
                    tip_pct: 0,
                  });
                }}
                className="w-full px-3 py-1.5 text-sm rounded-lg border border-gray-300
                  focus:outline-none focus:ring-2 focus:ring-orange-300/30"
                placeholder="0.00"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-brand-text-secondary mb-1">
                Propina (%)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                value={data.tip_pct || ""}
                onChange={(e) => {
                  update({
                    tip_pct: Number(e.target.value) || 0,
                    tip_amount: 0,
                  });
                }}
                className="w-full px-3 py-1.5 text-sm rounded-lg border border-gray-300
                  focus:outline-none focus:ring-2 focus:ring-orange-300/30"
                placeholder="0"
              />
            </div>
          </>
        )}

        {/* Notas de cocina */}
        <div className="col-span-2">
          <label className="block text-xs font-medium text-brand-text-secondary mb-1">
            Notas de Cocina
          </label>
          <textarea
            value={data.kitchen_notes ?? ""}
            onChange={(e) => update({ kitchen_notes: e.target.value })}
            placeholder="Ej: sin cebolla, término medio..."
            rows={2}
            className="w-full px-3 py-1.5 text-sm rounded-lg border border-gray-300
              focus:outline-none focus:ring-2 focus:ring-orange-300/30 resize-none"
          />
        </div>
      </div>
    </div>
  );
}
