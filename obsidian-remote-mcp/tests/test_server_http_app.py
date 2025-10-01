"""Regression tests for HTTP app construction."""

from obsidian_remote_mcp.paths import Vault
from obsidian_remote_mcp.server import Settings, create_server


def test_http_app_builds_with_security_middleware(tmp_path):
    vault_root = tmp_path / "vault"
    vault_root.mkdir()

    settings = Settings(
        vaults={"vault": Vault("vault", vault_root)},
        host="127.0.0.1",
        port=0,
        shared_secret="super-secret",
        log_level="INFO",
    )

    server, security_middleware = create_server(settings)

    app = server.http_app(middleware=security_middleware)

    assert app is not None
