/**
 * SerialSelectorModal — Modal de selección de seriales en POS.
 *
 * DT-F0-009 HU-F0-009-05: Seriales en venta
 *
 * Se abre cuando un producto con has_serial=true se agrega al ticket.
 * - Muestra seriales disponibles con checkboxes
 * - Valida que cantidad seleccionada = cantidad a vender
 * - Buscador para filtrar seriales (útil cuando hay muchos)
 * - Callback onConfirm(serials: string[])
 *
 * @module components/sales/SerialSelectorModal
 */

import { useState, useEffect, useMemo } from "react";
import type { ProductSerial } from "@/types";
import { getAvailableSerials } from "@/services/inventoryApi";

interface SerialSelectorModalProps {
  isOpen: boolean;
  productId: number;
  productName: string;
  quantity: number;
  /** Seriales ya seleccionados en otros items del mismo ticket (para evitar duplicados) */
  alreadySelectedSerials: string[];
  onConfirm: (serials: string[]) => void;
  onCancel: () => void;
}

export function SerialSelectorModal({
  isOpen,
  productId,
  productName,
  quantity,
  alreadySelectedSerials,
  onConfirm,
  onCancel,
}: SerialSelectorModalProps) {
  const [serials, setSerials] = useState<ProductSerial[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!isOpen) return;

    setLoading(true);
    setError(null);
    setSelected(new Set());

    getAvailableSerials(productId)
      .then((data) => {
        // Excluir seriales ya seleccionados en otros items del ticket
        const available = Array.isArray(data)
          ? data.filter((s) => !alreadySelectedSerials.includes(s.serial_number))
          : [];
        setSerials(available);
        if (available.length < quantity) {
          setError(`Stock insuficiente: solo ${available.length} seriales disponibles`);
        }
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Error al cargar seriales");
        setSerials([]);
      })
      .finally(() => setLoading(false));
  }, [isOpen, productId, alreadySelectedSerials]);

  const filteredSerials = useMemo(() => {
    if (!search.trim()) return serials;
    const q = search.toLowerCase();
    return serials.filter((s) => s.serial_number.toLowerCase().includes(q));
  }, [serials, search]);

  const toggleSerial = (serialNumber: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(serialNumber)) {
        next.delete(serialNumber);
      } else {
        // No permitir seleccionar más de la cantidad requerida
        if (next.size >= quantity) return prev;
        next.add(serialNumber);
      }
      return next;
    });
  };

  const handleConfirm = () => {
    if (selected.size !== quantity) return;
    onConfirm(Array.from(selected));
  };

  const canConfirm = selected.size === quantity && !error;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl p-6 w-full max-w-md mx-4 shadow-xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex-shrink-0 mb-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-brand-text-primary">
              🔢 Seleccionar Seriales
            </h3>
            <button
              onClick={onCancel}
              className="p-1.5 rounded-lg hover:bg-gray-100 text-brand-text-secondary"
              aria-label="Cerrar"
            >
              ✕
            </button>
          </div>
          <p className="text-sm text-brand-text-secondary mt-1">
            {productName} — Selecciona{" "}
            <strong className="text-brand-text-primary">{quantity}</strong> serial
            {quantity > 1 ? "es" : ""}
            {selected.size > 0 && (
              <span className="ml-2 text-brand-primary font-medium">
                ({selected.size}/{quantity} seleccionados)
              </span>
            )}
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="flex-shrink-0 mb-3 p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
            ⚠️ {error}
          </div>
        )}

        {/* Buscador */}
        <div className="flex-shrink-0 mb-3">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar serial..."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
          />
        </div>

        {/* Lista de seriales */}
        <div className="flex-1 overflow-y-auto border border-gray-200 rounded-lg">
          {loading ? (
            <div className="p-4 space-y-2">
              {Array.from({ length: Math.min(quantity + 2, 8) }).map((_, i) => (
                <div
                  key={i}
                  className="h-10 bg-gray-100 rounded animate-pulse"
                />
              ))}
            </div>
          ) : filteredSerials.length === 0 ? (
            <div className="p-6 text-center text-brand-text-secondary">
              <span className="text-2xl block mb-2">🔍</span>
              <p className="text-sm">
                {search ? "No se encontraron seriales" : "No hay seriales disponibles"}
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {filteredSerials.map((serial) => {
                const isSelected = selected.has(serial.serial_number);
                const isDisabled = !isSelected && selected.size >= quantity;

                return (
                  <label
                    key={serial.id}
                    className={`flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors
                      ${isSelected ? "bg-brand-primary/5" : "hover:bg-gray-50"}
                      ${isDisabled && !isSelected ? "opacity-40 cursor-not-allowed" : ""}`}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSerial(serial.serial_number)}
                      disabled={isDisabled && !isSelected}
                      className="w-4 h-4 rounded border-gray-300 text-brand-primary focus:ring-brand-primary/30 flex-shrink-0"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="font-mono text-sm font-medium text-brand-text-primary">
                        {serial.serial_number}
                      </div>
                      {serial.purchase_date && (
                        <div className="text-xs text-brand-text-secondary">
                          Compra: {new Date(serial.purchase_date).toLocaleDateString("es-PE")}
                        </div>
                      )}
                    </div>
                    {serial.cost_price != null && (
                      <div className="text-xs text-brand-text-secondary tabular-nums flex-shrink-0">
                        S/ {serial.cost_price.toFixed(2)}
                      </div>
                    )}
                  </label>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex-shrink-0 flex gap-3 justify-end mt-4">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            onClick={handleConfirm}
            disabled={!canConfirm}
            className="px-6 py-2 text-sm rounded-lg bg-brand-primary text-white hover:bg-brand-secondary disabled:opacity-50"
          >
            {canConfirm
              ? `Confirmar ${quantity} serial${quantity > 1 ? "es" : ""}`
              : `Selecciona ${quantity} serial${quantity > 1 ? "es" : ""}`}
          </button>
        </div>
      </div>
    </div>
  );
}
