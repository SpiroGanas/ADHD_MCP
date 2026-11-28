# Configuration

The server is configured only through environment variables. They are validated when it starts (`src/adhd_mcp/config.py`): a missing or malformed setting stops it with an error that names the variable, never its value. Private keys are read from files named by a variable, never from the variable itself.

## Data source

Set one. With neither, every patient tool returns a `not_configured` error.

| Variable | Meaning |
|---|---|
| `ADHD_MCP_FIXTURE_DIR` | A directory of FHIR R4 bundles (JSON) to read in memory. Use `tests/personas/bundles` for the 14 synthetic personas |
| `ADHD_MCP_FHIR_BASE_URL` | A FHIR R4 server. The server only issues GET requests to it. Wins over `ADHD_MCP_FIXTURE_DIR`. Must use https unless it is on this machine (`localhost`, `127.0.0.1`, `::1`) or `ADHD_MCP_ALLOW_PLAIN_HTTP=1`. A server not on this machine also needs `ADHD_MCP_PRIVACY_POLICY` (below) |
| `ADHD_MCP_ALLOW_PLAIN_HTTP` | `1`: allow plain http to a FHIR server or public URL that is not on this machine, for a private network the site trusts. Off by default (peer review 01, P5) |
| `ADHD_MCP_SCORER` | `rules-only` (default) or `dummy`. The dummy scorer is not a model: it always reports a score of 0.0 to prove the scorer slot (Phase 8). A score never changes the recommendation |
| `ADHD_MCP_EXPERIMENTAL_CONDITIONS` | Comma-separated experimental stub conditions to register; only `autism` exists. Off by default and not for clinical use ([rule card](../clinical/rule_card_autism_stub.md)) |
| `ADHD_MCP_SITE_CODES` | A packaged local code mapping in `src/adhd_mcp/data/site_codes/`, by name (only `synthetic` exists; any other name is refused at start-up). Defaults to `synthetic` with fixture data and to no mapping with a FHIR server, in which case checks that need local codes report "not performed" ([ADR 0008](../adr/0008-site-codes-and-search-warnings.md)) |
| `ADHD_MCP_SITE_CODES_FILE` | A site's own code mapping file, in the format of `synthetic.toml`; its file name must match its `id`. Loaded strictly: an unverified entry refuses start-up. Not with `ADHD_MCP_SITE_CODES` |

### A local FHIR server

For development against a real FHIR server, run HAPI FHIR in Docker and load the personas ([docs/dev/local_fhir_server.md](../dev/local_fhir_server.md)):

```bash
docker compose up -d fhir
uv run python scripts/load_personas.py
ADHD_MCP_FHIR_BASE_URL=http://localhost:8080/fhir ADHD_MCP_SITE_CODES=synthetic uv run adhd-mcp
```

### SMART backend services toward the FHIR server

All five or none ([ADR 0012](../adr/0012-authentication.md)). Needs `ADHD_MCP_FHIR_BASE_URL`, which must use https except on localhost.

| Variable | Meaning |
|---|---|
| `ADHD_MCP_SMART_TOKEN_URL` | The authorization server's token endpoint (https) |
| `ADHD_MCP_SMART_CLIENT_ID` | This server's registered client id |
| `ADHD_MCP_SMART_KEY_ID` | The `kid` of the signing key |
| `ADHD_MCP_SMART_SCOPE` | Scopes to request, for example `system/*.rs` |
| `ADHD_MCP_SMART_PRIVATE_KEY_FILE` | File holding the private key (PEM) used to sign the client assertion |
| `ADHD_MCP_SMART_AUDIENCE` | Optional: the client assertion's audience (`aud`); default the token URL. Required with the `lighthouse` profile |

### FHIR server profile

| Variable | Meaning |
|---|---|
| `ADHD_MCP_FHIR_SERVER_PROFILE` | `generic` (default: a full FHIR R4 server) or `lighthouse` (VA Lighthouse Patient Health API: only the types it offers, no `_include`, patient-scoped client credentials tokens). Needs `ADHD_MCP_FHIR_BASE_URL`. See [Lighthouse](../integration/lighthouse.md) |

## Transport

| Variable | Meaning |
|---|---|
| `ADHD_MCP_TRANSPORT` | `stdio` (default) or `http` (streamable HTTP at `/mcp`) |
| `ADHD_MCP_HOST`, `ADHD_MCP_PORT` | HTTP bind address; default `127.0.0.1:8000` |

### HTTP with OAuth

Over HTTP the server is an OAuth resource server: callers send a bearer token, and each tool needs its scope (`adhd.evidence.read` for the evidence tools, `adhd.referral.assess` for `assess_referral_need` and `draft_referral_proposal`). It publishes RFC 9728 protected-resource metadata.

| Variable | Meaning |
|---|---|
| `ADHD_MCP_PUBLIC_URL` | This server's public base URL |
| `ADHD_MCP_AUTH_ISSUER` | Expected token issuer (https) |
| `ADHD_MCP_AUTH_AUDIENCE` | Expected token audience: this server's resource URL, for example `https://mcp.example.org/mcp` |
| `ADHD_MCP_AUTH_JWKS_URI` or `ADHD_MCP_AUTH_PUBLIC_KEY_FILE` | Where the token signing keys come from; exactly one |
| `ADHD_MCP_AUTH_SERVERS` | Comma-separated authorization server URLs advertised to clients; default the issuer |
| `ADHD_MCP_AUDIT_FILE` | Required for HTTP (below) |
| `ADHD_MCP_ALLOW_UNAUTHENTICATED_HTTP` | `1` turns authentication off; allowed only with `ADHD_MCP_HOST=127.0.0.1`. For local testing only |

The server never forwards a caller's token to the FHIR server. Rate limiting is left to the hosting gateway ([threat model](../security/threat_model.md)).

## Audit and privacy

| Variable | Meaning |
|---|---|
| `ADHD_MCP_AUDIT_FILE` | Append-only JSON Lines file, one record per tool call: caller, versions, resource references and an output hash, never clinical values ([ADR 0011](../adr/0011-audit-tracing-and-privacy.md)). Its directory must exist. Optional over stdio, required over HTTP |
| `ADHD_MCP_PRIVACY_POLICY` | A site's sensitive-data policy file, or `packaged` for the packaged `src/adhd_mcp/data/privacy.toml`. Required when `ADHD_MCP_FHIR_BASE_URL` is not on this machine, so a site chooses its policy rather than inheriting one (peer review 01, P2). The packaged policy cites substance use, HIV and sickle-cell data: see below for what that hides and what it does not. Under `withhold`, a signal whose records were withheld for the patient reads "Not checked: records it needs were withheld by the privacy policy", and when no rule fires the result is `insufficient_data`, never `no_recommendation` |


### What `cite` hides, and what it does not

Under `cite` (the packaged policy's action for every category) a protected record is used by the rules, and outputs replace its code with `restricted`. They still show the record's reference (`Condition/<id>`), its date, and the signal or family it belongs to, for example "Alcohol involvement" or "Stimulant-related disorder". Under 42 CFR Part 2 and 38 U.S.C. 7332 the protected fact may be that such a record exists at all, so `cite` may not be enough for a site. `withhold` removes the records before any tool sees them; signals that needed them then read "Not checked: records it needs were withheld by the privacy policy", and the outputs count what was withheld per category. Categories that no output uses (HIV, sickle-cell disease) are never named, even in counts. Classification is by ICD-10-CM code and security label only: AUDIT-C results, drug screens and medications such as buprenorphine are not recognized as protected unless a site adds value sets for them.

## Examples

Sample data over stdio:

```bash
ADHD_MCP_FIXTURE_DIR=tests/personas/bundles uv run adhd-mcp
```

Sample data over local, unauthenticated HTTP (testing only):

```bash
mkdir -p build
ADHD_MCP_FIXTURE_DIR=tests/personas/bundles ADHD_MCP_TRANSPORT=http \
ADHD_MCP_ALLOW_UNAUTHENTICATED_HTTP=1 ADHD_MCP_AUDIT_FILE=build/audit.jsonl \
uv run adhd-mcp
```
