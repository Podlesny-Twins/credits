"""Build the sandbox page from the site's own data.

    python3 sandbox/build_sandbox.py [-o sandbox/sandbox.html]

Covers are inlined as 72px data-URIs: an artifact page may not make
external requests, so a cover on the live domain would not load there.

Markup, styles and logic live in template.html / app.css / app.js next to
this file, so the page can be rebuilt a year from now.
"""
from __future__ import annotations

import base64
import io
import json
import sys
import time
from pathlib import Path

from PIL import Image

from catalog import ROOT, GENRES, ROLES, AWARDS, read_catalog

HERE = Path(__file__).resolve().parent
THUMB = 72


def thumb(cover: str, cache: dict) -> str:
    """A 72px data-URI for one cover, or "" when the file is missing."""
    if cover in cache:
        return cache[cover]
    src = ROOT / cover.lstrip("/")
    # prefer the 300px variant; the 640px one is needlessly heavy to open
    small = src.with_name(src.name.replace("ab67616d0000b273", "ab67616d00001e02"))
    src = small if small.is_file() else src
    if not src.is_file():
        cache[cover] = ""
        return ""
    im = Image.open(src).convert("RGB").resize((THUMB, THUMB), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=72, optimize=True)
    uri = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    cache[cover] = uri
    return uri


def build(out: Path, keep_state: dict | None = None) -> None:
    works, _ = read_catalog()
    cache: dict[str, str] = {}
    for w in works:
        w["thumb"] = thumb(w["cover"], cache)
        w.pop("cover", None)

    catalog = {
        "works": works,
        "genres": GENRES,
        "roles": ROLES,
        "awards": AWARDS,
    }
    page = (HERE / "template.html").read_text(encoding="utf-8")
    page = page.replace("/*APP_CSS*/", (HERE / "app.css").read_text(encoding="utf-8"))
    page = page.replace("/*APP_JS*/", (HERE / "app.js").read_text(encoding="utf-8"))
    page = page.replace('"__CATALOG__"',
                        json.dumps(catalog, ensure_ascii=False, separators=(",", ":")))
    # A rebuild must never silently drop edits the owner has not handed over
    # yet: pass the live state with --state and it is carried into the new page.
    state = {"ready": None, "edits": {}, "queue": [], "moves": [], "interview": None}
    if keep_state:
        state.update({k: v for k, v in keep_state.items() if k in state})
    # buildId identifies this catalogue snapshot; the page's local draft is only
    # restored when it belongs to the same build (see app.js), so an applied and
    # rebuilt sandbox cannot resurrect edits that already went live.
    state["buildId"] = str(int(time.time()))
    page = page.replace('"__STATE__"', json.dumps(state, ensure_ascii=False))
    out.write_text(page, encoding="utf-8")
    print(f"{out}  {len(page) / 1024:.0f} КБ  "
          f"работ: {len(works)}  обложек: {sum(1 for v in cache.values() if v)}")
    if missing := [c for c, v in cache.items() if not v]:
        print("НЕТ ОБЛОЖКИ:", *missing, sep="\n  ")


if __name__ == "__main__":
    args = sys.argv[1:]
    out = Path(args[args.index("-o") + 1]) if "-o" in args else HERE / "sandbox.html"
    keep = None
    if "--state" in args:
        src = Path(args[args.index("--state") + 1])
        keep = json.loads(src.read_text(encoding="utf-8"))
        n = len(keep.get("edits", {})) + len(keep.get("queue", [])) + len(keep.get("moves", []))
        print(f"переношу неотданные правки: {n}")
    build(out, keep)
