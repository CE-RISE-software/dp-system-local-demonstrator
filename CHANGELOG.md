# Changelog

All notable changes to `dp-system-local-demonstrator` are documented in this file.

## [0.0.3] - 04-16-26

### Added
- Added the `re-indicators-calculation-service` extension with laptop payloads for all published laptop indicators
- Added `demo-re-indicators` and `validate-re-indicators` operator commands

### Changed
- Switched all model artifact resolution to published online CE-RISE model URLs
- Removed vendored local model artifacts and the local artifact-server path from the demonstrator stack
- Updated demo and validation scripts to match the online-artifacts-only stack layout
- Corrected the published RE-indicators service port mapping to `8081`
- Replaced broken `curl`-based container healthchecks with process healthchecks compatible with the published images
- Reduced podman-compose teardown and retry noise in the demo and validation output

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
