"""Editorial blog index. All articles render on the server; JS only filters them."""
from html import escape

TOPICS = [('all', 'Все темы'), ('bass', 'Бас'), ('drums', 'Барабаны'), ('vocals', 'Вокал'), ('mastering', 'Мастеринг'), ('workflow', 'Рабочий процесс'), ('stereo', 'Стерео')]

def topic(post):
    tags = ' '.join(post.get('tags', [])) if isinstance(post.get('tags'), list) else post.get('tags', '')
    if 'бас' in tags: return 'bass'
    if 'транзиенты' in tags or 'барабаны' in tags: return 'drums'
    if 'вокал' in tags: return 'vocals'
    if 'LUFS' in tags: return 'mastering'
    if 'стерео' in tags: return 'stereo'
    return 'workflow'

ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M5 19 19 5M5 5h14v14"/></svg>'

def cover(kind):
    if kind == 'bass':
        rings = ''.join(f'<circle cx="{770 + i * 2}" cy="{392 + i * 4}" r="{45 + i * 13}"/>' for i in range(23))
        return f'<div class="entry-cover cover-bass" aria-hidden="true"><svg viewBox="0 0 800 440" preserveAspectRatio="xMidYMid slice"><g fill="none" stroke="currentColor" stroke-width="3">{rings}</g></svg><span class="cover-copy"><span>Низ</span><span>имеет</span><span>значение.</span></span></div>'
    if kind == 'drums':
        import math
        lines = ''.join(f'<path d="M{30 + group*126 + j*8} {125 - 100*math.exp(-j/4)}v{200*math.exp(-j/4)}"/>' for group in range(4) for j in range(12))
        return f'<div class="entry-cover cover-drums" aria-hidden="true"><svg viewBox="0 0 530 250"><g fill="none" stroke="currentColor" stroke-width="1.5">{lines}</g></svg></div>'
    if kind == 'workflow':
        return '<div class="entry-cover cover-workflow" aria-hidden="true"><svg viewBox="0 0 160 160" fill="none" stroke="currentColor" stroke-width="3"><path d="M58 18h61v84H58zM24 62h60v80H24zM89 42h61v82H89z"/></svg></div>'
    return ''

TEASERS = {
    'pochemu-bas-ploho-zvuchit-v-mikse': (None, 'Рабочий диапазон баса, гармоники и конфликт с бочкой.'),
    'tranzienty-v-svedenii': ('Транзиенты в сведении: как вернуть атаку бочке', None),
    'templeyt-dlya-svedeniya': ('Как устроен наш темплейт для сведения', 'Обработка, роутинг и пять главных шин.'),
}

def index_rows(posts, site, tier_count):
    labels = dict(TOPICS)
    rows = []
    for i, p in enumerate(posts):
        if i == 3:
            rows.append(f'<li class="journal-resource"><a href="{site}/tier/">Тир-лист техник сведения{ARROW}</a><p>Приёмов в тир-листе: {tier_count}. Наши оценки по шкале от L до F.</p></li>')
            rows.append('<li class="archive-divider"><h2>Все материалы</h2><a href="https://t.me/lesnymix">@lesnymix</a></li>')
        kind = topic(p)
        title, description = TEASERS.get(p['slug'], (None, None))
        title, description = title or p['title'], description or p['description']
        y, m, d = p['date'].split('-')
        treatment = ['featured', 'secondary', 'compact'][i] if i < 3 else 'archive-entry'
        art = cover(kind) if i < 3 else ''
        rows.append(f'''<li class="journal-entry {treatment}" data-topic="{kind}">
  <article>
    {art}
    <h3><a href="{site}/blog/{p['slug']}/">{escape(title)}</a></h3>
    <p class="entry-description">{escape(description)}</p>
    <div class="entry-meta"><span>{labels[kind]}</span><time datetime="{p['date']}">{d}.{m}.{y}</time></div>
    <span class="read-link" aria-hidden="true">Читать статью{ARROW}</span>
  </article>
</li>''')
    return '\n'.join(line.rstrip() for line in '\n'.join(rows).splitlines())

def topic_controls(posts):
    return '\n'.join(f'<button type="button" data-filter="{key}" aria-pressed="{"true" if key == "all" else "false"}">{label}</button>' for key, label in TOPICS)

CSS = '''<style>
@font-face{font-family:Literal;src:url('https://static.tildacdn.com/tild6330-3266-4634-a532-316339613139/LiteralBold.WOFF') format('woff');font-weight:700;font-style:normal;font-display:swap}
.blog-index{--bg:#090b0f;--surface:#0b1723;--ink:#f2f4f7;--ink2:#bbc5d0;--mut:#a2adba;--line:#505a65;--blue:#b9d9ef;--red:var(--blue);--red-ink:var(--blue);background:var(--bg);color:var(--ink)}
html:has(.blog-index){scrollbar-color:#505a65 #090b0f}
.blog-index ::selection{background:var(--blue);color:var(--bg)}
.blog-index .wrap{max-width:1536px;padding:24px 44px 56px}
.blog-index .pfnav{padding:0;margin:0;border:0;min-height:44px}
.blog-index .pfbrand{width:145px;height:39px}
.blog-index .navlinks{gap:30px}
.blog-index .pflink{font-size:14px;font-weight:400;text-transform:none;letter-spacing:0}
.blog-index .pflink+.pflink{border:0;padding-left:0}
.blog-index .wave,.blog-index .bc{display:none}
.blog-index .journal-head{display:flex;align-items:center;justify-content:space-between;gap:40px;margin:38px 0 30px}
.blog-index h1{font:700 clamp(42px,6.2vw,92px)/1.1 Literal,'Work Sans',sans-serif;letter-spacing:-.04em;color:var(--blue);margin:0;max-width:none;text-wrap:nowrap}
.blog-index .journal-intro p{font-size:16px;line-height:1.6;margin:0;color:var(--ink2)}
.blog-index .journal-intro .journal-byline{font-size:14px;margin-top:3px}
.blog-index .journal-browser{border-top:1px solid var(--line);padding-top:12px;position:relative}
.blog-index .browser-top{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}
.blog-index [data-journal-controls]{display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:16px}
.blog-index .topics{display:flex;flex-wrap:wrap;gap:0 24px}
.blog-index .topics button{font:inherit;font-size:14px;color:var(--ink2);border:0;background:transparent;padding:10px 0;min-height:44px;cursor:pointer;white-space:nowrap}
.blog-index .topics button[aria-pressed=true]{color:var(--ink)}
.blog-index .topics button[aria-pressed=true]::before{content:'';display:inline-block;width:13px;height:13px;background:var(--blue);margin-right:12px}
.blog-index .topics button:hover{color:var(--blue)}
.blog-index .search{order:2;display:flex;gap:12px;align-items:center;color:var(--ink2);width:205px;flex-shrink:0}
.blog-index .search svg{width:20px;height:20px;flex-shrink:0}
.blog-index input{font:inherit;font-size:15px;background:transparent;border:0;border-bottom:1px solid transparent;min-width:0;width:100%;min-height:44px;color:var(--ink);padding:8px 0;border-radius:0;caret-color:var(--blue)}
.blog-index input::placeholder{color:var(--ink2);opacity:1}
.blog-index input:hover{border-color:var(--line)}
.blog-index input:focus-visible,.blog-index button:focus-visible,.blog-index a:focus-visible{outline:2px solid var(--blue);outline-offset:5px}
.blog-index .result-status{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}
.blog-index .journal-entries{display:grid;grid-template-columns:minmax(0,1.65fr) minmax(0,1fr);gap:28px 36px;list-style:none;padding:0;margin:0}
.blog-index .journal-entry{min-width:0}
.blog-index .journal-entry article{position:relative;height:100%}
.blog-index .featured{grid-column:1;grid-row:1 / 4}
.blog-index .secondary{grid-column:2;grid-row:1}
.blog-index .compact{grid-column:2;grid-row:2;border-top:1px solid var(--line);padding-top:22px}
.blog-index .journal-resource{grid-column:2;grid-row:3;border-top:1px solid var(--line);padding-top:20px;align-self:end}
.blog-index .entry-cover{overflow:hidden;position:relative;margin-bottom:20px;pointer-events:none}
.blog-index .entry-cover svg{display:block;width:100%;height:100%}
.blog-index .cover-bass{aspect-ratio:1.82;background:var(--blue);color:#090b0f;container-type:inline-size}
.blog-index .cover-bass>svg{position:absolute;inset:0}
.blog-index .cover-copy{position:relative;display:flex;flex-direction:column;font:700 clamp(44px,8vw,108px)/1 Literal,sans-serif;font-size:11.5cqw;letter-spacing:-.04em;padding:3.8% 4%;max-width:80%}
.blog-index .cover-drums{background:#0b1723;color:var(--ink);aspect-ratio:2.12}
.blog-index .cover-workflow{width:29%;float:right;margin:0 0 15px 20px;background:var(--blue);color:var(--bg);aspect-ratio:1}
.blog-index h2,.blog-index h3{font-family:Literal,'Work Sans',sans-serif;font-weight:700;letter-spacing:-.02em;color:var(--ink);text-wrap:pretty}
.blog-index .journal-entry h3{font-size:clamp(22px,2vw,29px);line-height:1.25;margin:0 0 13px}
.blog-index .featured h3{font-size:clamp(25px,2.2vw,33px)}
.blog-index .journal-entry h3 a::after{content:'';position:absolute;inset:0;z-index:1}
.blog-index .journal-entry h3 a:focus-visible{outline:0}
.blog-index .journal-entry:has(a:focus-visible){outline:2px solid var(--blue);outline-offset:6px}
.blog-index .journal-entry:hover h3{color:var(--blue)}
.blog-index .entry-description{font-size:16px;line-height:1.6;color:var(--ink2);margin:0 0 16px;max-width:65ch}
.blog-index .secondary .entry-description{display:none}
.blog-index .entry-meta{font-size:12px;color:var(--mut);display:flex;gap:16px;flex-wrap:wrap;font-variant-numeric:tabular-nums;margin-bottom:12px}
.blog-index .read-link{display:inline-flex;align-items:center;gap:18px;color:var(--blue);font-size:15px;min-height:36px;border-bottom:1px solid var(--blue)}
.blog-index .read-link svg,.blog-index .journal-resource svg{height:20px;width:20px}
.blog-index .secondary .read-link,.blog-index .compact .read-link{display:none}
.blog-index .journal-resource a{color:var(--blue);font-size:16px;display:inline-flex;align-items:center;gap:18px;text-decoration:underline;text-underline-offset:5px;min-height:44px}
.blog-index .journal-resource p{font-size:14px;line-height:1.6;color:var(--mut);margin:4px 0 0}
.blog-index .archive-divider{grid-column:1 / -1;border-top:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;padding-top:20px;margin-top:6px}
.blog-index .archive-divider h2{font-size:22px;margin:0}
.blog-index .archive-divider a{font-size:14px;color:var(--mut);min-height:44px;display:flex;align-items:center}
.blog-index .archive-entry{border-top:1px solid #252e37;padding-top:22px;padding-bottom:12px}
.blog-index .archive-entry h3{font-size:25px;max-width:32ch}
.blog-index .is-filtered .journal-entries{grid-template-columns:repeat(2,minmax(0,1fr))}
.blog-index .is-filtered .journal-entry{grid-area:auto;padding-top:20px;border-top:1px solid var(--line)}
.blog-index .is-filtered .entry-cover,.blog-index .is-filtered .journal-resource,.blog-index .is-filtered .archive-divider{display:none}
.blog-index .is-filtered .journal-entry h3{font-size:25px}
.blog-index .is-filtered .secondary .entry-description{display:block}
.blog-index .journal-empty{padding:40px 0}
.blog-index .journal-empty p{color:var(--ink2)}
.blog-index .reset-search{font:inherit;color:var(--blue);background:transparent;border:1px solid var(--line);padding:10px 20px;min-height:44px;cursor:pointer}
.blog-index .press-section{margin-top:55px;padding-top:30px;border-top:1px solid var(--line);display:grid;grid-template-columns:1fr 2fr;gap:40px}
.blog-index .press-section>h2{font-size:26px;margin:0}
.blog-index .press-section .posts{border:0}
.blog-index .press-section .posts li{display:block;border:0;padding:0}
.blog-index .press-section .posts .pt{font:700 25px/1.3 Literal,sans-serif;margin-bottom:14px;display:block}
.blog-index .press-section .posts .pd{color:var(--ink2)}
.blog-index .coda{display:flex;justify-content:space-between;gap:25px;align-items:center;border-top:1px solid var(--line);padding-top:24px;margin-top:50px}
.blog-index .coda .faqfoot{font-size:14px;color:var(--mut)}
.blog-index .coda .back{margin:0}
.blog-index [hidden]{display:none!important}
.blog-index .skip-link{position:absolute;left:20px;top:-80px;z-index:5;padding:12px;background:var(--blue);color:var(--bg)}
.blog-index .skip-link:focus{top:8px}
@media(max-width:1100px){.blog-index .wrap{padding:24px 28px 45px}.blog-index .journal-head{gap:24px}.blog-index h1{font-size:6.2vw}.blog-index .journal-intro p{font-size:14px}.blog-index [data-journal-controls]{flex-wrap:wrap}.blog-index .search{width:180px}.blog-index .topics{gap:0 18px}.blog-index .journal-entries{gap:24px}.blog-index .journal-entry h3{font-size:22px}.blog-index .entry-description{font-size:15px}}
@media(max-width:767px){.blog-index .wrap{padding:18px 20px 36px}.blog-index .pfnav{gap:14px}.blog-index .pfbrand{width:120px;height:32px}.blog-index .navlinks{gap:20px}.blog-index .pflink{font-size:13px}.blog-index .journal-head{display:block;margin:28px 0 20px}.blog-index h1{font-size:clamp(32px,8.7vw,64px);letter-spacing:-.04em}.blog-index .journal-intro{margin-top:17px}.blog-index .journal-intro p{font-size:14px}.blog-index [data-journal-controls]{display:flex;gap:4px;margin-bottom:14px}.blog-index .topics{gap:0 18px}.blog-index .topics button{font-size:13px}.blog-index .search{width:100%;margin-top:3px}.blog-index .search input{font-size:16px;border-color:#252e37}.blog-index .journal-entries,.blog-index .is-filtered .journal-entries{display:block}.blog-index .journal-entry{margin-bottom:28px}.blog-index .cover-bass{aspect-ratio:1.5}.blog-index .cover-copy{font-size:12.5cqw;max-width:90%;padding:6% 5%}.blog-index .entry-cover{margin-bottom:18px}.blog-index .journal-entry h3,.blog-index .featured h3{font-size:24px}.blog-index .secondary{padding-top:24px;border-top:1px solid var(--line)}.blog-index .cover-drums{aspect-ratio:2.3}.blog-index .entry-description{font-size:15px}.blog-index .journal-resource{padding:20px 0 26px}.blog-index .archive-divider{margin:0 0 20px;padding-top:18px}.blog-index .archive-divider h2{font-size:20px}.blog-index .archive-entry h3{font-size:23px}.blog-index .press-section{display:block;margin-top:38px}.blog-index .press-section>h2{font-size:23px;margin-bottom:22px}.blog-index .press-section .posts .pt{font-size:23px}.blog-index .coda{display:block;margin-top:36px}.blog-index .coda .back{margin-top:10px}}
@media(prefers-reduced-motion:reduce){.blog-index *{transition:none!important;scroll-behavior:auto!important}}
</style>'''

JS = '''<script>
(() => {
  const controls = document.querySelector('[data-journal-controls]');
  const input = document.querySelector('#article-search');
  const buttons = [...document.querySelectorAll('[data-filter]')];
  const entries = [...document.querySelectorAll('.journal-entry')];
  const status = document.querySelector('#result-status');
  const empty = document.querySelector('#journal-empty');
  const isEN = document.documentElement.lang === 'en';
  const normalize = value => value.toLocaleLowerCase().normalize('NFKC').replace(/ё/g, 'е');
  const index = entries.map(node => ({node, text:normalize(node.textContent)}));
  let topic = 'all';
  controls.hidden = false;
  function apply() {
    const words = normalize(input.value).trim().split(/\\s+/).filter(Boolean);
    let count = 0;
    index.forEach(({node, text}) => {
      node.hidden = !((topic === 'all' || node.dataset.topic === topic) && words.every(word => text.includes(word)));
      if (!node.hidden) count++;
    });
    buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.filter === topic)));
    status.textContent = (isEN ? 'Articles: ' : 'Статей: ') + count + ' / ' + entries.length;
    empty.hidden = count !== 0;
    document.querySelector('.journal-browser').classList.toggle('is-filtered', topic !== 'all' || words.length > 0);
  }
  buttons.forEach(button => button.addEventListener('click', () => {topic = button.dataset.filter;apply();}));
  input.addEventListener('input', apply);
  document.querySelector('.reset-search').addEventListener('click', () => {topic = 'all';input.value = '';apply();input.focus();});
  apply();
})();
</script>'''
