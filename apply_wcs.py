"""
SETU Project — Deterministic WCS Healing for Ahmedabad Phase 5  (Final)
Formula   : WCS = 0.35*D + 0.25*S + 0.20*W + 0.20*C
Pass 1    : WCS >= 0.70, buffer = 200 m
Pass 2    : WCS >= 0.60, buffer = 200 m  (on Pass-1 output)
Output    : healed graph pickle + full quality report
"""

import math
import pickle
import numpy as np
import networkx as nx
import rasterio
from rasterio.transform import xy
from rasterio.warp import reproject, Resampling
from scipy.ndimage import distance_transform_edt, maximum_filter
from scipy.spatial import cKDTree
from skimage.morphology import skeletonize
from skimage.draw import line
from pathlib import Path
from tqdm import tqdm

# ── Config ────────────────────────────────────────────────────────────────────
BASE = r"C:\Users\omkar\OneDrive\Desktop\sih"

CONFIG = {
    "road_mask"  : rf"{BASE}\ahmedabad_outputs\ahmedabad_road_mask_phase5.tif",
    "sar_raw"    : rf"{BASE}\ahmedabad_processed\ahmedabad_S1_VV_VH.tif",
    "output_dir" : rf"{BASE}\ahmedabad_outputs",
    "buffer_m"   : 200.0,   # max gap to consider bridging (metres)
    "wcs_thresh" : 0.70,    # Pass 1 threshold
    "lookback"   : 5,       # skeleton steps for stub direction estimate
    "sar_dil"    : 2,       # half-width of SAR corridor filter (pixels)
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def norm01(x):
    valid = np.isfinite(x) & (x > 0)
    if not valid.any():
        return np.zeros_like(x, dtype=np.float32)
    p2, p98 = np.percentile(x[valid], [2, 98])
    return np.clip((x - p2) / (p98 - p2 + 1e-6), 0, 1)


def pixel_size_metres(src):
    """
    Return pixel size in metres for both projected and geographic CRS.
    Uses Haversine for geographic (degree-based) CRS so EPSG:4326 masks
    are handled correctly.
    """
    if src.crs and src.crs.is_projected:
        return abs(src.transform.a)

    # Geographic CRS — measure one pixel east at the image centre
    cy, cx = src.height / 2, src.width / 2
    lon1, lat1 = src.xy(cy, cx)
    lon2, lat2 = src.xy(cy, cx + 1)
    R    = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a    = (math.sin(dphi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_stub_vector(r, c, skel, H, W, lookback=5):
    """
    Walk up to `lookback` steps along the skeleton from endpoint (r, c)
    to get a stable outgoing direction.  Returns unit vector or None.
    """
    visited = {(r, c)}
    cur     = (r, c)
    for _ in range(lookback):
        moved = False
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = cur[0] + dr, cur[1] + dc
                if (0 <= nr < H and 0 <= nc < W
                        and skel[nr, nc] and (nr, nc) not in visited):
                    visited.add((nr, nc))
                    cur   = (nr, nc)
                    moved = True
                    break
            if moved:
                break
        if not moved:
            break
    v = np.array([r - cur[0], c - cur[1]], dtype=np.float32)
    n = np.linalg.norm(v)
    return v / n if n > 1e-6 else None


def network_metrics(G):
    comps    = nx.number_connected_components(G)
    total_m  = sum(d.get("length_m", 1.0) for _, _, d in G.edges(data=True))
    total_km = max(total_m / 1000.0, 0.001)
    density  = (comps - 1) / total_km      # breaks per km — lower is better
    return comps, total_km, density


# ── Step 1: load data ─────────────────────────────────────────────────────────
def load_data():
    print("\n[1/5] Loading road mask and SAR data ...")

    with rasterio.open(CONFIG["road_mask"]) as mask_src:
        mask      = mask_src.read(1).astype(bool)
        transform = mask_src.transform
        crs       = mask_src.crs
        H, W      = mask_src.height, mask_src.width
        pixel_m   = pixel_size_metres(mask_src)

    print(f"  Mask  : {H}x{W}  |  pixel_m = {pixel_m:.4f} m  |  CRS = {crs}")

    # Reproject SAR onto the mask grid so pixel indices align exactly
    vv = np.zeros((H, W), dtype=np.float32)
    vh = np.zeros((H, W), dtype=np.float32)
    with rasterio.open(CONFIG["sar_raw"]) as sar_src:
        reproject(source=rasterio.band(sar_src, 1), destination=vv,
                  src_transform=sar_src.transform, src_crs=sar_src.crs,
                  dst_transform=transform, dst_crs=crs,
                  resampling=Resampling.bilinear)
        reproject(source=rasterio.band(sar_src, 2), destination=vh,
                  src_transform=sar_src.transform, src_crs=sar_src.crs,
                  dst_transform=transform, dst_crs=crs,
                  resampling=Resampling.bilinear)

    sar_norm     = 0.5 * norm01(vv) + 0.5 * norm01(vh)
    kernel       = 2 * CONFIG["sar_dil"] + 1
    sar_corridor = maximum_filter(sar_norm, size=kernel)

    # Width map in pixels (ratio in W_feat is dimensionless)
    width_map = distance_transform_edt(mask)
    skel      = skeletonize(mask)

    print(f"  Road px : {mask.sum():,}  |  Skeleton px : {skel.sum():,}")
    return skel, sar_corridor, width_map, transform, pixel_m, H, W


# ── Step 2: build graph ───────────────────────────────────────────────────────
def skeleton_to_graph(skel, transform, pixel_m, H, W):
    print("\n[2/5] Building road graph from skeleton ...")

    def neighbours(r, c):
        return [
            (r + dr, c + dc)
            for dr in (-1, 0, 1) for dc in (-1, 0, 1)
            if (dr != 0 or dc != 0)
            and 0 <= r + dr < H and 0 <= c + dc < W
            and skel[r + dr, c + dc]
        ]

    rows, cols = np.where(skel)
    node_px    = {}
    G          = nx.Graph()
    node_id    = 0

    for r, c in zip(rows, cols):
        if len(neighbours(r, c)) != 2:          # junction or endpoint
            rx, ry = xy(transform, r, c)
            G.add_node(node_id, row=int(r), col=int(c),
                       x=float(rx), y=float(ry))
            node_px[(r, c)] = node_id
            node_id += 1

    visited_edges = set()
    for (r0, c0), nid_start in tqdm(node_px.items(), desc="  Tracing edges"):
        for nr0, nc0 in neighbours(r0, c0):
            key = tuple(sorted(((r0, c0), (nr0, nc0))))
            if key in visited_edges:
                continue
            visited_edges.add(key)

            path_len = 1
            prev, cur = (r0, c0), (nr0, nc0)
            while cur not in node_px:
                nxts = [p for p in neighbours(*cur) if p != prev]
                if not nxts:
                    break
                k2 = tuple(sorted((cur, nxts[0])))
                visited_edges.add(k2)
                prev, cur = cur, nxts[0]
                path_len += 1

            if cur in node_px:
                G.add_edge(nid_start, node_px[cur],
                           length_m=path_len * pixel_m)

    G.remove_edges_from(nx.selfloop_edges(G))
    print(f"  Nodes: {G.number_of_nodes():,}  |  Edges: {G.number_of_edges():,}"
          f"  |  Components: {nx.number_connected_components(G):,}")
    return G


# ── Step 3 & 4: WCS healing (reusable for both passes) ───────────────────────
def heal_wcs(G, skel, sar_corridor, width_map, pixel_m, H, W,
             threshold_override=None):
    threshold = threshold_override if threshold_override is not None \
                else CONFIG["wcs_thresh"]
    buf_px    = CONFIG["buffer_m"] / pixel_m
    lookback  = CONFIG["lookback"]

    G2        = G.copy()
    terminals = [n for n in G2.nodes() if G2.degree(n) == 1]
    print(f"  Terminal endpoints : {len(terminals):,}")

    if len(terminals) < 2:
        print("  No terminals to heal.")
        return G2

    coords_px = np.array([[G2.nodes[n]['row'], G2.nodes[n]['col']]
                           for n in terminals], dtype=np.float32)
    pairs     = list(cKDTree(coords_px).query_pairs(r=buf_px))
    print(f"  Candidate pairs within {CONFIG['buffer_m']:.0f} m : {len(pairs):,}")

    candidates = []

    for i, j in pairs:
        ni, nj = terminals[i], terminals[j]
        ri, ci = G2.nodes[ni]['row'], G2.nodes[ni]['col']
        rj, cj = G2.nodes[nj]['row'], G2.nodes[nj]['col']

        # Stub vectors
        u1 = get_stub_vector(ri, ci, skel, H, W, lookback)
        u2 = get_stub_vector(rj, cj, skel, H, W, lookback)
        if u1 is None or u2 is None:
            continue

        # Gap vector in pixel space
        v_gap    = np.array([rj - ri, cj - ci], dtype=np.float32)
        gap_norm = float(np.linalg.norm(v_gap)) + 1e-9
        u_gap    = v_gap / gap_norm

        # D — directional alignment
        D = (max(0.0, float(np.dot(u1,  u_gap))) +
             max(0.0, float(np.dot(u2, -u_gap)))) / 2.0
        if D < 0.10:
            continue

        # C — collinearity
        C = max(0.0, float(np.dot(u1, -u2)))

        # W — width compatibility
        w1 = float(width_map[ri, ci])
        w2 = float(width_map[rj, cj])
        if w1 < 1.0 or w2 < 1.0:
            continue
        W_feat = 1.0 - abs(w1 - w2) / max(w1, w2)

        # S — SAR confidence along gap corridor
        rr, cc    = line(ri, ci, rj, cj)
        in_bounds = (rr >= 0) & (rr < H) & (cc >= 0) & (cc < W)
        if in_bounds.sum() == 0:
            continue
        S = float(np.mean(sar_corridor[rr[in_bounds], cc[in_bounds]]))

        # WCS score
        wcs = 0.35 * D + 0.25 * S + 0.20 * W_feat + 0.20 * C
        if wcs >= threshold:
            candidates.append((wcs, ni, nj, gap_norm * pixel_m))

    print(f"  Candidates passing WCS >= {threshold:.2f} : {len(candidates):,}")

    if not candidates:
        print("  Nothing healed — try lowering threshold or raising buffer_m.")
        return G2

    candidates.sort(key=lambda x: x[0], reverse=True)

    # Union-Find — initialise from existing edges so we never create
    # redundant bridges inside already-connected components
    parent = {n: n for n in G2.nodes()}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        pa, pb = find(a), find(b)
        if pa == pb:
            return False
        parent[pb] = pa
        return True

    for u, v in G2.edges():
        union(u, v)

    added = 0
    for wcs, ni, nj, gap_m in candidates:
        if union(ni, nj):
            G2.add_edge(ni, nj, length_m=float(gap_m), wcs=float(wcs))
            added += 1

    print(f"  Edges healed : {added:,}")
    return G2


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("  SETU -- Deterministic WCS Healing  |  Ahmedabad Phase 5")
    print("=" * 65)

    out_dir = Path(CONFIG["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    for key in ("road_mask", "sar_raw"):
        if not Path(CONFIG[key]).exists():
            print(f"  ERROR: {key} not found -> {CONFIG[key]}")
            return

    # Load
    skel, sar_corridor, width_map, transform, pixel_m, H, W = load_data()

    # Build initial graph
    G_initial = skeleton_to_graph(skel, transform, pixel_m, H, W)
    c_b, km_b, d_b = network_metrics(G_initial)

    # Pass 1 — conservative (WCS >= 0.70)
    print("\n[3/5] Pass 1 -- WCS >= 0.70 ...")
    G_pass1 = heal_wcs(G_initial, skel, sar_corridor, width_map, pixel_m, H, W)
    c_a1, km_a1, d_a1 = network_metrics(G_pass1)

    # Pass 2 — relaxed on pass-1 output (WCS >= 0.60)
    print("\n[4/5] Pass 2 -- WCS >= 0.60 ...")
    G_pass2 = heal_wcs(G_pass1, skel, sar_corridor, width_map, pixel_m, H, W,
                       threshold_override=0.60)
    c_a2, km_a2, d_a2 = network_metrics(G_pass2)

    # Report
    print("\n[5/5] Network Quality Report")
    print("=" * 65)
    print(f"  {'Metric':<35} {'Before':>10} {'Pass 1':>10} {'Pass 2':>10}")
    print(f"  {'-'*65}")
    print(f"  {'Connected components':<35} {c_b:>10,} {c_a1:>10,} {c_a2:>10,}")
    print(f"  {'Total road length (km)':<35} {km_b:>10.1f} {km_a1:>10.1f} {km_a2:>10.1f}")
    print(f"  {'Break density (breaks/km)':<35} {d_b:>10.3f} {d_a1:>10.3f} {d_a2:>10.3f}")
    r1 = 100.0 * (d_b - d_a1) / max(d_b, 1e-9)
    r2 = 100.0 * (d_b - d_a2) / max(d_b, 1e-9)
    print(f"\n  Break-density reduction -- Pass 1: {r1:.1f}%  |  Pass 2: {r2:.1f}%")
    print("=" * 65)

    # Save final healed graph (Pass 2)
    out_path = out_dir / "ahmedabad_graph_phase5_wcs_final.pkl"
    with open(out_path, "wb") as f:
        pickle.dump(G_pass2, f)
    print(f"\n  Final graph saved -> {out_path}")


if __name__ == "__main__":
    main()