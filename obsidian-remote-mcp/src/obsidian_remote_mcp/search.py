"""Simple search utilities for vault content."""

from __future__ import annotations

from pathlib import Path


def search_vault(root: Path, query: str, max_results: int = 50) -> list[str]:
    """Perform a naive full-text search for *query* within *root*."""

    if max_results <= 0:
        return []

    needle = query.lower()
    results: list[str] = []
    for path in sorted(root.rglob("*.md")):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if needle in content.lower():
            results.append(str(path))
        if len(results) >= max_results:
            break
    return results


def fetch(note_id: str) -> dict[str, str]:
    """Fetch the content of a note by its absolute identifier (path)."""

    path = Path(note_id)
    content = path.read_text(encoding="utf-8")
    return {
        "id": str(path),
        "title": path.stem,
        "content": content,
    }
