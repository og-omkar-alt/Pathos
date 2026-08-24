import json
import networkx as nx
from routing_engine import RouteMindEngine

print("Loading engine to extract 4 perfect demo routes...")
engine = RouteMindEngine()

# Grab the largest connected component so we know 100% these paths exist
largest_cc = list(max(nx.connected_components(engine.G), key=len))
total_nodes = len(largest_cc)

# Pick 4 distinct pairs of nodes spread across the graph
node_pairs = [
    (largest_cc[50], largest_cc[-50]),                        # Route 2: End-to-end
    (largest_cc[total_nodes // 4], largest_cc[-100]),         # Route 3: Quarter-span
    (largest_cc[total_nodes // 3], largest_cc[total_nodes // 2]), # Route 4: Short inner city
    (largest_cc[100], largest_cc[total_nodes // 3])           # Route 5: Mid-range arterial
]

for i, (n_start, n_end) in enumerate(node_pairs, 2): # Start counting at 2
    sd = engine.G.nodes[n_start]
    ed = engine.G.nodes[n_end]
    slon, slat = engine.to_gps.transform(sd["x"], sd["y"])
    elon, elat = engine.to_gps.transform(ed["x"], ed["y"])
    
    # Run the real A* routing
    res = engine.get_route(slat, slon, elat, elon, weight_type="travel_time", max_snap_dist_m=5000.0)
    
    # Flip to [Lon, Lat] for MapLibre
    if "route_coords" in res and len(res["route_coords"]) > 0:
        res["route_coords"] = [[c[1], c[0]] for c in res["route_coords"]]
        
    print(f"\n==================== ROUTE {i} ====================")
    print(json.dumps(res, indent=2))