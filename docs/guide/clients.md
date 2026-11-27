# Connecting MCP clients

The server speaks MCP over stdio (default) or streamable HTTP. These steps use the synthetic sample data; for other data sources see [configuration.md](configuration.md). Replace `/absolute/path/to/ADHD_MCP` with the folder you cloned.

Client menus and file locations change between versions; if a step below no longer matches, check the client's own MCP documentation. The server side does not change.

## Claude Desktop

Open the configuration file (Settings, Developer, Edit Config), which on macOS is `~/Library/Application Support/Claude/claude_desktop_config.json` and on Windows `%APPDATA%\Claude\claude_desktop_config.json`, and add:

```json
{
  "mcpServers": {
    "adhd-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/ADHD_MCP", "adhd-mcp"],
      "env": { "ADHD_MCP_FIXTURE_DIR": "/absolute/path/to/ADHD_MCP/tests/personas/bundles" }
    }
  }
}
```

Restart Claude Desktop. If `uv` is not found, give its absolute path (`which uv`) as `command`.

## Claude Code

From the repository folder:

```bash
claude mcp add adhd-mcp \
  --env ADHD_MCP_FIXTURE_DIR="$PWD/tests/personas/bundles" \
  -- uv run --directory "$PWD" adhd-mcp
```

Check it with `claude mcp list`, then ask: *"Use adhd-mcp to assess p01-patient as of 2026-06-15."*

## Other stdio clients

Any client that launches a stdio server needs the same three things: the command `uv`, the arguments `run --directory /absolute/path/to/ADHD_MCP adhd-mcp`, and the environment variable `ADHD_MCP_FIXTURE_DIR`. If the package is installed into an environment (`uv pip install .` or a wheel), the command is simply `adhd-mcp`.

## MCP Inspector

The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) is a browser UI for calling tools by hand. It needs Node.js:

```bash
ADHD_MCP_FIXTURE_DIR="$PWD/tests/personas/bundles" \
  npx @modelcontextprotocol/inspector uv run --directory "$PWD" adhd-mcp
```

Without Node, `uv run fastmcp inspect src/adhd_mcp/server.py:create_server` lists the tools, resources and prompts.

## Over HTTP

Start the server with `ADHD_MCP_TRANSPORT=http` ([configuration.md](configuration.md#http-with-oauth)); the MCP endpoint is `http://HOST:PORT/mcp`. Clients that support remote MCP servers with OAuth discover the authorization server from the server's protected-resource metadata and send a bearer token with the scopes `adhd.evidence.read` and `adhd.referral.assess`. For local testing only, `ADHD_MCP_ALLOW_UNAUTHENTICATED_HTTP=1` on 127.0.0.1 turns authentication off.

## Container

The `Dockerfile` builds an image with the server and the synthetic sample data (nothing is published to a registry). With Docker:

```bash
docker build -t adhd-mcp .
docker run --rm -i -e ADHD_MCP_FIXTURE_DIR=/app/sample-data adhd-mcp
```

A client launches it with the command `docker` and the arguments `run --rm -i -e ADHD_MCP_FIXTURE_DIR=/app/sample-data adhd-mcp`. For HTTP inside a container, set `ADHD_MCP_HOST=0.0.0.0` and the OAuth settings; unauthenticated HTTP is refused there, because it is allowed only on 127.0.0.1.

## Trying it

Patients `p01-patient` to `p14-patient` are described in [tests/personas/catalog.toml](../../tests/personas/catalog.toml). Their dates are set around 2026-06-15; pass `as_of: 2026-06-15` to reproduce the documented outcomes. Good first questions:

- *"Should I consider an ADHD screening referral for p01-patient?"* (a referral suggestion)
- *"And for p03-patient?"* (the safety gate comes first)
- *"What does the record of p07-patient show?"* (an empty record: insufficient data)
