import { useEffect, useState } from 'react'
import { useStore } from '../store'

export default function TopBar() {
  const { networkSummary } = useStore()
  const [time, setTime] = useState('')

  useEffect(() => {
    const tick = () => {
      const now = new Date()
      const match = now.toUTCString().match(/(\d{2}:\d{2}:\d{2})/)
      setTime(match ? match[1] + ' UTC' : '')
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  return (
    <div style={{
      height: 36,
      background: '#06060a',
      borderBottom: '1px solid #00f2fe1a',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 16px',
      flexShrink: 0,
      zIndex: 50,
    }}>
      {/* Left — logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <svg viewBox="0 0 24 24" width="16" height="16">
          <polygon points="12,3 21,20 3,20" fill="none" stroke="#00f2fe" strokeWidth="1.5" />
        </svg>
        <span style={{
          fontFamily: 'JetBrains Mono', fontSize: 12,
          color: '#00f2fe', fontWeight: 700, letterSpacing: '0.2em',
        }}>SETU</span>
      </div>

      {/* Centre — status indicators */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        <StatusDot color="#00f2fe" label="SYS:OP" />
        <StatusDot color="#10b981" label="NET:LIVE" />
        <StatusDot color="#00f2fe" label="DB:SYNC" />

        <span style={{
          fontFamily: 'JetBrains Mono', fontSize: 13,
          color: '#e2e8f0', letterSpacing: '0.1em', fontWeight: 600,
        }}>{time}</span>

        {/* Icons */}
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <IconBtn title="Signal">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#64748b" strokeWidth="2">
              <path d="M1 6s4-4 11-4 11 4 11 4M5 10s3-3 7-3 7 3 7 3M9 14s1-1 3-1 3 1 3 1M12 18h.01" />
            </svg>
          </IconBtn>
          <IconBtn title="Globe">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#64748b" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M2 12h20M12 2a15 15 0 010 20M12 2a15 15 0 000 20" />
            </svg>
          </IconBtn>
          <IconBtn title="Settings">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#64748b" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M12 1v3M12 20v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M1 12h3M20 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12" />
            </svg>
          </IconBtn>
        </div>
      </div>

      {/* Right — op label */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ fontFamily: 'JetBrains Mono', fontSize: 9, color: '#475569', letterSpacing: '0.15em' }}>OP:</span>
        <span style={{ fontFamily: 'JetBrains Mono', fontSize: 11, color: '#e2e8f0', letterSpacing: '0.1em', fontWeight: 600 }}>ALPHA</span>
        {networkSummary && (
          <span style={{ fontFamily: 'JetBrains Mono', fontSize: 9, color: '#334155', marginLeft: 12 }}>
            {networkSummary.nodes.toLocaleString()} NODES
          </span>
        )}
      </div>
    </div>
  )
}

function StatusDot({ color, label }: { color: string; label: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
      <div style={{
        width: 5, height: 5, borderRadius: '50%',
        background: color, boxShadow: `0 0 6px ${color}`,
        animation: 'pulse-dot 2s infinite',
      }} />
      <span style={{ fontFamily: 'JetBrains Mono', fontSize: 9, color: '#64748b', letterSpacing: '0.15em' }}>
        {label}
      </span>
    </div>
  )
}

function IconBtn({ children, title }: { children: React.ReactNode; title: string }) {
  return (
    <button title={title} style={{
      background: 'none', border: 'none', cursor: 'pointer',
      display: 'flex', alignItems: 'center', padding: 2,
      opacity: 0.6, transition: 'opacity 0.2s',
    }}
    onMouseEnter={e => (e.currentTarget.style.opacity = '1')}
    onMouseLeave={e => (e.currentTarget.style.opacity = '0.6')}
    >
      {children}
    </button>
  )
}