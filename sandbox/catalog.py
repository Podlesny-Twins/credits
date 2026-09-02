"""Shared catalog reader for the sandbox.

Single source of truth for how the sandbox and the apply command see the
site's works. Slugs and tile parsing are imported from build_who_mixed so
the two sides can never drift apart (a divergent key = a silently lost edit).

A work is a single tile (key "t:<spotify-id>") or an album tile
(key "a:<album name>"). Hidden works live in hidden.json with their full
tile HTML so they stay in the map and can be brought back.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build_who_mixed as bwm  # noqa: E402

INDEX = ROOT / "index.html"
HIDDEN_FILE = ROOT / "hidden.json"

GENRES = ["HIPHOP", "POP", "INDIE", "ROCK"]
ROLES = {"mix": "сведение", "mm": "сведение и мастеринг", "master": "мастеринг"}
AWARDS = {"GRAM": "Грэмми", "TOP1": "№1 в чарте"}

# One tile, single or album. Attributes are read positionally-free so a tile
# with or without data-aw parses the same way.
TILE_RE = re.compile(r'<button class="tile[^"]*"[^>]*>.*?</button>', re.S)


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return default


def attr(tile: str, name: str) -> str:
    m = re.search(rf'{name}="([^"]*)"', tile.split(">", 1)[0])
    return m.group(1) if m else ""


def inner(tile: str, cls: str) -> str:
    m = re.search(rf'<span class="{cls}">(.*?)</span>', tile, re.S)
    return bwm.html.unescape(re.sub(r"<[^>]+>", "", m.group(1))) if m else ""


def cover_of(tile: str) -> str:
    m = re.search(r'<img src="([^"]+)"', tile)
    return m.group(1) if m else ""


def album_map(doc: str) -> dict:
    raw = json.loads(re.search(r"var ALBUMS=(\[.*?\]);", doc, re.S).group(1))
    return {a["name"]: a for a in raw}


def read_catalog() -> tuple[list[dict], str]:
    """Every work on the site, hidden ones included, in grid order."""
    doc = INDEX.read_text(encoding="utf-8")
    roles = bwm.load_roles()
    notes = bwm.load_notes()
    hidden = load_json(HIDDEN_FILE, {})
    albums = album_map(doc)

    # slugs for every track, computed by the site's own builder
    bwm.NOTES = notes
    tracks = bwm.extract_tracks(doc, roles)
    bwm.assign_slugs(tracks)
    slug_by_id = {t["id"]: t["slug"] for t in tracks}

    works: list[dict] = []
    seen: set[str] = set()

    def add_tile(tile: str, hidden_meta: dict | None = None):
        is_album = "tile album" in tile.split(">", 1)[0]
        artist, title = inner(tile, "art"), inner(tile, "trk")
        common = {
            "artist": artist,
            "title": title,
            "cover": cover_of(tile),
            "genre": attr(tile, "data-g"),
            "award": attr(tile, "data-aw"),
            "hidden": hidden_meta is not None,
        }
        if is_album:
            alb = albums.get(title) or (hidden_meta or {}).get("album") or {}
            key = f"a:{title}"
            if key in seen:
                return
            seen.add(key)
            works.append({**common, "key": key, "kind": "album", "id": "",
                          "year": "", "slug": "",
                          # история релиза: приклеивается ко всем его трекам
                          "note": "\n\n".join(
                              notes.get(bwm.album_note_key(artist, title), [])),
                          "tracks": [{
                              "key": f"t:{tr['id']}", "id": tr["id"],
                              "title": tr["title"], "year": tr.get("year", ""),
                              "slug": slug_by_id.get(tr["id"], ""),
                              "role": roles.get(tr["id"], "mix"),
                              "note": "\n\n".join(notes.get(slug_by_id.get(tr["id"], ""), [])),
                          } for tr in alb.get("tracks", [])]})
        else:
            tid = attr(tile, "data-id")
            key = f"t:{tid}"
            if not tid or key in seen:
                return
            seen.add(key)
            slug = slug_by_id.get(tid, "")
            works.append({**common, "key": key, "kind": "track", "id": tid,
                          "year": inner(tile, "yr"), "slug": slug,
                          "role": roles.get(tid, "mix"),
                          "note": "\n\n".join(notes.get(slug, [])),
                          "tracks": []})

    for tile in TILE_RE.findall(doc):
        add_tile(tile)
    # hidden works are absent from the document; they must stay in the map
    for meta in hidden.values():
        add_tile(meta["html"], hidden_meta=meta)

    return works, doc
