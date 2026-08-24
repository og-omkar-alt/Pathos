'use client';

import React from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { ShieldAlert, BarChart2, MapPin } from 'lucide-react';

export const RoadDetailPanel: React.FC = () => {
  const { selectedRoadId, startSimulation, selectRoad } = useSimulation();

  if (!selectedRoadId) return null;

  return (
    <div className="flex flex-col h-full overflow-y-auto select-none">
      
      {/* Panel Header */}
      <div className="p-6 border-b border-[#1a1f35]/50 flex items-center justify-between bg-slate-950/20">
        <div>
          <span className="text-[8px] font-mono tracking-widest text-[#00f2fe] uppercase block mb-0.5">
            SELECTED CORRIDOR
          </span>
          <h2 className="text-sm font-mono font-bold text-slate-200 tracking-wider">
            {selectedRoadId}
          </h2>
        </div>
        <button
          onClick={() => selectRoad(null)}
          className="text-xs font-mono text-slate-500 hover:text-slate-200 cursor-pointer"
        >
          CLOSE [ESC]
        </button>
      </div>

      {/* Main Details */}
      <div className="p-6 flex-1 flex flex-col gap-6">
        
        <div>
          <span className="text-[9px] tracking-widest text-slate-500 font-mono uppercase block mb-1">
            Road Segment
          </span>
          <span className="text-lg font-bold text-white tracking-wider block">
            {selectedRoadId}
          </span>
          <div className="flex items-center gap-4 mt-2 font-mono text-xs text-slate-400">
            <div>
              <span className="text-slate-600">ID:</span> {selectedRoadId}
            </div>
          </div>
        </div>

        <div className="border-t border-[#1a1f35]/30 pt-5">
          <span className="text-[9px] tracking-widest text-slate-500 font-mono uppercase block mb-3 flex items-center gap-1.5">
            <BarChart2 className="w-3.5 h-3.5 text-[#00f2fe]" />
            SEGMENT INFO
          </span>
          <div className="bg-slate-900/40 border border-[#1a1f35] p-4 rounded text-slate-400 text-[9px] font-mono leading-relaxed">
            This road segment is part of the SAR-derived road network loaded from the backend graph. Click SIMULATE FAILURE below to test the impact of disrupting this corridor on the overall network.
          </div>
        </div>

        {/* Action Button: SIMULATE FAILURE */}
        <div className="mt-auto border-t border-[#1a1f35]/50 pt-5">
          <button
            onClick={startSimulation}
            className="w-full flex items-center justify-center gap-2 py-3 bg-red-950/40 hover:bg-red-950/80 border border-red-500/50 hover:border-red-400 rounded text-red-400 hover:text-white font-mono text-xs tracking-[0.2em] font-semibold transition-all duration-300 cursor-pointer shadow-[0_0_15px_rgba(239,68,68,0.1)] hover:shadow-[0_0_20px_rgba(239,68,68,0.25)]"
          >
            <ShieldAlert className="w-4 h-4" />
            SIMULATE FAILURE
          </button>
        </div>

      </div>
    </div>
  );
};
export default RoadDetailPanel;
