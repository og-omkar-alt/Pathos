'use client';

import React, { useState, useEffect } from 'react';
import { useSimulation } from '../context/SimulationContext';
import { Sidebar } from './Sidebar';

export const HomeView: React.FC = () => {
  const { setCurrentTab, currentTab, backendOnline } = useSimulation();
  const [transitioning, setTransitioning] = useState(false);

  const [currentTime, setCurrentTime] = useState('');

  useEffect(() => {
    setCurrentTime(new Date().toLocaleTimeString('en-US', { hour12: false }) + ' IST');
    const timer = setInterval(() => {
      setCurrentTime(new Date().toLocaleTimeString('en-US', { hour12: false }) + ' IST');
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const handleEnterDashboard = () => {
    setTransitioning(true);
    setTimeout(() => {
      setCurrentTab('DASHBOARD');
    }, 600);
  };

  if (currentTab !== 'HOME') return null;

  return (
    <div className={`relative flex w-full h-screen overflow-hidden bg-[#030307] transition-all duration-700 ${transitioning ? 'opacity-0 scale-98' : 'opacity-100 scale-100'}`}>
      
      {/* 1. Slim Left Sidebar (Constant position in navigation) */}
      <Sidebar />

      {/* 2. Main Space Earth Container */}
      <div 
        className="flex-1 h-full relative overflow-hidden flex flex-col justify-between py-12 px-16 bg-cover bg-center"
        style={{ backgroundImage: 'url("/space_stars_bg.jpg")' }}
      >
        
        {/* Cinematic Earth-observation motion plate background video */}
        <video
          autoPlay
          loop
          muted
          playsInline
          className="video-visual-layer"
        >
          <source src="/Satellite.mp4" type="video/mp4" />
          Your browser does not support the video tag.
        </video>

        {/* Ambient bottom gradient to blend the video into the background and improve text legibility */}
        <div className="absolute inset-x-0 bottom-0 h-44 bg-gradient-to-t from-[#030307] via-[#030307]/60 to-transparent z-1 pointer-events-none" />

        {/* TOP STATUS ROW */}
        <div className="w-full flex justify-end z-10 select-none">
          <div className="flex items-center gap-2">
            <span className="relative flex h-1.5 w-1.5">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${backendOnline ? 'bg-emerald-400' : 'bg-red-400'} opacity-75`}></span>
              <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${backendOnline ? 'bg-emerald-500' : 'bg-red-500'}`}></span>
            </span>
            <span className={`text-[9px] tracking-widest uppercase font-mono font-bold ${backendOnline ? 'text-[#50e3c2]' : 'text-red-400'}`}>
              {backendOnline ? 'SYSTEM ONLINE' : 'BACKEND OFFLINE'}
            </span>
          </div>
        </div>

        {/* MIDDLE CONTENT COLUMN - HERO ACCORDING TO REFERENCE */}
        <div className="flex-1 flex flex-col justify-center z-10 max-w-[360px] text-left select-none">
          
          {/* Logo & SETU wordmark row */}
          <div className="flex items-center gap-4 mb-5">
            {/* Minimal node connector triangle vector logo */}
            <svg viewBox="0 0 24 24" className="w-8 h-8 text-[#00f2fe]" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="12" cy="4" r="2.5" className="fill-[#030307] stroke-[#00f2fe] stroke-[2]" />
              <circle cx="5" cy="18" r="2.5" className="fill-[#030307] stroke-[#00f2fe] stroke-[2]" />
              <circle cx="19" cy="18" r="2.5" className="fill-[#030307] stroke-[#00f2fe] stroke-[2]" />
              <line x1="12" y1="6.5" x2="5.8" y2="15.8" className="stroke-[#00f2fe]" />
              <line x1="12" y1="6.5" x2="18.2" y2="15.8" className="stroke-[#00f2fe]" />
              <line x1="7.5" y1="18" x2="16.5" y2="18" className="stroke-[#00f2fe]" />
            </svg>
            <h1 className="text-4xl font-extrabold text-white tracking-widest leading-none font-sans">
              SETU
            </h1>
          </div>

          <h2 className="text-[11px] tracking-[0.25em] text-[#f8fafc] font-mono mb-5 uppercase leading-normal font-bold">
            Urban Road Resilience
            <br />
            & Network Intelligence
          </h2>

          <p className="text-slate-400 text-[10.5px] leading-relaxed mb-7 font-sans font-light">
            Advanced geospatial intelligence platform to analyze, simulate and strengthen urban road-network resilience for safer, smarter and more connected cities.
          </p>

          <button
            onClick={handleEnterDashboard}
            className="group w-fit flex items-center gap-3 px-5 py-2.5 border border-[#00f2fe]/60 bg-[#00f2fe]/5 hover:bg-[#00f2fe]/15 rounded text-[#00f2fe] hover:text-white font-mono text-[9px] tracking-[0.2em] font-semibold transition-all duration-200 cursor-pointer shadow-[0_0_10px_rgba(0,242,254,0.05)]"
          >
            ENTER DASHBOARD
            <span className="transition-transform duration-200 group-hover:translate-x-1">→</span>
          </button>
        </div>

        {/* BOTTOM ROW SYSTEM METADATA */}
        <div className="w-full flex justify-between items-end z-10 font-mono text-[8px] text-slate-600 select-none">
          <div className="flex flex-col gap-0.5 leading-normal">
            <span>LIVE ENVIRONMENT</span>
            <span>v1.0.0</span>
          </div>
        </div>

        {/* FAR RIGHT OVERLAY - TELEMETRY & NISAR METADATA */}
        <div className="absolute right-16 top-0 bottom-0 flex flex-col justify-center gap-12 z-10 font-mono text-[9px] text-right text-slate-400 select-none">
          <div className="flex flex-col gap-0.5">
            <span className="text-[7.5px] tracking-wider text-slate-600">LOCATION</span>
            <span className="text-slate-200 uppercase font-semibold">AHMEDABAD, INDIA</span>
          </div>

          <div className="flex flex-col gap-0.5">
            <span className="text-[7.5px] tracking-wider text-slate-600">DATE INDEX</span>
            <span className="text-slate-200 uppercase font-semibold">21 AUG 2026</span>
          </div>

          <div className="flex flex-col gap-0.5">
            <span className="text-[7.5px] tracking-wider text-slate-600">TELEMETRY TIME</span>
            <span className="text-slate-200 uppercase font-semibold w-20 inline-block text-right">{currentTime || '\u00A0'}</span>
          </div>

          <div className="flex flex-col gap-1 items-end mt-4">
            <span className="text-[7.5px] tracking-wider text-slate-600 uppercase">Data Source</span>
            <span className="text-[#00f2fe] uppercase font-bold flex items-center gap-1">
              SENTINEL-1 SATELLITE
            </span>
            
            {/* Crossed Sensor / Satellite outline icon graphic */}
            <svg viewBox="0 0 24 24" className="w-5 h-5 text-slate-500 mt-2" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M12 2L2 12h5v8h10v-8h5L12 2z" />
              <path d="M6 12l6-6 6 6" />
            </svg>
          </div>
        </div>

      </div>
    </div>
  );
};

export default HomeView;
