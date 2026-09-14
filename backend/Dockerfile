FROM python:3.11-slim

WORKDIR /app

# System deps for psycopg (build fallback) and curl for the embedding
# model download below.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Bake the ONNX embedding model + tokenizer into the image at build time
# instead of downloading them from Hugging Face on a cold start — a fresh
# Render instance would otherwise pay a ~90MB download before it can
# answer its first request. app/embeddings/service.py falls back to
# downloading lazily into this same path if it's ever missing (e.g. local
# dev outside Docker, or EMBEDDING_MODEL overridden to something else).
ARG EMBEDDING_MODEL=all-MiniLM-L6-v2
RUN mkdir -p /app/models/${EMBEDDING_MODEL} \
    && curl -sL -o /app/models/${EMBEDDING_MODEL}/model.onnx \
        https://huggingface.co/sentence-transformers/${EMBEDDING_MODEL}/resolve/main/onnx/model.onnx \
    && curl -sL -o /app/models/${EMBEDDING_MODEL}/tokenizer.json \
        https://huggingface.co/sentence-transformers/${EMBEDDING_MODEL}/resolve/main/tokenizer.json

COPY app ./app
COPY config ./config

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
