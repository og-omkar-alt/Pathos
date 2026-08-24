'use client';

import React from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { demoScenarios } from '../../data/demoScenarios';
import {
  CheckCircle2,
  Loader2,
  RotateCcw,
  Activity,
  Users,
  HeartPulse,
  Route,
  Zap,
  AlertTriangle,
} from 'lucide-react';

export const SimulationPanel: React.FC = () => {
  const {
    simState,
    loaderSteps,
    simulationResult,
    resetScenario,
    scenarioHistory,
    startSimulation,
    routeResult,
    alternateRoutes,
    setOriginCoords,
    setDestCoords,
  } = useSimulation();

  // ── ANALYZING state — show loader ─────────────────────────────────────────
  if (simState === 'ANALYZING') {
    return (
      <div className="flex flex-col h-full bg-[#05060b] select-none p-6 justify-center">
        <div className="flex flex-col gap-6 max-w-sm mx-auto w-full">
          <div className="flex items-center gap-3 mb-2 border-b border-[#1a1f35]/50 pb-4">
            <Loader2 className="w-5 h-5 text-[#00f2fe] animate-spin" />
            <div>
              <span className="text-[10px] font-mono tracking-widest text-[#00f2fe] uppercase block">
                ANALYSIS PIPELINE
              </span>
              <h2 className="text-xs font-mono font-bold text-slate-200 tracking-wider">
                CREATING FAILURE SCENARIO
              </h2>
            </div>
          </div>

          <div className="flex flex-col gap-3 font-mono text-xs text-slate-400">
            {loaderSteps.map((step) => (
              <div key={step.id} className="flex justify-between items-center py-1">
                <span>{step.label}</span>
                <span className="text-slate-500">
                  {step.status === 'pending' && '........ -'}
                  {step.status === 'loading' && (
                    <span className="text-[#00f2fe] flex items-center gap-1.5">
                      ........ <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    </span>
                  )}
                  {step.status === 'done' && (
                    <span className="text-emerald-400 flex items-center gap-1.5 font-bold">
                      ........ ✓
                    </span>
                  )}
                </span>
              </div>
            ))}
          </div>

          {loaderSteps.every((step) => step.status === 'done') && (
            <div className="mt-4 p-3 bg-emerald-950/20 border border-emerald-500/30 rounded
                            flex items-center gap-2.5 text-emerald-400 font-mono text-[10px]
                            tracking-widest uppercase animate-pulse">
              <CheckCircle2 className="w-4 h-4" />
              SCENARIO READY
            </div>
          )}
        </div>
      </div>
    );
  }

  // ── SIMULATION_ACTIVE — show results ──────────────────────────────────────
  if (simState === 'SIMULATION_ACTIVE') {

    // Guard: simulationResult may arrive slightly after simState flips
    if (!simulationResult) {
      return (
        <div className="flex flex-col items-center justify-center h-full gap-3 select-none">
          <Loader2 className="w-6 h-6 text-[#00f2fe] animate-spin" />
          <span className="text-slate-500 font-mono text-[10px] tracking-widest uppercase">
            LOADING SIMULATION DATA...
          </span>
        </div>
      );
    }

    const priorityColors: Record<string, string> = {
      CRITICAL: 'text-red-500 bg-red-950/20 border-red-500/40',
      HIGH:     'text-amber-500 bg-amber-950/20 border-amber-500/40',
      MEDIUM:   'text-emerald-500 bg-emerald-950/20 border-emerald-500/40',
      LOW:      'text-slate-500 bg-slate-900 border-slate-700',
    };

    const priority      = simulationResult?.emergencyPriority ?? 'HIGH';
    const priorityClass = priorityColors[priority] ?? priorityColors.HIGH;

    return (
      <div className="flex flex-col h-full overflow-y-auto select-none">

        {/* Header */}
        <div className="p-6 border-b border-[#1a1f35]/50 flex items-center justify-between bg-red-950/5">
          <div>
            <span className="text-[8px] font-mono tracking-widest text-red-400 uppercase block mb-0.5 font-bold">
              SCENARIO DISRUPTION
            </span>
            <h2 className="text-xs font-mono font-bold text-slate-200 tracking-wider truncate max-w-[200px]">
              {simulationResult?.failedRoadName ?? 'Unknown Corridor'} FAILURE
            </h2>
          </div>
          <div className="px-2 py-0.5 rounded bg-red-950/50 border border-red-800
                          text-[8px] font-mono text-red-400 font-bold uppercase tracking-widest">
            SIM MODE
          </div>
        </div>

        <div className="p-6 flex-1 flex flex-col gap-5 overflow-y-auto">
          <span className="text-[9px] tracking-widest text-slate-500 font-mono uppercase block mb-1">
            SIMULATION SUMMARY
          </span>

          {/* Priority card */}
          <div className={`p-4 rounded border flex items-center justify-between ${priorityClass}`}>
            <div className="flex flex-col">
              <span className="text-[8px] font-mono tracking-widest opacity-80 uppercase mb-0.5">
                EMERGENCY PRIORITY
              </span>
              <span className="text-md font-bold tracking-wider font-mono">{priority}</span>
              <span className="text-[8px] font-mono opacity-60 mt-1 block max-w-[160px] leading-tight">
                IMMEDIATE RESPONSE STRATEGY RECOMMENDED
              </span>
            </div>
            <div className="text-right">
              <span className="text-xs font-mono opacity-80 block uppercase text-[8px]">PRIORITY SCORE</span>
              <span className="text-2xl font-black font-mono tracking-tighter">
                {(simulationResult?.priorityScore ?? 0).toFixed(2)}
              </span>
            </div>
          </div>

          {/* Resilience */}
          <div className="border-t border-[#1a1f35]/30 pt-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-[#00f2fe]" />
              <div className="flex flex-col">
                <span className="text-[10px] font-mono font-bold text-slate-200 tracking-wider uppercase">
                  NETWORK RESILIENCE
                </span>
                <span className="text-[8px] font-mono text-slate-500">Structural integrity drop</span>
              </div>
            </div>
            <div className="font-mono text-xs font-bold text-white bg-slate-900 border border-[#1a1f35] px-2 py-1 rounded">
              {(simulationResult?.resilienceBefore ?? 0).toFixed(2)}
              {' → '}
              <span className="text-red-400">
                {(simulationResult?.resilienceAfter ?? 0).toFixed(2)}
              </span>
            </div>
          </div>

          {/* Disconnected clusters */}
          <div className="border-t border-[#1a1f35]/30 pt-4 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                <div className="flex flex-col">
                  <span className="text-[10px] font-mono font-bold text-slate-200 tracking-wider uppercase">
                    DISCONNECTED CLUSTERS
                  </span>
                  <span className="text-[8px] font-mono text-slate-500">Access isolation severity</span>
                </div>
              </div>
              <span className="text-xs font-bold font-mono text-amber-400">
                {simulationResult?.disconnectedWards ?? 0} Clusters
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5 mt-1">
              {Array.from({ length: Math.min(simulationResult?.disconnectedWards ?? 0, 6) }).map((_, idx) => (
                <span key={idx}
                      className="bg-red-950/20 border border-red-900/35 px-2 py-0.5 rounded
                                 text-[9px] font-mono text-red-400">
                  ISOLATED-ZONE-0{idx + 1}
                </span>
              ))}
            </div>
          </div>

          {/* Population affected */}
          <div className="border-t border-[#1a1f35]/30 pt-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-amber-400" />
              <div className="flex flex-col">
                <span className="text-[10px] font-mono font-bold text-slate-200 tracking-wider uppercase">
                  POPULATION AFFECTED
                </span>
                <span className="text-[8px] font-mono text-slate-500">Estimated urban impact</span>
              </div>
            </div>
            <span className="text-xs font-bold font-mono text-amber-400">
              {(simulationResult?.populationAffected ?? 0).toLocaleString()}
            </span>
          </div>

          {/* Hospitals impacted */}
          <div className="border-t border-[#1a1f35]/30 pt-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <HeartPulse className="w-4 h-4 text-red-400" />
              <div className="flex flex-col">
                <span className="text-[10px] font-mono font-bold text-slate-200 tracking-wider uppercase">
                  HOSPITALS IMPACTED
                </span>
                <span className="text-[8px] font-mono text-slate-500">Degraded medical corridors</span>
              </div>
            </div>
            <span className="text-xs font-bold font-mono text-red-400">
              {simulationResult?.hospitalsImpacted ?? 0} Impacted
            </span>
          </div>

          {/* Routes computed */}
          <div className="border-t border-[#1a1f35]/30 pt-4 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Route className="w-4 h-4 text-[#00f2fe]" />
                <div className="flex flex-col">
                  <span className="text-[10px] font-mono font-bold text-slate-200 tracking-wider uppercase">
                    ROUTES COMPUTED
                  </span>
                  <span className="text-[8px] font-mono text-slate-500">Live A* Pathfinding</span>
                </div>
              </div>
              <span className="text-xs font-bold font-mono text-[#00f2fe]">Dynamic Route ✓</span>
            </div>

            {routeResult?.status === 'success' && routeResult.metrics && (
              <div className="ml-6 flex flex-col gap-1 text-[9px] font-mono text-slate-400">
                <div className="flex justify-between">
                  <span className="text-[#00f2fe]">PRIMARY</span>
                  <span>
                    {routeResult.metrics.distance_km} km
                    {' · '}
                    {routeResult.metrics.estimated_time_mins} min
                  </span>
                </div>
                {alternateRoutes.map((alt, idx) =>
                  alt.status === 'success' && alt.metrics ? (
                    <div key={idx} className="flex justify-between">
                      <span className={idx === 0 ? 'text-[#a855f7]' : 'text-[#f59e0b]'}>
                        ALT {idx + 1}
                      </span>
                      <span>
                        {alt.metrics.distance_km} km · {alt.metrics.estimated_time_mins} min
                      </span>
                    </div>
                  ) : null
                )}
              </div>
            )}
          </div>

          {/* Reset */}
          <div className="mt-auto border-t border-[#1a1f35]/50 pt-4">
            <button
              onClick={resetScenario}
              className="w-full flex items-center justify-center gap-2 py-3
                         bg-slate-900 hover:bg-slate-800 border border-[#1a1f35]
                         hover:border-slate-500 rounded text-slate-300 hover:text-white
                         font-mono text-xs tracking-[0.2em] font-semibold
                         transition-all duration-300 cursor-pointer shadow-lg"
            >
              <RotateCcw className="w-4 h-4" />
              RESET SCENARIO
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Default — scenario selector ───────────────────────────────────────────
  const scenarioEndpoints: Record<string, {
    start: { lat: number; lon: number };
    destination: { lat: number; lon: number };
  }> = {
    scenario_1: { start: { lat: 23.12779, lon: 72.62634 }, destination: { lat: 23.17409, lon: 72.51987 } },
    scenario_2: { start: { lat: 23.05150, lon: 72.53000 }, destination: { lat: 23.10550, lon: 72.57000 } },
    scenario_3: { start: { lat: 23.02250, lon: 72.57140 }, destination: { lat: 23.06200, lon: 72.59400 } },
    scenario_4: { start: { lat: 23.00000, lon: 72.60000 }, destination: { lat: 23.03000, lon: 72.63000 } },
    scenario_5: { start: { lat: 23.09000, lon: 72.57000 }, destination: { lat: 23.12000, lon: 72.59000 } },
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto select-none">
      <div className="p-6 border-b border-[#1a1f35]/50 bg-slate-950/20">
        <span className="text-[8px] font-mono tracking-widest text-[#00f2fe] uppercase block mb-0.5">
          SIMULATION CONSOLE
        </span>
        <h2 className="text-sm font-mono font-bold text-slate-200 tracking-wider">FAILURE WORKFLOW</h2>
      </div>

      <div className="p-6 flex-1 flex flex-col gap-6 overflow-y-auto">
        {/* Scenario picker */}
        <div className="p-4 bg-[#0a0d14] border border-[#00f2fe]/30 rounded text-slate-400
                        text-[9px] font-mono shadow-[0_0_15px_rgba(0,242,254,0.1)]">
          <div className="flex items-center gap-2 text-[#00f2fe] font-bold mb-3 uppercase tracking-widest text-[10px]">
            <Zap className="w-4 h-4 animate-pulse" />
            SELECT PITCH SCENARIO
          </div>

          <select
            defaultValue=""
            className="w-full bg-[#05060b] border border-[#1a1f35] text-slate-200 text-xs
                       font-mono p-3 rounded outline-none cursor-pointer
                       hover:border-[#00f2fe]/50 transition-colors"
            onChange={(event) => {
              const scenarioId = event.target.value;
              if (!scenarioId) return;

              const scenario = demoScenarios[scenarioId as keyof typeof demoScenarios];
              if (!scenario?.routeCoords?.length) {
                console.warn('Selected scenario has no route coords.');
                return;
              }

              const endpoints = scenarioEndpoints[scenarioId];
              const start       = endpoints?.start       ?? { lat: 23.12779, lon: 72.62634 };
              const destination = endpoints?.destination ?? { lat: 23.17409, lon: 72.51987 };

              setOriginCoords(start);
              setDestCoords(destination);
              startSimulation(start, destination);
            }}
          >
            <option value="">-- Choose a verified route scenario --</option>
            <option value="scenario_1">{demoScenarios.scenario_1.label}</option>
            <option value="scenario_2">{demoScenarios.scenario_2.label}</option>
            <option value="scenario_3">{demoScenarios.scenario_3.label}</option>
            <option value="scenario_4">{demoScenarios.scenario_4.label}</option>
            <option value="scenario_5">{demoScenarios.scenario_5.label}</option>
          </select>
        </div>

        {/* Scenario history */}
        <div className="flex flex-col gap-3 font-mono text-[10px] mt-2">
          <span className="text-[9px] tracking-widest text-slate-500 uppercase font-bold block mb-1">
            PREVIOUS FAILURE TESTS
          </span>

          {scenarioHistory.length > 0 ? (
            scenarioHistory.map((item, idx) => (
              <div key={`${item.failedRoadId}-${idx}`}
                   className="p-3.5 bg-slate-900/60 border border-[#1a1f35] rounded">
                <div className="flex justify-between items-start mb-2">
                  <div className="flex flex-col">
                    <span className="text-white font-bold tracking-wide uppercase text-[11px]">
                      {item.failedRoadName}
                    </span>
                    <span className="text-slate-500 text-[8px] mt-0.5">ID: {item.failedRoadId}</span>
                  </div>
                  <span className="px-1.5 py-0.5 rounded text-[8px] font-bold
                                   bg-amber-950/50 border border-amber-800 text-amber-400">
                    {item.emergencyPriority}
                  </span>
                </div>
                <div className="flex justify-between items-center text-[8.5px] text-slate-400
                                border-t border-[#1a1f35]/50 pt-2 mt-2">
                  <span>Pop Impacted: {(item.populationAffected ?? 0).toLocaleString()}</span>
                  <span>Hosp: {item.hospitalsImpacted ?? 0}</span>
                </div>
              </div>
            ))
          ) : (
            <div className="bg-slate-900/40 border border-[#1a1f35] p-4 rounded
                            text-slate-500 text-[9px] text-center">
              No simulation history yet.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SimulationPanel;