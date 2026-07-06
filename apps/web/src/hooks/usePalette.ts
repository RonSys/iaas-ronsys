import { useEffect, useState } from "react";
import { getPalette, updatePalette } from "@/services";
import type { ColorPalette } from "@/types";

const DEFAULT_PALETTE: ColorPalette = {
  primary: "#1a365d",
  secondary: "#2b6cb0",
  accent: "#e53e3e",
  background: "#f7fafc",
  surface: "#ffffff",
  text_primary: "#1a202c",
  text_secondary: "#718096",
  success: "#38a169",
  warning: "#d69e2e",
  error: "#e53e3e",
};

/**
 * Carga la paleta desde el backend y la aplica como CSS custom properties.
 * Si falla (ej: 400 por falta de X-Tenant-ID), usa defaults hardcodeados.
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
        // Aplicar defaults para evitar CSS sin variables → página blanca
        applyPalette(DEFAULT_PALETTE);
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
