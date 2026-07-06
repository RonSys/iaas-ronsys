/**
 * Scenario types — Persistencia de escenarios del simulador.
 *
 * HU-SIM-002: UI de Escenarios Persistente
 *
 * @module types/scenario
 */

export interface Scenario {
  id: number;
  company_id: number;
  name: string;
  input_data: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface ScenarioCreateRequest {
  name: string;
  input_data: Record<string, any>;
}

export interface ScenarioUpdateRequest {
  name?: string;
  input_data?: Record<string, any>;
}
