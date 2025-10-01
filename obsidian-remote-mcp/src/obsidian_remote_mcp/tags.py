"""Tag management utilities for Obsidian markdown files."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

INLINE_TAG_PATTERN = re.compile(r"(?<![\\w/])#([A-Za-z0-9_\-/]+)")
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


class TagError(RuntimeError):
    """Raised when tag manipulation fails."""


def _normalize_tag(tag: str) -> str:
    tag = tag.strip()
    if not tag:
        raise TagError("Tags cannot be empty")
    if not tag.startswith("#"):
        tag = f"#{tag}"
    return tag


def _strip_hash(tag: str) -> str:
    return tag[1:] if tag.startswith("#") else tag


def _split_frontmatter(content: str) -> tuple[dict[str, Any], str, str]:
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return {}, "", content
    body = content[match.end() :]
    raw_frontmatter = match.group(1)
    loaded = yaml.safe_load(raw_frontmatter) or {}
    data: dict[str, Any]
    if isinstance(loaded, dict):
        data = dict(loaded)
    else:
        data = {}
    return data, content[: match.end()], body


def _dump_frontmatter(data: dict[str, Any]) -> str:
    rendered = yaml.safe_dump(data, sort_keys=True).strip()
    return f"---\n{rendered}\n---\n"


def extract_inline_tags(content: str) -> list[str]:
    """Return inline tags found within *content*."""

    return sorted({f"#{match.group(1)}" for match in INLINE_TAG_PATTERN.finditer(content)})


def extract_frontmatter_tags(data: dict[str, Any]) -> list[str]:
    value = data.get("tags")
    if isinstance(value, str):
        tags = {value}
    elif isinstance(value, Iterable):
        tags = {str(item) for item in value}
    else:
        tags = set()
    return sorted(tags)


def manage_tags(path: Path) -> list[str]:
    """Return sorted unique tags for the note at *path*."""

    content = path.read_text(encoding="utf-8")
    frontmatter, _, body = _split_frontmatter(content)
    inline_tags = extract_inline_tags(body)
    front_tags = [f"#{tag}" for tag in extract_frontmatter_tags(frontmatter)]
    return sorted(set(inline_tags) | set(front_tags))


def add_tags(path: Path, tags: Iterable[str]) -> None:
    """Append missing tags to the file at *path*."""

    normalized = [_normalize_tag(tag) for tag in tags]
    if not normalized:
        return

    content = path.read_text(encoding="utf-8")
    frontmatter, raw_frontmatter, body = _split_frontmatter(content)
    inline_existing = set(extract_inline_tags(body))
    front_existing = {_normalize_tag(tag) for tag in extract_frontmatter_tags(frontmatter)}
    existing = inline_existing | front_existing
    to_add = [tag for tag in normalized if tag not in existing]
    if not to_add:
        return

    if raw_frontmatter:
        fm_tags = set(extract_frontmatter_tags(frontmatter))
        updated = sorted(fm_tags | {_strip_hash(tag) for tag in to_add})
        frontmatter["tags"] = updated
        new_frontmatter = _dump_frontmatter(frontmatter)
    else:
        new_frontmatter = raw_frontmatter

    if not body.endswith("\n"):
        body += "\n"
    body += " ".join(to_add) + "\n"

    path.write_text(f"{new_frontmatter}{body}", encoding="utf-8")


def remove_tags(path: Path, tags: Iterable[str]) -> None:
    """Remove tags from both inline content and frontmatter."""

    normalized = {_normalize_tag(tag) for tag in tags}
    if not normalized:
        return

    content = path.read_text(encoding="utf-8")
    frontmatter, raw_frontmatter, body = _split_frontmatter(content)

    # Remove inline tags
    def _replacement(match: re.Match[str]) -> str:
        full = f"#{match.group(1)}"
        if full in normalized:
            return ""
        return match.group(0)

    body = INLINE_TAG_PATTERN.sub(_replacement, body)

    # Remove extra whitespace produced by tag removals
    body = re.sub(r"\n{3,}", "\n\n", body)

    if raw_frontmatter:
        fm_tags = extract_frontmatter_tags(frontmatter)
        remaining = [tag for tag in fm_tags if _normalize_tag(tag) not in normalized]
        if remaining:
            frontmatter["tags"] = remaining
        else:
            frontmatter.pop("tags", None)
        new_frontmatter = _dump_frontmatter(frontmatter) if frontmatter else ""
    else:
        new_frontmatter = raw_frontmatter

    path.write_text(f"{new_frontmatter}{body}", encoding="utf-8")


def rename_tag(old: str, new: str, root: Path) -> int:
    """Rename a tag across the vault rooted at *root*.

    Returns the number of replacements performed.
    """

    old_tag = _normalize_tag(old)
    new_tag = _normalize_tag(new)

    count = 0
    for file in root.rglob("*.md"):
        content = file.read_text(encoding="utf-8")
        frontmatter, raw_frontmatter, body = _split_frontmatter(content)

        replaced_body, body_count = INLINE_TAG_PATTERN.subn(
            lambda match: new_tag if f"#{match.group(1)}" == old_tag else match.group(0),
            body,
        )
        replaced_frontmatter = raw_frontmatter
        front_count = 0
        if raw_frontmatter:
            fm_tags = extract_frontmatter_tags(frontmatter)
            updated = []
            for tag in fm_tags:
                normalized_tag = _normalize_tag(tag)
                if normalized_tag == old_tag:
                    updated.append(_strip_hash(new_tag))
                    front_count += 1
                else:
                    updated.append(tag)
            if updated:
                frontmatter["tags"] = sorted({tag for tag in updated})
            else:
                frontmatter.pop("tags", None)
            replaced_frontmatter = _dump_frontmatter(frontmatter) if frontmatter else ""

        if body_count or front_count:
            file.write_text(f"{replaced_frontmatter}{replaced_body}", encoding="utf-8")
            count += body_count + front_count

    return count
