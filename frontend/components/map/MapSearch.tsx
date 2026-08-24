'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { geocodeArea } from '../../lib/api';
import { Search, MapPin, Navigation } from 'lucide-react';

interface SearchResult {
  name: string;
  lat: number;
  lon: number;
  display_name: string;
}

export const MapSearch: React.FC = () => {
  const { setOriginArea, setDestArea, currentTab, setCurrentTab } = useSimulation();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  // Close search dropdown when clicking outside
  useEffect(() => {
    const clickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', clickOutside);
    return () => document.removeEventListener('mousedown', clickOutside);
  }, []);

  // Debounced geocode search
  useEffect(() => {
    if (!query.trim() || query.trim().length < 3) {
      setResults([]);
      return;
    }

    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const geo = await geocodeArea(query.trim());
        setResults([{
          name: query.trim(),
          lat: geo.lat,
          lon: geo.lon,
          display_name: geo.display_name,
        }]);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 400);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  const handleSetAsOrigin = (item: SearchResult) => {
    setOriginArea(item.name);
    setQuery('');
    setIsOpen(false);
    if (currentTab !== 'DASHBOARD') setCurrentTab('DASHBOARD');
  };

  const handleSetAsDest = (item: SearchResult) => {
    setDestArea(item.name);
    setQuery('');
    setIsOpen(false);
    if (currentTab !== 'DASHBOARD') setCurrentTab('DASHBOARD');
  };

  return (
    <div ref={searchRef} className="absolute top-6 left-6 z-10 w-72 select-none">
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          placeholder="Search place name..."
          className="w-full bg-[#070b19]/80 backdrop-blur-md border border-[#1a1f35] rounded px-4 py-2 pl-10 text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:border-[#00f2fe]/60 shadow-lg"
        />
        <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
        {loading && (
          <div className="absolute right-3 top-2.5 w-4 h-4 border-2 border-[#00f2fe] border-t-transparent rounded-full animate-spin" />
        )}
      </div>

      {isOpen && results.length > 0 && (
        <div className="absolute top-11 left-0 right-0 bg-[#070b19]/95 border border-[#1a1f35] backdrop-blur-md rounded shadow-2xl overflow-hidden z-20">
          {results.map((item, idx) => (
            <div key={idx} className="px-4 py-3 border-b border-[#1a1f35]/50 last:border-b-0">
              <div className="flex items-start gap-3 mb-2">
                <MapPin className="w-4 h-4 text-[#00f2fe] mt-0.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-[11px] font-mono font-bold text-slate-200 truncate uppercase">
                    {item.name}
                  </div>
                  <div className="text-[8px] font-mono text-slate-500 mt-0.5 truncate">
                    {item.display_name}
                  </div>
                  <div className="text-[8px] font-mono text-slate-600 mt-0.5">
                    {item.lat.toFixed(4)}, {item.lon.toFixed(4)}
                  </div>
                </div>
              </div>
              <div className="flex gap-2 ml-7">
                <button
                  onClick={() => handleSetAsOrigin(item)}
                  className="flex-1 py-1 px-2 rounded text-[8px] font-mono font-bold tracking-wider
                             bg-emerald-950/30 border border-emerald-500/30 text-emerald-400
                             hover:bg-emerald-950/60 transition-colors cursor-pointer">
                  SET AS ORIGIN
                </button>
                <button
                  onClick={() => handleSetAsDest(item)}
                  className="flex-1 py-1 px-2 rounded text-[8px] font-mono font-bold tracking-wider
                             bg-red-950/30 border border-red-500/30 text-red-400
                             hover:bg-red-950/60 transition-colors cursor-pointer">
                  SET AS DEST
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
