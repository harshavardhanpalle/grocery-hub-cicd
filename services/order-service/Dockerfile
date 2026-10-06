FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 DB_PATH=/data/order.db
# Apply Debian security patches so the Trivy gate passes
RUN apt-get update && apt-get -y upgrade && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 app && mkdir /data && chown app /data
COPY --from=builder /install /usr/local
WORKDIR /app
COPY main.py .
USER app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
