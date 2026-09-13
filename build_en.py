#!/usr/bin/env python3
"""Build the English version of credits.podlesnytwins.com into ``en/``.

The EN site is a post-processing of the *generated* RU outputs, not a second
template: same DOM, same CSS, same JS, so design parity holds by construction.

    RU source                     ->  EN output
    index.html                    ->  en/index.html
    track/index.html              ->  en/track/index.html
    track/<slug>/index.html       ->  en/track/<slug>/index.html   (redirect stubs skipped)
    faq/index.html                ->  en/faq/index.html
    track-info.json               ->  en/track-info.json
    i18n/en/llms.txt (template)   ->  en/llms.txt   ({tracks}/{artists} filled in)

Usage
-----
    python3 build_en.py            # build en/** (lenient: see below); exit 1 on untranslated UI
    python3 build_en.py --strict   # unmapped artists / untranslated stories are fatal too
    python3 build_en.py --check    # structural diff RU vs EN (tag sequences) after a build
    python3 build_en.py --quiet    # build, print only the summary

Normally run through ``python3 build_who_mixed.py`` (it calls this script at
the end; ``--no-en`` skips that). Full order:
``build_who_mixed.py`` (→ build_en.py) → ``build_tier.py`` → ``build_llms_full.py``.

Lenient mode (default) — the owner's add-track routine touches roles/notes/
index.html but not i18n/, and must not be blocked:
  (a) artist not in artists.json  → Cyrillic name kept, listed as ``artist-unmapped``;
  (b) story without a translation → the story is OMITTED on the EN page (no
      ``<p class="note">``, no hub ``<details class="story">``, no entry in
      en/track-info.json, no ⓘ button, JSON-LD description falls back to the
      role sentence); listed as ``story-untranslated``;
  (c) any other Cyrillic UI string → fatal (a template changed).
Exit 0 with a one-line ``EN: N artists unmapped, M stories untranslated`` summary
when only (a)/(b) are pending; ``--strict`` makes them fatal. Run ``--strict``
before release once the translation agent has caught up.

Romanization (track pages only): a Cyrillic release title gets a BGN/PCGN-style
transliteration once in <title>, the meta/og description, the lead sentence and
as MusicRecording ``alternateName``; a Cyrillic artist with an
``artists.json._romanization`` entry gets ``Дора (Dora)`` on its first lead
mention. Tiles, hub and home page are untouched (parity).

Rerun after: ``python3 build_who_mixed.py`` (track pages / hub / index footer changed),
any edit of ``faq/index.html``, any edit of the dictionaries in ``i18n/en/``.
Idempotent: every run regenerates ``en/**`` from scratch and prunes stale
``en/track/<slug>/`` directories.

Dictionaries (``i18n/en/``, owned by the translation agent)
-----------------------------------------------------------
- ``ui.json``         exact RU string -> EN string (text nodes, attribute values,
                      FAQ answer paragraphs *including their inline HTML*).
- ``templates.json``  patterns for generated strings with ``{artist}``, ``{title}``,
                      ``{year}``, ``{role}``, ``{album}``, ``{n}``… placeholders.
                      Accepted shapes: ``{"ru pattern": "en pattern"}``,
                      ``{"name": {"ru": …, "en": …}}`` or ``{"name": ["ru", "en"]}``.
                      A key containing ``{…}`` in ``ui.json`` is treated as a
                      pattern too.
- ``notes.json``      same keys as ``notes.json`` (slug / ``album-<slug>``),
                      translated paragraphs.
- ``artists.json``    RU artist display name -> international display name.
- ``ui.build-agent.json`` fallback for trivial technical strings (JS literals,
                      plural helper…). Lower priority than ``ui.json``.

Every Cyrillic string the transformer cannot translate is written to
``i18n/missing.txt`` (deduplicated, with file + context) and the script exits
non-zero. Allowlisted: release titles, artist names absent from artists.json
(reported separately as ``artist-unmapped``), URLs, single Cyrillic letters
used as alphabet headings in the hub.

Deliberate deviations from "same markup" (all in EN output only):
- ``<html lang="en">``, self-canonical, ``og:url``, ``og:locale``, hreflang pair.
- JSON-LD page node gets the ``/en/`` url and ``inLanguage: "en"``.
- ``plt(n)`` on the home page is replaced by an English plural helper.
- Hub ``data-q`` / ``data-artist`` search keys get the EN artist name *appended*
  (RU kept) so the search box finds "Dima Bilan" as well as "Дима Билан".
- Hub letter groups / jump links are regenerated from the EN artist names.
- Internal links whose EN counterpart does not exist (e.g. ``/edit/``) keep the
  RU URL and get a " (Russian)" suffix on the link text. ``/tier/`` has a twin
  (``/en/tier/``, rendered by build_tier.py from i18n/en/tier.json, not by this
  script), so links to it move under ``/en/`` like every other translated page.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import sys
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import build_who_mixed as bwm  # noqa: E402  (extract_tracks, slugify, notes_for…)

SITE = "https://credits.podlesnytwins.com"
I18N = ROOT / "i18n"
DICT_DIR = I18N / "en"
OUT = ROOT / "en"
MISSING_FILE = I18N / "missing.txt"

CYR = re.compile(r"[А-Яа-яЁё]")
CYR_RUN = re.compile(r"[А-Яа-яЁё][А-Яа-яЁё\-’']*")

# attributes whose *value* is human-readable copy
TEXT_ATTRS = {"alt", "title", "aria-label", "placeholder", "aria-description", "label"}
META_NAMES = {
    "description", "keywords", "og:title", "og:description", "twitter:title",
    "twitter:description", "og:site_name",
}
# JSON-LD keys whose values are never copy
LD_SKIP_KEYS = {"@id", "@type", "@context", "url", "item", "image", "sameAs",
                "alternateName", "itemListOrder", "numberOfItems", "position",
                "roleName_keep"}
LD_TITLE_TYPES = {"MusicRecording", "MusicAlbum"}


# ─────────────────────────────────────────────────────────────── romanization

ROMAN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def romanize(text: str) -> str:
    """BGN/PCGN-style transliteration, Title Case per word; digits, Latin and
    punctuation pass through. ``Тысячи зим`` -> ``Tysyachi Zim``."""
    out = []
    for word in re.split(r"(\s+)", text):
        if not word or word.isspace():
            out.append(word)
            continue
        buf = []
        for ch in word:
            low = ch.lower()
            buf.append(ROMAN[low] if low in ROMAN else ch)
        w = "".join(buf)
        if CYR.search(word):
            i = next((k for k, c in enumerate(w) if c.isalpha()), None)
            if i is not None:
                w = w[:i] + w[i].upper() + w[i + 1:]
        out.append(w)
    return "".join(out)


# ─────────────────────────────────────────────────────────────── dictionaries

def _load_json(path: Path):
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:  # a half-written file must not kill the build
        print(f"warn: {path.name} is not valid JSON ({e}); ignored", file=sys.stderr)
        return None


def _pairs(obj) -> list[tuple[str, str]]:
    """Normalise a dictionary file into (ru, en) pairs (see module docstring).

    Walks nested dicts (``roles.ROLE_WORD.mix``), skips ``_``-prefixed keys and
    expands ``"a | b | c" -> "x | y"`` plural forms (first RU form -> first EN
    form, the other RU forms -> the last EN form).
    """
    out: list[tuple[str, str]] = []

    def add(ru: str, en: str):
        rus, ens = [x.strip() for x in ru.split("|")], [x.strip() for x in en.split("|")]
        if len(rus) > 1 and len(ens) > 1 and all("{" in x for x in rus + ens):
            for i, r in enumerate(rus):
                out.append((r, ens[0] if i == 0 else ens[-1]))
        else:
            out.append((ru, en))

    def walk(node):
        if isinstance(node, dict):
            if isinstance(node.get("ru"), str) and isinstance(node.get("en"), str):
                add(node["ru"], node["en"])
                return
            for k, v in node.items():
                if isinstance(k, str) and k.startswith("_"):
                    continue
                if isinstance(v, str):
                    add(k, v)
                elif isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(x, str) for x in v):
                    add(v[0], v[1])
                else:
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(obj)
    return out


PLACEHOLDER = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


NUMERIC_PH = {"n", "tracks", "artists", "total", "count", "year"}
CONST_PH = {"site": SITE}


NUM_SPAN = re.compile(r'<span[^>]*>(.*?)</span>')
NUM_WRAP = r'(?:<span[^>]*>)?'
NUM_UNWRAP = r'(?:</span>)?'


def _esc_literal(lit: str, html_mode: bool) -> str:
    """re.escape, but a .num span in the pattern matches with or without the span."""
    if not html_mode or not NUM_SPAN.search(lit):
        return re.escape(lit)
    out, pos = [], 0
    for m in NUM_SPAN.finditer(lit):
        out.append(re.escape(lit[pos:m.start()]))
        out.append(NUM_WRAP + re.escape(m.group(1)) + NUM_UNWRAP)
        pos = m.end()
    out.append(re.escape(lit[pos:]))
    return "".join(out)


def _ph_regex(name: str, html_mode: bool = False) -> str:
    if name in CONST_PH:
        return re.escape(CONST_PH[name])
    if name in NUMERIC_PH:
        return NUM_WRAP + r"\d+" + NUM_UNWRAP if html_mode else r"\d+"
    if any(x in name for x in ("anchor", "url", "href", "link")):
        return r"[^\s\"'<>]*"
    if name in ("title", "album", "name", "release"):
        return r"[^<>\n«»“”]*?"   # a title never carries the quotes around it
    return r"[^<>\n]*?"          # never crosses a tag or a line


class Template:
    def __init__(self, ru: str, en: str, html_mode: bool | None = None):
        # matched against *stripped* strings; the source's own whitespace is kept
        ru, en = ru.strip(), en.strip()
        self.ru, self.en = ru, en
        parts, pos, names = [], 0, []
        phs = list(PLACEHOLDER.finditer(ru))
        if html_mode is None:
            html_mode = "<" in ru
        for m in phs:
            parts.append(_esc_literal(ru[pos:m.start()], html_mode))
            name = m.group(1)
            rx = _ph_regex(name, html_mode)
            if m is phs[-1] and m.end() == len(ru) and rx.endswith("*?"):
                rx = rx[:-1]           # trailing placeholder: greedy, swallow the tail
            if name in names or name in CONST_PH:
                parts.append(f"(?P={name})" if name in names else rx)
            else:
                parts.append(f"(?P<{name}>{rx})")
            if name not in names and name not in CONST_PH:
                names.append(name)
            pos = m.end()
        parts.append(_esc_literal(ru[pos:], html_mode))
        body = "".join(parts)
        self.names = names
        self.literal_len = len(PLACEHOLDER.sub("", ru).strip())
        self.usable = self.literal_len > 0      # "{role}" -> "{role}" would match anything
        self.numeric_only = bool(names) and all(n in NUMERIC_PH for n in names)
        self.full = re.compile(rf"^{body}$")
        self.search = re.compile(body)
        self.has_html = html_mode


def _strip_tags(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s))


class Dictionaries:
    def __init__(self):
        self.ui: dict[str, str] = {}
        self.templates: list[Template] = []
        self.artists: dict[str, str] = {}
        self.notes: dict[str, list[str]] = {}
        self.llms_template: str | None = None
        self.loaded: list[str] = []

        ui_fallback = _load_json(DICT_DIR / "ui.build-agent.json")
        ui_main = _load_json(DICT_DIR / "ui.json")
        tpl = _load_json(DICT_DIR / "templates.json")
        for src, name in ((ui_fallback, "ui.build-agent.json"), (ui_main, "ui.json")):
            if src is None:
                continue
            self.loaded.append(name)
            for ru, en in _pairs(src):
                if PLACEHOLDER.search(ru):
                    self.templates.append(Template(ru, en))
                else:
                    self.ui[ru.strip()] = en  # later files override earlier (ui.json wins)
        self.tpl_literals: dict[str, str] = {}   # templates.json entries without placeholders
        if tpl is not None:
            self.loaded.append("templates.json")
            for ru, en in _pairs(tpl):
                self.templates.append(Template(ru, en))
                if not PLACEHOLDER.search(ru):
                    self.tpl_literals[ru.strip()] = en.strip()
            # the roles table is authoritative for {verb}: the hub h1 reuses the
            # same RU words ("Кто свёл") with a different EN rendering
            verbs = (tpl.get("roles") or {}).get("ROLE_VERB") if isinstance(tpl, dict) else None
            if isinstance(verbs, dict):
                for v in verbs.values():
                    if isinstance(v, dict) and "ru" in v and "en" in v:
                        self.tpl_literals[v["ru"].strip()] = v["en"].strip()
        # plain-text twins of inline-HTML entries: the FAQ JSON-LD carries the
        # same answers with tags stripped
        for ru, en in list(self.ui.items()):
            if "<" in ru:
                pr, pe = _strip_tags(ru), _strip_tags(en)
                self.ui.setdefault(pr, pe)
        for t in list(self.templates):
            if t.has_html:
                self.templates.append(Template(_strip_tags(t.ru), _strip_tags(t.en)))
            elif any(n in NUMERIC_PH for n in t.names):
                self.templates.append(Template(t.ru, t.en, html_mode=True))
        # later definitions of the same RU pattern win (ui.json < templates.json)
        seen: dict[tuple, Template] = OrderedDict()
        for t in self.templates:
            seen[(t.ru, t.has_html)] = t
        self.templates = sorted((t for t in seen.values() if t.usable), key=lambda t: -len(t.ru))

        self.romanization: dict[str, str] = {}
        art = _load_json(DICT_DIR / "artists.json")
        if art is not None:
            self.loaded.append("artists.json")
            if isinstance(art, dict) and isinstance(art.get("_romanization"), dict):
                self.romanization = {str(k).strip(): str(v).strip() for k, v in art["_romanization"].items()}
            for ru, en in _pairs(art):
                if ru.strip():
                    self.artists[ru.strip()] = en.strip()
        notes = _load_json(DICT_DIR / "notes.json")
        if isinstance(notes, dict):
            self.loaded.append("notes.json")
            for k, v in notes.items():
                if isinstance(v, str):
                    v = [v]
                if isinstance(v, list):
                    self.notes[k] = [str(p) for p in v]
        p = DICT_DIR / "llms.txt"
        if p.is_file():
            self.loaded.append("llms.txt")
            self.llms_template = p.read_text(encoding="utf-8")

        # fragment table: longest first, word-boundary aware
        frags = [(k, v) for k, v in self.ui.items() if CYR.search(k) and len(k) >= 3]
        frags += [(k, v) for k, v in self.artists.items() if k != v]
        self.fragments = sorted(set(frags), key=lambda kv: -len(kv[0]))
        # [switcher] EN-side label/aria for the language switcher (RU pages carry "EN" / "Switch to English")
        self.switcher = {"label": "RU", "aria": "Переключить на русский"}
        for src in (ui_fallback, ui_main):
            if isinstance(src, dict) and isinstance(src.get("_switcher"), dict):
                self.switcher.update({k: str(v) for k, v in src["_switcher"].items()})
        self.contact_by_href: dict[str, str] = {}
        if isinstance(ui_main, dict) and isinstance(ui_main.get("_contact_by_href"), dict):
            self.contact_by_href = {str(k): str(v) for k, v in ui_main["_contact_by_href"].items()}


# ─────────────────────────────────────────────────────────────── site model

class Site:
    """Everything the transformer needs to know about the RU catalogue."""

    def __init__(self):
        doc = (ROOT / "index.html").read_text(encoding="utf-8")
        roles = bwm.load_roles()
        bwm.NOTES = bwm.load_notes()
        self.tracks = bwm.extract_tracks(doc, roles)
        bwm.assign_slugs(self.tracks)
        self.by_slug = {t["slug"]: t for t in self.tracks}
        self.titles: set[str] = set()
        self.artist_names: set[str] = set()
        for t in self.tracks:
            self.titles.add(t["title"])
            if t.get("album"):
                self.titles.add(t["album"])
            for tok in re.split(r", |;", t["artist"]):
                tok = tok.replace("*", "").strip()
                if tok:
                    self.artist_names.add(tok)
                    self.artist_names.add(bwm.canon(tok))
            for f in bwm.feat_of(t):
                self.artist_names.add(f)
        am = re.search(r"var ALBUMS=(\[.*?\]);", doc, re.S)
        if am:
            for a in json.loads(am.group(1)):
                self.titles.add(a["name"])
                for t in a["tracks"]:
                    self.titles.add(t["title"])
        self.primary_artists = OrderedDict()
        for t in self.tracks:
            self.primary_artists.setdefault(bwm.primary_of(t["artist"]), True)
        self.n_tracks = len(self.tracks)
        self.n_artists = len(self.primary_artists)
        counts = getattr(bwm, "catalog_counts", None)
        if callable(counts):
            try:
                c = counts(self.tracks)
                self.n_tracks = int(c.get("tracks", c.get("works", self.n_tracks)))
                self.n_artists = int(c.get("artists", self.n_artists))
            except Exception:
                pass
        else:  # the hub's own counter line is the published truth
            hub = ROOT / "track" / "index.html"
            if hub.is_file():
                mm = re.search(r'class="stat">(\d+)[^<]*?(\d+)', hub.read_text(encoding="utf-8"))
                if mm:
                    self.n_tracks, self.n_artists = int(mm.group(1)), int(mm.group(2))
        # release titles containing Cyrillic, longest first (allowlist stripping)
        self.cyr_titles = sorted((x for x in self.titles if CYR.search(x)), key=len, reverse=True)
        self.cyr_artists = sorted((x for x in self.artist_names if CYR.search(x)), key=len, reverse=True)

        # RU track pages that are real pages (not retired-slug redirects)
        self.track_pages: list[str] = []
        for d in sorted((ROOT / "track").iterdir()):
            f = d / "index.html"
            if not f.is_file():
                continue
            if 'http-equiv="refresh"' in f.read_text(encoding="utf-8")[:1500]:
                continue
            self.track_pages.append(d.name)
        # the static set is owned by build_who_mixed (hreflang + sitemap use the
        # same one); it includes /tier/, which build_tier.py renders for EN
        self.en_paths = {"/" + p for p in bwm.EN_STATIC} | {f"/track/{s}/" for s in self.track_pages}


# ─────────────────────────────────────────────────────────────── missing log

class Missing:
    def __init__(self):
        self.items: "OrderedDict[str, tuple[str, str, int]]" = OrderedDict()
        self.artists: "OrderedDict[str, str]" = OrderedDict()
        self.stories: "OrderedDict[str, str]" = OrderedDict()   # slug -> note key(s)

    def add_story(self, slug: str, keys: list[str]):
        self.stories.setdefault(slug, ", ".join(keys))

    def add(self, text: str, file: str, ctx: str):
        text = " ".join(text.split())
        if not text:
            return
        if len(text) > 200:
            text = text[:200] + "…"
        if text in self.items:
            f, c, n = self.items[text]
            self.items[text] = (f, c, n + 1)
        else:
            self.items[text] = (file, ctx, 1)

    def add_artist(self, name: str, file: str):
        self.artists.setdefault(name, file)

    def write(self):
        lines = []
        for text, (f, c, n) in self.items.items():
            more = f" (+{n - 1} more)" if n > 1 else ""
            lines.append(f"{f}\t{c}{more}\t{text}")
        for name, f in self.artists.items():
            lines.append(f"{f}\tartist-unmapped\t{name}")
        for slug, keys in self.stories.items():
            lines.append(f"track/{slug}/index.html\tstory-untranslated\t{keys}")
        MISSING_FILE.parent.mkdir(parents=True, exist_ok=True)
        MISSING_FILE.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        return len(self.items), len(self.artists), len(self.stories)


# ─────────────────────────────────────────────────────────────── resolver

class Resolver:
    def __init__(self, d: Dictionaries, site: Site, missing: Missing):
        self.d, self.site, self.missing = d, site, missing
        self.file = "?"
        self.notes_plain: dict[str, str] = {}   # RU paragraph -> EN paragraph
        self.notes_html: dict[str, str] = {}    # linkified RU -> linkified EN
        self.untranslated_keys: set[str] = set()
        self.untranslated_html: list[str] = []    # linkified RU paragraphs to drop
        self.untranslated_plain: list[str] = []
        for key, paras in bwm.NOTES.items():
            en = d.notes.get(key)
            if not en or len(en) != len(paras):
                if paras:
                    self.untranslated_keys.add(key)
                    self.untranslated_html += [bwm.linkify(p) for p in paras]
                    self.untranslated_plain += list(paras)
                continue
            for ru_p, en_p in zip(paras, en):
                self.notes_plain[ru_p] = en_p
                self.notes_html[bwm.linkify(ru_p)] = bwm.linkify(en_p)
        self._notes_sorted = sorted(self.notes_plain, key=len, reverse=True)
        self.untranslated_plain.sort(key=len, reverse=True)
        self.untranslated_html.sort(key=len, reverse=True)
        # strings the translator wrote verbatim (quoted Cyrillic kept on purpose)
        self._trusted = set(d.ui.values())
        self._trusted_blob = "\x00".join(_strip_tags(v) for v in d.ui.values() if "<" in v)
        self._en_paras = set(self.notes_plain.values()) | set(self.notes_html.values())

    # -- helpers --------------------------------------------------------
    def artist(self, name: str) -> str:
        """Translate an artist display string ('A, B' / 'A;B' lists supported)."""
        def one(tok: str) -> str:
            star = tok.endswith("*")
            core = tok.rstrip("*").strip()
            if core in self.d.artists:
                return self.d.artists[core] + ("*" if star else "")
            canon = bwm.canon(core)
            if canon in self.d.artists:
                return self.d.artists[canon] + ("*" if star else "")
            if CYR.search(core):
                self.missing.add_artist(core, self.file)
            return tok
        if ", " in name:
            return ", ".join(one(x) for x in name.split(", "))
        if ";" in name:
            return ";".join(one(x) for x in name.split(";"))
        return one(name)

    def role(self, word: str) -> str:
        en = self.d.ui.get(word) or self.d.ui.get(word.capitalize()) or self.d.ui.get(word.lower())
        if en is None:
            return word
        if word[:1].islower():
            return en[:1].lower() + en[1:]
        if word[:1].isupper():
            return en[:1].upper() + en[1:]
        return en

    def _known_artist(self, v: str) -> bool:
        toks = [x.replace("*", "").strip() for x in re.split(r", |;", html.unescape(v))]
        return all((not CYR.search(x)) or x in self.site.artist_names or x in self.d.artists
                   for x in toks)

    def _fill(self, t: Template, m: re.Match, html_ctx: bool = False) -> str:
        vals = dict(CONST_PH)
        for name in t.names:
            v = m.group(name) or ""
            if name.startswith("artist") and "anchor" not in name and "url" not in name:
                if not self._known_artist(v):
                    raise _NoMatch
            if t.literal_len < 12 and name in ("title", "album") and html.unescape(v) not in self.site.titles:
                raise _NoMatch
            if name in ("title", "album", "name", "release", "slug"):
                vals[name] = v
            elif name in NUMERIC_PH:
                wrapped_in_en = re.search(r">\s*\{" + name + r"\}\s*<", t.en) is not None
                digits = re.search(r"\d+", v)
                vals[name] = digits.group(0) if (wrapped_in_en and digits) else v
            elif name.startswith("artist") or name == "feat":
                vals[name] = self.artist(v) if not any(x in name for x in ("anchor", "url")) else map_link(v, self.site)[0]
            elif any(x in name for x in ("anchor", "url", "href", "link")):
                vals[name] = map_link(v, self.site)[0]
            elif name in ("role", "role_lower"):
                vals[name] = self.role(v)
            elif name == "verb" and v.strip() in self.d.tpl_literals:
                vals[name] = self.d.tpl_literals[v.strip()]   # ROLE_VERB beats the hub h1 entry
            else:   # nested pattern / ui entry: year_bit, album_suffix, role_alt, verb…
                vals[name] = self.resolve(v, ctx="template", report=False, html_ctx=html_ctx) if v.strip() else v
        return PLACEHOLDER.sub(lambda mm: vals.get(mm.group(1), mm.group(0)), t.en)

    def leftover(self, s: str, quotes_ok: bool = False) -> list[str]:
        """Cyrillic runs that are not release titles / artist names / single letters.

        quotes_ok: Cyrillic kept on purpose inside quotes (a lyric, a title of a
        release outside the catalogue) is allowed — used for translated stories.
        """
        if quotes_ok:
            s = re.sub(r"[«“\"][^»”\"]*[»”\"]", " ", s)
        for tt in self.site.cyr_titles:
            s = s.replace(tt, " ")
        for a in self.site.cyr_artists:
            s = s.replace(a, " ")
        for ru_p in self._notes_sorted:            # already-known paragraphs
            if ru_p in s:
                s = s.replace(ru_p, " ")
        return [r for r in CYR_RUN.findall(s) if len(r) > 1]

    def _is_story(self, s: str) -> bool:
        """True when s contains (or is) a translated story paragraph."""
        return any(en_p and en_p in s for en_p in self._en_paras)

    # -- main entry -------------------------------------------------------
    def resolve(self, raw: str, ctx: str = "text", report: bool = True,
                html_ctx: bool = False) -> str:
        """Translate one human-readable string; whitespace around it is kept."""
        s = raw.strip()
        if not s:
            return raw
        lead = raw[: len(raw) - len(raw.lstrip())]
        tail = raw[len(raw.rstrip()):]

        out = self._resolve_core(s, html_ctx)
        if not html_ctx and "<" not in s and "<" in out:
            out = _strip_tags(out)          # a dictionary value re-emitting markup into plain text
        trusted = out in self._trusted or (len(out) > 20 and out in self._trusted_blob)
        if report and not trusted and self.leftover(out, quotes_ok=self._is_story(out)):
            self.missing.add(s, self.file, ctx)
        return lead + out + tail

    def _resolve_core(self, s: str, html_ctx: bool) -> str:
        d = self.d
        # 1. exact
        if s in d.ui:
            return d.ui[s]
        # 2. artist list
        if s in d.artists or (", " in s and all(x.strip() in d.artists or not CYR.search(x)
                                                 for x in s.split(", "))):
            return self.artist(s)
        if not CYR.search(s):
            return s
        # 3. full template match
        for t in d.templates:
            if t.has_html and not html_ctx:
                continue
            m = t.full.match(s)
            if m:
                try:
                    return self._fill(t, m, html_ctx)
                except _NoMatch:
                    continue
        # 4. story paragraphs embedded in a longer string (JSON-LD description);
        #    untranslated ones are dropped — never Russian prose on an EN page
        out = s
        for ru_p in self.untranslated_plain:
            if ru_p in out:
                out = re.sub(r"\s*" + re.escape(ru_p), "", out)
        for ru_p in self._notes_sorted:
            if ru_p in out:
                out = out.replace(ru_p, self.notes_plain[ru_p])
        if html_ctx:
            for ru_h, en_h in self.notes_html.items():
                if ru_h in out:
                    out = out.replace(ru_h, en_h)
        # 5. templates as substrings (long literal part only)
        for t in d.templates:
            if t.has_html and not html_ctx:
                continue
            if t.literal_len < (4 if t.numeric_only else 12):
                continue
            out = t.search.sub(lambda m, t=t: _try_fill(self, t, m, html_ctx), out)
        # 6. fragments (ui keys + artist names), word-boundary aware; release
        #    titles are shielded first so "Все" inside «Все пройдет» stays put
        shield: list[str] = []
        for tt in self.site.cyr_titles:
            if tt in out:
                shield.append(tt)
                out = out.replace(tt, f"\x01{len(shield) - 1}\x01")
        for ru, en in d.fragments:
            if ru in out:
                out = _replace_word(out, ru, en)
        out = re.sub(r"\x01(\d+)\x01", lambda m: shield[int(m.group(1))], out)
        return out


class _NoMatch(Exception):
    pass


def mirror_num_spans(ru_html: str, en_html: str) -> str:
    """Wrap in EN the numbers the RU markup wraps in <span …>, when EN lost the span."""
    for sp in re.finditer(r"(<span[^>]*>)([^<]*)</span>", ru_html):
        open_tag, inner = sp.group(1), sp.group(2)
        if re.search(r"<span[^>]*>" + re.escape(inner) + "</span>", en_html):
            continue
        for cand in OrderedDict.fromkeys([inner, inner.replace(" ", ","), inner.replace("\u00a0", ","),
                                          inner.replace(" ", ""), inner.replace("\u00a0", " ")]):
            if not cand.strip():
                continue
            pat = re.compile(r"(?<![\w,.<>\"=/-])" + re.escape(cand) + r"(?![\w,.<>\"=/-])")
            hit = None
            for mm in pat.finditer(en_html):
                # must sit in text, not inside a tag or an existing span
                before = en_html[: mm.start()]
                if before.rfind("<") <= before.rfind(">") and not re.search(r"<span[^>]*>[^<]*$", before):
                    hit = mm
                    break
            if hit:
                en_html = en_html[: hit.start()] + open_tag + cand + "</span>" + en_html[hit.end():]
                break
    return en_html


def _try_fill(res, t, m, html_ctx):
    try:
        out = res._fill(t, m, html_ctx)
    except _NoMatch:
        return m.group(0)
    # counter spans: mirror the RU source's exact <span …> around the same
    # number (attribute parity), unwrap when the RU source has no span there
    if html_ctx and NUM_SPAN.search(out):
        src = m.group(0)

        def mirror(mm: re.Match) -> str:
            inner = mm.group(1)
            ru_span = re.search(r"<span[^>]*>" + re.escape(inner) + "</span>", src)
            return ru_span.group(0) if ru_span else inner
        out = NUM_SPAN.sub(mirror, out)
    if html_ctx:
        out = mirror_num_spans(m.group(0), out)
    return out


def _replace_word(s: str, ru: str, en: str) -> str:
    pat = re.compile(rf"(?<![А-Яа-яЁёA-Za-z]){re.escape(ru)}(?![А-Яа-яЁёA-Za-z])")
    return pat.sub(lambda m: en, s)


# ─────────────────────────────────────────────────────────────── html lexer

TOKEN = re.compile(
    r"(?P<comment><!--.*?-->)"
    r"|(?P<script><script\b[^>]*>.*?</script\s*>)"
    r"|(?P<style><style\b[^>]*>.*?</style\s*>)"
    r"|(?P<doctype><!DOCTYPE[^>]*>)"
    r"|(?P<tag></?[a-zA-Z][^\s/>]*(?:\s+[^\s=/>]+(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+))?)*\s*/?>)"
    r"|(?P<text>[^<]+|<)",
    re.S | re.I,
)
ATTR = re.compile(r"""([^\s=/>]+)(\s*=\s*)("([^"]*)"|'([^']*)'|([^\s>]+))""")
TAG_NAME = re.compile(r"<(/?)([a-zA-Z][^\s/>]*)")


def tag_name(tok: str) -> tuple[bool, str]:
    m = TAG_NAME.match(tok)
    return (m.group(1) == "/", m.group(2).lower()) if m else (False, "")


def get_attr(tok: str, name: str) -> str | None:
    for m in ATTR.finditer(tok):
        if m.group(1).lower() == name:
            return html.unescape(m.group(4) if m.group(4) is not None
                                 else m.group(5) if m.group(5) is not None else m.group(6))
    return None


def set_attr(tok: str, name: str, value: str) -> str:
    """Replace the value of an existing attribute (quotes/spacing preserved)."""
    def sub(m: re.Match) -> str:
        if m.group(1).lower() != name:
            return m.group(0)
        v = html.escape(value, quote=True)
        q = m.group(3)[0] if m.group(3)[0] in "\"'" else '"'
        return f"{m.group(1)}{m.group(2)}{q}{v}{q}"
    return ATTR.sub(sub, tok)


# ─────────────────────────────────────────────────────────────── link mapping

def map_link(href: str, site: Site) -> tuple[str, bool]:
    """(new href, is_ru_only). Internal links move under /en/ when the page exists."""
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return href, False
    u = urlsplit(href)
    internal = (u.scheme in ("http", "https") and u.netloc == urlsplit(SITE).netloc) or (
        not u.scheme and not u.netloc and href.startswith("/"))
    if not internal:
        return href, False
    path = u.path or "/"
    if path.startswith("/en/"):
        return href, False
    if not path.endswith("/") and "." not in path.rsplit("/", 1)[-1]:
        path += "/"
    if path in site.en_paths:
        new_path = "/en" + path
        prefix = f"{u.scheme}://{u.netloc}" if u.scheme else ""
        rest = ("?" + u.query if u.query else "") + ("#" + u.fragment if u.fragment else "")
        return prefix + new_path + rest, False
    # assets and files keep working from the root
    if "." in path.rsplit("/", 1)[-1] or path.startswith("/covers/"):
        return href, False
    return href, True  # RU-only page (edit, …)


# ─────────────────────────────────────────────────────────────── transformer

class Page:
    def __init__(self, ru_rel: str, en_rel: str, site: Site, d: Dictionaries, res: Resolver):
        self.ru_rel, self.en_rel = ru_rel, en_rel
        self.site, self.d, self.res = site, d, res
        self.ru_url = SITE + "/" + ru_rel.replace("index.html", "")
        self.en_url = SITE + "/en/" + ru_rel.replace("index.html", "")
        self.en_path = "/" + ru_rel.replace("index.html", "")
        self.kind = ("home" if ru_rel == "index.html" else
                     "hub" if ru_rel == "track/index.html" else
                     "faq" if ru_rel == "faq/index.html" else "track")
        self.slug = ru_rel.split("/")[1] if self.kind == "track" else ""

    # -- whole-document pre-pass (inline-HTML dictionary entries) -----------
    def prepass(self, doc: str) -> str:
        parts = re.split(r"(<script\b[^>]*>.*?</script\s*>|<style\b[^>]*>.*?</style\s*>)", doc, flags=re.S | re.I)
        return "".join(p if i % 2 else self._prepass_markup(p) for i, p in enumerate(parts))

    def _prepass_markup(self, doc: str) -> str:
        doc = self.drop_untranslated_stories(doc)
        for ru, en in self.d.ui.items():
            if "<" in ru and ru in doc:
                doc = doc.replace(ru, mirror_num_spans(ru, en))
        for ru_h, en_h in self.res.notes_html.items():
            if ru_h in doc:
                doc = doc.replace(ru_h, en_h)
        for t in self.d.templates:
            if t.has_html:
                doc = t.search.sub(lambda m, t=t: _try_fill(self.res, t, m, True), doc)
        return doc

    def drop_untranslated_stories(self, doc: str) -> str:
        """Remove <p class="note"> / <details class="story"> blocks whose copy has
        no translation (lenient mode). The RU page keeps them; EN omits them."""
        if not self.res.untranslated_html:
            return doc
        bad = set(self.res.untranslated_html)

        def details(m: re.Match) -> str:
            body = m.group(0)
            return "" if any(h in body for h in bad) else body
        doc = re.sub(r'<details class="story">.*?</details>', details, doc, flags=re.S)
        for h in bad:
            doc = doc.replace(f'\n  <p class="note">{h}</p>', "")
            doc = doc.replace(f'<p class="note">{h}</p>', "")
        return doc

    def untranslated_story_keys(self, tr: dict) -> list[str]:
        keys = ([bwm.album_note_key(tr["artist"], tr["album"])] if tr.get("album") else []) + [tr["slug"]]
        return [k for k in keys if k in self.res.untranslated_keys]

    # -- head ------------------------------------------------------------
    def head(self, doc: str) -> str:
        doc = doc.replace('<html lang="ru">', '<html lang="en">', 1)
        # drop any hreflang links the RU page already carries; we add our own pair
        doc = re.sub(r'\n?<link rel="alternate" hreflang="[^"]*" href="[^"]*"\s*/?>', "", doc)
        doc = re.sub(r'<link rel="canonical" href="[^"]*">',
                     f'<link rel="canonical" href="{self.en_url}">\n'
                     f'<link rel="alternate" hreflang="ru" href="{self.ru_url}">\n'
                     f'<link rel="alternate" hreflang="en" href="{self.en_url}">\n'
                     f'<link rel="alternate" hreflang="x-default" href="{self.en_url}">',
                     doc, count=1)
        doc = re.sub(r'<meta property="og:url" content="[^"]*">',
                     f'<meta property="og:url" content="{self.en_url}">', doc, count=1)
        doc = re.sub(r'<meta property="og:locale" content="[^"]*">',
                     '<meta property="og:locale" content="en_US">', doc, count=1)
        return doc

    # -- JSON-LD ---------------------------------------------------------
    def ld(self, text: str) -> str:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return text
        self._ld_walk(data, None, None)
        return json.dumps(data, ensure_ascii=False)

    def _ld_walk(self, node, key, parent_type):
        res = self.res
        if isinstance(node, dict):
            t = node.get("@type")
            ptype = t if isinstance(t, str) else parent_type
            if ptype == "MusicRecording" and isinstance(node.get("name"), str) and CYR.search(node["name"]) \
                    and self.kind == "track" and "alternateName" not in node:
                node["alternateName"] = romanize(node["name"])
            if ptype in ("WebPage", "CollectionPage", "FAQPage", "AboutPage", "ItemPage") and "url" in node:
                u, _ = map_link(node["url"], self.site)
                node["url"] = u
                if isinstance(node.get("@id"), str) and node["@id"].startswith(node.get("url", "").replace("/en/", "/")):
                    node["@id"] = node["@id"].replace(SITE + "/", SITE + "/en/", 1)
                node["inLanguage"] = "en"
            for k, v in list(node.items()):
                if k in LD_SKIP_KEYS:
                    # [geo-ru Phase 2] the studio entity is one node shared by
                    # both languages (same @id) — its url stays the RU home
                    if k == "url" and node.get("@id") == bwm.STUDIO_ID:
                        continue
                    if k in ("url", "item") and isinstance(v, str):
                        node[k] = map_link(v, self.site)[0]
                    continue
                if isinstance(v, str):
                    if k == "name" and ptype in LD_TITLE_TYPES:
                        continue                                   # release title
                    if k == "name" and ptype in ("MusicGroup", "Person") and key == "byArtist":
                        node[k] = res.artist(v)
                    elif k == "name" and key == "byArtist":
                        node[k] = res.artist(v)
                    elif k == "name" and ptype == "MusicGroup" and key is None and v != "Podlesny Twins":
                        node[k] = res.artist(v)
                    elif k == "roleName":
                        node[k] = res.resolve(v, ctx="json-ld roleName")
                    elif CYR.search(v) or v.strip() in self.d.ui:
                        node[k] = res.resolve(v, ctx=f"json-ld {k}")
                else:
                    self._ld_walk(v, k, ptype)
        elif isinstance(node, list):
            for x in node:
                self._ld_walk(x, key, parent_type)

    # -- scripts -----------------------------------------------------------
    def script(self, tok: str) -> str:
        m = re.match(r"(<script\b[^>]*>)(.*)(</script\s*>)$", tok, re.S | re.I)
        if not m:
            return tok
        open_tag, body, close = m.groups()
        if 'application/ld+json' in open_tag:
            return open_tag + self.ld(body) + close
        if 'type="application/json"' in open_tag:
            return tok
        if not body.strip():
            return tok
        # album array on the home page: translate artist display names only
        am = re.search(r"var ALBUMS=(\[.*?\]);\n", body, re.S)
        albums_js = ""
        if am:
            albums = json.loads(am.group(1))
            for a in albums:
                a["artist"] = self.res.artist(a["artist"])
            albums_js = json.dumps(albums, ensure_ascii=False)
            body = body[: am.start(1)] + "\0ALBUMS\0" + body[am.end(1):]
        body = body.replace("fetch('/track-info.json')", "fetch('/en/track-info.json')")
        body = body.replace("'/track/'", "'/en/track/'").replace('"/track/"', '"/en/track/"')
        if "function plt(n)" in body:
            body = re.sub(r"function plt\(n\)\{[^}]*\}",
                          "function plt(n){return n+' '+(n===1?'track':'tracks');}", body, count=1)

        def lit(m: re.Match) -> str:
            q, inner = m.group(1), m.group(2)
            if not CYR.search(inner):
                return m.group(0)
            en = re.sub(r"  +", " ", self.res.resolve(inner, ctx="js-literal"))
            return q + en.replace(q, "\\" + q) + q

        # string literals (comments are left alone but scanned below)
        body_no_comments = re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), body, flags=re.S)
        pieces, pos = [], 0
        for m in re.finditer(r"""(['"])((?:\\.|(?!\1)[^\\\n])*)\1""", body_no_comments):
            pieces.append(body[pos:m.start()])
            pieces.append(lit(m))
            pos = m.end()
        pieces.append(body[pos:])
        return open_tag + "".join(pieces).replace("\0ALBUMS\0", albums_js) + close

    # -- tags ----------------------------------------------------------------
    def tag(self, tok: str) -> tuple[str, bool]:
        """Returns (new tag, link_is_ru_only)."""
        closing, name = tag_name(tok)
        if closing:
            return tok, False
        ru_only = False
        href = get_attr(tok, "href")
        if href is not None and name in ("a", "link", "area"):
            rel = (get_attr(tok, "rel") or "").lower()
            if name == "link" and rel in ("canonical", "alternate"):
                pass  # handled in head()
            else:
                new, ru_only = map_link(href, self.site)
                if new != href:
                    tok = set_attr(tok, "href", new)
        if name == "meta":
            key = (get_attr(tok, "name") or get_attr(tok, "property") or "").lower()
            content = get_attr(tok, "content")
            if key in META_NAMES and content:
                tok = set_attr(tok, "content", self.res.resolve(content, ctx=f"meta {key}"))
            return tok, False
        for attr in TEXT_ATTRS:
            v = get_attr(tok, attr)
            if v and v.strip():
                nv = self.res.resolve(v, ctx=f"attr {attr}")
                if nv != v:
                    tok = set_attr(tok, attr, nv)
        # [switcher] on EN pages the switcher always points back at the RU twin
        if name == "a" and "pflang" in (get_attr(tok, "class") or "").split():
            tok = set_attr(tok, "href", self.ru_url)
            tok = set_attr(tok, "hreflang", "ru")
            tok = set_attr(tok, "lang", "ru")
            tok = set_attr(tok, "aria-label", self.d.switcher["aria"])
        if self.kind == "hub":
            for attr in ("data-artist", "data-q"):
                v = get_attr(tok, attr)
                if v:
                    extra = self._search_extra(v)
                    if extra:
                        tok = set_attr(tok, attr, v + " " + extra)
        return tok, ru_only

    def _search_extra(self, v: str) -> str:
        """EN artist names (lowercased) whose RU form occurs in a search key."""
        found = []
        for ru, en in self.d.artists.items():
            if ru != en and ru.lower() in v:
                found.append(en.lower())
        return " ".join(OrderedDict.fromkeys(found))

    # -- document ------------------------------------------------------------
    def run(self, doc: str) -> str:
        self.res.file = self.ru_rel
        doc = self.head(doc)
        doc = self.prepass(doc)
        out: list[str] = []
        ru_only_depth: list[int] = []   # stack of <a> depths whose link is RU-only
        depth = 0
        forced_label: str | None = None  # next text node is replaced (contact links by href)
        for m in TOKEN.finditer(doc):
            kind = m.lastgroup
            tok = m.group(0)
            if kind == "script":
                out.append(self.script(tok))
            elif kind == "style":
                out.append(tok)
                self._scan_css(tok)
            elif kind == "tag":
                closing, name = tag_name(tok)
                if closing:
                    if name == "a" and ru_only_depth and ru_only_depth[-1] == depth:
                        ru_only_depth.pop()
                        # append suffix inside the link, before </a>
                        prev = out[-1] if out else ""
                        if prev.endswith(" (Russian)"):
                            pass
                        else:
                            out.append(" (Russian)")
                    if name not in VOID:
                        depth -= 1
                    out.append(tok)
                else:
                    new, ru_only = self.tag(tok)
                    out.append(new)
                    if name == "a":
                        forced_label = self.d.contact_by_href.get(get_attr(tok, "href") or "")
                        if "pflang" in (get_attr(tok, "class") or "").split():  # [switcher]
                            forced_label = self.d.switcher["label"]
                    if name not in VOID and not tok.endswith("/>"):
                        depth += 1
                        if name == "a" and ru_only:
                            ru_only_depth.append(depth)
            elif kind == "text":
                if forced_label and tok.strip():
                    out.append(html.escape(forced_label, quote=False))
                    forced_label = None
                elif tok.strip():
                    txt = html.unescape(tok)
                    new = self.res.resolve(txt, ctx="text")
                    out.append(html.escape(new, quote=False) if new != txt else tok)
                else:
                    out.append(tok)
            else:
                out.append(tok)
        doc = "".join(out)
        if self.kind == "hub":
            doc = self.regroup_hub(doc)
        if self.kind == "track":
            tr = self.site.by_slug.get(self.slug)
            if tr is not None:
                bad = self.untranslated_story_keys(tr)
                if bad:
                    self.res.missing.add_story(self.slug, bad)
                doc = self.romanize_track_page(doc, tr)
        return doc

    # -- track page: romanized title / artist once, for "who mixed Tysyachi Zim" queries
    def romanize_track_page(self, doc: str, tr: dict) -> str:
        title = tr["title"]
        ro = romanize(title) if CYR.search(title) else ""
        qt = "“" + html.escape(title, quote=False) + "”"

        def annotate(text: str) -> str:
            """first “title” gets (Ro) — or joins an existing parenthesis: (Ro, 2026)"""
            i = text.find(qt)
            if i < 0:
                return text
            j = i + len(qt)
            if text.startswith(" (", j):
                return text[: j + 2] + ro + ", " + text[j + 2:]
            return text[:j] + f" ({ro})" + text[j:]

        if ro:
            doc = re.sub(r"<title>(.*?)</title>", lambda m: "<title>" + annotate(m.group(1)) + "</title>", doc, count=1, flags=re.S)
            for key in ("description", "og:title", "og:description"):
                doc = re.sub(r'(<meta (?:name|property)="' + re.escape(key) + r'" content=")([^"]*)(")',
                             lambda m: m.group(1) + annotate(m.group(2)) + m.group(3), doc, count=1)
            doc = re.sub(r'(<p class="lead">)(.*?)(</p>)', lambda m: m.group(1) + annotate(m.group(2)) + m.group(3), doc, count=1, flags=re.S)
        # artist kept in Cyrillic: first mention in the lead gets its romanization
        for tok in re.split(r", |;", tr["artist"]):
            tok = bwm.canon(tok.replace("*", "").strip())
            en_name = self.d.artists.get(tok, tok)
            r = self.d.romanization.get(tok)
            if r and CYR.search(en_name):
                esc_name = html.escape(en_name, quote=False)
                doc = re.sub(r'(<p class="lead">.*?)' + re.escape(esc_name) + r'(?![^<]*\()',
                             lambda m: m.group(1) + esc_name + f" ({r})", doc, count=1, flags=re.S)
        return doc

    def _scan_css(self, tok: str):
        body = re.sub(r"/\*.*?\*/", "", tok, flags=re.S)
        for m in re.finditer(r'content\s*:\s*"([^"]*[А-Яа-яЁё][^"]*)"', body):
            self.res.missing.add(m.group(1), self.ru_rel, "css content")

    # -- hub: regroup letters by EN artist name ---------------------------------
    def regroup_hub(self, doc: str) -> str:
        m = re.search(r'(<div class="catalog" id="catalog">)(.*?)(</div>\s*<p class="empty")', doc, re.S)
        if not m:
            return doc
        catalog = m.group(2)
        blocks = re.findall(r'<div class="letter">.*?</div>|<section class="art-sec".*?</section>', catalog, re.S)
        sections = [b for b in blocks if b.startswith("<section")]
        if "".join(blocks) != catalog or not sections:
            return doc

        def name_of(sec: str) -> str:
            h = re.search(r"<h2>(.*?)</h2>", sec, re.S).group(1)
            return html.unescape(re.sub(r"<[^>]+>", "", h)).strip()

        sections.sort(key=lambda s: bwm._artist_sort_key(name_of(s)))
        new_blocks, jump, prev, seen = [], [], "", set()
        for sec in sections:
            n = name_of(sec)
            letter = n[:1].upper() if n else "#"
            if letter != prev:
                prev = letter
                new_blocks.append(f'<div class="letter">{html.escape(letter)}</div>')
            if letter not in seen:
                seen.add(letter)
                sid = re.search(r'id="([^"]*)"', sec).group(1)
                jump.append(f'<a class="lj" href="#{sid}">{html.escape(letter)}</a>')
            new_blocks.append(sec)
        doc = doc[: m.start(2)] + "".join(new_blocks) + doc[m.end(2):]
        doc = re.sub(r'(<nav class="jump"[^>]*>).*?(</nav>)',
                     lambda mm: mm.group(1) + "".join(jump) + mm.group(2), doc, count=1, flags=re.S)
        return doc


VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
        "param", "source", "track", "wbr"}


# ─────────────────────────────────────────────────────────────── outputs

def build_track_info(site: Site, res: Resolver, d: Dictionaries) -> list[str]:
    src = ROOT / "track-info.json"
    if not src.is_file():
        return []
    res.file = "track-info.json"
    data = json.loads(src.read_text(encoding="utf-8"))
    out = {}
    for tid, item in data.items():
        it = dict(item)
        it["artist"] = res.artist(item.get("artist", ""))
        it["role"] = res.role(item.get("role", "")) if item.get("role") else item.get("role", "")
        if CYR.search(it["role"]):
            res.missing.add(it["role"], "track-info.json", "role")
        tr = site.by_slug.get(item.get("slug", ""))
        notes = None
        if tr is not None:
            keys = ([bwm.album_note_key(tr["artist"], tr["album"])] if tr.get("album") else []) + [tr["slug"]]
            # lenient mode: paragraphs without a translation are omitted, exactly
            # as on the page; a work with nothing left gets no story at all
            keys = [k for k in keys if k not in res.untranslated_keys]
            if not any(bwm.NOTES.get(k) for k in keys):
                continue
            keys = ([bwm.album_note_key(tr["artist"], tr["album"])] if tr.get("album") else []) + [tr["slug"]]
            if all(k in d.notes for k in keys if bwm.NOTES.get(k)):
                notes = []
                for k in keys:
                    notes.extend(d.notes.get(k, []) if bwm.NOTES.get(k) else [])
        if notes is None:  # fall back to paragraph map (partial dictionaries)
            notes = [res.notes_plain.get(p, p) for p in item.get("notes", [])
                     if p not in res.untranslated_plain]
            if not notes:
                continue
        for p in notes:
            if CYR.search(p) and res.leftover(p, quotes_ok=True):
                res.missing.add(p[:120], "track-info.json", f"note {item.get('slug')}")
        it["notes"] = notes
        it["url"] = map_link(item.get("url", ""), site)[0]
        out[tid] = it
    (OUT / "track-info.json").write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return sorted(out)


def build_llms(site: Site, d: Dictionaries) -> bool:
    if d.llms_template is None:
        return False
    text = d.llms_template.replace("{tracks}", str(site.n_tracks)).replace("{artists}", str(site.n_artists))

    def fix(m: re.Match) -> str:
        return map_link(m.group(0), site)[0]
    text = re.sub(rf"{re.escape(SITE)}/[^\s)>\]]*", fix, text)
    (OUT / "llms.txt").write_text(text, encoding="utf-8")
    return True


def build(quiet: bool = False, strict: bool = False) -> int:
    d = Dictionaries()
    site = Site()
    missing = Missing()
    res = Resolver(d, site, missing)

    OUT.mkdir(exist_ok=True)
    (OUT / "track").mkdir(exist_ok=True)
    (OUT / "faq").mkdir(exist_ok=True)

    pages = [("index.html", "index.html"), ("track/index.html", "track/index.html"),
             ("faq/index.html", "faq/index.html")]
    pages += [(f"track/{s}/index.html", f"track/{s}/index.html") for s in site.track_pages]

    built = 0
    for ru_rel, en_rel in pages:
        src = ROOT / ru_rel
        if not src.is_file():
            continue
        page = Page(ru_rel, en_rel, site, d, res)
        doc = page.run(src.read_text(encoding="utf-8"))
        dst = OUT / en_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(doc, encoding="utf-8")
        if page.kind == "faq":
            # [geo-ru Phase 2] FAQPage answers must be copies of the visible
            # EN text, exactly as on the RU side — rebuild them from the page
            import sync_faq_schema
            if sync_faq_schema.main(dst) != 0:
                raise SystemExit("en/faq: FAQPage schema rebuild failed")
        built += 1

    # prune stale EN track dirs
    keep = set(site.track_pages)
    for dd in (OUT / "track").iterdir():
        if dd.is_dir() and dd.name not in keep:
            shutil.rmtree(dd)

    en_ids = build_track_info(site, res, d)
    has_llms = build_llms(site, d)

    # the ⓘ buttons are placed from this inline id list: only EN-available stories
    home = OUT / "index.html"
    if home.is_file():
        doc = home.read_text(encoding="utf-8")
        doc = re.sub(r'(<script type="application/json" id="track-story-ids">).*?(</script>)',
                     lambda m: m.group(1) + json.dumps(en_ids, separators=(",", ":")) + m.group(2),
                     doc, count=1, flags=re.S)
        home.write_text(doc, encoding="utf-8")

    n_missing, n_art, n_story = missing.write()
    if not quiet:
        print(f"dictionaries: {', '.join(d.loaded) or 'none'}")
        print(f"built {built} pages -> en/ ; track-info.json ({len(en_ids)} stories) ; "
              f"llms.txt: {'yes' if has_llms else 'no template'}")
    print(f"missing UI strings: {n_missing} -> {MISSING_FILE.relative_to(ROOT)}")
    if n_art or n_story:
        print(f"EN: {n_art} artists unmapped, {n_story} stories untranslated — see i18n/missing.txt")
    if n_missing:
        return 1
    return 1 if strict and (n_art or n_story) else 0


# ─────────────────────────────────────────────────────────────── structural check

def _skeleton(doc: str) -> list[str]:
    seq = []
    for m in TOKEN.finditer(doc):
        k = m.lastgroup
        tok = m.group(0)
        if k == "tag":
            closing, name = tag_name(tok)
            attrs = sorted(a.group(1).lower() for a in ATTR.finditer(tok)) if not closing else []
            seq.append(("/" if closing else "") + name + ("[" + ",".join(attrs) + "]" if attrs else ""))
        elif k in ("script", "style"):
            seq.append(k)
    return seq


def check() -> int:
    import difflib
    site = Site()
    d = Dictionaries()
    res = Resolver(d, site, Missing())
    dropper = Page("track/index.html", "track/index.html", site, d, res)
    pairs = [("index.html", "index.html"), ("track/index.html", "track/index.html"),
             ("faq/index.html", "faq/index.html")]
    # /tier/ is rendered per language by build_tier.py (not by this script), but
    # the two twins must still share one tag skeleton — checked like the others.
    if (DICT_DIR / "tier.json").is_file():
        pairs.append(("tier/index.html", "tier/index.html"))
    else:
        print("note     tier/index.html: i18n/en/tier.json absent, /en/tier/ not built — pair skipped")
    pairs += [(f"track/{s}/index.html",) * 2 for s in site.track_pages]
    bad = 0
    for ru_rel, en_rel in pairs:
        ru = dropper.drop_untranslated_stories((ROOT / ru_rel).read_text(encoding="utf-8"))
        en_p = OUT / en_rel
        if not en_p.is_file():
            print(f"MISSING  {en_rel}")
            bad += 1
            continue
        en = en_p.read_text(encoding="utf-8")
        if ru_rel == "track/index.html":
            # letter headings / jump links are regenerated from EN names (Cyrillic
            # initials merge into Latin ones), so they are excluded from the diff
            strip = lambda d: re.sub(r'<div class="letter">.*?</div>|<a class="lj"[^>]*>.*?</a>', "", d)
            ru, en = strip(ru), strip(en)
        a, b = _skeleton(ru), _skeleton(en)
        if ru_rel == "track/index.html":
            a, b = sorted(a), sorted(b)      # sections are re-sorted by EN name
        diffs = [x for x in difflib.ndiff(a, b) if x[:1] in "+-"]
        explainable = all(x[2:].startswith("link[") for x in diffs)
        status = "ok" if not diffs else ("ok (head links)" if explainable else "DIFF")
        if status == "DIFF":
            bad += 1
            print(f"{status:16} {ru_rel}: {len(diffs)} diffs, first: {diffs[:6]}")
        elif ru_rel in ("index.html", "track/index.html", "faq/index.html", "tier/index.html"):
            print(f"{status:16} {ru_rel}: {len(a)} tags, extra in EN: {[x[2:] for x in diffs if x[0]=='+']}")
    print(f"checked {len(pairs)} page pairs, {bad} structural differences")
    return 1 if bad else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--check" in args:
        sys.exit(check())
    sys.exit(build(quiet="--quiet" in args, strict="--strict" in args))
