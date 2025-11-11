# --- API (Flask) image ---
FROM python:3.11-slim

WORKDIR /app
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir flask flask-cors requests gunicorn

EXPOSE 8088

# Run API with gunicorn
CMD gunicorn -w 2 -k gthread -b 0.0.0.0:8088 app:app
