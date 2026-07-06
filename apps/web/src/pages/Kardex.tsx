/**
 * KardexPage — Control de inventarios y kárdex valorizado.
 *
 * Visualiza productos en inventario (código, nombre, stock, costo promedio,
 * valor total) en un grid de tarjetas. Al seleccionar un producto, muestra
 * su historial de movimientos con el método de costo promedio ponderado.
 *
 * Incluye 3 modales:
 * - Nuevo Producto: registro de producto con stock y costo inicial
 * - Entrada: registro de compra (cantidad + costo unitario)
 * - Salida: registro de consumo/venta (cantidad, sale a costo promedio)
 *
 * @page Kárdex
 */
import { useState, useEffect } from "react";
import { useKardexInventory, useKardex } from "@/hooks/useAccounting";
import { registerKardexEntry, registerKardexExit, registerProduct } from "@/services";
import { fmtCurrency, Skeleton } from "@/components/dashboard/KPICard";
import type { KardexProduct } from "@/types";

export function KardexPage() {
  const inventory = useKardexInventory();
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const kardex = useKardex(selectedCode ?? "");
  const [showNewProduct, setShowNewProduct] = useState(false);
  const [showEntry, setShowEntry] = useState(false);
  const [showExit, setShowExit] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    inventory.refetch();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (selectedCode) kardex.refetch();
  }, [selectedCode]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">📦 Kárdex — Inventario</h2>
        <div className="flex gap-2">
          <button onClick={() => setShowNewProduct(true)} className="btn btn-primary text-sm">
            + Producto
          </button>
          <button onClick={() => setShowEntry(true)} className="btn btn-secondary text-sm" disabled={!selectedCode}>
            + Entrada
          </button>
          <button onClick={() => setShowExit(true)} className="btn btn-accent text-sm" disabled={!selectedCode}>
            - Salida
          </button>
        </div>
      </div>

      {message && (
        <div className="card border-brand-success/30 bg-brand-success/5 text-brand-success text-sm">
          {message}
          <button onClick={() => setMessage(null)} className="ml-4 text-xs underline">Cerrar</button>
        </div>
      )}

      {/* Inventory Summary */}
      {inventory.loading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)}
        </div>
      ) : inventory.error ? (
        <div className="card text-brand-error text-sm">⚠️ {inventory.error}</div>
      ) : inventory.data && inventory.data.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {inventory.data.map((product) => (
            <ProductCard
              key={product.code}
              product={product}
              isSelected={selectedCode === product.code}
              onClick={() => setSelectedCode(product.code)}
            />
          ))}
        </div>
      ) : (
        <div className="card text-center py-8 text-brand-text-secondary">
          <span className="text-3xl">📦</span>
          <p className="mt-2">No hay productos registrados. Agregá uno para empezar.</p>
        </div>
      )}

      {/* Kardex detail for selected product */}
      {selectedCode && (
        <div className="card">
          <h3 className="font-bold text-brand-text-primary mb-4">
            📋 Movimientos: {selectedCode}
          </h3>
          {kardex.loading ? (
            <Skeleton className="h-32 w-full" />
          ) : kardex.error ? (
            <div className="text-brand-error text-sm">⚠️ {kardex.error}</div>
          ) : kardex.data && kardex.data.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b-2 border-brand-primary/20 text-left text-xs uppercase tracking-wider text-brand-text-secondary">
                    <th className="py-2 pr-2">Fecha</th>
                    <th className="py-2 pr-2">Concepto</th>
                    <th className="py-2 pr-2">Tipo</th>
                    <th className="py-2 pr-2 text-right">Cantidad</th>
                    <th className="py-2 pr-2 text-right">C.U.</th>
                    <th className="py-2 pr-2 text-right">Total</th>
                    <th className="py-2 pr-2 text-right">Saldo Cant.</th>
                    <th className="py-2 pr-2 text-right">Saldo C.U.</th>
                    <th className="py-2 text-right">Saldo Total</th>
                  </tr>
                </thead>
                <tbody>
                  {kardex.data.map((row, i) => (
                    <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-1.5 pr-2 text-xs">{new Date(row.date).toLocaleDateString("es-PE")}</td>
                      <td className="py-1.5 pr-2">{row.concept}</td>
                      <td className="py-1.5 pr-2">
                        <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                          row.movement_type === "entrada" ? "bg-brand-success/10 text-brand-success" :
                          row.movement_type === "salida" ? "bg-brand-error/10 text-brand-error" :
                          "bg-gray-100 text-brand-text-secondary"
                        }`}>
                          {row.movement_type}
                        </span>
                      </td>
                      <td className="py-1.5 pr-2 text-right font-mono text-xs">{row.quantity.toLocaleString()}</td>
                      <td className="py-1.5 pr-2 text-right font-mono text-xs">{fmtCurrency(row.unit_cost)}</td>
                      <td className="py-1.5 pr-2 text-right font-mono text-xs">{fmtCurrency(row.total)}</td>
                      <td className="py-1.5 pr-2 text-right font-mono text-xs font-semibold">{row.balance_quantity.toLocaleString()}</td>
                      <td className="py-1.5 pr-2 text-right font-mono text-xs">{fmtCurrency(row.balance_avg_cost)}</td>
                      <td className="py-1.5 text-right font-mono text-xs font-semibold">{fmtCurrency(row.balance_total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-brand-text-secondary">Sin movimientos registrados.</p>
          )}
        </div>
      )}

      {/* Modals */}
      {showNewProduct && (
        <NewProductModal
          onClose={() => setShowNewProduct(false)}
          onCreated={() => { setShowNewProduct(false); inventory.refetch(); setMessage("Producto creado ✅"); }}
        />
      )}
      {showEntry && selectedCode && (
        <KardexEntryModal
          productCode={selectedCode}
          onClose={() => setShowEntry(false)}
          onDone={() => { setShowEntry(false); kardex.refetch(); inventory.refetch(); setMessage("Entrada registrada ✅"); }}
        />
      )}
      {showExit && selectedCode && (
        <KardexExitModal
          productCode={selectedCode}
          onClose={() => setShowExit(false)}
          onDone={() => { setShowExit(false); kardex.refetch(); inventory.refetch(); setMessage("Salida registrada ✅"); }}
        />
      )}
    </div>
  );
}

/* ─── Product Card ─── */

function ProductCard({
  product,
  isSelected,
  onClick,
}: {
  product: KardexProduct;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`card text-left transition-all hover:shadow-md ${
        isSelected ? "ring-2 ring-brand-primary shadow-md" : ""
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="font-bold text-brand-text-primary">{product.name}</div>
          <div className="text-xs text-brand-text-secondary font-mono">{product.code}</div>
        </div>
        <span className="text-xs bg-gray-100 px-2 py-0.5 rounded font-mono">
          {product.unit}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-2 mt-3">
        <MiniInfo label="Stock" value={product.current_stock.toLocaleString()} />
        <MiniInfo label="C.U. Prom." value={fmtCurrency(product.average_cost)} />
        <MiniInfo label="Valor Total" value={fmtCurrency(product.total_value)} />
      </div>
    </button>
  );
}

function MiniInfo({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center">
      <div className="text-[10px] text-brand-text-secondary">{label}</div>
      <div className="text-sm font-bold font-mono text-brand-text-primary">{value}</div>
    </div>
  );
}

/* ─── New Product Modal ─── */

function NewProductModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [unit, setUnit] = useState("kg");
  const [stock, setStock] = useState(0);
  const [cost, setCost] = useState(0);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await registerProduct({ code, name, unit, initial_stock: stock, initial_cost: cost });
      onCreated();
    } catch {
      // error handled by parent
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
        <h3 className="font-bold text-lg mb-4">📦 Nuevo Producto</h3>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-xs font-medium text-brand-text-secondary">Código</label>
            <input className="input-field" value={code} onChange={(e) => setCode(e.target.value)} required />
          </div>
          <div>
            <label className="text-xs font-medium text-brand-text-secondary">Nombre</label>
            <input className="input-field" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div>
            <label className="text-xs font-medium text-brand-text-secondary">Unidad</label>
            <select className="input-field" value={unit} onChange={(e) => setUnit(e.target.value)}>
              <option value="kg">kg</option>
              <option value="L">Litro</option>
              <option value="un">Unidad</option>
              <option value="g">gramo</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-brand-text-secondary">Stock inicial</label>
              <input type="number" className="input-field" value={stock} onChange={(e) => setStock(Number(e.target.value))} min={0} />
            </div>
            <div>
              <label className="text-xs font-medium text-brand-text-secondary">Costo unitario</label>
              <input type="number" className="input-field" value={cost} onChange={(e) => setCost(Number(e.target.value))} min={0} step="0.01" />
            </div>
          </div>
          <div className="flex gap-2 pt-2">
            <button type="submit" disabled={loading} className="btn-primary flex-1">
              {loading ? "Creando..." : "Crear Producto"}
            </button>
            <button type="button" onClick={onClose} className="btn-ghost">Cancelar</button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ─── Entry Modal ─── */

function KardexEntryModal({
  productCode,
  onClose,
  onDone,
}: {
  productCode: string;
  onClose: () => void;
  onDone: () => void;
}) {
  const [qty, setQty] = useState(1);
  const [unitCost, setUnitCost] = useState(0);
  const [concept, setConcept] = useState("Compra de insumos");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await registerKardexEntry({
        product_code: productCode,
        quantity: qty,
        unit_cost: unitCost,
        concept,
        date: new Date().toISOString().split("T")[0],
      });
      onDone();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
        <h3 className="font-bold text-lg mb-4">➕ Registrar Entrada — {productCode}</h3>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-xs font-medium text-brand-text-secondary">Cantidad</label>
            <input type="number" className="input-field" value={qty} onChange={(e) => setQty(Number(e.target.value))} min={0.01} step="0.01" required />
          </div>
          <div>
            <label className="text-xs font-medium text-brand-text-secondary">Costo unitario</label>
            <input type="number" className="input-field" value={unitCost} onChange={(e) => setUnitCost(Number(e.target.value))} min={0} step="0.01" required />
          </div>
          <div>
            <label className="text-xs font-medium text-brand-text-secondary">Concepto</label>
            <input className="input-field" value={concept} onChange={(e) => setConcept(e.target.value)} required />
          </div>
          <div className="flex gap-2 pt-2">
            <button type="submit" disabled={loading} className="btn-primary flex-1">
              {loading ? "Registrando..." : "Registrar Entrada"}
            </button>
            <button type="button" onClick={onClose} className="btn-ghost">Cancelar</button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ─── Exit Modal ─── */

function KardexExitModal({
  productCode,
  onClose,
  onDone,
}: {
  productCode: string;
  onClose: () => void;
  onDone: () => void;
}) {
  const [qty, setQty] = useState(1);
  const [concept, setConcept] = useState("Venta / consumo");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await registerKardexExit({
        product_code: productCode,
        quantity: qty,
        concept,
        date: new Date().toISOString().split("T")[0],
      });
      onDone();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
        <h3 className="font-bold text-lg mb-4">➖ Registrar Salida — {productCode}</h3>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-xs font-medium text-brand-text-secondary">Cantidad</label>
            <input type="number" className="input-field" value={qty} onChange={(e) => setQty(Number(e.target.value))} min={0.01} step="0.01" required />
          </div>
          <div>
            <label className="text-xs font-medium text-brand-text-secondary">Concepto</label>
            <input className="input-field" value={concept} onChange={(e) => setConcept(e.target.value)} required />
          </div>
          <div className="flex gap-2 pt-2">
            <button type="submit" disabled={loading} className="btn-accent flex-1">
              {loading ? "Registrando..." : "Registrar Salida"}
            </button>
            <button type="button" onClick={onClose} className="btn-ghost">Cancelar</button>
          </div>
        </form>
      </div>
    </div>
  );
}
