"""
SETU Project — Production-Grade 4F WCS Learner (v4)
Key Fix: Skeleton-connectivity labeling replaces straight-line coverage.
  - Positive: endpoints NOT connected through skeleton, but lie near a real road (gap to fill)
  - Negative: endpoints with no road in their corridor at all
Other fixes carried forward: lookback stub vectors, EDT border masking,
  SAR corridor sampling, raw feature caching, 3-way split, tile outlier capping.
"""

import pickle
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from pathlib import Path
from collections import deque
from scipy.ndimage import distance_transform_edt, binary_dilation, maximum_filter
from scipy.spatial import cKDTree
from skimage.morphology import skeletonize
from skimage.draw import line
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import precision_recall_curve, f1_score
from sklearn.model_selection import train_test_split
from tqdm import tqdm

# ── Paths ────────────────────────────────────────────────────────────────────
BASE      = r"C:\Users\omkar\OneDrive\Desktop\sih"
MASK_DIR  = Path(BASE) / "spacenet_prepared" / "Mumbai" / "masks"
SAR_MOSAIC= Path(BASE) / "sentinel1_training" / "mumbai.tif"
CACHE_FILE= Path(BASE) / "checkpoints_phase5" / "wcs_features_cache_v4.pkl"

# ── Helpers ──────────────────────────────────────────────────────────────────
def norm01(x):
    valid = np.isfinite(x) & (x > 0)
    if not valid.any():
        return np.zeros_like(x, dtype=np.float32)
    p2, p98 = np.percentile(x[valid], [2, 98])
    return np.clip((x - p2) / (p98 - p2 + 1e-6), 0, 1)


def skeleton_connected_bfs(skel, r1, c1, r2, c2, max_path_px):
    """
    BFS on the skeleton to check whether (r1,c1) and (r2,c2) are already
    joined through existing skeleton pixels within max_path_px steps.
    Returns True if connected, False otherwise.
    """
    H, W = skel.shape
    target = (r2, c2)
    visited = np.zeros((H, W), dtype=bool)
    visited[r1, c1] = True
    queue = deque()
    queue.append((r1, c1, 0))

    while queue:
        r, c, dist = queue.popleft()
        if (r, c) == target:
            return True
        if dist >= max_path_px:
            continue
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < H and 0 <= nc < W and not visited[nr, nc] and skel[nr, nc]:
                    visited[nr, nc] = True
                    queue.append((nr, nc, dist + 1))
    return False


def get_stub_vector(r, c, skel, H, W, lookback=5):
    """
    Walk up to `lookback` steps along the skeleton away from endpoint (r,c)
    to get a stable outgoing direction vector.
    Returns unit vector or None if the endpoint is a single isolated pixel.
    """
    visited = {(r, c)}
    cur = (r, c)
    for _ in range(lookback):
        found = False
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = cur[0] + dr, cur[1] + dc
                if (0 <= nr < H and 0 <= nc < W
                        and skel[nr, nc] and (nr, nc) not in visited):
                    visited.add((nr, nc))
                    cur = (nr, nc)
                    found = True
                    break
            if found:
                break
        if not found:
            break
    v = np.array([r - cur[0], c - cur[1]], dtype=np.float32)
    norm = np.linalg.norm(v)
    if norm < 1e-6:
        return None          # single-pixel isolated fragment
    return v / norm


# ── Feature extraction ───────────────────────────────────────────────────────
def extract_4f_features(mask_path, sar_src,
                         buffer_m=100.0,
                         max_pos=1500, max_neg=4500,
                         border_px=5,
                         corridor_dilation=3):
    """
    Extract (D, S, W, C) feature vectors with skeleton-connectivity labels.

    Label logic
    -----------
    positive (1): pair is NOT connected through the skeleton (genuine gap)
                  AND the dilated corridor between them overlaps the GT road mask
                  at >= 60 % coverage  →  a gap that should be bridged.
    negative (0): pair has < 20 % road coverage in the corridor
                  →  not a road connection at all.
    ambiguous   : everything in between is dropped.
    """
    try:
        with rasterio.open(mask_path) as mask_src:
            gt_mask  = mask_src.read(1) > 0
            from pyproj import Transformer

            def get_pixel_size_metres(src):
                """Return pixel size in metres regardless of CRS."""
                if src.crs.is_projected:
                    return abs(src.transform.a)
                else:
                    # Geographic CRS: convert a 1-pixel step at image centre to metres
                    cx = src.width  / 2
                    cy = src.height / 2
                    lon1, lat1 = src.xy(cy, cx)
                    lon2, lat2 = src.xy(cy, cx + 1)
                    transformer = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True)
                    # Use geopy great-circle approximation
                    import math
                    R = 6_371_000  # Earth radius metres
                    phi1, phi2 = math.radians(lat1), math.radians(lat2)
                    dphi = math.radians(lat2 - lat1)
                    dlam = math.radians(lon2 - lon1)
                    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
                    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            H, W     = mask_src.height, mask_src.width

            vv = np.zeros((H, W), dtype=np.float32)
            vh = np.zeros((H, W), dtype=np.float32)
            reproject(source=rasterio.band(sar_src, 1), destination=vv,
                      src_transform=sar_src.transform, src_crs=sar_src.crs,
                      dst_transform=mask_src.transform, dst_crs=mask_src.crs,
                      resampling=Resampling.bilinear)
            reproject(source=rasterio.band(sar_src, 2), destination=vh,
                      src_transform=sar_src.transform, src_crs=sar_src.crs,
                      dst_transform=mask_src.transform, dst_crs=mask_src.crs,
                      resampling=Resampling.bilinear)

        # SAR: pre-dilated corridor via maximum filter (fast)
        sar_norm     = 0.5 * norm01(vv) + 0.5 * norm01(vh)
        sar_corridor = maximum_filter(sar_norm, size=2 * corridor_dilation + 1)

        # EDT width map with border masking
        width_map = distance_transform_edt(gt_mask) * 2.0 * pixel_m
        width_map[:border_px,  :] = 0
        width_map[-border_px:, :] = 0
        width_map[:,  :border_px] = 0
        width_map[:, -border_px:] = 0

        skel = skeletonize(gt_mask)

        # Find skeleton endpoints (degree-1 nodes)
        endpoints = []
        rows, cols = np.where(skel)
        for r, c in zip(rows, cols):
            nbrs = sum(
                1 for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                if (dr != 0 or dc != 0)
                and 0 <= r + dr < H and 0 <= c + dc < W
                and skel[r + dr, c + dc]
            )
            if nbrs == 1:
                endpoints.append((r, c))

        if len(endpoints) < 2:
            return [], []

        ep_arr = np.array(endpoints, dtype=np.float32)
        pairs  = list(cKDTree(ep_arr * pixel_m).query_pairs(r=buffer_m))

        if len(pairs) > 50_000:
            print(f"\n  ⚠ Outlier tile: {Path(mask_path).name} — {len(pairs):,} pairs")

        pos_samples, neg_samples = [], []
        stats = {"pos": 0, "neg": 0, "drop": 0, "already_connected": 0,
                 "geom_veto": 0, "bad_width": 0}

        for i, j in pairs:
            (r1, c1), (r2, c2) = endpoints[i], endpoints[j]

            # ── Border / width guard ─────────────────────────────────────────
            if (r1 < border_px or r1 >= H - border_px or
                    c1 < border_px or c1 >= W - border_px or
                    r2 < border_px or r2 >= H - border_px or
                    c2 < border_px or c2 >= W - border_px):
                stats["bad_width"] += 1
                continue

            w1, w2 = width_map[r1, c1], width_map[r2, c2]
            if w1 < 1.0 or w2 < 1.0:
                stats["bad_width"] += 1
                continue

            # ── Gap vector ───────────────────────────────────────────────────
            v_gap    = np.array([r2 - r1, c2 - c1], dtype=np.float32)
            norm_gap = float(np.linalg.norm(v_gap)) + 1e-9
            u_gap    = v_gap / norm_gap
            gap_px   = norm_gap   # in pixels

            # ── Stub vectors (lookback) ──────────────────────────────────────
            u1 = get_stub_vector(r1, c1, skel, H, W)
            u2 = get_stub_vector(r2, c2, skel, H, W)
            if u1 is None or u2 is None:
                continue

            D = (max(0.0, float(np.dot(u1,  u_gap))) +
                 max(0.0, float(np.dot(u2, -u_gap)))) / 2.0
            if D < 0.1:
                stats["geom_veto"] += 1
                continue

            C = max(0.0, float(np.dot(u1, -u2)))

            # ── Features ────────────────────────────────────────────────────
            W_feat = 1.0 - abs(w1 - w2) / max(w1, w2, 1.0)

            rr, cc  = line(r1, c1, r2, c2)
            in_bounds = (rr >= 0) & (rr < H) & (cc >= 0) & (cc < W)
            if in_bounds.sum() == 0:
                continue

            S = float(np.mean(sar_corridor[rr[in_bounds], cc[in_bounds]]))

            feat_vector = [D, S, W_feat, C]

            # ── LABEL: skeleton-connectivity + corridor road coverage ────────
            max_bfs_px = int(gap_px * 1.5)
            already_joined = skeleton_connected_bfs(
                skel, r1, c1, r2, c2, max_path_px=max_bfs_px)

            if already_joined:
                # Already connected through existing skeleton — not a gap
                stats["already_connected"] += 1
                neg_samples.append(feat_vector)   # strong negative: redundant link
                continue

            # Build a dilated corridor mask around the straight line
            line_mask          = np.zeros((H, W), dtype=bool)
            line_mask[rr[in_bounds], cc[in_bounds]] = True
            corridor_mask      = binary_dilation(line_mask, iterations=corridor_dilation)
            corridor_px        = corridor_mask.sum()
            road_in_corridor   = float((gt_mask & corridor_mask).sum())
            coverage           = road_in_corridor / max(corridor_px, 1)

            if coverage >= 0.60:
                pos_samples.append(feat_vector)
                stats["pos"] += 1
            elif coverage <= 0.20:
                neg_samples.append(feat_vector)
                stats["neg"] += 1
            else:
                stats["drop"] += 1

        # ── Tile-level outlier capping ───────────────────────────────────────
        if len(pos_samples) > max_pos:
            idx = np.random.choice(len(pos_samples), max_pos, replace=False)
            pos_samples = [pos_samples[k] for k in idx]
        if len(neg_samples) > max_neg:
            idx = np.random.choice(len(neg_samples), max_neg, replace=False)
            neg_samples = [neg_samples[k] for k in idx]

        return pos_samples, neg_samples

    except Exception as e:
        print(f"\n  ERROR [{Path(mask_path).name}]: {type(e).__name__}: {e}")
        return [], []


# ── Dataset balancing ────────────────────────────────────────────────────────
def balance_dataset(pos, neg, ratio=3):
    if len(pos) == 0 or len(neg) == 0:
        return np.empty((0, 4)), np.array([])
    pos_arr, neg_arr = np.array(pos), np.array(neg)
    max_pos = min(len(pos_arr), len(neg_arr) // ratio)
    if max_pos == 0:
        return np.empty((0, 4)), np.array([])
    pos_idx = np.random.choice(len(pos_arr), max_pos, replace=False)
    neg_idx = np.random.choice(len(neg_arr), max_pos * ratio, replace=False)
    X = np.vstack([pos_arr[pos_idx], neg_arr[neg_idx]])
    y = np.array([1] * max_pos + [0] * (max_pos * ratio))
    return X, y


def process_tile_set(tiles, sar_src, desc):
    pos_all, neg_all = [], []
    for t in tqdm(tiles, desc=desc):
        pos, neg = extract_4f_features(t, sar_src)
        pos_all.extend(pos)
        neg_all.extend(neg)
    return pos_all, neg_all


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("  SETU WCS v4 — Skeleton-Connectivity Labels + 3-Way Split")
    print("=" * 65)

    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tiles = sorted(MASK_DIR.glob("*.tif"))

    if not SAR_MOSAIC.exists() or len(tiles) == 0:
        print("ERROR: SAR mosaic or mask tiles not found.")
        return

    # 3-way split: 70 % train | 15 % val | 15 % test
    np.random.seed(42)
    train_tiles, temp_tiles = train_test_split(tiles, test_size=0.30, random_state=42)
    val_tiles,  test_tiles  = train_test_split(temp_tiles, test_size=0.50, random_state=42)
    print(f"Tiles — Train: {len(train_tiles)} | Val: {len(val_tiles)} | Test: {len(test_tiles)}")

    # ── Feature extraction (with raw-list caching) ───────────────────────────
    if CACHE_FILE.exists():
        print("\n  Loading raw features from cache …")
        with open(CACHE_FILE, "rb") as f:
            cache = pickle.load(f)
        t_pos, t_neg   = cache["train"]
        v_pos, v_neg   = cache["val"]
        te_pos, te_neg = cache["test"]
    else:
        with rasterio.open(SAR_MOSAIC) as sar_src:
            t_pos,  t_neg  = process_tile_set(train_tiles, sar_src, "Extracting Train")
            v_pos,  v_neg  = process_tile_set(val_tiles,   sar_src, "Extracting Val  ")
            te_pos, te_neg = process_tile_set(test_tiles,  sar_src, "Extracting Test ")

        with open(CACHE_FILE, "wb") as f:
            pickle.dump({"train": (t_pos, t_neg),
                         "val":   (v_pos, v_neg),
                         "test":  (te_pos, te_neg)}, f)
        print(f"\n  Cached raw features → {CACHE_FILE}")

    # ── Diagnostics ──────────────────────────────────────────────────────────
    pos_arr, neg_arr = np.array(t_pos), np.array(t_neg)
    if len(pos_arr) > 0 and len(neg_arr) > 0:
        print(f"\n  Feature Means [D, S, W, C]")
        print(f"    Positive class : {pos_arr.mean(axis=0).round(3)}")
        print(f"    Negative class : {neg_arr.mean(axis=0).round(3)}")
        print(f"  Raw counts — Train pos: {len(t_pos):,} | neg: {len(t_neg):,}")
    else:
        print("\n  WARNING: One or both classes are empty after extraction.")
        print("  Check tile paths, SAR mosaic CRS, and labeling thresholds.")
        return

    # ── Balance & scale ──────────────────────────────────────────────────────
    X_train, y_train = balance_dataset(t_pos,  t_neg)
    X_val,   y_val   = balance_dataset(v_pos,  v_neg)
    X_test,  y_test  = balance_dataset(te_pos, te_neg)

    print(f"\n  Balanced Train : {len(y_train):,} "
          f"(pos {int(y_train.sum()):,} | neg {int((y_train==0).sum()):,})")
    print(f"  Balanced Val   : {len(y_val):,}")
    print(f"  Balanced Test  : {len(y_test):,}")

    if len(y_train) == 0 or len(y_val) == 0 or len(y_test) == 0:
        print("\n  ERROR: Empty dataset after balancing. Aborting.")
        return

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s   = scaler.transform(X_val)
    X_test_s  = scaler.transform(X_test)

    # ── Train ─────────────────────────────────────────────────────────────────
    clf = LogisticRegression(solver="lbfgs", max_iter=1000)
    clf.fit(X_train_s, y_train)

    # ── Tune threshold on Val ─────────────────────────────────────────────────
    probs_val = clf.predict_proba(X_val_s)[:, 1]
    prec, rec, thresholds = precision_recall_curve(y_val, probs_val)
    f1_curve  = 2 * prec * rec / (prec + rec + 1e-9)
    best_idx  = int(np.argmax(f1_curve))
    best_thresh = float(thresholds[best_idx]) if best_idx < len(thresholds) else 0.50

    # ── Evaluate on held-out Test ─────────────────────────────────────────────
    probs_test = clf.predict_proba(X_test_s)[:, 1]
    test_preds = (probs_test >= best_thresh).astype(int)
    final_f1   = f1_score(y_test, test_preds)

    w_D, w_S, w_W, w_C = clf.coef_[0]
    b = float(clf.intercept_[0])

    print("\n" + "=" * 65)
    print("  LEARNED WCS FORMULA (standardised features):")
    print(f"  Logit = {w_D:+.3f}·D  {w_S:+.3f}·S  {w_W:+.3f}·W  {w_C:+.3f}·C  {b:+.3f}")
    print(f"  Val-optimal threshold : {best_thresh:.3f}")
    print(f"  Held-out Test F1      : {final_f1:.3f}")
    print("=" * 65)

    # ── Save ──────────────────────────────────────────────────────────────────
    out_model = Path(BASE) / "checkpoints_phase5" / "wcs_model_v4.pkl"
    out_model.parent.mkdir(parents=True, exist_ok=True)
    with open(out_model, "wb") as f:
        pickle.dump({
            "model":     clf,
            "scaler":    scaler,
            "weights":   {"w_D": w_D, "w_S": w_S, "w_W": w_W, "w_C": w_C, "b": b},
            "threshold": best_thresh,
            "version":   "v4-skeleton-connectivity",
        }, f)
    print(f"\n  Model saved → {out_model}")


