/**
 * ModifierBottomSheet — Bottom sheet para seleccionar modificadores de un ítem.
 *
 * HU-F0-016 v3: Modificadores en Take Away
 * - Usa vaul para un sheet táctil-friendly (tablet: sube desde abajo; desktop: dialog centrado)
 * - Tres tipos de modificador según max_select y modifier_group_id:
 *   1. Cuantificable (max_select > 1): contador −/+
 *   2. Booleano (max_select = 1, sin grupo): checkbox
 *   3. Grupo excluyente (mismo modifier_group_id): radio buttons (solo 1 seleccionable)
 * - CTA "Agregar al pedido" fijo en la parte inferior con total correcto
 * - Swipe-to-dismiss; si se cierra sin confirmar no agrega nada
 *
 * ⚠️  v3 fix: Selection state is tracked in a ref and committed to React state
 *     via requestAnimationFrame. This prevents synchronous React re-renders
 *     during pointer events which caused Radix Dialog (used by vaul) to
 *     misdetect modifier taps as "outside clicks" and close the sheet.
 *
 * @module components/restaurante/ModifierBottomSheet
 */
import React from "react";
import { Drawer } from "vaul";

export interface MenuModifier {
  id: number;
  name: string;
  price_adjustment: number;
  max_select: number;
  modifier_group_id?: number | null;
}

export interface ModifierSelection {
  id: number;
  name: string;
  price_adjustment: number;
  quantity: number;
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  itemName: string;
  modifiers: MenuModifier[];
  onConfirm: (selected: ModifierSelection[]) => void;
  selectedIds?: number[];
}

/**
 * Group modifiers by modifier_group_id.
 * - Modifiers sharing the same explicit modifier_group_id → one group (radio)
 * - Modifiers without modifier_group_id → each in their own singleton group
 */
function groupModifiers(modifiers: MenuModifier[]): Map<string, MenuModifier[]> {
  const map = new Map<string, MenuModifier[]>();
  for (const mod of modifiers) {
    const key =
      mod.modifier_group_id != null
        ? `group_${mod.modifier_group_id}`
        : `single_${mod.id}`;
    const group = map.get(key);
    if (group) {
      group.push(mod);
    } else {
      map.set(key, [mod]);
    }
  }
  return map;
}

export function ModifierBottomSheet({
  open,
  onOpenChange,
  itemName,
  modifiers,
  onConfirm,
  selectedIds: _externalSelectedIds,
}: Props) {
  // ── Ref-based selection state (avoids synchronous re-render during pointer events) ──
  const quantitiesRef = React.useRef<Record<number, number>>({});
  const [renderVersion, setRenderVersion] = React.useState(0);
  const rAFRef = React.useRef<ReturnType<typeof requestAnimationFrame> | null>(null);

  /** Schedule a deferred re-render via rAF. Batches rapid clicks into one render. */
  const scheduleRender = React.useCallback(() => {
    if (rAFRef.current !== null) return; // already scheduled
    rAFRef.current = requestAnimationFrame(() => {
      rAFRef.current = null;
      setRenderVersion((v) => v + 1);
    });
  }, []);

  // Reset to zero when sheet opens (synchronous ref update + deferred render)
  React.useEffect(() => {
    if (open) {
      quantitiesRef.current = {};
      scheduleRender();
    }
    return () => {
      if (rAFRef.current !== null) {
        cancelAnimationFrame(rAFRef.current);
        rAFRef.current = null;
      }
    };
  }, [open, scheduleRender]);

  const groups = React.useMemo(() => groupModifiers(modifiers), [modifiers]);

  // ── handlers (update ref synchronously, schedule deferred render) ──

  const setQty = React.useCallback(
    (modId: number, qty: number) => {
      quantitiesRef.current = {
        ...quantitiesRef.current,
        [modId]: Math.max(0, qty),
      };
      scheduleRender();
    },
    [scheduleRender],
  );

  const toggleBoolean = React.useCallback(
    (mod: MenuModifier) => {
      const cur = quantitiesRef.current[mod.id] ?? 0;
      quantitiesRef.current = {
        ...quantitiesRef.current,
        [mod.id]: cur ? 0 : 1,
      };
      scheduleRender();
    },
    [scheduleRender],
  );

  const selectRadio = React.useCallback(
    (mod: MenuModifier, groupKey: string) => {
      const group = groups.get(groupKey) ?? [];
      const next = { ...quantitiesRef.current };
      for (const gm of group) next[gm.id] = 0;
      next[mod.id] = 1;
      quantitiesRef.current = next;
      scheduleRender();
    },
    [groups, scheduleRender],
  );

  // ── derive selection list (reads from ref — always up-to-date) ──

  const selectionList = React.useMemo((): ModifierSelection[] => {
    const list: ModifierSelection[] = [];
    for (const mod of modifiers) {
      const qty = quantitiesRef.current[mod.id] ?? 0;
      if (qty > 0) {
        list.push({
          id: mod.id,
          name: mod.name,
          price_adjustment: mod.price_adjustment,
          quantity: qty,
        });
      }
    }
    return list;
  }, [modifiers, renderVersion]);

  // Read quantities from ref for rendering
  const quantities = quantitiesRef.current;

  const totalAdjustment = selectionList.reduce(
    (sum, s) => sum + s.price_adjustment * s.quantity,
    0,
  );

  const handleConfirm = () => {
    onConfirm(selectionList);
    onOpenChange(false);
  };

  // ── render each group ─────────────────────────────────────

  const renderGroup = (groupKey: string, groupMods: MenuModifier[]) => {
    const isRadioGroup = groupMods.length > 1;

    return (
      <div key={groupKey} className="space-y-1">
        {isRadioGroup && (
          <p className="text-[10px] font-semibold uppercase text-brand-text-secondary px-1">
            Elegí una opción
          </p>
        )}
        {groupMods.map((mod) => {
          const qty = quantities[mod.id] ?? 0;

          if (isRadioGroup) {
            return renderRadio(mod, qty, groupKey);
          }
          if (mod.max_select > 1) {
            return renderQuantifiable(mod, qty);
          }
          return renderBoolean(mod, qty);
        })}
      </div>
    );
  };

  // ── quantifiable: −/⁺ counter ─────────────────────────────

  const renderQuantifiable = (mod: MenuModifier, qty: number) => {
    const atMax = qty >= mod.max_select;
    const atMin = qty <= 0;

    return (
      <div
        key={mod.id}
        className="flex items-center justify-between py-2.5 px-3 rounded-lg border border-gray-200"
        style={{ minHeight: 48 }}
      >
        <div className="flex-1 min-w-0">
          <span className="text-sm font-medium">{mod.name}</span>
          {mod.price_adjustment > 0 && (
            <span className="text-xs text-orange-600 font-medium ml-1.5">
              +S/ {mod.price_adjustment.toFixed(2)}
            </span>
          )}
          {mod.price_adjustment < 0 && (
            <span className="text-xs text-green-600 font-medium ml-1.5">
              -S/ {Math.abs(mod.price_adjustment).toFixed(2)}
            </span>
          )}
          {qty > 1 && (
            <span className="text-[10px] text-brand-text-secondary ml-1">
              (total: S/ {(mod.price_adjustment * qty).toFixed(2)})
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 flex-shrink-0 ml-3">
          <button
            type="button"
            data-vaul-no-drag
            onClick={(e) => {
              e.stopPropagation();
              e.preventDefault();
              setQty(mod.id, qty - 1);
            }}
            disabled={atMin}
            className="w-8 h-8 rounded-lg border border-gray-300 flex items-center justify-center
              text-sm font-bold text-gray-600 hover:bg-gray-100
              disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            aria-label={`Quitar ${mod.name}`}
          >
            −
          </button>
          <span className="w-6 text-center text-sm font-semibold tabular-nums">
            {qty}
          </span>
          <button
            type="button"
            data-vaul-no-drag
            onClick={(e) => {
              e.stopPropagation();
              e.preventDefault();
              setQty(mod.id, qty + 1);
            }}
            disabled={atMax}
            className="w-8 h-8 rounded-lg border border-gray-300 flex items-center justify-center
              text-sm font-bold text-gray-600 hover:bg-gray-100
              disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            aria-label={`Agregar ${mod.name}`}
          >
            +
          </button>
        </div>
      </div>
    );
  };

  // ── boolean: checkbox ─────────────────────────────────────

  const renderBoolean = (mod: MenuModifier, qty: number) => {
    const isSelected = qty > 0;

    return (
      <label
        key={mod.id}
        data-vaul-no-drag
        className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer
          transition-colors ${
            isSelected
              ? "border-brand-primary bg-brand-primary/5"
              : "border-gray-200 hover:bg-gray-50 active:bg-gray-100"
          }`}
        style={{ minHeight: 48 }}
        onClick={(e) => {
          e.stopPropagation();
          e.preventDefault();
          toggleBoolean(mod);
        }}
      >
        <div className="flex-1 min-w-0">
          <span className="text-sm font-medium">{mod.name}</span>
          {mod.price_adjustment !== 0 && (
            <span
              className={`text-xs font-medium ml-1.5 ${
                mod.price_adjustment > 0 ? "text-orange-600" : "text-green-600"
              }`}
            >
              {mod.price_adjustment > 0 ? "+" : "-"}S/ {Math.abs(mod.price_adjustment).toFixed(2)}
            </span>
          )}
        </div>
        <div
          className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 ml-3
            transition-colors ${
              isSelected ? "bg-brand-primary border-brand-primary" : "border-gray-300"
            }`}
        >
          {isSelected && (
            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
            </svg>
          )}
        </div>
        <input
          type="checkbox"
          checked={isSelected}
          onChange={() => toggleBoolean(mod)}
          className="sr-only"
          tabIndex={-1}
        />
      </label>
    );
  };

  // ── radio: exclusive group member ─────────────────────────

  const renderRadio = (mod: MenuModifier, qty: number, groupKey: string) => {
    const isSelected = qty > 0;

    return (
      <label
        key={mod.id}
        data-vaul-no-drag
        className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer
          transition-colors ${
            isSelected
              ? "border-brand-primary bg-brand-primary/5"
              : "border-gray-200 hover:bg-gray-50 active:bg-gray-100"
          }`}
        style={{ minHeight: 48 }}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          selectRadio(mod, groupKey);
        }}
      >
        <div className="flex-1 min-w-0">
          <span className="text-sm font-medium">{mod.name}</span>
          {mod.price_adjustment !== 0 && (
            <span
              className={`text-xs font-medium ml-1.5 ${
                mod.price_adjustment > 0 ? "text-orange-600" : "text-green-600"
              }`}
            >
              {mod.price_adjustment > 0 ? "+" : "-"}S/ {Math.abs(mod.price_adjustment).toFixed(2)}
            </span>
          )}
        </div>
        <div
          className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ml-3
            transition-colors ${
              isSelected ? "border-brand-primary" : "border-gray-300"
            }`}
        >
          {isSelected && (
            <div className="w-2.5 h-2.5 rounded-full bg-brand-primary" />
          )}
        </div>
        <input
          type="radio"
          name={`mod-group-${groupKey}`}
          checked={isSelected}
          onChange={() => selectRadio(mod, groupKey)}
          className="sr-only"
          tabIndex={-1}
        />
      </label>
    );
  };

  // ── JSX ───────────────────────────────────────────────────

  const groupEntries = Array.from(groups.entries());

  return (
    <Drawer.Root open={open} onOpenChange={onOpenChange} shouldScaleBackground>
      <Drawer.Portal>
        <Drawer.Overlay className="fixed inset-0 bg-black/40 z-50" />
        <Drawer.Content
          className="fixed bottom-0 left-0 right-0 z-50 mt-24 flex flex-col
            rounded-t-2xl bg-white max-h-[85dvh] md:max-w-md md:left-1/2
            md:-translate-x-1/2 md:bottom-auto md:top-1/2
            md:-translate-y-1/2 md:rounded-2xl"
        >
          {/* Handle bar (visible on mobile/tablet) */}
          <div className="mx-auto mt-3 mb-1 h-1.5 w-12 flex-shrink-0 rounded-full bg-gray-300 md:hidden" />

          {/* Header */}
          <div className="px-6 pt-2 pb-2 border-b border-gray-100">
            <Drawer.Title className="text-lg font-bold text-brand-text-primary">
              {itemName}
            </Drawer.Title>
            <Drawer.Description className="text-xs text-brand-text-secondary mt-0.5">
              Personalizá tu pedido
            </Drawer.Description>
          </div>

          {/* Modifier list */}
          <div data-vaul-no-drag className="flex-1 overflow-y-auto px-6 py-3 space-y-3">
            {groupEntries.map(([gid, gmods]) => renderGroup(gid, gmods))}

            {modifiers.length === 0 && (
              <p className="text-sm text-brand-text-secondary text-center py-8">
                Este ítem no tiene modificadores disponibles.
              </p>
            )}
          </div>

          {/* Footer with total adjustment and CTA */}
          <div className="px-6 py-4 border-t border-gray-100 space-y-3 bg-white rounded-b-2xl">
            {selectionList.length > 0 && totalAdjustment !== 0 && (
              <div className="flex justify-between text-sm">
                <span className="text-brand-text-secondary">Ajuste por modificadores:</span>
                <span
                  className={`font-medium ${totalAdjustment > 0 ? "text-orange-600" : "text-green-600"}`}
                >
                  {totalAdjustment > 0 ? "+" : ""}S/ {totalAdjustment.toFixed(2)}
                </span>
              </div>
            )}
            <button
              data-vaul-no-drag
              onClick={handleConfirm}
              className="w-full py-3 bg-brand-primary text-white rounded-xl text-sm font-semibold
                hover:bg-brand-secondary active:scale-[0.98] transition-all
                disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100"
              style={{ minHeight: 48 }}
            >
              Agregar al pedido
            </button>
          </div>
        </Drawer.Content>
      </Drawer.Portal>
    </Drawer.Root>
  );
}
