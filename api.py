"""
SETU Project — FastAPI Backend  (Final Clean Version)
Changes:
  - SimRequest requires origin/destination — no silent defaults
  - hospitals_impacted removed from response
  - Added missing @app.post decorator for /api/v1/network/route
  - Fixed OSMnx "length" vs "length_m" dictionary bug
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import traceback

from routing_engine import RouteMindEngine

app = FastAPI(title="SETU RouteMind API", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Starting SETU backend ...")
engine = RouteMindEngine()
print("Engine ready.")


# ── Pydantic models ───────────────────────────────────────────────────────────

class RouteRequest(BaseModel):
    start_lat       : float
    start_lon       : float
    end_lat         : float
    end_lon         : float
    weight_type     : str   = "travel_time"
    max_snap_dist_m : float = 5000.0


class SimRequest(BaseModel):
    # Failure zone centre + radius
    lat      : float
    lon      : float
    radius_m : float = 800.0

    # Route comparison waypoints — REQUIRED, no defaults
    route_start_lat : float
    route_start_lon : float
    route_end_lat   : float
    route_end_lon   : float

    # Optional snap tolerance
    max_snap_dist_m : float = 3000.0


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/")
def health_check():
    return {
        "status" : "online",
        "system" : "SETU RouteMind AI",
        "summary": engine.graph_summary(),
    }


# ── Network summary ───────────────────────────────────────────────────────────

@app.get("/api/v1/network/summary")
def get_network_summary():
    try:
        import networkx as nx
        summary      = engine.graph_summary()
        n_nodes      = summary["nodes"]
        largest_cc   = len(max(nx.connected_components(engine.G), key=len))
        connectivity = round((largest_cc / max(n_nodes, 1)) * 100, 2)
        resilience   = round(
            1.0 - (summary["components"] / max(n_nodes, 1)), 4)

        return {
            "status" : "success",
            "metrics": {
                **summary,
                "connectivity": connectivity,
                "resilience"  : resilience,
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Network edges as GeoJSON ──────────────────────────────────────────────────

@app.get("/api/v1/network/edges")
def get_network_edges_geojson():
    """
    Returns every graph edge as a GeoJSON LineString with criticality.
    Use this to draw the live road network on the map.
    """
    try:
        features = []
        seen     = set()

        for u, v, data in engine.G.edges(data=True):
            key = (min(u, v), max(u, v))
            if key in seen:
                continue
            seen.add(key)

            nd_u = engine.G.nodes[u]
            nd_v = engine.G.nodes[v]
            lon_u, lat_u = engine.to_gps.transform(nd_u["x"], nd_u["y"])
            lon_v, lat_v = engine.to_gps.transform(nd_v["x"], nd_v["y"])

            cong = data.get("congestion_level", 1.0)
            if   cong >= 3.0: criticality = "HIGH"
            elif cong >= 2.0: criticality = "MEDIUM"
            elif cong >= 1.3: criticality = "LOW"
            else:             criticality = "VERY LOW"

            features.append({
                "type"    : "Feature",
                "geometry": {
                    "type"       : "LineString",
                    "coordinates": [[lon_u, lat_u], [lon_v, lat_v]],
                },
                "properties": {
                    "id"         : f"E-{u}-{v}",
                    # Fallback mapping for native OSMnx "length"
                    "length_m"   : round(data.get("length", data.get("length_m", 0)), 1),
                    "criticality": criticality,
                    "congestion" : round(cong, 2),
                },
            })

        return {"type": "FeatureCollection", "features": features}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Standard A* routing ───────────────────────────────────────────────────────

@app.get("/api/v1/network/test-waypoints")
def get_test_waypoints():
    """
    Returns two node coordinates guaranteed to be in the largest
    connected component.
    """
    try:
        import networkx as nx
        largest_cc  = max(nx.connected_components(engine.G), key=len)
        nodes       = list(largest_cc)
        n_start     = nodes[0]
        n_end       = nodes[len(nodes) // 2]
        s_lon, s_lat = engine.to_gps.transform(
            engine.G.nodes[n_start]["x"], engine.G.nodes[n_start]["y"])
        e_lon, e_lat = engine.to_gps.transform(
            engine.G.nodes[n_end]["x"],   engine.G.nodes[n_end]["y"])
        return {
            "status": "success",
            "start" : {"lat": round(s_lat, 6), "lon": round(s_lon, 6)},
            "end"   : {"lat": round(e_lat, 6), "lon": round(e_lon, 6)},
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/v1/simulation/demo-scenario")
def get_demo_scenario():
    """
    Returns a guaranteed working demo payload where:
    - Start and end are in the largest connected component
    - Failure zone sits on the normal route between them
    """
    try:
        import networkx as nx

        largest_cc = max(nx.connected_components(engine.G), key=len)
        nodes      = list(largest_cc)

        start_node = nodes[0]
        end_node   = nodes[len(nodes) // 2]

        try:
            path = nx.astar_path(
                engine.G, start_node, end_node,
                heuristic=engine._heuristic_time,
                weight="travel_time",
            )
        except nx.NetworkXNoPath:
            return {"status": "error",
                    "message": "Could not find base route in largest component."}

        # Place failure zone 1/3 along the route
        zone_node  = path[len(path) // 3]
        zone_nd    = engine.G.nodes[zone_node]
        zone_lon, zone_lat = engine.to_gps.transform(
            zone_nd["x"], zone_nd["y"])

        s_nd         = engine.G.nodes[start_node]
        e_nd         = engine.G.nodes[end_node]
        s_lon, s_lat = engine.to_gps.transform(s_nd["x"], s_nd["y"])
        e_lon, e_lat = engine.to_gps.transform(e_nd["x"], e_nd["y"])

        return {
            "status" : "success",
            "payload": {
                "lat"             : round(zone_lat, 6),
                "lon"             : round(zone_lon, 6),
                "radius_m"        : 500,
                "route_start_lat" : round(s_lat, 6),
                "route_start_lon" : round(s_lon, 6),
                "route_end_lat"   : round(e_lat, 6),
                "route_end_lon"   : round(e_lon, 6),
                "max_snap_dist_m" : 3000,
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/v1/network/route")
def calculate_route(data: RouteRequest):
    """
    Single A* route on the original graph.
    route_coords are [lon, lat] pairs — MapLibre native.
    """
    try:
        result = engine.get_route(
            data.start_lat,
            data.start_lon,
            data.end_lat,
            data.end_lon,
            weight_type    =data.weight_type,
            max_snap_dist_m=data.max_snap_dist_m,
        )
        return result
    except Exception as e:
        print(traceback.format_exc())
        return {"status": "error", "message": str(e), "route_coords": []}


# ── Full simulation ───────────────────────────────────────────────────────────

@app.post("/api/v1/simulation/simulate")
def run_simulation(data: SimRequest):
    try:
        result = engine.simulate_failure_impact(
            lat             =data.lat,
            lon             =data.lon,
            radius_m        =data.radius_m,
            route_start_lat =data.route_start_lat,
            route_start_lon =data.route_start_lon,
            route_end_lat   =data.route_end_lat,
            route_end_lon   =data.route_end_lon,
            max_snap_dist_m =data.max_snap_dist_m,
        )
        return result

    except Exception as e:
        print(traceback.format_exc())
        return {
            "status"           : "error",
            "message"          : str(e),
            "simulation_result": {},
            "failed_segments"  : [],
            "normal_route"     : None,
            "safe_route"       : None,
        }


if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)