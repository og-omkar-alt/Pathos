'use client';

import React, { useState } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { Activity } from 'lucide-react';

export const NetworkAnalysisPanel: React.FC = () => {
  const { networkSummary, simulationResult, simState } = useSimulation();
  const [analysisMode, setAnalysisMode] = useState<'baseline' | 'compare'>('baseline');

  const nodes = networkSummary?.nodes ?? 0;
  const edges = networkSummary?.edges ?? 0;
  const meanDegree = networkSummary?.mean_degree ?? 0;
  const totalKm = networkSummary?.total_km ?? 0;
  const connectivity = networkSummary?.connectivity ?? 0;
  const components = networkSummary?.components ?? 0;

  return (
    <div className="flex flex-col h-full overflow-y-auto select-none">
      
      {/* Panel Header */}
      <div className="p-6 border-b border-[#1a1f35]/50 bg-slate-950/20">
        <span className="text-[8px] font-mono tracking-widest text-[#00f2fe] uppercase block mb-0.5">
          NETWORK METRICS
        </span>
        <h2 className="text-sm font-mono font-bold text-slate-200 tracking-wider">
          TOPOLOGY ANALYSIS
        </h2>
      </div>

      {/* Analysis Mode Selector */}
      <div className="px-6 pt-5">
        <div className="flex gap-2">
          {['baseline', 'compare'].map((m) => (
            <button
              key={m}
              onClick={() => setAnalysisMode(m as any)}
              className={`flex-1 py-1.5 border rounded uppercase text-[8.5px] font-mono font-bold text-center cursor-pointer transition-all ${
                analysisMode === m 
                  ? 'border-[#00f2fe] bg-[#00f2fe]/10 text-[#00f2fe]' 
                  : 'border-[#1a1f35] bg-slate-900/40 text-slate-500 hover:border-slate-600'
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* Main Details */}
      <div className="p-6 flex-1 flex flex-col gap-5 overflow-y-auto font-mono text-[10px]">
        
        {analysisMode === 'baseline' ? (
          <div className="flex flex-col gap-4">
            <span className="text-[9px] tracking-widest text-slate-500 uppercase font-bold block mb-1">
              BASELINE GRAPH STATS
            </span>

            <div className="flex flex-col gap-2.5 bg-slate-900/40 border border-[#1a1f35] p-4 rounded text-slate-300">
              <div className="flex justify-between py-1 border-b border-[#1a1f35]/20">
                <span>GRAPH NODES</span>
                <span className="text-white font-bold">{nodes.toLocaleString()}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1a1f35]/20">
                <span>GRAPH EDGES</span>
                <span className="text-white font-bold">{edges.toLocaleString()}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1a1f35]/20">
                <span>MEAN DEGREE</span>
                <span className="text-white font-bold">{meanDegree}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1a1f35]/20">
                <span>TOTAL ROAD COVERAGE</span>
                <span className="text-white font-bold">{totalKm} km</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1a1f35]/20">
                <span>CONNECTED COMPONENTS</span>
                <span className="text-white font-bold">{components}</span>
              </div>
              <div className="flex justify-between py-1">
                <span>CONNECTIVITY</span>
                <span className="text-[#00f2fe] font-bold">{connectivity}%</span>
              </div>
            </div>

            <span className="text-[9px] tracking-widest text-slate-500 uppercase font-bold block mb-1 mt-2">
              PERFORMANCE OVERVIEW
            </span>
            <div className="flex flex-col gap-2 bg-slate-900/40 border border-[#1a1f35] p-4 rounded text-slate-400 leading-relaxed text-[9px]">
              <div className="flex items-center gap-1.5 text-slate-300 font-bold mb-1.5 uppercase text-[9.5px]">
                <Activity className="w-3.5 h-3.5 text-[#00f2fe]" />
                Connectivity Profile
              </div>
              SAR-derived road network with {nodes.toLocaleString()} junction nodes and {edges.toLocaleString()} road segments spanning {totalKm} km. Network has {components} connected components with {connectivity}% of nodes in the largest component.
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <span className="text-[9px] tracking-widest text-slate-500 uppercase font-bold block mb-1">
              SCENARIO COMPARISONS
            </span>

            {simState === 'SIMULATION_ACTIVE' && simulationResult ? (
              <div className="flex flex-col gap-2.5 bg-slate-900/40 border border-[#1a1f35] p-4 rounded text-slate-300">
                <div className="flex justify-between py-1 border-b border-[#1a1f35]/20">
                  <span>CONNECTIVITY BEFORE</span>
                  <span className="text-white font-bold">{simulationResult.connectivityBefore}%</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1a1f35]/20">
                  <span>CONNECTIVITY AFTER</span>
                  <span className="text-red-400 font-bold">{simulationResult.connectivityAfter}%</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1a1f35]/20">
                  <span>RESILIENCE BEFORE</span>
                  <span className="text-white font-bold">{simulationResult.resilienceBefore}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1a1f35]/20">
                  <span>RESILIENCE AFTER</span>
                  <span className="text-red-400 font-bold">{simulationResult.resilienceAfter}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span>DISCONNECTED CLUSTERS</span>
                  <span className="text-amber-400 font-bold">{simulationResult.disconnectedWards}</span>
                </div>
              </div>
            ) : (
              <div className="bg-slate-900/40 border border-[#1a1f35] p-4 rounded text-slate-500 text-[9px] leading-relaxed text-center py-8">
                No active failure comparison selected. Run a network failure simulation, then switch to Compare Mode to visualize composite criticality index shifts.
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
};
export default NetworkAnalysisPanel;
