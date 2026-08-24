"""
SETU Project — Phase 3 Step 3
Training Script v5 — Metric Accumulation & Topological Graphing

KEY FIXES:
  1. Accumulated global dataset metrics (no more batch-wise averaging).
  2. True graph-based breaks/km using 2D convolution for endpoint detection.
  3. Dynamic GSD pixel resolution tracking via rasterio.
  4. Full validation set evaluation.
"""

import os
import json
import torch
import numpy as np
import rasterio
from pathlib import Path
from torch.optim import AdamW
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.amp import autocast, GradScaler
from tqdm import tqdm
from scipy.ndimage import convolve

from model import SEGFormerRoadExtractor
from road_dataset import get_dataloaders


# ============================================================
# CONFIGURATION
# ============================================================
BASE = r"C:\Users\omkar\OneDrive\Desktop\sih"

CONFIG = {
    "prepared_dir"   : rf"{BASE}\spacenet_prepared",
    "cities"         : ["Mumbai", "Khartoum"],
    "checkpoint_dir" : rf"{BASE}\checkpoints_v5",
    "img_size"       : 512,
    "batch_size"     : 4,
    "num_epochs"     : 80,
    "lr_encoder"     : 5e-6,
    "lr_decoder"     : 5e-5,
    "num_workers"    : 0,
    "early_stop"     : 15,
    "save_every"     : 5,
    "pos_weight"     : 2.0,
    "tversky_alpha"  : 0.3,
    "tversky_beta"   : 0.7,
    "iou_threshold"  : 0.40,
    "device"         : "cuda" if torch.cuda.is_available() else "cpu",
}


# ============================================================
# HELPER: DYNAMIC RESOLUTION
# ============================================================
# ============================================================
# HELPER: DYNAMIC RESOLUTION
# ============================================================
# ============================================================
# HELPER: DYNAMIC RESOLUTION
# ============================================================
def get_pixel_size_m(prepared_dir, cities):
    """
    Reads actual pixel size from a sample mask TIF using rasterio.
    Handles both UTM (meters) and Geographic (degrees) CRS.
    """
    try:
        import rasterio
        from pathlib import Path
        for city in cities:
            mask_dir = Path(prepared_dir) / city / "masks"
            tifs = list(mask_dir.glob("*.tif"))
            if tifs:
                with rasterio.open(tifs[0]) as src:
                    pixel_m = abs(src.transform.a)
                    # If CRS is in degrees (EPSG:4326), approximate to meters
                    if pixel_m < 0.001:
                        pixel_m = pixel_m * 111_000
                    print(f"  [GSD] Dynamically read Pixel size: {pixel_m:.4f}m (from {tifs[0].name})")
                    return pixel_m
    except Exception as e:
        print(f"  [GSD] Error reading pixel size ({e}). Defaulting to 0.5m")
    
    return 0.5


# ============================================================
# LOSS
# ============================================================
class TverskyLoss(torch.nn.Module):
    def __init__(self, alpha=0.3, beta=0.7, smooth=1.0):
        super().__init__()
        self.alpha  = alpha
        self.beta   = beta
        self.smooth = smooth

    def forward(self, pred, target):
        pred = torch.sigmoid(pred)
        p    = pred.view(-1)
        t    = target.view(-1)
        tp   = (p * t).sum()
        fp   = (p * (1 - t)).sum()
        fn   = ((1 - p) * t).sum()
        return 1 - (tp + self.smooth) / (tp + self.alpha * fp + self.beta * fn + self.smooth)


class RoadLoss(torch.nn.Module):
    def __init__(self, pos_weight=3.0, alpha=0.3, beta=0.7):
        super().__init__()
        self.tversky = TverskyLoss(alpha=alpha, beta=beta)
        self.pos_weight = pos_weight

    def forward(self, pred, target):
        pw  = torch.tensor([self.pos_weight], device=pred.device)
        bce = torch.nn.functional.binary_cross_entropy_with_logits(pred, target, pos_weight=pw)
        return 0.6 * self.tversky(pred, target) + 0.4 * bce


# ============================================================
# METRICS (RAW ACCUMULATORS)
# ============================================================
def get_batch_stats(pred, target, threshold=0.40):
    """Returns raw pixel counts to accumulate across the entire dataset."""
    pred_bin = (torch.sigmoid(pred) > threshold).float()
    
    tp = (pred_bin * target).sum().item()
    fp = (pred_bin * (1 - target)).sum().item()
    fn = ((1 - pred_bin) * target).sum().item()
    
    intersection = tp
    union = pred_bin.sum().item() + target.sum().item() - intersection
    
    return intersection, union, tp, fp, fn


def compute_breaks_per_km(pred_np, pixel_size_m, threshold=0.40):
    """
    True topological graph break detection.
    Uses a 2D convolution to find endpoints (nodes with exactly 1 connection)
    on the skeletonized road network.
    """
    try:
        from skimage.morphology import skeletonize
        binary = (pred_np > threshold).astype(np.uint8)
        if binary.sum() == 0:
            return 0.0

        skel = skeletonize(binary).astype(np.uint8)
        
        # 3x3 kernel to count neighboring pixels
        kernel = np.array([[1, 1, 1],
                           [1, 0, 1],
                           [1, 1, 1]])
                           
        # Convolve skeleton with kernel to find degrees of each node
        neighbors = convolve(skel, kernel, mode='constant', cval=0)
        
        # Endpoints are pixels that are part of the skeleton AND have exactly 1 neighbor
        endpoints = (skel == 1) & (neighbors == 1)
        num_endpoints = endpoints.sum()
        
        # 2 endpoints generally imply 1 broken segment line
        breaks = num_endpoints / 2.0
        
        road_km = (skel.sum() * pixel_size_m) / 1000.0
        return breaks / max(road_km, 0.001)
    except Exception:
        return 0.0


# ============================================================
# TRAIN
# ============================================================
def train_one_epoch(model, loader, optimizer, criterion, scaler, device, epoch):
    model.train()
    total_loss = 0.0
    
    # Global accumulators
    g_inter = g_union = g_tp = g_fp = g_fn = 0.0
    use_amp = (device == "cuda")

    pbar = tqdm(loader, desc=f"Epoch {epoch}")
    for images, masks in pbar:
        images = images.to(device, non_blocking=True)
        masks  = masks.to(device,  non_blocking=True)
        optimizer.zero_grad()

        if use_amp:
            with autocast("cuda"):
                logits = model(images)
                loss   = criterion(logits, masks)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
        else:
            logits = model(images)
            loss   = criterion(logits, masks)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

        with torch.no_grad():
            i, u, tp, fp, fn = get_batch_stats(logits, masks, CONFIG["iou_threshold"])
            g_inter += i
            g_union += u
            g_tp += tp
            g_fp += fp
            g_fn += fn

        total_loss += loss.item()

        # Real-time batch approximations for the progress bar
        batch_iou = i / (u + 1e-6)
        batch_p   = tp / (tp + fp + 1e-6)
        pbar.set_postfix({"loss": f"{loss.item():.4f}", "iou_batch": f"{batch_iou:.3f}"})

    # Final Dataset-Level Metrics
    n = len(loader)
    final_iou  = g_inter / (g_union + 1e-6)
    final_prec = g_tp / (g_tp + g_fp + 1e-6)
    final_rec  = g_tp / (g_tp + g_fn + 1e-6)
    
    return total_loss / n, final_iou, final_prec, final_rec


# ============================================================
# VALIDATE
# ============================================================
def validate(model, loader, criterion, device, pixel_size_m):
    model.eval()
    total_loss = 0.0
    
    # Global accumulators
    g_inter = g_union = g_tp = g_fp = g_fn = 0.0
    all_breaks = []
    use_amp = (device == "cuda")

    with torch.no_grad():
        for images, masks in tqdm(loader, desc="Val"):
            images = images.to(device, non_blocking=True)
            masks  = masks.to(device,  non_blocking=True)

            if use_amp:
                with autocast("cuda"):
                    logits = model(images)
                    loss   = criterion(logits, masks)
            else:
                logits = model(images)
                loss   = criterion(logits, masks)

            total_loss += loss.item()
            
            i, u, tp, fp, fn = get_batch_stats(logits, masks, CONFIG["iou_threshold"])
            g_inter += i
            g_union += u
            g_tp += tp
            g_fp += fp
            g_fn += fn

            # Evaluate endpoint breaks across validation samples
            for b in range(logits.shape[0]):
                pred_np = torch.sigmoid(logits[b]).squeeze().cpu().numpy()
                all_breaks.append(compute_breaks_per_km(pred_np, pixel_size_m, CONFIG["iou_threshold"]))

    n = len(loader)
    final_iou  = g_inter / (g_union + 1e-6)
    # Corrected Dice formula: 2*TP / (2*TP + FP + FN)
    final_dice = (2.0 * g_inter) / (2.0 * g_tp + g_fp + g_fn + 1e-6)
    final_prec = g_tp / (g_tp + g_fp + 1e-6)
    final_rec  = g_tp / (g_tp + g_fn + 1e-6)
    
    return (total_loss / n, final_iou, final_dice, final_prec, final_rec, float(np.mean(all_breaks) if all_breaks else 0))

# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("  SETU — Training v5 (Global Metrics & Topology)")
    print("=" * 60)
    
    pixel_size_m = get_pixel_size_m(CONFIG["prepared_dir"], CONFIG["cities"])
    
    print(f"  Device       : {CONFIG['device']}")
    print(f"  LR encoder   : {CONFIG['lr_encoder']}")
    print(f"  LR decoder   : {CONFIG['lr_decoder']}")
    print("=" * 60)

    os.makedirs(CONFIG["checkpoint_dir"], exist_ok=True)

    train_loader, val_loader, test_loader = get_dataloaders(
        CONFIG["prepared_dir"], CONFIG["cities"],
        batch_size=CONFIG["batch_size"],
        num_workers=CONFIG["num_workers"],
        img_size=CONFIG["img_size"],
    )

    # NOTE: Phase 3 explicitly configures Optical-Only.
    # Phase 5 will toggle use_sar=True once NISAR dataloaders are implemented.
    model = SEGFormerRoadExtractor(num_classes=1, use_sar=False)
    model = model.to(CONFIG["device"])

    optimizer = AdamW([
        {"params": model.optical_encoder.parameters(), "lr": CONFIG["lr_encoder"]},
        {
            "params": list(model.optical_projections.parameters()) +
                      list(model.fusion.parameters()) +
                      list(model.head.parameters()),
            "lr": CONFIG["lr_decoder"]
        },
    ], weight_decay=0.01)

    # Removed deprecated verbose=True
    scheduler = ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5,
        patience=6, min_lr=1e-7
    )

    criterion = RoadLoss(pos_weight=CONFIG["pos_weight"], alpha=CONFIG["tversky_alpha"], beta=CONFIG["tversky_beta"])
    scaler = GradScaler("cuda") if CONFIG["device"] == "cuda" else None

    best_iou = patience = 0
    history  = []

    for epoch in range(1, CONFIG["num_epochs"] + 1):

        tr_loss, tr_iou, tr_prec, tr_rec = train_one_epoch(
            model, train_loader, optimizer, criterion, scaler, CONFIG["device"], epoch
        )
        vl_loss, vl_iou, vl_dice, vl_prec, vl_rec, vl_breaks = validate(
            model, val_loader, criterion, CONFIG["device"], pixel_size_m
        )

        scheduler.step(vl_iou)
        cur_lr_enc = optimizer.param_groups[0]["lr"]
        cur_lr_dec = optimizer.param_groups[1]["lr"]

        print(f"\nEpoch {epoch}/{CONFIG['num_epochs']}")
        print(f"  Train — loss: {tr_loss:.4f}  Dataset IoU: {tr_iou:.4f}  P: {tr_prec:.3f}  R: {tr_rec:.3f}")
        print(f"  Val   — loss: {vl_loss:.4f}  Dataset IoU: {vl_iou:.4f}  "
              f"Dice: {vl_dice:.4f}  P: {vl_prec:.3f}  R: {vl_rec:.3f}  Breaks/km: {vl_breaks:.1f}")

        history.append({
            "epoch"      : epoch,
            "train_loss" : round(tr_loss, 5),
            "train_iou"  : round(tr_iou, 5),
            "train_prec" : round(tr_prec, 4),
            "train_rec"  : round(tr_rec, 4),
            "val_loss"   : round(vl_loss, 5),
            "val_iou"    : round(vl_iou, 5),
            "val_dice"   : round(vl_dice, 5),
            "val_prec"   : round(vl_prec, 4),
            "val_rec"    : round(vl_rec, 4),
            "val_breaks" : round(vl_breaks, 2),
        })
        with open(rf"{CONFIG['checkpoint_dir']}\history.json", "w") as f:
            json.dump(history, f, indent=2)

        if vl_iou > best_iou:
            best_iou = vl_iou
            patience = 0
            torch.save({
                "epoch"            : epoch,
                "model_state_dict" : model.state_dict(),
                "val_iou"          : vl_iou,
            }, rf"{CONFIG['checkpoint_dir']}\best_model.pth")
            print(f"  ✓ Best saved — Dataset IoU: {vl_iou:.4f}")
        else:
            patience += 1
            if patience >= CONFIG["early_stop"]:
                print(f"\nEarly stopping at epoch {epoch}")
                break

    # Final test
    print("\n" + "=" * 60)
    print("Loading best Phase 3 model for final test...")
    ckpt = torch.load(rf"{CONFIG['checkpoint_dir']}\best_model.pth", map_location=CONFIG["device"], weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])

    ts_loss, ts_iou, ts_dice, ts_prec, ts_rec, ts_breaks = validate(
        model, test_loader, criterion, CONFIG["device"], pixel_size_m
    )

    print("\nPHASE 3 (OPTICAL BASELINE) TEST RESULTS:")
    print(f"  Dataset IoU: {ts_iou:.4f}   (Note: SETU Multi-modal target is ~0.882 mIoU)")
    print(f"  Dice:        {ts_dice:.4f}")
    print(f"  Precision:   {ts_prec:.4f}")
    print(f"  Recall:      {ts_rec:.4f}")
    print(f"  Breaks/km:   {ts_breaks:.2f}")


if __name__ == "__main__":
    main()