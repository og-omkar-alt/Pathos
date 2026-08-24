'use client';

import { SimulationProvider } from '../context/SimulationContext';
import { HomeView } from '../components/HomeView';
import { DashboardView } from '../components/DashboardView';

export default function App() {
  return (
    <SimulationProvider>
      <main className="w-full h-screen overflow-hidden bg-[#030307]">
        <HomeView />
        <DashboardView />
      </main>
    </SimulationProvider>
  );
}
