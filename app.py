"""
Route Backend API
=================
A lightweight Flask backend that calculates the fastest driving route between
two geographic coordinates using the public OSRM (Open Source Routing Machine) API.

This service is designed for deployment on Azure App Service and for consumption
by external frontends (e.g., web clients, mobile apps).

Author: Javier Lianes García
Version: 1.1
"""

from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import requests
import os

app = Flask(__name__)

# ---------------------------------------------------------------------------
# CORS (habilitado SIEMPRE para simplificar)
# ---------------------------------------------------------------------------
# Permite cualquier origen y maneja preflight automáticamente.
# Si luego quieres restringir, cambia origins="*" por una lista o regex p.ej. r"^https://.*\.vercel\.app$"
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    allow_headers=["Content-Type"],
    methods=["GET", "POST", "OPTIONS"],
    max_age=600,
)

# Respuesta explícita a OPTIONS en /route (algunos proxies/CDN son quisquillosos)
@app.route("/route", methods=["OPTIONS"])
def route_options():
    resp = make_response("", 204)
    origin = request.headers.get("Origin", "*")
    resp.headers["Access-Control-Allow-Origin"] = origin
    resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Vary"] = "Origin"
    return resp

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Default OSRM endpoint (uses public demo server if not overridden)
OSRM_BASE = os.environ.get("OSRM_BASE", "https://router.project-osrm.org")
# Timeout in seconds for OSRM HTTP requests
TIMEOUT = float(os.environ.get("OSRM_TIMEOUT", "15"))

# ---------------------------------------------------------------------------
# Health Check Endpoint
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    """
    Health check endpoint.
    Returns HTTP 200 with {"status": "ok"} when the service is up.
    """
    return {"status": "ok"}

# ---------------------------------------------------------------------------
# Routing Endpoint
# ---------------------------------------------------------------------------
@app.post("/route")
def route():
    """
    Calculate the fastest route between two points using OSRM.

    **Request Body (JSON):**
        {
            "from": [lat1, lon1],
            "to": [lat2, lon2]
        }

    **Response (200 OK):**
        {
            "distance_m": <float>,     # total distance in meters
            "duration_s": <float>,     # total duration in seconds
            "geometry": {              # GeoJSON LineString of the route
                "type": "LineString",
                "coordinates": [[lon, lat], ...]
            }
        }

    **Error Responses:**
        400 - Invalid request body.
        404 - No route found.
        502 - Upstream OSRM failure.
    """
    data = request.get_json(silent=True) or {}

    # Validate input format
    try:
        lat1, lon1 = data["from"]
        lat2, lon2 = data["to"]
    except Exception:
        return jsonify({"error": "Body must include 'from' and 'to' as [lat, lon]"}), 400

    # OSRM expects coordinates as lon,lat
    coords = f"{lon1},{lat1};{lon2},{lat2}"
    url = f"{OSRM_BASE}/route/v1/driving/{coords}"
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "false"
    }

    # Perform the OSRM request
    try:
        r = requests.get(url, params=params, timeout=TIMEOUT)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"OSRM request failed: {e}"}), 502

    if r.status_code != 200:
        return jsonify({"error": "OSRM response error", "status": r.status_code, "body": r.text}), 502

    resp = r.json()
    if "routes" not in resp or not resp["routes"]:
        return jsonify({"error": "No route found"}), 404

    route = resp["routes"][0]

    return jsonify({
        "distance_m": route.get("distance"),
        "duration_s": route.get("duration"),
        "geometry": route.get("geometry")
    })

# ---------------------------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    """
    Run the Flask development server (for local use only).
    In Azure, Gunicorn should be used instead:
        gunicorn -w 2 -k gthread -b 0.0.0.0:$PORT app:app
    """
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
