import axios from 'axios'
import type { SimulationData, NetworkSummary } from './store'

const BASE = 'http://127.0.0.1:8000'

const client = axios.create({
  baseURL: BASE,
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
})

export async function fetchNetworkSummary(): Promise<NetworkSummary> {
  const res = await client.get('/')
  return res.data.summary
}

export async function fetchDemoScenario() {
  const res = await client.get('/api/v1/simulation/demo-scenario')
  return res.data
}

export interface SimPayload {
  lat             : number
  lon             : number
  radius_m        : number
  route_start_lat : number
  route_start_lon : number
  route_end_lat   : number
  route_end_lon   : number
  max_snap_dist_m?: number
}

export async function runSimulation(payload: SimPayload): Promise<SimulationData> {
  const res = await client.post('/api/v1/simulation/simulate', {
    ...payload,
    max_snap_dist_m: payload.max_snap_dist_m ?? 3000,
  })
  return res.data
}

export async function getRoute(
  startLat: number, startLon: number,
  endLat  : number, endLon  : number,
  weightType = 'travel_time'
) {
  const res = await client.post('/api/v1/routing/route', {
    start_lat       : startLat,
    start_lon       : startLon,
    end_lat         : endLat,
    end_lon         : endLon,
    weight_type     : weightType,
    max_snap_dist_m : 3000,
  })
  return res.data
}