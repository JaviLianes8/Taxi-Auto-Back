# ----------------------------------------------------------
# Stage 1: Build OSRM dataset optimized for shortest distance
# ----------------------------------------------------------
FROM osrm/osrm-backend:latest AS osrm

# Modify the default car.lua profile to use "distance" instead of "duration"
RUN sed -i "s/weight_name = 'duration'/weight_name = 'distance'/" /opt/car.lua

# Download OpenStreetMap data (Spain region as example)
WORKDIR /data
RUN wget -q https://download.geofabrik.de/europe/spain-latest.osm.pbf

# Preprocess OSM data with the modified profile
# This generates the .osrm files needed by osrm-routed
RUN osrm-extract -p /opt/car.lua spain-latest.osm.pbf && \
    osrm-partition spain-latest.osrm && \
    osrm-customize spain-latest.osrm

# ----------------------------------------------------------
# Stage 2: Final image with Flask backend + OSRM runtime
# ----------------------------------------------------------
FROM python:3.11-slim

WORKDIR /app
COPY . /app

# Install Python dependencies (Flask backend)
RUN pip install --no-cache-dir flask flask-cors requests gunicorn

# Copy preprocessed OSRM data from the build stage
COPY --from=osrm /data /data

# Expose Flask (5000) and OSRM (5001) ports
EXPOSE 5000 5001

# Start both OSRM (shortest-distance mode) and Flask API
CMD osrm-routed /data/spain-latest.osrm --port 5001 --algorithm=MLD & \
    gunicorn -w 2 -k gthread -b 0.0.0.0:5000 app:app
