#!/usr/bin/env python3
"""Generate the blog: /blog/ (index), /blog/<slug>/ and /en/blog/<slug>/ from
blog-src/*.md and blog-src/en/*.md.

Why the blog exists: the studio's know-how lives in the Telegram channel
@lesnymix, and answer engines rarely cite a Telegram post. Each article
republishes one topic from the channel as a page built to be quoted: a short
answer up top, question-shaped headings, tables, an FAQ block, and the source
posts linked at the bottom (t.me/lesnymix/<id>) so every claim can be checked.
Rule for authors: an article says only what the channel already said in
public — NDA work stays out, and outside facts get a link to their source.

Source format (blog-src/<slug>.md; the English version, if any, is
blog-src/en/<same slug>.md with the same fields):

    ---
    slug: pochemu-bas-ploho-zvuchit-v-mikse
    title: H1 and og:title
    title_tag: <title>, up to ~60 characters
    description: meta description and the teaser on the index, ~150–160 chars
    date: 2026-10-01             # published
    updated: 2026-10-05          # optional, defaults to date
    order: 1                     # optional, position among posts of the same date
    lead: the "Коротко" answer block, 40–60 words, must stand on its own
    tags: comma, separated       # optional, goes to JSON-LD keywords
    sources:
      - 607 | 2026-08-30 | Post title as it reads in the channel
    ---
    Markdown body. "## … {#faq}" with "### question" + answer paragraphs
    becomes the FAQPage schema. Site links are written as /path/ (EN: /en/path/).

Shell: like build_tier.py, the <style>, header and waveform strip are LIFTED
from faq/index.html (EN: en/faq/index.html) at build time, so the blog never
drifts from the FAQ. Re-run after a FAQ header change or a build_en.py run.

Languages: the RU index is rendered here; its EN twin /en/blog/ is produced by
build_en.py from it. So that the EN index shows the same title and teaser as
the EN article, this script writes each EN title/description into
i18n/en/ui.json keyed by the RU strings. An article without an EN file stays
RU-only: the EN index then marks its link "(Russian)".

Writes: blog/index.html, blog/<slug>/index.html, en/blog/<slug>/index.html,
blog/posts.json (manifest read by build_who_mixed.write_sitemap and
build_llms_full.py), the "## Блог" section of llms.txt and the "## Blog"
section of the EN llms template (i18n/en/llms.txt).

Build order: build_blog.py → build_who_mixed.py (→ build_en.py, sitemap)
→ build_tier.py → build_llms_full.py
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import build_who_mixed as bwm  # noqa: E402
from build_tier import rail_script, shell, studio_entity  # noqa: E402  (one shell, one studio entity)

SITE = "https://credits.podlesnytwins.com"
SRC = ROOT / "blog-src"
MANIFEST = ROOT / "blog" / "posts.json"
UI = ROOT / "i18n" / "en" / "ui.json"
CHANNEL = "https://t.me/lesnymix"
CHAT = "https://t.me/+VXgXHnAXj9w2ZGYy"
AUTHORS = [f"{SITE}/#anton-podlesny", f"{SITE}/#pavel-podlesny"]
BLOG_ID = f"{SITE}/blog/#blog"
REQUIRED = ("slug", "title", "title_tag", "description", "date", "lead", "sources")

LANG = {
    "ru": {
        "src": SRC,
        "out": ROOT / "blog",
        "shell": ROOT / "faq" / "index.html",
        "prefix": "",
        "other_prefix": "en/",
        "html_lang": "ru",
        "og_locale": "ru_RU",
        "llms": ROOT / "llms.txt",
        "s": {
            "portfolio": "Портфолио",
            "blog": "Блог",
            "blog_link": "Блог",
            "in_short": "Коротко",
            "contents": "Содержание",
            "updated": "обновлено",
            "byline": "Антон и Павел Подлесные, звукорежиссёры студии",
            "sources": "Источники",
            "sources_intro": "Статья написана по постам студии в Telegram-канале",
            "about": "Об авторах",
            "about_text": ("<strong>Podlesny Twins</strong> — студия сведения и мастеринга братьев-близнецов "
                           "Антона и Павла Подлесных из Санкт-Петербурга. Работают с 2017 года, сотрудничали "
                           "с Хаски, ЛСП, NAVAI, T-Fest, Димой Биланом и ANNA ASTI."),
            "works": "Все работы с указанием роли",
            "tier": "Тир-лист техник сведения",
            "faq": "Вопросы и ответы",
            "more": "Ещё в блоге",
            "more_aria": "Другие статьи блога",
            "back": "Все статьи блога",
            "llms_head": "## Блог",
            "llms_intro": ("Статьи студии о сведении и мастеринге — {SITE}/blog/ — по материалам "
                           "Telegram-канала @lesnymix; у каждой внизу ссылки на исходные посты."),
            "llms_anchor": "## Полный контент",
        },
    },
    "en": {
        "src": SRC / "en",
        "out": ROOT / "en" / "blog",
        "shell": ROOT / "en" / "faq" / "index.html",
        "prefix": "en/",
        "other_prefix": "",
        "html_lang": "en",
        "og_locale": "en_US",
        "llms": ROOT / "i18n" / "en" / "llms.txt",
        "s": {
            "portfolio": "Portfolio",
            "blog": "Blog",
            "blog_link": "Blog",
            "in_short": "In short",
            "contents": "Contents",
            "updated": "updated",
            "byline": "Anton and Pavel Podlesny, mixing engineers at",
            "sources": "Sources",
            "sources_intro": "This article is based on the studio's posts in its Telegram channel (in Russian)",
            "about": "About the authors",
            "about_text": ("<strong>Podlesny Twins</strong> is a mixing and mastering studio run by twin brothers "
                           "Anton and Pavel Podlesny in Saint Petersburg. They have worked since 2017, with "
                           "artists including Husky, LSP, NAVAI, T-Fest, Dima Bilan and ANNA ASTI."),
            "works": "All credits with roles",
            "tier": "Mixing techniques tier list",
            "faq": "FAQ",
            "more": "More from the blog",
            "more_aria": "Other blog articles",
            "back": "All blog articles",
            "llms_head": "## Blog",
            "llms_intro": ("Articles by the studio on mixing and mastering, based on its Telegram channel "
                           "@lesnymix; each one links to the source posts (in Russian)."),
            "llms_anchor": "## Full content",
        },
    },
}

INDEX = {
    "title": "Блог Podlesny Twins — статьи о сведении и мастеринге",
    "description": ("Статьи звукорежиссёров Podlesny Twins о сведении и мастеринге: бас, транзиенты, "
                    "вокал, стерео, громкость и устройство темплейта — по материалам канала @lesnymix."),
    "h1": "Блог о сведении и мастеринге",
    "lead": ("Разборы приёмов и рабочих решений студии Podlesny Twins — "
             "по материалам нашего Telegram-канала @lesnymix."),
    "blog_name": "Блог Podlesny Twins",
}

# Press and interviews shown on the index. Facts from the publication itself.
INTERVIEWS = [
    {
        "title": "Антон и Павел Подлесные: большое интервью",
        "outlet": "ИМИ.Журнал",
        "date": "2026-07-15",
        "url": "https://i-m-i.ru/post/anton-i-pavel-podlesnye-bolshoe-intervyu",
        "about": ("Как пришли в профессию и получили первые крупные заказы, почему грязный звук — "
                  "это сложная звукорежиссёрская работа, в чём главная техническая проблема "
                  "soundcloud-сцены и как Скриптонит поменял подход к сведению в русском хип-хопе."),
    },
]

MONTHS_RU = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
             "сентября", "октября", "ноября", "декабря"]
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August",
             "September", "October", "November", "December"]

EXTRA_CSS = """
<style>
/* ---- blog: article head, prose, credits rows, and the index as a contents page ---- */
.pflink[aria-current="page"]{color:var(--red-ink)}
.dek{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 22px;margin:-4px 0 0;font-size:15px;color:var(--mut)}
.dek p,.dek .meta{margin:0;font-size:inherit}
.byline a{color:var(--ink2);font-weight:600;transition:color .15s}
.byline a:hover{color:var(--ink)}
.post{font-size:17px;line-height:1.75;color:var(--ink2);max-width:66ch}
.post p{margin:0 0 20px}
.post h2{margin:84px 0 22px}
.post>h2:first-child{margin-top:0}
.post h3{font-size:19px;font-weight:700;line-height:1.35;color:var(--ink);margin:40px 0 10px}
.post #faq~h3{margin:0;padding:24px 0 10px;border-top:1px solid var(--line)}
.post ul,.post ol{margin:0 0 24px;padding-left:22px}
.post li{margin:0 0 10px;padding-left:4px}
.post li::marker{color:var(--red);font-weight:700}
.post a,.src a,.about a{color:var(--ink);font-weight:500;text-decoration:underline;text-decoration-color:var(--red);text-decoration-thickness:1px;text-underline-offset:.24em;transition:text-decoration-thickness .15s,color .15s}
.post a:hover,.src a:hover,.about a:hover{color:#fff;text-decoration-thickness:2px}
.post strong{color:var(--ink);font-weight:600}
.post blockquote{margin:36px 0;padding:0;font-size:clamp(18px,1.7vw,21px);line-height:1.5;font-weight:500;color:var(--ink)}
.post blockquote p{margin:0}
.post figure{margin:40px 0 44px}
.post figure img{display:block;width:auto;max-width:100%;height:auto;max-height:min(78vh,720px);border-radius:6px;background:var(--surface)}
.post figcaption{font-size:13px;line-height:1.5;color:var(--mut);margin-top:12px;max-width:56ch}
.post code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.9em;background:var(--surface);padding:1px 5px;border-radius:4px}
.tbl{overflow-x:auto;margin:4px 0 28px;-webkit-overflow-scrolling:touch}
.tbl table{width:100%;border-collapse:collapse;font-size:14.5px;line-height:1.55;font-variant-numeric:tabular-nums}
/* only wide tables scroll sideways on phones; two columns fit as they are */
.tbl table:has(th:nth-child(3)){min-width:540px}
.tbl table:has(th:nth-child(4)){min-width:660px}
.tbl th,.tbl td{text-align:left;vertical-align:top;padding:11px 14px 11px 0;border-bottom:1px solid var(--line)}
.tbl th{font-size:11.5px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--mut)}
.tbl td:first-child{color:var(--ink);font-weight:600}

/* credits under the article: the same margin-head grid as the rest of the sheet */
.src,.about,.more{display:grid;grid-template-columns:var(--rail) minmax(0,1fr);column-gap:var(--gap);align-items:start;margin:0;padding:30px 0;border-top:1px solid var(--line)}
.src{margin-top:96px}
.src>:not(.eyebrow),.about>:not(.eyebrow),.more>:not(.eyebrow){grid-column:2}
.src>p:not(.eyebrow),.about>p:not(.eyebrow){margin:0 0 10px;font-size:15px;line-height:1.6;color:var(--ink2);max-width:62ch}
.src ul{list-style:none;margin:4px 0 0;padding:0}
.src li{margin:0;padding:6px 0;font-size:15px;line-height:1.5;color:var(--mut)}
.more ul{list-style:none;margin:0;padding:0}
.more li+li{border-top:1px solid var(--line)}
.more a{display:flex;align-items:center;min-height:52px;padding:14px 0;font-family:var(--display);font-weight:400;font-size:21px;line-height:1.1;color:var(--ink)}
.more li:first-child a{padding-top:0;min-height:44px}
.more .t{text-decoration:underline;text-decoration-color:transparent;text-decoration-thickness:2px;text-underline-offset:.14em;transition:text-decoration-color .2s}
.more a:hover .t,.more a:focus-visible .t{text-decoration-color:var(--red)}
.more a:focus-visible{outline:2px solid var(--red);outline-offset:4px}

/* ---- the index: a contents page across the full measure — title left, what it is about right ---- */
.tierlink{font-size:15px;line-height:1.6;color:var(--mut);margin:0;max-width:62ch}
.shelf{display:block;margin:72px 0 0;padding:0;border:0}
.shelf+.shelf{margin-top:88px}
.shelf>h2{margin:0 0 18px;font-size:22px;line-height:1.1}
.posts{list-style:none;margin:0;padding:0;border-bottom:1px solid var(--line)}
.posts li{position:relative;display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);column-gap:56px;align-items:start;padding:30px 0 32px;border-top:1px solid var(--line)}
.posts li>*{grid-column:2}
/* every article title in the display face, same size — on the index, under "Ещё в блоге" and as the article's own H1 */
.posts .pt{grid-column:1;grid-row:1 / span 3;font-family:var(--display);font-weight:400;font-size:clamp(24px,2.5vw,32px);line-height:1.04;color:var(--ink);text-decoration:underline;text-decoration-color:transparent;text-decoration-thickness:2px;text-underline-offset:.12em;transition:text-decoration-color .2s}
.posts .pt::before{content:"";position:absolute;inset:0}
.posts li:hover .pt{text-decoration-color:var(--red)}
.posts .pt:focus-visible{outline:none;text-decoration-color:var(--red)}
.posts li:has(.pt:focus-visible){outline:2px solid var(--red);outline-offset:6px}
.posts .pd{margin:3px 0 0;font-size:16px;line-height:1.55;color:#bdb6b6;transition:color .2s}
.posts li:hover .pd{color:var(--ink2)}
.posts .pm{margin:10px 0 0;font-size:13px;font-weight:500;color:var(--mut);font-variant-numeric:tabular-nums}
.coda{display:block;margin-top:96px;padding:30px 0 0;border-top:0}
.coda .faqfoot{margin:0;font-size:clamp(17px,1.5vw,19px);line-height:1.5;font-weight:500;color:var(--ink2);max-width:44ch}
.coda .faqfoot,.coda .back{margin-left:0}
.coda .back{margin-top:18px}
@media(min-width:768px) and (max-width:1023px){
  .post{font-size:16.5px}
}
@media(max-width:767px){
  .src,.about,.more{display:block}
  .posts li{display:block;padding:24px 0 26px}
  .posts .pd{margin-top:10px}
  .src{margin-top:72px}
  .coda{margin-top:72px}
}
@media(max-width:520px){
  .dek{gap:4px 16px;font-size:14px}
  .post{font-size:16.5px}
  .post h2{margin-top:60px}
  .posts .pt{font-size:clamp(22px,6.4vw,26px)}
}
</style>
"""

GA = (
    '<!-- Google tag (gtag.js) -->\n'
    '<script async src="https://www.googletagmanager.com/gtag/js?id=G-JWPH35TTVX"></script>\n'
    "<script>\n  window.dataLayer = window.dataLayer || [];\n"
    "  function gtag(){dataLayer.push(arguments);}\n"
    "  gtag('js', new Date());\n  gtag('config', 'G-JWPH35TTVX');\n</script>"
)


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def attr(s: str) -> str:
    return html.escape(s, quote=True)


def strip_tags(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def human_date(iso: str, lang: str) -> str:
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{d} {MONTHS_RU[m - 1]} {y}" if lang == "ru" else f"{MONTHS_EN[m - 1]} {d}, {y}"


def dotted(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{d}.{m}.{y}"


def ld_json(graph: list) -> str:
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)


# ── source parsing ─────────────────────────────────────────────────────

def parse(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    if not m:
        raise SystemExit(f"{path}: no front matter")
    meta: dict = {}
    key = None
    for line in m.group(1).split("\n"):
        if not line.strip():
            continue
        if re.match(r"^\s+- ", line):
            if key is None or not isinstance(meta.get(key), list):
                raise SystemExit(f"{path}: list item outside a list: {line!r}")
            meta[key].append(line.strip()[2:].strip())
            continue
        k, sep, v = line.partition(":")
        if not sep:
            raise SystemExit(f"{path}: bad front-matter line {line!r}")
        key, v = k.strip(), v.strip()
        meta[key] = v if v else []
    missing = [k for k in REQUIRED if not meta.get(k)]
    if missing:
        raise SystemExit(f"{path}: missing {', '.join(missing)}")
    if meta["slug"] != path.stem:
        raise SystemExit(f"{path}: slug {meta['slug']!r} must equal the file name")
    for k in ("date", "updated"):
        if meta.get(k) and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta[k]):
            raise SystemExit(f"{path}: {k} must be YYYY-MM-DD")
    if not meta.get("updated"):
        meta["updated"] = meta["date"]
    sources = []
    for s in meta["sources"]:
        parts = [x.strip() for x in s.split("|")]
        if len(parts) != 3 or not parts[0].isdigit() or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", parts[1]):
            raise SystemExit(f"{path}: source must be 'id | YYYY-MM-DD | title': {s!r}")
        sources.append({"id": int(parts[0]), "date": parts[1], "title": parts[2],
                        "url": f"{CHANNEL}/{parts[0]}"})
    meta["sources"] = sources
    tags = meta.get("tags") or ""
    meta["tags"] = [t.strip() for t in tags.split(",") if t.strip()] if isinstance(tags, str) else []
    meta["body"] = render_markdown(m.group(2))
    im = re.search(r'<img src="([^"]+)"[^>]* width="(\d+)" height="(\d+)"', meta["body"])
    meta["image"] = {"url": im.group(1), "width": int(im.group(2)), "height": int(im.group(3))} if im else None
    meta["faq"] = faq_pairs(meta["body"])
    meta["words"] = len(strip_tags(meta["lead"] + " " + meta["body"]).split())
    return meta


def render_markdown(src: str) -> str:
    md = markdown.Markdown(
        extensions=["tables", "attr_list", "toc", "sane_lists"],
        extension_configs={"toc": {"slugify": lambda value, sep: bwm.slugify(value)}},
    )
    out = md.convert(src)

    def link(m: re.Match) -> str:
        href = m.group(1)
        if href.startswith("/"):
            return f'<a href="{SITE}{href}"'
        if href.startswith("http") and not href.startswith(SITE):
            return f'<a href="{href}" rel="noopener"'
        return m.group(0)

    out = re.sub(r'<a href="([^"]+)"', link, out)
    out = re.sub(r'<p><img alt="([^"]*)" src="([^"]+)"(?: title="([^"]*)")? ?/?></p>', figure, out)
    return out.replace("<table>", '<div class="tbl"><table>').replace("</table>", "</table></div>")


def figure(m: re.Match) -> str:
    """![alt](/blog/img/x.jpg "caption") → <figure> with real width/height
    (no layout shift) and lazy loading; the caption is the visible text an
    answer engine can lift, the alt says what the picture shows."""
    alt, src, cap = m.group(1), m.group(2), m.group(3)
    if not src.startswith("/"):
        raise SystemExit(f"image must be a site path (/blog/img/…): {src}")
    path = ROOT / src.lstrip("/")
    if not path.is_file():
        raise SystemExit(f"image not found: {src}")
    from PIL import Image  # only needed when an article has pictures
    with Image.open(path) as im:
        w, h = im.size
    caption = f"<figcaption>{cap}</figcaption>" if cap else ""
    return (f'<figure><img src="{SITE}{src}" alt="{alt}" width="{w}" height="{h}" '
            f'loading="lazy" decoding="async">{caption}</figure>')


def faq_pairs(body: str) -> list[tuple[str, str]]:
    m = re.search(r'<h2 id="faq">.*?</h2>(.*)', body, re.S)
    if not m:
        return []
    seg = re.split(r"<h2[ >]", m.group(1))[0]
    return [(strip_tags(q), strip_tags(a))
            for q, a in re.findall(r"<h3[^>]*>(.*?)</h3>\s*(.*?)(?=<h3|\Z)", seg, re.S)]


def check(p: dict, lang: str) -> list[str]:
    """Soft GEO/SEO checks — printed as warnings, never fatal."""
    w = []
    if len(p["title_tag"]) > 65:
        w.append(f"title_tag {len(p['title_tag'])} chars (aim ≤ 60)")
    if not 110 <= len(p["description"]) <= 175:
        w.append(f"description {len(p['description'])} chars (aim 150–160)")
    n = len(p["lead"].split())
    if not 30 <= n <= 75:
        w.append(f"lead {n} words (aim 40–60)")
    if not p["faq"]:
        w.append("no FAQ block (## … {#faq})")
    if p["body"].count(f'href="{SITE}/') < 3:
        w.append("fewer than 3 internal links")
    if lang == "en" and re.search(r"[А-Яа-яЁё]", strip_tags(p["body"])):
        w.append("Cyrillic in the EN body (fine for release titles and artist names only)")
    return w


# ── shell ──────────────────────────────────────────────────────────────

def lifted_shell(lang: str, twin_rel: str) -> tuple[str, str]:
    cfg = LANG[lang]
    style, nav = shell({"shell": cfg["shell"], "twin_rel": twin_rel})
    blog_link = f'<a class="pflink" href="{SITE}/{cfg["prefix"]}blog/">{cfg["s"]["blog_link"]}</a>'
    if nav.count(blog_link) != 1:
        raise SystemExit(f"{cfg['shell'].relative_to(ROOT)}: header has no single blog link — cannot mark it current")
    current = blog_link.replace('">', '" aria-current="page">', 1)
    return style, nav.replace(blog_link, current), rail_script(cfg["shell"])


# ── article ────────────────────────────────────────────────────────────

def render_post(p: dict, lang: str, siblings: list[dict], has_twin: bool) -> str:
    cfg, s = LANG[lang], LANG[lang]["s"]
    base = f"{SITE}/{cfg['prefix']}"
    page = f"{base}blog/{p['slug']}/"
    twin_rel = (f"{cfg['other_prefix']}blog/{p['slug']}/" if has_twin
                else f"{cfg['other_prefix']}blog/")
    style, nav, rail_js = lifted_shell(lang, twin_rel)
    studio = studio_entity({"shell": cfg["shell"]})
    hreflang = bwm.hreflang_links(f"blog/{p['slug']}/") if has_twin else ""

    crumbs = {
        "@type": "BreadcrumbList",
        "@id": f"{page}#breadcrumbs",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": s["portfolio"], "item": base},
            {"@type": "ListItem", "position": 2, "name": s["blog"], "item": f"{base}blog/"},
            {"@type": "ListItem", "position": 3, "name": p["title"], "item": page},
        ],
    }
    posting = {
        "@type": "BlogPosting",
        "@id": f"{page}#article",
        "url": page,
        "mainEntityOfPage": page,
        "headline": p["title"],
        "description": p["description"],
        "abstract": p["lead"],
        "inLanguage": cfg["html_lang"],
        "datePublished": p["date"],
        "dateModified": p["updated"],
        "author": [{"@id": a} for a in AUTHORS],
        "publisher": {"@id": bwm.STUDIO_ID},
        "isPartOf": {"@id": BLOG_ID},
        "breadcrumb": {"@id": f"{page}#breadcrumbs"},
        "wordCount": p["words"],
        "citation": [
            {"@type": "SocialMediaPosting", "url": x["url"], "headline": x["title"],
             "datePublished": x["date"], "inLanguage": "ru", "author": {"@id": bwm.STUDIO_ID}}
            for x in p["sources"]
        ],
    }
    if has_twin:
        posting["workTranslation" if lang == "ru" else "translationOfWork"] = {
            "@id": f"{SITE}/{cfg['other_prefix']}blog/{p['slug']}/#article"}
    if p["tags"]:
        posting["keywords"] = ", ".join(p["tags"])
    if p["image"]:
        posting["image"] = {"@type": "ImageObject", **p["image"]}
    graph = [*studio, crumbs, posting]
    if p["faq"]:
        graph.append({
            "@type": "FAQPage",
            "@id": f"{page}#faq",
            "url": page,
            "inLanguage": cfg["html_lang"],
            "isPartOf": {"@id": f"{page}#article"},
            "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                for q, a in p["faq"]
            ],
        })

    sources = "\n".join(
        f'      <li><a href="{x["url"]}" rel="noopener">«{esc(x["title"])}»</a>, {human_date(x["date"], lang)}</li>'
        if lang == "ru" else
        f'      <li><a href="{x["url"]}" rel="noopener">{esc(x["title"])}</a>, {human_date(x["date"], lang)}</li>'
        for x in p["sources"]
    )
    others = "\n".join(
        f'      <li><a href="{base}blog/{o["slug"]}/"><span class="t">{esc(o["title"])}</span></a></li>'
        for o in siblings if o["slug"] != p["slug"]
    )
    contents = "\n".join(
        f'      <li><a href="#{hid}">{esc(strip_tags(h))}</a></li>'
        for hid, h in re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', p["body"], re.S)
    )
    og_image = (f'<meta property="og:image" content="{p["image"]["url"]}">\n'
                f'<meta property="og:image:width" content="{p["image"]["width"]}">\n'
                f'<meta property="og:image:height" content="{p["image"]["height"]}">\n'
                if p["image"] else "")
    updated = (f' · {s["updated"]} <time datetime="{p["updated"]}">{human_date(p["updated"], lang)}</time>'
               if p["updated"] != p["date"] else "")

    return f"""<!DOCTYPE html>
<html lang="{cfg["html_lang"]}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{GA}
<title>{esc(p["title_tag"])}</title>
<meta name="description" content="{attr(p["description"])}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{page}">
{hreflang.rstrip()}
<meta property="og:type" content="article">
<meta property="og:title" content="{attr(p["title"])}">
<meta property="og:description" content="{attr(p["description"])}">
<meta property="og:url" content="{page}">
<meta property="og:locale" content="{cfg["og_locale"]}">
<meta property="og:site_name" content="Podlesny Twins">
<meta property="article:published_time" content="{p["date"]}">
<meta property="article:modified_time" content="{p["updated"]}">
{og_image}<meta name="twitter:card" content="{"summary_large_image" if p["image"] else "summary"}">
<link rel="icon" type="image/png" href="{SITE}/favicon.png">
<script type="application/ld+json">{ld_json(graph)}</script>
{style}
{EXTRA_CSS}</head>
<body>
<div class="wrap">
  {nav}

  <p class="bc"><a href="{base}">{s["portfolio"]}</a> / <a href="{base}blog/">{s["blog"]}</a> / {esc(p["title"])}</p>

  <h1>{esc(p["title"])}</h1>
  <div class="dek">
    <p class="byline">{s["byline"]} <a href="{base}faq/">Podlesny Twins</a></p>
    <p class="meta"><time datetime="{p["date"]}">{human_date(p["date"], lang)}</time>{updated}</p>
  </div>

  <div class="intro">
    <p class="eyebrow">{s["in_short"]}</p>
    <p>{esc(p["lead"])}</p>
  </div>

  <div class="doc">
    <nav class="rail rail-c" aria-labelledby="contents-h">
      <p class="rail-h" id="contents-h">{s["contents"]}</p>
      <ol class="toc">
{contents}
      </ol>
    </nav>
    <article class="post flow">
{p["body"]}
    </article>
  </div>

  <aside class="src">
    <p class="eyebrow">{s["sources"]}</p>
    <p>{s["sources_intro"]} <a href="{CHANNEL}" rel="noopener">@lesnymix</a>:</p>
    <ul>
{sources}
    </ul>
  </aside>

  <aside class="about">
    <p class="eyebrow">{s["about"]}</p>
    <p>{s["about_text"]}</p>
    <p><a href="{base}track/">{s["works"]}</a> · <a href="{base}tier/">{s["tier"]}</a> · <a href="{base}faq/">{s["faq"]}</a></p>
  </aside>

  <nav class="more" aria-label="{s["more_aria"]}">
    <p class="eyebrow">{s["more"]}</p>
    <ul>
{others}
    </ul>
  </nav>

  <p class="back"><a href="{base}blog/">{s["back"]}</a></p>
</div>
{rail_js}
</body>
</html>
"""


# ── RU index (its EN twin comes from build_en.py) ──────────────────────

def render_index(posts: list[dict]) -> str:
    page = f"{SITE}/blog/"
    style, nav, _ = lifted_shell("ru", "en/blog/")
    studio = studio_entity({"shell": LANG["ru"]["shell"]})
    hreflang = bwm.hreflang_links("blog/")
    if not hreflang:
        raise SystemExit("build_who_mixed.EN_STATIC no longer lists blog/ — the index would lose hreflang")
    crumbs = {
        "@type": "BreadcrumbList",
        "@id": f"{page}#breadcrumbs",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Портфолио", "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": "Блог", "item": page},
        ],
    }
    graph = [
        *studio,
        crumbs,
        {
            "@type": "CollectionPage",
            "@id": f"{page}#webpage",
            "url": page,
            "name": INDEX["title"],
            "description": INDEX["description"],
            "inLanguage": "ru",
            "about": {"@id": bwm.STUDIO_ID},
            "mainEntity": {"@id": BLOG_ID},
            "breadcrumb": {"@id": f"{page}#breadcrumbs"},
        },
        {
            "@type": "Blog",
            "@id": BLOG_ID,
            "url": page,
            "name": INDEX["blog_name"],
            "description": INDEX["description"],
            "publisher": {"@id": bwm.STUDIO_ID},
            "blogPost": [
                {"@type": "BlogPosting", "@id": f"{SITE}/blog/{p['slug']}/#article",
                 "url": f"{SITE}/blog/{p['slug']}/", "headline": p["title"], "datePublished": p["date"]}
                for p in posts
            ],
        },
    ]
    items = "\n".join(running_order(posts))
    press = "\n".join(
        f'    <li><a class="pt" href="{i["url"]}" rel="noopener">{esc(i["title"])}</a>'
        f'<p class="pd">{esc(i["about"])}</p>'
        f'<p class="pm"><span>{esc(i["outlet"])}</span> · <time datetime="{i["date"]}">{dotted(i["date"])}</time></p></li>'
        for i in INTERVIEWS
    )
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{GA}
<title>{esc(INDEX["title"])}</title>
<meta name="description" content="{attr(INDEX["description"])}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{page}">
{hreflang.rstrip()}
<meta property="og:type" content="website">
<meta property="og:title" content="{attr(INDEX["title"])}">
<meta property="og:description" content="{attr(INDEX["description"])}">
<meta property="og:url" content="{page}">
<meta property="og:locale" content="ru_RU">
<meta name="twitter:card" content="summary">
<link rel="icon" type="image/png" href="{SITE}/favicon.png">
<script type="application/ld+json">{ld_json(graph)}</script>
{style}
{EXTRA_CSS}</head>
<body>
<div class="wrap">
  {nav}

  <div class="bc"><a href="{SITE}/">Портфолио</a> / Блог</div>

  <h1>{esc(INDEX["h1"])}</h1>
  <p class="lead">{esc(INDEX["lead"])}</p>
  <p class="tierlink">{tier_sentence()}</p>

  <section class="shelf">
  <h2 id="posts">Статьи</h2>
  <ul class="posts">
{items}
  </ul>
  </section>

  <section class="shelf">
  <h2 id="interviews">Интервью</h2>
  <ul class="posts">
{press}
  </ul>
  </section>

  <div class="coda">
  <p class="faqfoot">Новые заметки сначала выходят в Telegram-канале <a href="{CHANNEL}" rel="noopener">@lesnymix</a> · <a href="{CHAT}" rel="noopener">Чат</a></p>
  <p class="back"><a href="{SITE}/">Все работы студии</a></p>
  </div>
</div>
</body>
</html>
"""


def running_order(posts: list[dict]) -> list[str]:
    """Index rows, all alike: title on the left, teaser on the right. A row
    shows the date only when it differs from the row above, so a batch
    published on one day shows it once. No reading time and no pictures:
    the owner reads the first as generated filler, and the post images are
    too uneven to set side by side."""
    rows, prev = [], None
    for p in posts:
        link = f'<a class="pt" href="{SITE}/blog/{p["slug"]}/">{esc(p["title"])}</a>'
        teaser = f'<p class="pd">{esc(p["description"])}</p>'
        date = f'<time datetime="{p["date"]}">{dotted(p["date"])}</time>'
        when = f'<p class="pm">{date}</p>' if p["date"] != prev else ""
        rows.append(f'    <li>{link}{teaser}{when}</li>')
        prev = p["date"]
    return rows


# ── the tier-list pointer on the index ────────────────────────────────

def tier_count() -> int:
    return len(json.loads((ROOT / "tier.json").read_text(encoding="utf-8"))["items"])


def tier_sentence(lang: str = "ru") -> str:
    """One visible link from the blog to /tier/: the tier list had no internal
    referrer Google could see (it was found through the sitemap only)."""
    n = tier_count()
    if lang == "ru":
        word = "приёма" if n % 10 == 1 and n % 100 != 11 else "приёмов"   # «оценки 51 приёма»
        return (f'Ещё у нас есть <a href="{SITE}/tier/">тир-лист техник сведения</a>: '
                f"оценки {n} {word} сведения и мастеринга по шкале от L до F.")
    return (f'We also have a <a href="{SITE}/tier/">mixing techniques tier list</a>: '
            f"our ratings of {n} mixing and mastering techniques on a scale from L to F.")


# ── llms.txt (RU) and the EN llms template ─────────────────────────────

def patch_llms(lang: str, posts: list[dict]) -> None:
    cfg, s = LANG[lang], LANG[lang]["s"]
    path = cfg["llms"]
    src = path.read_text(encoding="utf-8")
    lines = [s["llms_head"], "", s["llms_intro"].format(SITE=SITE), ""]
    lines += [f"- [{p['title']}]({SITE}/{cfg['prefix']}blog/{p['slug']}/): {p['description']}" for p in posts]
    block = "\n".join(lines)
    head = s["llms_head"]
    if f"\n{head}\n" in src:
        src = re.sub(rf"\n{re.escape(head)}\n.*?(?=\n## )", "\n" + block + "\n", src, count=1, flags=re.S)
    else:
        anchor = s["llms_anchor"]
        if anchor not in src:
            raise SystemExit(f"{path.relative_to(ROOT)}: «{anchor}» anchor not found")
        src = src.replace(anchor, block + "\n\n" + anchor, 1)
    path.write_text(src, encoding="utf-8")


def sync_ui(ru_posts: list[dict], en_by_slug: dict) -> int:
    """The EN index is a translation of the RU one: make its title/teaser for
    each article the EN article's own title/description."""
    ui = json.loads(UI.read_text(encoding="utf-8"))
    n = 0
    if ui.get(tier_sentence("ru")) != tier_sentence("en"):   # inline-HTML entry for build_en
        ui = {k: v for k, v in ui.items() if not k.startswith("Ещё у нас есть <a href=")}
        ui[tier_sentence("ru")] = tier_sentence("en")
        n += 1
    for p in ru_posts:
        en = en_by_slug.get(p["slug"])
        if not en:
            continue
        for ru_key, en_val in ((p["title"], en["title"]), (p["description"], en["description"])):
            if ui.get(ru_key) != en_val:
                ui[ru_key] = en_val
                n += 1
    if n:
        UI.write_text(json.dumps(ui, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return n


# ── main ───────────────────────────────────────────────────────────────

def sort_posts(posts: list[dict]) -> list[dict]:
    posts.sort(key=lambda p: int(p.get("order") or 100))     # within one date: `order:`
    posts.sort(key=lambda p: p["date"], reverse=True)        # newest first
    return posts


def main() -> None:
    ru = sort_posts([parse(f) for f in sorted(SRC.glob("*.md"))])
    if not ru:
        raise SystemExit(f"{SRC.relative_to(ROOT)}: no articles")
    ru_slugs = {p["slug"] for p in ru}
    en_files = sorted((SRC / "en").glob("*.md")) if (SRC / "en").is_dir() else []
    en = [parse(f) for f in en_files]
    orphans = [p["slug"] for p in en if p["slug"] not in ru_slugs]
    if orphans:
        raise SystemExit(f"blog-src/en: no Russian original for {', '.join(orphans)}")
    order = {p["slug"]: i for i, p in enumerate(ru)}
    en.sort(key=lambda p: order[p["slug"]])                  # same order on both sides
    en_by_slug = {p["slug"]: p for p in en}

    for lang, posts in (("ru", ru), ("en", en)):
        out = LANG[lang]["out"]
        for p in posts:
            has_twin = (p["slug"] in en_by_slug) if lang == "ru" else True
            d = out / p["slug"]
            d.mkdir(parents=True, exist_ok=True)
            (d / "index.html").write_text(render_post(p, lang, posts, has_twin), encoding="utf-8")
            warn = check(p, lang)
            print(f"{LANG[lang]['prefix']}blog/{p['slug']}/ — {p['words']} words, {len(p['faq'])} FAQ"
                  + (f"  ⚠ {'; '.join(warn)}" if warn else ""))
        # stale article dirs (renamed or removed sources); the EN index itself is build_en's
        keep = {p["slug"] for p in posts}
        if out.is_dir():
            for d in out.iterdir():
                if d.is_dir() and d.name not in keep and (d / "index.html").is_file():
                    (d / "index.html").unlink()
                    d.rmdir()
                    print(f"removed stale {LANG[lang]['prefix']}blog/{d.name}/")

    (ROOT / "blog" / "index.html").write_text(render_index(ru), encoding="utf-8")
    MANIFEST.write_text(json.dumps([
        {k: p[k] for k in ("slug", "title", "description", "date", "updated", "lead")}
        | {"url": f"{SITE}/blog/{p['slug']}/", "sources": [x["url"] for x in p["sources"]]}
        | ({"en": {k: en_by_slug[p["slug"]][k] for k in ("title", "description", "lead", "updated")}
                  | {"url": f"{SITE}/en/blog/{p['slug']}/"}} if p["slug"] in en_by_slug else {})
        for p in ru], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    patch_llms("ru", ru)
    if en:
        patch_llms("en", en)
    synced = sync_ui(ru, en_by_slug)
    print(f"blog/index.html — {len(ru)} RU / {len(en)} EN; blog/posts.json; llms sections"
          + (f"; ui.json: {synced} index strings synced from EN articles" if synced else ""))


if __name__ == "__main__":
    main()
