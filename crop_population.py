"""
SETU Project — Local Population Cropping (WorldPop 2020 UN-Adj)
Slices the Ahmedabad bounding box from the 1.5GB India raster and 
aligns it to the Phase 5 geometric grid using conservative sum resampling.
"""

import rasterio
from rasterio.warp import transform_bounds, reproject, Resampling
from rasterio.windows import from_bounds
import numpy as np
from pathlib import Path

BASE = r"C:\Users\omkar\OneDrive\Desktop\sih"
INDIA_POP_PATH = rf"{BASE}\ahmedabad_processed\ind_ppp_2020_UNadj.tif"
MASK_PATH = rf"{BASE}\ahmedabad_outputs\ahmedabad_road_mask_phase5.tif"
OUT_PATH = rf"{BASE}\ahmedabad_outputs\ahmedabad_population_100m.tif"

def crop_population():
    print("=" * 60)
    print("  SETU — Slicing Local Population Grid")
    print("=" * 60)

    print("\n[1/3] Reading Ahmedabad mask bounds...")
    with rasterio.open(MASK_PATH) as dst_src:
        dst_crs = dst_src.crs
        dst_transform = dst_src.transform
        dst_width = dst_src.width
        dst_height = dst_src.height
        dst_bounds = dst_src.bounds
        profile = dst_src.profile

        # Project mask bounds to EPSG:4326 to match WorldPop
        min_lon, min_lat, max_lon, max_lat = transform_bounds(
            dst_crs, 'EPSG:4326', *dst_bounds
        )

    print("[2/3] Slicing Ahmedabad from the 1.5GB India raster...")
    with rasterio.open(INDIA_POP_PATH) as src:
        # Buffer window to ensure seamless reprojection edges
        window = from_bounds(min_lon - 0.05, min_lat - 0.05, max_lon + 0.05, max_lat + 0.05, src.transform)
        window = window.round_offsets().round_lengths()
        
        pop_subset = src.read(1, window=window)
        subset_transform = src.window_transform(window)
        src_crs = src.crs

    print("[3/3] Aligning to grid (Using Resampling.sum to conserve counts)...")
    aligned_pop = np.zeros((dst_height, dst_width), dtype=np.float32)
    
    reproject(
        source=pop_subset,
        destination=aligned_pop,
        src_transform=subset_transform,
        src_crs=src_crs,
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        resampling=Resampling.sum 
    )

    # Clean NoData values
    aligned_pop[aligned_pop < 0] = 0
    aligned_pop[np.isnan(aligned_pop)] = 0

    profile.update(dtype=rasterio.float32, count=1, compress='lzw')
    with rasterio.open(OUT_PATH, 'w', **profile) as out:
        out.write(aligned_pop, 1)

    print("=" * 60)
    print(f"  Success! Clipped population saved to:")
    print(f"  {OUT_PATH}")
    print("=" * 60)

if __name__ == "__main__":
    crop_population()