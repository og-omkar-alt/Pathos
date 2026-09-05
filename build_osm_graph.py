"""
SETU Project — Build Ahmedabad Road Graph from OSM
Replaces the SAR-derived graph with a fully connected OSM graph.
Preserves the same node/edge attribute format so routing_engine.py
works without any changes.
"""

import pickle
import numpy as np
import networkx as nx
from pyproj import Transformer
from pathlib import Path

import urllib3.util.connection as urllib3_cn
urllib3_cn.HAS_IPV6 = False

try:
    import osmnx as ox
except ImportError:
    raise ImportError("Run: pip install osmnx --break-system-packages")

BASE     = r"C:\Users\omkar\OneDrive\Desktop\sih"
OUT_PATH = rf"{BASE}\ahmedabad_outputs\ahmedabad_routing_graph.pkl"

# ── Config ────────────────────────────────────────────────────────────────────
PLACE         = "Ahmedabad, Gujarat, India"
NETWORK_TYPE  = "drive"          # driveable roads only
AVG_SPEED_MPS = 11.1             # 40 km/h

def build():
    print("=" * 60)
    print("  SETU — Building OSM Road Graph for Ahmedabad")
    print("=" * 60)

    # ── 1. Download OSM road network ──────────────────────────────────────────
    print(f"\n[1/5] Loading road network from local XML file ...")
    
    # Point this to the exact location where you saved the exported file
    osm_file_path = rf"{BASE}\ahmedabad.osm"
    
    # Read the graph directly from the local file, bypassing all network checks
    G_directed = ox.graph_from_xml(osm_file_path)
    
    print(f"      Loaded: {G_directed.number_of_nodes():,} nodes, "
          f"{G_directed.number_of_edges():,} edges (directed)")

    # ── 2. Convert to undirected ──────────────────────────────────────────────
    print("\n[2/5] Converting to undirected graph ...")
    G = G_directed.to_undirected()
    print(f"      Undirected: {G.number_of_nodes():,} nodes, "
          f"{G.number_of_edges():,} edges")

    # ── 3. Add UTM coordinates (x, y) to every node ───────────────────────────
    # routing_engine.py expects x, y in EPSG:32643 (UTM Zone 43N)
    print("\n[3/5] Adding UTM coordinates to nodes ...")
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
    to_gps = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)

    for node_id, data in G.nodes(data=True):
        # OSMnx stores lon=x, lat=y in EPSG:4326
        lon = data.get("x", 0.0)
        lat = data.get("y", 0.0)
        utm_x, utm_y = to_utm.transform(lon, lat)
        data["x"]   = float(utm_x)
        data["y"]   = float(utm_y)
        data["lon"] = float(lon)
        data["lat"] = float(lat)
        # row/col not needed for OSM graph (no raster pixel coords)
        data["row"] = 0
        data["col"] = 0

    # ── 4. Add edge attributes ────────────────────────────────────────────────
    print("\n[4/5] Adding edge attributes (length, travel_time, congestion) ...")

    for u, v, data in G.edges(data=True):
        # Length — OSMnx provides this in metres
        length_m = float(data.get("length", 100.0))
        data["length_m"] = length_m

        # Travel time — base speed 40 km/h
        data["travel_time"] = length_m / AVG_SPEED_MPS

        # Congestion proxy — use highway type as a surrogate
        highway = data.get("highway", "residential")
        if isinstance(highway, list):
            highway = highway[0]

        if   "motorway"   in str(highway): congestion = 1.2
        elif "trunk"      in str(highway): congestion = 1.3
        elif "primary"    in str(highway): congestion = 1.5
        elif "secondary"  in str(highway): congestion = 1.8
        elif "tertiary"   in str(highway): congestion = 2.0
        elif "residential"in str(highway): congestion = 2.5
        else:                              congestion = 2.0

        data["congestion_level"] = congestion
        # Congestion-weighted travel time
        data["travel_time"] = (length_m / AVG_SPEED_MPS) * congestion

    # ── 5. Report and save ────────────────────────────────────────────────────
    print("\n[5/5] Analysing and saving ...")

    n_components = nx.number_connected_components(G)
    largest_cc   = max(nx.connected_components(G), key=len)
    connectivity = round(len(largest_cc) / G.number_of_nodes() * 100, 1)
    total_km     = sum(d.get("length_m", 0)
                       for _, _, d in G.edges(data=True)) / 1000.0

    print(f"\n  Nodes              : {G.number_of_nodes():,}")
    print(f"  Edges              : {G.number_of_edges():,}")
    print(f"  Components         : {n_components:,}")
    print(f"  Largest component  : {len(largest_cc):,} nodes")
    print(f"  Connectivity       : {connectivity}%")
    print(f"  Total road length  : {total_km:,.1f} km")

    # Verify Vasna area is covered
    vasna_test_lon, vasna_test_lat = 72.5588, 23.0089
    vasna_utm_x, vasna_utm_y = to_utm.transform(vasna_test_lon, vasna_test_lat)

    from scipy.spatial import cKDTree
    coords   = np.array([[d["x"], d["y"]]
                          for _, d in G.nodes(data=True)], dtype=np.float64)
    tree     = cKDTree(coords)
    dist, _  = tree.query([vasna_utm_x, vasna_utm_y])
    print(f"\n  Vasna (23.0089, 72.5588) nearest node: {dist:.0f} m away")
    if dist < 500:
        print("  ✅ Vasna area IS covered — flood scenario will work!")
    else:
        print(f"  ⚠ Vasna nearest node is {dist:.0f}m away — "
              f"may need wider snap distance")

    Path(OUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "wb") as f:
        pickle.dump(G, f)

    print(f"\n  Saved → {OUT_PATH}")
    print("=" * 60)
    print("  Run api.py — routing engine will load the new graph.")
    print("=" * 60)

if __name__ == "__main__":
    build()