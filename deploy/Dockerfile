# ── Cloud Deploy ──────────────────────────────────────────────────────
# Thin web UI + config generator layer on top of the published
# auto-archiver Docker image. Used by the Railway one-click deploy.
#
# Build:
#   docker build -f deploy/Dockerfile -t auto-archiver-deploy .
#
# Run:
#   docker run -p 8080:8080 -e PORT=8080 -e AUTH_PASSWORD=secret auto-archiver-deploy
# ──────────────────────────────────────────────────────────────────────

FROM bellingcat/auto-archiver:latest

USER root

# Install the lightweight web layer dependencies
RUN pip install --no-cache-dir fastapi uvicorn[standard] python-multipart pyyaml

# Copy deploy scripts into the image
COPY deploy/ /app/deploy/

# Ensure writable dirs exist
RUN mkdir -p /app/local_archive /app/secrets && \
    chown -R 1000:1000 /app/local_archive /app/secrets /app/deploy

USER 1000

# Railway sets PORT; default to 8080
ENV PORT=8080

EXPOSE ${PORT}

# Override the CLI entrypoint with the web server
ENTRYPOINT ["python3", "-m", "deploy.start"]
