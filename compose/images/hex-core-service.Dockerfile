FROM rust:1-slim AS builder

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends pkg-config libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY vendor/hex-core-service/Cargo.toml vendor/hex-core-service/Cargo.lock ./
COPY vendor/hex-core-service/crates crates/

RUN cargo build --release -p hex-api

FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --no-create-home --shell /bin/false app

COPY --from=builder /build/target/release/hex-api /usr/local/bin/hex-core-service

USER app

EXPOSE 8080

ENTRYPOINT ["hex-core-service"]
