# One reviewed, digest-pinned multi-architecture Python 3.12 base for both stages.
ARG PYTHON_IMAGE=python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c
FROM ${PYTHON_IMAGE} AS build
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
WORKDIR /app
RUN python -m pip install --no-cache-dir uv==0.10.0
COPY pyproject.toml uv.lock ./
COPY app/ ./app/
RUN uv sync --frozen --no-dev --no-editable --python /usr/local/bin/python

FROM ${PYTHON_IMAGE} AS runtime
RUN groupadd --gid 10001 axiom && \
    useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin axiom
WORKDIR /app
COPY --from=build --chown=10001:10001 /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    AXIOM_BIND_HOST=0.0.0.0 \
    AXIOM_PORT=8000
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "app.api"]
