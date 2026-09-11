FROM python:3.11-slim

WORKDIR /app

# System deps for psycopg (build fallback) and sentence-transformers' torch
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
# CPU-only torch first: the default PyPI wheel bundles CUDA and balloons
# the image to ~10GB, which won't fit on Render's free tier. sentence-
# transformers then reuses this already-installed torch instead of
# pulling the CUDA build itself.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY config ./config

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
