'use client';

import React, { useState } from 'react';

import {
  useSimulation,
  type DemoRoute,
} from '../context/SimulationContext';

import { demoScenarios } from '../data/demoScenarios';

import { MapComponent } from './map/MapComponent';
import { Sidebar } from './Sidebar';

import { RoadDetailPanel } from './panels/RoadDetailPanel';
import { SimulationPanel } from './panels/SimulationPanel';
import { ReportsPanel } from './panels/ReportsPanel';
import { SettingsPanel } from './panels/SettingsPanel';
import { CriticalityPanel } from './panels/CriticalityPanel';
import { NetworkAnalysisPanel } from './panels/NetworkAnalysisPanel';

import { MapLayersControl } from './map/MapLayersControl';
import { MapLegend } from './map/MapLegend';

import {
  Bell,
  HelpCircle,
  User,
  TrendingDown,
  TrendingUp,
  Layers,
  ShieldAlert,
  Navigation,
} from 'lucide-react';

export const DashboardView: React.FC = () => {

  const {
    currentTab,
    setCurrentTab, // 👈 STEP 1: ADD THIS EXACT LINE RIGHT HERE
    simState,
    selectedRoadId,

    metrics,
    startSimulation,
    resetScenario,

    backendOnline,

    originArea,
    setOriginArea,

    destArea,
    setDestArea,

    setOriginCoords,
    setDestCoords,

    setSimState,
    setSimulationResult,
    setRouteResult,
    setMetrics,
  } = useSimulation() as any;

  const [layersOpen, setLayersOpen] =
    useState(false);

  const [selectedDemoId, setSelectedDemoId] =
    useState('');

  // ---------------------------------------------------------------------------
  // USE THE ACTUAL SAVED DEMO SCENARIOS
  // ---------------------------------------------------------------------------

  const demoRoutes = Object.values(
    demoScenarios
  ) as any[];

  // ---------------------------------------------------------------------------
  // SELECT PRESET ROUTE
  // ---------------------------------------------------------------------------

  const handleRouteSelect = (
    e: React.ChangeEvent<HTMLSelectElement>
  ) => {
    const id = e.target.value;

    setSelectedDemoId(id);

    if (!id) {
      setOriginArea('');
      setDestArea('');

      setOriginCoords(null);
      setDestCoords(null);

      return;
    }

    const route =
      demoRoutes.find(
        (item) => item.id === id
      );

    if (!route) return;

    const first =
      route.routeCoords[0];

    const last =
      route.routeCoords[
        route.routeCoords.length - 1
      ];

    const origin = {
      lat: first[1],
      lon: first[0],
    };

    const destination = {
      lat: last[1],
      lon: last[0],
    };

    setOriginArea(
      `Lat: ${origin.lat.toFixed(
        4
      )}, Lon: ${origin.lon.toFixed(4)}`
    );

    setDestArea(
      `Lat: ${destination.lat.toFixed(
        4
      )}, Lon: ${destination.lon.toFixed(4)}`
    );

    setOriginCoords(origin);
    setDestCoords(destination);

    console.log(
      '🟢 SELECTED VERIFIED DEMO:',
      {
        id: route.id,
        label: route.label,
        points:
          route.routeCoords.length,
        first,
        last,
      }
    );
  };

  // ---------------------------------------------------------------------------
  // START SIMULATION
  // ---------------------------------------------------------------------------
  const handleSimulateClick = () => {
    const selectedRoute = demoRoutes.find((route) => route.id === selectedDemoId);

    if (selectedRoute) {
      // 1. Switch tab and trigger "LOADING" state
      if (setCurrentTab) setCurrentTab('SIMULATION');
      if (setSimState) setSimState('ANALYZING'); 

      // 2. FAKE BACKEND PROCESSING TIME (1.8 seconds)
      setTimeout(() => {
        if (setSimulationResult) {
          setSimulationResult({
            failedRoadId: selectedRoute.id,
            failedRoadName: selectedRoute.label,
            disconnectedWards: (selectedRoute as any).disconnectedWards || 0,
            populationAffected: (selectedRoute as any).populationAffected || 0,
            hospitalsImpacted: (selectedRoute as any).hospitalsImpacted || 0,
            connectivityBefore: (selectedRoute as any).connectivityBefore || 0,
            connectivityAfter: (selectedRoute as any).connectivityAfter || 0,
            resilienceBefore: (selectedRoute as any).resilienceBefore || 0,
            resilienceAfter: (selectedRoute as any).resilienceAfter || 0,
            priorityScore: (selectedRoute as any).priorityScore || 0,
            emergencyPriority: (selectedRoute as any).emergencyPriority || 'HIGH',
          });
        }

        if (setRouteResult) {
          setRouteResult({
            status: 'success',
            route_coords: selectedRoute.routeCoords,
            metrics: {
              distance_km: (selectedRoute as any).distance_km || 0,
              estimated_time_mins: (selectedRoute as any).estimated_time_mins || 0,
            }
          });
        }

        // Change state to active to reveal the data
        if (setSimState) setSimState('SIMULATION_ACTIVE');
      }, 1800); // <-- 1.8 SECOND DELAY 

      return;
    }

    startSimulation(); 
  };
  
  // ---------------------------------------------------------------------------
  // HEADER CONTEXT
  // ---------------------------------------------------------------------------

  const getHeaderContext = () => {
    switch (currentTab) {
      case 'HOME':
        return 'HOME ENVIRONMENT';

      case 'DASHBOARD':
        return 'AHMEDABAD NETWORK OVERVIEW';

      case 'NETWORK_ANALYSIS':
        return 'NETWORK TOPOLOGY ANALYSIS';

      case 'SIMULATION':
        return simState === 'ANALYZING'
          ? 'SCENARIO GENERATION'
          : 'SIMULATION MODE';

      case 'CRITICALITY':
        return 'CRITICALITY CORRIDORS RANKING';

      case 'REPORTS':
        return 'RESILIENCE ASSESSMENT REPORT';

      case 'DATA_LAYERS':
        return 'GEOSPATIAL DATA LAYERS';

      case 'SETTINGS':
        return 'WORKSPACE PREFERENCES';

      default:
        return 'AHMEDABAD NETWORK OVERVIEW';
    }
  };

  if (currentTab === 'HOME') {
    return null;
  }

  return (
    <div className="flex w-full h-screen overflow-hidden bg-[#07070a] text-slate-100 font-sans">

      <Sidebar />

      <div className="flex-1 flex flex-col h-full overflow-hidden relative">

        {/* ---------------------------------------------------------------- */}
        {/* TOP BAR */}
        {/* ---------------------------------------------------------------- */}

        <header className="h-14 border-b border-[#1a1f35]/50 bg-[#05060b] px-6 flex items-center justify-between z-10 select-none">

          <div className="flex items-center gap-3">
            <span className="text-xs font-mono font-bold tracking-widest text-[#00f2fe]">
              SETU
            </span>

            <span className="text-[10px] text-slate-500 font-mono">
              /
            </span>

            <span className="text-xs font-bold tracking-wider text-slate-200">
              {getHeaderContext()}
            </span>
          </div>

          <div className="flex items-center gap-6">

            <div className="flex items-center gap-2">
              <span
                className={`inline-block w-1.5 h-1.5 rounded-full ${
                  backendOnline
                    ? 'bg-emerald-500'
                    : 'bg-red-500'
                } animate-pulse`}
              />

              <span
                className={`text-[9px] font-mono tracking-widest font-bold uppercase ${
                  backendOnline
                    ? 'text-emerald-500'
                    : 'text-red-500'
                }`}
              >
                {backendOnline
                  ? 'BACKEND ONLINE'
                  : 'BACKEND OFFLINE'}
              </span>
            </div>

            <div className="flex items-center gap-4 text-slate-400">
              <button className="hover:text-[#00f2fe] transition-colors">
                <Bell className="w-4 h-4" />
              </button>

              <button className="hover:text-[#00f2fe] transition-colors">
                <HelpCircle className="w-4 h-4" />
              </button>

              <button className="hover:text-[#00f2fe] transition-colors">
                <User className="w-4 h-4" />
              </button>
            </div>

          </div>
        </header>

        {/* ---------------------------------------------------------------- */}
        {/* MAIN */}
        {/* ---------------------------------------------------------------- */}

        <div className="flex-1 flex w-full h-full overflow-hidden relative">

          {/* MAP COLUMN */}

          <div className="flex-1 h-full relative overflow-hidden flex flex-col">

            {/* ------------------------------------------------------------ */}
            {/* ROUTING BAR */}
            {/* ------------------------------------------------------------ */}

            <div className="absolute top-6 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-2">

              <div className="flex gap-3 w-[750px] bg-[#070b19]/95 border border-[#1a1f35] p-2.5 rounded shadow-2xl backdrop-blur-md items-center">

                {/* VERIFIED DEMO ROUTES */}

                <select
                  value={selectedDemoId}
                  onChange={handleRouteSelect}
                  disabled={
                    simState ===
                    'SIMULATION_ACTIVE'
                  }
                  className="bg-[#05060b] border border-[#1a1f35] rounded px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-[#00f2fe]/40 disabled:opacity-50 disabled:cursor-not-allowed transition-colors w-52 appearance-none cursor-pointer hover:border-slate-600"
                >
                  <option value="">
                    Select verified route...
                  </option>

                  {demoRoutes.map(
                    (route) => (
                      <option
                        key={route.id}
                        value={route.id}
                      >
                        {route.label}
                      </option>
                    )
                  )}
                </select>

                {/* ORIGIN */}

                <div className="flex-1 relative">

                  <span className="absolute left-3 top-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]" />

                  <input
                    type="text"
                    value={originArea}
                    onChange={(e) =>
                      setOriginArea(
                        e.target.value
                      )
                    }
                    disabled={
                      simState ===
                      'SIMULATION_ACTIVE'
                    }
                    placeholder="Origin"
                    className="w-full bg-[#05060b] border border-[#1a1f35] rounded px-3 py-2 pl-8 text-sm text-white font-mono placeholder-slate-500 focus:outline-none focus:border-[#00f2fe]/40 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  />

                </div>

                <span className="text-slate-500 text-xs font-mono">
                  →
                </span>

                {/* DESTINATION */}

                <div className="flex-1 relative">

                  <span className="absolute left-3 top-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]" />

                  <input
                    type="text"
                    value={destArea}
                    onChange={(e) =>
                      setDestArea(
                        e.target.value
                      )
                    }
                    disabled={
                      simState ===
                      'SIMULATION_ACTIVE'
                    }
                    placeholder="Destination"
                    className="w-full bg-[#05060b] border border-[#1a1f35] rounded px-3 py-2 pl-8 text-sm text-white font-mono placeholder-slate-500 focus:outline-none focus:border-[#00f2fe]/40 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  />

                </div>

                {/* SIMULATE */}

                <button
                  onClick={
                    simState ===
                    'SIMULATION_ACTIVE'
                      ? resetScenario
                      : handleSimulateClick
                  }
                  className={`px-6 py-2 rounded font-bold tracking-wider text-xs transition-all flex items-center gap-2 shadow-lg shrink-0 cursor-pointer ${
                    simState ===
                    'SIMULATION_ACTIVE'
                      ? 'bg-transparent border border-red-500 text-red-500 hover:bg-red-500 hover:text-white'
                      : 'bg-[#2563eb] text-white hover:bg-[#1d4ed8] border border-transparent'
                  }`}
                >

                  <Navigation className="w-3.5 h-3.5" />

                  {simState ===
                  'SIMULATION_ACTIVE'
                    ? 'RESET'
                    : 'SIMULATE'}

                </button>

              </div>

              {simState ===
                'SIMULATION_ACTIVE' && (
                <div className="text-[10px] font-mono text-[#00f2fe]/70 tracking-widest">
                  VERIFIED BACKEND ROUTE · SAVED A* GEOMETRY
                </div>
              )}

            </div>

            {/* MAP */}

            <MapComponent />

            {/* ------------------------------------------------------------ */}
            {/* LAYERS */}
            {/* ------------------------------------------------------------ */}

            <div className="absolute left-6 bottom-32 z-10 flex flex-col items-start gap-2">

              <button
                onClick={() =>
                  setLayersOpen(
                    !layersOpen
                  )
                }
                className={`flex items-center gap-2 px-3 py-2 border rounded font-mono text-[10px] tracking-widest uppercase transition-all shadow-lg select-none cursor-pointer ${
                  layersOpen
                    ? 'bg-[#00f2fe]/10 border-[#00f2fe] text-[#00f2fe]'
                    : 'bg-[#070b19]/80 border-[#1a1f35] text-slate-300 hover:border-slate-500'
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                LAYERS
              </button>

              {layersOpen && (
                <div className="bg-[#070b19]/90 border border-[#1a1f35] backdrop-blur-md rounded shadow-2xl p-4 w-52 max-h-80 overflow-y-auto">
                  <MapLayersControl
                    onClose={() =>
                      setLayersOpen(
                        false
                      )
                    }
                  />
                </div>
              )}

            </div>

            <MapLegend />

            {/* ------------------------------------------------------------ */}
            {/* METRICS */}
            {/* ------------------------------------------------------------ */}

            <div className="absolute bottom-6 left-6 right-6 h-20 bg-[#070b19]/85 backdrop-blur-sm border border-[#1a1f35]/80 rounded p-4 z-10 flex items-center justify-between shadow-2xl pointer-events-auto select-none">

              {[
                {
                  label: 'RESILIENCE INDEX',
                  value: simState === 'SIMULATION_ACTIVE' 
                    ? (demoRoutes.find(r => r.id === selectedDemoId) as any)?.ui_resilience?.toFixed(3) || '0.740'
                    : (metrics?.resilienceIndex || 0.74).toFixed(2),
                  trend: simState === 'SIMULATION_ACTIVE' ? { dir: 'down', txt: '-21.7%' } : { dir: 'up', txt: 'OPTIMAL' },
                },
                {
                  label: 'CONNECTIVITY',
                  value: simState === 'SIMULATION_ACTIVE'
                    ? `${(demoRoutes.find(r => r.id === selectedDemoId) as any)?.ui_connectivity || '1.55'}x`
                    : `${(metrics?.connectivity || 99.8).toFixed(1)}%`,
                  trend: simState === 'SIMULATION_ACTIVE' ? { dir: 'down', txt: '-14.3%' } : { dir: 'up', txt: 'STABLE' },
                },
                {
                  label: 'BREAKS / KM',
                  value: (metrics?.breaksPerKm || 4.2).toFixed(1),
                  trend: null,
                },
                {
                  label: 'POPULATION COVERED',
                  value: simState === 'SIMULATION_ACTIVE'
                    ? (demoRoutes.find(r => r.id === selectedDemoId) as any)?.ui_population || '0.0K nodes'
                    : '4.1M',
                  trend: null,
                },
                {
                  label: 'CRITICAL CORRIDORS',
                  value: simState === 'SIMULATION_ACTIVE'
                    ? String((demoRoutes.find(r => r.id === selectedDemoId) as any)?.ui_corridors || 14)
                    : String(metrics?.criticalCorridors || 14),
                  trend: null,
                },
              ].map(
                (
                  {
                    label,
                    value,
                    trend,
                  },
                  i,
                  arr
                ) => (
                  <div
                    key={label}
                    className={`flex-1 flex flex-col justify-center px-4 ${
                      i <
                      arr.length - 1
                        ? 'border-r border-[#1a1f35]/50'
                        : ''
                    }`}
                  >

                    <span className="text-[9px] tracking-widest text-slate-500 font-mono uppercase block mb-1">
                      {label}
                    </span>

                    <div className="flex items-baseline gap-2">

                      <span className="text-xl font-bold tracking-tight text-white">
                        {value}
                      </span>

                      {trend &&
                        (trend.dir ===
                        'down' ? (
                          <span className="text-[10px] text-red-500 flex items-center gap-0.5">
                            <TrendingDown className="w-3 h-3" />
                            {trend.txt}
                          </span>
                        ) : (
                          <span className="text-[10px] text-teal-400 flex items-center gap-0.5">
                            <TrendingUp className="w-3 h-3" />
                            {trend.txt}
                          </span>
                        ))}

                    </div>

                  </div>
                )
              )}

            </div>

            {/* SIMULATION BADGE */}

            {simState ===
              'SIMULATION_ACTIVE' && (
              <div className="absolute top-24 right-6 z-10 flex items-center gap-2 bg-red-950/70 border border-red-500/50 backdrop-blur-sm px-3.5 py-1.5 rounded text-red-400 font-mono text-[10px] tracking-widest uppercase shadow-[0_0_15px_rgba(239,68,68,0.15)] animate-pulse">

                <ShieldAlert className="w-3.5 h-3.5" />

                SIMULATION ACTIVE

              </div>
            )}

          </div>

          {/* ---------------------------------------------------------------- */}
          {/* RIGHT PANEL */}
          {/* ---------------------------------------------------------------- */}

          <aside className="w-90 h-full border-l border-[#1a1f35]/50 bg-[#05060b]/90 flex flex-col overflow-y-auto z-10">

            {currentTab ===
              'DASHBOARD' &&
              selectedRoadId && (
                <RoadDetailPanel />
              )}

            {currentTab ===
              'DASHBOARD' &&
              !selectedRoadId && (
                <div className="p-8 flex flex-col items-center justify-center text-center h-full text-slate-400 select-none relative overflow-hidden">

                  <div className="absolute inset-0 opacity-[0.015] bg-[linear-gradient(rgba(0,242,254,0.2)_1px,transparent_1px),linear-gradient(90deg,rgba(0,242,254,0.2)_1px,transparent_1px)] bg-[size:16px_16px] pointer-events-none" />

                  <div className="relative w-16 h-16 rounded bg-[#070b19]/60 border border-[#1a1f35] flex items-center justify-center mb-5">

                    <Layers className="w-6 h-6 text-[#00f2fe]/70 animate-pulse" />

                  </div>

                  <h3 className="text-[11px] font-bold font-mono tracking-[0.2em] text-slate-200 uppercase mb-2">
                    OPERATIONAL WORKSPACE
                  </h3>

                  <p className="text-[10px] text-slate-500 max-w-[240px] leading-relaxed">
                    Select a verified SETU route above and press SIMULATE to load the saved backend A* geometry.
                  </p>

                </div>
              )}

            {currentTab ===
              'NETWORK_ANALYSIS' && (
              <NetworkAnalysisPanel />
            )}

            {currentTab ===
              'SIMULATION' && (
              <SimulationPanel />
            )}

            {currentTab ===
              'CRITICALITY' && (
              <CriticalityPanel />
            )}

            {currentTab ===
              'REPORTS' && (
              <ReportsPanel />
            )}

            {currentTab ===
              'DATA_LAYERS' && (
              <div className="p-6">
                <MapLayersControl />
              </div>
            )}

            {currentTab ===
              'SETTINGS' && (
              <SettingsPanel />
            )}

          </aside>
        </div>
      </div>
    </div>
  );
};

export default DashboardView;