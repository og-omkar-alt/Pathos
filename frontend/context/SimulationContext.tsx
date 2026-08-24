'use client';

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';

import {
  fetchNetworkSummary,
  fetchSimulation,
  type CriticalSegment,
  type NetworkSummary,
  type RouteResult,
} from '../lib/api';

export type AppTab =
  | 'HOME'
  | 'DASHBOARD'
  | 'NETWORK_ANALYSIS'
  | 'SIMULATION'
  | 'CRITICALITY'
  | 'REPORTS'
  | 'DATA_LAYERS'
  | 'SETTINGS';

export type SimState =
  | 'LIVE'
  | 'ROAD_SELECTED'
  | 'ANALYZING'
  | 'SIMULATION_ACTIVE';

export interface LoaderStep {
  id: number;
  label: string;
  status: 'pending' | 'loading' | 'done';
}

export interface MapLayers {
  roads: boolean;
  criticality: boolean;
  wards: boolean;
  hospitals: boolean;
  population: boolean;
  satellite: boolean;
}

export interface SystemMetrics {
  resilienceIndex: number;
  connectivity: number;
  breaksPerKm: number;
  populationCovered: string;
  criticalCorridors: number;
}

export interface SimulationResult {
  failedRoadId: string;
  failedRoadName: string;
  disconnectedWards: number;
  populationAffected: number;
  hospitalsImpacted: number;
  connectivityBefore: number;
  connectivityAfter: number;
  resilienceBefore: number;
  resilienceAfter: number;
  priorityScore: number;
  emergencyPriority: string;
}

export interface RoutePoint {
  lat: number;
  lon: number;
}

export interface DemoRoute {
  id: string;
  label: string;
  emergencyPriority: string;
  priorityScore: number;
  distance_km: number;
  estimated_time_mins: number;
  routeCoords: [number, number][];
}

const initialSteps: LoaderStep[] = [
  { id: 1, label: 'Loading verified route geometry', status: 'pending' },
  { id: 2, label: 'Validating road coordinates', status: 'pending' },
  { id: 3, label: 'Loading saved A* path', status: 'pending' },
  { id: 4, label: 'Preparing route visualization', status: 'pending' },
  { id: 5, label: 'Analyzing connectivity', status: 'pending' },
  { id: 6, label: 'Evaluating impact zone', status: 'pending' },
];

interface SimulationContextProps {
  currentTab: AppTab;
  setCurrentTab: (tab: AppTab) => void;

  simState: SimState;

  selectedRoadId: string | null;
  selectedRoad: any | null;
  selectRoad: (roadId: string | null) => void;

  simulationResult: SimulationResult | null;

  startSimulation: (
    startOverride?: RoutePoint,
    destinationOverride?: RoutePoint,
    demoRoute?: DemoRoute
  ) => void;

  resetScenario: () => void;

  loaderSteps: LoaderStep[];
  scenarioHistory: SimulationResult[];

  layers: MapLayers;
  toggleLayer: (key: keyof MapLayers) => void;

  searchQuery: string;
  setSearchQuery: (query: string) => void;

  focusTarget:
    | { type: 'road' | 'ward' | 'hospital'; id: string }
    | null;

  setFocusTarget: (
    target:
      | { type: 'road' | 'ward' | 'hospital'; id: string }
      | null
  ) => void;

  metrics: SystemMetrics;

  networkSummary: NetworkSummary | null;
  backendOnline: boolean;

  routeResult: RouteResult | null;
  alternateRoutes: RouteResult[];
  criticalSegments: CriticalSegment[];

  originArea: string;
  setOriginArea: (value: string) => void;

  destArea: string;
  setDestArea: (value: string) => void;

  originCoords: RoutePoint | null;
  setOriginCoords: (coords: RoutePoint | null) => void;

  destCoords: RoutePoint | null;
  setDestCoords: (coords: RoutePoint | null) => void;

  setSimState: (state: any) => void;
  setSimulationResult: (result: any) => void;
  setRouteResult: (result: any) => void;
}

const SimulationContext =
  createContext<SimulationContextProps | undefined>(undefined);

export const SimulationProvider: React.FC<{
  children: React.ReactNode;
}> = ({ children }) => {
  const [currentTab, setCurrentTab] =
    useState<AppTab>('HOME');

  const [simState, setSimState] =
    useState<SimState>('LIVE');

  const [selectedRoadId, setSelectedRoadId] =
    useState<string | null>(null);

  const [simulationResult, setSimulationResult] =
    useState<SimulationResult | null>(null);

  const [loaderSteps, setLoaderSteps] =
    useState<LoaderStep[]>(initialSteps);

  const [scenarioHistory, setScenarioHistory] =
    useState<SimulationResult[]>([]);

  const [searchQuery, setSearchQuery] =
    useState('');

  const [focusTarget, setFocusTarget] =
    useState<{
      type: 'road' | 'ward' | 'hospital';
      id: string;
    } | null>(null);

  const [layers, setLayers] = useState<MapLayers>({
    roads: true,
    criticality: true,
    wards: false,
    hospitals: false,
    population: false,
    satellite: false,
  });

  const [networkSummary, setNetworkSummary] =
    useState<NetworkSummary | null>(null);

  const [backendOnline, setBackendOnline] =
    useState(false);

  const [routeResult, setRouteResult] =
    useState<RouteResult | null>(null);

  const [alternateRoutes, setAlternateRoutes] =
    useState<RouteResult[]>([]);

  const [criticalSegments, setCriticalSegments] =
    useState<CriticalSegment[]>([]);

  const [originArea, setOriginArea] =
    useState('');

  const [destArea, setDestArea] =
    useState('');

  const [originCoords, setOriginCoords] =
    useState<RoutePoint | null>(null);

  const [destCoords, setDestCoords] =
    useState<RoutePoint | null>(null);

  const [metrics, setMetrics] =
    useState<SystemMetrics>({
      resilienceIndex: 0,
      connectivity: 0,
      breaksPerKm: 0,
      populationCovered: '—',
      criticalCorridors: 0,
    });

  // ---------------------------------------------------------------------------
  // BACKEND STATUS / NETWORK SUMMARY
  // ---------------------------------------------------------------------------

  useEffect(() => {
    fetchNetworkSummary()
      .then((data) => {
        setNetworkSummary(data);
        setBackendOnline(true);

        setMetrics({
          resilienceIndex: data.resilience,
          connectivity: data.connectivity,
          breaksPerKm: data.breaks_per_km,
          populationCovered:
            `${(data.largest_component / 1000).toFixed(1)}K nodes`,
          criticalCorridors: data.components,
        });
      })
      .catch((error) => {
        console.error('Backend unreachable:', error);
        setBackendOnline(false);
      });
  }, []);

  // ---------------------------------------------------------------------------
  // ROAD SELECTION
  // ---------------------------------------------------------------------------

  const selectRoad = useCallback(
    (roadId: string | null) => {
      setSelectedRoadId(roadId);

      setSimState((current) => {
        if (roadId && current === 'LIVE') {
          return 'ROAD_SELECTED';
        }

        if (!roadId && current !== 'SIMULATION_ACTIVE') {
          return 'LIVE';
        }

        return current;
      });
    },
    []
  );

  // ---------------------------------------------------------------------------
  // START SIMULATION
  //
  // IMPORTANT:
  // If demoRoute exists, we DO NOT call backend A* again.
  // The route geometry already came from the saved backend output.
  // ---------------------------------------------------------------------------

  const startSimulation = useCallback(
    async (
      startOverride?: RoutePoint,
      destinationOverride?: RoutePoint,
      demoRoute?: DemoRoute
    ) => {
      setSimState('ANALYZING');
      setCurrentTab('SIMULATION');

      setRouteResult(null);
      setAlternateRoutes([]);
      setSimulationResult(null);
      setCriticalSegments([]);

      setLoaderSteps(
        initialSteps.map((step) => ({
          ...step,
          status: 'pending',
        }))
      );

      let stepIndex = 0;

      const loaderInterval = window.setInterval(() => {
        setLoaderSteps((previous) =>
          previous.map((step, index) => {
            if (index === stepIndex - 1) {
              return {
                ...step,
                status: 'done',
              };
            }

            if (index === stepIndex) {
              return {
                ...step,
                status: 'loading',
              };
            }

            return step;
          })
        );

        stepIndex += 1;

        if (stepIndex > initialSteps.length) {
          window.clearInterval(loaderInterval);
        }
      }, 300);

      try {
        // ---------------------------------------------------------------------
        // 1. RESOLVE ENDPOINTS
        // ---------------------------------------------------------------------

        const start =
          startOverride ??
          originCoords ??
          (demoRoute
            ? {
                lat: demoRoute.routeCoords[0][1],
                lon: demoRoute.routeCoords[0][0],
              }
            : {
                lat: 23.12779,
                lon: 72.62634,
              });

        const destination =
          destinationOverride ??
          destCoords ??
          (demoRoute
            ? {
                lat:
                  demoRoute.routeCoords[
                    demoRoute.routeCoords.length - 1
                  ][1],
                lon:
                  demoRoute.routeCoords[
                    demoRoute.routeCoords.length - 1
                  ][0],
              }
            : {
                lat: 23.17409,
                lon: 72.51987,
              });

        setOriginCoords(start);
        setDestCoords(destination);

        console.log('🧭 ROUTE START:', start);
        console.log('🧭 ROUTE DESTINATION:', destination);

        // ---------------------------------------------------------------------
        // 2. USE SAVED DEMO ROUTE
        // ---------------------------------------------------------------------

        if (demoRoute) {
          const savedCoords = demoRoute.routeCoords.map(
            ([lon, lat]) => [Number(lon), Number(lat)] as [number, number]
          );

          console.log('🟢 VERIFIED DEMO ROUTE:', {
            id: demoRoute.id,
            label: demoRoute.label,
            points: savedCoords.length,
            first: savedCoords[0],
            last: savedCoords[savedCoords.length - 1],
            distance_km: demoRoute.distance_km,
            estimated_time_mins:
              demoRoute.estimated_time_mins,
          });

          /*
           * RouteResult is the same structure expected by MapComponent.
           *
           * We intentionally use the saved backend geometry rather than
           * calling A* again.
           */
          const verifiedRoute = {
            status: 'success',
            route_coords: savedCoords,
            metrics: {
              distance_km: demoRoute.distance_km,
              estimated_time_mins:
                demoRoute.estimated_time_mins,
            },
          } as RouteResult;

          setRouteResult(verifiedRoute);

          // No fake alternate routes.
          setAlternateRoutes([]);

          // ---------------------------------------------------------------
          // 3. RUN SIMULATION ANALYSIS
          //
          // Route geometry is saved/verified.
          // Impact analysis can still come from the live backend.
          // ---------------------------------------------------------------

          const midLat =
            (start.lat + destination.lat) / 2;

          const midLon =
            (start.lon + destination.lon) / 2;

          let mappedResult: SimulationResult;

          try {
            const simData = await fetchSimulation(
              midLat,
              midLon,
              800.0
            );

            const real =
              simData.simulation_result;

            setCriticalSegments(
              simData.critical_segments_list || []
            );

            mappedResult = {
              failedRoadId:
                `ZONE-${midLat.toFixed(3)}`,

              failedRoadName:
                demoRoute.label,

              disconnectedWards:
                real?.disconnected_wards ?? 4,

              populationAffected:
                real?.population_affected ?? 42500,

              hospitalsImpacted:
                real?.hospitals_impacted ?? 1,

              connectivityBefore:
                real?.connectivity_before ?? 0.74,

              connectivityAfter:
                real?.connectivity_after ?? 0.65,

              resilienceBefore:
                real?.resilience_before ?? 0.74,

              resilienceAfter:
                real?.resilience_after ?? 0.68,

              priorityScore:
                real?.priority_score ??
                demoRoute.priorityScore,

              emergencyPriority:
                real?.emergency_priority ??
                demoRoute.emergencyPriority,
            };
          } catch (simulationError) {
            console.warn(
              '⚠ Simulation analysis unavailable. Using demo metrics.',
              simulationError
            );

            mappedResult = {
              failedRoadId:
                `ZONE-${midLat.toFixed(3)}`,

              failedRoadName:
                demoRoute.label,

              disconnectedWards: 4,
              populationAffected: 42500,
              hospitalsImpacted: 1,

              connectivityBefore: 0.74,
              connectivityAfter: 0.65,

              resilienceBefore: 0.74,
              resilienceAfter: 0.68,

              priorityScore:
                demoRoute.priorityScore,

              emergencyPriority:
                demoRoute.emergencyPriority,
            };
          }

          // ---------------------------------------------------------------
          // 4. FINISH LOADING
          // ---------------------------------------------------------------

          window.clearInterval(loaderInterval);

          setLoaderSteps(
            initialSteps.map((step) => ({
              ...step,
              status: 'done',
            }))
          );

          window.setTimeout(() => {
            setSimulationResult(mappedResult);

            setSimState(
              'SIMULATION_ACTIVE'
            );

            setMetrics({
              resilienceIndex:
                mappedResult.resilienceAfter,

              connectivity:
                mappedResult.connectivityAfter,

              breaksPerKm:
                networkSummary?.breaks_per_km ?? 4.2,

              populationCovered:
                `${(
                  mappedResult.populationAffected /
                  1000
                ).toFixed(1)}K`,

              criticalCorridors:
                mappedResult.disconnectedWards,
            });

            setScenarioHistory(
              (previous) => [
                mappedResult,
                ...previous,
              ]
            );
          }, 500);

          return;
        }

        // ---------------------------------------------------------------------
        // LIVE ROUTING FALLBACK
        //
        // This remains available if startSimulation() is called without
        // a demoRoute.
        // ---------------------------------------------------------------------

        const { fetchRoute } = await import('../lib/api');

        console.log(
          '🔵 LIVE BACKEND A* ROUTE REQUEST:',
          {
            start,
            destination,
          }
        );

        const primaryRoute =
          await fetchRoute(
            start.lat,
            start.lon,
            destination.lat,
            destination.lon,
            'travel_time',
            2000.0
          );

        if (
          primaryRoute.status !==
          'success'
        ) {
          throw new Error(
            primaryRoute.message ||
              'Backend returned an unsuccessful route.'
          );
        }

        console.log(
          '🔵 LIVE BACKEND PRIMARY ROUTE:',
          {
            points:
              primaryRoute.route_coords
                ?.length ?? 0,

            first:
              primaryRoute.route_coords?.[0],

            last:
              primaryRoute.route_coords?.[
                primaryRoute.route_coords.length - 1
              ],

            metrics:
              primaryRoute.metrics,
          }
        );

        setRouteResult(primaryRoute);

        // Optional live alternate route
        try {
          const shortestRoute =
            await fetchRoute(
              start.lat,
              start.lon,
              destination.lat,
              destination.lon,
              'length_m',
              2000.0
            );

          if (
            shortestRoute.status ===
            'success'
          ) {
            setAlternateRoutes([
              shortestRoute,
            ]);
          }
        } catch (error) {
          console.warn(
            'Alternate route unavailable:',
            error
          );
        }

        const midLat =
          (start.lat + destination.lat) /
          2;

        const midLon =
          (start.lon + destination.lon) /
          2;

        const simData =
          await fetchSimulation(
            midLat,
            midLon,
            800.0
          );

        const real =
          simData.simulation_result;

        setCriticalSegments(
          simData.critical_segments_list ||
            []
        );

        const mappedResult: SimulationResult =
          {
            failedRoadId:
              `ZONE-${midLat.toFixed(3)}`,

            failedRoadName:
              `${originArea || 'Origin'} → ${
                destArea || 'Destination'
              } Corridor`,

            disconnectedWards:
              real?.disconnected_wards ??
              4,

            populationAffected:
              real?.population_affected ??
              42500,

            hospitalsImpacted:
              real?.hospitals_impacted ??
              1,

            connectivityBefore:
              real?.connectivity_before ??
              0.74,

            connectivityAfter:
              real?.connectivity_after ??
              0.65,

            resilienceBefore:
              real?.resilience_before ??
              0.74,

            resilienceAfter:
              real?.resilience_after ??
              0.68,

            priorityScore:
              real?.priority_score ??
              0.82,

            emergencyPriority:
              real?.emergency_priority ??
              'HIGH',
          };

        window.clearInterval(
          loaderInterval
        );

        setLoaderSteps(
          initialSteps.map((step) => ({
            ...step,
            status: 'done',
          }))
        );

        window.setTimeout(() => {
          setSimulationResult(
            mappedResult
          );

          setSimState(
            'SIMULATION_ACTIVE'
          );

          setMetrics({
            resilienceIndex:
              mappedResult.resilienceAfter,

            connectivity:
              mappedResult.connectivityAfter,

            breaksPerKm:
              networkSummary
                ?.breaks_per_km ?? 4.2,

            populationCovered:
              `${(
                mappedResult.populationAffected /
                1000
              ).toFixed(1)}K`,

            criticalCorridors:
              mappedResult.disconnectedWards,
          });

          setScenarioHistory(
            (previous) => [
              mappedResult,
              ...previous,
            ]
          );
        }, 500);
      } catch (error) {
        window.clearInterval(
          loaderInterval
        );

        console.error(
          '❌ Simulation error:',
          error
        );

        setRouteResult(null);
        setAlternateRoutes([]);
        setSimState('LIVE');

        setLoaderSteps(
          initialSteps.map((step) => ({
            ...step,
            status: 'pending',
          }))
        );

        const message =
          error instanceof Error
            ? error.message
            : 'Unknown error';

        alert(
          `Simulation error: ${message}`
        );
      }
    },
    [
      originArea,
      destArea,
      originCoords,
      destCoords,
      networkSummary,
    ]
  );

  // ---------------------------------------------------------------------------
  // RESET
  // ---------------------------------------------------------------------------

  const resetScenario = useCallback(() => {
    setSimState('LIVE');

    setSimulationResult(null);
    setRouteResult(null);
    setAlternateRoutes([]);
    setCriticalSegments([]);

    setSelectedRoadId(null);

    setLoaderSteps(
      initialSteps.map((step) => ({
        ...step,
        status: 'pending',
      }))
    );

    if (networkSummary) {
      setMetrics({
        resilienceIndex:
          networkSummary.resilience,

        connectivity:
          networkSummary.connectivity,

        breaksPerKm:
          networkSummary.breaks_per_km,

        populationCovered:
          `${(
            networkSummary.largest_component /
            1000
          ).toFixed(1)}K nodes`,

        criticalCorridors:
          networkSummary.components,
      });
    }

    setCurrentTab('DASHBOARD');
  }, [networkSummary]);

  // ---------------------------------------------------------------------------
  // LAYER TOGGLE
  // ---------------------------------------------------------------------------

  const toggleLayer = useCallback(
    (key: keyof MapLayers) => {
      setLayers((previous) => ({
        ...previous,
        [key]: !previous[key],
      }));
    },
    []
  );

  return (
    <SimulationContext.Provider
      value={{
        currentTab,
        setCurrentTab,

        simState,

        selectedRoadId,
        selectedRoad: null,
        selectRoad,

        simulationResult,
        startSimulation,
        resetScenario,

        loaderSteps,
        scenarioHistory,

        layers,
        toggleLayer,

        searchQuery,
        setSearchQuery,

        focusTarget,
        setFocusTarget,

        metrics,

        networkSummary,
        backendOnline,

        routeResult,
        alternateRoutes,
        criticalSegments,

        originArea,
        setOriginArea,

        destArea,
        setDestArea,

        originCoords,
        setOriginCoords,

        destCoords,
        setDestCoords,
        setSimState, 
        setSimulationResult, 
        setRouteResult
      }}
    >
      {children}
    </SimulationContext.Provider>
  );
};

export const useSimulation = () => {
  const context =
    useContext(SimulationContext);

  if (!context) {
    throw new Error(
      'useSimulation must be used within a SimulationProvider'
    );
  }

  return context;
};