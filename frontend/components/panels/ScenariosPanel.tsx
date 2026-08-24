'use client';

import React from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { History, Zap } from 'lucide-react';

export const ScenariosPanel: React.FC = () => {
  const { scenarioHistory, selectRoad, startSimulation, setCurrentTab } = useSimulation();

  const handleOpenScenario = (roadId: string) => {
    selectRoad(roadId);
    setTimeout(() => {
      startSimulation();
    }, 150);
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto select-none">
      
      {/* Panel Header */}
      <div className="p-6 border-b border-[#1a1f35]/50 bg-slate-950/20">
        <span className="text-[8px] font-mono tracking-widest text-[#00f2fe] uppercase block mb-0.5">
          SIMULATION LOG
        </span>
        <h2 className="text-sm font-mono font-bold text-slate-200 tracking-wider">
          HYPOTHETICAL FAILURES
        </h2>
      </div>

      {/* Body List */}
      <div className="p-6 flex-1 flex flex-col gap-4 overflow-y-auto">
        <span className="text-[9px] tracking-widest text-slate-500 font-mono uppercase block mb-1">
          SCENARIO HISTORY ({scenarioHistory.length})
        </span>

        <div className="flex flex-col gap-3 font-mono text-[10px]">
          {scenarioHistory.length > 0 ? (
            scenarioHistory.map((item, idx) => (
              <div 
                key={`${item.failedRoadId}-${idx}`}
                onClick={() => handleOpenScenario(item.failedRoadId)}
                className="p-3.5 bg-slate-900/60 hover:bg-[#00f2fe]/5 border border-[#1a1f35] hover:border-[#00f2fe]/40 rounded cursor-pointer transition-all duration-200 group"
              >
                <div className="flex justify-between items-start mb-2">
                  <div className="flex flex-col">
                    <span className="text-white font-bold tracking-wide uppercase text-[11px] group-hover:text-[#00f2fe]">
                      {item.failedRoadName}
                    </span>
                    <span className="text-slate-500 text-[8px] mt-0.5">ID: {item.failedRoadId}</span>
                  </div>
                  <span className={`px-1.5 py-0.5 rounded text-[8px] font-bold ${
                    item.emergencyPriority === 'CRITICAL' ? 'bg-red-950/50 border border-red-800 text-red-400' :
                    item.emergencyPriority === 'HIGH' ? 'bg-amber-950/50 border border-amber-800 text-amber-400' : 'bg-emerald-950 border border-emerald-800 text-emerald-400'
                  }`}>
                    {item.emergencyPriority}
                  </span>
                </div>
                <div className="flex justify-between items-center text-[8.5px] text-slate-400 border-t border-[#1a1f35]/50 pt-2 mt-2">
                  <span>Pop Impacted: {item.populationAffected.toLocaleString()}</span>
                  <span>Hosp: {item.hospitalsImpacted}</span>
                </div>
              </div>
            ))
          ) : (
            <div className="bg-slate-900/40 border border-[#1a1f35] p-6 rounded text-slate-500 text-[9px] font-mono leading-relaxed text-center">
              <Zap className="w-5 h-5 text-slate-600 mx-auto mb-3" />
              No simulation scenarios have been run yet. Enter origin/destination areas and press SIMULATE to create your first failure scenario.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
export default ScenariosPanel;
