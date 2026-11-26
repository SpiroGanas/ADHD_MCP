# Local FHIR server

Integration tests run the HTTP adapter against a real FHIR R4 server loaded with the synthetic personas. The server is HAPI FHIR, pinned to `hapiproject/hapi:v8.12.0-2` in `docker-compose.yml` and in the CI `integration` job. It keeps data in memory, so every restart starts empty.

## Run it

```bash
docker compose up -d fhir
```

```bash
uv run python scripts/load_personas.py
```

```bash
uv run pytest -m integration
```

The integration tests load the personas themselves, so the second command is only needed when exploring the server by hand, for example at `http://localhost:8080/fhir/Condition?patient=p01-patient`. The first start takes about a minute; the loader waits for the server.

To use another local server, set `ADHD_MCP_TEST_FHIR_URL` (default `http://localhost:8080/fhir`).

## Safety

- `scripts/load_personas.py` is test tooling and writes to the server. The MCP server itself never writes.
- The loader refuses any host other than `localhost`, `127.0.0.1` or the compose service name `fhir`, unless `--allow-remote-test-server` is given. Never point it at a server holding real data.

## Stop it

```bash
docker compose down
```
