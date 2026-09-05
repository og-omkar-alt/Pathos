import { useStore } from '../store'

export default function CliBar() {
  const { cliLines } = useStore()
  const last = cliLines[cliLines.length - 1] ?? 'Awaiting command...'

  return (
    <div className="cli-bar" style={{ flexShrink: 0 }}>
      <span style={{ color: '#00f2fe', fontWeight: 600 }}>SETU_CLI</span>
      <span style={{ color: '#334155' }}>&gt;</span>
      <span style={{ color: '#94a3b8', flex: 1, overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
        {last}
      </span>
      <span className="cli-cursor" />
    </div>
  )
}