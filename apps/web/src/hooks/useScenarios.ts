/**
 * useScenarios — Hook para CRUD de escenarios del simulador.
 *
 * HU-SIM-002: UI de Escenarios Persistente
 *
 * @module hooks/useScenarios
 */
import { useState, useEffect, useCallback } from "react";
import {
  getScenarios,
  createScenario,
  updateScenario,
  deleteScenario as deleteScenarioApi,
} from "@/services";
import type { Scenario } from "@/types";

export function useScenarios() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const fetchScenarios = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getScenarios();
      setScenarios(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error cargando escenarios";
      // 404 is fine — no scenarios yet
      if (!msg.includes("404")) setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { fetchScenarios(); }, [fetchScenarios]);

  const saveScenario = useCallback(async (name: string, inputData: Record<string, any>) => {
    setIsSaving(true);
    setError(null);
    try {
      const created = await createScenario({ name, input_data: inputData });
      setScenarios((prev) => [...prev, created]);
      return created;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error guardando escenario";
      setError(msg);
      throw err;
    } finally {
      setIsSaving(false);
    }
  }, []);

  const editScenario = useCallback(async (id: number, name: string, inputData: Record<string, any>) => {
    setIsSaving(true);
    setError(null);
    try {
      const updated = await updateScenario(id, { name, input_data: inputData });
      setScenarios((prev) => prev.map((s) => (s.id === id ? updated : s)));
      return updated;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error actualizando escenario";
      setError(msg);
      throw err;
    } finally {
      setIsSaving(false);
    }
  }, []);

  const removeScenario = useCallback(async (id: number) => {
    setIsSaving(true);
    setError(null);
    try {
      await deleteScenarioApi(id);
      setScenarios((prev) => prev.filter((s) => s.id !== id));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error eliminando escenario";
      setError(msg);
      throw err;
    } finally {
      setIsSaving(false);
    }
  }, []);

  return {
    scenarios,
    isLoading,
    error,
    isSaving,
    fetchScenarios,
    saveScenario,
    updateScenario: editScenario,
    deleteScenario: removeScenario,
  };
}
