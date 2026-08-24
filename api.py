"""
SETU Project — FastAPI Backend Server
Bulletproof Edition - Guaranteed to return 200 OKs and valid GeoJSON formats.
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import numpy as np
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import traceback

# Import your core routing engine
from routing_engine import RouteMindEngine

# Initialize the FastAPI app
app = FastAPI(title="SETU RouteMind API", version="2.0")

# Bulletproof CORS: Allows any frontend (Vite, Next.js, vanilla) to connect without blocking
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("🚀 Starting SETU backend server... Loading ML Graph...")
engine = RouteMindEngine()
print("✅ Graph loaded successfully.")

# ══════════════════════════════════════════════════════════════════════════════
# PYDANTIC BLUEPRINTS
# ══════════════════════════════════════════════════════════════════════════════
class RouteRequest(BaseModel):
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    weight_type: str = "travel_time"
    max_snap_dist_m: float = 5000.0  # Defaulted to 5km to guarantee it finds a road

class DynamicSimRequest(BaseModel):
    lat: float = 23.0063
    lon: float = 72.5510
    radius_m: float = 800.0

# ══════════════════════════════════════════════════════════════════════════════
# CORE ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/")
def health_check():
    """System status and baseline KPI metrics."""
    return {
        "status": "online", 
        "system": "SETU RouteMind AI", 
        "summary": engine.graph_summary()
    }

@app.post("/api/v1/simulation/simulate")
def run_dynamic_simulation(data: DynamicSimRequest):
    """Executes network dissection. Never throws a 500, always returns a clean payload."""
    try:
        results = engine.simulate_failure_impact(
            lat=data.lat,
            lon=data.lon,
            radius_m=data.radius_m
        )
        return {"status": "success", "data": results}
    except Exception as e:
        print(f"Simulation Error: {traceback.format_exc()}")
        # Safe fallback so the UI doesn't explode
        return {"status": "error", "message": str(e), "data": {}}

@app.post("/api/v1/routing/route")
def calculate_route(data: RouteRequest):
    """
    Handles A* routing requests. 
    Converts [Lat, Lon] to [Lon, Lat] so MapLibre can draw it natively.
    Catches disconnected graph errors gracefully.
    """
    try:
        result = engine.get_route(
            data.start_lat, data.start_lon, 
            data.end_lat, data.end_lon, 
            weight_type=data.weight_type,
            max_snap_dist_m=data.max_snap_dist_m
        )
        
        # HACKATHON SAFETY NET: Catch disconnected nodes without throwing a 400 error
        if result.get("status") == "error":
            return {
                "status": "error", 
                "message": result.get("message", "No navigable path exists."),
                "route_coords": []
            }
            
        # NATIVE MAPLIBRE FORMATTING: Flip to [Lon, Lat] on the backend
        if "route_coords" in result and len(result["route_coords"]) > 0:
            flipped_coords = [[c[1], c[0]] for c in result["route_coords"]]
            result["route_coords"] = flipped_coords
            
        return result

    except Exception as e:
        print(f"Routing Error: {traceback.format_exc()}")
        return {"status": "error", "message": str(e), "route_coords": []}

# ══════════════════════════════════════════════════════════════════════════════
# DATA EXTRACTION ENDPOINTS (For rendering the frontend map)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/network/summary")
def get_network_summary():
    """Returns live graph statistics for the dashboard."""
    import networkx as nx
    try:
        summary = engine.graph_summary()
        n_nodes = summary["nodes"]
        n_edges = summary["edges"]
        n_components = summary["components"]
        total_km = summary["total_km"]

        largest_cc = len(max(nx.connected_components(engine.G), key=len))
        connectivity = round((largest_cc / max(n_nodes, 1)) * 100, 2)
        resilience = round(1.0 - (n_components / max(n_nodes, 1)), 4)

        return {
            "status": "success",
            "metrics": {
                "nodes": n_nodes,
                "edges": n_edges,
                "components": n_components,
                "total_km": total_km,
                "connectivity": connectivity,
                "resilience": resilience,
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/v1/network/edges")
def get_network_edges_geojson():
    """
    Returns all graph edges as a GeoJSON FeatureCollection.
    Use this endpoint to generate your baseline map lines!
    """
    try:
        features = []
        seen = set()

        for u, v, data in engine.G.edges(data=True):
            edge_key = (min(u, v), max(u, v))
            if edge_key in seen:
                continue
            seen.add(edge_key)

            nd_u = engine.G.nodes[u]
            nd_v = engine.G.nodes[v]

            lon_u, lat_u = engine.to_gps.transform(nd_u["x"], nd_u["y"])
            lon_v, lat_v = engine.to_gps.transform(nd_v["x"], nd_v["y"])

            length_m = data.get("length_m", 0.0)
            congestion = data.get("congestion_level", 1.0)

            if congestion >= 3.0: criticality = "HIGH"
            elif congestion >= 2.0: criticality = "MEDIUM"
            elif congestion >= 1.3: criticality = "LOW"
            else: criticality = "VERY LOW"

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[lon_u, lat_u], [lon_v, lat_v]]
                },
                "properties": {
                    "id": f"E-{u}-{v}",
                    "name": f"Segment ({round(length_m, 0)}m)",
                    "criticality": criticality
                }
            })

        return {"type": "FeatureCollection", "features": features}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)