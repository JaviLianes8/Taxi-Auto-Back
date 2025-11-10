# Azure Route Backend (OSRM, no traffic)

A lightweight **API-only** backend that returns the **fastest driving route** between two geographic coordinates using **OSRM** (Open Source Routing Machine).  
Designed for **Azure App Service (Linux)** and intended to be consumed by an **external frontend** (different origin/domain).

---

## Endpoints

### `POST /route`
Calculates the fastest route (no live traffic data).

**Request Body (JSON):**
```json
{ "from": [lat, lon], "to": [lat, lon] }
```

**Response (200):**
```json
{
  "distance_m": 7750.3,
  "duration_s": 769.3,
  "geometry": { "type": "LineString", "coordinates": [[lon, lat], ...] }
}
```

**Error Codes:**
- `400` – Invalid body (must include `from` and `to` as `[lat, lon]`).
- `404` – No route found.
- `502` – OSRM service failed or timed out.

### `GET /health`
Returns `{"status": "ok"}` to confirm service availability.

---

## Environment Variables

| Variable | Description | Default |
|-----------|--------------|----------|
| `OSRM_BASE` | URL of the OSRM routing server | `https://router.project-osrm.org` |
| `OSRM_TIMEOUT` | Timeout (in seconds) for OSRM requests | `15` |
| `ENABLE_CORS` | Set to `1` to enable CORS (requires `flask-cors`) | Disabled |
| `CORS_ORIGINS` | Allowed origins for CORS | `*` |

---

## Running Locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt

# (Optional) Enable CORS for your frontend
# Windows CMD
set ENABLE_CORS=1
set CORS_ORIGINS=http://localhost:3000

# Run in dev mode
python app.py
# Open: http://localhost:5000/health
```

Quick test:
```bash
curl -X POST http://localhost:5000/route -H "Content-Type: application/json" -d "{\"from\":[40.4066,-3.6893],\"to\":[40.4723,-3.6834]}"
```

---

# Deploying on Azure App Service (Linux)

## Quick Setup via Azure CLI

1. **Login and create/update the app**
   ```bash
   az login
   cd azure-route-backend

   # create the web app (choose a unique global name)
   az webapp up --runtime "PYTHON:3.11" --sku B1 --location "westeurope" --name UNIQUE_APP_NAME
   ```

2. **Configure the startup command (Gunicorn)**
   ```bash
   az webapp config set \
     --name UNIQUE_APP_NAME \
     --resource-group RESOURCE_GROUP_NAME \
     --startup-file "gunicorn -w 2 -k gthread -b 0.0.0.0:$PORT app:app"
   ```

3. **(Optional) Environment variables (CORS, OSRM, etc.)**
   ```bash
   az webapp config appsettings set \
     --name UNIQUE_APP_NAME \
     --resource-group RESOURCE_GROUP_NAME \
     --settings ENABLE_CORS=1 CORS_ORIGINS=https://your-frontend.com
   ```

4. **Deploy via ZIP when you update the code**
   ```bash
   az webapp deploy --resource-group RESOURCE_GROUP_NAME --name UNIQUE_APP_NAME --src-path . --type zip
   ```

5. **Test your deployment**
   - Health: `https://UNIQUE_APP_NAME.azurewebsites.net/health`
   - Route: `POST https://UNIQUE_APP_NAME.azurewebsites.net/route`

---

## Production Notes

- **Workers**: Adjust `-w` in the Gunicorn command based on CPU/RAM (e.g. `-w 4`).
- **Networking**: Ensure outbound HTTPS access to `OSRM_BASE` if using a restricted VNet.
- **Logs:**
  ```bash
  az webapp log config -g RESOURCE_GROUP_NAME -n UNIQUE_APP_NAME --application-logging true --level information
  az webapp log tail   -g RESOURCE_GROUP_NAME -n UNIQUE_APP_NAME
  ```

---

# Frontend Consumption Example

### Example using JavaScript `fetch()`
```js
async function getRoute(fromLat, fromLon, toLat, toLon) {
  const res = await fetch("https://UNIQUE_APP_NAME.azurewebsites.net/route", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ from: [fromLat, fromLon], to: [toLat, toLon] }),
  });
  if (!res.ok) throw new Error("Route error: " + res.status);
  return await res.json();
}

// Usage example
getRoute(40.4066, -3.6893, 40.4723, -3.6834).then(data => {
  console.log("Distance (km):", (data.distance_m / 1000).toFixed(1));
  // data.geometry is a GeoJSON LineString -> draw on your map
});
```

### CORS Notes
- If your frontend is hosted on another domain, set:
  - `ENABLE_CORS=1`
  - `CORS_ORIGINS=https://your-frontend.com` (multiple values allowed, comma-separated).
- If your frontend is behind a proxy/gateway, handle CORS there instead of Flask.

---

## Project Structure
```
azure-route-backend/
├─ app.py
├─ requirements.txt
└─ README.md
```
