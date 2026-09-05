import { useState } from 'react'
import { motion } from 'framer-motion'
import { useStore } from '../store'
import { runSimulation } from '../api'

export default function LeftPanel() {
  const {
    lat, lon, radiusM,
    originLat, originLon, destLat, destLon,
    setLat, setLon, setRadiusM,
    setOriginLat, setOriginLon, setDestLat, setDestLon,
    clickMode, setClickMode,
    isSimulating, setIsSimulating,
    setSimData, addCliLine,
  } = useStore()

  const [sliderPct, setSliderPct] = useState(
    ((radiusM - 500) / (2000 - 500)) * 100
  )

  const handleRadiusChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = Number(e.target.value)
    setRadiusM(v)
    const pct = ((v - 500) / (2000 - 500)) * 100
    setSliderPct(pct)
    e.target.style.setProperty('--val', `${pct}%`)
  }

  const handleSimulate = async () => {
    if (isSimulating) return
    if (!lat || !lon) {
      addCliLine('> ✗ Select incident location on map first.')
      return
    }
    if (!originLat || !destLat) {
      addCliLine('> ✗ Origin and destination auto-set. Ready to simulate.')
    }
    setIsSimulating(true)
    setSimData(null)  // clear previous data immediately
    addCliLine(`> INITIATING simulation at [${lat.toFixed(4)}, ${lon.toFixed(4)}] r=${radiusM}m`)
    addCliLine('> Running A* pathfinding on graph...')

    try {
      const data = await runSimulation({
        lat,
        lon,
        radius_m        : radiusM,
        route_start_lat : originLat,
        route_start_lon : originLon,
        route_end_lat   : destLat,
        route_end_lon   : destLon,
        max_snap_dist_m : 3000,
      })
      setSimData(data)
      const priority = data.simulation_result?.emergency_priority ?? 'DONE'
      const pop      = data.simulation_result?.population_affected?.toLocaleString() ?? '—'
      const safeStatus = data.safe_route?.status ?? 'unknown'
      addCliLine(`> ✓ Simulation complete — Priority: ${priority}`)
      addCliLine(`> Pop affected: ${pop} | Safe route: ${safeStatus}`)
    } catch (e: any) {
      addCliLine(`> ✗ Error: ${e?.message ?? 'Backend unreachable. Is api.py running?'}`)
    } finally {
      setIsSimulating(false)
    }
  }

  const handleReset = () => {
    setSimData(null)
    addCliLine('> Simulation cleared.')
  }

  return (
    <motion.div
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="panel"
      style={{
        width: 210,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        overflowY: 'auto',
        borderRight: '1px solid #00f2fe1a',
      }}
    >
      {/* ── INCIDENT CONTROL ── */}
      <div className="panel-header">
        <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="#00f2fe" strokeWidth="2">
          <circle cx="12" cy="12" r="3" />
          <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" />
        </svg>
        INCIDENT CONTROL
        <span className="badge-active" style={{ marginLeft: 'auto' }}>ACTIVE</span>
      </div>

      <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 10 }}>

        {/* Select on map */}
        <button
          onClick={() => setClickMode(clickMode === 'incident' ? null : 'incident')}
          style={{
            background   : clickMode === 'incident' ? '#00f2fe15' : 'transparent',
            border       : `1px solid ${clickMode === 'incident' ? '#00f2fe' : '#00f2fe33'}`,
            color        : '#00f2fe',
            fontFamily   : 'JetBrains Mono',
            fontSize     : 10,
            letterSpacing: '0.15em',
            padding      : '6px 0',
            borderRadius : 3,
            cursor       : 'pointer',
            display      : 'flex',
            alignItems   : 'center',
            justifyContent: 'center',
            gap          : 6,
          }}
        >
          <svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="3" />
            <circle cx="12" cy="12" r="9" opacity="0.3" />
            <line x1="12" y1="2" x2="12" y2="6" />
            <line x1="12" y1="18" x2="12" y2="22" />
            <line x1="2"  y1="12" x2="6"  y2="12" />
            <line x1="18" y1="12" x2="22" y2="12" />
          </svg>
          {clickMode === 'incident' ? 'CLICK MAP...' : 'SELECT ON MAP'}
        </button>

        {/* Lat / Lon */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
          <div>
            <label style={{ fontFamily: 'JetBrains Mono', fontSize: 8, color: '#475569', letterSpacing: '0.15em', display: 'block', marginBottom: 3 }}>
              LATITUDE
            </label>
            <input className="setu-input" type="number" step="0.0001"
              value={lat} onChange={e => setLat(Number(e.target.value))} />
          </div>
          <div>
            <label style={{ fontFamily: 'JetBrains Mono', fontSize: 8, color: '#475569', letterSpacing: '0.15em', display: 'block', marginBottom: 3 }}>
              LONGITUDE
            </label>
            <input className="setu-input" type="number" step="0.0001"
              value={lon} onChange={e => setLon(Number(e.target.value))} />
          </div>
        </div>
      </div>

      {/* ── IMPACT RADIUS ── */}
      <div className="panel-header" style={{ marginTop: 2 }}>
        <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="#00f2fe" strokeWidth="2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
        IMPACT RADIUS
      </div>

      <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontFamily: 'JetBrains Mono', fontSize: 9, color: '#475569', letterSpacing: '0.1em' }}>RANGE</span>
          <span style={{ fontFamily: 'JetBrains Mono', fontSize: 11, color: '#00f2fe', fontWeight: 600 }}>
            {radiusM} m
          </span>
        </div>
        <input
          type="range" min={500} max={2000} step={50}
          value={radiusM}
          className="setu-slider"
          style={{ '--val': `${sliderPct}%` } as any}
          onChange={handleRadiusChange}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ fontFamily: 'JetBrains Mono', fontSize: 8, color: '#334155' }}>500m</span>
          <span style={{ fontFamily: 'JetBrains Mono', fontSize: 8, color: '#334155' }}>2000m</span>
        </div>
      </div>

      {/* ── ROUTING ── */}
      <div className="panel-header" style={{ marginTop: 2 }}>
        <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="#00f2fe" strokeWidth="2">
          <polyline points="22 12 18 8 14 12" />
          <polyline points="2 12 6 16 10 12" />
          <path d="M18 8v4a4 4 0 01-8 0V8" />
        </svg>
        ROUTING
      </div>

      <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 8 }}>

        {/* Origin lat */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', border: '1.5px solid #64748b', flexShrink: 0 }} />
          <input className="setu-input" placeholder="ORIGIN LAT" type="number" step="0.0001"
            value={originLat} onChange={e => setOriginLat(Number(e.target.value))} style={{ flex: 1 }} />
          <button
            onClick={() => setClickMode(clickMode === 'origin' ? null : 'origin')}
            title="Click map to set origin"
            style={{
              background: clickMode === 'origin' ? '#00f2fe22' : 'transparent',
              border: '1px solid #00f2fe33', borderRadius: 3,
              padding: '4px 6px', cursor: 'pointer', flexShrink: 0,
            }}
          >
            <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="#00f2fe" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <line x1="12" y1="2" x2="12" y2="6" />
              <line x1="12" y1="18" x2="12" y2="22" />
              <line x1="2"  y1="12" x2="6"  y2="12" />
              <line x1="18" y1="12" x2="22" y2="12" />
            </svg>
          </button>
        </div>

        {/* Origin lon */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 8, height: 8, flexShrink: 0 }} />
          <input className="setu-input" placeholder="ORIGIN LON" type="number" step="0.0001"
            value={originLon} onChange={e => setOriginLon(Number(e.target.value))} style={{ flex: 1 }} />
        </div>

        <div style={{ height: 1, background: '#0f172a', margin: '2px 0' }} />

        {/* Dest lat */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#ef4444', flexShrink: 0, boxShadow: '0 0 6px #ef4444' }} />
          <input className="setu-input" placeholder="DEST LAT" type="number" step="0.0001"
            value={destLat} onChange={e => setDestLat(Number(e.target.value))} style={{ flex: 1 }} />
          <button
            onClick={() => setClickMode(clickMode === 'destination' ? null : 'destination')}
            title="Click map to set destination"
            style={{
              background: clickMode === 'destination' ? '#00f2fe22' : 'transparent',
              border: '1px solid #00f2fe33', borderRadius: 3,
              padding: '4px 6px', cursor: 'pointer', flexShrink: 0,
            }}
          >
            <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="#00f2fe" strokeWidth="2">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 1118 0z" />
              <circle cx="12" cy="10" r="3" />
            </svg>
          </button>
        </div>

        {/* Dest lon */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 8, height: 8, flexShrink: 0 }} />
          <input className="setu-input" placeholder="DEST LON" type="number" step="0.0001"
            value={destLon} onChange={e => setDestLon(Number(e.target.value))} style={{ flex: 1 }} />
        </div>

        {/* Simulate button */}
        <div style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 6 }}>
          <button
            className={`btn-simulate${isSimulating ? ' running' : ''}`}
            onClick={handleSimulate}
            disabled={isSimulating}
          >
            {isSimulating ? (
              <>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                  style={{ width: 11, height: 11, border: '1.5px solid #f59e0b', borderTopColor: 'transparent', borderRadius: '50%' }}
                />
                SIMULATING...
              </>
            ) : (
              <>
                <svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                SIMULATE ROUTE
              </>
            )}
          </button>

          {/* Reset button — only show after simulation */}
          {!isSimulating && (
            <button
              onClick={handleReset}
              style={{
                background: 'transparent',
                border: '1px solid #334155',
                color: '#475569',
                fontFamily: 'JetBrains Mono',
                fontSize: 10,
                letterSpacing: '0.1em',
                padding: '6px 0',
                borderRadius: 3,
                cursor: 'pointer',
                width: '100%',
                transition: 'all 0.2s',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = '#64748b'
                e.currentTarget.style.color = '#94a3b8'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = '#334155'
                e.currentTarget.style.color = '#475569'
              }}
            >
              CLEAR
            </button>
          )}
        </div>
      </div>
    </motion.div>
  )
}