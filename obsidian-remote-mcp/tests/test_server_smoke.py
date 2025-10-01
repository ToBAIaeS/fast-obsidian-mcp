from obsidian_remote_mcp.paths import Vault
from obsidian_remote_mcp.server import NoteService


def test_note_service_smoke(tmp_path):
    root = tmp_path / "vault"
    root.mkdir()
    service = NoteService({"vault": Vault("vault", root)})

    result = service.create_note("vault/hello", "Hello world")
    assert result["ok"]
    read = service.read_note("vault/hello")
    assert read["exists"] and "Hello" in read["content"]

    edit = service.edit_note("vault/hello", insert="\nMore")
    assert edit["ok"]
    tags = service.add_tags("vault/hello", ["demo"])
    assert tags["ok"]
    manage = service.manage_tags("vault/hello")
    assert "#demo" in manage["tags"]

    search = service.search_vault("hello", root="vault")
    assert search["ids"]

    fetch = service.fetch(search["ids"][0])
    assert fetch["ok"] and fetch["content"]

    fetch_by_id = service.fetch(id=search["ids"][0])
    assert fetch_by_id["ok"] and fetch_by_id["content"]

    missing_identifier = service.fetch(note_id=None, id=None)
    assert not missing_identifier["ok"]
    assert "missing" in missing_identifier["error"].lower()

    rename = service.rename_tag("demo", "demo-renamed", "vault")
    assert rename["replacements"] >= 1

    delete = service.delete_note("vault/hello")
    assert delete["ok"]


def test_search_vault_defaults_to_single_vault(tmp_path):
    root = tmp_path / "vault"
    root.mkdir()
    service = NoteService({"vault": Vault("vault", root)})

    (root / "note.md").write_text("Needle", encoding="utf-8")

    result = service.search_vault("Needle")
    assert result["ok"] and result["ids"]


def test_search_vault_requires_root_for_multiple_vaults(tmp_path):
    root_a = tmp_path / "vault-a"
    root_b = tmp_path / "vault-b"
    root_a.mkdir()
    root_b.mkdir()

    service = NoteService(
        {
            "vault-a": Vault("vault-a", root_a),
            "vault-b": Vault("vault-b", root_b),
        }
    )

    result = service.search_vault("anything")
    assert not result["ok"]
    assert "multiple vaults" in result["error"].lower()
