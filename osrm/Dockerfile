# --- OSRM (Madrid) con perfil por DISTANCIA ---
FROM osrm/osrm-backend:latest AS osrm

# Copia un perfil car a trabajo
RUN set -eux; \
    SRC="/opt/car.lua"; \
    [ -f /opt/profiles/car.lua ] && SRC="/opt/profiles/car.lua" || true; \
    cp "$SRC" /opt/car-distance.lua; \
    # 1) Poner weight_name='distance' robusto para ambas formas
    sed -ri "s/(^|[^a-zA-Z_])weight_name\s*=\s*'[^']+'/\1weight_name = 'distance'/" /opt/car-distance.lua; \
    sed -ri "s/(^|[^a-zA-Z_])properties\.weight_name\s*=\s*'[^']+'/\1properties.weight_name = 'distance'/" /opt/car-distance.lua; \
    # 2) Quitar penalizaciones típicas
    sed -ri "s/(u_turn_penalty\s*=\s*)[0-9]+/\10/" /opt/car-distance.lua; \
    sed -ri "s/(traffic_light_penalty\s*=\s*)[0-9]+/\10/" /opt/car-distance.lua; \
    # 3) Forzar velocidad constante al final de process_way
    #   Insertamos tras la línea que define process_way si no existe
    grep -q 'result.forward_speed = 1' /opt/car-distance.lua || \
      awk '1; /function process_way/ {ins=1} ins && /end/ && !done {print "  result.forward_speed = 1"; print "  result.backward_speed = 1"; done=1}' /opt/car-distance.lua > /opt/car-distance.tmp && \
      mv /opt/car-distance.tmp /opt/car-distance.lua

WORKDIR /data
ADD https://download.geofabrik.de/europe/spain/madrid-latest.osm.pbf /data/madrid-latest.osm.pbf

RUN osrm-extract -p /opt/car-distance.lua madrid-latest.osm.pbf && \
    osrm-partition madrid-latest.osrm && \
    osrm-customize madrid-latest.osrm

EXPOSE 5001
CMD ["osrm-routed","/data/madrid-latest.osrm","--port","5001","--algorithm=MLD"]
