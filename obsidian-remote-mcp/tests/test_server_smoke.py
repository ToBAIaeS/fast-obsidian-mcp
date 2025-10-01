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

    search = service.search_vault("vault", "hello")
    assert search["ids"]

    fetch = service.fetch(search["ids"][0])
    assert fetch["ok"] and fetch["content"]

    rename = service.rename_tag("demo", "demo-renamed", "vault")
    assert rename["replacements"] >= 1

    delete = service.delete_note("vault/hello")
    assert delete["ok"]
