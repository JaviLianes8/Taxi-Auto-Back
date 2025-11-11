# ----------------------------------------------------------
# Stage 1: Build OSRM dataset optimized for shortest distance
# ----------------------------------------------------------
FROM osrm/osrm-backend:latest AS osrm

# Use shortest path (distance) instead of fastest (duration)
RUN sed -i "s/weight_name = 'duration'/weight_name = 'distance'/" /opt/car.lua

# Download OpenStreetMap data for the Madrid region (smaller & faster)
WORKDIR /data
RUN wget -q https://download.geofabrik.de/europe/spain/madrid-latest.osm.pbf

# Preprocess OSM data (build the graph)
RUN osrm-extract -p /opt/car.lua madrid-latest.osm.pbf && \
    osrm-partition madrid-latest.osrm && \
    osrm-customize madrid-latest.osrm

# ----------------------------------------------------------
# Stage 2: Final runtime with Flask + OSRM
# ----------------------------------------------------------
FROM python:3.11-slim

WORKDIR /app
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir flask flask-cors requests gunicorn

# Copy preprocessed OSRM data
COPY --from=osrm /data /data

# Expose Flask and OSRM ports (Flask: 8088, OSRM: 5001)
EXPOSE 8088 5001

# Launch both servers
CMD osrm-routed /data/madrid-latest.osrm --port 5001 --algorithm=MLD & \
    gunicorn -w 2 -k gthread -b 0.0.0.0:8088 app:app
