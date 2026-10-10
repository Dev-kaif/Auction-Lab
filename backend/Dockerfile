FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AUCTIONLAB_DATABASE_URL=sqlite:////data/auctionlab.db

WORKDIR /app

# Install the project and its runtime dependencies from pyproject.toml.
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 auctionlab \
    && mkdir -p /data \
    && chown auctionlab:auctionlab /data

USER auctionlab

EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
