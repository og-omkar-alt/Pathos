"""
SETU Project — RouteMind AI  |  Streamlit Frontend v2
Area-based search + Simulate button. No map clicking required.
Space-tech mission-control aesthetic.
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
from pathlib import Path
import sys
import random
import numpy as np
import networkx as nx
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import networkx as nx

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
from routing_engine import RouteMindEngine

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SETU · RouteMind AI",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
    background-color: #080d17;
    color: #c8d8f0;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b1120 0%, #0d1528 100%);
    border-right: 1px solid #1a2a4a;
}
[data-testid="stSidebar"] * { color: #c8d8f0 !important; }
.main .block-container {
    background-color: #080d17;
    padding-top: 1.5rem;
    max-width: 1400px;
}

/* Header */
.setu-header {
    background: linear-gradient(135deg, #0b1628 0%, #0f2040 50%, #0b1628 100%);
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1.5rem;
    position: relative;
    overflow: hidden;
}
.setu-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: repeating-linear-gradient(
        90deg, transparent, transparent 60px,
        rgba(30,90,160,0.04) 60px, rgba(30,90,160,0.04) 61px
    );
}
.setu-logo {
    font-family: 'Space Mono', monospace;
    font-size: 2.4rem;
    font-weight: 700;
    color: #4fc3f7;
    letter-spacing: 0.12em;
    line-height: 1;
}
.setu-tagline {
    font-size: 0.78rem;
    color: #5a8abf;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-top: 0.3rem;
}
.setu-subtitle {
    font-size: 1rem;
    color: #8aafcf;
    max-width: 480px;
    line-height: 1.5;
}
.setu-badge {
    margin-left: auto;
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    color: #2ecc71;
    border: 1px solid #2ecc71;
    padding: 0.25rem 0.6rem;
    border-radius: 4px;
    letter-spacing: 0.15em;
    background: rgba(46,204,113,0.06);
}

/* Cards */
.metric-card {
    background: #0d1a2e;
    border: 1px solid #1a2e4a;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.75rem;
    position: relative;
    overflow: hidden;
}
.metric-card::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #4fc3f7, #1565c0);
}
.metric-label {
    font-size: 0.68rem;
    color: #5a8abf;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 0.4rem;
}
.metric-value {
    font-family: 'Space Mono', monospace;
    font-size: 1.6rem;
    font-weight: 700;
    color: #4fc3f7;
    line-height: 1;
}
.metric-unit { font-size: 0.75rem; color: #5a8abf; margin-top: 0.2rem; }

/* Status */
.status-success {
    background: rgba(46,204,113,0.08);
    border: 1px solid rgba(46,204,113,0.3);
    border-left: 3px solid #2ecc71;
    border-radius: 8px;
    padding: 0.9rem 1.2rem;
    color: #2ecc71;
    font-size: 0.9rem;
    margin-bottom: 1rem;
}
.status-error {
    background: rgba(231,76,60,0.08);
    border: 1px solid rgba(231,76,60,0.3);
    border-left: 3px solid #e74c3c;
    border-radius: 8px;
    padding: 0.9rem 1.2rem;
    color: #e74c3c;
    font-size: 0.9rem;
    margin-bottom: 1rem;
}
.status-warning {
    background: rgba(241,196,15,0.08);
    border: 1px solid rgba(241,196,15,0.3);
    border-left: 3px solid #f1c40f;
    border-radius: 8px;
    padding: 0.9rem 1.2rem;
    color: #f1c40f;
    font-size: 0.9rem;
    margin-bottom: 1rem;
}
.status-idle {
    background: rgba(79,195,247,0.06);
    border: 1px solid rgba(79,195,247,0.2);
    border-left: 3px solid #4fc3f7;
    border-radius: 8px;
    padding: 0.9rem 1.2rem;
    color: #5a8abf;
    font-size: 0.88rem;
    margin-bottom: 1rem;
}

/* Coord box */
.coord-box {
    background: #0a1525;
    border: 1px solid #1a2e4a;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    font-family: 'Space Mono', monospace;
    font-size: 0.78rem;
    color: #4fc3f7;
    margin-bottom: 0.75rem;
    line-height: 1.9;
}
.coord-label { color: #3a6a9a; font-size: 0.65rem; letter-spacing: 0.15em; text-transform: uppercase; }

/* Sidebar labels */
.sidebar-section {
    font-family: 'Space Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #2a4a7a !important;
    border-bottom: 1px solid #1a2a4a;
    padding-bottom: 0.4rem;
    margin: 1.2rem 0 0.8rem;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #1565c0, #0d47a1) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
    padding: 0.5rem 1.2rem !important;
    width: 100% !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #1976d2, #1565c0) !important;
    box-shadow: 0 4px 20px rgba(79,195,247,0.2) !important;
}

/* Simulate button — accent colour */
div[data-testid="stButton"]:has(button[kind="primary"]) > button {
    background: linear-gradient(135deg, #00897b, #00695c) !important;
}

.stTextInput > div > div > input {
    background: #0d1a2e !important;
    border: 1px solid #1a2e4a !important;
    color: #c8d8f0 !important;
    border-radius: 6px !important;
    font-family: 'Space Grotesk', sans-serif !important;
}
.stSelectbox > div > div {
    background: #0d1a2e !important;
    border: 1px solid #1a2e4a !important;
    color: #c8d8f0 !important;
}
footer { display: none; }
#MainMenu { display: none; }
div[data-testid="stDecoration"] { display: none; }
.map-wrapper { border: 1px solid #1a2e4a; border-radius: 12px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)


# ── Engine ────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Initialising RouteMind engine …")
def load_engine():
    try:
        return RouteMindEngine(), None
    except Exception as e:
        return None, str(e)


# ── Geocoder ──────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def geocode_area(area_name: str):
    """
    Returns (lat, lon) for a place name using Nominatim, biased to Ahmedabad.
    Returns None if geocoding fails.
    """
    try:
        geolocator = Nominatim(user_agent="setu_routemind_v2", timeout=5)
        # Append city context so partial names resolve correctly
        query = f"{area_name}, Ahmedabad, Gujarat, India"
        loc   = geolocator.geocode(query)
        if loc:
            return (loc.latitude, loc.longitude)
        return None
    except (GeocoderTimedOut, GeocoderServiceError):
        return None


def find_nearest_node_to_gps(engine, lat, lon, max_dist_m=1000):
    """Snap a GPS coordinate to the nearest graph node."""
    try:
        node_id = engine._snap_to_node(lat, lon, max_dist_m=max_dist_m)
        return node_id
    except ValueError:
        return None


@st.cache_data(show_spinner=False)
def get_largest_component_set(_engine):
    """Returns the set of node IDs in the largest connected component."""
    largest_cc = max(nx.connected_components(_engine.G), key=len)
    return largest_cc

def pick_random_node_near(engine, lat, lon, radius_nodes=50):
    """
    Pick a random node from the largest component among the
    `radius_nodes` closest nodes to the GPS coordinate.
    Falls back to nearest node in largest component if none found nearby.
    """
    largest_cc = get_largest_component_set(engine)
    
    utm_x, utm_y = engine.to_utm.transform(lon, lat)
    # Query more candidates to increase chance of hitting largest component
    k = min(radius_nodes * 4, len(engine.node_ids))
    dists, idxs = engine.tree.query([utm_x, utm_y], k=k)
    
    # Filter to only nodes in the largest component
    valid_idxs = [idx for idx in idxs 
                  if engine.node_ids[idx] in largest_cc]
    
    if valid_idxs:
        chosen_idx = random.choice(valid_idxs[:radius_nodes])
        return engine.node_ids[chosen_idx]
    
    # Last resort — return closest node in largest component regardless of distance
    for idx in idxs:
        if engine.node_ids[idx] in largest_cc:
            return engine.node_ids[idx]
    
    return None


# ── Session state ─────────────────────────────────────────────────────────────
for k, v in {
    "route_result"  : None,
    "start_node_gps": None,   # (lat, lon) of snapped origin
    "end_node_gps"  : None,   # (lat, lon) of snapped destination
    "origin_area"   : "",
    "dest_area"     : "",
    "sim_count"     : 0,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Load engine ───────────────────────────────────────────────────────────────
engine, engine_err = load_engine()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="setu-header">
    <div>
        <div class="setu-logo">SETU</div>
        <div class="setu-tagline">Satellite-Enhanced Terrain Understanding</div>
    </div>
    <div class="setu-subtitle">
        SAR-derived road network · WCS gap healing · population-weighted A* routing.<br>
        Search by area name and simulate a route.
    </div>
    <div class="setu-badge">● SYSTEM ONLINE</div>
</div>
""", unsafe_allow_html=True)

if engine_err:
    st.markdown(f'<div class="status-error">⚠ Engine failed to load: {engine_err}</div>',
                unsafe_allow_html=True)
    st.stop()

summary = engine.graph_summary()

# ── Layout ────────────────────────────────────────────────────────────────────
sidebar      = st.sidebar
col_map, col_panel = st.columns([3, 1], gap="medium")


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with sidebar:
    st.markdown('<div class="sidebar-section">Network Status</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="coord-box">
        <span class="coord-label">Nodes</span><br>{summary['nodes']:,}<br>
        <span class="coord-label">Edges</span><br>{summary['edges']:,}<br>
        <span class="coord-label">Components</span><br>{summary['components']:,}<br>
        <span class="coord-label">Road coverage</span><br>{summary['total_km']:,.1f} km
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">Route Settings</div>', unsafe_allow_html=True)
    weight_type = st.selectbox(
        "Optimise for",
        options=["travel_time", "length_m"],
        format_func=lambda x: "⏱ Fastest (congestion-aware)" if x == "travel_time"
                               else "📏 Shortest distance",
        label_visibility="collapsed",
    )
    snap_dist = st.slider("Snap radius (m)", 200, 2000, 1000, 100)

    st.markdown('<div class="sidebar-section">About</div>', unsafe_allow_html=True)
    with st.expander("ℹ SETU pipeline", expanded=False):
        st.markdown("""
**SETU** extracts navigable road networks from Sentinel-1 SAR imagery:

- **Phase 5** deep-learning road mask
- **WCS healing** — 38.8 % break-density reduction
- **Population telemetry** — WorldPop 100 m density (1×–5× congestion)
- **A\*** with admissible Euclidean heuristics
        """)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN — search inputs + simulate
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### 🛰 Plan a Route")

inp_col1, inp_col2, btn_col = st.columns([2, 2, 1])

with inp_col1:
    origin_input = st.text_input(
        "🟢 Origin area",
        value=st.session_state.origin_area,
        placeholder="e.g. Satellite Road, Ahmedabad",
        key="origin_text",
    )

with inp_col2:
    dest_input = st.text_input(
        "🔴 Destination area",
        value=st.session_state.dest_area,
        placeholder="e.g. Maninagar, Ahmedabad",
        key="dest_text",
    )

with btn_col:
    st.markdown("<br>", unsafe_allow_html=True)   # vertical align
    simulate_clicked = st.button("🚀 Simulate Route", type="primary", key="btn_simulate")

# ── Simulate logic ────────────────────────────────────────────────────────────
if simulate_clicked:
    if not origin_input.strip() or not dest_input.strip():
        st.markdown('<div class="status-warning">⚠ Enter both an origin and a destination area.</div>',
                    unsafe_allow_html=True)
    else:
        st.session_state.origin_area = origin_input.strip()
        st.session_state.dest_area   = dest_input.strip()

        with st.spinner("Geocoding areas …"):
            origin_gps = geocode_area(origin_input.strip())
            dest_gps   = geocode_area(dest_input.strip())

        if origin_gps is None:
            st.markdown(f'<div class="status-error">✕ Could not locate "{origin_input}". '
                        f'Try a more specific name, e.g. "Vastrapur, Ahmedabad".</div>',
                        unsafe_allow_html=True)
        elif dest_gps is None:
            st.markdown(f'<div class="status-error">✕ Could not locate "{dest_input}". '
                        f'Try a more specific name.</div>',
                        unsafe_allow_html=True)
        else:
            with st.spinner("Snapping to road network …"):
                # Pick a random nearby node for variety across simulations
                start_node = pick_random_node_near(engine, origin_gps[0], origin_gps[1])
                end_node   = pick_random_node_near(engine, dest_gps[0],   dest_gps[1])

                if start_node is None:
                    st.markdown('<div class="status-error">✕ No road nodes found near origin. '
                                'Try a different area.</div>', unsafe_allow_html=True)
                elif end_node is None:
                    st.markdown('<div class="status-error">✕ No road nodes found near destination. '
                                'Try a different area.</div>', unsafe_allow_html=True)
                else:
                    # Convert snapped nodes back to GPS for display
                    nd_s = engine.G.nodes[start_node]
                    nd_e = engine.G.nodes[end_node]
                    s_lon, s_lat = engine.to_gps.transform(nd_s["x"], nd_s["y"])
                    e_lon, e_lat = engine.to_gps.transform(nd_e["x"], nd_e["y"])

                    st.session_state.start_node_gps = (s_lat, s_lon)
                    st.session_state.end_node_gps   = (e_lat, e_lon)

                    # Pre-flight connectivity check
                    if engine.component_map.get(start_node) != engine.component_map.get(end_node):
                        st.markdown(
                            '<div class="status-warning">⚠ These areas are on disconnected road '
                            'segments. Trying nearest connected alternative …</div>',
                            unsafe_allow_html=True)

                    with st.spinner("Running A* pathfinding …"):
                        result = engine.get_route(
                            s_lat, s_lon, e_lat, e_lon,
                            weight_type=weight_type,
                            max_snap_dist_m=snap_dist,
                        )
                    st.session_state.route_result = result
                    st.session_state.sim_count   += 1
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# MAP
# ══════════════════════════════════════════════════════════════════════════════
with col_map:
    result = st.session_state.route_result
    s_gps  = st.session_state.start_node_gps
    e_gps  = st.session_state.end_node_gps

    # Map centre — use midpoint of route if available, else Ahmedabad
    if s_gps and e_gps:
        centre = [(s_gps[0] + e_gps[0]) / 2, (s_gps[1] + e_gps[1]) / 2]
        zoom   = 13
    else:
        centre = [22.607, 72.508]
        zoom   = 12

    m = folium.Map(location=centre, zoom_start=zoom,
                   tiles="CartoDB dark_matter", prefer_canvas=True)

    # Origin marker
    if s_gps:
        folium.CircleMarker(
            location=s_gps, radius=10,
            color="#2ecc71", fill=True, fill_color="#2ecc71", fill_opacity=0.9,
            tooltip=f"Origin · {s_gps[0]:.4f}, {s_gps[1]:.4f}",
        ).add_to(m)
        folium.Marker(
            location=s_gps,
            icon=folium.DivIcon(html=f"""
                <div style="font-family:'Space Grotesk',sans-serif;font-size:11px;
                            color:#2ecc71;font-weight:600;white-space:nowrap;
                            text-shadow:0 0 6px #000;">
                    🟢 {st.session_state.origin_area}
                </div>""", icon_size=(200, 30), icon_anchor=(0, 0)),
        ).add_to(m)

    # Destination marker
    if e_gps:
        folium.CircleMarker(
            location=e_gps, radius=10,
            color="#e74c3c", fill=True, fill_color="#e74c3c", fill_opacity=0.9,
            tooltip=f"Destination · {e_gps[0]:.4f}, {e_gps[1]:.4f}",
        ).add_to(m)
        folium.Marker(
            location=e_gps,
            icon=folium.DivIcon(html=f"""
                <div style="font-family:'Space Grotesk',sans-serif;font-size:11px;
                            color:#e74c3c;font-weight:600;white-space:nowrap;
                            text-shadow:0 0 6px #000;">
                    🔴 {st.session_state.dest_area}
                </div>""", icon_size=(200, 30), icon_anchor=(0, 0)),
        ).add_to(m)

    # Route polyline
    if result and result.get("status") == "success":
        coords = result["route_coords"]
        # Glow layer
        folium.PolyLine(coords, color="#4fc3f7", weight=14, opacity=0.12).add_to(m)
        # Main line
        folium.PolyLine(coords, color="#4fc3f7", weight=4,  opacity=0.95,
                        tooltip="Computed route").add_to(m)

    st.markdown('<div class="map-wrapper">', unsafe_allow_html=True)
    st_folium(m, width="100%", height=560, returned_objects=[])
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# RIGHT PANEL
# ══════════════════════════════════════════════════════════════════════════════
with col_panel:
    result = st.session_state.route_result
    s_gps  = st.session_state.start_node_gps
    e_gps  = st.session_state.end_node_gps

    # Waypoint summary
    origin_str = (f"{s_gps[0]:.5f}, {s_gps[1]:.5f}" if s_gps else "—")
    dest_str   = (f"{e_gps[0]:.5f}, {e_gps[1]:.5f}" if e_gps else "—")
    o_area     = st.session_state.origin_area or "—"
    d_area     = st.session_state.dest_area   or "—"

    st.markdown(f"""
    <div class="coord-box">
        <span class="coord-label">🟢 Origin</span><br>
        {o_area}<br>
        {origin_str}<br><br>
        <span class="coord-label">🔴 Destination</span><br>
        {d_area}<br>
        {dest_str}
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.sim_count > 0:
        st.markdown(
            f'<div class="coord-box"><span class="coord-label">Simulations run</span>'
            f'<br>{st.session_state.sim_count}</div>',
            unsafe_allow_html=True)

    # Result
    if result is None:
        st.markdown(
            '<div class="status-idle">Enter areas above and press <b>Simulate Route</b>.</div>',
            unsafe_allow_html=True)

    elif result["status"] == "success":
        m_data = result["metrics"]
        cong   = m_data["avg_congestion_multiplier"]
        cong_c = "#2ecc71" if cong < 2 else "#f1c40f" if cong < 3.5 else "#e74c3c"

        st.markdown('<div class="status-success">✓ Route simulated successfully</div>',
                    unsafe_allow_html=True)

        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Distance</div>
            <div class="metric-value">{m_data['distance_km']}</div>
            <div class="metric-unit">kilometres</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Est. travel time</div>
            <div class="metric-value">{m_data['estimated_time_mins']}</div>
            <div class="metric-unit">minutes @ 40 km/h</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Congestion index</div>
            <div class="metric-value" style="color:{cong_c};">{cong}×</div>
            <div class="metric-unit">population-weighted proxy</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Road segments</div>
            <div class="metric-value">{m_data['segments_count']}</div>
            <div class="metric-unit">graph edges traversed</div>
        </div>
        """, unsafe_allow_html=True)

        # Re-simulate hint
        st.markdown(
            '<div class="status-idle">Press <b>Simulate Route</b> again for a different '
            'route variation within the same areas.</div>',
            unsafe_allow_html=True)

    elif result["status"] == "warning":
        st.markdown(f'<div class="status-warning">⚠ {result.get("message","")}</div>',
                    unsafe_allow_html=True)
    else:
        msg = result.get("message", "Unknown error")
        if "disconnected" in msg.lower() or "no navigable" in msg.lower():
            msg = ("No path found. These areas may be on disconnected road segments. "
                   "Try areas that are geographically closer or on major roads.")
        st.markdown(f'<div class="status-error">✕ {msg}</div>',
                    unsafe_allow_html=True)