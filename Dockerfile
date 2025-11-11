# ----------------------------------------------------------
# Stage 1: Build OSRM dataset optimized for shortest distance
# ----------------------------------------------------------
FROM osrm/osrm-backend:latest AS osrm

# Change routing profile from "duration" to "distance"
RUN sed -i "s/weight_name = 'duration'/weight_name = 'distance'/" /opt/car.lua

# Download OpenStreetMap data (Spain region example)
WORKDIR /data
RUN wget -q https://download.geofabrik.de/europe/spain-latest.osm.pbf

# Preprocess map data using the modified profile
RUN osrm-extract -p /opt/car.lua spain-latest.osm.pbf && \
    osrm-partition spain-latest.osrm && \
    osrm-customize spain-latest.osrm

# ----------------------------------------------------------
# Stage 2: Final runtime image with Flask + OSRM
# ----------------------------------------------------------
FROM python:3.11-slim

WORKDIR /app
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir flask flask-cors requests gunicorn

# Copy preprocessed OSRM data from the previous stage
COPY --from=osrm /data /data

# Expose Flask and OSRM ports
EXPOSE 5000 5001

# Start both OSRM and Flask API
CMD osrm-routed /data/spain-latest.osrm --port 5001 --algorithm=MLD & \
    gunicorn -w 2 -k gthread -b 0.0.0.0:$PORT app:app
