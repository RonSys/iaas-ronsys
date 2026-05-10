import { useEffect, useState } from "react";
import { getPalette, updatePalette } from "@/services";
import type { ColorPalette } from "@/types";

/**
 * Carga la paleta desde el backend y la aplica como CSS custom properties.
 */
export function usePalette() {
  const [palette, setPalette] = useState<ColorPalette | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPalette()
      .then((p) => {
        setPalette(p);
        applyPalette(p);
      })
      .catch((err) => {
        setError(err.message);
        console.warn("usePalette: usando defaults", err);
      })
      .finally(() => setLoading(false));
  }, []);

  const changePalette = async (p: ColorPalette) => {
    const updated = await updatePalette(p);
    setPalette(updated);
    applyPalette(updated);
    return updated;
  };

  return { palette, loading, error, changePalette };
}

/** Aplica la paleta al :root como CSS custom properties */
function applyPalette(p: ColorPalette) {
  const root = document.documentElement.style;
  root.setProperty("--color-primary", p.primary);
  root.setProperty("--color-secondary", p.secondary);
  root.setProperty("--color-accent", p.accent);
  root.setProperty("--color-background", p.background);
  root.setProperty("--color-surface", p.surface);
  root.setProperty("--color-text-primary", p.text_primary);
  root.setProperty("--color-text-secondary", p.text_secondary);
  root.setProperty("--color-success", p.success);
  root.setProperty("--color-warning", p.warning);
  root.setProperty("--color-error", p.error);
}
