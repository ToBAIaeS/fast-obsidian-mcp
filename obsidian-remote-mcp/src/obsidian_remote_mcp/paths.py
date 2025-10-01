"""Utilities for working with vault paths safely."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Vault:
    """Container representing a vault root."""

    name: str
    root: Path


class VaultConfigurationError(ValueError):
    """Raised when vault configuration is invalid."""


def parse_vault_paths(raw: str) -> dict[str, Vault]:
    """Parse a comma separated list of vault paths into :class:`Vault` objects."""

    if not raw:
        raise VaultConfigurationError("VAULT_PATHS must be provided")

    vaults: dict[str, Vault] = {}
    for chunk in raw.split(","):
        candidate = chunk.strip()
        if not candidate:
            continue
        path = Path(candidate).expanduser()
        if not path.is_absolute():
            raise VaultConfigurationError(f"Vault path must be absolute: {candidate!r}")
        root = path.resolve(strict=False)
        name = root.name or root.stem
        if name in vaults:
            raise VaultConfigurationError(f"Duplicate vault name detected: {name}")
        vaults[name] = Vault(name=name, root=root)

    if not vaults:
        raise VaultConfigurationError("No valid vault paths provided")

    return vaults


def ensure_in_vault(path: Path, vaults: Mapping[str, Vault]) -> Vault:
    """Ensure *path* is inside one of the configured vaults."""

    resolved = path.resolve(strict=False)
    for vault in vaults.values():
        try:
            resolved.relative_to(vault.root)
        except ValueError:
            continue
        return vault
    raise PermissionError(f"Path {resolved} is outside configured vaults")


def _select_vault_and_relative(path: Path, vaults: Mapping[str, Vault]) -> tuple[Vault, Path]:
    if path.is_absolute():
        vault = ensure_in_vault(path, vaults)
        relative = path.resolve(strict=False).relative_to(vault.root)
        return vault, relative

    if not path.parts:
        raise ValueError("Empty path provided")

    first = path.parts[0]
    if first in vaults:
        vault = vaults[first]
        relative = Path(*path.parts[1:]) if len(path.parts) > 1 else Path()
        return vault, relative

    if len(vaults) == 1:
        vault = next(iter(vaults.values()))
        return vault, path

    raise ValueError("Ambiguous path - prefix with vault name (e.g. 'VaultName/note.md')")


def ensure_markdown_suffix(path: Path) -> Path:
    if path.suffix:
        return path
    return path.with_suffix(".md")


def resolve_note_path(path_str: str, vaults: Mapping[str, Vault]) -> Path:
    """Resolve a note path within the configured vaults."""

    raw_path = Path(path_str)
    vault, relative = _select_vault_and_relative(raw_path, vaults)
    target = ensure_markdown_suffix(vault.root / relative)
    ensure_in_vault(target, vaults)
    return target


def resolve_directory_path(path_str: str, vaults: Mapping[str, Vault]) -> Path:
    """Resolve a directory path within the configured vaults."""

    raw_path = Path(path_str)
    vault, relative = _select_vault_and_relative(raw_path, vaults)
    target = vault.root / relative
    ensure_in_vault(target, vaults)
    return target


def list_vault_names(vaults: Iterable[Vault]) -> list[str]:
    """Return vault names sorted alphabetically."""

    return sorted(v.name for v in vaults)
