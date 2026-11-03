# CE-RISE Digital Passport System: Local Demonstrator

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19093662.svg)](https://doi.org/10.5281/zenodo.19093662)

This repository provides a local-only CE-RISE Digital Passport demonstrator adapted from the
`dp-system-gitops-template` structure, using published service images and deterministic scripted workflows.

The demo stack runs:

- `hex-core-service`
- `dp-storage-jsondb-service`
- PostgreSQL for backend persistence
- `re-indicators-calculation-service` for the extended laptop scenario
- `see-impacts-calculation-service` for the photovoltaic (PV) scenario

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

The PV scenario validates Product System and LCI Dataset records through HEX Core, calculates all
25 configured impact indicators in one request, compares them with the published reference, and
persists and reads back the complete Integrated LCA result through the backend.

## Prerequisites

Bash and Docker with Compose. The chair and RE-indicators shell flows also use `curl`, `jq`, and
`timeout` on the host. The SEE request client runs inside the existing demo-runner container and
does not require host Python or an installed calculation library.

`make` is convenient but optional. Every operation also has a `docker compose` or `./demo.sh` path.

## Quickstart

```bash
make demo
```

Without `make`:

```bash
./demo.sh demo
```

`make demo` starts the stack, runs the full pipeline, and brings the stack down automatically at the end.
The wrapper creates `compose/.env` from `.env.example` if it is absent; it does not overwrite an
existing configuration. Image references in `.env.example` are pinned to published releases.

The supplied project name is `ce-rise-dp-local-demonstrator`, separate from other Compose stacks.
For an existing `.env`, set `COMPOSE_PROJECT_NAME` explicitly before running alongside another
deployment. Project names also scope PostgreSQL volumes: selecting a new name uses a separate
volume and leaves the old one untouched. Keep the same project name across startup and teardown.

To run the RE-indicators extension instead:

```bash
make demo-re-indicators
```

To run the full SEE scenario:

```bash
make demo-see-impacts
```

The full PV calculation can take several minutes.

For SEE readiness and record validation without the numerical calculation:

```bash
make validate-see-impacts
```

## Auth Handling

Default mode is local no-auth:

- `hex-core-service` uses `AUTH_MODE=none`
- `dp-storage-jsondb-service` uses `AUTH_MODE=disabled`

This keeps the demonstrator Docker-only and deterministic. The demo still shows login/logout steps by
creating, dropping, and recreating a local demo session in the scripted flow. Record recovery after
"re-login" still works because the persisted data is stored in PostgreSQL and queried again through the core.

## Repo Layout

- [`demo.sh`](demo.sh)
- [`compose/docker-compose.yml`](compose/docker-compose.yml)
- [`compose/.env.example`](compose/.env.example)
- [`compose/registry/catalog.json`](compose/registry/catalog.json)
- [`payloads/dp_valid.json`](payloads/dp_valid.json)
- [`payloads/dp_invalid.json`](payloads/dp_invalid.json)
- [`payloads/re-indicators`](payloads/re-indicators)
- [`payloads/see-impacts`](payloads/see-impacts)

## Commands

```bash
make up
make demo
make demo-re-indicators
make demo-see-impacts
make down
make clean
make validate
make validate-re-indicators
make validate-see-impacts
```

Equivalent non-`make` wrapper commands:

```bash
./demo.sh up
./demo.sh demo
./demo.sh demo-re-indicators
./demo.sh demo-see-impacts
./demo.sh down
./demo.sh clean
./demo.sh validate
./demo.sh validate-re-indicators
./demo.sh validate-see-impacts
```

Direct stack-management commands with `docker compose`:

```bash
docker compose -f compose/docker-compose.yml --env-file compose/.env up -d postgres dp-storage-jsondb-service hex-core-service
docker compose -f compose/docker-compose.yml --env-file compose/.env up -d postgres dp-storage-jsondb-service hex-core-service re-indicators-calculation-service
docker compose -f compose/docker-compose.yml --env-file compose/.env --profile see-impacts up -d postgres dp-storage-jsondb-service hex-core-service see-impacts-calculation-service
docker compose -f compose/docker-compose.yml --env-file compose/.env down --remove-orphans
docker compose -f compose/docker-compose.yml --env-file compose/.env down --remove-orphans --volumes
docker compose -f compose/docker-compose.yml --env-file compose/.env ps
docker compose -f compose/docker-compose.yml --env-file compose/.env logs -f
```

Command behavior:

- `make demo` or `./demo.sh demo` runs the pipeline and then shuts the stack down automatically
- `make demo-re-indicators` or `./demo.sh demo-re-indicators` runs the laptop RE-indicators pipeline and then shuts the stack down automatically
- `make demo-see-impacts` or `./demo.sh demo-see-impacts` runs the PV calculation, reference comparison, validation, and persistence pipeline and then shuts the stack down automatically
- `make validate` or `./demo.sh validate` runs smoke checks and then shuts the stack down automatically
- `make validate-re-indicators` or `./demo.sh validate-re-indicators` runs smoke checks for the RE-indicators path and then shuts the stack down automatically
- `make validate-see-impacts` or `./demo.sh validate-see-impacts` checks SEE startup, rejects an invalid input, validates the example inputs and saved output against the deployed models, and then shuts the stack down without running a numerical calculation
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

## SEE Impacts Scenario

The scenario uses the PV example published with
[SEE Impacts Calculation v0.0.1](https://codeberg.org/CE-RISE-software/see-impacts-calculation-service/releases/tag/v0.0.1).
Its functional unit is `1 m^2` of the panel reference flow. The records are copied unchanged from
that release:

| File | Role |
| --- | --- |
| [`product-system.json`](payloads/see-impacts/product-system.json) | Product System input |
| [`lci-dataset.json`](payloads/see-impacts/lci-dataset.json) | Referenced inventory input |
| [`expected-integrated-lca.json`](payloads/see-impacts/expected-integrated-lca.json) | Published numerical reference, not a replacement for the calculated result |

The full command:

1. Starts the published core, storage backend, PostgreSQL, and SEE images.
2. Validates both input records through HEX Core using the registered model versions.
3. Checks that a deliberately non-conforming Product System is rejected by model validation.
4. Persists and reads back both valid input records through HEX Core and the storage backend.
5. Sends one valid calculation request to SEE and receives the complete Integrated LCA record.
6. Compares all 25 indicator identifiers, values, units, methods, and factor-set references with the published reference.
7. Validates the generated output through HEX Core, persists it, and verifies the complete read-back payload.

The comparison uses relative tolerance `1e-7` and absolute tolerance `1e-12`, matching the upstream
numerical test. The terminal prints every result and the stored record identifiers. A diagnostic,
missing indicator, numerical mismatch, schema failure, or read-back mismatch fails the command.
Read-back checks compare every field and allow only floating-point serialization rounding
(relative tolerance `1e-14`, with no absolute tolerance). The checked-in input records are not modified.

The catalog registers `product-system` `0.0.1`, `lci-dataset` `0.0.1`, and `integrated-lca` `0.2.0`
through versioned online artifacts. No schema copies or background archives are included in this
demonstrator. SEE uses the data supplied by its published image; the demonstrator only supplies the
example records through its HTTP API.

SEE's host endpoint is `127.0.0.1:8084`. Its calculation time limit defaults to 900 seconds, while
the client allows 1020 seconds for the request. These are controlled by
`SEE_IMPACTS_CALCULATION_TIMEOUT_SECS` and `DEMO_SEE_TIMEOUT_SECS`. Concurrency is limited to one
calculation for the local demonstration. Update an existing `compose/.env` explicitly when changing
image versions or these settings; the wrapper preserves that file.

The local helper image is built from `demo/runner`; no upstream service is rebuilt or wrapped.
For details of the calculator's API and assessment methods, use the
[SEE service documentation](https://ce-rise-software.codeberg.page/see-impacts-calculation-service/).

## Development Tests

With Python 3 installed:

```bash
make test
```

These tests exercise the SEE client workflow, single-calculation behavior, numerical comparison,
validation reports, invalid-input handling, and storage read-back without starting containers.
Use `make demo-see-impacts` for the full integration run against the published services.

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

- Port conflict: the chair and RE shell flows use the default API ports `8080`, `8081`, and `8083`; these must be free. The SEE flow uses internal service URLs and supports alternative host ports in `compose/.env`. The PostgreSQL host port can also be changed independently.
- Core not ready: inspect `hex-core-service` logs.
- Backend not ready: inspect `dp-storage-jsondb-service` and `postgres` logs.
- RE-indicators path not ready: inspect `re-indicators-calculation-service` logs and confirm port `8083` is free.
- SEE path not ready: inspect `see-impacts-calculation-service` logs and its `/capabilities` response.
- SEE schema validation unavailable: confirm that the three required models are present in the catalog and reachable through HEX Core.
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
