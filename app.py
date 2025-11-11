"""
Route Backend API
=================
A lightweight Flask backend that calculates the *shortest* driving route (by
distance in meters) between two geographic coordinates using the public OSRM
(Open Source Routing Machine) API.

This service is designed for deployment on Azure App Service and for consumption
by external frontends (e.g., web clients, mobile apps).

Author: Javier Lianes García
Version: 1.2
"""

from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import requests
import os
from math import inf

app = Flask(__name__)

# ---------------------------------------------------------------------------
# CORS (enabled ALWAYS for simplicity)
# ---------------------------------------------------------------------------
# Allows any origin and handles preflight automatically.
# If you want to restrict later, change origins="*" to a list or regex, e.g. r"^https://.*\\.vercel\\.app$"
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    allow_headers=["Content-Type"],
    methods=["GET", "POST", "OPTIONS"],
    max_age=600,
)

# Explicit OPTIONS response on /route (some proxies/CDNs are picky)
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
# Default OSRM endpoint (uses the public demo server if not overridden)
OSRM_BASE = os.environ.get("OSRM_BASE", "https://router.project-osrm.org")
# Timeout in seconds for OSRM HTTP requests
TIMEOUT = float(os.environ.get("OSRM_TIMEOUT", "15"))
# Whether to request alternatives from OSRM to pick the shortest one
REQUEST_ALTERNATIVES = os.environ.get("OSRM_ALTERNATIVES", "true").lower() in ("1", "true", "yes")

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
# Routing Endpoint (returns the SHORTEST route by distance)
# ---------------------------------------------------------------------------
@app.post("/route")
def route():
    """
    Calculate the shortest route (by distance in meters) between two points
    using OSRM. The API contract (endpoint & response shape) is preserved.

    **Request Body (JSON):**
        {
            "from": [lat1, lon1],
            "to": [lat2, lon2]
        }

    **Response (200 OK):**
        {
            "distance_m": <float>,     # total distance in meters (shortest among alternatives)
            "duration_s": <float>,     # total duration in seconds (for the chosen shortest route)
            "geometry": {              # GeoJSON LineString of the chosen route
                "type": "LineString",
                "coordinates": [[lon, lat], ...]
            }
        }

    **Error Responses:**
        400 - Invalid request body.
        404 - No route found.
        502 - Upstream OSRM failure.

    **Implementation note:**
        - This endpoint requests OSRM route alternatives and selects the one
          with the minimum `distance`. On the public OSRM server, "alternatives"
          are not guaranteed to include the absolute globally-shortest path,
          but in practice this yields the shortest among the provided options.
        - For a hard guarantee of shortest-by-distance, you must run your own
          OSRM instance with a distance-weighted profile (weight_name="distance").
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

    # Ask for alternatives to be able to choose the shortest by distance
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "false",
        # true = OSRM returns 1..N routes; we will pick the one with min distance
        "alternatives": "true" if REQUEST_ALTERNATIVES else "false",
    }

    # Perform the OSRM request
    try:
        r = requests.get(url, params=params, timeout=TIMEOUT)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"OSRM request failed: {e}"}), 502

    if r.status_code != 200:
        return jsonify({"error": "OSRM response error", "status": r.status_code, "body": r.text}), 502

    resp = r.json()
    routes = resp.get("routes") or []
    if not routes:
        return jsonify({"error": "No route found"}), 404

    # Choose the route with the smallest distance (meters)
    shortest = min(routes, key=lambda rt: rt.get("distance", inf))

    return jsonify({
        "distance_m": shortest.get("distance"),
        "duration_s": shortest.get("duration"),
        "geometry": shortest.get("geometry")
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