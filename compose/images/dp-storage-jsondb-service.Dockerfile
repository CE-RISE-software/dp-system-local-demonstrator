ARG DP_STORAGE_BASE_IMAGE
FROM ${DP_STORAGE_BASE_IMAGE}

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

USER appuser
