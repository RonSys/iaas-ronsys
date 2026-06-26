/**
 * PosPage — Página de gestión de caja (POS Session).
 *
 * Muestra:
 * - Si no hay sesión: PosSessionOpen
 * - Si hay sesión: PosSessionStatus + botón cerrar → PosSessionClose modal
 *
 * HU-F2-008: UI de apertura y cierre de caja
 *
 * @module pages/Pos
 */
import { useState, useCallback } from "react";
import { usePosSession } from "@/hooks/usePosSession";
import { PosSessionOpen } from "@/components/pos/PosSessionOpen";
import { PosSessionStatus } from "@/components/pos/PosSessionStatus";
import { PosSessionClose } from "@/components/pos/PosSessionClose";
import { Skeleton } from "@/components/dashboard/KPICard";

export function PosPage() {
  const {
    session,
    isOpen,
    loading,
    actionLoading,
    error,
    open,
    close,
  } = usePosSession();

  const [showCloseModal, setShowCloseModal] = useState(false);

  const handleOpen = useCallback(
    async (openingCash: number) => {
      await open({ opening_cash: openingCash });
    },
    [open],
  );

  const handleClose = useCallback(
    async (closingCash: number, notes: string) => {
      const result = await close({ closing_cash: closingCash, notes });
      return result;
    },
    [close],
  );

  const handleCloseRequest = () => {
    setShowCloseModal(true);
  };

  const handleCloseCancel = () => {
    setShowCloseModal(false);
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full max-w-md" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-brand-text-primary">
            💰 Caja
          </h2>
          <p className="text-sm text-brand-text-secondary">
            {isOpen ? "Sesión de caja activa" : "Abrí una nueva sesión de caja"}
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
          {error}
        </div>
      )}

      {isOpen && session ? (
        <PosSessionStatus
          session={session}
          onCloseRequest={handleCloseRequest}
        />
      ) : (
        <PosSessionOpen
          onSubmit={handleOpen}
          loading={actionLoading}
          error={error}
        />
      )}

      {/* Close Modal */}
      {showCloseModal && session && (
        <PosSessionClose
          expectedCash={(session.cash_sales ?? 0) + session.opening_cash}
          totalSales={session.total_sales ?? 0}
          onSubmit={handleClose}
          loading={actionLoading}
          error={error}
          onCancel={handleCloseCancel}
        />
      )}
    </div>
  );
}
