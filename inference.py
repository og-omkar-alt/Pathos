"""
SETU Project — Inference v4

FIXES vs v3:
  BUG: 221% road coverage. Root cause: prob tensor not guaranteed 2D before
       stitch accumulation. If model output shape is (1,512,512) instead of
       (512,512), broadcasting adds values incorrectly into canvas rows.
       Fix: prob = prob.reshape(tile_size, tile_size) — always forces 2D.

  Also: default threshold raised from 0.5 to 0.75.
       At epoch 23 precision is still low (~0.15-0.20), so the model assigns
       high probability to non-road pixels. 0.75 cuts most false positives
       while retaining genuine high-confidence road predictions.
       A diagnostic sweep across thresholds is printed after stitching.
"""

import os
import numpy as np
import torch
import rasterio
from pathlib import Path
from tqdm import tqdm
import albumentations as A
from albumentations.pytorch import ToTensorV2

from model import SEGFormerRoadExtractor

# ============================================================
# CONFIGURATION
# ============================================================
BASE     = r"C:\Users\omkar\OneDrive\Desktop\sih"
PROC_DIR = rf"{BASE}\ahmedabad_processed"
CKPT_DIR = rf"{BASE}\checkpoints_v5"

CONFIG = {
    "sentinel2_tif" : rf"{PROC_DIR}\ahmedabad_S2_RGB.tif",
    "sentinel1_tif" : rf"{PROC_DIR}\ahmedabad_S1_VV_VH.tif",
    "nisar_tif"     : rf"{PROC_DIR}\ahmedabad_NISAR_HH_HV.tif",
    "checkpoint"    : rf"{CKPT_DIR}\best_model.pth",
    "output_dir"    : rf"{BASE}\ahmedabad_outputs",
    "tile_size"     : 512,
    "overlap"       : 64,
    "use_sar"       : True,
    "sar_source"    : "sentinel1",
    "threshold"     : 0.30,   # raised from 0.5 — model over-predicts at epoch 23
    "device"        : "cuda" if torch.cuda.is_available() else "cpu",
}

OPT_TRANSFORM = A.Compose([
    A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ToTensorV2(),
])


# ============================================================
# DATA LOADING
# ============================================================
def load_optical(tif_path):
    print(f"Loading optical: {tif_path}")
    with rasterio.open(tif_path) as src:
        img     = src.read([1, 2, 3]).astype(np.float32)
        profile = src.profile.copy()
        H, W    = src.height, src.width
    img = np.clip(img, 0, 255).astype(np.uint8)
    img = np.transpose(img, (1, 2, 0))
    print(f"  Shape: {img.shape}")
    return img, profile, H, W


def load_sar(tif_path):
    print(f"Loading SAR: {tif_path}")
    with rasterio.open(tif_path) as src:
        data = src.read().astype(np.float32)
    img = np.transpose(data, (1, 2, 0))
    print(f"  Shape: {img.shape}  range [{data.min():.3f}, {data.max():.3f}]")
    return img


# ============================================================
# TILING
# ============================================================
def extract_tiles(image_hw_c, tile_size, overlap):
    H, W   = image_hw_c.shape[:2]
    stride = tile_size - overlap
    rows   = list(range(0, max(H - tile_size, 0) + 1, stride))
    cols   = list(range(0, max(W - tile_size, 0) + 1, stride))
    if not rows or rows[-1] + tile_size < H:
        rows.append(max(0, H - tile_size))
    if not cols or cols[-1] + tile_size < W:
        cols.append(max(0, W - tile_size))
    rows = sorted(set(rows))
    cols = sorted(set(cols))

    tiles = []
    for r in rows:
        for c in cols:
            r_end = min(r + tile_size, H)
            c_end = min(c + tile_size, W)
            tile  = image_hw_c[r:r_end, c:c_end]
            if tile.shape[0] < tile_size or tile.shape[1] < tile_size:
                pad_h = tile_size - tile.shape[0]
                pad_w = tile_size - tile.shape[1]
                tile  = np.pad(tile, ((0, pad_h), (0, pad_w), (0, 0)),
                               mode='reflect')
            tiles.append((tile, r, c))
    return tiles


# ============================================================
# STITCH
# ============================================================
def stitch(predictions, H, W, tile_size):
    canvas = np.zeros((H, W), dtype=np.float64)   # float64 for accumulation precision
    count  = np.zeros((H, W), dtype=np.float32)

    for prob, r, c in predictions:
        # FIX: force exactly 2D before any accumulation
        # If model returns (1,512,512), squeeze alone may not work correctly
        # when batch dim is present. reshape is explicit and safe.
        prob = np.array(prob).reshape(tile_size, tile_size)

        h_end     = min(r + tile_size, H)
        w_end     = min(c + tile_size, W)
        prob_crop = prob[:h_end - r, :w_end - c]

        canvas[r:h_end, c:w_end] += prob_crop
        count[r:h_end, c:w_end]  += 1.0

    result = (canvas / np.maximum(count, 1.0)).astype(np.float32)

    # Sanity check — must be in [0, 1]
    if result.max() > 1.0 or result.min() < 0.0:
        print(f"  WARNING: prob range [{result.min():.4f}, {result.max():.4f}] "
              f"— clamping to [0,1]")
        result = np.clip(result, 0.0, 1.0)

    return result


def threshold_sweep(full_prob):
    """Print road coverage % at multiple thresholds so you can pick the right one."""
    print("\n  Threshold sweep (pick threshold where coverage looks realistic):")
    print("  Ahmedabad road network covers roughly 2-8% of urban tile area.")
    for t in [0.30, 0.40, 0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90]:
        pct = 100.0 * (full_prob > t).sum() / full_prob.size
        bar = "#" * int(pct / 0.5)
        flag = " <-- reasonable" if 1.0 <= pct <= 10.0 else ""
        print(f"    t={t:.2f}  {pct:6.2f}%  {bar}{flag}")


# ============================================================
# INFERENCE
# ============================================================
def run_inference():
    print("=" * 60)
    print(f"  SETU Inference  Phase {'5 (SAR+optical)' if CONFIG['use_sar'] else '3 (optical)'}")
    print("=" * 60)
    print(f"  Device    : {CONFIG['device']}")
    print(f"  Threshold : {CONFIG['threshold']}")

    os.makedirs(CONFIG["output_dir"], exist_ok=True)

    if not Path(CONFIG["sentinel2_tif"]).exists():
        print(f"ERROR: {CONFIG['sentinel2_tif']} not found. Run preprocess_ahmedabad.py first.")
        return

    sar_tif = None
    if CONFIG["use_sar"]:
        key     = "nisar_tif" if CONFIG["sar_source"] == "nisar" else "sentinel1_tif"
        sar_tif = CONFIG[key]
        if not Path(sar_tif).exists():
            print(f"ERROR: {sar_tif} not found. Run preprocess_ahmedabad.py first.")
            return

    if not Path(CONFIG["checkpoint"]).exists():
        print(f"ERROR: checkpoint not found: {CONFIG['checkpoint']}")
        return

    model = SEGFormerRoadExtractor(num_classes=1, use_sar=CONFIG["use_sar"])
    ckpt  = torch.load(CONFIG["checkpoint"],
                       map_location=CONFIG["device"], weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model = model.to(CONFIG["device"])
    model.eval()
    print(f"  Checkpoint: epoch {ckpt.get('epoch','?')}  "
          f"val IoU {ckpt.get('val_iou', 0):.4f}  "
          f"val P {ckpt.get('val_prec', 0):.3f}  "
          f"val R {ckpt.get('val_rec', 0):.3f}")

    optical, profile, H, W = load_optical(CONFIG["sentinel2_tif"])
    sar_img = load_sar(sar_tif) if sar_tif else None

    tile_size = CONFIG["tile_size"]
    overlap   = CONFIG["overlap"]
    opt_tiles = extract_tiles(optical, tile_size, overlap)
    sar_tiles = extract_tiles(sar_img, tile_size, overlap) if sar_img is not None else None
    print(f"\n  Tiles: {len(opt_tiles)}  size={tile_size}  overlap={overlap}")

    predictions = []
    for idx, (opt_tile, r, c) in enumerate(tqdm(opt_tiles, desc="Inference")):

        aug        = OPT_TRANSFORM(image=opt_tile)
        opt_tensor = aug["image"].unsqueeze(0).to(CONFIG["device"])

        sar_tensor = None
        if sar_tiles is not None:
            sar_tile, _, _ = sar_tiles[idx]
            sar_tensor = (
                torch.from_numpy(sar_tile)
                     .permute(2, 0, 1)
                     .float()
                     .unsqueeze(0)
                     .to(CONFIG["device"])
            )
            sar_tensor = (sar_tensor - 0.5) / 0.5

        with torch.no_grad():
            logits = model(opt_tensor, sar_tensor)
            # FIX: explicit 2D squeeze — handles (1,1,H,W), (1,H,W), (H,W)
            prob = torch.sigmoid(logits).squeeze().cpu().numpy()

        predictions.append((prob, r, c))

    print("\nStitching...")
    full_prob = stitch(predictions, H, W, tile_size)

    # Diagnostic sweep before committing to one threshold
    threshold_sweep(full_prob)

    threshold = CONFIG["threshold"]
    road_mask = (full_prob > threshold).astype(np.uint8)
    pct       = 100.0 * road_mask.sum() / road_mask.size
    print(f"\n  Road coverage at t={threshold}: {pct:.2f}%")

    # Save probability map (always useful for tuning threshold later)
    prob_profile = profile.copy()
    prob_profile.update(count=1, dtype=rasterio.float32, driver="GTiff")
    prob_path = Path(CONFIG["output_dir"]) / "ahmedabad_road_probability.tif"
    with rasterio.open(str(prob_path), "w", **prob_profile) as dst:
        dst.write(full_prob, 1)

    # Save binary mask at chosen threshold
    mask_profile = profile.copy()
    mask_profile.update(count=1, dtype=rasterio.uint8, driver="GTiff")
    mask_path = Path(CONFIG["output_dir"]) / "ahmedabad_road_mask.tif"
    with rasterio.open(str(mask_path), "w", **mask_profile) as dst:
        dst.write(road_mask, 1)

    print(f"\n  Probability map : {prob_path}")
    print(f"  Binary mask     : {mask_path}")
    print("\n  TIP: Load ahmedabad_road_probability.tif in QGIS and use")
    print("  Raster -> Reclassify by table to try different thresholds visually.")
    print("\nNext: python graph_builder.py")


if __name__ == "__main__":
    run_inference()