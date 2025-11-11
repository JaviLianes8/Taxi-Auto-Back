"""
Route Backend API
=================
A lightweight Flask backend that calculates the shortest driving route between
two geographic coordinates using an internal OSRM (Open Source Routing Machine) server.

Designed for deployment on Azure App Service as a Docker container.
Can also work with the public OSRM server if desired.

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
# Allow all origins for simplicity.
# If you want to restrict, replace "*" with a specific domain or regex.
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    allow_headers=["Content-Type"],
    methods=["GET", "POST", "OPTIONS"],
    max_age=600,
)

# Explicit OPTIONS handler for /route (helps with some CDNs and proxies)
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
# CONFIGURATION
# ---------------------------------------------------------------------------
# Default OSRM endpoint (uses local OSRM running on port 5001)
# You can override it using an environment variable OSRM_BASE
OSRM_BASE = os.environ.get("OSRM_BASE", "http://localhost:5001")
# Timeout in seconds for OSRM HTTP requests
TIMEOUT = float(os.environ.get("OSRM_TIMEOUT", "15"))

# ---------------------------------------------------------------------------
# HEALTH CHECK ENDPOINT
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    """
    Simple health check endpoint.
    Returns HTTP 200 with {"status": "ok"} if the service is running.
    """
    return {"status": "ok"}

# ---------------------------------------------------------------------------
# ROUTING ENDPOINT
# ---------------------------------------------------------------------------
@app.post("/route")
def route():
    """
    Calculate the shortest route between two points using OSRM.

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
        400 - Invalid request body
        404 - No route found
        502 - OSRM request failed
    """
    data = request.get_json(silent=True) or {}

    # Validate JSON input format
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

    # Call OSRM backend
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
# APP ENTRY POINT
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    """
    Run Flask development server (for local testing only).
    In Azure, Gunicorn (defined in Dockerfile) is used instead.
    """
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
