"""
SETU Project — Download and clip WorldPop population raster for Ahmedabad.
Replaces the incorrect ahmedabad_population_100m.tif with real WorldPop data.
Run this AFTER build_osm_graph.py.
"""

import numpy as np
import requests
import rasterio
from rasterio.windows import from_bounds
from rasterio.transform import from_bounds as transform_from_bounds
from pathlib import Path
import tempfile
import os

BASE     = r"C:\Users\omkar\OneDrive\Desktop\sih"
OUT_PATH = rf"{BASE}\ahmedabad_outputs\ahmedabad_population_100m.tif"

# Ahmedabad bounding box — wide enough to cover OSM graph extent
MIN_LON, MAX_LON = 72.35, 72.75
MIN_LAT, MAX_LAT = 22.85, 23.25

def download_worldpop():
    """
    Downloads WorldPop India 2020 unconstrained 100m raster.
    Direct download from WorldPop FTP — no login required.
    """
    print("=" * 60)
    print("  SETU — Building Ahmedabad Population Raster")
    print("=" * 60)

    # WorldPop India 2020 — 100m unconstrained individual countries
    # This is the official public URL
    WORLDPOP_URL = (
        "https://data.worldpop.org/GIS/Population/"
        "Global_2000_2020/2020/IND/ind_ppp_2020.tif"
    )

    tmp_path = Path(tempfile.gettempdir()) / "ind_ppp_2020.tif"

    if not tmp_path.exists():
        print(f"\n[1/3] Downloading WorldPop India 2020 (~500MB) ...")
        print(f"      URL: {WORLDPOP_URL}")
        print("      This will take 5-15 minutes depending on connection.")

        with requests.get(WORLDPOP_URL, stream=True, timeout=300) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total * 100
                        print(f"\r      {pct:.1f}% ({downloaded//1024//1024}MB)", end="")
        print(f"\n      Downloaded to {tmp_path}")
    else:
        print(f"\n[1/3] Using cached download: {tmp_path}")

    return tmp_path


def clip_to_ahmedabad(worldpop_path):
    print(f"\n[2/3] Clipping to Ahmedabad bbox "
          f"({MIN_LAT}–{MAX_LAT}N, {MIN_LON}–{MAX_LON}E) ...")

    with rasterio.open(worldpop_path) as src:
        print(f"      Source CRS    : {src.crs}")
        print(f"      Source shape  : {src.shape}")
        print(f"      Source max val: {src.read(1).max():.2f}")

        window    = from_bounds(MIN_LON, MIN_LAT, MAX_LON, MAX_LAT,
                                transform=src.transform)
        data      = src.read(1, window=window)
        out_trans = src.window_transform(window)
        nodata    = src.nodata if src.nodata is not None else -99999

    # Replace nodata with 0
    data = np.where(data == nodata, 0, data)
    data = np.where(data < 0,       0, data)

    valid = data[data > 0]
    print(f"      Clipped shape : {data.shape}")
    print(f"      Max value     : {valid.max():.2f} people/pixel")
    print(f"      Mean (non-zero): {valid.mean():.2f}")
    print(f"      Total population estimate: {int(valid.sum()):,}")

    Path(OUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(OUT_PATH, "w",
                       driver="GTiff",
                       height=data.shape[0],
                       width=data.shape[1],
                       count=1,
                       dtype=data.dtype,
                       crs="EPSG:4326",
                       transform=out_trans,
                       nodata=0) as dst:
        dst.write(data, 1)

    print(f"\n[3/3] Saved → {OUT_PATH}")
    print("\n  ✅ Population raster ready.")
    print("     Expected population_affected for 800m radius: 20,000–80,000")
    print("=" * 60)


def verify():
    """Quick sanity check on the saved raster."""
    print("\n  Verifying saved raster ...")
    with rasterio.open(OUT_PATH) as src:
        data  = src.read(1)
        valid = data[data > 0]
        print(f"  CRS          : {src.crs}")
        print(f"  Shape        : {src.shape}")
        print(f"  Max value    : {valid.max():.2f}")
        print(f"  Non-zero px  : {len(valid):,}")
        print(f"  Total pop    : {int(valid.sum()):,}")
    if valid.max() > 10:
        print("  ✅ Looks correct — values are people per pixel")
    else:
        print("  ⚠ Max value is low — may not be WorldPop people/pixel data")


if __name__ == "__main__":
    try:
        worldpop_path = download_worldpop()
        clip_to_ahmedabad(worldpop_path)
        verify()
    except requests.exceptions.ConnectionError:
        print("\n  ❌ Download failed — no internet connection or URL changed.")
        print("  Manual alternative:")
        print("  1. Go to: https://hub.worldpop.org/geodata/summary?id=24777")
        print("  2. Download 'ind_ppp_2020.tif'")
        print(f"  3. Save to: {tempfile.gettempdir()}\\ind_ppp_2020.tif")
        print("  4. Run this script again.")
    except Exception as e:
        print(f"\n  ❌ Error: {e}")
        import traceback
        traceback.print_exc()