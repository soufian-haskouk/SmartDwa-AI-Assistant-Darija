FROM python:3.12-slim
WORKDIR /srv
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./backend/app
COPY scripts ./scripts
COPY eval ./eval
ENV PROJECT_ROOT=/srv DATA_DIR=/data PYTHONUNBUFFERED=1
WORKDIR /srv/backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
