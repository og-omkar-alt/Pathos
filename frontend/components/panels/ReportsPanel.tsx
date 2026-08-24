'use client';

import React, { useState } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { Download, Check, AlertCircle } from 'lucide-react';

export const ReportsPanel: React.FC = () => {
  const { simulationResult, simState, networkSummary, routeResult } = useSimulation();
  const [downloading, setDownloading] = useState(false);
  const [downloaded, setDownloaded] = useState(false);

  const handleExport = () => {
    setDownloading(true);
    setTimeout(() => {
      setDownloading(false);
      setDownloaded(true);
      
      const content = `SETU - FAILURE SCENARIO REPORT\n\n` +
        `Generated: ${new Date().toISOString()}\n` +
        `Target Corridor: ${simulationResult?.failedRoadName || 'N/A'} (${simulationResult?.failedRoadId || 'N/A'})\n` +
        `----------------------------------------\n` +
        `1. Connectivity Before: ${simulationResult?.connectivityBefore ?? 'N/A'}%\n` +
        `2. Connectivity After: ${simulationResult?.connectivityAfter ?? 'N/A'}%\n` +
        `3. Disconnected Clusters: ${simulationResult?.disconnectedWards ?? 'N/A'}\n` +
        `4. Population Impacted: ${simulationResult?.populationAffected?.toLocaleString() ?? 'N/A'} citizens\n` +
        `5. Hospitals Impacted: ${simulationResult?.hospitalsImpacted ?? 'N/A'}\n` +
        `6. Resilience: ${simulationResult?.resilienceBefore ?? 'N/A'} → ${simulationResult?.resilienceAfter ?? 'N/A'}\n` +
        `7. Emergency Priority: ${simulationResult?.emergencyPriority ?? 'N/A'} (Score: ${simulationResult?.priorityScore ?? 'N/A'})\n` +
        `----------------------------------------\n` +
        (routeResult ? 
          `ROUTE METRICS:\n` +
          `  Distance: ${routeResult.metrics.distance_km} km\n` +
          `  Est. Time: ${routeResult.metrics.estimated_time_mins} min\n` +
          `  Avg Congestion: ${routeResult.metrics.avg_congestion_multiplier}x\n` +
          `  Segments: ${routeResult.metrics.segments_count}\n` +
          `----------------------------------------\n` : '') +
        `INFRASTRUCTURE ASSESSMENT REPORT - LIVE ENVIRONMENT`;

      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `SETU-Report-${simulationResult?.failedRoadId || 'baseline'}.txt`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      setTimeout(() => setDownloaded(false), 3000);
    }, 1500);
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto select-none">
      
      {/* Panel Header */}
      <div className="p-6 border-b border-[#1a1f35]/50 bg-slate-950/20">
        <span className="text-[8px] font-mono tracking-widest text-[#00f2fe] uppercase block mb-0.5">
          REPORT LAYER
        </span>
        <h2 className="text-sm font-mono font-bold text-slate-200 tracking-wider">
          RESILIENCE ASSESSMENT
        </h2>
      </div>

      {/* Body details */}
      <div className="p-6 flex-1 flex flex-col gap-5 overflow-y-auto font-mono text-[10px]">
        
        {simState !== 'SIMULATION_ACTIVE' ? (
          // Baseline state report summary
          <div className="flex flex-col gap-4">
            <span className="text-[9px] tracking-widest text-slate-500 uppercase block">
              BASELINE REPORT
            </span>
            <div className="p-4 bg-slate-900/40 border border-[#1a1f35] rounded leading-relaxed text-slate-400 text-[9.5px]">
              <div className="flex items-center gap-2 text-slate-300 font-bold mb-2">
                <AlertCircle className="w-4 h-4 text-[#00f2fe]" />
                SYSTEM RUNNING OPTIMALLY
              </div>
              Network has {networkSummary?.nodes?.toLocaleString() ?? '—'} nodes across {networkSummary?.components ?? '—'} components. 
              Total road coverage: {networkSummary?.total_km ?? '—'} km. 
              Connectivity: {networkSummary?.connectivity ?? '—'}%. 
              No simulated failures are active.
            </div>
          </div>
        ) : (
          // Simulation active report summary
          simulationResult && (
            <div className="flex flex-col gap-5">
              <span className="text-[9px] tracking-widest text-slate-500 uppercase block">
                SCENARIO DISRUPTION SUMMARY
              </span>
              
              <div className="flex flex-col gap-3 bg-slate-900/60 border border-[#1a1f35] p-4 rounded text-slate-300">
                <div className="flex justify-between pb-2 border-b border-[#1a1f35]/40 font-bold">
                  <span>DISRUPTED CORRIDOR</span>
                  <span className="text-red-400">{simulationResult.failedRoadName}</span>
                </div>

                <div className="flex justify-between py-1 border-b border-[#1a1f35]/20">
                  <span>CONNECTIVITY</span>
                  <span>{simulationResult.connectivityBefore}% → <span className="text-red-400 font-bold">{simulationResult.connectivityAfter}%</span></span>
                </div>

                <div className="flex justify-between py-1 border-b border-[#1a1f35]/20">
                  <span>DISCONNECTED CLUSTERS</span>
                  <span>{simulationResult.disconnectedWards}</span>
                </div>

                <div className="flex justify-between py-1 border-b border-[#1a1f35]/20">
                  <span>POPULATION IMPACTED</span>
                  <span>{simulationResult.populationAffected.toLocaleString()}</span>
                </div>

                <div className="flex justify-between py-1 border-b border-[#1a1f35]/20">
                  <span>HOSPITALS IMPACTED</span>
                  <span className="text-red-400">{simulationResult.hospitalsImpacted}</span>
                </div>

                <div className="flex justify-between pt-1">
                  <span>EMERGENCY PRIORITY</span>
                  <span className="text-red-400 font-bold">{simulationResult.emergencyPriority}</span>
                </div>
              </div>

              {/* Route metrics if available */}
              {routeResult && routeResult.status === 'success' && (
                <div className="flex flex-col gap-3 bg-slate-900/60 border border-[#1a1f35] p-4 rounded text-slate-300">
                  <div className="font-bold text-[#00f2fe] border-b border-[#1a1f35]/40 pb-2">
                    ROUTE ANALYSIS
                  </div>
                  <div className="flex justify-between py-1 border-b border-[#1a1f35]/20">
                    <span>DISTANCE</span>
                    <span className="text-white font-bold">{routeResult.metrics.distance_km} km</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-[#1a1f35]/20">
                    <span>EST. TRAVEL TIME</span>
                    <span className="text-white font-bold">{routeResult.metrics.estimated_time_mins} min</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-[#1a1f35]/20">
                    <span>AVG CONGESTION</span>
                    <span className="text-white font-bold">{routeResult.metrics.avg_congestion_multiplier}×</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span>ROAD SEGMENTS</span>
                    <span className="text-white font-bold">{routeResult.metrics.segments_count}</span>
                  </div>
                </div>
              )}

              {/* Action Button: EXPORT REPORT */}
              <div className="pt-2">
                <button
                  onClick={handleExport}
                  disabled={downloading}
                  className="w-full flex items-center justify-center gap-2 py-3 bg-[#00f2fe]/10 hover:bg-[#00f2fe]/20 border border-[#00f2fe]/40 hover:border-[#00f2fe] rounded text-[#00f2fe] hover:text-white font-mono text-xs tracking-[0.2em] font-semibold transition-all duration-300 cursor-pointer shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {downloading ? (
                    <span>COMPILING DATA...</span>
                  ) : downloaded ? (
                    <span className="flex items-center gap-1.5 text-emerald-400">
                      <Check className="w-4 h-4" /> REPORT EXPORTED
                    </span>
                  ) : (
                    <>
                      <Download className="w-4 h-4" />
                      EXPORT REPORT
                    </>
                  )}
                </button>
              </div>
            </div>
          )
        )}
      </div>
    </div>
  );
};
export default ReportsPanel;
