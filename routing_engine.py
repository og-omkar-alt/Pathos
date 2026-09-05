"""
SETU Project — RouteMind AI Core Routing Engine  (Final Clean Version)
Fixes:
  - No hardcoded origin/destination fallbacks — caller must supply them
  - hospitals_impacted removed (was fake node-count math, not real data)
  - Population bbox CRS-aware
  - simulate_failure_impact returns failed_segments geometry + both routes
"""

import math
import pickle
import numpy as np
import networkx as nx
from scipy.spatial import cKDTree
from pyproj import Transformer
from pathlib import Path
import rasterio
from rasterio.windows import from_bounds

BASE               = r"C:\Users\omkar\OneDrive\Desktop\sih"
DEFAULT_GRAPH_PATH = rf"{BASE}\ahmedabad_outputs\ahmedabad_routing_graph.pkl"
POP_TIF_PATH       = rf"{BASE}\ahmedabad_outputs\ahmedabad_population_100m.tif"
AVG_SPEED_MS       = 11.1   # 40 km/h urban average


class RouteMindEngine:

    def __init__(self, graph_path=DEFAULT_GRAPH_PATH):
        print("Initialising RouteMind AI Routing Engine ...")
        self.graph_path = Path(graph_path)

        if not self.graph_path.exists():
            raise FileNotFoundError(
                f"Routing graph not found at {self.graph_path}.\n"
                f"Run build_telemetry_graph.py first."
            )

        with open(self.graph_path, "rb") as f:
            self.G = pickle.load(f)

        for u, v, data in self.G.edges(data=True):
            # --- ADD THIS LINE TO FIX THE 0.0 KM BUG ---
            if "length" in data: data["length_m"] = data["length"]
            # -------------------------------------------
            if "travel_time" not in data:
                data["travel_time"] = data.get("length_m", 1.0) / AVG_SPEED_MS
            if "congestion_level" not in data:
                data["congestion_level"] = 1.0

        self.to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
        self.to_gps = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)

        self.nodes    = list(self.G.nodes(data=True))
        self.node_ids = [n[0] for n in self.nodes]
        coords        = np.array(
            [[n[1]["x"], n[1]["y"]] for n in self.nodes], dtype=np.float64
        )
        self.tree = cKDTree(coords)

        print("  Building component index ...")
        self.component_map = {}
        for i, component in enumerate(nx.connected_components(self.G)):
            for node in component:
                self.component_map[node] = i

        print(
            f"  Engine ready: {len(self.nodes):,} nodes | "
            f"{self.G.number_of_edges():,} edges | "
            f"{nx.number_connected_components(self.G):,} components"
        )

    # ── Helpers ───────────────────────────────────────────────────────────────
    def graph_summary(self):
        total_km = sum(
            d.get("length_m", 0) for _, _, d in self.G.edges(data=True)
        ) / 1000.0
        return {
            "nodes"     : self.G.number_of_nodes(),
            "edges"     : self.G.number_of_edges(),
            "components": nx.number_connected_components(self.G),
            "total_km"  : round(total_km, 1),
        }

    def _snap_to_node(self, lat, lon, max_dist_m=500.0):
        utm_x, utm_y = self.to_utm.transform(lon, lat)
        dist, idx    = self.tree.query([utm_x, utm_y])
        if dist > max_dist_m:
            raise ValueError(
                f"No road found within {max_dist_m:.0f} m of your location. "
                f"Try a point closer to a road."
            )
        return self.node_ids[idx]

    def _node_lonlat(self, node_id):
        """Return [lon, lat] — MapLibre native format."""
        nd       = self.G.nodes[node_id]
        lon, lat = self.to_gps.transform(nd["x"], nd["y"])
        return [lon, lat]

    def _point_to_segment_distance(self, px, py, ax, ay, bx, by):
        """Minimum distance from point (px,py) to segment A→B, in metres."""
        abx = bx - ax
        aby = by - ay
        ab2 = abx * abx + aby * aby
        if ab2 == 0:
            return math.hypot(px - ax, py - ay)
        t = ((px - ax) * abx + (py - ay) * aby) / ab2
        t = max(0.0, min(1.0, t))
        closest_x = ax + t * abx
        closest_y = ay + t * aby
        return math.hypot(px - closest_x, py - closest_y)

    def _find_node_outside_zone(self, node_id, utm_x, utm_y,
                                radius_m, temp_G, search_mult=3.0):
        """
        BFS outward from node_id on the ORIGINAL graph to find the nearest
        node that is outside the failure zone (radius × search_mult) AND
        still exists in temp_G (not removed).
        Returns node_id or None.
        """
        visited = {node_id}
        queue   = [node_id]

        while queue:
            current = queue.pop(0)
            nd      = self.G.nodes[current]
            dist    = math.hypot(nd["x"] - utm_x, nd["y"] - utm_y)

            if dist > radius_m * search_mult and current in temp_G:
                return current

            for neighbor in self.G.neighbors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return None

    def same_component(self, start_lat, start_lon, end_lat, end_lon,
                       max_snap_dist_m=500.0):
        try:
            s = self._snap_to_node(start_lat, start_lon, max_dist_m=max_snap_dist_m)
            e = self._snap_to_node(end_lat,   end_lon,   max_dist_m=max_snap_dist_m)
            return self.component_map[s] == self.component_map[e]
        except ValueError:
            return False

    def _heuristic_time(self, u, v):
        n1, n2 = self.G.nodes[u], self.G.nodes[v]
        return np.hypot(n1["x"] - n2["x"], n1["y"] - n2["y"]) / AVG_SPEED_MS

    def _heuristic_dist(self, u, v):
        n1, n2 = self.G.nodes[u], self.G.nodes[v]
        return np.hypot(n1["x"] - n2["x"], n1["y"] - n2["y"])

    def _path_to_result(self, G, path):
        """Convert node-ID path → route_coords [lon,lat] + metrics."""
        coords       = []
        total_dist_m = 0.0
        total_time_s = 0.0
        total_cong   = 0.0

        for i in range(len(path) - 1):
            u, v  = path[i], path[i + 1]
            
            # --- FIX: Extract nested MultiDiGraph edge data ---
            edge_dict = G[u][v]
            edata = edge_dict[0] if 0 in edge_dict else list(edge_dict.values())[0]
            # --------------------------------------------------
            
            # Fallback to check both 'length_m' and 'length' keys
            length = edata.get("length_m", edata.get("length", 0.0))
            
            total_dist_m += length
            total_time_s += edata.get("travel_time", length / AVG_SPEED_MS)
            total_cong   += edata.get("congestion_level", 1.0)
            
            coords.append(self._node_lonlat(u))

        coords.append(self._node_lonlat(path[-1]))
        n_segs = max(1, len(path) - 1)

        return {
            "route_coords": coords,
            "metrics"     : {
                "distance_km"              : round(total_dist_m / 1000.0, 2),
                "estimated_time_mins"      : round(total_time_s / 60.0, 1),
                "avg_congestion_multiplier": round(total_cong / n_segs, 2),
                "segments_count"           : n_segs,
            },
        }
    # ── Standard A* route ─────────────────────────────────────────────────────
    def get_route(self, start_lat, start_lon, end_lat, end_lon,
                  weight_type="travel_time", max_snap_dist_m=500.0):
        try:
            start_node = self._snap_to_node(
                start_lat, start_lon, max_dist_m=max_snap_dist_m)
            end_node   = self._snap_to_node(
                end_lat,   end_lon,   max_dist_m=max_snap_dist_m)

            if start_node == end_node:
                return {
                    "status"      : "warning",
                    "message"     : "Origin and destination are the same node.",
                    "route_coords": [self._node_lonlat(start_node)],
                    "metrics"     : {
                        "distance_km"              : 0.0,
                        "estimated_time_mins"      : 0.0,
                        "avg_congestion_multiplier": 1.0,
                        "segments_count"           : 0,
                    },
                }

            heuristic = (self._heuristic_time
                         if weight_type == "travel_time"
                         else self._heuristic_dist)

            path   = nx.astar_path(self.G, start_node, end_node,
                                   heuristic=heuristic, weight=weight_type)
            result = self._path_to_result(self.G, path)
            return {"status": "success", **result}

        except ValueError as e:
            return {"status": "error", "message": str(e)}
        except nx.NetworkXNoPath:
            return {"status": "error",
                    "message": "No navigable path between these points."}
        except Exception as e:
            return {"status": "error", "message": f"{type(e).__name__}: {e}"}

    # ── Population query (CRS-aware) ──────────────────────────────────────────
    def _query_population(self, utm_x: float, utm_y: float,
                          radius_m: float) -> int:
        pop_path = Path(POP_TIF_PATH)
        if not pop_path.exists():
            area_km2 = math.pi * (radius_m / 1000.0) ** 2
            return int(area_km2 * 11_000 * 0.35)

        try:
            with rasterio.open(pop_path) as src:
                if src.crs and src.crs.is_geographic:
                    centre_lon, centre_lat = self.to_gps.transform(utm_x, utm_y)
                    lat_deg = radius_m / 111_320.0
                    lon_deg = radius_m / (111_320.0 * math.cos(
                        math.radians(centre_lat)))
                    bbox = (centre_lon - lon_deg, centre_lat - lat_deg,
                            centre_lon + lon_deg, centre_lat + lat_deg)
                else:
                    bbox = (utm_x - radius_m, utm_y - radius_m,
                            utm_x + radius_m, utm_y + radius_m)

                window   = from_bounds(*bbox, transform=src.transform)
                pop_data = src.read(1, window=window)
                valid    = pop_data[pop_data > 0]
                # WorldPop stores people per pixel directly — sum is total headcount
                total    = int(np.sum(valid))
                print(f"  Pop window={pop_data.shape}, "
                      f"valid_px={len(valid)}, total={total:,}")
                return total
        except Exception as e:
            print(f"  Population raster error: {e}")
            area_km2 = math.pi * (radius_m / 1000.0) ** 2
            return int(area_km2 * 11_000 * 0.35)

    # ── Full simulation ───────────────────────────────────────────────────────
    def simulate_failure_impact(
        self,
        lat             : float,
        lon             : float,
        radius_m        : float,
        route_start_lat : float,          # REQUIRED — no defaults
        route_start_lon : float,
        route_end_lat   : float,
        route_end_lon   : float,
        max_snap_dist_m : float = 3000.0,
    ) -> dict:
        """
        Returns:
          simulation_result  — KPI metrics (no fake hospital count)
          failed_segments    — GeoJSON LineStrings WITH coordinates
          normal_route       — A* on original graph
          safe_route         — A* on temp_G (failed edges removed)
        """
        utm_x, utm_y = self.to_utm.transform(lon, lat)

        # ── Baseline ──────────────────────────────────────────────────────────
        total_nodes           = self.G.number_of_nodes()
        baseline_components   = nx.number_connected_components(self.G)
        baseline_largest_cc   = len(max(nx.connected_components(self.G), key=len))
        baseline_connectivity = round((baseline_largest_cc / total_nodes) * 100, 2)
        baseline_resilience   = round(
            1.0 - (baseline_components / total_nodes), 3)

        # ── Failure zone ──────────────────────────────────────────────────────
        nodes_in_zone     = self.tree.query_ball_point([utm_x, utm_y], r=radius_m)
        affected_node_ids = {self.node_ids[i] for i in nodes_in_zone}

        temp_G        = self.G.copy()
        edges_removed = []
        seen_edges    = set()

        for u, v, data in list(temp_G.edges(data=True)):
            if u not in temp_G or v not in temp_G:
                continue
            u_data = temp_G.nodes[u]
            v_data = temp_G.nodes[v]
            ux, uy = u_data["x"], u_data["y"]
            vx, vy = v_data["x"], v_data["y"]
            distance = self._point_to_segment_distance(
                utm_x, utm_y, ux, uy, vx, vy)
            if distance <= radius_m:
                key = (min(u, v), max(u, v))
                if key in seen_edges:
                    continue
                seen_edges.add(key)
                edges_removed.append((u, v, dict(data)))
                temp_G.remove_edge(u, v)

        # ── Post-failure ──────────────────────────────────────────────────────
        post_components   = nx.number_connected_components(temp_G)
        post_largest_cc   = len(max(nx.connected_components(temp_G), key=len))
        post_connectivity = round((post_largest_cc / total_nodes) * 100, 2)
        post_resilience   = round(1.0 - (post_components / total_nodes), 3)

        disconnected_clusters = max(0, post_components - baseline_components)
        priority_score        = round(
            min(1.0,
                (len(edges_removed) * 0.05) +
                (baseline_connectivity - post_connectivity) / 50.0),
            2,
        )
        emergency_priority = (
            "CRITICAL" if priority_score > 0.75 else
            "HIGH"     if priority_score > 0.45 else
            "MEDIUM"
        )

        # ── Failed segment geometry ───────────────────────────────────────────
        failed_segments = []
        for u, v, data in edges_removed:
            length = round(data.get("length_m", 0.0), 1)
            cong   = data.get("congestion_level", 1.0)
            score  = round(
                min(0.99, (length / 500.0) * 0.4 + (cong / 2.0) * 0.6), 3)
            crit   = (
                "CRITICAL" if score > 0.75 else
                "HIGH"     if score > 0.5  else
                "MEDIUM"
            )
            failed_segments.append({
                "id"         : f"SEG-{u}-{v}",
                "criticality": crit,
                "score"      : score,
                "length_m"   : length,
                "coordinates": [self._node_lonlat(u), self._node_lonlat(v)],
            })

        # ── Route comparison ──────────────────────────────────────────────────
        normal_route = None
        safe_route   = None

        try:
            start_node = self._snap_to_node(
                route_start_lat, route_start_lon, max_dist_m=max_snap_dist_m)
            end_node   = self._snap_to_node(
                route_end_lat, route_end_lon, max_dist_m=max_snap_dist_m)

            # Normal route — original graph
            try:
                normal_path  = nx.astar_path(
                    self.G, start_node, end_node,
                    heuristic=self._heuristic_time, weight="travel_time")
                normal_route = {"status": "success",
                                **self._path_to_result(self.G, normal_path)}
            except nx.NetworkXNoPath:
                normal_route = {
                    "status" : "no_path",
                    "message": "Normal route has no path.",
                    "route_coords": [], "metrics": {},
                }

            # Safe route — temp_G with failed edges removed
            try:
                safe_path  = nx.astar_path(
                    temp_G, start_node, end_node,
                    heuristic=self._heuristic_time, weight="travel_time")
                safe_route = {"status": "success",
                              **self._path_to_result(temp_G, safe_path)}

                # Detour comparison
                if (normal_route and
                        normal_route.get("status") == "success" and
                        normal_route.get("metrics")):
                    n_dist = normal_route["metrics"].get("distance_km", 0)
                    n_time = normal_route["metrics"].get("estimated_time_mins", 0)
                    s_dist = safe_route["metrics"].get("distance_km", 0)
                    s_time = safe_route["metrics"].get("estimated_time_mins", 0)
                    safe_route["detour_km"]   = round(s_dist - n_dist, 2)
                    safe_route["detour_mins"] = round(s_time - n_time, 1)

            except nx.NetworkXNoPath:
                # Direct path is broken — try bypass nodes outside failure zone
                print("  Direct safe path blocked. Trying bypass nodes ...")
                alt_start = self._find_node_outside_zone(
                    start_node, utm_x, utm_y, radius_m, temp_G)
                alt_end   = self._find_node_outside_zone(
                    end_node,   utm_x, utm_y, radius_m, temp_G)

                if alt_start and alt_end and alt_start != alt_end:
                    try:
                        safe_path  = nx.astar_path(
                            temp_G, alt_start, alt_end,
                            heuristic=self._heuristic_time,
                            weight="travel_time")
                        safe_route = {
                            "status": "success",
                            "note"  : "Rerouted via bypass nodes outside failure zone",
                            **self._path_to_result(temp_G, safe_path),
                        }
                        # Detour comparison
                        if (normal_route and
                                normal_route.get("status") == "success" and
                                normal_route.get("metrics")):
                            n_dist = normal_route["metrics"].get("distance_km", 0)
                            n_time = normal_route["metrics"].get("estimated_time_mins", 0)
                            s_dist = safe_route["metrics"].get("distance_km", 0)
                            s_time = safe_route["metrics"].get("estimated_time_mins", 0)
                            safe_route["detour_km"]   = round(s_dist - n_dist, 2)
                            safe_route["detour_mins"] = round(s_time - n_time, 1)
                        print(f"  Bypass route found: "
                              f"{safe_route['metrics']['distance_km']} km")
                    except nx.NetworkXNoPath:
                        safe_route = {
                            "status" : "isolated",
                            "message": (
                                "Area fully isolated — no bypass route possible. "
                                "This zone has no alternate road connection."
                            ),
                            "route_coords": [], "metrics": {},
                        }
                else:
                    safe_route = {
                        "status" : "isolated",
                        "message": (
                            "Area fully isolated — no bypass route possible. "
                            "This zone has no alternate road connection."
                        ),
                        "route_coords": [], "metrics": {},
                    }

        except ValueError as e:
            # Snap failed — caller provided bad coordinates
            normal_route = {"status": "error", "message": str(e)}
            safe_route   = {"status": "error", "message": str(e)}

        # ── Population ────────────────────────────────────────────────────────
        total_pop = self._query_population(utm_x, utm_y, radius_m)

        return {
            "status": "success",

            # KPI metrics — hospitals_impacted removed (no real data)
            "simulation_result": {
                "disconnected_wards"  : disconnected_clusters,
                "population_affected" : total_pop,
                "connectivity_before" : baseline_connectivity,
                "connectivity_after"  : post_connectivity,
                "resilience_before"   : baseline_resilience,
                "resilience_after"    : post_resilience,
                "priority_score"      : priority_score,
                "emergency_priority"  : emergency_priority,
                "edges_removed"       : len(edges_removed),
                "nodes_in_zone"       : len(nodes_in_zone),
            },

            # Map geometry — real coordinates per failed edge
            "failed_segments": failed_segments,

            # Both routes for comparison
            "normal_route": normal_route,
            "safe_route"  : safe_route,
        }


# ── Smoke test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not Path(DEFAULT_GRAPH_PATH).exists():
        print(f"Graph not found: {DEFAULT_GRAPH_PATH}")
    else:
        engine = RouteMindEngine()
        print(f"\nGraph summary: {engine.graph_summary()}")

        print("\nSimulation — Vasna 1500m, Satellite→Kankaria route:")
        sim = engine.simulate_failure_impact(
            lat             = 23.0089,
            lon             = 72.5588,
            radius_m        = 1500,
            route_start_lat = 23.0339,
            route_start_lon = 72.5262,
            route_end_lat   = 23.0064,
            route_end_lon   = 72.6022,
        )

        sr = sim["simulation_result"]
        print(f"  Population affected : {sr['population_affected']:,}")
        print(f"  Disconnected wards  : {sr['disconnected_wards']}")
        print(f"  Edges removed       : {sr['edges_removed']}")
        print(f"  Connectivity        : "
              f"{sr['connectivity_before']} → {sr['connectivity_after']}")
        print(f"  Resilience          : "
              f"{sr['resilience_before']} → {sr['resilience_after']}")
        print(f"  Priority            : "
              f"{sr['emergency_priority']} ({sr['priority_score']})")
        print(f"  Failed segments     : {len(sim['failed_segments'])} with coords")

        nr = sim.get("normal_route")
        sf = sim.get("safe_route")
        if nr and nr.get("status") == "success":
            print(f"\n  Normal : {nr['metrics']['distance_km']} km  "
                  f"{nr['metrics']['estimated_time_mins']} min")
        if sf and sf.get("status") == "success":
            print(f"  Safe   : {sf['metrics']['distance_km']} km  "
                  f"{sf['metrics']['estimated_time_mins']} min  "
                  f"(+{sf.get('detour_km', 0)} km detour)")