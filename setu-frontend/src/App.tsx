import { useStore } from './store'
import { fetchNetworkSummary } from './api'
import { useEffect } from 'react'
import LandingPage from './components/LandingPage'
import Dashboard   from './components/Dashboard'

export default function App() {
  const { page, setNetworkSummary } = useStore()

  useEffect(() => {
    fetchNetworkSummary()
      .then(setNetworkSummary)
      .catch(() => setNetworkSummary({
        nodes: 63524, edges: 83253, components: 1, total_km: 8528
      }))
  }, [])

  if (page === 'landing') return <LandingPage />
  return <Dashboard />
}