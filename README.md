# CE-RISE Digital Passport System: Local Demonstrator

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19093662.svg)](https://doi.org/10.5281/zenodo.19093662)

This repository provides a local-only CE-RISE Digital Passport demonstrator adapted from the
`dp-system-gitops-template` structure, using published service images and deterministic scripted workflows.

Three demonstrations share HEX Core, the JSONDB storage backend, and PostgreSQL:

- **Chair passport:** validate a product record, persist it, retrieve it, and reject invalid data.
- **Laptop RE indicators:** calculate all five published laptop indicators with the RE Indicators service.
- **Photovoltaic (PV) impacts:** validate the inputs, calculate all 25 configured environmental impact
  indicators with the SEE Impacts service, compare the results, and persist the complete Integrated LCA record.

Model artifacts are retrieved from published CE-RISE sources at runtime; none are bundled here.

## Prerequisites

Bash, Docker with Compose, and an internet connection for downloading images and model artifacts.
The chair and laptop commands also require `curl`, `jq`, and GNU `timeout` on the host.
The SEE client runs in a helper container and requires no host Python or calculation libraries.

`make` is optional: each demonstration and validation command has a `./demo.sh` equivalent.

## Quickstart

Run a command from the repository root:

| Demonstration | Command | Without `make` |
| --- | --- | --- |
| Chair passport | `make demo` | `./demo.sh demo` |
| Laptop RE indicators | `make demo-re-indicators` | `./demo.sh demo-re-indicators` |
| PV environmental impacts | `make demo-see-impacts` | `./demo.sh demo-see-impacts` |

Each command starts the required services, runs its complete demonstration, and stops the stack
automatically. Persisted records remain in PostgreSQL. The PV calculation can take several minutes.
Run one demonstration at a time within the same Compose project.

## Configuration

[`demo.sh`](demo.sh) creates `compose/.env` from
[`compose/.env.example`](compose/.env.example) on first use. It preserves an existing `.env`, so
update that file explicitly when changing images, ports, or timeouts. The supplied service images
are pinned to published releases in the example configuration.

[`compose/docker-compose.yml`](compose/docker-compose.yml) defines the stack, and
[`compose/registry/catalog.json`](compose/registry/catalog.json) registers its model versions and
online validation artifacts.

The default `COMPOSE_PROJECT_NAME` is `ce-rise-dp-local-demonstrator`. Use a distinct project name
when running alongside another deployment, including when updating an older `.env`. The project
name also scopes PostgreSQL storage: changing it selects a separate volume without deleting the
previous one. Keep the same name for startup and teardown.

Authentication is disabled for local use: HEX Core uses `AUTH_MODE=none`, and the storage backend
uses `AUTH_MODE=disabled`. The chair script's login/logout steps simulate a local session; they do
not authenticate against an identity provider.

## Demonstrations

### Chair Passport

`make demo` uses the fictional `AIKIA LIDEN Chair` and the
[`valid`](payloads/dp_valid.json) and [`invalid`](payloads/dp_invalid.json) passport records.
It validates the valid record, persists it, simulates logout and login, retrieves the stored record
through HEX Core, and verifies rejection of the invalid record.

The record uses `dp-record-metadata` `0.0.2` as its framing model, with nested `product-profile`
and `usage-and-maintenance` content declared in `applied_schemas`. The operation targets
`dp-record-metadata`; the additional content remains part of the same stored payload.

### Laptop RE Indicators

`make demo-re-indicators` uses the fictional `Leveto T14 Eco` and the
[`laptop payloads`](payloads/re-indicators) for the `re-indicators-specification` model.
It calculates `REcycle_Laptop`, `REfurbish_Laptop`, `REmanufacture_Laptop`, `REpair_Laptop`, and
`REuse_Laptop`, printing the returned total score for each indicator. It also verifies rejection
of an unknown `indicator_specification_id`.

### PV Environmental Impacts

The scenario uses the PV example published with
[SEE Impacts Calculation v0.0.1](https://codeberg.org/CE-RISE-software/see-impacts-calculation-service/releases/tag/v0.0.1).
Its functional unit is `1 m^2` of the panel reference flow. The records are copied unchanged from
that release:

| File | Role |
| --- | --- |
| [`product-system.json`](payloads/see-impacts/product-system.json) | Product System input |
| [`lci-dataset.json`](payloads/see-impacts/lci-dataset.json) | Referenced inventory input |
| [`expected-integrated-lca.json`](payloads/see-impacts/expected-integrated-lca.json) | Published numerical reference, not a replacement for the calculated result |

`make demo-see-impacts`:

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

SEE's host endpoint defaults to `127.0.0.1:8084`. Its calculation time limit defaults to 900 seconds,
while the client allows 1020 seconds for the request. These are controlled by
`SEE_IMPACTS_CALCULATION_TIMEOUT_SECS` and `DEMO_SEE_TIMEOUT_SECS` in `compose/.env`.
Concurrency defaults to one calculation for the local demonstration.

The local helper image is built from `demo/runner`; no upstream service is rebuilt or wrapped.
For details of the calculator's API and assessment methods, use the
[SEE service documentation](https://ce-rise-software.codeberg.page/see-impacts-calculation-service/).

## Validation

These commands check service integration without running a complete demonstration:

| Command | Without `make` | Checks performed |
| --- | --- | --- |
| `make validate` | `./demo.sh validate` | Compose configuration, HEX Core readiness and version, and storage health. No records are written. |
| `make validate-re-indicators` | `./demo.sh validate-re-indicators` | Configuration and service readiness, plus one laptop reuse calculation. |
| `make validate-see-impacts` | `./demo.sh validate-see-impacts` | Configuration and service readiness, live validation of the PV inputs and saved reference output, and rejection of a non-conforming input. No numerical calculation or record persistence. |

Each command starts the required services and stops the stack afterwards, retaining existing data.
Use `make demo-see-impacts` for the numerical comparison and persistence checks on newly calculated
results; validating the saved reference alone does not perform those checks.

## Stack Management

| Operation | Command | Without `make` |
| --- | --- | --- |
| Start the core, storage backend, and PostgreSQL; leave them running | `make up` | `./demo.sh up` |
| Stop the stack and retain records | `make down` | `./demo.sh down` |
| Stop the stack and delete its persistent data | `make clean` | `./demo.sh clean` |

`make clean` is destructive: it removes the project's PostgreSQL volume. Ordinary shutdown retains
the named `postgres_data` volume and its records.

With the stack running, inspect service status and logs:

```bash
docker compose -f compose/docker-compose.yml --env-file compose/.env ps
docker compose -f compose/docker-compose.yml --env-file compose/.env logs -f
```

For manual operation of the calculation services, start the relevant service alongside the base stack:

```bash
docker compose -f compose/docker-compose.yml --env-file compose/.env up -d postgres dp-storage-jsondb-service hex-core-service re-indicators-calculation-service
docker compose -f compose/docker-compose.yml --env-file compose/.env --profile see-impacts up -d postgres dp-storage-jsondb-service hex-core-service see-impacts-calculation-service
```

## Development Tests

With Python 3 installed:

```bash
make test
```

These tests exercise the SEE client workflow, single-calculation behavior, numerical comparison,
validation reports, invalid-input handling, and storage read-back without starting containers.
Use `make demo-see-impacts` for the full integration run against the published services.

## Troubleshooting

- Port conflict: the chair and RE shell flows use the default API ports `8080`, `8081`, and `8083`; these must be free. The SEE flow uses internal service URLs and supports alternative host ports in `compose/.env`. The PostgreSQL host port can also be changed independently.
- Core not ready: inspect `hex-core-service` logs.
- Backend not ready: inspect `dp-storage-jsondb-service` and `postgres` logs.
- RE-indicators path not ready: inspect `re-indicators-calculation-service` logs and confirm port `8083` is free.
- SEE path not ready: inspect `see-impacts-calculation-service` logs and its `/capabilities` response.
- SEE schema validation unavailable: confirm that the three required models are present in the catalog and reachable through HEX Core.
- Invalid RE-indicators payload passes unexpectedly: verify the invalid payload still uses an unknown `indicator_specification_id`.
- On hosts using `podman-compose` through `docker compose`, the chair and laptop commands also check actual API availability if startup reports a failure. The SEE command requires successful Compose startup; inspect its printed startup logs if it fails.

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
