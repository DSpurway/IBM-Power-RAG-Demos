# Multi-stage build for RAG Backend Service with OpenSearch
# NOTE: uses python:3.12-slim (Debian) not UBI9 — avoids Quay CDN IPv6 issue
#       on TechZone pok-systems VMs. Path: /usr/local/lib/python3.12/site-packages
FROM python:3.12-slim AS builder

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    make \
    python3-dev \
    libopenblas-dev \
    liblcms2-dev \
    libfreetype6-dev \
    libjpeg62-turbo-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
# Use IBM Power-optimized wheels where available for better performance
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --prefer-binary \
        torch==2.9.1 \
        torchvision==0.24.1 \
        sentence-transformers \
        transformers \
        lxml \
        numpy \
        --extra-index-url=https://wheels.developerfirst.ibm.com/ppc64le/linux/+simple/ && \
    grep -Ev "^(torch|torchvision|sentence-transformers|transformers|huggingface-hub|tokenizers|lxml|numpy)" requirements.txt > requirements-base.txt && \
    pip install --no-cache-dir --prefer-binary -r requirements-base.txt \
        --extra-index-url=https://wheels.developerfirst.ibm.com/ppc64le/linux/+simple/ && \
    mkdir -p /app/docling-models

# Copy application code
COPY app.py .
COPY web_scraper.py .
COPY docling_config.py .
COPY token_utils.py .
COPY docling_converter.py .
COPY hierarchical_chunker.py .
COPY sales_manual_chunker.py .
COPY query_classifier.py .
COPY watson_assistant_service.py .
COPY table_lookup_service.py .
COPY server_mtm_mapper.py .
COPY reranker_service.py .
COPY activation_feature_service.py .
COPY physical_feature_service.py .

# Create PDF directory and copy sample PDFs
RUN mkdir -p /app/pdfs
COPY pdfs/*.pdf /app/pdfs/

# ============================================================================
# Production Stage
# ============================================================================
FROM python:3.12-slim

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application
COPY --from=builder /app/app.py .
COPY --from=builder /app/web_scraper.py .
COPY --from=builder /app/docling_config.py .
COPY --from=builder /app/token_utils.py .
COPY --from=builder /app/docling_converter.py .
COPY --from=builder /app/hierarchical_chunker.py .
COPY --from=builder /app/sales_manual_chunker.py .
COPY --from=builder /app/query_classifier.py .
COPY --from=builder /app/watson_assistant_service.py .
COPY --from=builder /app/table_lookup_service.py .
COPY --from=builder /app/server_mtm_mapper.py .
COPY --from=builder /app/reranker_service.py .
COPY --from=builder /app/activation_feature_service.py .
COPY --from=builder /app/physical_feature_service.py .
COPY --from=builder /app/pdfs /app/pdfs

# Environment variables with defaults
ENV OPENSEARCH_HOST=opensearch-service \
    OPENSEARCH_PORT=9200 \
    OPENSEARCH_USERNAME=admin \
    OPENSEARCH_PASSWORD=admin \
    OPENSEARCH_DB_PREFIX=rag \
    OPENSEARCH_INDEX_NAME=default \
    OPENSEARCH_NUM_SHARDS=1 \
    LLAMA_HOST=llama-service \
    LLAMA_PORT=8080 \
    PDF_DIR=/app/pdfs \
    DOCLING_MODELS_PATH=/app/docling-models \
    USE_DOCLING=false \
    ENABLE_TABLES=true \
    ENABLE_OCR=false \
    DOCLING_CHUNK_SIZE=768 \
    DOCLING_CHUNK_OVERLAP=50 \
    PDF_CHUNK_SIZE=100 \
    CORS_ORIGIN=* \
    PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=5)"

# Run with gunicorn for production
# Timeout set to 1800s (30 minutes) to allow for large Sales Manual chunking and embedding
# Using 1 worker to ensure consistent responses (no worker-level caching issues)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "1800", "--access-logfile", "-", "--error-logfile", "-", "app:app"]