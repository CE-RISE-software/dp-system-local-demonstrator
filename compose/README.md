# Compose Baseline

This directory contains the local demonstrator Compose stack.

Default mode:

- deploy `hex-core-service`
- deploy `dp-storage-jsondb-service` with PostgreSQL persistence
- optionally deploy `re-indicators-calculation-service` for the laptop RE-indicators scenario
- optionally enable the `see-impacts` profile for the PV calculation scenario
- resolve model artifacts from the published online Pages URLs
- run the scripted demonstration through `./demo.sh`

The default auth mode is intentionally local and insecure:

- core uses `AUTH_MODE=none`
- backend uses `AUTH_MODE=disabled`

That mode exists only for this isolated local demonstrator.

Use `make demo-see-impacts` from the repository root for the complete PV workflow, or
`make validate-see-impacts` for readiness and schema checks without a numerical calculation.
The SEE host port is loopback-only at `127.0.0.1:8084`; the demo client connects over the internal
Compose network. Existing `compose/.env` files are preserved.
