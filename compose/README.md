# Compose Baseline

This directory contains the local demonstrator Compose stack.

Default mode:

- deploy `hex-core-service`
- deploy `dp-storage-jsondb-service` with PostgreSQL persistence
- serve vendored local model artifacts through `artifact-server`
- run the scripted demonstration through `demo-runner`

The default auth mode is intentionally local and insecure:

- core uses `AUTH_MODE=none`
- backend uses `AUTH_MODE=disabled`

That mode exists only for this isolated local demonstrator.
