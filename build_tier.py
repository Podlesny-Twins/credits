#!/usr/bin/env python3
"""Generate /tier/ and /en/tier/ — the mixing-technique tier list — from tier.json
and i18n/en/tier.json.

Why this page exists: the studio's verdicts live in an hour-long YouTube video,
and answer engines cannot read a video. Fetching the watch page as GPTBot returns
the title, the description and the chapter list — and not one word of speech. So
the verdicts are republished here as text, on a domain whose robots.txt already
lets the AI crawlers in.

Chrome/design: the shell (fonts, palette, nav, waveform strip, <details> rhythm)
is READ from faq/index.html at build time rather than copied. One page's styling
can then never drift from the other's, and this file only adds the tier badges.
The EN page lifts its shell from en/faq/index.html the same way, so the EN
header (nav labels, language switcher) comes from build_en.py for free — the
only thing this file re-points is the switcher's href (FAQ twin → tier twin).

Order matters in one direction: the shell comes from faq/index.html and
en/faq/index.html, so after any edit to the FAQ page (or a build_en.py run)
this must be re-run or the pages drift apart.

Languages: RU is rendered from tier.json, EN from i18n/en/tier.json (same
structure, translated; verdicts start with "S tier:" instead of "S-тир:").
The UI chrome that is not in the data (breadcrumb, "In short", the footer
sentence…) lives in STRINGS below. Both pages carry the same hreflang set
(ru / en / x-default → EN), exactly as build_who_mixed.hreflang_links emits it
for the other translated pages.

Run:  python3 build_tier.py             # both languages (EN skipped with a
                                        # warning if i18n/en/tier.json is absent)
      python3 build_tier.py --lang en   # one language
      python3 build_tier.py --lang en --data path/to/other.json   # test data
Build order: build_who_mixed.py (→ build_en.py) → build_tier.py → build_llms_full.py
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import build_who_mixed as bwm  # noqa: E402  (hreflang_links: one definition for every page)

SITE = "https://credits.podlesnytwins.com"

# Order of the ladder as the video defines it, best first. L sits above S:
# it is the hosts' own top step, not the usual gaming scale.
#
# "N" is not a step of theirs. Some techniques were discussed at length but never
# given a letter, and inventing one would put words in the studio's mouth — so
# they sit in their own group at the bottom, marked with a dash instead.
TIER_ORDER = ["L", "S", "A", "B", "C", "D", "F", "N"]
NO_TIER = "N"

# The verdict line must open with the tier letter in words ("B-тир: …" /
# "B tier: …"): the badge is a styled letter and a text-only scrape would
# otherwise lose the verdict. Both spellings are accepted; the letter must
# agree with the item's tier.
VERDICT_RE = re.compile(r"^([A-Z])(?:-тир|\s+tier)\b")

# Everything per language that is not part of the data file. Strings with
# {…} are format templates; the data (title, h1, lead, tiers…) is translated
# in the data file itself.
LANGS = {
    "ru": {
        "data": ROOT / "tier.json",
        "shell": ROOT / "faq" / "index.html",
        "out": ROOT / "tier" / "index.html",
        "rel": "tier/",                       # site-relative dir of the page
        "html_lang": "ru",
        "og_locale": "ru_RU",
        "twin_rel": "en/tier/",               # where the language switcher goes
        "strings": {
            "crumb_home": "Podlesny Twins",
            "meta": "{n} техник · разбор студии",
            "intro_eyebrow": "Коротко",
            "scale": "Шкала",
            "alt": "Также называют: ",
            "watch": "Podlesny Twins разбирают это в «Тир-листе техник сведения» — ",
            "list_item": "{name} — {tier}-тир",
            "updated": ("Обновлено: {date}. Оценки — позиция студии Podlesny Twins\n"
                        "  (Антон и Павел Подлесные), а не универсальное правило: тир техники меняется\n"
                        "  вместе с материалом и задачей."),
            "full_video": "Разбор целиком — ",
            "video_label": "видео «{title}»",
            "faq": "Вопросы и ответы о студии",
            "works": "Работы студии",
            "back": "← К портфолио",
        },
    },
    "en": {
        "data": ROOT / "i18n" / "en" / "tier.json",
        "shell": ROOT / "en" / "faq" / "index.html",
        "out": ROOT / "en" / "tier" / "index.html",
        "rel": "en/tier/",
        "html_lang": "en",
        "og_locale": "en_US",
        "twin_rel": "tier/",
        "strings": {
            "crumb_home": "Podlesny Twins",
            "meta": "{n} techniques · the studio's verdicts",
            "intro_eyebrow": "In short",
            "scale": "The scale",
            "alt": "Also known as: ",
            "watch": "Podlesny Twins cover this in the “Mixing techniques tier list” video — ",
            "list_item": "{name} — {tier} tier",
            "updated": ("Last updated: {date}. The ratings are the position of Podlesny Twins\n"
                        "  (Anton and Pavel Podlesny), not a universal rule: a technique's tier changes\n"
                        "  with the material and the task."),
            "full_video": "The full breakdown — ",
            "video_label": "the video “{title}”",
            "faq": "FAQ about the studio",
            "works": "Studio credits",
            "back": "← Back to the portfolio",
        },
    },
}


def badge(t: str) -> str:
    return "—" if t == NO_TIER else t


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def hhmmss(sec: int) -> str:
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def iso_duration(sec: int) -> str:
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return "PT" + (f"{h}H" if h else "") + (f"{m}M" if m else "") + f"{s}S"


def shell(cfg: dict) -> tuple[str, str]:
    """Pull the shared <style> and the nav+waveform markup out of the FAQ page
    of the same language, and re-point the language switcher at the tier twin
    (the FAQ's switcher points at the FAQ twin)."""
    src = cfg["shell"].read_text(encoding="utf-8")
    style = re.search(r"<style>.*?</style>", src, re.S)
    nav = re.search(r'<div class="pfnav">.*?</nav>\s*</div>', src, re.S)
    wave = re.search(r'<div class="wave".*?</div>', src, re.S)
    if not (style and nav and wave):
        raise SystemExit(f"{cfg['shell'].relative_to(ROOT)} changed shape — cannot lift the shell")
    nav_html, n = re.subn(r'(<a class="pflink pflang" href=")[^"]*(")',
                          lambda m: m.group(1) + f"{SITE}/{cfg['twin_rel']}" + m.group(2),
                          nav.group(0), count=1)
    if n != 1:
        raise SystemExit(f"{cfg['shell'].relative_to(ROOT)}: no language switcher (a.pflang) in the header")
    return style.group(0), nav_html + "\n\n  " + wave.group(0)


STUDIO_ID = f"{SITE}/#podlesnytwins"


def studio_entity(cfg: dict) -> list[dict]:
    """The studio Organization node and its founder Person nodes, read from
    the FAQ page's JSON-LD (build_who_mixed.py keeps that graph normalised;
    build_en.py carries it over with the same @ids). Fails loudly if the FAQ
    graph lost the entity or still types it MusicGroup."""
    src = cfg["shell"].read_text(encoding="utf-8")
    block = re.search(r'<script type="application/ld\+json">(.*?)</script>', src, re.S)
    if not block:
        raise SystemExit(f"{cfg['shell'].relative_to(ROOT)} has no JSON-LD — cannot lift the studio entity")
    graph = json.loads(block.group(1))["@graph"]
    studio = next((n for n in graph if n.get("@id") == STUDIO_ID), None)
    if not studio or studio.get("@type") != "Organization":
        raise SystemExit(f"{cfg['shell'].relative_to(ROOT)}: studio node missing or not an Organization — "
                         "run build_who_mixed.py first")
    founder_ids = {f["@id"] for f in studio.get("founder", [])}
    founders = [n for n in graph if n.get("@id") in founder_ids]
    if len(founders) != len(founder_ids):
        raise SystemExit(f"{cfg['shell'].relative_to(ROOT)}: founder @id without a Person node")
    return [studio, *founders]


EXTRA_CSS = """
<style>
/* ---- tier list: the ladder is the only thing this page adds to the FAQ shell ---- */
.tierkey{list-style:none;margin:0 0 46px;padding:0;display:grid;gap:2px}
.tierkey li{display:grid;grid-template-columns:44px 1fr;gap:14px;align-items:baseline;padding:9px 0;border-bottom:1px solid var(--line);font-size:14.5px;color:#cfc9c9}
.tierkey li:last-child{border-bottom:0}
.tg{display:inline-flex;align-items:center;justify-content:center;min-width:26px;padding:2px 7px;border-radius:4px;font-family:'SaarSP',Arial,sans-serif;font-size:13px;font-weight:600;letter-spacing:.04em;color:var(--ink);background:#2e2d2b;border:1px solid var(--line)}
.tg-L{background:var(--red);border-color:var(--red);color:#fff}
.tg-S{background:#8f2409;border-color:#8f2409;color:#fff}
.tg-A{background:#4a3a1d;border-color:#5d4923}
.tg-B{background:#3a3833;border-color:#4a4740}
.tg-C{background:#302f2c;border-color:#403e39}
.tg-D{background:#2b2a28;border-color:#3a3934;color:#b9b2b2}
.tg-F{background:#2a2a29;border-color:#3d3c38;color:var(--mut)}
.tg-N{background:transparent;border-style:dashed;color:var(--mut)}
h2 .tg{font-size:14px}
details summary .tg{flex:0 0 auto;margin-left:auto;margin-right:6px}
details summary .qn{flex:1 1 auto}
.vd{color:var(--ink);font-weight:600}
.at{display:block;font-size:12.5px;color:var(--mut);margin-top:10px;letter-spacing:.02em}
.at a{color:var(--mut);font-weight:600}
.at a:hover{color:var(--ink);text-decoration:underline}
@media(max-width:520px){
  .tierkey li{grid-template-columns:38px 1fr;gap:10px;font-size:14px}
}
</style>
"""


def render_item(it: dict, video_id: str, s: dict) -> str:
    tier = it["tier"]
    ts = int(it["t"])
    watch = f"https://www.youtube.com/watch?v={video_id}&t={ts}s"
    body = "".join(f"<p>{esc(p)}</p>" for p in it["body"])
    alt = ""
    if it.get("alt"):
        alt = f'<p class="at">{esc(s["alt"])}{esc(", ".join(it["alt"]))}</p>'
    # The tier badge is a styled letter, so a plain-text scrape of <summary> would
    # read "OTTB". A crawler that lifts one block out of the page must still see
    # the verdict, so it is repeated as the block's own lead sentence.
    return (
        f'<details id="{it["slug"]}">\n'
        f'  <summary><span class="qn">{esc(it["name"])}</span> '
        f'<span class="tg tg-{tier}">{badge(tier)}</span></summary>\n'
        f'  <div class="ans"><p class="vd">{esc(it["verdict"])}</p>{body}{alt}'
        f'<p class="at">{esc(s["watch"])}'
        f'<a href="{watch}" rel="noopener">{hhmmss(ts)}</a></p></div>\n'
        f"</details>"
    )


def render(data: dict, cfg: dict) -> str:
    s = cfg["strings"]
    page = f"{SITE}/{cfg['rel']}"
    style, nav = shell(cfg)
    v = data["video"]
    items = data["items"]
    by_tier = {t: [i for i in items if i["tier"] == t] for t in TIER_ORDER}
    tiers = {t["key"]: t for t in data["tiers"]}

    toc = "".join(
        f'<li><a href="#tier-{t}">{tiers[t]["short"]} <span class="fc">{len(by_tier[t])}</span></a></li>'
        for t in TIER_ORDER if by_tier[t]
    )

    key = "".join(
        f'<li><span class="tg tg-{t}">{badge(t)}</span><span>{esc(tiers[t]["desc"])}</span></li>'
        for t in TIER_ORDER if by_tier[t]
    )

    sections = []
    for t in TIER_ORDER:
        if not by_tier[t]:
            continue
        # No per-section repeat of the legend: each technique already opens with
        # its own "X-тир: …" line, which is the unit a crawler actually lifts.
        sections.append(
            f'<h2 id="tier-{t}"><span class="tg tg-{t}">{badge(t)}</span> {esc(tiers[t]["name"])}</h2>\n'
            + "\n".join(render_item(i, v["id"], s) for i in by_tier[t])
        )

    # The studio entity (Organization + its two founders) is lifted from the
    # FAQ's graph the same way the shell is — one definition, no drift.
    studio_nodes = studio_entity(cfg)

    crumbs = {
        "@type": "BreadcrumbList",
        "@id": f"{page}#breadcrumbs",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": s["crumb_home"],
             "item": f"{SITE}/" if cfg["html_lang"] == "ru" else f"{SITE}/en/"},
            {"@type": "ListItem", "position": 2, "name": data["title"], "item": page},
        ],
    }

    graph = [
        *studio_nodes,
        crumbs,
        {
            "@type": "WebPage",
            "@id": f"{page}#webpage",
            "url": page,
            "name": data["title"],
            "inLanguage": cfg["html_lang"],
            "datePublished": data["published"],
            "dateModified": data["modified"],
            "about": {"@id": f"{SITE}/#podlesnytwins"},
            "isBasedOn": {"@id": f"{page}#video"},
            "mainEntity": {"@id": f"{page}#list"},
            "breadcrumb": {"@id": f"{page}#breadcrumbs"},
        },
        {
            "@type": "VideoObject",
            "@id": f"{page}#video",
            "name": v["title"],
            "description": data["lead"],
            "uploadDate": v.get("uploaded", v["published"]),
            "duration": iso_duration(v["duration"]),
            "thumbnailUrl": f"https://i.ytimg.com/vi/{v['id']}/maxresdefault.jpg",
            "embedUrl": f"https://www.youtube.com/embed/{v['id']}",
            "url": f"https://www.youtube.com/watch?v={v['id']}",
            "creator": {"@id": f"{SITE}/#podlesnytwins"},
            "hasPart": [
                {
                    "@type": "Clip",
                    "name": i["name"],
                    "startOffset": int(i["t"]),
                    "endOffset": int(items[n + 1]["t"]) if n + 1 < len(items) else v["duration"],
                    "url": f"https://www.youtube.com/watch?v={v['id']}&t={int(i['t'])}s",
                }
                for n, i in enumerate(items)
            ],
        },
        {
            "@type": "ItemList",
            "@id": f"{page}#list",
            "name": data["title"],
            "numberOfItems": len(items),
            "itemListOrder": "https://schema.org/ItemListOrderDescending",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": n,
                    "name": (
                        i["name"] if i["tier"] == NO_TIER
                        else s["list_item"].format(name=i["name"], tier=i["tier"])
                    ),
                    "url": f"{page}#{i['slug']}",
                    "description": i["verdict"],
                }
                for n, i in enumerate(
                    [i for t in TIER_ORDER for i in by_tier[t]], start=1
                )
            ],
        },
    ]
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)

    ga = (
        '<!-- Google tag (gtag.js) -->\n'
        '<script async src="https://www.googletagmanager.com/gtag/js?id=G-JWPH35TTVX"></script>\n'
        "<script>\n  window.dataLayer = window.dataLayer || [];\n"
        "  function gtag(){dataLayer.push(arguments);}\n"
        "  gtag('js', new Date());\n  gtag('config', 'G-JWPH35TTVX');\n</script>"
    )

    # Same hreflang set on both twins (ru / en / x-default → EN), from the one
    # function that emits it for every other translated page.
    hreflang = bwm.hreflang_links("tier/")
    if not hreflang:
        raise SystemExit("build_who_mixed.EN_STATIC no longer lists tier/ — the twins would lose hreflang")

    home = f"{SITE}/" if cfg["html_lang"] == "ru" else f"{SITE}/en/"
    faq = f"{SITE}/faq/" if cfg["html_lang"] == "ru" else f"{SITE}/en/faq/"
    works = f"{SITE}/track/" if cfg["html_lang"] == "ru" else f"{SITE}/en/track/"

    return f"""<!DOCTYPE html>
<html lang="{cfg["html_lang"]}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{ga}
<title>{esc(data["title"])} — Podlesny Twins</title>
<meta name="description" content="{esc(data["meta_description"])}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{page}">
{hreflang.rstrip()}
<meta property="og:type" content="article">
<meta property="og:title" content="{esc(data["title"])} — Podlesny Twins">
<meta property="og:description" content="{esc(data["meta_description"])}">
<meta property="og:url" content="{page}">
<meta property="og:locale" content="{cfg["og_locale"]}">
<meta property="og:image" content="https://i.ytimg.com/vi/{v['id']}/maxresdefault.jpg">
<meta property="og:image:width" content="1280">
<meta property="og:image:height" content="720">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/png" href="{SITE}/favicon.png">
<script type="application/ld+json">{ld}</script>
{style}
{EXTRA_CSS}</head>
<body>
<div class="wrap">
  {nav}

  <p class="bc"><a href="{home}">{esc(s["crumb_home"])}</a> → {esc(data["title"])}</p>

  <p class="meta">{esc(s["meta"].format(n=len(items)))}</p>
  <h1>{esc(data["h1"])}</h1>
  <p class="lead">{esc(data["lead"])}</p>

  <div class="intro">
    <p class="eyebrow">{esc(s["intro_eyebrow"])}</p>
    <p>{data["intro"]}</p>
  </div>

  <ul class="toc">{toc}</ul>

  <p class="meta">{esc(s["scale"])}</p>
  <ul class="tierkey">{key}</ul>

  {"".join(sections)}

  <p class="upd">{esc(s["updated"].format(date=data["modified_human"]))}</p>
  <p class="faqfoot">{esc(s["full_video"])}<a href="https://www.youtube.com/watch?v={v['id']}" rel="noopener">{esc(s["video_label"].format(title=v["title"]))}</a>
   · <a href="{faq}">{esc(s["faq"])}</a>
   · <a href="{works}">{esc(s["works"])}</a></p>
  <p class="back"><a href="{home}">{esc(s["back"])}</a></p>
</div>
<script>
// Every technique is addressable as /tier/#slug — that is what the JSON-LD
// publishes and what an answer engine cites. Browsers do not open a targeted
// <details>, so a visitor would land on a closed row. Open it on arrival.
(function () {{
  function target() {{
    try {{
      var el = location.hash && document.querySelector(location.hash);
      return el && el.tagName === 'DETAILS' ? el : null;
    }} catch (e) {{ return null; }}
  }}
  // Open before the browser settles on a scroll position: expanding the block
  // afterwards shifts everything below it and the anchor lands off-screen.
  function open(el) {{ if (el && !el.open) el.open = true; }}
  open(target());
  addEventListener('load', function () {{
    var el = target();
    open(el);
    if (el) el.scrollIntoView();
  }});
  addEventListener('hashchange', function () {{
    var el = target();
    open(el);
    if (el) el.scrollIntoView();
  }});
}})();
</script>
</body>
</html>
"""


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    seen = set()
    for i in data["items"]:
        if i["tier"] not in TIER_ORDER:
            raise SystemExit(f"{path.name}: unknown tier {i['tier']!r} on {i['slug']}")
        if i["slug"] in seen:
            raise SystemExit(f"{path.name}: duplicate slug {i['slug']!r}")
        seen.add(i["slug"])
        m = VERDICT_RE.match(i["verdict"])
        if i["tier"] != NO_TIER and (not m or m.group(1) != i["tier"]):
            raise SystemExit(f"{path.name}: verdict on {i['slug']} must open with "
                             f"\"{i['tier']}-тир\" / \"{i['tier']} tier\": {i['verdict'][:60]!r}")
    return data


def build(lang: str, data_path: Path | None = None) -> None:
    cfg = LANGS[lang]
    data = load(data_path or cfg["data"])
    if lang == "en":
        ru = json.loads(LANGS["ru"]["data"].read_text(encoding="utf-8"))
        ru_slugs = [i["slug"] for i in ru["items"]]
        en_slugs = [i["slug"] for i in data["items"]]
        if ru_slugs != en_slugs:
            raise SystemExit(f"{(data_path or cfg['data']).name}: items differ from tier.json "
                             f"({len(en_slugs)} vs {len(ru_slugs)}; same slugs in the same order expected)")
    cfg["out"].parent.mkdir(exist_ok=True)
    cfg["out"].write_text(render(data, cfg), encoding="utf-8")
    print(f"{cfg['out'].relative_to(ROOT)} — {len(data['items'])} techniques")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--lang", choices=sorted(LANGS), help="one language (default: both)")
    ap.add_argument("--data", type=Path, help="data file override (test data); needs --lang")
    a = ap.parse_args()
    if a.data and not a.lang:
        ap.error("--data needs --lang")
    if a.lang:
        build(a.lang, a.data)
        return
    build("ru")
    if LANGS["en"]["data"].is_file():
        build("en")
    else:
        print(f"WARNING: {LANGS['en']['data'].relative_to(ROOT)} not found — /en/tier/ skipped "
              "(the RU page and the sitemap already point at it)", file=sys.stderr)


if __name__ == "__main__":
    main()
