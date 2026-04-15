# Changelog

All notable changes to `dp-system-local-demonstrator` are documented in this file.

## [0.0.3] - unreleased

### Changed
- Switched all model artifact resolution to published online CE-RISE model URLs
- Removed vendored local model artifacts and the local artifact-server path from the demonstrator stack
- Updated demo and validation scripts to match the online-artifacts-only stack layout

## [0.0.2] - 03-27-26

### Changed
- Removed route artifact references and placeholder `route.json` files to match the current (0.0.9) published `hex-core-service` image
- Updated demonstrator checks to rely on core readiness/version endpoints
- Updated the artifact server healthcheck to probe schema artifacts instead of route artifacts

## [0.0.1] - 03-18-26

### Added
- Local demonstrator structure adapted from `dp-system-gitops-template`
- Docker Compose stack for `hex-core-service`, `dp-storage-jsondb-service`, PostgreSQL, and a local artifact server
- Published-image local demo flow with `make` and `./demo.sh` commands
- Deterministic pipeline covering validate, create, read-back, and invalid rejection
- Stable valid and invalid payloads for a fictional `AIKIA LIDEN Chair`
- Vendored local model artifacts for `dp-record-metadata`, `product-profile`, and `usage-and-maintenance`
