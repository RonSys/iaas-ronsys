/**
 * SaleFilters — Filtros de listado de ventas.
 *
 * HU-F2-011: UI de listado de ventas con filtros + ticket
 *
 * @module components/sales/SaleFilters
 */
import { useState, type FormEvent } from "react";
import type { SaleFilters as SaleFiltersType, BusinessType } from "@/types";

interface SaleFiltersProps {
  filters: SaleFiltersType;
  onChange: (filters: SaleFiltersType) => void;
  loading: boolean;
}

const BUSINESS_TYPES: { value: BusinessType | ""; label: string }[] = [
  { value: "", label: "Todos" },
  { value: "restaurant", label: "🍽️ Restaurante" },
  { value: "hardware", label: "🔧 Ferretería" },
  { value: "retail", label: "🛍️ Retail" },
  { value: "service", label: "🔨 Servicio" },
];

const PAYMENT_METHODS: { value: string; label: string }[] = [
  { value: "", label: "Todos" },
  { value: "cash", label: "💰 Efectivo" },
  { value: "card", label: "💳 Tarjeta" },
  { value: "yape", label: "📱 Yape" },
  { value: "plin", label: "📱 Plin" },
  { value: "transfer", label: "🏦 Transferencia" },
];

export function SaleFilters({ filters, onChange, loading }: SaleFiltersProps) {
  const [local, setLocal] = useState({
    from: filters.from ?? "",
    to: filters.to ?? "",
    business_type: filters.business_type ?? "",
    session_id: filters.session_id?.toString() ?? "",
    is_voided: filters.is_voided?.toString() ?? "",
    payment_method: filters.payment_method ?? "",
  });

  const handleApply = (e: FormEvent) => {
    e.preventDefault();
    const applied: SaleFiltersType = { page: 1, limit: filters.limit ?? 20 };
    if (local.from) applied.from = local.from;
    if (local.to) applied.to = local.to;
    if (local.business_type) applied.business_type = local.business_type as BusinessType;
    if (local.session_id) applied.session_id = Number(local.session_id);
    if (local.is_voided !== "" && local.is_voided !== undefined)
      applied.is_voided = local.is_voided === "true";
    if (local.payment_method) applied.payment_method = local.payment_method;
    onChange(applied);
  };

  const handleClear = () => {
    setLocal({ from: "", to: "", business_type: "", session_id: "", is_voided: "", payment_method: "" });
    onChange({ page: 1, limit: 20 });
  };

  return (
    <form onSubmit={handleApply} className="flex flex-wrap items-end gap-3 mb-4">
      <div>
        <label className="block text-xs font-medium text-brand-text-secondary mb-1">
          Desde
        </label>
        <input
          type="date"
          value={local.from}
          onChange={(e) => setLocal((p) => ({ ...p, from: e.target.value }))}
          disabled={loading}
          className="px-2 py-1.5 text-sm rounded-lg border border-gray-300
            focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-brand-text-secondary mb-1">
          Hasta
        </label>
        <input
          type="date"
          value={local.to}
          onChange={(e) => setLocal((p) => ({ ...p, to: e.target.value }))}
          disabled={loading}
          className="px-2 py-1.5 text-sm rounded-lg border border-gray-300
            focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-brand-text-secondary mb-1">
          Tipo Negocio
        </label>
        <select
          value={local.business_type}
          onChange={(e) => setLocal((p) => ({ ...p, business_type: e.target.value }))}
          disabled={loading}
          className="px-2 py-1.5 text-sm rounded-lg border border-gray-300
            focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
        >
          {BUSINESS_TYPES.map((bt) => (
            <option key={bt.value} value={bt.value}>
              {bt.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-xs font-medium text-brand-text-secondary mb-1">
          Sesión #
        </label>
        <input
          type="number"
          value={local.session_id}
          onChange={(e) => setLocal((p) => ({ ...p, session_id: e.target.value }))}
          disabled={loading}
          placeholder="ID"
          className="w-20 px-2 py-1.5 text-sm rounded-lg border border-gray-300
            focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-brand-text-secondary mb-1">
          Estado
        </label>
        <select
          value={local.is_voided}
          onChange={(e) => setLocal((p) => ({ ...p, is_voided: e.target.value }))}
          disabled={loading}
          className="px-2 py-1.5 text-sm rounded-lg border border-gray-300
            focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
        >
          <option value="">Todos</option>
          <option value="false">Activas</option>
          <option value="true">Anuladas</option>
        </select>
      </div>
      <div>
        <label className="block text-xs font-medium text-brand-text-secondary mb-1">
          Pago
        </label>
        <select
          value={local.payment_method}
          onChange={(e) => setLocal((p) => ({ ...p, payment_method: e.target.value }))}
          disabled={loading}
          className="px-2 py-1.5 text-sm rounded-lg border border-gray-300
            focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
        >
          {PAYMENT_METHODS.map((pm) => (
            <option key={pm.value} value={pm.value}>
              {pm.label}
            </option>
          ))}
        </select>
      </div>
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-1.5 text-sm rounded-lg bg-brand-primary text-white hover:opacity-90
            disabled:opacity-50"
        >
          Filtrar
        </button>
        <button
          type="button"
          onClick={handleClear}
          disabled={loading}
          className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 text-brand-text-secondary
            hover:bg-gray-50 disabled:opacity-50"
        >
          Limpiar
        </button>
      </div>
    </form>
  );
}
