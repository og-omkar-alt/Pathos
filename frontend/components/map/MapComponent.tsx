'use client';

import React, { useEffect, useRef } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useSimulation } from '../../context/SimulationContext';
import { demoScenarios } from '../../data/demoScenarios';

if (typeof window !== 'undefined') {
  maplibregl.setWorkerUrl('/maplibre-gl-worker.mjs');
}

const EMPTY: any = { type: 'FeatureCollection', features: [] };
// Normalise any coord pair to [lon, lat]
// lon is always > 40 (72.x), lat is always < 40 (23.x)
const toLonLat = (c: [number, number]): [number, number] =>
  Number(c[0]) > 40 ? [Number(c[0]), Number(c[1])] : [Number(c[1]), Number(c[0])];

export function MapComponent() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef       = useRef<maplibregl.Map | null>(null);
  const styleLoaded  = useRef(false);

  const { simState, routeResult, setSimState, setRouteResult } = useSimulation() as any;

  // ── Init map ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          carto: {
            type: 'raster',
            tiles: ['https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'],
            tileSize: 256,
          },
        },
        layers: [
          { id: 'bg',    type: 'background', paint: { 'background-color': '#10131a' } },
          { id: 'carto', type: 'raster', source: 'carto', minzoom: 0, maxzoom: 20 },
        ],
      },
      center: [72.545, 23.035],
      zoom: 12,
      attributionControl: false,
    });

    mapRef.current = map;

    map.on('load', () => {
      // ── Glow ──────────────────────────────────────────────────────────────
      map.addSource('route-glow', { type: 'geojson', data: EMPTY });
      map.addLayer({
        id: 'route-glow-layer', type: 'line', source: 'route-glow',
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': '#00f2fe', 'line-width': 20, 'line-opacity': 0.15, 'line-blur': 8 },
      });

      // ── Primary route ──────────────────────────────────────────────────────
      map.addSource('primary-route', { type: 'geojson', data: EMPTY });
      map.addLayer({
        id: 'primary-route-line', type: 'line', source: 'primary-route',
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': '#00f2fe', 'line-width': 6, 'line-opacity': 1.0 },
      });

      // ── Markers ────────────────────────────────────────────────────────────
      map.addSource('route-markers', { type: 'geojson', data: EMPTY });
      map.addLayer({
        id: 'route-markers-circle', type: 'circle', source: 'route-markers',
        paint: {
          'circle-color':        ['get', 'color'],
          'circle-radius':       10,
          'circle-stroke-width': 2.5,
          'circle-stroke-color': '#ffffff',
        },
      });

      styleLoaded.current = true;
    });

    return () => { map.remove(); mapRef.current = null; styleLoaded.current = false; };
  }, []);

  // ── Draw whenever state changes ───────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const draw = () => {
      if (simState !== 'SIMULATION_ACTIVE') {
        // Clear all layers and fly home
        (map.getSource('route-glow')     as maplibregl.GeoJSONSource)?.setData(EMPTY);
        (map.getSource('primary-route')  as maplibregl.GeoJSONSource)?.setData(EMPTY);
        (map.getSource('route-markers')  as maplibregl.GeoJSONSource)?.setData(EMPTY);
        map.flyTo({ center: [72.545, 23.035], zoom: 12, duration: 900 });
        return;
      }

      // ── Resolve coords: prefer live backend result, fall back to demo store ──
      let coords: [number, number][] = [];

      if (routeResult?.status === 'success' && routeResult.route_coords?.length > 1) {
        // Live backend returned coords — deep-clone to strip React proxies
        const raw: [number, number][] = JSON.parse(JSON.stringify(routeResult.route_coords));
        coords = raw.map(toLonLat);
        console.log(`🛰 Drawing LIVE route: ${coords.length} pts, first=${JSON.stringify(coords[0])}`);

      } else {
        // Backend failed — inject the pre-saved demo scenario coords directly
        // Pick scenario_2 (S.G. Highway) as the showcase — change key to taste
        const fallbackKey = 'scenario_2';
        const demo = (demoScenarios as any)[fallbackKey];
        if (demo?.routeCoords?.length > 1) {
          coords = (demo.routeCoords as [number, number][]).map(toLonLat);
          console.warn(`⚠ Backend unavailable — drawing stored demo route "${demo.label}": ${coords.length} pts`);

          // Inject the stored route into context so SimulationPanel shows metrics
          if (setRouteResult) {
            setRouteResult({
              status: 'success',
              route_coords: coords,
              metrics: {
                distance_km:               demo.distance_km ?? 8.4,
                estimated_time_mins:       demo.estimated_time_mins ?? 14,
                avg_congestion_multiplier: 1.8,
                segments_count:            demo.points ?? coords.length,
              },
            });
          }
        }
      }

      if (coords.length < 2) {
        console.error('No valid coordinates to draw.');
        return;
      }

      const routeGeoJSON: any = {
        type: 'FeatureCollection',
        features: [{
          type: 'Feature',
          properties: {},
          geometry: { type: 'LineString', coordinates: coords },
        }],
      };

      // Set both glow and main line
      (map.getSource('route-glow')    as maplibregl.GeoJSONSource)?.setData(routeGeoJSON);
      (map.getSource('primary-route') as maplibregl.GeoJSONSource)?.setData(routeGeoJSON);

      // Origin (green) + Destination (red) markers
      (map.getSource('route-markers') as maplibregl.GeoJSONSource)?.setData({
        type: 'FeatureCollection',
        features: [
          { type: 'Feature', properties: { color: '#2ecc71' }, geometry: { type: 'Point', coordinates: coords[0] } },
          { type: 'Feature', properties: { color: '#e74c3c' }, geometry: { type: 'Point', coordinates: coords[coords.length - 1] } },
        ],
      });

      // Fit camera exactly to route bounds
      const bounds = new maplibregl.LngLatBounds();
      coords.forEach(c => bounds.extend(c));
      map.fitBounds(bounds, { padding: 100, duration: 1200, maxZoom: 15 });
    };

    if (styleLoaded.current) draw();
    else mapRef.current?.once('load', draw);

  }, [simState, routeResult]);

  return (
    <div ref={containerRef} className="absolute inset-0 w-full h-full bg-[#10131a]" />
  );
}

export default MapComponent;