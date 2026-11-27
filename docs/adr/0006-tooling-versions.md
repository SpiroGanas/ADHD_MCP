# ADR 0006: Tooling and pinned versions

- **Status:** Accepted
- **Date:** 2026-11-26
- **Decided by:** Project owner (options proposed by the developer)

## Context

Phase 1 needs a reproducible toolchain. FastMCP and the MCP specification change quickly, so versions were checked against the package index and the installed packages on 2026-11-26 rather than taken from the research notes (which named FastMCP 2.x/3.x).

Findings on 2026-11-26:

- FastMCP 4.2.6 is current. It depends on the official MCP Python SDK 2.3.0, whose latest protocol version is `2026-07-28`.
- FastMCP 4 provides an in-memory `Client(server)` for tests, structured tool output from Pydantic return types, tool annotations (`readOnlyHint`), and `fastmcp inspect` / `fastmcp dev` for local inspection.
- The MCP SDK depends on `httpx2`, the successor package to `httpx`.

## Decision

| Concern | Choice | Pinned |
|---|---|---|
| Python | CPython 3.12 (`requires-python >=3.12,<3.13`) | 3.12 |
| MCP framework | FastMCP | 4.2.6 |
| Typed models | Pydantic v2 | 2.14.4 |
| HTTP client (FHIR adapter) | httpx2, already required by the MCP SDK; declared directly so the adapter does not rely on a transitive dependency | 2.16.2 |
| JWT signing (SMART backend services) | PyJWT, already required by FastMCP; declared directly (owner approval 2026-11-27) | 2.15.1 |
| Cryptography (RSA/EC keys for JWT) | cryptography, already required by FastMCP; declared directly (owner approval 2026-11-27) | 50.0.2 |
| Package and environment manager | uv, with a committed `uv.lock` | uv 0.11 |
| Build backend | hatchling | from lock |
| Test runner | pytest, pytest-cov, anyio's pytest plugin, Hypothesis | 9.2.0, 7.1.0, 4.16.0, 6.170.17 |
| Lint and format | ruff | 0.17.6 |
| Type checker | mypy, `strict = true`, with the Pydantic plugin | 2.4.1 |
| FHIR validation in tests | `fhir.resources` (R4B models), development only; see ADR 0007 | 8.3.0 |
| Data file format | TOML, read with the standard library `tomllib` (no extra dependency, allows comments for reviewers) | n/a |

Runtime dependencies are pinned exactly in `pyproject.toml`; the lock file pins everything transitively. Coverage floor is 90% of lines with branch coverage enabled.

## Alternatives considered

| Option | Why not |
|---|---|
| pyright instead of mypy | Needs Node in CI; mypy's Pydantic plugin is mature |
| pip with requirements files | No lock file for transitive pins; slower |
| `httpx` 0.x as the FHIR client | Would install a second HTTP library next to `httpx2` |
| YAML for data files | Extra dependency; TOML is in the standard library |
| Python 3.13 | Supported by the stack, but 3.12 is the more widely deployed baseline in health-system environments |

## Consequences

- One command installs (`uv sync`) and one runs every check (`./scripts/check`); both are in CLAUDE.md and README.
- Upgrading FastMCP or the MCP SDK is a deliberate change: re-read their changelogs, regenerate the lock, and expect contract snapshot review.
- `filterwarnings = error` in pytest turns deprecation warnings from these libraries into failures, so upgrades surface early.
