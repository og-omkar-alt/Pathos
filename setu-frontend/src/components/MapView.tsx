import { useEffect, useRef } from 'react'
import * as maplibregl from 'maplibre-gl'
import { useStore } from '../store'

const EMPTY: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] }

const toLonLat = (c: [number, number]): [number, number] =>
  c[0] > 40 ? [c[0], c[1]] : [c[1], c[0]]

export default function MapView() {
  const mapContainer = useRef<HTMLDivElement>(null)
  const mapRef       = useRef<maplibregl.Map | null>(null)
  const loaded       = useRef(false)
  const markers      = useRef<maplibregl.Marker[]>([])

  const {
    simData, clickMode,
    lat, lon,
  } = useStore()

  // ── Init map ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '© OpenStreetMap contributors',
          },
        },
        layers: [
          { id: 'bg', type: 'background', paint: { 'background-color': '#06060a' } },
          {
            id: 'osm', type: 'raster', source: 'osm',
            minzoom: 0, maxzoom: 20,
            paint: {
              'raster-brightness-min': 0,
              'raster-brightness-max': 0.22,
              'raster-saturation':    -0.85,
              'raster-contrast':       0.1,
              'raster-opacity':        0.85,
            },
          },
        ],
        glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
      },
      center: [72.5588, 23.0089],
      zoom: 12,
      attributionControl: false,
    })
    mapRef.current = map

    map.on('load', () => {
      // Failed roads
      map.addSource('failed-roads', { type: 'geojson', data: EMPTY })
      map.addLayer({
        id: 'failed-glow', type: 'line', source: 'failed-roads',
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': '#ef4444', 'line-width': 14, 'line-opacity': 0.18, 'line-blur': 6 },
      })
      map.addLayer({
        id: 'failed-line', type: 'line', source: 'failed-roads',
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': '#ef4444', 'line-width': 4, 'line-opacity': 1, 'line-dasharray': [2, 2] },
      })

      // Normal route (grey dashed)
      map.addSource('normal-route', { type: 'geojson', data: EMPTY })
      map.addLayer({
        id: 'normal-line', type: 'line', source: 'normal-route',
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': '#94a3b8', 'line-width': 3, 'line-opacity': 0.9, 'line-dasharray': [4, 3] },
      })

      // Safe route (cyan)
      map.addSource('safe-route', { type: 'geojson', data: EMPTY })
      map.addLayer({
        id: 'safe-glow', type: 'line', source: 'safe-route',
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': '#00f2fe', 'line-width': 18, 'line-opacity': 0.15, 'line-blur': 8 },
      })
      map.addLayer({
        id: 'safe-line', type: 'line', source: 'safe-route',
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': '#00f2fe', 'line-width': 4, 'line-opacity': 1 },
      })

      // Route markers
      map.addSource('route-markers', { type: 'geojson', data: EMPTY })
      map.addLayer({
        id: 'route-markers-circle', type: 'circle', source: 'route-markers',
        paint: {
          'circle-color'       : ['get', 'color'],
          'circle-radius'      : 8,
          'circle-stroke-width': 2,
          'circle-stroke-color': '#ffffff',
        },
      })

      loaded.current = true
    })

    // Map click handler
    map.on('click', (e) => {
      const { lng, lat: clat } = e.lngLat
      const mode = useStore.getState().clickMode
      if (!mode) return

      const newLat = parseFloat(clat.toFixed(4))
      const newLon = parseFloat(lng.toFixed(4))

      if (mode === 'incident') {
        useStore.getState().setLat(newLat)
        useStore.getState().setLon(newLon)
        // Auto-set origin north and destination south of failure zone
        useStore.getState().setOriginLat(parseFloat((newLat + 0.02).toFixed(4)))
        useStore.getState().setOriginLon(parseFloat((newLon).toFixed(4)))
        useStore.getState().setDestLat(parseFloat((newLat - 0.02).toFixed(4)))
        useStore.getState().setDestLon(parseFloat((newLon).toFixed(4)))
      } else if (mode === 'origin') {
        useStore.getState().setOriginLat(newLat)
        useStore.getState().setOriginLon(newLon)
      } else if (mode === 'destination') {
        useStore.getState().setDestLat(newLat)
        useStore.getState().setDestLon(newLon)
      }
      useStore.getState().setClickMode(null)
    })

    // Cursor change based on click mode
    const unsub = useStore.subscribe((state) => {
      if (!mapRef.current) return
      mapRef.current.getCanvas().style.cursor = state.clickMode ? 'crosshair' : ''
    })

    return () => {
      unsub()
      map.remove()
      mapRef.current  = null
      loaded.current  = false
    }
  }, [])

  // ── Fly to new incident location when lat/lon changes ──────────────────
  useEffect(() => {
    const map = mapRef.current
    if (!map || !loaded.current) return
    map.flyTo({ center: [lon, lat], zoom: 13, duration: 800 })
  }, [lat, lon])

  // ── Draw simulation results ───────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    const draw = () => {
      // Clear old markers
      markers.current.forEach(m => m.remove())
      markers.current = []

      if (!simData) {
        ;(map.getSource('failed-roads')  as maplibregl.GeoJSONSource)?.setData(EMPTY)
        ;(map.getSource('normal-route')  as maplibregl.GeoJSONSource)?.setData(EMPTY)
        ;(map.getSource('safe-route')    as maplibregl.GeoJSONSource)?.setData(EMPTY)
        ;(map.getSource('route-markers') as maplibregl.GeoJSONSource)?.setData(EMPTY)
        return
      }

      const { failed_segments, normal_route, safe_route } = simData

      // Failed segments
      if (failed_segments?.length > 0) {
        ;(map.getSource('failed-roads') as maplibregl.GeoJSONSource)?.setData({
          type: 'FeatureCollection',
          features: failed_segments.map(seg => ({
            type: 'Feature',
            properties: { criticality: seg.criticality },
            geometry: {
              type: 'LineString',
              coordinates: seg.coordinates.map(toLonLat),
            },
          })),
        })
      }

      // Normal route
      if (normal_route?.route_coords?.length > 1) {
        const coords = (normal_route.route_coords as [number,number][]).map(toLonLat)
        ;(map.getSource('normal-route') as maplibregl.GeoJSONSource)?.setData({
          type: 'FeatureCollection',
          features: [{ type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: coords } }],
        })
      }

      // Safe route
      if (safe_route?.route_coords?.length > 1) {
        const safeCoords = (safe_route.route_coords as [number,number][]).map(toLonLat)
        ;(map.getSource('safe-route') as maplibregl.GeoJSONSource)?.setData({
          type: 'FeatureCollection',
          features: [{ type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: safeCoords } }],
        })

        // Start + end markers
        ;(map.getSource('route-markers') as maplibregl.GeoJSONSource)?.setData({
          type: 'FeatureCollection',
          features: [
            { type: 'Feature', properties: { color: '#10b981' }, geometry: { type: 'Point', coordinates: safeCoords[0] } },
            { type: 'Feature', properties: { color: '#ef4444' }, geometry: { type: 'Point', coordinates: safeCoords[safeCoords.length - 1] } },
          ],
        })

        // Fit camera to full scene
        const bounds = new maplibregl.LngLatBounds()
        safeCoords.forEach(c => bounds.extend(c))
        if (normal_route?.route_coords?.length > 1) {
          (normal_route.route_coords as [number,number][]).map(toLonLat).forEach(c => bounds.extend(c))
        }
        if (failed_segments?.length > 0) {
          failed_segments.forEach(seg =>
            seg.coordinates.forEach(c => bounds.extend(toLonLat(c)))
          )
        }
        map.fitBounds(bounds, { padding: 80, duration: 1200, maxZoom: 14 })
      } else if (failed_segments?.length > 0) {
        // No safe route but has failed segments — zoom to failure zone
        const bounds = new maplibregl.LngLatBounds()
        failed_segments.forEach(seg =>
          seg.coordinates.forEach(c => bounds.extend(toLonLat(c)))
        )
        map.fitBounds(bounds, { padding: 120, duration: 1200, maxZoom: 14 })
      }

      // Pulsing failure zone marker
      const el = document.createElement('div')
      el.style.cssText = `
        width: 24px; height: 24px; border-radius: 50%;
        background: rgba(239,68,68,0.25);
        border: 2px solid #ef4444;
        box-shadow: 0 0 20px #ef4444;
        animation: circle-pulse 1.5s ease-in-out infinite;
      `
      const state = useStore.getState()
      markers.current.push(
        new maplibregl.Marker({ element: el })
          .setLngLat([state.lon, state.lat])
          .addTo(map)
      )
    }

    if (loaded.current) draw()
    else mapRef.current?.once('load', draw)

  }, [simData])

  const legendItems = [
    { color: '#94a3b8', dash: true,  label: 'NORMAL' },
    { color: '#ef4444', dash: true,  label: 'FAILED' },
    { color: '#10b981', dash: false, label: 'ORIG'   },
    { color: '#00f2fe', dash: false, label: 'REC'    },
  ]

  return (
    <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
      <div ref={mapContainer} style={{ width: '100%', height: '100%' }} />

      {/* Legend */}
      <div style={{
        position: 'absolute', bottom: 12, left: 12,
        background: 'rgba(6,6,10,0.88)',
        border: '1px solid #00f2fe22',
        borderRadius: 3,
        padding: '5px 12px',
        display: 'flex',
        gap: 16,
        alignItems: 'center',
        backdropFilter: 'blur(8px)',
      }}>
        {legendItems.map(item => (
          <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{
              width: 20, height: 2,
              background: item.dash ? 'none' : item.color,
              borderTop: item.dash ? `2px dashed ${item.color}` : undefined,
            }} />
            <span style={{
              fontFamily: 'JetBrains Mono', fontSize: 8,
              color: '#64748b', letterSpacing: '0.1em',
            }}>
              {item.label}
            </span>
          </div>
        ))}
      </div>

      {/* Click mode hint */}
      {clickMode && (
        <div style={{
          position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)',
          background: 'rgba(0,242,254,0.1)',
          border: '1px solid #00f2fe55',
          borderRadius: 3,
          padding: '6px 18px',
          fontFamily: 'JetBrains Mono',
          fontSize: 10,
          color: '#00f2fe',
          letterSpacing: '0.15em',
          backdropFilter: 'blur(8px)',
          whiteSpace: 'nowrap',
        }}>
          CLICK MAP TO SET {clickMode.toUpperCase()}
        </div>
      )}
    </div>
  )
}