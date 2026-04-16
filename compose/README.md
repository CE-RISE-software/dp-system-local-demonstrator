# Compose Baseline

This directory contains the local demonstrator Compose stack.

Default mode:

- deploy `hex-core-service`
- deploy `dp-storage-jsondb-service` with PostgreSQL persistence
- optionally deploy `re-indicators-calculation-service` for the laptop RE-indicators scenario
- resolve model artifacts from the published online Pages URLs
- run the scripted demonstration through `./demo.sh`

The default auth mode is intentionally local and insecure:

- core uses `AUTH_MODE=none`
- backend uses `AUTH_MODE=disabled`

That mode exists only for this isolated local demonstrator.
