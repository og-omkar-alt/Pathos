'use client';

import React from 'react';
import { useSimulation } from '../../context/SimulationContext';

export const MapLegend: React.FC = () => {
  const { simState } = useSimulation();

  return (
    <div className="absolute bottom-32 right-6 z-10 bg-[#070b19]/80 border border-[#1a1f35] backdrop-blur-md rounded p-3 shadow-xl select-none font-mono text-[9px] tracking-wider text-slate-300">
      
      <div className="text-[10px] font-bold text-slate-200 border-b border-[#1a1f35]/50 pb-1.5 mb-2 uppercase">
        LEGEND
      </div>

      <div className="flex flex-col gap-2">
        {/* Criticality states */}
        <div className="flex flex-col gap-1.5">
          <span className="text-[8px] text-slate-500 uppercase font-bold tracking-widest block mb-0.5">
            ROAD CRITICALITY
          </span>
          <div className="flex items-center gap-2">
            <span className="w-4 h-0.5 bg-[#ef4444]" />
            <span>HIGH</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-0.5 bg-[#f59e0b]" />
            <span>MEDIUM</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-0.5 bg-[#10b981]" />
            <span>LOW</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-0.5 bg-[#64748b]" />
            <span>VERY LOW</span>
          </div>
        </div>

        {/* Simulation states */}
        {simState === 'SIMULATION_ACTIVE' && (
          <div className="flex flex-col gap-1.5 border-t border-[#1a1f35]/50 pt-2 mt-1">
            <span className="text-[8px] text-slate-500 uppercase font-bold tracking-widest block mb-0.5">
              SIMULATION DISRUPTION
            </span>
            <div className="flex items-center gap-2">
              <span className="w-4 h-0.5 border-t-2 border-dashed border-red-500" />
              <span className="text-red-400 font-bold">FAILED ROAD</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 bg-red-950/40 border border-red-800/60 rounded-sm" />
              <span>AFFECTED WARD</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-4 h-0.5 border-t-2 border-dashed border-[#00f2fe]" />
              <span className="text-[#00f2fe]">DETOUR ROUTE</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 bg-red-500 border border-red-300 rounded-full flex items-center justify-center text-[7px] text-white font-bold">H</span>
              <span>IMPACTED HOSPITAL</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
