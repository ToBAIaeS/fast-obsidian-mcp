from pathlib import Path

from obsidian_remote_mcp.tags import add_tags, manage_tags, remove_tags, rename_tag


def _write_note(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_manage_tags_reads_inline_and_frontmatter(tmp_path):
    note = tmp_path / "note.md"
    _write_note(
        note,
        """---
tags:
  - project/foo
  - sample
---
This is a #demo note.
#project/foo
""",
    )

    tags = manage_tags(note)
    assert tags == ["#demo", "#project/foo", "#sample"]


def test_add_tags_appends_and_updates_frontmatter(tmp_path):
    note = tmp_path / "note.md"
    _write_note(
        note,
        """---
title: Example
---
Content
""",
    )

    add_tags(note, ["demo", "demo"])  # duplicates ignored
    content = note.read_text(encoding="utf-8")
    assert "#demo" in content
    tags = manage_tags(note)
    assert tags == ["#demo"]


def test_remove_tags_from_inline_and_frontmatter(tmp_path):
    note = tmp_path / "note.md"
    _write_note(
        note,
        """---
tags:
  - sample
---
A #sample tag appears here.
""",
    )

    remove_tags(note, ["sample"])
    content = note.read_text(encoding="utf-8")
    assert "#sample" not in content
    assert "tags" not in content
    assert content.startswith("A ")


def test_rename_tag_across_vault(tmp_path):
    root = tmp_path / "vault"
    note1 = root / "note1.md"
    note2 = root / "nested" / "note2.md"
    _write_note(note1, "Tag #old to rename.")
    _write_note(
        note2,
        """---
tags:
  - old
---
Another #old tag.
""",
    )

    replacements = rename_tag("old", "new", root)
    assert replacements == 3
    assert "#new" in note1.read_text(encoding="utf-8")
    assert "#new" in note2.read_text(encoding="utf-8")
