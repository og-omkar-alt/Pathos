"""
Run this to see current training status and find the best checkpoint.
"""
import json
from pathlib import Path

BASE = r"C:\Users\omkar\OneDrive\Desktop\sih"

# Check all checkpoint dirs
for v in ["checkpoints_v5", "checkpoints_v4", "checkpoints_v3"]:
    hist = Path(BASE) / v / "history.json"
    best = Path(BASE) / v / "best_model.pth"
    if not hist.exists():
        continue

    with open(hist) as f:
        h = json.load(f)

    print(f"\n{'='*50}")
    print(f"  {v}  ({len(h)} epochs logged)")
    print(f"  best_model.pth exists: {best.exists()}")
    print(f"{'='*50}")

    # Best val IoU
    best_entry = max(h, key=lambda x: x["val_iou"])
    last_entry = h[-1]

    print(f"  Best epoch : {best_entry['epoch']}  "
          f"IoU={best_entry['val_iou']:.4f}  "
          f"P={best_entry.get('val_prec',0):.3f}  "
          f"R={best_entry.get('val_rec',0):.3f}")
    print(f"  Last epoch : {last_entry['epoch']}  "
          f"IoU={last_entry['val_iou']:.4f}  "
          f"P={last_entry.get('val_prec',0):.3f}  "
          f"R={last_entry.get('val_rec',0):.3f}")

    # Trend: last 5 epochs
    print(f"\n  Last 5 epochs:")
    print(f"  {'ep':>4}  {'tr_iou':>7}  {'val_iou':>7}  {'P':>6}  {'R':>6}  {'breaks':>8}")
    for e in h[-5:]:
        print(f"  {e['epoch']:>4}  "
              f"{e['train_iou']:>7.4f}  "
              f"{e['val_iou']:>7.4f}  "
              f"{e.get('val_prec',0):>6.3f}  "
              f"{e.get('val_rec',0):>6.3f}  "
              f"{e.get('val_breaks',0):>8.1f}")

    # Is it still improving?
    if len(h) >= 5:
        recent_ious = [e["val_iou"] for e in h[-5:]]
        trend = recent_ious[-1] - recent_ious[0]
        if trend > 0.005:
            print(f"\n  TREND: improving (+{trend:.4f} over last 5 epochs) — keep training")
        elif trend > -0.005:
            print(f"\n  TREND: plateauing ({trend:+.4f}) — may need LR adjustment")
        else:
            print(f"\n  TREND: declining ({trend:+.4f}) — possible overfitting")