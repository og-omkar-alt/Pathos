import TopBar    from './TopBar'
import LeftPanel from './LeftPanel'
import MapView   from './MapView'
import RightPanel from './RightPanel'
import CliBar    from './CliBar'

export default function Dashboard() {
  return (
    <div style={{
      width: '100vw', height: '100vh',
      display: 'flex', flexDirection: 'column',
      background: '#06060a',
      overflow: 'hidden',
    }}>
      <TopBar />

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', minHeight: 0 }}>
        <LeftPanel />
        <MapView />
        <RightPanel />
      </div>

      <CliBar />
    </div>
  )
}