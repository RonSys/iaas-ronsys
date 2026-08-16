/**
 * Settings — Configuración de la empresa (branding).
 *
 * Permite personalizar la paleta de 10 colores que se aplica
 * a toda la interfaz vía CSS custom properties. Incluye:
 * - 4 paletas predefinidas (Azul Marino, Verde Bosque, Rojizo Cálido, Púrpura)
 * - 10 color pickers individuales con vista previa
 * - Información de la empresa (moneda, zona horaria, formato fecha)
 *
 * Los cambios se persisten vía PATCH /api/settings/palette y se aplican
 * al instante sin recargar la página.
 *
 * @page Settings
 */
import { useState, useEffect } from "react";
import { getSettings } from "@/services";
import { usePalette } from "@/hooks/usePalette";
import { useCompanySettings } from "@/hooks/useCompanySettings";
import {
  getAppointmentSettings,
  patchAppointmentSettings,
  type AppointmentSettings,
} from "@/services/appointmentsApi";
import type { ColorPalette, CompanySettings } from "@/types";

const PALETTE_KEYS: { key: keyof ColorPalette; label: string; cssVar: string }[] = [
  { key: "primary", label: "Primario", cssVar: "--color-primary" },
  { key: "secondary", label: "Secundario", cssVar: "--color-secondary" },
  { key: "accent", label: "Acento", cssVar: "--color-accent" },
  { key: "background", label: "Fondo", cssVar: "--color-background" },
  { key: "surface", label: "Superficie", cssVar: "--color-surface" },
  { key: "text_primary", label: "Texto Principal", cssVar: "--color-text-primary" },
  { key: "text_secondary", label: "Texto Secundario", cssVar: "--color-text-secondary" },
  { key: "success", label: "Éxito", cssVar: "--color-success" },
  { key: "warning", label: "Advertencia", cssVar: "--color-warning" },
  { key: "error", label: "Error", cssVar: "--color-error" },
];

export function Settings() {
  const { palette, changePalette } = usePalette();
  const { businessType } = useCompanySettings();
  const [settings, setSettings] = useState<CompanySettings | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [messageType, setMessageType] = useState<"success" | "error">("success");

  // ─── F6 (Spec 07): Agenda de Citas — companies.settings.appointments (D3) ───
  const [apptSettings, setApptSettings] = useState<AppointmentSettings | null>(null);
  const [apptSaving, setApptSaving] = useState(false);

  // Predefined palettes
  const presets = [
    { name: "Azul Marino", primary: "#1a365d", secondary: "#2b6cb0", accent: "#e53e3e", background: "#f7fafc", surface: "#ffffff", text_primary: "#1a202c", text_secondary: "#718096", success: "#38a169", warning: "#d69e2e", error: "#e53e3e" },
    { name: "Verde Bosque", primary: "#22543d", secondary: "#38a169", accent: "#d69e2e", background: "#f0fff4", surface: "#ffffff", text_primary: "#1a202c", text_secondary: "#718096", success: "#38a169", warning: "#d69e2e", error: "#e53e3e" },
    { name: "Rojizo Cálido", primary: "#9b2c2c", secondary: "#c53030", accent: "#d69e2e", background: "#fffaf0", surface: "#ffffff", text_primary: "#1a202c", text_secondary: "#718096", success: "#38a169", warning: "#d69e2e", error: "#c53030" },
    { name: "Púrpura", primary: "#553c9a", secondary: "#805ad5", accent: "#e53e3e", background: "#faf5ff", surface: "#ffffff", text_primary: "#1a202c", text_secondary: "#718096", success: "#38a169", warning: "#d69e2e", error: "#e53e3e" },
  ];

  useEffect(() => {
    getSettings().then(setSettings).catch(console.warn);
  }, []);

  // D3: la ventana de reservas es configurable desde la UI staff (solo restaurante)
  useEffect(() => {
    if (businessType !== "restaurant") return;
    getAppointmentSettings().then(setApptSettings).catch(console.warn);
  }, [businessType]);

  const notify = (msg: string, type: "success" | "error" = "success") => {
    setMessage(msg);
    setMessageType(type);
    setTimeout(() => setMessage(null), 3000);
  };

  const handleColorChange = async (key: keyof ColorPalette, value: string) => {
    if (!palette) return;
    const updated = { ...palette, [key]: value };
    try {
      await changePalette(updated);
      notify(`Color "${key}" actualizado`);
    } catch {
      notify("Error al actualizar", "error");
    }
  };

  const handlePreset = async (preset: ColorPalette) => {
    try {
      await changePalette(preset);
      notify("Paleta predefinida aplicada");
    } catch {
      notify("Error al aplicar paleta", "error");
    }
  };

  /** D3: persiste la config de agenda vía PATCH /api/settings (patrón voice_ai) */
  const handleApptSave = async () => {
    if (!apptSettings) return;
    const { enabled, hours, duration_min_default, reminder_hours_before } = apptSettings;
    if (hours.open >= hours.close) {
      notify("La hora de apertura debe ser anterior al cierre", "error");
      return;
    }
    setApptSaving(true);
    try {
      const saved = await patchAppointmentSettings({
        enabled,
        hours: { open: hours.open, close: hours.close },
        duration_min_default,
        reminder_hours_before,
      });
      setApptSettings(saved);
      notify("Configuración de agenda guardada");
    } catch {
      notify("Error al guardar la agenda", "error");
    } finally {
      setApptSaving(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      <h2 className="text-xl font-bold">⚙️ Configuración</h2>

      {message && (
        <div className={`card border-2 text-sm animate-fade-in ${
          messageType === "success"
            ? "border-brand-success/30 bg-brand-success/5 text-brand-success"
            : "border-brand-error/30 bg-brand-error/5 text-brand-error"
        }`}>
          {message}
        </div>
      )}

      {/* Paleta actual */}
      <div className="card">
        <h3 className="font-bold text-brand-text-primary mb-2">🎨 Paleta de Colores</h3>
        <p className="text-sm text-brand-text-secondary mb-4">
          Configurá los colores de la interfaz para tu empresa. Los cambios se aplican al instante.
        </p>

        {/* Predefined palettes */}
        <div className="mb-6">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-brand-text-secondary mb-2">
            Paletas predefinidas
          </h4>
          <div className="flex flex-wrap gap-2">
            {presets.map((preset) => (
              <button
                key={preset.name}
                onClick={() => handlePreset(preset)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-200 
                           hover:border-brand-primary hover:shadow-sm transition-all text-sm"
              >
                <div className="flex gap-0.5">
                  <span className="w-3 h-3 rounded-full" style={{ background: preset.primary }} />
                  <span className="w-3 h-3 rounded-full" style={{ background: preset.secondary }} />
                  <span className="w-3 h-3 rounded-full" style={{ background: preset.accent }} />
                </div>
                {preset.name}
              </button>
            ))}
          </div>
        </div>

        {/* Color pickers */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {PALETTE_KEYS.map(({ key, label, cssVar }) => {
            const color = palette?.[key] ?? "#000";
            return (
              <div key={key} className="flex items-start gap-3 p-2.5 rounded-lg hover:bg-gray-50">
                <input
                  type="color"
                  value={color}
                  onChange={(e) => handleColorChange(key, e.target.value)}
                  className="w-9 h-9 rounded border border-gray-300 cursor-pointer shrink-0 mt-0.5"
                />
                <div className="flex-1 min-w-0 space-y-1">
                  <div className="text-sm font-medium text-brand-text-primary">
                    {label}
                  </div>
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                    <code className="text-[11px] text-brand-text-secondary bg-gray-100 px-1.5 py-0.5 rounded font-mono">
                      {color}
                    </code>
                    <span className="text-[10px] text-brand-text-secondary/60">
                      {cssVar}
                    </span>
                  </div>
                </div>
                <div
                  className="w-7 h-7 rounded ring-1 ring-black/10 shrink-0"
                  style={{ background: color }}
                  title={label}
                />
              </div>
            );
          })}
        </div>
      </div>

      {/* Company info */}
      {settings && (
        <div className="card">
          <h3 className="font-bold text-brand-text-primary mb-4">🏢 Información de la Empresa</h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <InfoRow label="Moneda" value={settings.currency} />
            <InfoRow label="Zona Horaria" value={settings.timezone} />
            <InfoRow label="Formato de Fecha" value={settings.date_format} />
            <InfoRow label="Logo" value={settings.logo_url ?? "No configurado"} />
          </div>
        </div>
      )}

      {/* F6 (Spec 07 D3): Agenda de Citas — solo restaurante */}
      {businessType === "restaurant" && (
        <div className="card">
          <h3 className="font-bold text-brand-text-primary mb-2">📅 Agenda de Citas</h3>
          <p className="text-sm text-brand-text-secondary mb-4">
            Configurá la ventana de reservas del local (D3 — independiente del horario del
            salón y del delivery). Default: 12:00–23:00, duración 60 min, recordatorio 24h antes.
          </p>

          {!apptSettings ? (
            <p className="text-xs text-gray-400">Cargando configuración…</p>
          ) : (
            <div className="space-y-4">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={apptSettings.enabled}
                  onChange={(e) =>
                    setApptSettings({ ...apptSettings, enabled: e.target.checked })
                  }
                  className="h-4 w-4 rounded border-gray-300 text-brand-primary"
                />
                <span className="font-medium text-brand-text-primary">
                  Agenda de citas habilitada
                </span>
              </label>

              <div className="grid grid-cols-2 gap-3">
                <label className="block text-xs text-gray-500">
                  Apertura de reservas
                  <input
                    type="time"
                    value={apptSettings.hours.open}
                    onChange={(e) =>
                      setApptSettings({
                        ...apptSettings,
                        hours: { ...apptSettings.hours, open: e.target.value },
                      })
                    }
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </label>
                <label className="block text-xs text-gray-500">
                  Cierre de reservas
                  <input
                    type="time"
                    value={apptSettings.hours.close}
                    onChange={(e) =>
                      setApptSettings({
                        ...apptSettings,
                        hours: { ...apptSettings.hours, close: e.target.value },
                      })
                    }
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </label>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <label className="block text-xs text-gray-500">
                  Duración default (min)
                  <input
                    type="number"
                    min={15}
                    max={240}
                    step={15}
                    value={apptSettings.duration_min_default}
                    onChange={(e) =>
                      setApptSettings({
                        ...apptSettings,
                        duration_min_default: Math.max(15, Number(e.target.value) || 60),
                      })
                    }
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </label>
                <label className="block text-xs text-gray-500">
                  Recordatorio (horas antes)
                  <input
                    type="number"
                    min={1}
                    max={72}
                    value={apptSettings.reminder_hours_before}
                    onChange={(e) =>
                      setApptSettings({
                        ...apptSettings,
                        reminder_hours_before: Math.max(1, Number(e.target.value) || 24),
                      })
                    }
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </label>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleApptSave}
                  disabled={apptSaving}
                  className="rounded-lg bg-brand-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                >
                  {apptSaving ? "Guardando…" : "Guardar agenda"}
                </button>
                <span className="text-xs text-gray-400">
                  Se persiste en <code className="font-mono">companies.settings.appointments</code>
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Live preview */}
      <div className="card">
        <h3 className="font-bold text-brand-text-primary mb-4">👁️ Vista Previa</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <PreviewBox color="primary" label="Primario" />
          <PreviewBox color="secondary" label="Secundario" />
          <PreviewBox color="accent" label="Acento" />
          <PreviewBox color="success" label="Éxito" />
          <PreviewBox color="warning" label="Advertencia" />
          <PreviewBox color="error" label="Error" />
          <PreviewBox color="background" label="Fondo" border />
          <PreviewBox color="surface" label="Superficie" border />
        </div>
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-xs text-brand-text-secondary">{label}</span>
      <div className="font-medium text-brand-text-primary">{value}</div>
    </div>
  );
}

function PreviewBox({
  color,
  label,
  border,
}: {
  color: string;
  label: string;
  border?: boolean;
}) {
  return (
    <div className="text-center">
      <div
        className={`h-14 rounded-lg mb-1.5 ${border ? "border border-gray-200" : ""}`}
        style={{ background: `var(--color-${color})` }}
      />
      <span className="text-xs text-brand-text-secondary">{label}</span>
    </div>
  );
}
