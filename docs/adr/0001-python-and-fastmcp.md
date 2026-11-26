# ADR 0001: Python and FastMCP

- **Status:** Accepted
- **Date:** 2026-11-26
- **Decided by:** Project owner

## Context

The server needs an MCP implementation, FHIR and data-handling libraries, and a path to statistical models later. The project owner chose the stack.

## Decision

Build the server in Python using the FastMCP framework.

## Alternatives considered

| Option | Why not |
|---|---|
| Official low-level MCP Python SDK | More boilerplate for tools, schemas and testing; FastMCP provides these directly |
| TypeScript MCP SDK | Weaker fit for the health-data and modeling ecosystem |
| Adapting an existing generic FHIR MCP server | Those expose generic search and write tools, which conflicts with ADR 0002 |

## Consequences

- Tool input and output schemas come from typed Python models, which supports contract testing.
- FastMCP's in-memory client makes tool-level tests fast and network-free.
- FastMCP and the MCP specification change quickly. Exact versions are pinned in Phase 1 (ADR 0006), and documentation must be checked before relying on any feature, including authentication and transport support.
