/**
 * Tests del parseo WS de callsApi — F2 (call.*) + F3 (ai_call_state,
 * call.transferred) — Spec 05 §3.5.3 / Spec 06 §3.5.2.
 *
 * Cubre el formato de envoltura real del backend
 * (`{"event": ..., "data": {...}}`) y el plano de la spec.
 */
import { parseCallWsMessage } from "@/services/callsApi";

describe("parseCallWsMessage — eventos F2 (regresión)", () => {
  it("parsea call.incoming con envoltura {event, data}", () => {
    const ev = parseCallWsMessage(
      JSON.stringify({
        event: "call.incoming",
        data: { id: 42, external_call_id: "ABC-1", caller: "+51999000001", callee: "100", started_at: "2026-08-13T20:00:00Z" },
      }),
    );
    expect(ev).toEqual({
      event: "call.incoming",
      id: 42,
      external_call_id: "ABC-1",
      caller: "+51999000001",
      callee: "100",
      direction: "", // s() devuelve "" cuando falta (comportamiento F2 existente)
      started_at: "2026-08-13T20:00:00Z",
    });
  });

  it("parsea call.incoming en formato plano de la spec", () => {
    const ev = parseCallWsMessage(
      JSON.stringify({ event: "call.incoming", external_call_id: "ABC-2", caller: "999", started_at: "2026-08-13T20:01:00Z" }),
    );
    expect(ev?.event).toBe("call.incoming");
    expect((ev as { external_call_id: string }).external_call_id).toBe("ABC-2");
  });

  it("devuelve null para JSON malformado y eventos desconocidos", () => {
    expect(parseCallWsMessage("no-json")).toBeNull();
    expect(parseCallWsMessage('{"event": "call.alien", "data": {}}')).toBeNull();
  });
});

describe("parseCallWsMessage — ai_call_state (F3, Spec 06 §3.5.2)", () => {
  it("normaliza el payload real del backend (envelope)", () => {
    const ev = parseCallWsMessage(
      JSON.stringify({
        event: "ai_call_state",
        data: {
          external_call_id: "ABC-1",
          call_record_id: 7,
          caller: "+51999000001",
          ai_state: "taking_order",
          duration_sec: 23,
          converted_order_id: null,
          transfer_reason: null,
          context_summary: "cliente pide 2 ceviches",
        },
      }),
    );
    expect(ev).toEqual({
      event: "ai_call_state",
      external_call_id: "ABC-1",
      call_record_id: 7,
      caller: "+51999000001",
      ai_state: "taking_order",
      duration_sec: 23,
      converted_order_id: null,
      transfer_reason: null,
      context_summary: "cliente pide 2 ceviches",
    });
  });

  it("acepta el formato plano {event, external_call_id, ...}", () => {
    const ev = parseCallWsMessage(
      JSON.stringify({ event: "ai_call_state", external_call_id: "ABC-3", ai_state: "transfer", transfer_reason: "user_requested" }),
    );
    expect(ev?.event).toBe("ai_call_state");
    expect((ev as { ai_state: string }).ai_state).toBe("transfer");
  });

  it("pone ai_state=null cuando el estado no está en AI_STATES (ignora corruptos)", () => {
    const ev = parseCallWsMessage(
      JSON.stringify({ event: "ai_call_state", data: { external_call_id: "ABC-4", ai_state: "hallucinating" } }),
    );
    expect(ev?.event).toBe("ai_call_state");
    expect((ev as { ai_state: string | null }).ai_state).toBeNull();
  });
});

describe("parseCallWsMessage — call.transferred (F3, Spec 06 §3.5.1/D9)", () => {
  it("normaliza el payload del bridge (envelope)", () => {
    const ev = parseCallWsMessage(
      JSON.stringify({
        event: "call.transferred",
        data: {
          external_call_id: "ABC-1",
          caller: "+51999000001",
          transfer_reason: "user_requested",
          context_summary: "cliente quiere hablar con persona",
          transferred_to: "6001",
          via: "sip",
          priority: "normal",
        },
      }),
    );
    expect(ev).toEqual({
      event: "call.transferred",
      external_call_id: "ABC-1",
      caller: "+51999000001",
      transfer_reason: "user_requested",
      context_summary: "cliente quiere hablar con persona",
      transferred_to: "6001",
      via: "sip",
      priority: "normal",
    });
  });

  it("acepta el formato plano con campos opcionales ausentes", () => {
    const ev = parseCallWsMessage(JSON.stringify({ event: "call.transferred", external_call_id: "ABC-5" }));
    expect(ev?.event).toBe("call.transferred");
    expect((ev as { transferred_to: string | null }).transferred_to).toBeNull();
    expect((ev as { via?: string }).via).toBeUndefined();
  });
});
