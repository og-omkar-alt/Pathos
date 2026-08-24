'use client';

import React from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { Layers, Eye, EyeOff } from 'lucide-react';

interface MapLayersControlProps {
  onClose?: () => void;
}

export const MapLayersControl: React.FC<MapLayersControlProps> = () => {
  const { layers, toggleLayer } = useSimulation();

  const LayerToggle: React.FC<{
    label: string;
    description: string;
    active: boolean;
    onClick: () => void;
  }> = ({ label, description, active, onClick }) => (
    <button
      onClick={onClick}
      className={`w-full flex items-center justify-between py-2 px-1 hover:bg-slate-900/50 rounded transition-colors text-left font-mono select-none cursor-pointer`}
    >
      <div className="flex-1 min-w-0 pr-2">
        <span className="text-[10px] font-bold text-slate-200 tracking-wider block uppercase">
          {label}
        </span>
        <span className="text-[8px] text-slate-500 block truncate">
          {description}
        </span>
      </div>
      <div className={`p-1 rounded ${active ? 'text-[#00f2fe]' : 'text-slate-600'}`}>
        {active ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
      </div>
    </button>
  );

  return (
    <div className="flex flex-col gap-2.5">
      <div className="flex items-center gap-1.5 border-b border-[#1a1f35]/50 pb-2 mb-1 select-none">
        <Layers className="w-3.5 h-3.5 text-[#00f2fe]" />
        <span className="text-[10px] font-bold font-mono tracking-widest text-[#00f2fe] uppercase">
          MAP LAYERS
        </span>
      </div>

      <div className="flex flex-col gap-1.5">
        <LayerToggle
          label="Road Network"
          description="Baseline urban road links"
          active={layers.roads}
          onClick={() => toggleLayer('roads')}
        />
        <LayerToggle
          label="Road Criticality"
          description="Color corridors by centrality"
          active={layers.criticality}
          onClick={() => toggleLayer('criticality')}
        />
        <LayerToggle
          label="Ward Boundaries"
          description="Administrative limits"
          active={layers.wards}
          onClick={() => toggleLayer('wards')}
        />
        <LayerToggle
          label="Medical Centers"
          description="Emergency & general hospitals"
          active={layers.hospitals}
          onClick={() => toggleLayer('hospitals')}
        />
        <LayerToggle
          label="Population Density"
          description="Citizen density heat layer"
          active={layers.population}
          onClick={() => toggleLayer('population')}
        />
        <LayerToggle
          label="Satellite Imagery"
          description="High res base layer toggle"
          active={layers.satellite}
          onClick={() => toggleLayer('satellite')}
        />
      </div>
    </div>
  );
};
