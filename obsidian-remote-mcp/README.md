# Obsidian Remote MCP

A production-ready [FastMCP](https://github.com/ekzhang/fastmcp) server that exposes
Obsidian-like note operations over HTTP so ChatGPT and other Model Context Protocol (MCP)
clients can work with your vaults remotely. The server mirrors the public surface of
[`obsidian-mcp`](https://github.com/StevenStavrakis/obsidian-mcp) where practical, while
adding hardening for remote deployments: strict path safety, shared-secret authentication
and container-friendly packaging.

```
+-----------------+      HTTPS       +--------------------------+
| ChatGPT / MCP   |  <----------->   |  Obsidian Remote MCP     |
| connector       |                  |  (FastMCP over HTTP)     |
+-----------------+                  +--------------------------+
                                             |  |  |
                                             v  v  v
                                      Obsidian vault roots
```

## Features

* **FastMCP HTTP transport** compatible with ChatGPT connectors and Deep Research.
* **Vault safety** – all file operations are constrained to configured vault roots.
* **Optional shared-secret authentication** via the `x-mcp-secret` header on MCP requests.
* Full suite of tools mirroring Obsidian actions:
  - `list_available_vaults`
  - `read_note`
  - `create_note`
  - `edit_note`
  - `delete_note`
  - `move_note`
  - `create_directory`
  - `manage_tags`
  - `add_tags`
  - `remove_tags`
  - `rename_tag`
  - `search_vault`
  - `fetch`
  - `search` (alias for Deep Research compatibility)
* Markdown tag parsing (inline + YAML frontmatter), rename and cleanup utilities.
* Naive full-text search + fetch API for Deep Research.
* Production tooling: tests, type checking, linting, coverage, Docker image, Compose,
  GitHub Actions CI and `Makefile` automation.

## Security model

When `MCP_SHARED_SECRET` is set, all MCP HTTP requests must include a shared secret header:

```
x-mcp-secret: <your-secret>
```

The secret is configured via the `MCP_SHARED_SECRET` environment variable. A request
missing or providing the wrong secret receives a 401 response. Only the `/mcp/health`
endpoint is exempt so you can probe liveness.

If you omit `MCP_SHARED_SECRET` the server skips the authentication middleware and accepts
unauthenticated requests. This is useful for ChatGPT connectors today, which only support
OAuth or no authentication, but it should only be used for trusted, private deployments.

Every file system path is resolved and validated to ensure it remains inside one of the
configured vault roots. Symlink traversal, `..` escapes and cross-vault access are blocked.

## Configuration

| Environment variable | Description | Default |
| -------------------- | ----------- | ------- |
| `VAULT_PATHS`        | Comma-separated absolute paths to Obsidian vault roots (required) | – |
| `MCP_SHARED_SECRET`  | Shared secret for MCP requests (optional, recommended) | – |
| `HOST`               | Bind host | `0.0.0.0` |
| `PORT`               | HTTP port | `8000` |
| `LOG_LEVEL`          | Python logging level | `info` |

Copy `.env.example` to `.env` and update the values before running locally or in Docker.

## Local setup

```bash
cp .env.example .env
# edit .env with your vault paths (absolute) and optional shared secret
python3.11 -m venv .venv
source .venv/bin/activate
make setup
make test  # optional sanity check
make run   # starts the FastMCP server
```

The service listens on `http://HOST:PORT/mcp/` and requires the shared-secret header for
all MCP interactions.

### Docker

```bash
docker compose up --build
```

The compose file mounts `./vaults` into `/vaults` in the container. Create that directory
and populate it with your Obsidian vault(s), then set `VAULT_PATHS=/vaults` in `.env`.

### Health check

Verify the container is up:

```bash
curl http://localhost:8000/mcp/health
# -> {"status": "ok"}
```

## Tool reference

Each tool responds with JSON payloads. Examples below use the `vault` named root.

<details>
<summary>list_available_vaults</summary>

Request:

```json
{"path": "list_available_vaults"}
```

Response:

```json
{"vaults": ["vault"]}
```
</details>

<details>
<summary>read_note</summary>

```json
{"path": "vault/Projects/plan"}
```

```json
{"ok": true, "path": "/vaults/vault/Projects/plan.md", "exists": true, "content": "..."}
```
</details>

<details>
<summary>create_note</summary>

```json
{"path": "vault/Inbox/idea", "content": "New idea", "overwrite": false}
```

```json
{"ok": true, "path": "/vaults/vault/Inbox/idea.md"}
```
</details>

<details>
<summary>search_vault / search</summary>

```json
{"root": "vault", "query": "deep learning", "max_results": 20}
```

```json
{"ok": true, "ids": ["/vaults/vault/Research/note.md", "..."]}
```
</details>

<details>
<summary>fetch</summary>

```json
{"note_id": "/vaults/vault/Research/note.md"}
```

```json
{"ok": true, "id": "/vaults/vault/Research/note.md", "title": "note", "content": "..."}
```
</details>

All other tools follow similar request/response patterns and return `{"ok": false, "error": "..."}`
when something fails.

## ChatGPT connector setup

1. Enable **Developer Mode** in ChatGPT.
2. Create a new **Model Context Protocol (MCP) connector**.
3. Set the Server URL to `https://YOUR_HOST:PORT/mcp/` (include the trailing slash).
4. If you configured `MCP_SHARED_SECRET`, add a custom header `x-mcp-secret: <your-secret>`.
   When the UI does not support custom headers, place the MCP server behind a reverse proxy
   (e.g. Nginx) that injects the header before forwarding requests. If you left the secret
   unset, skip this step.
5. Save and enable the connector for your conversations.

The connector can now call tools like `search`, `fetch`, `read_note`, etc.

### Deep Research

The optional `search` alias and `fetch` tool match the interface expected by ChatGPT Deep
Research. Configure the connector as above, then ask Deep Research prompts; it will call
`search` for document IDs and `fetch` to retrieve their contents.

## Development workflow

* `make lint` – Ruff linting.
* `make format` – Black formatting.
* `make typecheck` – mypy strict typing.
* `make test` – Pytest with coverage (`pytest -q`).
* GitHub Actions runs the full pipeline on pushes and pull requests.

## Path safety & backups

The server rejects any path that escapes the configured vault roots. Symlinks pointing
outside the vault are ignored. For additional safety, keep your vault under version control
(Git) so you can diff and restore changes made by connectors.

## Limitations & roadmap

* Search is a simple case-insensitive substring scan – integrate with ripgrep, sqlite or
  embeddings for larger vaults.
* No incremental sync or websockets; the server is stateless HTTP-only.
* Authentication is a single shared secret; integrate mTLS or OAuth if you need multi-user
  access.
* Tag parsing handles YAML lists and inline hashtags; complex metadata schemas may require
  customization.

Contributions and feedback are welcome!
