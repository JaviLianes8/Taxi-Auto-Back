"""
Route Backend API
=================
Flask backend that calculates the **shortest** driving route (by distance)
between two geographic coordinates using a local OSRM server.

Author: Javier Lianes García
Version: 1.1
"""

from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import requests
import os

app = Flask(__name__)

# ---------------------------------------------------------------------------
# CORS CONFIGURATION
# ---------------------------------------------------------------------------
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    allow_headers=["Content-Type"],
    methods=["GET", "POST", "OPTIONS"],
    max_age=600,
)

@app.route("/route", methods=["OPTIONS"])
def route_options():
    """Handle preflight requests (for browsers / CDNs)"""
    resp = make_response("", 204)
    origin = request.headers.get("Origin", "*")
    resp.headers["Access-Control-Allow-Origin"] = origin
    resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Vary"] = "Origin"
    return resp

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
OSRM_BASE = os.environ.get("OSRM_BASE", "http://localhost:5001")
TIMEOUT = float(os.environ.get("OSRM_TIMEOUT", "15"))

# ---------------------------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    """Simple check to confirm the service is alive."""
    return {"status": "ok"}

# ---------------------------------------------------------------------------
# ROUTE ENDPOINT
# ---------------------------------------------------------------------------
@app.post("/route")
def route():
    """Calculate the shortest route using OSRM (distance-based profile)."""
    data = request.get_json(silent=True) or {}

    try:
        lat1, lon1 = data["from"]
        lat2, lon2 = data["to"]
    except Exception:
        return jsonify({"error": "Body must include 'from' and 'to' as [lat, lon]"}), 400

    coords = f"{lon1},{lat1};{lon2},{lat2}"
    url = f"{OSRM_BASE}/route/v1/driving/{coords}"
    params = {"overview": "full", "geometries": "geojson", "steps": "false"}

    try:
        r = requests.get(url, params=params, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"OSRM request failed: {e}"}), 502

    resp = r.json()
    routes = resp.get("routes", [])
    if not routes:
        return jsonify({"error": "No route found"}), 404

    route = routes[0]
    return jsonify({
        "distance_m": route.get("distance"),
        "duration_s": route.get("duration"),
        "geometry": route.get("geometry")
    })

# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8088"))  # 👈 custom port (for router)
    app.run(host="0.0.0.0", port=port, debug=False)
