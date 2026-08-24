"""
SETU Project — Phase 5 Step 3
Dual-modal inference: Sentinel-2 optical + Sentinel-1 SAR on Ahmedabad

Input:
  - ahmedabad_S2_RGB.tif       (optical — from preprocess_ahmedabad.py)
  - ahmedabad_S1_VV_VH.tif     (SAR — from preprocess_ahmedabad.py)
  - best_model_phase5.pth      (trained dual-modal model)

Output:
  - ahmedabad_road_mask_phase5.tif
  - ahmedabad_road_probability_phase5.tif
"""

import os
import numpy as np
import torch
import rasterio
from rasterio.warp import reproject, Resampling
from pathlib import Path
from tqdm import tqdm

from model import SEGFormerRoadExtractor


# ============================================================
# CONFIGURATION
# ============================================================
BASE = r"C:\Users\omkar\OneDrive\Desktop\sih"

CONFIG = {
    "optical_path"  : rf"{BASE}\ahmedabad_processed\ahmedabad_S2_RGB.tif",
    "sar_path"      : rf"{BASE}\ahmedabad_processed\ahmedabad_S1_VV_VH.tif",
    "checkpoint"    : rf"{BASE}\checkpoints_phase5\best_model_phase5.pth",
    "output_dir"    : rf"{BASE}\ahmedabad_outputs",
    "tile_size"     : 512,
    "overlap"       : 64,
    "threshold"     : 0.35,
    "device"        : "cuda" if torch.cuda.is_available() else "cpu",
}


# ============================================================
# LOAD AND ALIGN DATA
# ============================================================
def load_optical(path):
    print(f"\nLoading optical: {Path(path).name}")
    with rasterio.open(path) as src:
        img       = src.read([1, 2, 3]).astype(np.float32)
        profile   = src.profile.copy()
        transform = src.transform
        crs       = src.crs
        H, W      = src.height, src.width

    img = np.transpose(img, (1, 2, 0))
    p2  = np.percentile(img, 2, axis=(0, 1))
    p98 = np.percentile(img, 98, axis=(0, 1))
    img = np.clip(img, p2, p98)
    img = (img - p2) / (p98 - p2 + 1e-6) * 255.0
    print(f"  Shape: {img.shape}  Range: {img.min():.1f}-{img.max():.1f}")
    return img.astype(np.uint8), profile, transform, crs, H, W


def load_and_align_sar(sar_path, opt_transform, opt_crs, H, W):
    print(f"\nLoading + aligning SAR: {Path(sar_path).name}")

    with rasterio.open(sar_path) as src:
        print(f"  SAR original: {src.height}x{src.width}  CRS: {src.crs}")
        sar_arr = np.zeros((2, H, W), dtype=np.float32)

        # Force reprojection to match the optical 10980x10980 grid exactly
        for b in range(2):
            reproject(
                source        = rasterio.band(src, b + 1),
                destination   = sar_arr[b],
                src_crs       = src.crs,
                dst_crs       = opt_crs,
                dst_transform = opt_transform,
                dst_width     = W,
                dst_height    = H,
                resampling    = Resampling.bilinear,
            )

    sar_img = np.transpose(sar_arr, (1, 2, 0))  # (H, W, 2)
    valid   = (sar_img != 0).mean()
    print(f"  SAR aligned: {sar_img.shape}  Valid pixels: {valid*100:.1f}%")

    return sar_img


# ============================================================
# TILING
# ============================================================
def extract_tiles(opt_img, sar_img, tile_size=512, overlap=64):
    H, W  = opt_img.shape[:2]
    stride = tile_size - overlap
    tiles  = []

    rows = list(range(0, H - tile_size + 1, stride))
    cols = list(range(0, W - tile_size + 1, stride))
    if not rows or rows[-1] + tile_size < H:
        rows.append(max(0, H - tile_size))
    if not cols or cols[-1] + tile_size < W:
        cols.append(max(0, W - tile_size))

    for r in rows:
        for c in cols:
            opt_tile = opt_img[r:r+tile_size, c:c+tile_size]
            sar_tile = sar_img[r:r+tile_size, c:c+tile_size]
            tiles.append((opt_tile, sar_tile, r, c))

    return tiles, H, W


def stitch(predictions, H, W, tile_size=512):
    canvas = np.zeros((H, W), dtype=np.float32)
    counts = np.zeros((H, W), dtype=np.float32)

    for prob, r, c in predictions:
        h_end = min(r + tile_size, H)
        w_end = min(c + tile_size, W)
        h_t   = h_end - r
        w_t   = w_end - c
        canvas[r:h_end, c:w_end] += prob[:h_t, :w_t]
        counts[r:h_end, c:w_end] += 1.0

    counts = np.maximum(counts, 1.0)
    return canvas / counts


# ============================================================
# PREPROCESSING FOR MODEL
# ============================================================
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def preprocess_optical(tile):
    img = tile.astype(np.float32) / 255.0
    img = (img - IMAGENET_MEAN) / IMAGENET_STD
    return torch.from_numpy(img.transpose(2, 0, 1)).float()


def preprocess_sar(tile):
    sar = tile.astype(np.float32)
    sar = np.transpose(sar, (2, 0, 1))  # (2, H, W)
    t   = torch.from_numpy(sar)
    t   = (t - 0.5) / 0.5
    return t


# ============================================================
# MAIN INFERENCE
# ============================================================
def run_inference():
    print("=" * 60)
    print("  SETU Phase 5 — Dual-Modal Inference")
    print("  Sentinel-2 Optical + Sentinel-1 SAR")
    print("=" * 60)
    print(f"  Device : {CONFIG['device']}")

    os.makedirs(CONFIG["output_dir"], exist_ok=True)

    # Load data
    opt_img, profile, transform, crs, H, W = load_optical(CONFIG["optical_path"])
    sar_img = load_and_align_sar(
        CONFIG["sar_path"], transform, crs, H, W
    )

    # Load model
    print(f"\nLoading Phase 5 model: {Path(CONFIG['checkpoint']).name}")
    if not Path(CONFIG["checkpoint"]).exists():
        print(f"  ERROR: Checkpoint not found — run train_phase5.py first")
        return

    model = SEGFormerRoadExtractor(num_classes=1, use_sar=True)
    ckpt  = torch.load(CONFIG["checkpoint"],
                       map_location=CONFIG["device"], weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model = model.to(CONFIG["device"])
    model.eval()
    print(f"  Loaded epoch {ckpt['epoch']}  Val IoU: {ckpt['val_iou']:.4f}")

    # Tile
    print(f"\nTiling: size={CONFIG['tile_size']}  overlap={CONFIG['overlap']}")
    tiles, H, W = extract_tiles(
        opt_img, sar_img,
        CONFIG["tile_size"], CONFIG["overlap"]
    )
    print(f"  Total tiles: {len(tiles)}")

    # Inference
    print("\nRunning dual-modal inference...")
    predictions = []
    batch_size  = 2

    with torch.no_grad():
        for i in tqdm(range(0, len(tiles), batch_size)):
            batch      = tiles[i:i + batch_size]
            opt_batch  = torch.stack([preprocess_optical(t[0]) for t in batch])
            sar_batch  = torch.stack([preprocess_sar(t[1])     for t in batch])

            opt_batch  = opt_batch.to(CONFIG["device"])
            sar_batch  = sar_batch.to(CONFIG["device"])

            logits = model(opt_batch, sar_batch)
            probs  = torch.sigmoid(logits).squeeze(1).cpu().numpy()

            for j, (_, _, r, c) in enumerate(batch):
                predictions.append((probs[j], r, c))

    # Stitch
    print("\nStitching predictions...")
    prob_map  = stitch(predictions, H, W, CONFIG["tile_size"])
    road_mask = (prob_map > CONFIG["threshold"]).astype(np.uint8)

    # Coverage stats
    print("\n  Threshold sweep:")
    for t in [0.25, 0.30, 0.35, 0.40, 0.50]:
        pct = 100 * (prob_map > t).sum() / prob_map.size
        bar = "#" * int(pct * 2)
        print(f"    t={t:.2f}  {pct:.2f}%  {bar}")

    # Save
    out_prob = Path(CONFIG["output_dir"]) / "ahmedabad_road_probability_phase5.tif"
    out_mask = Path(CONFIG["output_dir"]) / "ahmedabad_road_mask_phase5.tif"

    prof_float = profile.copy()
    prof_float.update(count=1, dtype=rasterio.float32)
    with rasterio.open(str(out_prob), "w", **prof_float) as dst:
        dst.write(prob_map.astype(np.float32), 1)

    prof_mask = profile.copy()
    prof_mask.update(count=1, dtype=rasterio.uint8)
    with rasterio.open(str(out_mask), "w", **prof_mask) as dst:
        dst.write(road_mask, 1)

    road_pct = 100 * road_mask.sum() / road_mask.size
    print(f"\n  Road coverage at t={CONFIG['threshold']}: {road_pct:.2f}%")
    print(f"  Probability map : {out_prob}")
    print(f"  Binary mask     : {out_mask}")

    print("\n  Compare in QGIS:")
    print("  - ahmedabad_road_mask.tif        (Phase 3 optical only)")
    print("  - ahmedabad_road_mask_phase5.tif (Phase 5 SAR + optical)")
    print("  Phase 5 should show more roads in occluded areas")
    print("\n  Next: python graph_builder.py --mask ahmedabad_road_mask_phase5.tif")


if __name__ == "__main__":
    run_inference()
