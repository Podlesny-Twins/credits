"""Apply sandbox edits to the site's data.

Usage:  python3 sandbox/apply_edits.py <state.json> [--dry-run]

Each field has exactly one home, and this command knows which:

    role   -> roles.json  (album: applied to every track in it)
    note   -> notes.json  (keyed by the builder's own slug)
    genre  -> data-g attribute on the tile in index.html
    award  -> data-aw attribute on the tile in index.html
    hidden -> tile is cut out of index.html into hidden.json, whole, so it
              can come back; its stale /track/<slug>/ pages are removed
    moves  -> the tile is cut and re-inserted after its anchor in index.html

Anything that fails to find its target is printed at the end. A silent
miss is the worst outcome here: the owner believes the edit landed.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

from catalog import (ROOT, INDEX, HIDDEN_FILE, TILE_RE, GENRES, ROLES, AWARDS,
                     album_map, attr, inner, load_json, read_catalog)

ROLES_FILE = ROOT / "roles.json"
NOTES_FILE = ROOT / "notes.json"
TRACK_DIR = ROOT / "track"

misses: list[str] = []
changed_moves: list[str] = []


def miss(msg: str) -> None:
    misses.append(msg)


def tile_of(doc: str, work: dict) -> str | None:
    """Locate a work's tile. Single tiles key off data-id; an album has no
    page and no id, so it falls back to its title — computed identically on
    both sides (see catalog.inner)."""
    for tile in TILE_RE.findall(doc):
        head = tile.split(">", 1)[0]
        if work["kind"] == "track":
            if attr(tile, "data-id") == work["id"] and "tile album" not in head:
                return tile
        elif "tile album" in head and inner(tile, "trk") == work["title"]:
            return tile
    return None


def set_attr(tile: str, name: str, value: str) -> str:
    """Set, replace or drop one attribute in the tile's opening tag."""
    head, rest = tile.split(">", 1)
    if re.search(rf'\s{name}="[^"]*"', head):
        head = re.sub(rf'\s{name}="[^"]*"',
                      f' {name}="{value}"' if value else "", head)
    elif value:
        head = head.replace(' data-id="', f' {name}="{value}" data-id="', 1) \
            if ' data-id="' in head else head.replace(' onclick=', f' {name}="{value}" onclick=', 1)
    return head + ">" + rest


def apply_state(state: dict, dry: bool) -> int:
    works, doc = read_catalog()
    # album tracks are editable too (their own role and description), so they
    # must be in the map — an edit that finds no target is a lost edit
    by_key = {w["key"]: w for w in works}
    for w in works:
        for tr in w["tracks"]:
            by_key.setdefault(tr["key"], {**tr, "kind": "track", "artist": w["artist"],
                                          "hidden": w["hidden"], "album": w["title"],
                                          "tracks": []})
    roles = load_json(ROLES_FILE, {})
    notes = load_json(NOTES_FILE, {})
    hidden = load_json(HIDDEN_FILE, {})
    albums = album_map(doc)
    changed: list[str] = []

    for key, edit in (state.get("edits") or {}).items():
        work = by_key.get(key)
        if not work:
            miss(f"{key}: нет такой работы в каталоге")
            continue
        label = f"{work['artist']} — {work['title']}"

        if "role" in edit:
            role = edit["role"]
            if role not in ROLES:
                miss(f"{label}: неизвестная роль {role!r}")
            else:
                ids = [work["id"]] if work["kind"] == "track" else [t["id"] for t in work["tracks"]]
                hit = [t for t in filter(None, ids) if roles.get(t) != role]
                for tid in hit:
                    roles[tid] = role
                if hit:
                    n = f" ({len(hit)} тр.)" if work["kind"] == "album" else ""
                    changed.append(f"роль {label}{n} → {ROLES[role]}")

        if "note" in edit:
            targets = [(work["slug"], label)] if work["kind"] == "track" else []
            for tr in work["tracks"]:
                if tr["key"] == key:
                    targets = [(tr["slug"], label)]
            if not targets:
                miss(f"{label}: описание некуда положить — у альбома нет страницы")
            for slug, lbl in targets:
                paras = [p.strip() for p in edit["note"].split("\n\n") if p.strip()]
                if paras:
                    if notes.get(slug) != paras:
                        notes[slug] = paras
                        changed.append(f"описание {lbl}")
                elif slug in notes:
                    del notes[slug]
                    changed.append(f"описание {lbl} — убрано")

        for field, name, allowed in (("genre", "data-g", GENRES),
                                     ("award", "data-aw", list(AWARDS) + [""])):
            if field not in edit:
                continue
            value = edit[field]
            if value not in allowed:
                miss(f"{label}: недопустимое значение {field}={value!r}")
                continue
            tile = tile_of(doc, work)
            if tile is None:
                miss(f"{label}: тайл не найден в index.html ({field})"
                     + (" — у трека внутри альбома он общий, правьте альбом"
                        if work.get("album") else ""))
                continue
            if attr(tile, name) != value:
                doc = doc.replace(tile, set_attr(tile, name, value), 1)
                changed.append(f"{field} {label} → {value or '—'}")

        if "hidden" in edit and bool(edit["hidden"]) != work["hidden"]:
            if edit["hidden"]:
                tile = tile_of(doc, work)
                if tile is None:
                    miss(f"{label}: тайл не найден в index.html (скрытие)")
                    continue
                before = doc.split(tile, 1)[0]
                prev = TILE_RE.findall(before)
                hidden[key] = {
                    "html": tile,
                    "after": attr(prev[-1], "data-id") if prev else "",
                    "after_album": inner(prev[-1], "trk") if prev and "tile album" in prev[-1].split(">", 1)[0] else "",
                }
                if work["kind"] == "album":
                    hidden[key]["album"] = albums.pop(work["title"], None)
                doc = re.sub(r"\n\s*" + re.escape(tile), "", doc, count=1)
                for slug in ([work["slug"]] if work["kind"] == "track"
                             else [t["slug"] for t in work["tracks"]]):
                    page = TRACK_DIR / slug
                    if page.is_dir():
                        if not dry:
                            shutil.rmtree(page)
                        changed.append(f"удалена страница /track/{slug}/")
                changed.append(f"скрыто: {label}")
            else:
                meta = hidden.pop(key, None)
                if not meta:
                    miss(f"{label}: нечего возвращать — записи в hidden.json нет")
                    continue
                doc = restore(doc, meta)
                if meta.get("album"):
                    albums[meta["album"]["name"]] = meta["album"]
                changed.append(f"возвращено: {label}")

    for mv in state.get("moves") or []:
        doc = apply_move(doc, by_key, mv)

    doc = sync_albums(doc, albums)

    changed += [f"порядок: {m}" for m in changed_moves]
    print("\n".join(f"  ✓ {c}" for c in changed) or "  правок нет")
    if misses:
        print("\nНЕ ПРИМЕНЕНО:")
        print("\n".join(f"  ✗ {m}" for m in misses))
    if queue := state.get("queue") or []:
        print(f"\nОЧЕРЕДЬ НА ДОБАВЛЕНИЕ ({len(queue)}) — через скилл credits-add-track:")
        for item in queue:
            extra = " ".join(filter(None, [
                f"--genre {item['genre']}" if item.get("genre") else "",
                f"--role {item['role']}" if item.get("role") else "",
            ]))
            print(f"  {item.get('url', '?')}  {extra}")
            if item.get("note"):
                print(f"      заметка: {item['note']}")

    if dry:
        print("\n--dry-run: ничего не записано")
        return 1 if misses else 0

    if changed:
        INDEX.write_text(doc, encoding="utf-8")
        ROLES_FILE.write_text(json.dumps(roles, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
        NOTES_FILE.write_text(json.dumps(notes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if hidden:
            HIDDEN_FILE.write_text(json.dumps(hidden, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        elif HIDDEN_FILE.exists():
            HIDDEN_FILE.unlink()
    return 1 if misses else 0


def apply_move(doc: str, by_key: dict, mv: dict) -> str:
    """Cut a tile and put it back after its anchor (or first in the grid).

    Tile order IS the site's curation — the hand-picked top of the grid — so a
    move is expressed relative to a neighbour, never as an absolute position:
    an index would silently mean something else after any other change.
    """
    work = by_key.get(mv.get("key"))
    if not work:
        miss(f"{mv.get('key')}: перемещение — нет такой работы")
        return doc
    label = f"{work['artist']} — {work['title']}"
    if work.get("album"):
        miss(f"{label}: трек внутри альбома нельзя двигать по сетке — у него нет своего тайла")
        return doc

    tile = tile_of(doc, work)
    if tile is None:
        miss(f"{label}: перемещение — тайл не найден (работа спрятана?)")
        return doc

    after = mv.get("after") or ""
    if after:
        anchor_work = by_key.get(after)
        anchor_tile = tile_of(doc, anchor_work) if anchor_work else None
        if anchor_tile is None:
            miss(f"{label}: перемещение — соседа {after} на сетке нет")
            return doc
    else:
        anchor_tile = None

    indent = re.search(r"\n(\s*)" + re.escape(tile), doc)
    pad = indent.group(1) if indent else "      "
    doc = re.sub(r"\n\s*" + re.escape(tile), "", doc, count=1)

    if anchor_tile is None:                      # to the very front of the grid
        first = TILE_RE.search(doc).group(0)
        doc = doc.replace(first, tile + "\n" + pad + first, 1)
        changed_moves.append(f"{label} → в начало")
    else:
        doc = doc.replace(anchor_tile, anchor_tile + "\n" + pad + tile, 1)
        a = by_key[after]
        changed_moves.append(f"{label} → после «{a['artist']} — {a['title']}»")
    return doc


def restore(doc: str, meta: dict) -> str:
    """Put a hidden tile back where it was; fall back to the end of the grid
    if its neighbour is gone."""
    tile = meta["html"]
    for cand in TILE_RE.findall(doc):
        head = cand.split(">", 1)[0]
        hit = (meta.get("after_album") and "tile album" in head
               and inner(cand, "trk") == meta["after_album"]) \
            or (meta.get("after") and attr(cand, "data-id") == meta["after"])
        if hit:
            return doc.replace(cand, cand + "\n      " + tile, 1)
    last = TILE_RE.findall(doc)[-1]
    return doc.replace(last, last + "\n      " + tile, 1)


def sync_albums(doc: str, albums: dict) -> str:
    """Rebuild var ALBUMS and the openAlbum(N) indices together.

    N is a position in the ALBUMS array, so hiding an album from the middle
    would silently shift every later tile onto the wrong album. Deriving the
    array order from the tile order makes that impossible.
    """
    order: list[dict] = []
    for tile in TILE_RE.findall(doc):
        if "tile album" in tile.split(">", 1)[0]:
            alb = albums.get(inner(tile, "trk"))
            if alb is None:
                miss(f"{inner(tile, 'trk')}: тайл альбома есть, а записи в ALBUMS нет")
                continue
            doc = doc.replace(tile, re.sub(r"openAlbum\(\d+\)",
                                           f"openAlbum({len(order)})", tile, count=1), 1)
            order.append(alb)

    orphans = [n for n in albums if n not in {a["name"] for a in order}]
    for name in orphans:
        miss(f"{name}: запись в ALBUMS без тайла на сетке")

    m = re.search(r"var ALBUMS=(\[.*?\]);", doc, re.S)
    rendered = json.dumps(order + [albums[n] for n in orphans], ensure_ascii=False)
    if rendered == m.group(1):
        return doc
    return doc[:m.start(1)] + rendered + doc[m.end(1):]


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(2)
    state = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    sys.exit(apply_state(state, "--dry-run" in sys.argv))
