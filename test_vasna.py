"""
Quick test — run this to verify everything works before touching frontend.
"""
import requests
import json

BASE = "http://127.0.0.1:8000"

print("=" * 55)
print("  SETU — Backend Verification Test")
print("=" * 55)

# 1. Health check
print("\n[1/3] Health check ...")
r = requests.get(f"{BASE}/")
s = r.json()
print(f"  Status  : {s['status']}")
print(f"  Nodes   : {s['summary']['nodes']:,}")
print(f"  Edges   : {s['summary']['edges']:,}")
print(f"  Comp    : {s['summary']['components']:,}")

# 2. Demo scenario
print("\n[2/3] Getting demo scenario ...")
r = requests.get(f"{BASE}/api/v1/simulation/demo-scenario")
demo = r.json()
print(f"  Status  : {demo['status']}")
if demo['status'] == 'success':
    p = demo['payload']
    print(f"  Zone    : lat={p['lat']}, lon={p['lon']}, r={p['radius_m']}m")
    print(f"  Start   : {p['route_start_lat']}, {p['route_start_lon']}")
    print(f"  End     : {p['route_end_lat']}, {p['route_end_lon']}")

# 3. Vasna simulation
print("\n[3/3] Running Vasna flood simulation ...")
payload = {
    "lat"             : 23.0089,
    "lon"             : 72.5588,
    "radius_m"        : 800,
    "route_start_lat" : 23.0450,
    "route_start_lon" : 72.5400,
    "route_end_lat"   : 22.9900,
    "route_end_lon"   : 72.5700,
    "max_snap_dist_m" : 3000,
}
r  = requests.post(f"{BASE}/api/v1/simulation/simulate",
                   json=payload, timeout=60)
d  = r.json()
sr = d.get("simulation_result", {})

print(f"  Status          : {d['status']}")
print(f"  Population      : {sr.get('population_affected', 0):,}")
print(f"  Disconnected    : {sr.get('disconnected_wards', 0)}")
print(f"  Edges removed   : {sr.get('edges_removed', 0)}")
print(f"  Connectivity    : {sr.get('connectivity_before')} → "
      f"{sr.get('connectivity_after')}")
print(f"  Resilience      : {sr.get('resilience_before')} → "
      f"{sr.get('resilience_after')}")
print(f"  Priority        : {sr.get('emergency_priority')} "
      f"({sr.get('priority_score')})")
print(f"  Failed segments : {len(d.get('failed_segments', []))}")

nr = d.get("normal_route", {})
sf = d.get("safe_route", {})
print(f"\n  Normal route    : {nr.get('status')} "
      f"— {nr.get('metrics', {}).get('distance_km', '—')} km "
      f"/ {nr.get('metrics', {}).get('estimated_time_mins', '—')} min")
print(f"  Safe route      : {sf.get('status')} "
      f"— {sf.get('metrics', {}).get('distance_km', '—')} km "
      f"/ {sf.get('metrics', {}).get('estimated_time_mins', '—')} min")

if sf.get('status') == 'success':
    print(f"  Detour          : +{sf.get('detour_km', 0)} km "
          f"/ +{sf.get('detour_mins', 0)} min")
    print("\n  ✅ EVERYTHING WORKING — ready for frontend build")
elif sf.get('status') == 'isolated':
    print("\n  ⚠ Safe route isolated — try radius_m: 500")
else:
    print(f"\n  ⚠ Safe route: {sf.get('message', 'unknown')}")

print("=" * 55)