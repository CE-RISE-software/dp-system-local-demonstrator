# CE-RISE DP System Local Demonstrator

This repository provides a local-only CE-RISE Digital Passport demonstrator adapted from the
`dp-system-gitops-template` structure and aimed at a deterministic Docker-only workflow.

The demo stack runs:

- `hex-core-service`
- `dp-storage-jsondb-service`
- PostgreSQL for backend persistence
- a local artifact server with vendored model artifacts for:
  - `dp-record-metadata`
  - `product-profile`
  - `usage-and-maintenance`

The core service image is built locally from a vendored upstream source snapshot so the demonstrator
tracks the current model-operation routing behavior rather than an older published image variant.

The scripted demonstration uses a fictional chair product, `AIKIA LIDEN Chair`, and walks through:

1. local stack startup
2. no-auth session initialization
3. valid payload validation
4. record creation and persistence
5. logout and login again
6. stored record read-back through query
7. invalid payload rejection with clear error output

## Prerequisites

Docker only.

`make` is convenient but optional. Every operation also has a `docker compose` or `./demo.sh` path.

## Quickstart

```bash
cp compose/.env.example compose/.env
make up
make demo
```

Without `make`:

```bash
cp compose/.env.example compose/.env
./demo.sh up
./demo.sh demo
```

## Auth Handling

Default mode is local no-auth:

- `hex-core-service` uses `AUTH_MODE=none`
- `dp-storage-jsondb-service` uses `AUTH_MODE=disabled`

This keeps the demonstrator Docker-only and deterministic. The demo still shows login/logout steps by
creating, dropping, and recreating a local demo session in the runner container. Record recovery after
"re-login" still works because the persisted data is stored in PostgreSQL and queried again through the core.

## Repo Layout

- [`compose/docker-compose.yml`](/home/riccardo/code/CE-RISE-software/dp-system-local-demonstrator/compose/docker-compose.yml)
- [`compose/.env.example`](/home/riccardo/code/CE-RISE-software/dp-system-local-demonstrator/compose/.env.example)
- [`compose/registry/catalog.json`](/home/riccardo/code/CE-RISE-software/dp-system-local-demonstrator/compose/registry/catalog.json)
- [`demo/runner/run-demo.sh`](/home/riccardo/code/CE-RISE-software/dp-system-local-demonstrator/demo/runner/run-demo.sh)
- [`payloads/dp_valid.json`](/home/riccardo/code/CE-RISE-software/dp-system-local-demonstrator/payloads/dp_valid.json)
- [`payloads/dp_invalid.json`](/home/riccardo/code/CE-RISE-software/dp-system-local-demonstrator/payloads/dp_invalid.json)

## Commands

```bash
make up
make demo
make down
make clean
make validate
```

Equivalent wrapper commands:

```bash
./demo.sh up
./demo.sh demo
./demo.sh down
./demo.sh clean
./demo.sh validate
```

## Payload Modeling

The default valid payload is a composite record built around:

- `dp-record-metadata` as the record framing layer
- `product-profile` as the product identity/content layer
- `usage-and-maintenance` as accessory lifecycle information

The demo operation itself targets the `dp-record-metadata` model/version, while the accessory model data is
nested in the payload and declared in `applied_schemas`.

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

- Port conflict on `8080`, `8081`, `8082`, or `5432`: adjust values in [`compose/.env.example`](/home/riccardo/code/CE-RISE-software/dp-system-local-demonstrator/compose/.env.example) and regenerate `compose/.env`.
- Core not ready: inspect `hex-core-service` logs and confirm the artifact server is healthy.
- Backend not ready: inspect `dp-storage-jsondb-service` and `postgres` logs.
- Invalid payload passes unexpectedly: verify the demo is targeting `dp-record-metadata` `0.0.2` and that the local vendored schema files are mounted.

## License

Licensed under the [European Union Public Licence v1.2 (EUPL-1.2)](LICENSE).
