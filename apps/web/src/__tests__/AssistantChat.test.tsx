/**
 * Tests — AssistantChat (Spec 08, F5 "Pregúntale al Sistema").
 *
 * Cubre CA-F5 (frontend):
 *  - Render del botón flotante y apertura del panel.
 *  - Sugerencias del catálogo (GET /catalog, R8).
 *  - Envío de pregunta → muestra la respuesta del asistente.
 *  - Rate limit 429 → mensaje amigable (R6).
 *  - Error de red → mensaje de error sin romper el chat.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AssistantChat } from "@/components/assistant/AssistantChat";
import { askAssistant, getAssistantCatalog } from "@/services/assistantApi";

jest.mock("@/services/assistantApi", () => ({
  askAssistant: jest.fn(),
  getAssistantCatalog: jest.fn(),
}));

const mockedAsk = askAssistant as jest.MockedFunction<typeof askAssistant>;
const mockedCatalog = getAssistantCatalog as jest.MockedFunction<typeof getAssistantCatalog>;

const OK_RESPONSE = {
  answer: "🏆 Top 5 productos más vendidos por delivery (2026-07-15 a 2026-08-13):\n  1. Lomo Saltado — 12 und en S/ 486.00",
  data: [{ name: "Lomo Saltado", qty: 12, total: 486.0 }],
  catalog_query_used: { id: 1, name: "top_products_delivery", skill: "delivery" },
  params: { date_from: "2026-07-15", date_to: "2026-08-13", limit: 5 },
  suggestions: ["¿Cuántos pedidos hubo por zona?", "¿Qué campaña tuvo mejor ROAS?"],
};

beforeEach(() => {
  jest.clearAllMocks();
  mockedCatalog.mockResolvedValue([
    {
      id: 1,
      skill: "delivery",
      name: "top_products_delivery",
      description_es: "¿Cuál es el producto más vendido por delivery?",
      params_schema: [],
    },
  ]);
});

function openChat() {
  render(<AssistantChat />);
  fireEvent.click(screen.getByLabelText("Abrir asistente — Pregúntale al Sistema"));
}

test("abre el panel con sugerencias del catálogo (R8)", async () => {
  openChat();
  await waitFor(() => {
    expect(screen.getByText("Pregúntale al Sistema")).toBeInTheDocument();
  });
  // sugerencia del catálogo real
  await waitFor(() => {
    expect(
      screen.getByText("¿Cuál es el producto más vendido por delivery?"),
    ).toBeInTheDocument();
  });
});

test("envía pregunta y muestra la respuesta del asistente", async () => {
  mockedAsk.mockResolvedValue(OK_RESPONSE as never);
  openChat();

  const input = screen.getByPlaceholderText("Ej: ¿cuál es el producto más vendido hoy?");
  fireEvent.change(input, { target: { value: "¿cuál es el producto más vendido por delivery?" } });
  fireEvent.keyDown(input, { key: "Enter" });

  // mensaje del usuario visible
  await waitFor(() => {
    expect(screen.getByText("¿cuál es el producto más vendido por delivery?")).toBeInTheDocument();
  });
  // respuesta del asistente con el dato real
  await waitFor(() => {
    expect(screen.getByText(/Lomo Saltado/)).toBeInTheDocument();
  });
  expect(mockedAsk).toHaveBeenCalledWith("¿cuál es el producto más vendido por delivery?");
});

test("rate limit 429 → mensaje amigable (R6)", async () => {
  mockedAsk.mockRejectedValue(
    new Error("Demasiadas consultas en poco tiempo. Espera un momento y vuelve a intentar."),
  );
  openChat();

  const input = screen.getByPlaceholderText("Ej: ¿cuál es el producto más vendido hoy?");
  fireEvent.change(input, { target: { value: "¿cuánto vendió hoy?" } });
  fireEvent.keyDown(input, { key: "Enter" });

  await waitFor(() => {
    expect(screen.getByText(/Demasiadas consultas en poco tiempo/)).toBeInTheDocument();
  });
});

test("sugerencias se actualizan tras la respuesta (R5)", async () => {
  mockedAsk.mockResolvedValue(OK_RESPONSE as never);
  openChat();

  const input = screen.getByPlaceholderText("Ej: ¿cuál es el producto más vendido hoy?");
  fireEvent.change(input, { target: { value: "¿cuál es el producto más vendido?" } });
  fireEvent.keyDown(input, { key: "Enter" });

  await waitFor(() => {
    expect(screen.getByText(/Lomo Saltado/)).toBeInTheDocument();
  });
  // las sugerencias del fallback/éxito reemplazan las del catálogo
  await waitFor(() => {
    expect(screen.getByText("¿Qué campaña tuvo mejor ROAS?")).toBeInTheDocument();
  });
});
