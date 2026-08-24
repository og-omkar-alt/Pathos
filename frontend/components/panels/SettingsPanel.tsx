'use client';

import React, { useState } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { Settings, Shield, Globe, Cpu, Sliders } from 'lucide-react';

export const SettingsPanel: React.FC = () => {
  const [telemetry, setTelemetry] = useState(true);
  const [renderQuality, setRenderQuality] = useState('high');

  return (
    <div className="flex flex-col h-full overflow-y-auto select-none">
      
      {/* Panel Header */}
      <div className="p-6 border-b border-[#1a1f35]/50 bg-slate-950/20">
        <span className="text-[8px] font-mono tracking-widest text-[#00f2fe] uppercase block mb-0.5">
          SYSTEM SETTINGS
        </span>
        <h2 className="text-sm font-mono font-bold text-slate-200 tracking-wider">
          WORKSPACE CONFIG
        </h2>
      </div>

      {/* Settings Options */}
      <div className="p-6 flex-1 flex flex-col gap-6 overflow-y-auto font-mono text-[10px]">
        
        {/* Render Quality */}
        <div className="flex flex-col gap-3">
          <span className="text-[9px] tracking-widest text-slate-500 uppercase flex items-center gap-1.5 font-bold">
            <Globe className="w-3.5 h-3.5 text-[#00f2fe]" />
            3D EARTH QUALITY
          </span>
          <div className="flex gap-2">
            {['high', 'medium', 'low'].map((q) => (
              <button
                key={q}
                onClick={() => setRenderQuality(q)}
                className={`flex-1 py-1.5 border rounded uppercase text-[8px] font-bold text-center cursor-pointer transition-all ${
                  renderQuality === q 
                    ? 'border-[#00f2fe] bg-[#00f2fe]/10 text-[#00f2fe]' 
                    : 'border-[#1a1f35] bg-slate-900/40 text-slate-500 hover:border-slate-600'
                }`}
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Telemetry Stream */}
        <div className="border-t border-[#1a1f35]/30 pt-5 flex flex-col gap-3">
          <div className="flex justify-between items-center">
            <span className="text-[9px] tracking-widest text-slate-500 uppercase flex items-center gap-1.5 font-bold">
              <Cpu className="w-3.5 h-3.5 text-[#00f2fe]" />
              TELEMETRY LOG STREAM
            </span>
            <button
              onClick={() => setTelemetry(!telemetry)}
              className={`px-2 py-0.5 border rounded text-[8px] font-bold cursor-pointer transition-all ${
                telemetry 
                  ? 'border-[#50e3c2]/50 bg-[#50e3c2]/5 text-[#50e3c2]' 
                  : 'border-slate-800 text-slate-600'
              }`}
            >
              {telemetry ? 'ACTIVE' : 'MUTED'}
            </button>
          </div>
          <span className="text-[8.5px] leading-relaxed text-slate-500">
            Stream NISAR and Sentinel-2 telemetry metrics in real-time on home dashboard overlays. Disabling optimizes network requests.
          </span>
        </div>

        {/* Security context info */}
        <div className="border-t border-[#1a1f35]/30 pt-5 flex flex-col gap-3">
          <span className="text-[9px] tracking-widest text-slate-500 uppercase flex items-center gap-1.5 font-bold">
            <Shield className="w-3.5 h-3.5 text-[#00f2fe]" />
            WORKSPACE SECURITY
          </span>
          <div className="bg-slate-900/40 border border-[#1a1f35] p-3.5 rounded text-slate-500 text-[8.5px] leading-relaxed">
            Role: Lead Infrastructure Resilience Planner
            <br />
            Context: Ahmedabad Grid Analysis
            <br />
            Session Token Expires: 23 hrs 55 mins
          </div>
        </div>

      </div>
    </div>
  );
};
export default SettingsPanel;
