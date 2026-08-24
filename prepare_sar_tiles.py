"""
SETU Project — Phase 5 Step 1
Prepare SAR tiles: crop city-wide Sentinel-1 GeoTIFF
into 512x512 tiles matching existing SpaceNet optical tiles exactly.

Output: spacenet_prepared/Mumbai/sar/ and spacenet_prepared/Khartoum/sar/
Each SAR tile matches the corresponding optical tile by filename.
"""

import os
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import reproject, Resampling
from pathlib import Path
from tqdm import tqdm


# ============================================================
# CONFIGURATION
# ============================================================
BASE = r"C:\Users\omkar\OneDrive\Desktop\sih"

CONFIG = {
    "cities": {
        "Mumbai": {
            "s1_path"    : rf"{BASE}\sentinel1_training\mumbai.tif",
            "optical_dir": rf"{BASE}\spacenet_prepared\Mumbai\images",
            "sar_out_dir": rf"{BASE}\spacenet_prepared\Mumbai\sar",
        },
        "Khartoum": {
            "s1_path"    : rf"{BASE}\sentinel1_training\khartoum.tif",
            "optical_dir": rf"{BASE}\spacenet_prepared\Khartoum\images",
            "sar_out_dir": rf"{BASE}\spacenet_prepared\Khartoum\sar",
        },
    }
}


def normalize_sar_band(arr):
    """Convert to dB then normalize to 0-1"""
    arr  = arr.astype(np.float32)
    arr  = np.where(arr > 0, 10 * np.log10(arr + 1e-10), -30.0)
    p2, p98 = np.percentile(arr[arr > -30], (2, 98))
    arr  = np.clip(arr, p2, p98)
    arr  = (arr - p2) / (p98 - p2 + 1e-8)
    return arr.astype(np.float32)


def process_city(city_name, cfg):
    print(f"\n{'='*55}")
    print(f"  Processing: {city_name}")
    print(f"{'='*55}")

    optical_dir = Path(cfg["optical_dir"])
    sar_out_dir = Path(cfg["sar_out_dir"])
    sar_out_dir.mkdir(parents=True, exist_ok=True)

    optical_tiles = sorted(list(optical_dir.glob("*.tif")))
    print(f"  Optical tiles found : {len(optical_tiles)}")

    if not optical_tiles:
        print(f"  ERROR: No optical tiles in {optical_dir}")
        return 0

    success = skipped = failed = 0

    with rasterio.open(cfg["s1_path"]) as s1_src:
        s1_crs       = s1_src.crs
        s1_transform = s1_src.transform
        s1_bounds    = s1_src.bounds
        print(f"  S1 CRS     : {s1_crs}")
        print(f"  S1 bounds  : {s1_bounds}")

        for opt_path in tqdm(optical_tiles, desc=f"  {city_name}"):
            tile_name = opt_path.stem
            out_path  = sar_out_dir / f"{tile_name}_sar.tif"

            if out_path.exists():
                skipped += 1
                continue

            # Get optical tile bounds and CRS
            with rasterio.open(str(opt_path)) as opt_src:
                opt_bounds    = opt_src.bounds
                opt_crs       = opt_src.crs
                opt_transform = opt_src.transform
                opt_w         = opt_src.width
                opt_h         = opt_src.height

            try:
                # Reproject SAR to match optical tile exactly
                sar_arr = np.zeros((2, opt_h, opt_w), dtype=np.float32)

                for band_idx in range(2):
                    reproject(
                        source        = rasterio.band(s1_src, band_idx + 1),
                        destination   = sar_arr[band_idx],
                        src_crs       = s1_crs,
                        dst_crs       = opt_crs,
                        dst_transform = opt_transform,
                        dst_width     = opt_w,
                        dst_height    = opt_h,
                        resampling    = Resampling.bilinear,
                    )

                # Normalize each band
                sar_arr[0] = normalize_sar_band(sar_arr[0])  # VV
                sar_arr[1] = normalize_sar_band(sar_arr[1])  # VH

                # Check if SAR has valid data (not all zeros = outside S1 footprint)
                if sar_arr.sum() == 0:
                    skipped += 1
                    continue

                # Save SAR tile
                profile = {
                    "driver"    : "GTiff",
                    "dtype"     : "float32",
                    "count"     : 2,
                    "height"    : opt_h,
                    "width"     : opt_w,
                    "crs"       : opt_crs,
                    "transform" : opt_transform,
                    "compress"  : "lzw",
                }
                with rasterio.open(str(out_path), "w", **profile) as dst:
                    dst.write(sar_arr)

                success += 1

            except Exception as e:
                failed += 1
                if failed <= 3:
                    print(f"\n  ERROR on {tile_name}: {e}")

    print(f"\n  {city_name} done:")
    print(f"    Created  : {success}")
    print(f"    Skipped  : {skipped}  (outside S1 footprint or already exists)")
    print(f"    Failed   : {failed}")
    return success


def main():
    print("=" * 55)
    print("  SETU Phase 5 — Prepare SAR Tiles")
    print("=" * 55)

    total = 0
    for city_name, cfg in CONFIG["cities"].items():
        if not Path(cfg["s1_path"]).exists():
            print(f"\nSkipping {city_name} — S1 not found: {cfg['s1_path']}")
            continue
        total += process_city(city_name, cfg)

    print(f"\n{'='*55}")
    print(f"  Total SAR tiles prepared: {total}")
    print(f"{'='*55}")

    if total > 0:
        print("\n  Verify one sample:")
        print("  python -c \"")
        print("  import rasterio, glob")
        print(r"  f = glob.glob(r'C:\Users\omkar\OneDrive\Desktop\sih\spacenet_prepared\Mumbai\sar\*.tif')[0]")
        print("  s = rasterio.open(f)")
        print("  print(s.count, s.width, s.height, s.read().min(), s.read().max())")
        print("  \"")
        print("\n  Next: python train_phase5.py")


if __name__ == "__main__":
    main()