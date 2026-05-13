/**
 * Tests for useScenarios hook — CRUD de escenarios.
 *
 * HU-SIM-002: UI de Escenarios Persistente
 */
import { renderHook, act, waitFor } from "@testing-library/react";
import { useScenarios } from "@/hooks/useScenarios";

jest.mock("@/services", () => ({
  getScenarios: jest.fn(),
  createScenario: jest.fn(),
  updateScenario: jest.fn(),
  deleteScenario: jest.fn(),
  __esModule: true,
}));

import {
  getScenarios,
  createScenario,
  deleteScenario,
} from "@/services";

const mockedGet = getScenarios as jest.MockedFunction<typeof getScenarios>;
const mockedCreate = createScenario as jest.MockedFunction<typeof createScenario>;
const mockedDelete = deleteScenario as jest.MockedFunction<typeof deleteScenario>;

describe("useScenarios", () => {
  beforeEach(() => jest.clearAllMocks());

  it("starts with isLoading=true and empty scenarios", () => {
    mockedGet.mockImplementation(() => new Promise(() => {}));
    const { result } = renderHook(() => useScenarios());
    expect(result.current.isLoading).toBe(true);
    expect(result.current.scenarios).toEqual([]);
    expect(result.current.error).toBeNull();
  });

  it("loads scenarios on mount", async () => {
    const mockScenarios = [
      {
        id: 1, company_id: 1, name: "Realista",
        input_data: { price: 28, platesPerDay: 40, costPct: 40, rent: 2500, salaries: 5000 },
        created_at: "2026-06-01T00:00:00Z", updated_at: "2026-06-01T00:00:00Z",
      },
      {
        id: 2, company_id: 1, name: "Optimista",
        input_data: { price: 35, platesPerDay: 60 },
        created_at: "2026-06-01T01:00:00Z", updated_at: "2026-06-01T01:00:00Z",
      },
    ];
    mockedGet.mockResolvedValue(mockScenarios);
    const { result } = renderHook(() => useScenarios());
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.scenarios).toHaveLength(2);
    expect(result.current.scenarios[0].name).toBe("Realista");
  });

  it("handles load error gracefully", async () => {
    mockedGet.mockRejectedValue(new Error("Network error"));
    const { result } = renderHook(() => useScenarios());
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBe("Network error");
  });

  it("ignores 404 on load", async () => {
    mockedGet.mockRejectedValue(new Error("404 Not Found"));
    const { result } = renderHook(() => useScenarios());
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBeNull();
    expect(result.current.scenarios).toEqual([]);
  });

  it("saves a scenario via POST and adds to list", async () => {
    mockedGet.mockResolvedValue([]);
    const created = {
      id: 1, company_id: 1, name: "Realista",
      input_data: { price: 28 },
      created_at: "2026-06-01T00:00:00Z", updated_at: "2026-06-01T00:00:00Z",
    };
    mockedCreate.mockResolvedValue(created);

    const { result } = renderHook(() => useScenarios());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    let savedId = 0;
    await act(async () => {
      const s = await result.current.saveScenario("Realista", { price: 28 });
      savedId = s.id;
    });

    expect(mockedCreate).toHaveBeenCalledWith({
      name: "Realista",
      input_data: { price: 28 },
    });
    expect(savedId).toBe(1);
    expect(result.current.scenarios).toHaveLength(1);
    expect(result.current.scenarios[0].name).toBe("Realista");
  });

  it("handles save error", async () => {
    mockedGet.mockResolvedValue([]);
    mockedCreate.mockRejectedValue(new Error("409 Conflict"));

    const { result } = renderHook(() => useScenarios());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      try {
        await result.current.saveScenario("X", {});
      } catch {
        // expected
      }
    });

    expect(result.current.error).toBe("409 Conflict");
  });

  it("deletes a scenario via DELETE and removes from list", async () => {
    mockedGet.mockResolvedValue([
      {
        id: 1, company_id: 1, name: "Realista",
        input_data: {}, created_at: "", updated_at: "",
      },
      {
        id: 2, company_id: 1, name: "Optimista",
        input_data: {}, created_at: "", updated_at: "",
      },
    ]);
    mockedDelete.mockResolvedValue(undefined);

    const { result } = renderHook(() => useScenarios());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.deleteScenario(1);
    });

    expect(mockedDelete).toHaveBeenCalledWith(1);
    expect(result.current.scenarios).toHaveLength(1);
    expect(result.current.scenarios[0].name).toBe("Optimista");
  });
});
