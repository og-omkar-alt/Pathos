"""
SETU Project — Telemetry Fusion & Routing Engine
Fuses the Phase 5 spatial graph with population density to calculate
dynamic traversal weights (population-weighted congestion proxy) for A* pathfinding.
Ensures strict grid alignment and robust node/edge validation.
"""

import pickle
import numpy as np
import networkx as nx
import rasterio
from rasterio.warp import reproject, Resampling
from skimage.draw import line
from pathlib import Path
from tqdm import tqdm

BASE = r"C:\Users\omkar\OneDrive\Desktop\sih"
GRAPH_PATH = rf"{BASE}\ahmedabad_outputs\ahmedabad_graph_phase5_wcs_final.pkl"
MASK_PATH  = rf"{BASE}\ahmedabad_outputs\ahmedabad_road_mask_phase5.tif"
POP_PATH   = rf"{BASE}\ahmedabad_outputs\ahmedabad_population_100m.tif"
OUT_PATH   = rf"{BASE}\ahmedabad_outputs\ahmedabad_routing_graph.pkl"

def build_telemetry_graph():
    print("=" * 60)
    print("  SETU — Fusing Network with Population Telemetry")
    print("=" * 60)

    print("\n[1/4] Loading and aligning spatial grids...")
    
    # Load road mask to get the reference grid
    with rasterio.open(MASK_PATH) as mask_src:
        ref_transform = mask_src.transform
        ref_crs       = mask_src.crs
        ref_H, ref_W  = mask_src.height, mask_src.width

    # Reproject population to match the road mask grid exactly
    with rasterio.open(POP_PATH) as pop_src:
        pop_aligned = np.zeros((ref_H, ref_W), dtype=np.float32)
        reproject(
            source=rasterio.band(pop_src, 1),
            destination=pop_aligned,
            src_transform=pop_src.transform, src_crs=pop_src.crs,
            dst_transform=ref_transform,     dst_crs=ref_crs,
            resampling=Resampling.bilinear
        )
        pop_grid = pop_aligned
        H, W     = ref_H, ref_W

    print("[2/4] Loading healed road graph...")
    with open(GRAPH_PATH, "rb") as f:
        G = pickle.load(f)

    # Robust normalization: 95th percentile of non-zero population cells
    valid_pop = pop_grid[pop_grid > 0]
    if len(valid_pop) > 0:
        max_pop = np.percentile(valid_pop, 95)
    else:
        max_pop = 1.0
        
    if max_pop == 0: max_pop = 1.0

    print(f"\n[3/4] Calculating population-weighted congestion proxy for {G.number_of_edges():,} edges...")
    
    for u, v, data in tqdm(G.edges(data=True), desc="  Processing network"):
        # Guard against nodes without row/col coordinates
        r1 = G.nodes[u].get('row')
        c1 = G.nodes[u].get('col')
        r2 = G.nodes[v].get('row')
        c2 = G.nodes[v].get('col')

        if None in (r1, c1, r2, c2):
            mean_density = 0.0
        else:
            rr, cc = line(int(r1), int(c1), int(r2), int(c2))
            valid = (rr >= 0) & (rr < H) & (cc >= 0) & (cc < W)
            mean_density = float(np.mean(pop_grid[rr[valid], cc[valid]])) if valid.any() else 0.0
        
        # Calculate proxy: Base speed multiplier (1.0x to 5.0x based on population density)
        density_ratio = np.clip(mean_density / max_pop, 0.0, 1.0)
        congestion_multiplier = 1.0 + (4.0 * density_ratio)
        
        # Base speed: assume 40 km/h (11.1 meters/second)
        base_speed_mps = 11.1
        length_m = data.get('length_m', 10.0)
        
        # Final weight: Proxy travel time in seconds to cross this edge
        travel_time_seconds = (length_m / base_speed_mps) * congestion_multiplier
        
        # Store attributes for the frontend routing engine
        G[u][v]['travel_time'] = float(travel_time_seconds)
        G[u][v]['congestion_level'] = float(congestion_multiplier)
        G[u][v]['pop_density'] = float(mean_density)

    print("\n[4/4] Summary and Save...")
    congestion_vals = [d['congestion_level'] for _,_,d in G.edges(data=True)]
    print(f"  Congestion multiplier — min: {min(congestion_vals):.2f}  "
          f"max: {max(congestion_vals):.2f}  "
          f"mean: {np.mean(congestion_vals):.2f}")

    with open(OUT_PATH, "wb") as f:
        pickle.dump(G, f)
        
    print("=" * 60)
    print(f"  System Ready! Routing graph updated with congestion proxy:")
    print(f"  {OUT_PATH}")
    print("=" * 60)

if __name__ == "__main__":
    build_telemetry_graph()