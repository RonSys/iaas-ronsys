/**
 * TicketPreview — Vista previa del ticket en formato texto.
 *
 * Renderiza el texto del ticket en <pre> monoespaciado.
 * También incluye botón de impresión.
 *
 * HU-F2-011: UI de listado de ventas con filtros + ticket
 *
 * @module components/sales/TicketPreview
 */

interface TicketPreviewProps {
  ticketText: string | null;
  loading: boolean;
  error: string | null;
  onPrint?: () => void;
  onClose: () => void;
}

export function TicketPreview({
  ticketText,
  loading,
  error,
  onPrint,
  onClose,
}: TicketPreviewProps) {
  const handlePrint = () => {
    if (onPrint) {
      onPrint();
    } else if (ticketText) {
      const w = window.open("", "_blank", "width=400,height=600");
      if (w) {
        w.document.write(`<pre style="font-family:monospace;font-size:12px;padding:16px;">${ticketText.replace(/\n/g, "<br>")}</pre>`);
        w.document.close();
        w.print();
      }
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 z-40 w-full md:w-96 bg-white shadow-2xl border-l overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 bg-white border-b px-4 py-3 flex items-center justify-between">
        <h3 className="font-bold text-brand-text-primary">🧾 Ticket</h3>
        <div className="flex gap-2">
          {ticketText && (
            <button
              onClick={handlePrint}
              className="px-3 py-1 text-xs rounded-lg bg-brand-primary text-white hover:opacity-90"
            >
              🖨️ Imprimir
            </button>
          )}
          <button
            onClick={onClose}
            className="px-3 py-1 text-xs rounded-lg border border-gray-300 text-brand-text-secondary hover:bg-gray-50"
          >
            Cerrar
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-brand-primary border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {error && (
          <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
            {error}
          </div>
        )}

        {ticketText && (
          <pre className="text-xs font-mono text-brand-text-primary bg-gray-50 p-3 rounded-lg border overflow-x-auto whitespace-pre-wrap leading-relaxed">
            {ticketText}
          </pre>
        )}

        {!loading && !error && !ticketText && (
          <p className="text-sm text-brand-text-secondary text-center py-12">
            No hay ticket disponible
          </p>
        )}
      </div>
    </div>
  );
}
