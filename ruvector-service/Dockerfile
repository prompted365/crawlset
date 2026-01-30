# Multi-stage Rust build for RuVector service
# Stage 1: Build the Rust binary
FROM rust:1.77-bookworm AS builder

WORKDIR /build

# Copy vendor ruvector source (if available) or use the local crate
COPY Cargo.toml Cargo.lock* ./
COPY src/ ./src/

# Build release binary
RUN cargo build --release

# Stage 2: Runtime image
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the built binary
COPY --from=builder /build/target/release/ruvector-server /usr/local/bin/ruvector-server

# Create data directory
RUN mkdir -p /data/ruvector

# Expose HTTP port
EXPOSE 6333

# Environment defaults
ENV RUVECTOR_HOST=0.0.0.0
ENV RUVECTOR_PORT=6333
ENV RUVECTOR_DATA_DIR=/data/ruvector

# Health check
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:6333/health || exit 1

ENTRYPOINT ["ruvector-server"]
