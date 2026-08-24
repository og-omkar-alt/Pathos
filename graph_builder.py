"""
SETU Project — Phase 3
Graph Builder: Road Mask → Optical Graph Baseline

Architectural Fixes:
  1. Bidirectional edge tracing (prevents infinite loops/duplicates)
  2. Independent geometric vectors for D and C
  3. LoS Raycast spatial gate to prevent water/building crossings
  4. Strict optical heuristic thresholding (no fake SAR weights)
"""

import os
import json
import pickle
import numpy as np
import networkx as nx
import rasterio
from rasterio.transform import xy
from skimage.morphology import skeletonize
from skimage.draw import line
from scipy.spatial import cKDTree
from pathlib import Path
from tqdm import tqdm


# ============================================================
# CONFIGURATION
# ============================================================
BASE = r"C:\Users\omkar\OneDrive\Desktop\sih"

CONFIG = {
    
    "road_mask"     : rf"{BASE}\ahmedabad_outputs\ahmedabad_road_mask_phase5.tif",
    "road_prob"     : rf"{BASE}\ahmedabad_outputs\ahmedabad_road_probability_phase5.tif",
    "output_dir"    : rf"{BASE}\ahmedabad_outputs",

    # Strict Optical Heuristic Parameters
    "buffer_m"      : 100.0,    # max Euclidean gap (metres)
    "heuristic_thresh": 0.35,  # Strict gate for D+C alignment
    "los_min_prob"  : 0.05,    # Veto gaps crossing dead zones (<5% prob)

    # Centrality
    "k_betweenness" : 300,     
}


# ============================================================
# STEP 1 — SKELETONIZE & LOAD
# ============================================================
def load_data(mask_path, prob_path):
    print("\n[1/5] Loading spatial data and skeletonizing...")
    
    with rasterio.open(prob_path) as src:
        prob_map = src.read(1)
        
    with rasterio.open(mask_path) as src:
        mask       = src.read(1).astype(bool)
        transform  = src.transform
        crs        = src.crs
        pixel_m    = abs(src.transform.a)

    print(f"  Mask shape    : {mask.shape}")
    print(f"  Road pixels   : {mask.sum():,}")
    print(f"  Pixel size    : {pixel_m:.2f} m")

    skel = skeletonize(mask)
    print(f"  Skeleton px   : {skel.sum():,}")

    return skel, prob_map, transform, crs, pixel_m


# ============================================================
# STEP 2 — BUILD INITIAL GRAPH
# ============================================================
def skeleton_to_graph(skel, transform, pixel_m):
    print("\n[2/5] Building graph from skeleton...")

    H, W   = skel.shape
    rows, cols = np.where(skel)

    def get_neighbors(r, c):
        nbrs = []
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                r2, c2 = r + dr, c + dc
                if 0 <= r2 < H and 0 <= c2 < W and skel[r2, c2]:
                    nbrs.append((r2, c2))
        return nbrs

    G       = nx.Graph()
    node_px = {}    
    node_id = 0

    # Place nodes at endpoints (1 neighbour) and junctions (3+ neighbours)
    for r, c in zip(rows, cols):
        n = len(get_neighbors(r, c))
        if n == 1 or n >= 3:
            real_x, real_y = xy(transform, r, c)
            G.add_node(node_id,
                       row=int(r), col=int(c),
                       x=float(real_x), y=float(real_y),
                       node_type='endpoint' if n == 1 else 'junction')
            node_px[(r, c)] = node_id
            node_id += 1

    print(f"  Nodes placed  : {G.number_of_nodes():,}")

    # Bidirectional step tracking prevents duplicate edge tracing
    visited_steps = set()
    
    for (r0, c0), nid_start in tqdm(node_px.items(), desc="  Tracing edges"):
        for nr, nc in get_neighbors(r0, c0):
            step = tuple(sorted(((r0, c0), (nr, nc))))
            if step in visited_steps:
                continue
                
            path = [(r0, c0)]
            prev, curr = (r0, c0), (nr, nc)
            visited_steps.add(step)
            
            while curr not in node_px:
                path.append(curr)
                nxt = [p for p in get_neighbors(curr[0], curr[1]) if p != prev]
                if not nxt:
                    break
                
                next_step = tuple(sorted((curr, nxt[0])))
                visited_steps.add(next_step)
                prev, curr = curr, nxt[0]
                
            if curr in node_px:
                nid_end = node_px[curr]
                path.append(curr)
                length_m = len(path) * pixel_m
                G.add_edge(nid_start, nid_end,
                           length_m=length_m,
                           pixel_path=path[:5],   
                           edge_type='original')

    print(f"  Edges placed  : {G.number_of_edges():,}")
    G.remove_edges_from(nx.selfloop_edges(G))
    print(f"  Components    : {nx.number_connected_components(G):,}")
    return G


# ============================================================
# STEP 3 — HEURISTIC HEALING (OPTICAL ONLY)
# ============================================================
def compute_heuristic_score(G, ni, nj, prob_map):
    r_i, c_i = G.nodes[ni]['row'], G.nodes[ni]['col']
    r_j, c_j = G.nodes[nj]['row'], G.nodes[nj]['col']
    
    # 1. SPATIAL GATE: Line-of-Sight Raycast
    # Extract pixels along the path between the two dead ends
    rr, cc = line(r_i, c_i, r_j, c_j)
    if len(rr) > 2:
        gap_rr, gap_cc = rr[1:-1], cc[1:-1]
        gap_prob = prob_map[gap_rr, gap_cc]
        # VETO: If the maximum probability in the gap is absolutely dead (e.g. water)
        if np.max(gap_prob) < CONFIG["los_min_prob"]:
            return 0.0

    # 2. GEOMETRIC INDEPENDENCE
    xi, yi = G.nodes[ni]['x'], G.nodes[ni]['y']
    xj, yj = G.nodes[nj]['x'], G.nodes[nj]['y']
    
    # Gap Vector (A -> B)
    v_gap = np.array([xj - xi, yj - yi])
    norm_gap = np.linalg.norm(v_gap) + 1e-9
    u_gap = v_gap / norm_gap
    
    # Vector A (leaving Node A into the gap)
    nbrs_i = list(G.neighbors(ni))
    if nbrs_i:
        xn, yn = G.nodes[nbrs_i[0]]['x'], G.nodes[nbrs_i[0]]['y']
        v_A = np.array([xi - xn, yi - yn])
        u_A = v_A / (np.linalg.norm(v_A) + 1e-9)
    else:
        u_A = u_gap
        
    # Vector B (leaving Node B into the gap)
    nbrs_j = list(G.neighbors(nj))
    if nbrs_j:
        xn, yn = G.nodes[nbrs_j[0]]['x'], G.nodes[nbrs_j[0]]['y']
        v_B = np.array([xj - xn, yj - yn]) 
        u_B = v_B / (np.linalg.norm(v_B) + 1e-9)
    else:
        u_B = -u_gap
        
    # Direction: Do the stubs point AT the gap?
    direction_A = np.dot(u_A, u_gap)
    direction_B = np.dot(u_B, -u_gap)
    direction = (max(0.0, float(direction_A)) + max(0.0, float(direction_B))) / 2.0
    
    # Curvature: Do the stubs agree with each other?
    curvature = max(0.0, float(np.dot(u_A, -u_B)))
    
    # Strict 70/30 baseline heuristic (No fake SAR/Width variables)
    score = 0.7 * direction + 0.3 * curvature
    return score


class DSU:
    def __init__(self, nodes):
        self.parent = {n: n for n in nodes}
        self.rank   = {n: 0  for n in nodes}

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py:
            return False
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1
        return True

    def same(self, x, y):
        return self.find(x) == self.find(y)


def heal_graph(G, prob_map, buffer_m=15.0, threshold=0.80):
    print(f"\n[3/5] Strict Geometric Healing (Thresh: {threshold})...")

    G2       = G.copy()
    terminals = [n for n in G2.nodes() if G2.degree(n) == 1]
    print(f"  Terminal nodes: {len(terminals):,}")

    if len(terminals) < 2:
        print("  No gaps to heal")
        return G2

    coords = np.array([[G2.nodes[n]['x'], G2.nodes[n]['y']] for n in terminals])
    tree   = cKDTree(coords)
    pairs  = list(tree.query_pairs(r=buffer_m))
    print(f"  Candidate pairs within {buffer_m}m: {len(pairs):,}")

    scored = []
    for i, j in pairs:
        ni, nj = terminals[i], terminals[j]
        score  = compute_heuristic_score(G2, ni, nj, prob_map)
        scored.append((score, ni, nj))
    scored.sort(key=lambda x: x[0], reverse=True)

    dsu   = DSU(list(G2.nodes()))
    for u, v in G2.edges():
        dsu.union(u, v)

    added = 0
    for score, ni, nj in scored:
        if score < threshold:
            break
        if not dsu.same(ni, nj):
            xi, yi = G2.nodes[ni]['x'], G2.nodes[ni]['y']
            xj, yj = G2.nodes[nj]['x'], G2.nodes[nj]['y']
            dist   = np.sqrt((xi-xj)**2 + (yi-yj)**2)
            G2.add_edge(ni, nj,
                        length_m=dist,
                        heuristic_score=score,
                        edge_type='healed_baseline')
            dsu.union(ni, nj)
            added += 1

    print(f"  Edges healed  : {added:,}")
    print(f"  Components    : {nx.number_connected_components(G2):,}")
    return G2


# ============================================================
# STEP 4 — DIAGNOSTIC METRICS
# ============================================================
def compute_metrics(G, label=""):
    if G.number_of_nodes() == 0:
        print(f"\n  Metrics {label}: Empty Graph")
        return 0.0, 0.0

    components  = list(nx.connected_components(G))
    n_comp      = len(components)
    largest     = max(components, key=len)
    total_len_m = sum(d.get('length_m', 1.0) for _, _, d in G.edges(data=True))
    total_km    = total_len_m / 1000.0
    
    # Corrected terminology
    break_density = max(0, n_comp - 1) / max(total_km, 0.001)
    connectivity = len(largest) / max(G.number_of_nodes(), 1)

    print(f"\n  Metrics {label}:")
    print(f"    Nodes                  : {G.number_of_nodes():,}")
    print(f"    Edges                  : {G.number_of_edges():,}")
    print(f"    Components             : {n_comp:,}")
    print(f"    Road length            : {total_km:.1f} km")
    print(f"    Component Break Density: {break_density:.2f} (Diagnostic)")
    print(f"    Connectivity Ratio     : {connectivity:.3f}")
    return break_density, connectivity


# ============================================================
# STEP 5 — CENTRALITY
# ============================================================
def run_centrality(G, k=300):
    print(f"\n[5/5] Centrality analysis (k={k} sample)...")
    
    if G.number_of_nodes() == 0:
        return G

    print("  Betweenness centrality...")
    bet = nx.betweenness_centrality(G, k=min(k, G.number_of_nodes()),
                                    weight='length_m', normalized=True, seed=42)
    nx.set_node_attributes(G, bet, 'betweenness')

    print("  k-core decomposition...")
    core = nx.core_number(G)
    nx.set_node_attributes(G, core, 'core_number')
    max_k  = max(core.values()) if core else 1
    thresh = max(1, int(max_k * 0.7))
    nx.set_node_attributes(G, {n: (v >= thresh) for n, v in core.items()}, 'in_backbone')

    print("  Composite criticality...")
    max_bet = max(bet.values(), default=1.0)
    for node in G.nodes():
        b = G.nodes[node].get('betweenness', 0.0) / (max_bet + 1e-9)
        k_flag = 1.0 if G.nodes[node].get('in_backbone', False) else 0.0
        score  = 0.7 * b + 0.3 * k_flag
        G.nodes[node]['criticality'] = float(score)

        if score >= 0.7:
            G.nodes[node]['color'] = '#0F6E56'   
        elif score >= 0.3:
            G.nodes[node]['color'] = '#BA7517'   
        else:
            G.nodes[node]['color'] = '#9A9A9A'   

    for u, v, data in G.edges(data=True):
        cu = G.nodes[u].get('criticality', 0)
        cv = G.nodes[v].get('criticality', 0)
        s  = max(cu, cv)
        data['criticality'] = s
        if s >= 0.7:
            data['color'] = '#0F6E56'
            data['width'] = 4
        elif s >= 0.3:
            data['color'] = '#BA7517'
            data['width'] = 2
        else:
            data['color'] = '#9A9A9A'
            data['width'] = 1

    high = sum(1 for n in G.nodes if G.nodes[n].get('criticality', 0) >= 0.7)
    mid  = sum(1 for n in G.nodes if 0.3 <= G.nodes[n].get('criticality', 0) < 0.7)
    low  = sum(1 for n in G.nodes if G.nodes[n].get('criticality', 0) < 0.3)
    print(f"  High (teal)   : {high:,} nodes")
    print(f"  Medium (amber): {mid:,} nodes")
    print(f"  Low (gray)    : {low:,} nodes")

    return G


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("  SETU — Phase 5 SAR + Optical Graph Builder")
    print("=" * 60)

    os.makedirs(CONFIG["output_dir"], exist_ok=True)

    # Step 1
    skel, prob_map, transform, crs, pixel_m = load_data(CONFIG["road_mask"], CONFIG["road_prob"])

    # Step 2
    G_initial = skeleton_to_graph(skel, transform, pixel_m)
    breaks_before, conn_before = compute_metrics(G_initial, label="BEFORE heuristic")

    # Step 3
    G_healed = heal_graph(G_initial, prob_map,
                          buffer_m=CONFIG["buffer_m"],
                          threshold=CONFIG["heuristic_thresh"])
    breaks_after, conn_after = compute_metrics(G_healed, label="AFTER heuristic")

    # Step 4 summary
    print("\n" + "="*60)
    print("  PHASE 5 DUAL-MODAL GRAPH HEALING RESULTS:")
    print(f"    Component Break Density: {breaks_before:.2f} → {breaks_after:.2f}")
    print(f"    Connectivity Ratio     : {conn_before:.3f} → {conn_after:.3f}")
    print("="*60)

    # Step 5
    G_final = run_centrality(G_healed, k=CONFIG["k_betweenness"])

    # Save outputs
    # Save outputs
    graph_path = Path(CONFIG["output_dir"]) / "ahmedabad_graph_phase5.pkl"
    with open(str(graph_path), 'wb') as f:
        pickle.dump(G_final, f)
    print(f"\n  Phase 5 Graph saved  : {graph_path}")

    metrics = {
        "before_heuristic": {
            "component_break_density" : round(breaks_before, 3),
            "connectivity_ratio"      : round(conn_before, 3),
        },
        "after_heuristic": {
            "component_break_density" : round(breaks_after, 3),
            "connectivity_ratio"      : round(conn_after, 3),
        },
        "nodes" : G_final.number_of_nodes(),
        "edges" : G_final.number_of_edges(),
        "pixel_size_m" : pixel_m,
    }
    metrics_path = Path(CONFIG["output_dir"]) / "phase5_metrics.json"
    with open(str(metrics_path), 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"  Metrics saved        : {metrics_path}")

    print("\n  Next step: Deploy Phase 5 SAR Inference to heal remaining density.")


if __name__ == "__main__":
    main()