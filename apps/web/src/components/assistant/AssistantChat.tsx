/**
 * AssistantChat — "Pregúntale al Sistema" (Spec 08, F5).
 *
 * Chat flotante en el Panel del Dueño: el dueño pregunta en lenguaje natural
 * y el asistente responde con datos REALES del sistema (catálogo cerrado,
 * D1 — el LLM nunca escribe SQL).
 *
 * - Chips de sugerencias desde GET /api/v1/assistant/catalog (R8, rol)
 * - Respuesta con markdown-lite (negritas/emojis ya vienen en `answer`)
 * - Estado de escritura "…" mientras el backend responde
 * - Errores amigables: 429 (R6), 401/403, red
 * - Historial solo en memoria de la sesión (no persiste, Spec 08 §3.3)
 *
 * @component AssistantChat
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { askAssistant, getAssistantCatalog } from "@/services/assistantApi";
import type { AskResponse, CatalogItem, ChatMessage } from "@/types";

/** Preguntas rápidas de ejemplo si el catálogo aún carga o está vacío. */
const FALLBACK_SUGGESTIONS = [
  "¿Cuál es el producto más vendido por delivery?",
  "¿Cuántos pedidos hubo por zona?",
  "¿Qué campaña tuvo mejor ROAS?",
  "Resumen de delivery",
  "¿Cuántos pedidos se cancelaron?",
];

/** Render de la respuesta: respeta saltos de línea (lista por consulta). */
function AnswerText({ content }: { content: string }) {
  // Evita inyección de HTML: render como texto plano con <br> por línea
  return (
    <div className="whitespace-pre-wrap break-words text-sm leading-relaxed">
      {content}
    </div>
  );
}

export function AssistantChat() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>(FALLBACK_SUGGESTIONS);
  const [thinking, setThinking] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  // Cargar catálogo → sugerencias reales del rol (R8)
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    getAssistantCatalog()
      .then((items: CatalogItem[]) => {
        if (cancelled) return;
        if (items.length > 0) {
          setSuggestions(items.slice(0, 5).map((i) => i.description_es));
        }
      })
      .catch(() => {
        /* catálogo no disponible → se mantienen las sugerencias por defecto */
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  // Auto-scroll al último mensaje (defensivo: jsdom no implementa scrollTo)
  useEffect(() => {
    const el = listRef.current;
    if (el && typeof el.scrollTo === "function") {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    } else if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages, thinking]);

  const send = useCallback(
    async (text: string) => {
      const question = text.trim();
      if (!question || thinking) return;
      setInput("");
      setMessages((prev) => [...prev, { role: "user", content: question }]);
      setThinking(true);
      try {
        const res: AskResponse = await askAssistant(question);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: res.answer, data: res.data },
        ]);
        if (res.suggestions && res.suggestions.length > 0) {
          setSuggestions(res.suggestions);
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Error al consultar al sistema.";
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `⚠️ ${msg}`,
          },
        ]);
      } finally {
        setThinking(false);
      }
    },
    [thinking],
  );

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      void send(input);
    }
  };

  return (
    <>
      {/* Botón flotante */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Cerrar asistente" : "Abrir asistente — Pregúntale al Sistema"}
        title="Pregúntale al Sistema (Spec 08, F5)"
        className="fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-brand-primary to-indigo-600 text-2xl shadow-xl shadow-brand-primary/30 transition-transform hover:scale-105 active:scale-95"
      >
        {open ? "✕" : "🤖"}
        {!open && messages.length > 0 && (
          <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
            {messages.length}
          </span>
        )}
      </button>

      {/* Panel del chat */}
      {open && (
        <div className="fixed bottom-24 right-6 z-40 flex h-[560px] max-h-[70vh] w-[380px] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border border-slate-700 bg-slate-900/95 shadow-2xl backdrop-blur animate-fade-in">
          {/* Header */}
          <div className="flex items-center gap-2 border-b border-slate-700 bg-slate-800/80 px-4 py-3">
            <span className="text-xl">🤖</span>
            <div className="min-w-0 flex-1">
              <h3 className="text-sm font-bold text-slate-100">Pregúntale al Sistema</h3>
              <p className="text-[10px] text-slate-400">
                Datos reales del negocio · catálogo seguro
              </p>
            </div>
          </div>

          {/* Mensajes */}
          <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
            {messages.length === 0 && (
              <div className="mt-4 text-center text-xs text-slate-500">
                <div className="mb-1 text-2xl">👋</div>
                <p>Pregunta en lenguaje natural, por ejemplo:</p>
              </div>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                className={`max-w-[85%] rounded-2xl px-3 py-2 ${
                  m.role === "user"
                    ? "ml-auto bg-brand-primary text-white"
                    : "mr-auto bg-slate-800 border border-slate-700 text-slate-100"
                }`}
              >
                <AnswerText content={m.content} />
              </div>
            ))}
            {thinking && (
              <div className="mr-auto max-w-[85%] rounded-2xl border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-400">
                <span className="inline-flex gap-1">
                  <span className="animate-bounce">•</span>
                  <span className="animate-bounce [animation-delay:120ms]">•</span>
                  <span className="animate-bounce [animation-delay:240ms]">•</span>
                </span>
                <span className="ml-1">Consultando al sistema…</span>
              </div>
            )}
          </div>

          {/* Sugerencias: bienvenida (vacío) o seguimiento tras respuesta del asistente */}
          {(messages.length === 0 || messages[messages.length - 1]?.role === "assistant") &&
            suggestions.length > 0 && (
              <div className="flex flex-wrap gap-1.5 border-t border-slate-700/60 px-3 py-2">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => void send(s)}
                    className="rounded-full border border-brand-primary/40 bg-brand-primary/10 px-2.5 py-1 text-[11px] text-brand-primary transition-colors hover:bg-brand-primary/20"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}

          {/* Input */}
          <div className="border-t border-slate-700 bg-slate-800/60 p-3">
            <div className="flex items-center gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="Ej: ¿cuál es el producto más vendido hoy?"
                maxLength={500}
                className="min-w-0 flex-1 rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-brand-primary focus:outline-none"
              />
              <button
                type="button"
                onClick={() => void send(input)}
                disabled={thinking || !input.trim()}
                className="rounded-lg bg-brand-primary px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-primary/90 disabled:opacity-40"
              >
                ➤
              </button>
            </div>
            <p className="mt-1.5 text-[10px] text-slate-500">
              El asistente solo consulta el catálogo seguro de delivery (R1/R7).
            </p>
          </div>
        </div>
      )}
    </>
  );
}
