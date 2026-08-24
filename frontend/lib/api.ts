/**
 * SETU Frontend — Centralized API Service
 * All backend communication goes through this module.
 * Backend: FastAPI running at http://127.0.0.1:8000
 */

const API_BASE = 'http://127.0.0.1:8000';

// ── Types ────────────────────────────────────────────────────────────────────

export interface NetworkSummary {
  nodes: number;
  edges: number;
  components: number;
  total_km: number;
  mean_degree: number;
  connectivity: number;
  resilience: number;
  breaks_per_km: number;
  largest_component: number;
  avg_congestion: number;
}

export interface RouteMetrics {
  distance_km: number;
  estimated_time_mins: number;
  avg_congestion_multiplier: number;
  segments_count: number;
}

export interface RouteResult {
  status: 'success' | 'warning' | 'error';
  message?: string;
  route_coords: [number, number][]; // [lat, lon][]
  metrics: RouteMetrics;
}

export interface SimulationBackendResult {
  disconnected_wards: number;
  population_affected: number;
  hospitals_impacted: number;
  connectivity_before: number;
  connectivity_after: number;
  resilience_before: number;
  resilience_after: number;
  priority_score: number;
  emergency_priority: string;
}

export interface CriticalSegment {
  id: string;
  name: string;
  criticality: string;
  score: number;
}

export interface SimulationApiResponse {
  status: string;
  simulation_result: SimulationBackendResult;
  critical_segments_list: CriticalSegment[];
}

export interface GeocodeResult {
  lat: number;
  lon: number;
  display_name: string;
}

export interface GeoJSONFeature {
  type: 'Feature';
  geometry: {
    type: string;
    coordinates: number[][];
  };
  properties: {
    id: string;
    name: string;
    length_m: number;
    congestion_level: number;
    criticality: string;
    criticalityScore: number;
  };
}

export interface GeoJSONFeatureCollection {
  type: 'FeatureCollection';
  features: GeoJSONFeature[];
}

// ── API Functions ────────────────────────────────────────────────────────────

export async function fetchHealthCheck(): Promise<{ status: string; system: string; summary: any }> {
  const res = await fetch(`${API_BASE}/`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}

export async function fetchNetworkSummary(): Promise<NetworkSummary> {
  const res = await fetch(`${API_BASE}/api/v1/network/summary`);
  if (!res.ok) throw new Error(`Network summary failed: ${res.status}`);
  return res.json();
}

export async function fetchNetworkEdgesGeoJSON(): Promise<GeoJSONFeatureCollection> {
  const res = await fetch(`${API_BASE}/api/v1/network/edges`);
  if (!res.ok) throw new Error(`Network edges failed: ${res.status}`);
  return res.json();
}

export async function fetchRoute(
  startLat: number, startLon: number,
  endLat: number, endLon: number,
  weightType: string = 'travel_time',
  maxSnapDistM: number = 2000.0
): Promise<RouteResult> {
  const res = await fetch(`${API_BASE}/api/v1/routing/route`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      start_lat: startLat,
      start_lon: startLon,
      end_lat: endLat,
      end_lon: endLon,
      weight_type: weightType,
      max_snap_dist_m: maxSnapDistM,
    }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => 'Unknown error');
    throw new Error(`Route failed (${res.status}): ${detail}`);
  }
  return res.json();
}

export async function fetchSimulation(
  lat: number = 23.0063,
  lon: number = 72.5510,
  radiusM: number = 800.0
): Promise<SimulationApiResponse> {
  const res = await fetch(`${API_BASE}/api/v1/simulation/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ lat, lon, radius_m: radiusM }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => 'Unknown error');
    throw new Error(`Simulation failed (${res.status}): ${detail}`);
  }
  return res.json();
}

export async function geocodeArea(query: string): Promise<GeocodeResult> {
  const res = await fetch(`${API_BASE}/api/v1/geocode?q=${encodeURIComponent(query)}`);
  if (!res.ok) {
    if (res.status === 404) throw new Error(`Could not locate "${query}"`);
    throw new Error(`Geocoding failed: ${res.status}`);
  }
  return res.json();
}
