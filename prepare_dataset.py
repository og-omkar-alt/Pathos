"""
SETU Project — Phase 3 Step 1
Dataset Preparation: Mumbai + Khartoum

HOW TO RUN:
  VS Code terminal -> python prepare_dataset.py
"""

import os
import json
import shutil
import numpy as np
import rasterio
from rasterio.features import rasterize
import geopandas as gpd
from pathlib import Path
from tqdm import tqdm


# ============================================================
# YOUR EXACT PATHS
# ============================================================

BASE = r"C:\Users\omkar\OneDrive\Desktop\sih"

CITIES = {
    "Mumbai": {
        "ps_rgb"  : rf"{BASE}\SN5_roads\tiles_upload\train\AOI_8_Mumbai\PS-RGB",
        "geojson" : rf"{BASE}\SN5_roads\tiles_upload\train\AOI_8_Mumbai\geojson_roads_speed",
    },
    "Khartoum": {
        "ps_rgb_folder"  : "PS-RGB",
        "geojson_folder" : "geojson_roads",
        "search_in"      : BASE,
        "city_keyword"   : "Khartoum",
    },
}

OUTPUT_DIR = rf"{BASE}\spacenet_prepared"

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def resolve_khartoum_paths():
    """
    Scans for the specific directory containing both PS-RGB and geojson_roads directly.
    Handles the nested AOI_5_Khartoum folder inside the extracted SN3 directory.
    """
    cfg = CITIES["Khartoum"]
    search_root = Path(cfg["search_in"])

    for root, dirs, files in os.walk(search_root):
        r_path = Path(root)
        if cfg["city_keyword"].lower() in r_path.name.lower():
            ps_rgb = r_path / cfg["ps_rgb_folder"]
            # Check for either 'geojson_roads' or 'geojson'
            geojson = r_path / cfg["geojson_folder"]
            if not geojson.exists():
                geojson = r_path / "geojson"

            if ps_rgb.exists() and geojson.exists():
                print(f"\n  Found Khartoum data directory: {r_path}")
                return str(ps_rgb), str(geojson)

    return None, None


def find_matching_geojson(tile_name, geojson_dir):
    """Matches an image tile name to its corresponding GeoJSON file."""
    geojson_dir = Path(geojson_dir)

    # 1. Direct match
    direct = geojson_dir / f"{tile_name}.geojson"
    if direct.exists():
        return direct

    # 2. Token substitution for standard SpaceNet naming conventions
    for old_token in ["PS-RGB", "PS-MS", "PAN", "MS", "RGB-PanSharpen"]:
        for new_token in ["geojson_roads_speed", "geojson_roads", "geojson"]:
            candidate = tile_name.replace(old_token, new_token)
            if (geojson_dir / f"{candidate}.geojson").exists():
                return geojson_dir / f"{candidate}.geojson"

    # 3. Match by trailing parts/suffixes
    parts = tile_name.replace("-", "_").split("_")
    for n in range(1, 5):
        if len(parts) >= n:
            suffix = "_".join(parts[-n:])
            matches = list(geojson_dir.glob(f"*{suffix}*.geojson"))
            if matches:
                return matches[0]

    # 4. Fallback match by last numeric token
    for part in reversed(parts):
        if part.isdigit():
            matches = list(geojson_dir.glob(f"*{part}.geojson"))
            if matches:
                return matches[0]

    return None


def rasterize_roads(geojson_path, reference_tif, output_mask, road_width=2):
    """Converts GeoJSON road vector polylines into binary segmentation masks."""
    with rasterio.open(reference_tif) as src:
        transform = src.transform
        width     = src.width
        height    = src.height
        crs       = src.crs
        profile   = src.profile.copy()

    pixel_size = abs(transform.a)

    with open(geojson_path) as f:
        geojson = json.load(f)

    if not geojson.get("features"):
        mask = np.zeros((height, width), dtype=np.uint8)
    else:
        try:
            gdf = gpd.read_file(geojson_path)
            if gdf.empty:
                mask = np.zeros((height, width), dtype=np.uint8)
            else:
                if gdf.crs is None:
                    gdf = gdf.set_crs("EPSG:4326")
                if gdf.crs != crs:
                    gdf = gdf.to_crs(crs)

                gdf["geometry"] = gdf.geometry.buffer(road_width * pixel_size)
                shapes = [(g, 1) for g in gdf.geometry if g is not None and not g.is_empty]

                mask = rasterize(
                    shapes, out_shape=(height, width),
                    transform=transform, fill=0, dtype=np.uint8
                ) if shapes else np.zeros((height, width), dtype=np.uint8)

        except Exception as e:
            print(f"\n    GeoJSON error: {e}")
            mask = np.zeros((height, width), dtype=np.uint8)

    profile.update(count=1, dtype=rasterio.uint8, nodata=None)
    with rasterio.open(output_mask, "w", **profile) as dst:
        dst.write(mask, 1)
    return int(mask.sum())


def prepare_city(city_name, ps_rgb_dir, geojson_dir):
    """Copies images and generates corresponding ground-truth mask tiles."""
    out_img  = Path(OUTPUT_DIR) / city_name / "images"
    out_mask = Path(OUTPUT_DIR) / city_name / "masks"
    out_img.mkdir(parents=True, exist_ok=True)
    out_mask.mkdir(parents=True, exist_ok=True)

    images = sorted(Path(ps_rgb_dir).glob("*.tif"))
    print(f"\n{'='*55}")
    print(f"  City     : {city_name}")
    print(f"  Images   : {len(images):,}")
    print(f"  PS-RGB   : {ps_rgb_dir}")
    print(f"  GeoJSON  : {geojson_dir}")
    print(f"{'='*55}")

    if not images:
        print("  ERROR: No .tif files found — check directory path")
        return 0

    success = failed = no_match = blank = 0

    for img_path in tqdm(images, desc=f"  {city_name}"):
        name = img_path.stem
        geo  = find_matching_geojson(name, geojson_dir)

        if geo is None:
            no_match += 1
            continue

        try:
            shutil.copy2(str(img_path), str(out_img / f"{name}.tif"))
            px = rasterize_roads(str(geo), str(img_path),
                                 str(out_mask / f"{name}_mask.tif"))
            blank   += (px == 0)
            success += 1
        except Exception as e:
            failed += 1
            if failed <= 3:
                print(f"\n  ERROR {name}: {e}")

    print(f"\n  {city_name} processing summary:")
    print(f"    Prepared    : {success:,}")
    print(f"    Blank masks : {blank:,}  (tiles with no roads)")
    print(f"    No GeoJSON  : {no_match:,}")
    print(f"    Errors      : {failed:,}")
    return success


# ============================================================
# MAIN EXECUTION PIPELINE
# ============================================================

def main():
    print("\n" + "="*55)
    print("  SETU — Dataset Preparation")
    print("  Cities: Mumbai + Khartoum")
    print("="*55)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    total = 0

    # ---- Mumbai (Direct Resolution) ----
    m_rgb = CITIES["Mumbai"]["ps_rgb"]
    m_geo = CITIES["Mumbai"]["geojson"]

    if not Path(m_rgb).exists():
        print(f"\nERROR: Mumbai PS-RGB directory not found:\n  {m_rgb}")
    elif not Path(m_geo).exists():
        print(f"\nERROR: Mumbai GeoJSON directory not found:\n  {m_geo}")
    else:
        total += prepare_city("Mumbai", m_rgb, m_geo)

    # ---- Khartoum (Automated Path Resolution) ----
    k_rgb, k_geo = resolve_khartoum_paths()

    if k_rgb and Path(k_rgb).exists() and k_geo and Path(k_geo).exists():
        total += prepare_city("Khartoum", k_rgb, k_geo)
    else:
        if k_rgb is None:
            print(f"\nERROR: Could not resolve Khartoum data folder under {BASE}")
        else:
            if not Path(k_rgb).exists():
                print(f"\nERROR: Khartoum PS-RGB directory not found:\n  {k_rgb}")
            if not Path(k_geo).exists():
                print(f"ERROR: Khartoum GeoJSON directory not found:\n  {k_geo}")

    # ---- Summary ----
    print("\n" + "="*55)
    print(f"  TOTAL pairs prepared : {total:,}")
    print(f"  Output folder        : {OUTPUT_DIR}")
    print("="*55)

    if total > 0:
        print("\n  Next step: Run python verify_sample.py")
    else:
        print("\n  Check folder structures and re-run.")


if __name__ == "__main__":
    main()