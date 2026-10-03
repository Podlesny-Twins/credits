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

def index_rows(posts, site):
    labels = dict(TOPICS)
    rows = []
    for i, p in enumerate(posts):
        kind = topic(p)
        y, m, d = p['date'].split('-')
        rows.append(f'''<li class="journal-entry{' featured' if i == 0 else ''}" data-topic="{kind}">
  <article>
    <h3><a href="{site}/blog/{p['slug']}/">{escape(p['title'])}</a></h3>
    <p class="entry-description">{escape(p['description'])}</p>
    <div class="entry-meta"><span>{labels[kind]}</span><time datetime="{p['date']}">{d}.{m}.{y}</time></div>
    <span class="entry-arrow" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 12h16M13 5l7 7-7 7"/></svg></span>
  </article>
</li>''')
    return '\n'.join(rows)

def topic_controls(posts):
    return '\n'.join(f'<button type="button" data-filter="{key}" aria-pressed="{"true" if key == "all" else "false"}">{label}<span aria-hidden="true">{len(posts) if key == "all" else sum(topic(p) == key for p in posts)}</span></button>' for key, label in TOPICS)

CSS = '''<style>
/* The index has its own reading hierarchy; article pages retain their shell. */
@font-face{font-family:'Literal';src:url('https://static.tildacdn.com/tild6330-3266-4634-a532-316339613139/LiteralBold.WOFF') format('woff');font-weight:700;font-style:normal;font-display:swap}
.blog-index{--mut:#aaa4a0;--line:#3b3935}
.blog-index .wrap{max-width:1320px;padding:30px 48px 60px}
.blog-index .pfnav{margin-bottom:0;padding-bottom:20px}
.blog-index .wave{display:none}
.blog-index .bc{margin:24px 0 25px}
.blog-index .journal-head{display:grid;grid-template-columns:1.3fr 1fr;gap:64px;align-items:end;margin:0 0 42px}
.blog-index h1{font-size:clamp(54px,6.5vw,88px);line-height:1.02;margin:0;max-width:10em;text-wrap:balance}
.blog-index .journal-intro{padding-bottom:5px}
.blog-index .journal-intro p{font-size:17px;line-height:1.65;color:var(--ink2);margin:0;max-width:44ch}
.blog-index .journal-intro .journal-byline{margin-top:18px;font-size:13px;color:var(--mut)}
.blog-index .journal-byline a{text-decoration:underline;text-underline-offset:4px}
.blog-index .journal-browser{position:relative;border-top:1px solid var(--line);padding-top:20px;margin-bottom:0}
.blog-index .browser-top{display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:8px}
.blog-index .browser-top h2{font-size:30px;margin:0}
.blog-index .search{position:absolute;right:0;top:10px;display:flex;align-items:center;gap:10px;border-bottom:1px solid #77716b;width:280px;color:var(--mut)}
.blog-index .search svg{width:18px;height:18px;flex-shrink:0}
.blog-index input{font:inherit;font-size:15px;color:var(--ink);width:100%;min-width:0;border:0;background:transparent;padding:11px 0;min-height:44px;caret-color:var(--red-ink);border-radius:0}
.blog-index input::placeholder{color:var(--mut);opacity:1}
.blog-index input:focus-visible{outline:2px solid var(--red-ink);outline-offset:4px}
.blog-index .topics{display:flex;flex-wrap:wrap;gap:0 25px;margin-bottom:8px}
.blog-index .topics button{font:inherit;font-size:14px;min-height:44px;border:0;border-bottom:2px solid transparent;background:none;padding:8px 0;color:var(--mut);cursor:pointer;white-space:nowrap;transition:color .18s,border-color .18s}
.blog-index .topics button span{margin-left:7px;font-size:11px;font-variant-numeric:tabular-nums}
.blog-index .topics button[aria-pressed=true]{color:var(--ink);border-color:var(--red-ink)}
.blog-index .topics button:hover{color:#fff}
.blog-index button:focus-visible{outline:2px solid var(--red-ink);outline-offset:4px}
.blog-index .result-status{font-size:13px;color:var(--mut);margin:10px 0 18px;min-height:21px}
.blog-index .journal-layout{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:56px}
.blog-index .journal-entries{list-style:none;margin:0;padding:0}
.blog-index .journal-entry{border-top:1px solid var(--line)}
.blog-index .journal-entry article{position:relative;padding:28px 38px 30px 0}
.blog-index .journal-entry h3{font-family:'Literal','Work Sans',Arial,sans-serif;font-size:25px;line-height:1.3;font-weight:700;letter-spacing:-.02em;margin:0 0 12px;text-wrap:pretty;max-width:30ch}
.blog-index .journal-entry h3 a::after{content:'';position:absolute;inset:0}
.blog-index .journal-entry h3 a{transition:color .18s}
.blog-index .journal-entry h3 a:hover{color:#fff;text-decoration:underline;text-decoration-color:var(--red-ink);text-underline-offset:5px;text-decoration-thickness:1px}
.blog-index .journal-entry:has(a:focus-visible){outline:2px solid var(--red-ink);outline-offset:4px}
.blog-index .journal-entry h3 a:focus-visible{outline:0}
.blog-index .entry-description{font-size:15px;color:var(--ink2);line-height:1.65;margin:0 0 18px;max-width:68ch}
.blog-index .entry-meta{display:flex;flex-wrap:wrap;align-items:center;gap:8px 22px;font-size:12px;color:var(--mut);font-variant-numeric:tabular-nums}
.blog-index .entry-meta span{color:var(--ink2)}
.blog-index .entry-arrow{position:absolute;right:0;top:34px;width:24px;height:24px;color:var(--mut);transition:transform .2s,color .2s}
.blog-index .entry-arrow svg{display:block;width:100%;height:100%}
.blog-index .journal-entry:hover .entry-arrow{transform:translateX(4px);color:var(--red-ink)}
.blog-index .featured{border-top:2px solid var(--red)}
.blog-index .featured h3{font-size:clamp(29px,3vw,39px);line-height:1.17;max-width:23ch}
.blog-index .featured article{padding-top:26px;padding-bottom:32px}
.blog-index .journal-aside{border-top:2px solid var(--line);padding-top:26px}
.blog-index .tier-feature{display:block;background:#e4dfd5;color:#242321;padding:25px 24px 28px;transition:background .2s}
.blog-index .tier-feature:hover{background:#f2ede3}
.blog-index .tier-feature h2{font-size:38px;line-height:1.08;color:inherit;margin:0 0 20px}
.blog-index .tier-feature p{font-size:15px;line-height:1.6;margin:0 0 25px}
.blog-index .tier-feature .tier-action{font-size:14px;font-weight:700;border-bottom:1px solid #a22c11;padding-bottom:4px}
.blog-index .aside-channel{margin-top:30px;padding-top:22px;border-top:1px solid var(--line)}
.blog-index .aside-channel h2{font-size:25px;margin:0 0 12px}
.blog-index .aside-channel p{font-size:14px;color:var(--ink2);line-height:1.65;margin:0 0 10px}
.blog-index .aside-channel a{display:inline-flex;min-height:44px;align-items:center;color:var(--ink);font-size:16px;text-decoration:underline;text-decoration-color:var(--red-ink);text-underline-offset:5px}
.blog-index .journal-empty{padding:32px 0;border-top:1px solid var(--line)}
.blog-index .journal-empty p{margin:0 0 10px;color:var(--ink2)}
.blog-index .reset-search{background:transparent;border:1px solid #827b74;color:var(--ink);font:inherit;font-size:14px;padding:10px 16px;min-height:44px;cursor:pointer}
.blog-index .press-section{margin-top:64px;padding-top:28px;border-top:1px solid var(--line);display:grid;grid-template-columns:1fr 2fr;gap:48px}
.blog-index .press-section>h2{font-size:40px;margin:0}
.blog-index .press-section .posts{border-bottom:0}
.blog-index .press-section .posts li{display:block;border:0;padding:0}
.blog-index .press-section .posts .pt{font-family:'Literal','Work Sans',Arial,sans-serif;font-size:25px;line-height:1.3;display:block;margin-bottom:14px}
.blog-index .press-section .posts .pd{font-size:15px}
.blog-index .coda{margin-top:56px;padding-top:20px;border-top:1px solid var(--line);display:flex;justify-content:space-between;gap:24px;align-items:center}
.blog-index .coda .faqfoot{font-size:13px;max-width:55ch}
.blog-index .coda .back{font-size:13px;margin:0}
.blog-index [hidden]{display:none!important}
.blog-index .skip-link{position:absolute;left:24px;top:-80px;padding:12px;background:var(--ink);color:var(--bg);z-index:5}
.blog-index .skip-link:focus{top:8px}
@media(min-width:1600px){.blog-index .wrap{max-width:1400px}}
@media(max-width:1000px){.blog-index .wrap{padding-left:32px;padding-right:32px}.blog-index .journal-head{gap:35px}.blog-index .journal-layout{grid-template-columns:minmax(0,1fr) 240px;gap:32px}.blog-index .topics{gap:0 20px}}
@media(max-width:767px){.blog-index .wrap{padding:20px 20px 40px}.blog-index .pfnav{gap:10px;padding-bottom:14px}.blog-index .journal-head{display:block;margin-bottom:25px}.blog-index h1{font-size:clamp(42px,9.7vw,66px);max-width:12em;line-height:1.03}.blog-index .bc{margin:18px 0}.blog-index .journal-intro{margin-top:18px}.blog-index .journal-intro p{font-size:15px;line-height:1.55;max-width:46ch}.blog-index .journal-intro .journal-byline{margin-top:10px;font-size:12px}.blog-index .browser-top{align-items:center}.blog-index .browser-top h2{font-size:27px}.blog-index .search{width:55%;max-width:280px}.blog-index input{font-size:16px}.blog-index .topics{gap:0 19px;margin-top:8px}.blog-index .topics button{font-size:13px}.blog-index .journal-layout{display:block}.blog-index .journal-entry h3{font-size:23px}.blog-index .featured h3{font-size:29px}.blog-index .journal-entry article{padding:24px 30px 25px 0}.blog-index .entry-description{font-size:15px}.blog-index .journal-aside{margin-top:32px;display:grid;grid-template-columns:1fr 1fr;gap:24px}.blog-index .aside-channel{margin:0;padding-top:0;border:0}.blog-index .tier-feature{padding:22px}.blog-index .press-section{display:block;margin-top:40px}.blog-index .press-section>h2{font-size:32px;margin-bottom:24px}.blog-index .press-section .posts .pt{font-size:23px}.blog-index .coda{display:block;margin-top:36px}.blog-index .coda .back{margin-top:10px}}
@media(max-width:450px){.blog-index .journal-aside{display:block}.blog-index .aside-channel{margin-top:28px}.blog-index .topics{gap:0 15px}.blog-index .topics button span{margin-left:4px}.blog-index .navlinks{gap:12px}.blog-index .pflink+.pflink{padding-left:12px}.blog-index .pflang{min-width:44px;justify-content:center}}
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
  }
  buttons.forEach(button => button.addEventListener('click', () => {topic = button.dataset.filter;apply();}));
  input.addEventListener('input', apply);
  document.querySelector('.reset-search').addEventListener('click', () => {topic = 'all';input.value = '';apply();input.focus();});
  apply();
})();
</script>'''
