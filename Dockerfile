# syntax=docker/dockerfile:1
# SAT-SA multi-stage offline build (TASK 8.3).
# Stage 1 installs from pre-downloaded local wheels only (--no-index).
# Stage 2 runs as non-root with a read-only root filesystem.

FROM python:3.11-slim AS builder
WORKDIR /build
COPY packaging/wheels/ ./packaging/wheels/
COPY requirements.txt pyproject.toml README.md ./
COPY server/src/ ./server/src/
RUN pip install --no-index --find-links packaging/wheels -e .[lite] \
 && pip install --no-index --find-links packaging/wheels -r requirements-dev.txt \
 && python -m compileall -q server/src/satsa

FROM python:3.11-slim AS runtime
RUN useradd --uid 1000 --create-home satsa
USER 1000
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/satsa /usr/local/bin/satsa
COPY --chown=1000:1000 server/src/ ./server/src/
COPY --chown=1000:1000 configs/ ./configs/
VOLUME ["/data", "/models", "/configs"]
ENTRYPOINT ["satsa"]
CMD ["run"]
