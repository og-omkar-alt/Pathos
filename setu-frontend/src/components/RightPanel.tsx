import { motion, AnimatePresence } from 'framer-motion'
import { useStore } from '../store'
import { useEffect, useState } from 'react'

function AnimatedNumber({ target, decimals = 0 }: { target: number; decimals?: number }) {
  const [val, setVal] = useState(0)
  useEffect(() => {
    let start = 0
    const end = target
    const duration = 1200
    const step = 16
    const increment = (end - start) / (duration / step)
    const timer = setInterval(() => {
      start += increment
      if (start >= end) { setVal(end); clearInterval(timer) }
      else setVal(start)
    }, step)
    return () => clearInterval(timer)
  }, [target])
  return <>{decimals > 0 ? val.toFixed(decimals) : Math.round(val).toLocaleString()}</>
}

export default function RightPanel() {
  const { simData } = useStore()
  const sr = simData?.simulation_result
  const nr = simData?.normal_route
  const sf = simData?.safe_route
  const fs = simData?.failed_segments ?? []

  return (
    <motion.div
      initial={{ x: 20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.4 }}
      style={{
        width: 220,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 0,
        overflowY: 'auto',
        borderLeft: '1px solid #00f2fe1a',
        background: 'rgba(6,6,10,0.95)',
      }}
    >
      {/* ── NETWORK IMPACT ── */}
      <div className="panel-header">
        <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="#00f2fe" strokeWidth="2">
          <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
        </svg>
        NETWORK IMPACT
      </div>

      <div style={{ padding: '10px 12px' }}>
        <AnimatePresence mode="wait">
          {!sr ? (
            <div style={{ fontFamily: 'JetBrains Mono', fontSize: 9, color: '#334155', letterSpacing: '0.1em' }}>
              AWAITING SIMULATION...
            </div>
          ) : (
            <motion.div key="impact" initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>

              {/* Population */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 4 }}>
                <div>
                  <div style={{ fontFamily: 'JetBrains Mono', fontSize: 8, color: '#475569', letterSpacing: '0.15em' }}>
                    POP. AFFECTED
                  </div>
                  <div className="counter-value" style={{ fontSize: 22 }}>
                    <AnimatedNumber target={sr.population_affected} />
                  </div>
                </div>
              </div>

              {/* Priority badge */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontFamily: 'JetBrains Mono', fontSize: 8, color: '#475569' }}>PRIORITY</span>
                <span className={sr.emergency_priority === 'CRITICAL' ? 'badge-crit' : sr.emergency_priority === 'HIGH' ? 'badge-risk' : 'badge-ok'}>
                  {sr.emergency_priority}
                </span>
              </div>

              {/* Topology delta */}
              <div style={{ borderTop: '1px solid #00f2fe11', paddingTop: 8 }}>
                <div style={{ fontFamily: 'JetBrains Mono', fontSize: 8, color: '#475569', letterSpacing: '0.15em', marginBottom: 6 }}>
                  TOPOLOGY DELTA
                </div>

                <DeltaRow
                  label="Connectivity"
                  before={sr.connectivity_before}
                  after={sr.connectivity_after}
                  unit="%"
                />
                <DeltaRow
                  label="Resilience"
                  before={sr.resilience_before}
                  after={sr.resilience_after}
                  decimals={2}
                  unit=""
                />
                <DeltaRow
                  label="Components"
                  before={0}
                  after={sr.disconnected_wards}
                  unit=" new"
                  invert
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ── ROUTE COMPARE ── */}
      <div className="panel-header" style={{ borderTop: '1px solid #00f2fe1a' }}>
        <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="#00f2fe" strokeWidth="2">
          <path d="M3 12h18M3 6h18M3 18h18" />
        </svg>
        ROUTE COMPARE
      </div>

      <div style={{ padding: '8px 12px' }}>
        <AnimatePresence mode="wait">
          {!nr ? (
            <div style={{ fontFamily: 'JetBrains Mono', fontSize: 9, color: '#334155' }}>
              AWAITING SIMULATION...
            </div>
          ) : (
            <motion.div key="routes" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={thStyle}>METRIC</th>
                    <th style={thStyle}>ORIG</th>
                    <th style={thStyle}>ALT</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style={tdLabel}>Status</td>
                    <td style={tdVal}>
                      <span className={nr.status === 'success' ? 'badge-ok' : 'badge-crit'}>
                        {nr.status === 'success' ? 'OK' : 'FAIL'}
                      </span>
                    </td>
                    <td style={tdVal}>
                      <span className={sf?.status === 'success' ? 'badge-ok' : 'badge-crit'}>
                        {sf?.status === 'success' ? 'OK' : sf?.status === 'isolated' ? 'ISO' : 'FAIL'}
                      </span>
                    </td>
                  </tr>
                  <tr>
                    <td style={tdLabel}>Dist</td>
                    <td style={tdVal}>{nr.metrics?.distance_km ?? '—'}km</td>
                    <td style={tdVal}>{sf?.metrics?.distance_km ?? '—'}km</td>
                  </tr>
                  <tr>
                    <td style={tdLabel}>ETA</td>
                    <td style={tdVal}>{nr.metrics?.estimated_time_mins ?? '—'}m</td>
                    <td style={tdVal}>{sf?.metrics?.estimated_time_mins ?? '—'}m</td>
                  </tr>
                  {sf?.detour_km !== undefined && (
                    <tr>
                      <td style={tdLabel}>Detour</td>
                      <td style={tdVal}>—</td>
                      <td style={{ ...tdVal, color: '#f59e0b' }}>+{sf.detour_km}km</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ── CRITICAL SEGS ── */}
      <div className="panel-header" style={{ borderTop: '1px solid #00f2fe1a' }}>
        <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="#f59e0b" strokeWidth="2">
          <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
        <span style={{ color: '#f59e0b' }}>CRITICAL SEGS</span>
      </div>

      <div style={{ padding: '8px 12px', flex: 1, overflowY: 'auto' }}>
        <AnimatePresence>
          {fs.length === 0 ? (
            <div style={{ fontFamily: 'JetBrains Mono', fontSize: 9, color: '#334155' }}>
              NO ACTIVE SEGMENTS
            </div>
          ) : (
            <>
              <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 4 }}>
                <thead>
                  <tr>
                    <th style={thStyle}>ID</th>
                    <th style={thStyle}>STAT</th>
                    <th style={thStyle}>VULN</th>
                  </tr>
                </thead>
                <tbody>
                  {fs.slice(0, 8).map((seg, i) => (
                    <motion.tr
                      key={seg.id}
                      initial={{ opacity: 0, x: 10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                    >
                      <td style={{ ...tdLabel, fontSize: 9 }}>
                        {seg.id.replace('SEG-', 'SG-').substring(0, 10)}
                      </td>
                      <td style={tdVal}>
                        <span className={seg.criticality === 'CRITICAL' ? 'badge-crit' : 'badge-risk'}>
                          {seg.criticality === 'CRITICAL' ? 'CRIT' : 'RISK'}
                        </span>
                      </td>
                      <td style={{ ...tdVal, color: seg.score > 0.75 ? '#ef4444' : '#f59e0b' }}>
                        {seg.score.toFixed(2)}
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
              {fs.length > 8 && (
                <div style={{ fontFamily: 'JetBrains Mono', fontSize: 8, color: '#334155', textAlign: 'center' }}>
                  +{fs.length - 8} more segments
                </div>
              )}
            </>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}

function DeltaRow({ label, before, after, unit = '', decimals = 1, invert = false }: {
  label: string; before: number; after: number;
  unit?: string; decimals?: number; invert?: boolean;
}) {
  const improved = invert ? after < before : after > before
  const color    = improved ? '#10b981' : '#ef4444'
  const fmt      = (v: number) => decimals > 0 ? v.toFixed(decimals) : Math.round(v)

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 5 }}>
      <span style={{ fontFamily: 'JetBrains Mono', fontSize: 9, color: '#64748b' }}>{label}</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <span style={{ fontFamily: 'JetBrains Mono', fontSize: 9, color: '#94a3b8' }}>
          {fmt(before)}{unit}
        </span>
        <span style={{ color, fontSize: 9 }}>→</span>
        <span style={{ fontFamily: 'JetBrains Mono', fontSize: 10, color, fontWeight: 600 }}>
          {fmt(after)}{unit}
        </span>
      </div>
    </div>
  )
}

const thStyle: React.CSSProperties = {
  fontFamily: 'JetBrains Mono', fontSize: 8,
  color: '#475569', letterSpacing: '0.1em',
  textAlign: 'left', paddingBottom: 4,
  borderBottom: '1px solid #0f172a',
}
const tdLabel: React.CSSProperties = {
  fontFamily: 'JetBrains Mono', fontSize: 9,
  color: '#64748b', padding: '3px 0',
}
const tdVal: React.CSSProperties = {
  fontFamily: 'JetBrains Mono', fontSize: 9,
  color: '#e2e8f0', padding: '3px 0',
}