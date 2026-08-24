'use client';

import React from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { Zap } from 'lucide-react';

export const CriticalityPanel: React.FC = () => {
  const { criticalSegments, selectRoad, setFocusTarget, setCurrentTab, simState } = useSimulation();

  const handleSelectRoad = (roadId: string) => {
    selectRoad(roadId);
    setCurrentTab('DASHBOARD');
  };

  // Sort by score descending
  const ranked = [...criticalSegments].sort((a, b) => b.score - a.score);

  return (
    <div className="flex flex-col h-full overflow-y-auto select-none">
      
      {/* Panel Header */}
      <div className="p-6 border-b border-[#1a1f35]/50 bg-slate-950/20">
        <span className="text-[8px] font-mono tracking-widest text-[#00f2fe] uppercase block mb-0.5">
          NETWORK TOPOLOGY
        </span>
        <h2 className="text-sm font-mono font-bold text-slate-200 tracking-wider">
          CRITICAL CORRIDORS
        </h2>
      </div>

      {/* Ranked List */}
      <div className="p-6 flex-1 flex flex-col gap-4 overflow-y-auto">
        <span className="text-[9px] tracking-widest text-slate-500 font-mono uppercase block mb-1">
          CRITICALITY RANKINGS
        </span>

        {ranked.length > 0 ? (
          <div className="flex flex-col gap-2 font-mono">
            {ranked.map((seg, idx) => (
              <div
                key={seg.id}
                onClick={() => handleSelectRoad(seg.id)}
                className="flex justify-between items-center p-3.5 bg-slate-950/30 hover:bg-[#00f2fe]/5 border border-[#1a1f35] hover:border-[#00f2fe]/40 rounded cursor-pointer transition-all duration-300 group hover:shadow-[0_0_15px_rgba(0,242,254,0.05)]"
              >
                <div className="flex items-center gap-3">
                  <span className="text-[#00f2fe]/50 font-bold w-5 text-[10px] border-r border-[#1a1f35]/80 pr-2">
                    {(idx + 1).toString().padStart(2, '0')}
                  </span>
                  <div className="flex flex-col pl-1">
                    <span className="text-slate-200 font-bold group-hover:text-[#00f2fe] uppercase text-[11px] tracking-wide transition-colors duration-200">
                      {seg.name}
                    </span>
                    <span className="text-slate-500 text-[8px] mt-0.5 tracking-wider">ID: {seg.id}</span>
                  </div>
                </div>

                <div className="flex flex-col items-end gap-1.5">
                  <span className="text-slate-300 text-[10.5px] font-bold tracking-wider">
                    {seg.score.toFixed(3)}
                  </span>
                  <span className={`text-[7.5px] px-1.5 py-0.5 rounded font-black tracking-widest uppercase border ${
                    seg.criticality === 'CRITICAL' 
                      ? 'bg-red-950/40 border-red-500/30 text-red-400 shadow-[0_0_10px_rgba(239,68,68,0.1)]' 
                      : seg.criticality === 'HIGH' 
                      ? 'bg-amber-950/40 border-amber-500/30 text-amber-400 shadow-[0_0_10px_rgba(245,158,11,0.1)]' 
                      : 'bg-slate-900/40 border-slate-700/30 text-slate-400'
                  }`}>
                    {seg.criticality}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-slate-900/40 border border-[#1a1f35] p-6 rounded text-slate-500 text-[9px] font-mono leading-relaxed text-center">
            <Zap className="w-5 h-5 text-slate-600 mx-auto mb-3" />
            {simState === 'SIMULATION_ACTIVE' 
              ? 'No critical segments identified in this zone.'
              : 'Run a failure simulation to compute critical corridor rankings from the live road network graph.'}
          </div>
        )}
      </div>
    </div>
  );
};
export default CriticalityPanel;
