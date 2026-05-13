/**
 * usePosSession — Hook para gestionar sesiones de caja POS.
 *
 * Maneja estado de sesión actual, apertura, cierre y arqueo.
 *
 * HU-F2-008: UI de apertura y cierre de caja
 *
 * @module hooks/usePosSession
 */

import { useState, useEffect, useCallback } from "react";
import {
  getCurrentPosSession,
  openPosSession,
  closePosSession,
} from "@/services";
import type {
  PosSession,
  PosSessionOpenRequest,
  PosSessionCloseRequest,
  PosSessionCloseResponse,
} from "@/types";

export function usePosSession() {
  const [session, setSession] = useState<PosSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchSession = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const s = await getCurrentPosSession();
      setSession(s);
    } catch (err: unknown) {
      // 404 = no session active, that's normal
      const msg = err instanceof Error ? err.message : "";
      if (!msg.includes("404") && !msg.includes("No hay")) {
        setError(msg);
      }
      setSession(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSession();
  }, [fetchSession]);

  const open = useCallback(async (data: PosSessionOpenRequest) => {
    setActionLoading(true);
    setError(null);
    try {
      const s = await openPosSession(data);
      setSession(s);
      return s;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al abrir caja";
      setError(msg);
      throw err;
    } finally {
      setActionLoading(false);
    }
  }, []);

  const close = useCallback(
    async (data: PosSessionCloseRequest): Promise<PosSessionCloseResponse> => {
      if (!session) throw new Error("No hay sesión activa");
      setActionLoading(true);
      setError(null);
      try {
        const result = await closePosSession(session.id, data);
        setSession(null); // Session is now closed
        return result;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Error al cerrar caja";
        setError(msg);
        throw err;
      } finally {
        setActionLoading(false);
      }
    },
    [session],
  );

  return {
    session,
    isOpen: session !== null && session.status === "open",
    loading,
    actionLoading,
    error,
    refetch: fetchSession,
    open,
    close,
  };
}
