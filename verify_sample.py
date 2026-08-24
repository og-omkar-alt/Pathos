"""
SETU Project — Phase 3 Step 2
Dataset Verification

HOW TO RUN:
  VS Code terminal -> python verify_sample.py
"""

import os
import random
import numpy as np
import rasterio
import matplotlib.pyplot as plt
from pathlib import Path

# Corrected path to match your output directory
PREPARED_DIR = r"C:\Users\omkar\OneDrive\Desktop\sih\spacenet_prepared"

def normalize_percentile(img):
    """
    Removes sensor glare. Normalizes using the 2nd and 98th percentiles
    instead of the absolute max, preventing the image from appearing pitch black.
    """
    p2, p98 = np.percentile(img, (2, 98))
    img_c = np.clip(img, p2, p98)
    # Prevent division by zero
    if p98 == p2:
        return img_c
    return (img_c - p2) / (p98 - p2)

def verify_city(city="Mumbai"):
    img_dir = Path(PREPARED_DIR) / city / "images"
    mask_dir = Path(PREPARED_DIR) / city / "masks"

    if not img_dir.exists():
        print(f"ERROR: {img_dir} not found. Run prepare_dataset.py first.")
        return

    images = list(img_dir.glob("*.tif"))
    
    print(f"\n{city}:")
    print(f"  Images Available: {len(images)}")

    if not images:
        print("  ERROR: No images found")
        return

    # Keep grabbing a random tile until we find one that actually has roads
    max_attempts = 50
    for _ in range(max_attempts):
        img_path = random.choice(images)
        mask_path = mask_dir / f"{img_path.stem}_mask.tif"
        
        if not mask_path.exists():
            continue
            
        with rasterio.open(str(mask_path)) as src:
            mask = src.read(1)
            
        # If the tile has at least a few road pixels, break the loop and use it
        if mask.sum() > 500: 
            break

    # Load and normalize the optical image
    with rasterio.open(str(img_path)) as src:
        img = src.read([1, 2, 3])
        img = np.transpose(img, (1, 2, 0)).astype(np.float32)
        img_norm = normalize_percentile(img)

    road_pct = 100 * mask.sum() / mask.size
    print(f"  Visualizing: {img_path.name}")
    print(f"  Road pixels: {mask.sum()} / {mask.size} = {road_pct:.2f}%")

    if road_pct < 0.1:
        print("  WARNING: Very few road pixels")
    elif road_pct > 30:
        print("  WARNING: Too many road pixels")
    else:
        print("  Road density optimal")

    # Plotting
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # Panel 1: Optical
    axes[0].imshow(img_norm)
    axes[0].set_title(f"Satellite Image\n{img_path.name}")
    axes[0].axis('off')

    # Panel 2: Mask
    axes[1].imshow(mask, cmap='magma')
    axes[1].set_title("Generated Road Label Mask\n(Bright = Road)")
    axes[1].axis('off')

    # Panel 3: Overlay
    overlay = img_norm.copy()
    overlay[mask == 1, 0] = 1.0   # Red channel maxed out for roads
    overlay[mask == 1, 1] = 0.0
    overlay[mask == 1, 2] = 0.0
    axes[2].imshow(overlay)
    axes[2].set_title("Data Pipeline Overlay\n(Red = Extracted Vector)")
    axes[2].axis('off')

    plt.tight_layout()
    out_path = f"verify_{city}.png"
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    print(f"  Saved verification image to: {out_path}")
    plt.show()

def check_all_cities():
    print("=" * 60)
    print("Dataset Verification Pipeline")
    print("=" * 60)

    prepared_path = Path(PREPARED_DIR)
    if not prepared_path.exists():
        print(f"ERROR: Base directory {PREPARED_DIR} does not exist.")
        return

    cities = [d.name for d in prepared_path.iterdir() if d.is_dir()]

    if not cities:
        print("No cities found. Run prepare_dataset.py first.")
        return

    for city in cities:
        verify_city(city)

    print("\nVerification complete.")

if __name__ == "__main__":
    check_all_cities()