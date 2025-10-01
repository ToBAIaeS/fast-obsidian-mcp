import pytest

from obsidian_remote_mcp.paths import (
    VaultConfigurationError,
    ensure_in_vault,
    parse_vault_paths,
    resolve_directory_path,
    resolve_note_path,
)


def test_parse_vault_paths(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    mapping = parse_vault_paths(str(vault))
    assert len(mapping) == 1
    assert "vault" in mapping
    assert mapping["vault"].root == vault.resolve()


def test_parse_vault_paths_requires_absolute():
    with pytest.raises(VaultConfigurationError):
        parse_vault_paths("relative/path")


def test_resolve_note_path_adds_suffix(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    vaults = parse_vault_paths(str(vault))
    result = resolve_note_path("note", vaults)
    assert result.suffix == ".md"
    assert result.parent == vault


def test_resolve_note_path_with_vault_prefix(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    vaults = parse_vault_paths(f"{first},{second}")
    result = resolve_note_path("second/sub/note.md", vaults)
    assert str(result).startswith(str(second))


def test_resolve_note_path_ambiguous_without_prefix(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    vaults = parse_vault_paths(f"{first},{second}")
    with pytest.raises(ValueError):
        resolve_note_path("note.md", vaults)


def test_ensure_in_vault_rejects_escape(tmp_path):
    vault = tmp_path / "vault"
    outside = tmp_path / "outside"
    vault.mkdir()
    outside.mkdir()
    vaults = parse_vault_paths(str(vault))
    target = outside / "note.md"
    with pytest.raises(PermissionError):
        ensure_in_vault(target, vaults)


def test_resolve_directory_path(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    vaults = parse_vault_paths(str(vault))
    result = resolve_directory_path("folder/sub", vaults)
    assert result == vault / "folder" / "sub"
