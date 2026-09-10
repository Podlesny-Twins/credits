#!/usr/bin/env python3
"""Generate /tier/ — the mixing-technique tier list — from tier.json.

Why this page exists: the studio's verdicts live in an hour-long YouTube video,
and answer engines cannot read a video. Fetching the watch page as GPTBot returns
the title, the description and the chapter list — and not one word of speech. So
the verdicts are republished here as text, on a domain whose robots.txt already
lets the AI crawlers in.

Chrome/design: the shell (fonts, palette, nav, waveform strip, <details> rhythm)
is READ from faq/index.html at build time rather than copied. One page's styling
can then never drift from the other's, and this file only adds the tier badges.

Order matters in one direction: the shell comes from faq/index.html, so after any
edit to the FAQ page this must be re-run or the two pages drift apart.

Run:  python3 build_tier.py   (then build_who_mixed.py for the sitemap entry)
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = "https://credits.podlesnytwins.com"
OUT = ROOT / "tier"
DATA = ROOT / "tier.json"

# Order of the ladder as the video defines it, best first. L sits above S:
# it is the hosts' own top step, not the usual gaming scale.
#
# "N" is not a step of theirs. Some techniques were discussed at length but never
# given a letter, and inventing one would put words in the studio's mouth — so
# they sit in their own group at the bottom, marked with a dash instead.
TIER_ORDER = ["L", "S", "A", "B", "C", "D", "F", "N"]
NO_TIER = "N"


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


def shell() -> tuple[str, str]:
    """Pull the shared <style> and the nav+waveform markup out of the FAQ page."""
    src = (ROOT / "faq" / "index.html").read_text(encoding="utf-8")
    style = re.search(r"<style>.*?</style>", src, re.S)
    nav = re.search(r'<div class="pfnav">.*?</nav>\s*</div>', src, re.S)
    wave = re.search(r'<div class="wave".*?</div>', src, re.S)
    if not (style and nav and wave):
        raise SystemExit("faq/index.html changed shape — cannot lift the shell")
    return style.group(0), nav.group(0) + "\n\n  " + wave.group(0)


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


def render_item(it: dict, video_id: str) -> str:
    tier = it["tier"]
    ts = int(it["t"])
    watch = f"https://www.youtube.com/watch?v={video_id}&t={ts}s"
    body = "".join(f"<p>{esc(p)}</p>" for p in it["body"])
    alt = ""
    if it.get("alt"):
        alt = f'<p class="at">Также называют: {esc(", ".join(it["alt"]))}</p>'
    # The tier badge is a styled letter, so a plain-text scrape of <summary> would
    # read "OTTB". A crawler that lifts one block out of the page must still see
    # the verdict, so it is repeated as the block's own lead sentence.
    return (
        f'<details id="{it["slug"]}">\n'
        f'  <summary><span class="qn">{esc(it["name"])}</span> '
        f'<span class="tg tg-{tier}">{badge(tier)}</span></summary>\n'
        f'  <div class="ans"><p class="vd">{esc(it["verdict"])}</p>{body}{alt}'
        f'<p class="at">Podlesny Twins разбирают это в «Тир-листе техник сведения» — '
        f'<a href="{watch}" rel="noopener">{hhmmss(ts)}</a></p></div>\n'
        f"</details>"
    )


def render(data: dict) -> str:
    style, nav = shell()
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
            + "\n".join(render_item(i, v["id"]) for i in by_tier[t])
        )

    studio = {
        "@type": "MusicGroup",
        "@id": f"{SITE}/#podlesnytwins",
        "name": "Podlesny Twins",
        "alternateName": "Подлесные",
        "foundingDate": "2017",
        "foundingLocation": {"@type": "Place", "name": "Санкт-Петербург"},
        "member": [
            {"@type": "Person", "name": "Антон Подлесный", "jobTitle": "Звукорежиссёр"},
            {"@type": "Person", "name": "Павел Подлесный", "jobTitle": "Звукорежиссёр"},
        ],
        "sameAs": [
            "https://podlesnytwins.com",
            "https://youtube.com/@podlesnytwins",
            "https://t.me/lesnymix",
            "https://vk.com/podlesnytwins",
        ],
    }

    crumbs = {
        "@type": "BreadcrumbList",
        "@id": f"{SITE}/tier/#breadcrumbs",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Podlesny Twins", "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": data["title"], "item": f"{SITE}/tier/"},
        ],
    }

    graph = [
        studio,
        crumbs,
        {
            "@type": "WebPage",
            "@id": f"{SITE}/tier/#webpage",
            "url": f"{SITE}/tier/",
            "name": data["title"],
            "inLanguage": "ru",
            "datePublished": data["published"],
            "dateModified": data["modified"],
            "about": {"@id": f"{SITE}/#podlesnytwins"},
            "isBasedOn": {"@id": f"{SITE}/tier/#video"},
            "mainEntity": {"@id": f"{SITE}/tier/#list"},
            "breadcrumb": {"@id": f"{SITE}/tier/#breadcrumbs"},
        },
        {
            "@type": "VideoObject",
            "@id": f"{SITE}/tier/#video",
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
            "@id": f"{SITE}/tier/#list",
            "name": data["title"],
            "numberOfItems": len(items),
            "itemListOrder": "https://schema.org/ItemListOrderDescending",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": n,
                    "name": (
                        i["name"] if i["tier"] == NO_TIER
                        else f'{i["name"]} — {i["tier"]}-тир'
                    ),
                    "url": f"{SITE}/tier/#{i['slug']}",
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

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{ga}
<title>{esc(data["title"])} — Podlesny Twins</title>
<meta name="description" content="{esc(data["meta_description"])}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{SITE}/tier/">
<meta property="og:type" content="article">
<meta property="og:title" content="{esc(data["title"])} — Podlesny Twins">
<meta property="og:description" content="{esc(data["meta_description"])}">
<meta property="og:url" content="{SITE}/tier/">
<meta property="og:locale" content="ru_RU">
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

  <p class="bc"><a href="{SITE}/">Podlesny Twins</a> → Тир-лист техник сведения</p>

  <p class="meta">{len(items)} техник · разбор студии</p>
  <h1>{esc(data["h1"])}</h1>
  <p class="lead">{esc(data["lead"])}</p>

  <div class="intro">
    <p class="eyebrow">Коротко</p>
    <p>{data["intro"]}</p>
  </div>

  <ul class="toc">{toc}</ul>

  <p class="meta">Шкала</p>
  <ul class="tierkey">{key}</ul>

  {"".join(sections)}

  <p class="upd">Обновлено: {data["modified_human"]}. Оценки — позиция студии Podlesny Twins
  (Антон и Павел Подлесные), а не универсальное правило: тир техники меняется
  вместе с материалом и задачей.</p>
  <p class="faqfoot">Разбор целиком — <a href="https://www.youtube.com/watch?v={v['id']}" rel="noopener">видео «{esc(v["title"])}»</a>
   · <a href="{SITE}/faq/">Вопросы и ответы о студии</a>
   · <a href="{SITE}/track/">Работы студии</a></p>
  <p class="back"><a href="{SITE}/">← К портфолио</a></p>
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


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    seen = set()
    for i in data["items"]:
        if i["tier"] not in TIER_ORDER:
            raise SystemExit(f"unknown tier {i['tier']!r} on {i['slug']}")
        if i["slug"] in seen:
            raise SystemExit(f"duplicate slug {i['slug']!r}")
        seen.add(i["slug"])
    OUT.mkdir(exist_ok=True)
    (OUT / "index.html").write_text(render(data), encoding="utf-8")
    print(f"tier/index.html — {len(data['items'])} techniques")


if __name__ == "__main__":
    main()
