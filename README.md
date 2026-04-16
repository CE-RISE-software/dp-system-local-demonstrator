# CE-RISE Digital Passport System: Local Demonstrator

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19093662.svg)](https://doi.org/10.5281/zenodo.19093662)

This repository provides a local-only CE-RISE Digital Passport demonstrator adapted from the
`dp-system-gitops-template` structure and aimed at a deterministic Docker-only workflow.

The demo stack runs:

- `hex-core-service`
- `dp-storage-jsondb-service`
- PostgreSQL for backend persistence
- `re-indicators-calculation-service` for the extended laptop scenario

All model artifacts are resolved from the published CE-RISE model pages at runtime. No model
artifacts are vendored locally in this repository.

The scripted demonstration uses a fictional chair product, `AIKIA LIDEN Chair`, and walks through:

1. local stack startup
2. no-auth session initialization
3. valid payload validation
4. record creation and persistence
5. logout and login again
6. stored record read-back through query
7. invalid payload rejection with clear error output

An additional scripted scenario uses a fictional laptop, `Leveto T14 Eco`, and computes all currently
published laptop RE indicators through `re-indicators-calculation-service`.

## Prerequisites

Docker only.

`make` is convenient but optional. Every operation also has a `docker compose` or `./demo.sh` path.

## Quickstart

```bash
cp compose/.env.example compose/.env
make demo
```

Without `make`:

```bash
cp compose/.env.example compose/.env
./demo.sh demo
```

`make demo` starts the stack, runs the full pipeline, and brings the stack down automatically at the end.

To run the RE-indicators extension instead:

```bash
cp compose/.env.example compose/.env
make demo-re-indicators
```

## Auth Handling

Default mode is local no-auth:

- `hex-core-service` uses `AUTH_MODE=none`
- `dp-storage-jsondb-service` uses `AUTH_MODE=disabled`

This keeps the demonstrator Docker-only and deterministic. The demo still shows login/logout steps by
creating, dropping, and recreating a local demo session in the scripted flow. Record recovery after
"re-login" still works because the persisted data is stored in PostgreSQL and queried again through the core.

## Repo Layout

- [`demo.sh`](/home/riccardo/code/CE-RISE-software/dp-system-local-demonstrator/demo.sh)
- [`compose/docker-compose.yml`](/home/riccardo/code/CE-RISE-software/dp-system-local-demonstrator/compose/docker-compose.yml)
- [`compose/.env.example`](/home/riccardo/code/CE-RISE-software/dp-system-local-demonstrator/compose/.env.example)
- [`compose/registry/catalog.json`](/home/riccardo/code/CE-RISE-software/dp-system-local-demonstrator/compose/registry/catalog.json)
- [`payloads/dp_valid.json`](/home/riccardo/code/CE-RISE-software/dp-system-local-demonstrator/payloads/dp_valid.json)
- [`payloads/dp_invalid.json`](/home/riccardo/code/CE-RISE-software/dp-system-local-demonstrator/payloads/dp_invalid.json)
- [`payloads/re-indicators`](/home/riccardo/code/CE-RISE-software/dp-system-local-demonstrator/payloads/re-indicators)

## Commands

```bash
make up
make demo
make demo-re-indicators
make down
make clean
make validate
make validate-re-indicators
```

Equivalent non-`make` wrapper commands:

```bash
./demo.sh up
./demo.sh demo
./demo.sh demo-re-indicators
./demo.sh down
./demo.sh clean
./demo.sh validate
./demo.sh validate-re-indicators
```

Direct stack-management commands with `docker compose`:

```bash
docker compose -f compose/docker-compose.yml --env-file compose/.env up -d postgres dp-storage-jsondb-service hex-core-service
docker compose -f compose/docker-compose.yml --env-file compose/.env up -d postgres dp-storage-jsondb-service hex-core-service re-indicators-calculation-service
docker compose -f compose/docker-compose.yml --env-file compose/.env down --remove-orphans
docker compose -f compose/docker-compose.yml --env-file compose/.env down --remove-orphans --volumes
docker compose -f compose/docker-compose.yml --env-file compose/.env ps
docker compose -f compose/docker-compose.yml --env-file compose/.env logs -f
```

Command behavior:

- `make demo` or `./demo.sh demo` runs the pipeline and then shuts the stack down automatically
- `make demo-re-indicators` or `./demo.sh demo-re-indicators` runs the laptop RE-indicators pipeline and then shuts the stack down automatically
- `make validate` or `./demo.sh validate` runs smoke checks and then shuts the stack down automatically
- `make validate-re-indicators` or `./demo.sh validate-re-indicators` runs smoke checks for the RE-indicators path and then shuts the stack down automatically
- `make up` or `./demo.sh up` leaves the stack running for inspection

## Payload Modeling

The default valid payload is a composite record built around:

- `dp-record-metadata` as the record framing layer
- `product-profile` as the product identity/content layer
- `usage-and-maintenance` as accessory lifecycle information

The demo operation itself targets the `dp-record-metadata` model/version, while the accessory model data is
nested in the payload and declared in `applied_schemas`.

## RE Indicators Scenario

The extended scenario uses the fictional laptop `Leveto T14 Eco` and the published
`re-indicators-specification` model.

It computes all currently supported laptop indicators:

- `REcycle_Laptop`
- `REfurbish_Laptop`
- `REmanufacture_Laptop`
- `REpair_Laptop`
- `REuse_Laptop`

The demonstrator calls the published `re-indicators-calculation-service` image locally and prints the
returned total score for each indicator. The invalid case uses an unknown
`indicator_specification_id`, which the published service rejects deterministically.

## Inspecting Logs and Persistence

Service logs:

```bash
docker compose -f compose/docker-compose.yml --env-file compose/.env logs -f
```

Check service status:

```bash
docker compose -f compose/docker-compose.yml --env-file compose/.env ps
```

Persistence is backed by the named volume `postgres_data`. The record created in the demo remains available
across `make down` and is removed only by `make clean`.

## Teardown

Stop services:

```bash
make down
```

Stop services and delete volumes:

```bash
make clean
```

`make clean` is destructive and removes the persisted backend data.

## Troubleshooting

- Port conflict on `8080`, `8081`, `8083`, or `5432`: adjust values in [`compose/.env.example`](/home/riccardo/code/CE-RISE-software/dp-system-local-demonstrator/compose/.env.example) and regenerate `compose/.env`.
- Core not ready: inspect `hex-core-service` logs.
- Backend not ready: inspect `dp-storage-jsondb-service` and `postgres` logs.
- RE-indicators path not ready: inspect `re-indicators-calculation-service` logs and confirm port `8083` is free.
- Invalid RE-indicators payload passes unexpectedly: verify the invalid payload still uses an unknown `indicator_specification_id`.
- On hosts using `podman-compose` through `docker compose`, the stack start command may return non-zero even when the services do come up; the validation and demo scripts therefore judge success by actual service availability.

---

<a href="https://europa.eu" target="_blank" rel="noopener noreferrer">
  <img src="https://ce-rise.eu/wp-content/uploads/2023/01/EN-Funded-by-the-EU-PANTONE-e1663585234561-1-1.png" alt="EU emblem" width="200"/>
</a>

Funded by the European Union under Grant Agreement No. 101092281 — CE-RISE.  
Views and opinions expressed are those of the author(s) only and do not necessarily reflect those of the European Union or the granting authority (HADEA).
Neither the European Union nor the granting authority can be held responsible for them.

© 2026 CE-RISE consortium.  
Licensed under the [European Union Public Licence v1.2 (EUPL-1.2)](LICENSE).  
Attribution: CE-RISE project (Grant Agreement No. 101092281) and the individual authors/partners as indicated.

<a href="https://www.nilu.com" target="_blank" rel="noopener noreferrer">
  <img src="https://nilu.no/wp-content/uploads/2023/12/nilu-logo-seagreen-rgb-300px.png" alt="NILU logo" height="20"/>
</a>

Developed by NILU (Riccardo Boero — ribo@nilu.no) within the CE-RISE project.
