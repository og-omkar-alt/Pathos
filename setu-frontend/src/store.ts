import { create } from 'zustand'

export type Page = 'landing' | 'dashboard'

export interface SimulationResult {
  disconnected_wards   : number
  population_affected  : number
  connectivity_before  : number
  connectivity_after   : number
  resilience_before    : number
  resilience_after     : number
  priority_score       : number
  emergency_priority   : 'CRITICAL' | 'HIGH' | 'MEDIUM'
  edges_removed        : number
  nodes_in_zone        : number
}

export interface RouteMetrics {
  distance_km               : number
  estimated_time_mins        : number
  avg_congestion_multiplier  : number
  segments_count             : number
}

export interface RouteData {
  status      : string
  route_coords: [number, number][]
  metrics     : RouteMetrics
  detour_km?  : number
  detour_mins?: number
  message?    : string
}

export interface FailedSegment {
  id          : string
  criticality : string
  score       : number
  length_m    : number
  coordinates : [number, number][]
}

export interface SimulationData {
  status            : string
  simulation_result : SimulationResult
  failed_segments   : FailedSegment[]
  normal_route      : RouteData
  safe_route        : RouteData
}

export interface NetworkSummary {
  nodes      : number
  edges      : number
  components : number
  total_km   : number
}

interface SetuStore {
  page        : Page
  setPage     : (p: Page) => void

  networkSummary    : NetworkSummary | null
  setNetworkSummary : (s: NetworkSummary) => void

  // Input state
  lat       : number | null
  lon       : number | null
  radiusM   : number
  originLat : number | null
  originLon : number | null
  destLat   : number | null
  destLon   : number | null

  setLat       : (v: number) => void
  setLon       : (v: number) => void
  setRadiusM   : (v: number) => void
  setOriginLat : (v: number) => void
  setOriginLon : (v: number) => void
  setDestLat   : (v: number) => void
  setDestLon   : (v: number) => void

  // Map click mode
  clickMode    : 'incident' | 'origin' | 'destination' | null
  setClickMode : (m: 'incident' | 'origin' | 'destination' | null) => void

  // Simulation
  isSimulating   : boolean
  simData        : SimulationData | null
  setIsSimulating: (v: boolean) => void
  setSimData     : (d: SimulationData | null) => void

  // CLI log
  cliLines    : string[]
  addCliLine  : (line: string) => void
  clearCli    : () => void
}

export const useStore = create<SetuStore>((set) => ({
  page    : 'landing',
  setPage : (p) => set({ page: p }),

  networkSummary    : null,
  setNetworkSummary : (s) => set({ networkSummary: s }),

  // Vasna defaults — verified working with OSM graph
  lat       : null,
  lon       : null,
  radiusM   : 800,
  originLat : null,
  originLon : null,
  destLat   : null,
  destLon   : null,

  setLat       : (v) => set({ lat: v }),
  setLon       : (v) => set({ lon: v }),
  setRadiusM   : (v) => set({ radiusM: v }),
  setOriginLat : (v) => set({ originLat: v }),
  setOriginLon : (v) => set({ originLon: v }),
  setDestLat   : (v) => set({ destLat: v }),
  setDestLon   : (v) => set({ destLon: v }),

  clickMode    : null,
  setClickMode : (m) => set({ clickMode: m }),

  isSimulating   : false,
  simData        : null,
  setIsSimulating: (v) => set({ isSimulating: v }),
  setSimData     : (d) => set({ simData: d }),

  cliLines   : ['SETU_CLI v2.0 — System ready.', 'Awaiting command...'],
  addCliLine : (line) => set((s) => ({
    cliLines: [...s.cliLines.slice(-6), line]
  })),
  clearCli   : () => set({ cliLines: ['SETU_CLI v2.0 — System ready.'] }),
}))