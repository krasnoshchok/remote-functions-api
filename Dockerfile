# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install dependencies into an isolated prefix so they can be copied cleanly
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

# Non-root user (good practice, required by some CF environments)
RUN useradd --no-create-home --shell /bin/false appuser

WORKDIR /app

# Copy installed packages from build stage
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Make sure log directory exists and is writable
RUN mkdir -p logs && chown -R appuser:appuser /app

USER appuser

# Cloud Foundry injects PORT at runtime (default 8080).
# Uvicorn reads it from the shell variable.
ENV PORT=8080

EXPOSE ${PORT}

CMD uvicorn main:app \
      --host 0.0.0.0 \
      --port ${PORT} \
      --workers 1 \
      --log-level info
