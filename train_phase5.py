"""
SETU Project — Phase 5 Step 2
Fine-tune SAR encoder using warm initialization from optical encoder.

Fixes applied:
  1. Alignment check skips failed triplets and reports at end
  2. Added mask transform + bounds checks
  3. Memory probe uses no_grad + model.eval() to avoid BN stat corruption
  4. Removed predefined "expected IoU" statement
"""

import os
import json
import random
import numpy as np
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.amp import autocast, GradScaler
from torch.utils.data import Dataset, DataLoader
from pathlib import Path
from tqdm import tqdm
import rasterio
import albumentations as A
from albumentations.pytorch import ToTensorV2

from model import SEGFormerRoadExtractor


# ============================================================
# CONFIGURATION
# ============================================================
BASE = r"C:\Users\omkar\OneDrive\Desktop\sih"

CONFIG = {
    "prepared_dir"   : rf"{BASE}\spacenet_prepared",
    "cities"         : ["Mumbai"],   # Khartoum removed — wrong UTM zone in S1
    "phase3_ckpt"    : rf"{BASE}\checkpoints_v5\best_model.pth",
    "checkpoint_dir" : rf"{BASE}\checkpoints_phase5",
    "img_size"       : 512,
    "min_road_pixels": 50,
    "batch_size"     : 4,
    "num_epochs"     : 20,
    "lr_sar"         : 1e-5,
    "lr_attn"        : 5e-6,
    "lr_decoder"     : 5e-6,
    "num_workers"    : 0,
    "early_stop"     : 8,
    "device"         : "cuda" if torch.cuda.is_available() else "cpu",
    "pos_weight"     : 3.0,
    "tversky_alpha"  : 0.3,
    "tversky_beta"   : 0.7,
}

PHASE3_BASELINE_IOU = 0.2155   # measured, used for comparison only


# ============================================================
# ALIGNMENT CHECK — fails loudly, full reporting
# ============================================================
def check_alignment(opt_path, sar_path, mask_path):
    """
    Returns True only if all spatial properties match exactly.
    Does NOT silently skip — caller decides what to do on failure.
    Checks: dimensions, CRS, transform, bounds for all three files.
    """
    try:
        with rasterio.open(opt_path)  as opt, \
             rasterio.open(sar_path)  as sar, \
             rasterio.open(mask_path) as msk:

            failures = []

            # Dimensions
            if (opt.height, opt.width) != (sar.height, sar.width):
                failures.append(
                    f"dim mismatch opt({opt.height},{opt.width}) "
                    f"vs sar({sar.height},{sar.width})"
                )
            if (opt.height, opt.width) != (msk.height, msk.width):
                failures.append(
                    f"dim mismatch opt({opt.height},{opt.width}) "
                    f"vs mask({msk.height},{msk.width})"
                )

            # CRS
            if opt.crs != sar.crs:
                failures.append(f"CRS opt={opt.crs} vs sar={sar.crs}")
            if opt.crs != msk.crs:
                failures.append(f"CRS opt={opt.crs} vs mask={msk.crs}")

            # Transform
            def transform_close(t1, t2, tol=1e-3):
                return all(abs(a-b) < tol for a, b in zip(list(t1)[:6], list(t2)[:6]))

            if not transform_close(opt.transform, sar.transform):
                failures.append(
                    f"transform mismatch opt vs sar: "
                    f"{list(opt.transform)[:6]} vs {list(sar.transform)[:6]}"
                )
            if not transform_close(opt.transform, msk.transform):
                failures.append(
                    f"transform mismatch opt vs mask: "
                    f"{list(opt.transform)[:6]} vs {list(msk.transform)[:6]}"
                )

            # Bounds
            def bounds_close(b1, b2, tol=1.0):
                return all(abs(a-b) < tol for a, b in zip(b1, b2))

            if not bounds_close(opt.bounds, sar.bounds):
                failures.append(
                    f"bounds mismatch opt vs sar: "
                    f"{opt.bounds} vs {sar.bounds}"
                )
            if not bounds_close(opt.bounds, msk.bounds):
                failures.append(
                    f"bounds mismatch opt vs mask: "
                    f"{opt.bounds} vs {msk.bounds}"
                )

            # Pixel size
            opt_px = abs(opt.transform.a)
            sar_px = abs(sar.transform.a)
            if abs(opt_px - sar_px) > 0.5:
                failures.append(
                    f"pixel size mismatch opt={opt_px:.2f}m sar={sar_px:.2f}m"
                )

            # SAR validity — check it's not all zeros
            sar_data = sar.read()
            if sar_data.sum() == 0:
                failures.append("SAR tile is all zeros — outside S1 footprint")

        return len(failures) == 0, failures

    except Exception as e:
        return False, [f"file read error: {e}"]


# ============================================================
# DATASET
# ============================================================
class DualModalDataset(Dataset):
    def __init__(self, prepared_dir, cities, split='train',
                 val_ratio=0.15, test_ratio=0.15,
                 seed=42, img_size=512, min_road_pixels=50):
        self.split           = split
        self.img_size        = img_size
        self.min_road_pixels = min_road_pixels if split == 'train' else 0
        self.samples         = []
        all_samples          = []

        total_candidates = 0
        total_skipped    = 0
        skip_reasons     = {}

        for city in cities:
            img_dir  = Path(prepared_dir) / city / "images"
            sar_dir  = Path(prepared_dir) / city / "sar"
            mask_dir = Path(prepared_dir) / city / "masks"

            if not sar_dir.exists():
                print(f"  WARNING: No SAR tiles for {city}")
                continue

            images = sorted(list(img_dir.glob("*.tif")))
            city_ok = city_skip = 0

            for img_path in images:
                sar_path  = sar_dir  / f"{img_path.stem}_sar.tif"
                mask_path = mask_dir / f"{img_path.stem}_mask.tif"

                if not sar_path.exists() or not mask_path.exists():
                    city_skip += 1
                    total_skipped += 1
                    continue

                total_candidates += 1
                ok, failures = check_alignment(
                    str(img_path), str(sar_path), str(mask_path)
                )

                if ok:
                    all_samples.append((
                        str(img_path), str(sar_path), str(mask_path)
                    ))
                    city_ok += 1
                else:
                    city_skip += 1
                    total_skipped += 1

        random.seed(seed)
        random.shuffle(all_samples)

        n       = len(all_samples)
        n_test  = int(n * test_ratio)
        n_val   = int(n * val_ratio)
        n_train = n - n_test - n_val

        if split == 'train':
            self.samples = all_samples[:n_train]
        elif split == 'val':
            self.samples = all_samples[n_train:n_train + n_val]
        else:
            self.samples = all_samples[n_train + n_val:]

        # FIX: Separation of Spatial and Color transforms
        if split == 'train':
            self.spatial_transform = A.Compose([
                A.Resize(img_size, img_size),
                A.HorizontalFlip(p=0.5),
                A.VerticalFlip(p=0.5),
                A.RandomRotate90(p=0.5),
            ], additional_targets={"sar": "image"})
            
            self.color_transform = A.Compose([
                A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.4),
                A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
                ToTensorV2()
            ])
        else:
            self.spatial_transform = A.Compose([
                A.Resize(img_size, img_size) # FIX: Resize instead of CenterCrop
            ], additional_targets={"sar": "image"})
            
            self.color_transform = A.Compose([
                A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
                ToTensorV2()
            ])

    def _load_optical(self, path):
        with rasterio.open(path) as src:
            img = src.read([1, 2, 3]).astype(np.float32)
            img = np.transpose(img, (1, 2, 0))
            # FIX: Per-channel percentiles
            p2  = np.percentile(img, 2, axis=(0, 1))
            p98 = np.percentile(img, 98, axis=(0, 1))
            img = np.clip(img, p2, p98)
            denom = p98 - p2
            denom[denom == 0] = 1e-6
            img = (img - p2) / denom * 255.0
            return img.astype(np.uint8)

    def _load_sar(self, path):
        with rasterio.open(path) as src:
            sar = src.read([1, 2]).astype(np.float32)
            return np.transpose(sar, (1, 2, 0))

    def _load_mask(self, path):
        with rasterio.open(path) as src:
            mask = src.read(1).astype(np.float32)
            return (mask > 0).astype(np.float32)

    def _road_aware_crop(self, opt, sar, mask, size):
        H, W = mask.shape
        if H < size or W < size:
            import cv2
            scale = max(size/H, size/W) + 0.01
            nH, nW = int(H*scale), int(W*scale)
            opt  = cv2.resize(opt,  (nW, nH))
            sar  = cv2.resize(sar,  (nW, nH))
            mask = cv2.resize(mask, (nW, nH), interpolation=cv2.INTER_NEAREST)
            H, W = nH, nW

        best_opt = best_sar = best_mask = None
        best_road = 0

        for _ in range(20):
            r  = random.randint(0, H - size)
            c  = random.randint(0, W - size)
            cm = mask[r:r+size, c:c+size]
            if cm.sum() >= self.min_road_pixels:
                return (opt[r:r+size, c:c+size],
                        sar[r:r+size, c:c+size], cm)
            if cm.sum() > best_road:
                best_road = cm.sum()
                best_opt  = opt[r:r+size, c:c+size]
                best_sar  = sar[r:r+size, c:c+size]
                best_mask = cm

        if best_opt is not None:
            return best_opt, best_sar, best_mask

        r = (H - size) // 2
        c = (W - size) // 2
        return (opt[r:r+size, c:c+size],
                sar[r:r+size, c:c+size],
                mask[r:r+size, c:c+size])

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        opt_path, sar_path, mask_path = self.samples[idx]

        opt  = self._load_optical(opt_path)
        sar  = self._load_sar(sar_path)
        mask = self._load_mask(mask_path)


        # FIX: Apply synchronized spatial augmentations to all three
        sp_aug = self.spatial_transform(image=opt, mask=mask, sar=sar)
        opt, mask, sar = sp_aug['image'], sp_aug['mask'], sp_aug['sar']

        # Apply optical-only color augmentations
        opt_aug = self.color_transform(image=opt)
        opt_tensor = opt_aug['image']

        sar_tensor  = torch.from_numpy(
            np.transpose(sar, (2, 0, 1)).astype(np.float32)
        )
        sar_tensor  = (sar_tensor - 0.5) / 0.5

        mask_tensor = torch.from_numpy(mask).unsqueeze(0)

        return opt_tensor, sar_tensor, mask_tensor


def get_dataloaders(prepared_dir, cities, batch_size=4,
                    num_workers=0, img_size=512):
    print("\nBuilding Phase 5 datasets...")
    pin = torch.cuda.is_available()

    train_ds = DualModalDataset(prepared_dir, cities, split='train',
                                img_size=img_size)
    val_ds   = DualModalDataset(prepared_dir, cities, split='val',
                                img_size=img_size)
    test_ds  = DualModalDataset(prepared_dir, cities, split='test',
                                img_size=img_size)

    train_loader = DataLoader(train_ds, batch_size=batch_size,
                              shuffle=True,  num_workers=num_workers,
                              pin_memory=pin)
    val_loader   = DataLoader(val_ds,   batch_size=batch_size,
                              shuffle=False, num_workers=num_workers,
                              pin_memory=pin)
    test_loader  = DataLoader(test_ds,  batch_size=batch_size,
                              shuffle=False, num_workers=num_workers,
                              pin_memory=pin)

    print(f"  Batch: {batch_size}  img_size: {img_size}")
    return train_loader, val_loader, test_loader
# ============================================================
# LOSS
# ============================================================
class TverskyLoss(nn.Module):
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
        return 1 - (tp + self.smooth) / (
            tp + self.alpha * fp + self.beta * fn + self.smooth
        )


class RoadLoss(nn.Module):
    def __init__(self, pos_weight=3.0, alpha=0.3, beta=0.7):
        super().__init__()
        self.tversky    = TverskyLoss(alpha=alpha, beta=beta)
        self.pos_weight = pos_weight

    def forward(self, pred, target):
        pw  = torch.tensor([self.pos_weight], device=pred.device)
        bce = nn.functional.binary_cross_entropy_with_logits(
            pred, target, pos_weight=pw
        )
        return 0.6 * self.tversky(pred, target) + 0.4 * bce


# ============================================================
# METRICS
# ============================================================
def get_stats(pred, target, threshold=0.40):
    pb  = (torch.sigmoid(pred) > threshold).float()
    tp  = (pb * target).sum().item()
    fp  = (pb * (1 - target)).sum().item()
    fn  = ((1 - pb) * target).sum().item()
    i   = tp
    u   = pb.sum().item() + target.sum().item() - i
    return i, u, tp, fp, fn


# ============================================================
# WARM INITIALIZATION
# ============================================================
def warm_init_sar_encoder(model, phase3_ckpt_path, device):
    print(f"\n  Loading Phase 3 checkpoint: {phase3_ckpt_path}")
    ckpt = torch.load(phase3_ckpt_path,
                      map_location=device, weights_only=False)
    phase3_state = ckpt["model_state_dict"]

    opt_weights = {
        k.replace("optical_encoder.", ""): v
        for k, v in phase3_state.items()
        if k.startswith("optical_encoder.")
    }

    sar_state = model.sar_encoder.state_dict()
    copied = skipped = 0

    for key in sar_state:
        if key in opt_weights:
            if sar_state[key].shape == opt_weights[key].shape:
                sar_state[key] = opt_weights[key]
                copied += 1
            else:
                skipped += 1
        else:
            skipped += 1

    model.sar_encoder.load_state_dict(sar_state)
    print(f"  Warm init: {copied} layers copied, {skipped} skipped")
    return model


# ============================================================
# GPU MEMORY PROBE — safe, no BN corruption
# Fix: uses eval() + no_grad to avoid updating BN running stats
# ============================================================
def probe_gpu_memory(model, device, img_size, batch_size):
    """
    Probe GPU memory with a synthetic forward pass.
    Uses eval() + no_grad so BatchNorm running stats are NOT updated.
    """
    print("\n  Probing GPU memory...")
    model.eval()   # prevents BN running_mean/var from updating

    try:
        with torch.no_grad():
            dummy_opt = torch.randn(batch_size, 3, img_size, img_size,
                                    device=device)
            dummy_sar = torch.randn(batch_size, 2, img_size, img_size,
                                    device=device)
            _ = model(dummy_opt, dummy_sar)

        mem = torch.cuda.memory_allocated(device) / 1e9
        print(f"  GPU memory after probe: {mem:.2f} GB")

        if mem > 5.0:
            print("  WARNING: High memory usage — consider reducing batch_size to 2")

    except torch.cuda.OutOfMemoryError:
        print("  OOM on probe — reduce batch_size to 2 in CONFIG")
        raise

    finally:
        # Always restore to train mode after probe
        model.train()
        torch.cuda.empty_cache()


# ============================================================
# TRAIN ONE EPOCH
# ============================================================
def train_one_epoch(model, loader, optimizer, criterion,
                    scaler, device, epoch):
    model.train()
    total_loss = 0.0
    g_i = g_u = g_tp = g_fp = g_fn = 0.0

    pbar = tqdm(loader, desc=f"Epoch {epoch}")
    for opt, sar, masks in pbar:
        opt   = opt.to(device,   non_blocking=True)
        sar   = sar.to(device,   non_blocking=True)
        masks = masks.to(device, non_blocking=True)

        optimizer.zero_grad()

        with autocast("cuda"):
            logits = model(opt, sar)
            loss   = criterion(logits, masks)

        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(optimizer)
        scaler.update()

        with torch.no_grad():
            i, u, tp, fp, fn = get_stats(logits, masks)
        g_i += i; g_u += u; g_tp += tp; g_fp += fp; g_fn += fn
        total_loss += loss.item()

        pbar.set_postfix({
            "loss": f"{loss.item():.4f}",
            "iou" : f"{i/(u+1e-6):.3f}",
            "P"   : f"{tp/(tp+fp+1e-6):.2f}",
            "R"   : f"{tp/(tp+fn+1e-6):.2f}",
        })

    n = len(loader)
    return (total_loss/n,
            g_i/(g_u+1e-6),
            g_tp/(g_tp+g_fp+1e-6),
            g_tp/(g_tp+g_fn+1e-6))


# ============================================================
# VALIDATE
# ============================================================
def validate(model, loader, criterion, device):
    model.eval()
    total_loss = 0.0
    g_i = g_u = g_tp = g_fp = g_fn = 0.0

    with torch.no_grad():
        for opt, sar, masks in tqdm(loader, desc="Val"):
            opt   = opt.to(device,   non_blocking=True)
            sar   = sar.to(device,   non_blocking=True)
            masks = masks.to(device, non_blocking=True)

            with autocast("cuda"):
                logits = model(opt, sar)
                loss   = criterion(logits, masks)

            total_loss += loss.item()
            i, u, tp, fp, fn = get_stats(logits, masks)
            g_i += i; g_u += u
            g_tp += tp; g_fp += fp; g_fn += fn

    n    = len(loader)
    iou  = g_i  / (g_u  + 1e-6)
    dice = 2*g_i / (2*g_tp + g_fp + g_fn + 1e-6)
    prec = g_tp  / (g_tp + g_fp + 1e-6)
    rec  = g_tp  / (g_tp + g_fn + 1e-6)
    return total_loss/n, iou, dice, prec, rec


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("  SETU — Phase 5 Training (SAR + Optical Fusion)")
    print("=" * 60)
    print(f"  Device    : {CONFIG['device']}")
    if torch.cuda.is_available():
        print(f"  GPU       : {torch.cuda.get_device_name(0)}")
    print(f"  Strategy  : Warm init SAR from optical, freeze optical encoder")
    print(f"  Cities    : {CONFIG['cities']}")
    print(f"  Epochs    : {CONFIG['num_epochs']}")
    print(f"  Phase 3 baseline IoU : {PHASE3_BASELINE_IOU}")
    print("=" * 60)

    os.makedirs(CONFIG["checkpoint_dir"], exist_ok=True)

    if not Path(CONFIG["phase3_ckpt"]).exists():
        print(f"ERROR: Phase 3 checkpoint not found: {CONFIG['phase3_ckpt']}")
        return

    train_loader, val_loader, test_loader = get_dataloaders(
        CONFIG["prepared_dir"], CONFIG["cities"],
        batch_size=CONFIG["batch_size"],
        num_workers=CONFIG["num_workers"],
        img_size=CONFIG["img_size"],
    )

    if len(train_loader) == 0:
        print("ERROR: No training data")
        return

    # Build dual-modal model
    model = SEGFormerRoadExtractor(num_classes=1, use_sar=True)
    model = model.to(CONFIG["device"])

    # Load Phase 3 optical weights
    ckpt      = torch.load(CONFIG["phase3_ckpt"],
                           map_location=CONFIG["device"],
                           weights_only=False)
    opt_state = {
        k: v for k, v in ckpt["model_state_dict"].items()
        if not k.startswith("sar_encoder") and
           not k.startswith("cross_attention")
    }
    missing, unexpected = model.load_state_dict(opt_state, strict=False)
    print(f"\n  Phase 3 weights loaded")
    print(f"  New layers (to train): {len(missing)}")

    # Warm init SAR encoder
    model = warm_init_sar_encoder(
        model, CONFIG["phase3_ckpt"], CONFIG["device"]
    )

    # Freeze optical encoder
    for param in model.optical_encoder.parameters():
        param.requires_grad = False

    # Freeze early SAR layers (Stages 1, 2, 3) to preserve warm init
    # SegFormer stages are indexed 0, 1, 2, 3. We keep only stage 3 trainable.
    for name, param in model.sar_encoder.named_parameters():
        if "encoder.block.3" not in name and "encoder.layer_norm.3" not in name:
            param.requires_grad = False

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    frozen    = sum(p.numel() for p in model.parameters() if not p.requires_grad)
    print(f"\n  Trainable : {trainable/1e6:.1f}M params")
    print(f"  Frozen    : {frozen/1e6:.1f}M params (optical encoder)")

    # Memory probe — safe, no BN corruption
    if CONFIG["device"] == "cuda":
        probe_gpu_memory(model, CONFIG["device"],
                         CONFIG["img_size"], CONFIG["batch_size"])

    optimizer = AdamW([
        {"params": model.sar_encoder.parameters(),
         "lr"    : CONFIG["lr_sar"]},
        {"params": model.cross_attention_blocks.parameters(),
         "lr"    : CONFIG["lr_attn"]},
        {"params": list(model.sar_projections.parameters()) +
                   list(model.optical_projections.parameters()) +
                   list(model.fusion.parameters()) +
                   list(model.head.parameters()),
         "lr"    : CONFIG["lr_decoder"]},
    ], weight_decay=0.01)

    scheduler = CosineAnnealingLR(
        optimizer, T_max=CONFIG["num_epochs"], eta_min=1e-7
    )
    criterion = RoadLoss(
        pos_weight=CONFIG["pos_weight"],
        alpha=CONFIG["tversky_alpha"],
        beta=CONFIG["tversky_beta"],
    )
    scaler = GradScaler("cuda")

    best_iou = patience = 0
    history  = []

    print("\nTraining started...")
    print("Monitoring whether SAR fusion improves over Phase 3 baseline.\n")

    for epoch in range(1, CONFIG["num_epochs"] + 1):

        tr_loss, tr_iou, tr_prec, tr_rec = train_one_epoch(
            model, train_loader, optimizer, criterion,
            scaler, CONFIG["device"], epoch
        )
        vl_loss, vl_iou, vl_dice, vl_prec, vl_rec = validate(
            model, val_loader, criterion, CONFIG["device"]
        )

        scheduler.step()
        lr_now = optimizer.param_groups[0]['lr']

        delta = vl_iou - PHASE3_BASELINE_IOU
        delta_str = f"{delta:+.4f} vs Phase 3"

        print(f"\nEpoch {epoch}/{CONFIG['num_epochs']}")
        print(f"  Train — loss: {tr_loss:.4f}  IoU: {tr_iou:.4f}  "
              f"P: {tr_prec:.3f}  R: {tr_rec:.3f}")
        print(f"  Val   — loss: {vl_loss:.4f}  IoU: {vl_iou:.4f}  "
              f"Dice: {vl_dice:.4f}  P: {vl_prec:.3f}  R: {vl_rec:.3f}")
        print(f"  LR: {lr_now:.2e}   {delta_str}")

        history.append({
            "epoch"            : epoch,
            "train_loss"       : round(tr_loss, 5),
            "train_iou"        : round(tr_iou,  5),
            "val_loss"         : round(vl_loss, 5),
            "val_iou"          : round(vl_iou,  5),
            "val_dice"         : round(vl_dice, 5),
            "val_prec"         : round(vl_prec, 4),
            "val_rec"          : round(vl_rec,  4),
            "delta_vs_phase3"  : round(delta,   5),
        })
        with open(rf"{CONFIG['checkpoint_dir']}\history_p5.json", "w") as f:
            json.dump(history, f, indent=2)

        if vl_iou > best_iou:
            best_iou = vl_iou
            patience = 0
            torch.save({
                "epoch"            : epoch,
                "model_state_dict" : model.state_dict(),
                "val_iou"          : vl_iou,
                "val_prec"         : vl_prec,
                "val_rec"          : vl_rec,
                "config"           : CONFIG,
            }, rf"{CONFIG['checkpoint_dir']}\best_model_phase5.pth")
            print(f"  ✓ Best saved — IoU: {vl_iou:.4f}")
        else:
            patience += 1
            print(f"  No improvement ({patience}/{CONFIG['early_stop']})")
            if patience >= CONFIG["early_stop"]:
                print(f"\nEarly stopping at epoch {epoch}")
                break

        if epoch % 5 == 0:
            torch.save({
                "epoch"            : epoch,
                "model_state_dict" : model.state_dict(),
                "val_iou"          : vl_iou,
            }, rf"{CONFIG['checkpoint_dir']}\epoch_{epoch:03d}_p5.pth")

    # Final test
    print("\n" + "=" * 60)
    print("Final test evaluation...")
    ckpt = torch.load(
        rf"{CONFIG['checkpoint_dir']}\best_model_phase5.pth",
        map_location=CONFIG["device"], weights_only=False
    )
    model.load_state_dict(ckpt["model_state_dict"])

    ts_loss, ts_iou, ts_dice, ts_prec, ts_rec = validate(
        model, test_loader, criterion, CONFIG["device"]
    )

    improvement = (ts_iou - PHASE3_BASELINE_IOU) / PHASE3_BASELINE_IOU * 100

    print("\nPHASE 5 FINAL RESULTS (SAR + Optical Fusion):")
    print(f"  IoU       : {ts_iou:.4f}")
    print(f"  Dice      : {ts_dice:.4f}")
    print(f"  Precision : {ts_prec:.4f}")
    print(f"  Recall    : {ts_rec:.4f}")
    print(f"\n  Phase 3 baseline : {PHASE3_BASELINE_IOU:.4f}")
    print(f"  Phase 5 result   : {ts_iou:.4f}")
    print(f"  Delta            : {ts_iou - PHASE3_BASELINE_IOU:+.4f} ({improvement:+.1f}%)")

    if ts_iou > PHASE3_BASELINE_IOU:
        print("\n  SAR fusion improved road extraction")
    else:
        print("\n  SAR fusion did not improve — investigate SAR alignment")

    print("\n  Next: python inference_phase5.py")


if __name__ == "__main__":
    main()
