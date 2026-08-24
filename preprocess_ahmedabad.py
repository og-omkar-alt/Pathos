"""
SETU Project — Ahmedabad Data Preprocessing v3

BUGS FIXED vs v2:
  BUG: NISAR coordinate indexing was re-sorting x/y arrays before slicing,
       which inverted the row axis when y_coords is stored ascending (standard
       Cartesian UTM). This caused the windowed read to slice the wrong geographic
       area (potentially hundreds of km off).

  FIX: Use np.searchsorted on the NATIVE coordinate arrays without any sorting.
       Detect axis direction first, then compute row/col indices accordingly.
       flip_y flag marks whether to vertically flip the read chunk before writing,
       so the GeoTIFF is always written top-to-bottom.
"""

import numpy as np
from pathlib import Path
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject, transform_bounds
from rasterio.transform import from_origin

# ============================================================
# PATHS
# ============================================================
S2_SAFE    = r"C:\Users\omkar\Downloads\S2C_MSIL2A_20251227T054241_N0511_R005_T43QBF_20251227T092116.SAFE"
S1_SAFE    = r"C:\Users\omkar\Downloads\S1A_IW_GRDH_1SDV_20250904T010205_20250904T010230_060831_0792E0_E98E.SAFE"
NISAR_H5   = r"C:\Users\omkar\Downloads\NISAR_S2_PR_GCOV_025_113_A_013_3700_DHNA_A_20260716T003554_20260716T003630_P00500_M_F_I_001.h5"
OUTPUT_DIR = r"C:\Users\omkar\OneDrive\Desktop\sih\ahmedabad_processed"


# ============================================================
# HELPER: reproject any GeoTIFF to match reference grid
# ============================================================
def reproject_to_match(src_path, dst_path, ref_crs, ref_transform,
                       ref_width, ref_height, count, dtype):
    with rasterio.open(src_path) as src:
        profile = src.profile.copy()
        profile.update({
            "crs"      : ref_crs,
            "transform": ref_transform,
            "width"    : ref_width,
            "height"   : ref_height,
            "count"    : count,
            "dtype"    : dtype,
            "driver"   : "GTiff",
        })
        with rasterio.open(str(dst_path), "w", **profile) as dst:
            for b in range(1, src.count + 1):
                reproject(
                    source        = rasterio.band(src, b),
                    destination   = rasterio.band(dst, b),
                    src_transform = src.transform,
                    src_crs       = src.crs,
                    dst_transform = ref_transform,
                    dst_crs       = ref_crs,
                    resampling    = Resampling.bilinear,
                )
    print(f"    Reprojected -> {Path(dst_path).name}")


# ============================================================
# STEP 1: Sentinel-2 RGB
# ============================================================
def process_sentinel2(safe_dir, output_dir):
    print("\n[1/3] Sentinel-2 RGB...")
    safe = Path(safe_dir)

    r10m_dirs = list(safe.glob("GRANULE/*/IMG_DATA/R10m"))
    if not r10m_dirs:
        raise FileNotFoundError(f"R10m folder not found under {safe_dir}")
    r10m = r10m_dirs[0]

    def find_band(pattern):
        m = list(r10m.glob(pattern))
        if not m:
            raise FileNotFoundError(f"{pattern} not found in {r10m}")
        return m[0]

    b04_path = find_band("*_B04_10m.jp2")
    b03_path = find_band("*_B03_10m.jp2")
    b02_path = find_band("*_B02_10m.jp2")
    print(f"  R:{b04_path.name}  G:{b03_path.name}  B:{b02_path.name}")

    with rasterio.open(b04_path) as src:
        ref_profile   = src.profile.copy()
        ref_transform = src.transform
        ref_crs       = src.crs
        ref_width     = src.width
        ref_height    = src.height
        band_r = src.read(1).astype(np.float32)
    with rasterio.open(b03_path) as src:
        band_g = src.read(1).astype(np.float32)
    with rasterio.open(b02_path) as src:
        band_b = src.read(1).astype(np.float32)

    print(f"  Grid: {ref_height}x{ref_width}  CRS: {ref_crs.to_epsg()}")

    def stretch(arr):
        p2, p98 = np.percentile(arr, 2), np.percentile(arr, 98)
        arr = np.clip(arr, p2, p98)
        return ((arr - p2) / (p98 - p2 + 1e-6) * 255.0).astype(np.uint8)

    rgb = np.stack([stretch(band_r), stretch(band_g), stretch(band_b)], axis=0)

    out_path = Path(output_dir) / "ahmedabad_S2_RGB.tif"
    ref_profile.update(count=3, dtype=rasterio.uint8, driver="GTiff")
    with rasterio.open(str(out_path), "w", **ref_profile) as dst:
        dst.write(rgb)

    print(f"  Saved: {out_path.name}  {rgb.shape}")
    return str(out_path), ref_crs, ref_transform, ref_width, ref_height


# ============================================================
# STEP 2: Sentinel-1 VV + VH
# ============================================================
def process_sentinel1(safe_dir, output_dir, ref_crs, ref_transform,
                      ref_width, ref_height):
    print("\n[2/3] Sentinel-1 VV+VH...")
    safe = Path(safe_dir)
    meas = safe / "measurement"
    if not meas.exists():
        raise FileNotFoundError(f"measurement/ not found in {safe_dir}")

    vv_path = next(iter(meas.glob("*-vv-*.tiff")), None)
    vh_path = next(iter(meas.glob("*-vh-*.tiff")), None)
    if vv_path is None or vh_path is None:
        raise FileNotFoundError("VV or VH tiff not found")
    print(f"  VV:{vv_path.name}  VH:{vh_path.name}")

    def load_s1(path):
        with rasterio.open(path) as src:
            data    = src.read(1).astype(np.float32)
            profile = src.profile.copy()
        data = np.where(data > 0, 10 * np.log10(np.maximum(data, 1e-10)), -30.0)
        data = np.clip(data, -25.0, 5.0)
        return ((data + 25.0) / 30.0).astype(np.float32), profile

    vv, s1_profile = load_s1(vv_path)
    vh, _          = load_s1(vh_path)

    s1_profile.update(count=2, dtype=rasterio.float32, driver="GTiff")
    tmp = Path(output_dir) / "_s1_tmp.tif"
    with rasterio.open(str(tmp), "w", **s1_profile) as dst:
        dst.write(vv, 1)
        dst.write(vh, 2)

    out_path = Path(output_dir) / "ahmedabad_S1_VV_VH.tif"
    reproject_to_match(str(tmp), str(out_path),
                       ref_crs, ref_transform, ref_width, ref_height,
                       count=2, dtype="float32")
    tmp.unlink(missing_ok=True)
    print(f"  Saved: {out_path.name}")
    return str(out_path)


# ============================================================
# STEP 3: NISAR GCOV HH + HV  — windowed read, correct indexing
# ============================================================
def process_nisar(h5_path, output_dir, ref_crs, ref_transform,
                  ref_width, ref_height):
    print("\n[3/3] NISAR GCOV HH+HV (windowed, axis-aware)...")
    try:
        import h5py
    except ImportError:
        print("  ERROR: pip install h5py")
        return None

    with h5py.File(h5_path, "r") as f:
        fa = "science/SSAR/GCOV/grids/frequencyA"

        # -- Read CRS --
        nisar_crs = None
        for attr in ["projection", "crs_wkt", "spatial_ref"]:
            val = f[fa].attrs.get(attr, None)
            if val is not None:
                try:
                    if isinstance(val, bytes):
                        val = val.decode()
                    nisar_crs = rasterio.crs.CRS.from_wkt(str(val))
                    print(f"  CRS from attr '{attr}': EPSG {nisar_crs.to_epsg()}")
                    break
                except Exception:
                    pass
        if nisar_crs is None:
            try:
                ds_val = f[f"{fa}/projection"][()]
                if isinstance(ds_val, bytes):
                    ds_val = ds_val.decode()
                nisar_crs = rasterio.crs.CRS.from_epsg(int(str(ds_val).strip()))
                print(f"  CRS from dataset: EPSG {nisar_crs.to_epsg()}")
            except Exception as e:
                print(f"  CRS read failed ({e}) — defaulting UTM 43N")
                nisar_crs = rasterio.crs.CRS.from_epsg(32643)

        # -- Read native coordinate arrays (DO NOT SORT) --
        x_coords = np.array(f[f"{fa}/xCoordinates"][:], dtype=np.float64)
        y_coords = np.array(f[f"{fa}/yCoordinates"][:], dtype=np.float64)

        nisar_full_h = len(y_coords)
        nisar_full_w = len(x_coords)
        dx = float(abs(x_coords[1] - x_coords[0])) if len(x_coords) > 1 else 20.0
        dy = float(abs(y_coords[1] - y_coords[0])) if len(y_coords) > 1 else 20.0

        print(f"  Grid: {nisar_full_h}x{nisar_full_w}  dx={dx:.1f}m dy={dy:.1f}m")
        print(f"  x_coords: [{x_coords[0]:.0f} .. {x_coords[-1]:.0f}]")
        print(f"  y_coords: [{y_coords[0]:.0f} .. {y_coords[-1]:.0f}]")

        # -- Transform S2 AOI into NISAR CRS --
        s2_bounds   = rasterio.transform.array_bounds(
            ref_height, ref_width, ref_transform
        )
        aoi_bounds  = transform_bounds(ref_crs, nisar_crs, *s2_bounds)
        aoi_x_min, aoi_y_min, aoi_x_max, aoi_y_max = aoi_bounds

        # 10% buffer
        bx = (aoi_x_max - aoi_x_min) * 0.10
        by = (aoi_y_max - aoi_y_min) * 0.10
        aoi_x_min -= bx;  aoi_x_max += bx
        aoi_y_min -= by;  aoi_y_max += by

        print(f"  AOI in NISAR CRS: x=[{aoi_x_min:.0f},{aoi_x_max:.0f}]  "
              f"y=[{aoi_y_min:.0f},{aoi_y_max:.0f}]")

        # -- BUG FIX: axis-direction-aware indexing using searchsorted --
        # x_coords: always ascending in NISAR GCOV (UTM Easting)
        col_start = max(0, int(np.searchsorted(x_coords, aoi_x_min, side='left') - 1))
        col_end   = min(nisar_full_w, int(np.searchsorted(x_coords, aoi_x_max, side='right') + 1))
        win_x_origin = float(x_coords[col_start])

        # y_coords: detect ascending vs descending
        y_ascending = bool(y_coords[1] > y_coords[0])
        print(f"  y_coords direction: {'ascending' if y_ascending else 'descending'}")

        if y_ascending:
            # Standard Cartesian (south-to-north): searchsorted works directly
            row_start  = max(0, int(np.searchsorted(y_coords, aoi_y_min, side='left') - 1))
            row_end    = min(nisar_full_h, int(np.searchsorted(y_coords, aoi_y_max, side='right') + 1))
            # GeoTIFF needs top-left = max-Y; after reading we flip vertically
            win_y_origin = float(y_coords[row_end - 1])   # top = max northing
            flip_y = True
        else:
            # Image convention (north-to-south): negate for searchsorted
            row_start  = max(0, int(np.searchsorted(-y_coords, -aoi_y_max, side='left') - 1))
            row_end    = min(nisar_full_h, int(np.searchsorted(-y_coords, -aoi_y_min, side='right') + 1))
            win_y_origin = float(y_coords[row_start])     # top = first row = max northing
            flip_y = False

        win_h = row_end - row_start
        win_w = col_end - col_start

        print(f"  Window: rows {row_start}:{row_end}  cols {col_start}:{col_end}  "
              f"=> {win_h}x{win_w} ({win_h * win_w / 1e6:.1f}M pixels)")

        if win_h <= 0 or win_w <= 0:
            print("  ERROR: Empty window — NISAR may not cover Ahmedabad")
            print(f"  x_coords range: [{x_coords.min():.0f}, {x_coords.max():.0f}]")
            print(f"  y_coords range: [{y_coords.min():.0f}, {y_coords.max():.0f}]")
            return None

        available = list(f[fa].keys())
        print(f"  Available datasets: {available}")

        hh_key = next((k for k in ["HHHH", "VVVV", "HH"] if k in available), None)
        hv_key = next((k for k in ["HVHV", "VHVH", "VVHV", "HV"] if k in available), None)

        if hh_key is None:
            print(f"  ERROR: No HH band found in {available}")
            return None

        def read_window(key):
            ds = f[f"{fa}/{key}"]
            if ds.ndim == 3:
                chunk = ds[0, row_start:row_end, col_start:col_end]
            else:
                chunk = ds[row_start:row_end, col_start:col_end]
            arr = np.array(chunk)
            if np.iscomplexobj(arr):
                arr = np.abs(arr) ** 2      # covariance diagonal -> power
            return arr.real.astype(np.float32)

        print(f"  Reading {hh_key}...")
        hh_raw = read_window(hh_key)

        if hv_key:
            print(f"  Reading {hv_key}...")
            hv_raw = read_window(hv_key)
        else:
            print("  HV not found — using zeros")
            hv_raw = np.zeros_like(hh_raw)

        # Flip vertically if y was ascending (so GeoTIFF is top-to-bottom)
        if flip_y:
            hh_raw = np.flipud(hh_raw)
            hv_raw = np.flipud(hv_raw)

    # Normalise: power -> dB -> 0-1
    def norm_power(x):
        x = np.where(x > 0, 10 * np.log10(x + 1e-10), -30.0)
        x = np.clip(x, -30.0, 5.0)
        return ((x + 30.0) / 35.0).astype(np.float32)

    hh_norm = norm_power(hh_raw)
    hv_norm = norm_power(hv_raw)
    print(f"  HH norm range: [{hh_norm.min():.3f}, {hh_norm.max():.3f}]")

    nisar_win_transform = from_origin(win_x_origin, win_y_origin, dx, dy)

    tmp = Path(output_dir) / "_nisar_tmp.tif"
    nisar_profile = {
        "driver"   : "GTiff",
        "dtype"    : "float32",
        "width"    : win_w,
        "height"   : win_h,
        "count"    : 2,
        "crs"      : nisar_crs,
        "transform": nisar_win_transform,
    }
    with rasterio.open(str(tmp), "w", **nisar_profile) as dst:
        dst.write(hh_norm, 1)
        dst.write(hv_norm, 2)

    out_path = Path(output_dir) / "ahmedabad_NISAR_HH_HV.tif"
    reproject_to_match(str(tmp), str(out_path),
                       ref_crs, ref_transform, ref_width, ref_height,
                       count=2, dtype="float32")
    tmp.unlink(missing_ok=True)
    print(f"  Saved: {out_path.name}")
    return str(out_path)


# ============================================================
# VERIFICATION: print shape/CRS/bounds for all three outputs
# ============================================================
def verify_outputs(output_dir):
    print("\n--- Output Verification ---")
    for name in ["ahmedabad_S2_RGB.tif", "ahmedabad_S1_VV_VH.tif", "ahmedabad_NISAR_HH_HV.tif"]:
        p = Path(output_dir) / name
        if not p.exists():
            print(f"  MISSING: {name}")
            continue
        with rasterio.open(str(p)) as src:
            bounds = src.bounds
            print(f"  {name}")
            print(f"    Shape : {src.height}x{src.width}  bands={src.count}")
            print(f"    CRS   : EPSG {src.crs.to_epsg()}")
            print(f"    Bounds: left={bounds.left:.0f} right={bounds.right:.0f} "
                  f"bottom={bounds.bottom:.0f} top={bounds.top:.0f}")
    print("  All three should have identical Shape, CRS, and Bounds.")
    print("  If not, reproject_to_match failed — check rasterio installation.")


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("  SETU — Ahmedabad Preprocessing v3")
    print("=" * 60)

    out = Path(OUTPUT_DIR)
    out.mkdir(parents=True, exist_ok=True)

    s2_path, ref_crs, ref_transform, ref_w, ref_h = process_sentinel2(S2_SAFE, OUTPUT_DIR)
    s1_path  = process_sentinel1(S1_SAFE,  OUTPUT_DIR, ref_crs, ref_transform, ref_w, ref_h)
    nsr_path = process_nisar(NISAR_H5,    OUTPUT_DIR, ref_crs, ref_transform, ref_w, ref_h)

    verify_outputs(OUTPUT_DIR)

    print("\n" + "=" * 60)
    print("  DONE")
    print("=" * 60)
    print(f"  S2 RGB   : {s2_path}")
    print(f"  S1 VV+VH : {s1_path}")
    print(f"  NISAR    : {nsr_path or 'FAILED'}")
    print(f"\n  Next: python inference.py")


if __name__ == "__main__":
    main()
