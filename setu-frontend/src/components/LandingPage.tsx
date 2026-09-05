import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useStore } from '../store'
const earthVideo = '/src/assets/earth.mp4'

function LiveClock() {
  const [time, setTime] = useState('')
  const [date, setDate] = useState('')

  useEffect(() => {
    const tick = () => {
      const now = new Date()
      const match = now.toUTCString().match(/(\d{2}:\d{2}:\d{2})/)
      setTime(match ? match[1] + ' UTC' : '')
      setDate(now.toLocaleDateString('en-GB', {
        day: '2-digit', month: 'short', year: 'numeric'
      }).toUpperCase())
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="text-right">
      <p style={{ fontFamily: 'JetBrains Mono', fontSize: 11, color: '#64748b', letterSpacing: '0.15em' }}>
        AHMEDABAD, INDIA
      </p>
      <p style={{ fontFamily: 'JetBrains Mono', fontSize: 11, color: '#94a3b8' }}>{date}</p>
      <p style={{ fontFamily: 'JetBrains Mono', fontSize: 14, color: '#00f2fe', fontWeight: 600 }}>{time}</p>
    </div>
  )
}

export default function LandingPage() {
  const setPage = useStore(s => s.setPage)

  return (
    <div style={{ position: 'relative', width: '100vw', height: '100vh', overflow: 'hidden', background: '#06060a' }}>

      {/* Earth video background */}
      <video
        className="landing-video"
        src={earthVideo}
        autoPlay
        loop
        muted
        playsInline
      />

      {/* Dark overlay — stronger on left for text readability */}
      <div className="landing-overlay" />

      {/* Scan line */}
      <div className="scan-line" />

      {/* Grid overlay */}
      <div className="grid-bg" style={{ position: 'absolute', inset: 0, opacity: 0.3, pointerEvents: 'none' }} />

      {/* Top right — system status */}
      <div style={{ position: 'absolute', top: 24, right: 32, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 12 }}>
        {/* System online */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="dot-online" />
          <span style={{ fontFamily: 'JetBrains Mono', fontSize: 10, color: '#00f2fe', letterSpacing: '0.2em' }}>
            SYSTEM ONLINE
          </span>
        </div>

        <LiveClock />

        {/* Data source */}
        <div style={{ marginTop: 8, textAlign: 'right' }}>
          <p style={{ fontFamily: 'JetBrains Mono', fontSize: 9, color: '#475569', letterSpacing: '0.2em' }}>
            DATA SOURCE
          </p>
          <p style={{ fontFamily: 'JetBrains Mono', fontSize: 13, color: '#e2e8f0', fontWeight: 600, letterSpacing: '0.1em' }}>
            NISAR SATELLITE
          </p>
          {/* X / cross icon */}
          <div style={{ marginTop: 8, display: 'flex', justifyContent: 'flex-end' }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6l12 12" stroke="#00f2fe" strokeWidth="2" strokeLinecap="round" opacity="0.6"/>
              <circle cx="12" cy="12" r="10" stroke="#00f2fe" strokeWidth="1" opacity="0.2"/>
            </svg>
          </div>
        </div>
      </div>

      {/* Main content — left side */}
      <div style={{ position: 'absolute', left: 64, bottom: 80, maxWidth: 480 }}>
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        >
          {/* SETU Logo + name */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20 }}>
            {/* Triangle logo */}
            <div style={{
              width: 48, height: 48,
              border: '1px solid #00f2fe55',
              background: '#00f2fe10',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              borderRadius: 4,
            }}>
              <svg viewBox="0 0 24 24" width="28" height="28">
                <polygon points="12,3 21,20 3,20" fill="none" stroke="#00f2fe" strokeWidth="1.5" />
                <line x1="12" y1="3" x2="12" y2="20" stroke="#00f2fe" strokeWidth="0.5" opacity="0.4" />
              </svg>
            </div>
            <motion.h1
              className="neon-text"
              style={{
                fontFamily: 'JetBrains Mono',
                fontSize: 52,
                fontWeight: 700,
                color: '#00f2fe',
                letterSpacing: '0.1em',
                lineHeight: 1,
              }}
              animate={{ textShadow: ['0 0 10px #00f2fe', '0 0 30px #00f2fe, 0 0 60px #00f2fe44', '0 0 10px #00f2fe'] }}
              transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
            >
              SETU
            </motion.h1>
          </div>

          {/* Tagline */}
          <h2 style={{
            fontFamily: 'Inter',
            fontSize: 22,
            fontWeight: 600,
            color: '#f1f5f9',
            marginBottom: 12,
            lineHeight: 1.3,
            letterSpacing: '0.02em',
          }}>
            URBAN ROAD RESILIENCE<br />
            & NETWORK INTELLIGENCE
          </h2>

          {/* Description */}
          <p style={{
            fontFamily: 'Inter',
            fontSize: 13,
            color: '#94a3b8',
            lineHeight: 1.7,
            marginBottom: 36,
            maxWidth: 380,
          }}>
            Advanced geospatial intelligence platform to analyze, simulate
            and strengthen urban road-network resilience for safer, smarter
            and more connected cities.
          </p>

          {/* CTA button */}
          <motion.button
            onClick={() => setPage('dashboard')}
            whileHover={{ scale: 1.02, boxShadow: '0 0 24px #00f2fe44' }}
            whileTap={{ scale: 0.98 }}
            style={{
              background: 'transparent',
              border: '1px solid #00f2fe',
              color: '#00f2fe',
              fontFamily: 'JetBrains Mono',
              fontSize: 13,
              letterSpacing: '0.2em',
              padding: '14px 36px',
              borderRadius: 3,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              transition: 'all 0.2s',
            }}
          >
            ENTER DASHBOARD
            <span style={{ fontSize: 16 }}>→</span>
          </motion.button>
        </motion.div>
      </div>

      {/* Bottom left version */}
      <div style={{ position: 'absolute', bottom: 16, left: 64 }}>
        <p style={{ fontFamily: 'JetBrains Mono', fontSize: 9, color: '#334155', letterSpacing: '0.15em' }}>
          DEMO ENVIRONMENT · v2.0.0
        </p>
      </div>

      {/* Satellite orbit animation */}
      <div style={{
        position: 'absolute',
        top: '50%', left: '50%',
        transform: 'translate(-50%, -50%)',
        pointerEvents: 'none',
      }}>
        <motion.div
          style={{ position: 'relative', width: 600, height: 400 }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1, duration: 1 }}
        >
          {/* Elliptical orbit path */}
          <svg
            viewBox="0 0 600 400"
            style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
          >
            <ellipse
              cx="300" cy="200"
              rx="280" ry="160"
              fill="none"
              stroke="#00f2fe"
              strokeWidth="0.5"
              strokeDasharray="4 8"
              opacity="0.2"
            />
          </svg>
          {/* Orbiting satellite dot */}
          <motion.div
            style={{
              position: 'absolute',
              width: 8, height: 8,
              background: '#00f2fe',
              borderRadius: '50%',
              boxShadow: '0 0 12px #00f2fe, 0 0 24px #00f2fe44',
              top: '50%', left: '50%',
              marginLeft: -4, marginTop: -4,
            }}
            animate={{
              x: [280, 140, -280, -140, 280],
              y: [0, -160, 0, 160, 0],
            }}
            transition={{
              duration: 8,
              repeat: Infinity,
              ease: 'linear',
            }}
          />
        </motion.div>
      </div>
    </div>
  )
}