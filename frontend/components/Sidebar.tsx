'use client';

import React from 'react';
import { useSimulation, AppTab } from '../context/SimulationContext';
import { 
  Home, 
  LayoutDashboard, 
  LineChart, 
  Play, 
  Zap, 
  FileText, 
  Layers, 
  Settings,
  Database
} from 'lucide-react';

interface SidebarItemProps {
  tab: AppTab;
  icon: React.ReactNode;
  label: string;
  badge?: string;
  disabled?: boolean;
}

export const Sidebar: React.FC = () => {
  const { currentTab, setCurrentTab, simState } = useSimulation();

  const SidebarItem: React.FC<SidebarItemProps> = ({ tab, icon, label, badge, disabled }) => {
    const isActive = currentTab === tab;

    const handleClick = () => {
      if (disabled) return;
      setCurrentTab(tab);
    };

    return (
      <button
        onClick={handleClick}
        disabled={disabled}
        className={`group relative w-full flex flex-col items-center py-4 px-1 transition-all duration-300 border-l-[3px] select-none cursor-pointer ${
          isActive 
            ? 'border-[#00f2fe] bg-[#00f2fe]/5 text-[#00f2fe]' 
            : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/30'
        } ${disabled ? 'opacity-30 cursor-not-allowed' : ''}`}
      >
        <div className={`transition-all duration-300 group-hover:scale-110 group-hover:-translate-y-[1px] ${
          isActive ? 'drop-shadow-[0_0_6px_rgba(0,242,254,0.75)]' : ''
        }`}>
          {icon}
        </div>
        <span className="text-[9px] tracking-wider font-mono uppercase mt-2.5 font-bold text-center leading-tight">
          {label}
        </span>

        {/* Floating Tooltip */}
        <div className="absolute left-20 top-1/2 -translate-y-1/2 z-50 bg-[#070b19] border border-[#00f2fe]/30 px-3 py-1.5 rounded text-white text-[10px] tracking-widest uppercase font-mono shadow-2xl opacity-0 scale-90 group-hover:opacity-100 group-hover:scale-100 transition-all duration-150 pointer-events-none whitespace-nowrap">
          {label} {badge && `[${badge}]`}
        </div>
      </button>
    );
  };

  return (
    <aside className="w-22 h-full bg-[#05060b] border-r border-[#1a1f35]/50 flex flex-col justify-between items-center py-5 z-20 flex-shrink-0">
      
      {/* Brand Logo - Top of Sidebar */}
      <div className="flex flex-col items-center gap-1 cursor-pointer" onClick={() => setCurrentTab('HOME')}>
        <div className="w-9 h-9 border border-[#00f2fe]/40 rounded bg-[#070e20]/60 flex items-center justify-center relative shadow-[0_0_10px_rgba(0,242,254,0.15)]">
          <Database className="w-4.5 h-4.5 text-[#00f2fe]" />
          <div className="absolute -bottom-0.5 -right-0.5 w-1.5 h-1.5 bg-[#00f2fe] rounded-full" />
        </div>
        <span className="text-[10px] font-black tracking-widest text-white mt-1">SETU</span>
      </div>

      {/* Navigation Group */}
      <div className="w-full flex flex-col gap-0.5 justify-center my-auto">
        <SidebarItem 
          tab="HOME" 
          icon={<Home className="w-4.5 h-4.5" />} 
          label="Home" 
        />
        <SidebarItem 
          tab="DASHBOARD" 
          icon={<LayoutDashboard className="w-4.5 h-4.5" />} 
          label="Dashboard" 
        />
        <SidebarItem 
          tab="NETWORK_ANALYSIS" 
          icon={<LineChart className="w-4.5 h-4.5" />} 
          label="Network Analysis" 
        />
        <SidebarItem 
          tab="SIMULATION" 
          icon={<Play className="w-4.5 h-4.5" />} 
          label="Simulation"
          badge={simState === 'SIMULATION_ACTIVE' ? 'ACTIVE' : undefined}
          disabled={simState === 'LIVE' || simState === 'ROAD_SELECTED'} 
        />
        <SidebarItem 
          tab="CRITICALITY" 
          icon={<Zap className="w-4.5 h-4.5" />} 
          label="Criticality" 
        />
        <SidebarItem 
          tab="REPORTS" 
          icon={<FileText className="w-4.5 h-4.5" />} 
          label="Reports" 
        />
        <SidebarItem 
          tab="DATA_LAYERS" 
          icon={<Layers className="w-4.5 h-4.5" />} 
          label="Data Layers" 
        />
      </div>

      {/* Bottom Settings & Status Info */}
      <div className="w-full flex flex-col items-center gap-4">
        <SidebarItem 
          tab="SETTINGS" 
          icon={<Settings className="w-4.5 h-4.5" />} 
          label="Settings" 
        />
        
        {/* Bottom environment log text */}
        <div className="text-center font-mono text-[7px] text-slate-600 border-t border-[#1a1f35]/50 w-full pt-3 mt-1 leading-normal select-none">
          DEMO ENV
          <br />
          v1.0.0
        </div>
      </div>
    </aside>
  );
};
export default Sidebar;
