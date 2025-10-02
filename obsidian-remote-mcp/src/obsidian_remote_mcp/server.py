"""FastMCP server exposing Obsidian-like tools."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, TypeVar, cast

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.middleware import Middleware

from .paths import (
    Vault,
    list_vault_names,
    parse_vault_paths,
    resolve_directory_path,
    resolve_note_path,
)
from .search import fetch as fetch_note
from .search import search_vault as search_vault_content
from .security import build_security_middleware
from .tags import add_tags as add_tags_to_note
from .tags import manage_tags as read_tags
from .tags import remove_tags as remove_tags_from_note
from .tags import rename_tag as rename_tag_in_vault

TToolFunc = TypeVar("TToolFunc", bound=Callable[..., Any])

load_dotenv()


@dataclass(slots=True)
class Settings:
    vaults: Mapping[str, Vault]
    host: str
    port: int
    shared_secret: str | None
    log_level: str


@dataclass(slots=True)
class NoteService:
    """Business logic for manipulating notes."""

    vaults: Mapping[str, Vault]

    def list_available_vaults(self) -> dict[str, list[str]]:
        return {"vaults": list_vault_names(self.vaults.values())}

    def read_note(self, path: str) -> dict[str, Any]:
        try:
            target = resolve_note_path(path, self.vaults)
        except Exception as exc:  # pragma: no cover - defensive
            return {"ok": False, "error": str(exc), "path": path, "exists": False}

        if target.exists():
            content = target.read_text(encoding="utf-8")
            return {
                "ok": True,
                "path": str(target),
                "exists": True,
                "content": content,
            }
        return {
            "ok": True,
            "path": str(target),
            "exists": False,
            "content": "",
        }

    def create_note(
        self, path: str, content: str | None = "", overwrite: bool = False
    ) -> dict[str, Any]:
        try:
            target = resolve_note_path(path, self.vaults)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and not overwrite:
                return {"ok": False, "error": "File already exists", "path": str(target)}
            target.write_text(content or "", encoding="utf-8")
            return {"ok": True, "path": str(target)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def edit_note(
        self,
        path: str,
        replace: str | None = None,
        find: str | None = None,
        insert: str | None = None,
    ) -> dict[str, Any]:
        try:
            target = resolve_note_path(path, self.vaults)
            if not target.exists():
                return {"ok": False, "error": "Note does not exist"}
            content = target.read_text(encoding="utf-8")
            if replace is not None:
                content = replace
            elif find is not None and insert is not None:
                if find not in content:
                    return {"ok": False, "error": "Find text not present"}
                content = content.replace(find, insert, 1)
            elif insert is not None:
                if not content.endswith("\n"):
                    content += "\n"
                content += insert
            else:
                return {"ok": False, "error": "No edit operation specified"}
            target.write_text(content, encoding="utf-8")
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def delete_note(self, path: str) -> dict[str, Any]:
        try:
            target = resolve_note_path(path, self.vaults)
            if target.exists():
                target.unlink()
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def move_note(self, src: str, dst: str, overwrite: bool = False) -> dict[str, Any]:
        try:
            source = resolve_note_path(src, self.vaults)
            destination = resolve_note_path(dst, self.vaults)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not source.exists():
                return {"ok": False, "error": "Source note does not exist"}
            if destination.exists() and not overwrite:
                return {"ok": False, "error": "Destination exists"}
            if destination.exists():
                destination.unlink()
            source.rename(destination)
            return {"ok": True, "path": str(destination)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def create_directory(self, path: str) -> dict[str, Any]:
        try:
            target = resolve_directory_path(path, self.vaults)
            target.mkdir(parents=True, exist_ok=True)
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def manage_tags(self, path: str) -> dict[str, Any]:
        try:
            target = resolve_note_path(path, self.vaults)
            if not target.exists():
                return {"ok": False, "error": "Note does not exist"}
            tags = read_tags(target)
            return {"ok": True, "tags": tags}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def add_tags(self, path: str, tags: list[str]) -> dict[str, Any]:
        try:
            target = resolve_note_path(path, self.vaults)
            if not target.exists():
                return {"ok": False, "error": "Note does not exist"}
            add_tags_to_note(target, tags)
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def remove_tags(self, path: str, tags: list[str]) -> dict[str, Any]:
        try:
            target = resolve_note_path(path, self.vaults)
            if not target.exists():
                return {"ok": False, "error": "Note does not exist"}
            remove_tags_from_note(target, tags)
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def rename_tag(self, old: str, new: str, root: str) -> dict[str, Any]:
        try:
            vault_root = resolve_directory_path(root, self.vaults)
            replacements = rename_tag_in_vault(old, new, vault_root)
            return {"ok": True, "replacements": replacements}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def search_vault(
        self, query: str, root: str | None = None, max_results: int = 50
    ) -> dict[str, Any]:
        try:
            if root is None:
                if len(self.vaults) == 1:
                    vault_root = next(iter(self.vaults.values())).root
                else:
                    raise ValueError(
                        "Multiple vaults configured; specify the 'root' parameter"
                    )
            else:
                vault_root = resolve_directory_path(root, self.vaults)
            results = search_vault_content(vault_root, query, max_results)
            return {"ok": True, "ids": results}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def fetch(
        self, note_id: str | None = None, *, id: str | None = None
    ) -> dict[str, Any]:
        identifier = id if id is not None else note_id
        if identifier is None:
            return {"ok": False, "error": "Missing note identifier"}

        try:
            path = resolve_note_path(identifier, self.vaults)
            data = fetch_note(str(path))
            return {"ok": True, **data}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


def load_settings() -> Settings:
    """Load configuration from environment variables."""

    raw_vaults = os.environ.get("VAULT_PATHS", "")
    vaults = parse_vault_paths(raw_vaults)

    host = os.environ.get("HOST", "0.0.0.0")  # noqa: S104 (intentional bind)
    port = int(os.environ.get("PORT", "8000"))
    shared_secret = os.environ.get("MCP_SHARED_SECRET")

    log_level = os.environ.get("LOG_LEVEL", "info").upper()
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO))

    return Settings(
        vaults=vaults,
        host=host,
        port=port,
        shared_secret=shared_secret,
        log_level=log_level,
    )


def create_server(settings: Settings | None = None) -> tuple[FastMCP, list[Middleware]]:
    """Create a configured :class:`FastMCP` instance and its security middleware."""

    settings = settings or load_settings()
    server = FastMCP(
        "Obsidian Remote",
        instructions="Remote Obsidian MCP for ChatGPT",
    )

    security_middleware = build_security_middleware(settings.shared_secret)

    service = NoteService(settings.vaults)

    def tool(*args: Any, **kwargs: Any) -> Callable[[TToolFunc], TToolFunc]:
        decorator = server.tool(*args, **kwargs)
        return cast(Callable[[TToolFunc], TToolFunc], decorator)

    @tool()
    async def list_available_vaults() -> dict[str, list[str]]:
        return service.list_available_vaults()

    @tool()
    async def read_note(path: str) -> dict[str, Any]:
        return service.read_note(path)

    @tool()
    async def create_note(
        path: str, content: str | None = "", overwrite: bool = False
    ) -> dict[str, Any]:
        return service.create_note(path, content, overwrite)

    @tool()
    async def edit_note(
        path: str,
        replace: str | None = None,
        find: str | None = None,
        insert: str | None = None,
    ) -> dict[str, Any]:
        return service.edit_note(path, replace, find, insert)

    @tool()
    async def delete_note(path: str) -> dict[str, Any]:
        return service.delete_note(path)

    @tool()
    async def move_note(src: str, dst: str, overwrite: bool = False) -> dict[str, Any]:
        return service.move_note(src, dst, overwrite)

    @tool()
    async def create_directory(path: str) -> dict[str, Any]:
        return service.create_directory(path)

    @tool()
    async def manage_tags(path: str) -> dict[str, Any]:
        return service.manage_tags(path)

    @tool()
    async def add_tags(path: str, tags: list[str]) -> dict[str, Any]:
        return service.add_tags(path, tags)

    @tool()
    async def remove_tags(path: str, tags: list[str]) -> dict[str, Any]:
        return service.remove_tags(path, tags)

    @tool()
    async def rename_tag(old: str, new: str, root: str) -> dict[str, Any]:
        return service.rename_tag(old, new, root)

    @tool()
    async def search_vault(
        query: str, root: str | None = None, max_results: int = 50
    ) -> dict[str, Any]:
        return service.search_vault(query, root, max_results)

    @tool(name="search")
    async def search_alias(
        query: str, root: str | None = None, max_results: int = 50
    ) -> dict[str, Any]:
        return service.search_vault(query, root, max_results)

    @tool()
    async def fetch(id: str, note_id: str | None = None) -> dict[str, Any]:
        identifier = id or note_id
        if identifier is None:
            return {"ok": False, "error": "Either 'id' or 'note_id' must be provided"}

        if id:
            return service.fetch(id=id)
        return service.fetch(identifier)

    @server.custom_route("/mcp/health", methods=["GET"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return cast(FastMCP, server), security_middleware


def main() -> None:
    """Run the FastMCP server."""

    settings = load_settings()
    server, security_middleware = create_server(settings)
    server.run(
        transport="http",
        host=settings.host,
        port=settings.port,
        middleware=security_middleware,
    )


if __name__ == "__main__":
    main()
