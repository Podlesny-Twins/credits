/* Sandbox for credits.podlesnytwins.com.
   Collects the owner's edits and hands them over on one button. It never
   touches the site itself and has no access to the repository. */
(() => {
  const $ = (sel, el = document) => el.querySelector(sel);
  const read = id => JSON.parse(document.getElementById(id).textContent);

  const CAT = read("catalog");
  const WORKS = CAT.works;
  const BY_KEY = new Map(WORKS.map(w => [w.key, w]));
  for (const w of WORKS) for (const t of w.tracks) BY_KEY.set(t.key, { ...t, kind: "track", parent: w });

  /* Every publish reloads the page, and a publish can fail (network, 404 on
     the reload, a closed tab). Anything living only in the published document
     is lost in that window — so answers are ALSO written to localStorage the
     moment they're typed, and merged back on load. This is the belt: the
     published state is the braces. */
  /* The key carries the catalogue build: once edits are applied and the
     sandbox is rebuilt, the key changes and the stale draft is ignored (and
     swept) instead of resurrecting work that already went live. */
  const BUILD = read("state").buildId || "0";
  const DRAFT = "credits-sandbox-draft-v1:" + BUILD;
  try {
    // Answers typed under the previous build (or the build-less first version)
    // are carried over once, then the old keys are swept: an unsent answer must
    // survive the very upgrade that fixes losing it.
    const LEGACY = "credits-sandbox-draft-v1";     // first version, no build tag
    const merged = JSON.parse(localStorage.getItem(DRAFT) || "{}");
    let carried = false;
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const k = localStorage.key(i);
      if (!k || !k.startsWith(LEGACY) || k === DRAFT) continue;
      if (k === LEGACY) {                          // carry it over once
        try { Object.assign(merged, JSON.parse(localStorage.getItem(k)) || {}); carried = true; } catch {}
      }
      localStorage.removeItem(k);                  // other builds: already applied
    }
    if (carried) localStorage.setItem(DRAFT, JSON.stringify(merged));
  } catch {}
  const draft = {
    read() { try { return JSON.parse(localStorage.getItem(DRAFT)) || {}; } catch { return {}; } },
    write(obj) { try { localStorage.setItem(DRAFT, JSON.stringify(obj)); } catch {} },
    clear(keys) {
      const d = this.read();
      for (const k of keys) delete d[k];
      this.write(d);
    },
  };

  let state = read("state");
  if (!state.moves) state.moves = [];
  if (state.interview === undefined) state.interview = null;

  // Recover anything typed but never published (the 404-mid-interview case).
  let recovered = 0;
  for (const [key, note] of Object.entries(draft.read())) {
    if (!note) continue;
    const cur = state.edits[key]?.note;
    if (cur === note) continue;          // already published — nothing to do
    if ((BY_KEY.get(key)?.note || "") === note) continue;   // already live on the site
    state.edits[key] = { ...(state.edits[key] || {}), note };
    recovered++;
  }
  let tab = "catalog";
  let open = null;          // key of the work being edited
  let query = "", genreF = "";
  let sorting = false;      // "порядок" mode
  let picked = null;        // the work taken to be re-placed
  let rev = 0;              // bumped by every edit; identifies a snapshot
  let saved = 0;            // the rev last written into the page
  let publishing = false;
  let again = false;        // an edit arrived mid-publish
  let readOnly = false;
  let saveError = null;   // last publish failure, shown in the UI
  let artifact = null;
  const root = $("#root");

  // Outside the artifact viewer there is no window.claude at all — the page
  // must still open and work, it just cannot save.
  Promise.resolve(window.claude?.use?.("artifact"))
    .then(a => { artifact = a || null; render(); save(); }, () => {});

  /* ── edits ──────────────────────────────────────────────
     An edit is stored only when it differs from what the site has now;
     setting a field back to its original value removes it again, so the
     summary never shows a change that isn't one. */
  const original = (key, field) => {
    const w = BY_KEY.get(key);
    if (!w) return "";
    if (field === "note") return w.note || "";
    if (field === "hidden") return !!(w.parent ? w.parent.hidden : w.hidden);
    if (field === "role") return w.role || (w.kind === "album" ? albumRole(w) : "mix");
    return w[field] ?? "";
  };
  const albumRole = w => {
    const set = new Set(w.tracks.map(t => t.role));
    return set.size === 1 ? [...set][0] : "";
  };
  const current = (key, field) => {
    const e = state.edits[key];
    return e && field in e ? e[field] : original(key, field);
  };
  const setField = (key, field, value) => {
    saveError = null;
    if (field === "note") {
      const d = draft.read();
      if (value) d[key] = value; else delete d[key];
      draft.write(d);
    }
    const e = state.edits[key] || {};
    if (value === original(key, field)) delete e[field];
    else e[field] = value;
    if (Object.keys(e).length) state.edits[key] = e;
    else delete state.edits[key];
    if (state.ready) state.ready = null;   // changed after handing over
    rev++;
  };
  const editCount = () =>
    Object.keys(state.edits).length + state.queue.length + state.moves.length;

  /* Tile order is the site's curation, so a move is stored relative to a
     neighbour ("after this one"), never as an absolute index — an index would
     quietly mean something else after any other move. */
  const ordered = () => {
    const list = WORKS.slice();
    for (const mv of state.moves) {
      const i = list.findIndex(w => w.key === mv.key);
      if (i < 0) continue;
      const [w] = list.splice(i, 1);
      if (!mv.after) { list.unshift(w); continue; }
      const j = list.findIndex(x => x.key === mv.after);
      list.splice(j < 0 ? list.length : j + 1, 0, w);
    }
    return list;
  };
  const moveAfter = (key, after) => {
    state.moves = state.moves.filter(m => m.key !== key);
    state.moves.push({ key, after });
    if (state.ready) state.ready = null;
    rev++;
  };
  const isMoved = key => state.moves.some(m => m.key === key);

  /* Three questions per work, picked deterministically from a small bank so
     the same work always gets the same three (stable across renders/reloads)
     but neighbouring works don't read like the same form repeated. */
  const QUESTION_BANK = [
    [ "Что запомнилось в этой работе?",
      "Была тут какая-то деталь, о которой стоит рассказать?",
      "Чем эта работа отличалась от обычной?",
      "Что в ней было нестандартным?" ],
    [ "Что именно вы делали и какие решения принимали?",
      "Какой приём здесь сработал лучше всего?",
      "С чем пришлось повозиться дольше обычного?",
      "Что технически было интересного в этой работе?" ],
    [ "Кто ещё участвовал — музыканты, продюсер? Есть что о них рассказать?",
      "Как вы получили этот заказ или познакомились с артистом?",
      "Есть история, связанная с этой работой?",
      "Чем эта работа запомнилась лично вам?" ],
  ];
  const hash = s => { let h = 5381; for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0; return Math.abs(h); };
  const pickQuestions = key => {
    const h = hash(key);
    return QUESTION_BANK.map((pool, i) => pool[(h + i * 7) % pool.length]);
  };
  const qaBlock = key => {
    const answers = (current(key, "note") || "").split(/\n\n+/).map(s => s.trim());
    return pickQuestions(key).map((q, i) => `
      <div class="qa-item">
        <label class="qa-q">${esc(q)}</label>
        <textarea class="qa-a" data-qi="${i}" placeholder="Можно пропустить">${esc(answers[i] || "")}</textarea>
      </div>`).join("");
  };
  const collectQA = () => {
    const nodes = root.querySelectorAll(".qa-a");
    return [...nodes].map(t => t.value.trim()).filter(Boolean).join("\n\n");
  };

  /* The order every work is offered in: no text first (that's the point of
     the interview), then everyone else, so a short session covers the gaps. */
  const interviewQueue = () => {
    const list = [];
    for (const w of ordered()) {
      if (w.hidden || current(w.key, "hidden")) continue;
      if (w.kind === "track") list.push(w.key);
      else for (const t of w.tracks) list.push(t.key);
    }
    return list.sort((a, b) => !!current(a, "note") - !!current(b, "note"));
  };

  /* ── writing the page ───────────────────────────────────
     Rebuild the document from this page's own unchanging blocks — never
     from the live DOM, which would freeze the current view into the saved
     copy. Publishing reloads every open view, so this is only ever called
     when the owner has finished an edit, never while they type. */
  const documentSource = () => {
    const css = document.getElementById("app-css").textContent;
    const js = document.getElementById("app-js").textContent;
    const cat = document.getElementById("catalog").textContent;
    state.ts = Date.now();
    const st = JSON.stringify(state);
    const esc = s => s.replace(/<\/script/gi, "<\\/script");
    return `<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Песочница Credits</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Work+Sans:wght@400;500;600;800&display=swap">
<style id="app-css">${css}</style>
</head>
<body>
<div id="root"></div>

<script id="catalog" type="application/json">${esc(cat)}<\/script>
<script id="state" type="application/json">${esc(st)}<\/script>
<script id="app-js">${esc(js)}<\/script>
</body>
</html>
`;
  };

  async function save() {
    if (readOnly) return;
    if (rev === saved) return;
    // A publish in flight must not swallow edits made while it runs: remember
    // that one is waiting and run again, and only mark saved the snapshot that
    // was actually published.
    if (publishing) { again = true; return; }
    if (!window.claude) { return; }              // opened outside the viewer
    if (!artifact) { again = true; return; }     // capability still resolving
    publishing = true;
    const snapshot = rev;
    render();
    try {
      await artifact.publish(documentSource());
      saved = snapshot;                          // the view reloads to it
      draft.clear(Object.keys(state.edits).filter(k => state.edits[k].note));
    } catch (err) {
      if (err.code === "not_writer" || err.code === "not_granted" || err.code === "not_declared") {
        readOnly = true;
      } else if (err.code !== "conflict") {
        // alert() is unreliable inside the artifact frame, so the failure has
        // to be visible in the page itself — silence here is what made a lost
        // answer look like a working one.
        saveError = err.code || "ошибка сети";
        again = true;                            // try once more on its own
      }
    } finally {
      publishing = false;
      if (!saveError && rev === saved) saveError = null;
      render();
      if (again) { again = false; setTimeout(save, 1200); }
    }
  }

  // A save is a publish, and a publish reloads this very page. So it happens
  // at the end of an edit — never on input, or the page would reload mid-word.
  document.addEventListener("visibilitychange", () => { if (document.hidden) save(); });
  window.addEventListener("pagehide", save);

  /* ── render ─────────────────────────────────────────── */
  const saveBanner = () => {
    if (saveError) return `<div class="bar-warn">Не сохранилось на сервер (${esc(saveError)}). ` +
      `Ответы записаны в этом браузере и не потеряются — пробую ещё раз.</div>`;
    if (recovered) return `<div class="bar-ok">Восстановлено несохранённых ответов: ${recovered}. ` +
      `Нажмите «Дальше» или «Готово», чтобы отправить.</div>`;
    return "";
  };

  const esc = s => String(s ?? "").replace(/[&<>"]/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  const roleWord = r => CAT.roles[r] || "—";
  const isEdited = w => !!state.edits[w.key] ||
    (w.kind === "album" && w.tracks.some(t => state.edits[t.key]));

  function render() {
    if (state.interview) { root.innerHTML = viewInterview(); wireInterview(); return; }
    const n = editCount();
    root.innerHTML = `
      <header class="top">
        <div class="bar">
          <h1>Песочница <em>Credits</em></h1>
          <span class="who">${WORKS.length} работ · правки не уезжают сами</span>
        </div>
        <nav class="tabs" role="tablist">
          ${[["catalog", "Каталог", 0], ["add", "Добавить", state.queue.length],
             ["summary", "Сводка", n]].map(([id, label, badge]) => `
            <button role="tab" aria-selected="${tab === id}" data-tab="${id}">
              ${label}${badge ? `<span class="n">${badge}</span>` : ""}
            </button>`).join("")}
        </nav>
      </header>
      <main>${saveBanner()}${tab === "catalog" ? viewCatalog() : tab === "add" ? viewAdd() : viewSummary()}</main>
      ${open ? viewSheet(open) : ""}
      ${publishing ? '<div class="saving">Сохраняю…</div>' : ""}`;
    wire();
  }

  function viewInterview() {
    const { queue, i } = state.interview;
    if (i >= queue.length) {
      return `<div class="wiz-done">
        <h1>Готово</h1>
        <p>Прошли ${queue.length} ${plural(queue.length)}. Остальное можно дозаполнить
           в любой момент, открыв работу в каталоге.</p>
        <button class="btn-main" id="wiz-exit">К каталогу</button>
      </div>`;
    }
    const key = queue[i];
    const w = BY_KEY.get(key);
    return `
      <header class="wiz-top">
        <button class="wiz-x" id="wiz-exit" aria-label="Закрыть интервью">✕</button>
        <span class="wiz-progress">${i + 1} / ${queue.length}</span>
      </header>
      <main class="wiz-main" data-qa-for="${esc(key)}">
        ${saveBanner()}
        <div class="wiz-head">
          <img src="${(w.parent || w).thumb}" alt="">
          <div><h2>${esc(w.title)}</h2><p>${esc(w.parent ? w.parent.artist : w.artist)}</p></div>
        </div>
        ${qaBlock(key)}
      </main>
      <footer class="wiz-acts">
        <button class="btn-ghost" id="wiz-skip">Пропустить</button>
        <button class="btn-main" id="wiz-next">Дальше →</button>
      </footer>`;
  }
  const plural = n => { const m = n % 10, h = n % 100;
    return h >= 11 && h <= 14 ? "работ" : m === 1 ? "работу" : m >= 2 && m <= 4 ? "работы" : "работ"; };

  function wireInterview() {
    const commit = () => {
      const { queue, i } = state.interview;
      const key = queue[i];
      if (key && root.querySelector(`[data-qa-for="${key}"]`)) setField(key, "note", collectQA());
    };
    const exit = $("#wiz-exit");
    if (exit) exit.onclick = () => { commit(); state.interview = null; rev++; render(); save(); };
    const skip = $("#wiz-skip");
    if (skip) skip.onclick = () => { state.interview.i++; rev++; render(); save(); };
    const next = $("#wiz-next");
    if (next) next.onclick = () => { commit(); state.interview.i++; rev++; render(); save(); };
  }

  function viewCatalog() {
    const q = query.trim().toLowerCase();
    // Order mode shows the whole grid: a filtered view would hide the tile you
    // are about to drop next to, and the move would land somewhere unexpected.
    const list = sorting ? ordered() : ordered().filter(w =>
      (!genreF || w.genre === genreF) &&
      (!q || (w.artist + " " + w.title).toLowerCase().includes(q)));
    const takenName = picked ? BY_KEY.get(picked) : null;
    return `
      ${sorting ? `
        <div class="mode">
          <p>${takenName
            ? `Взяли <strong>${esc(takenName.title)}</strong>. Теперь нажмите ту работу, <em>после</em> которой её поставить.`
            : "Нажмите работу, которую надо передвинуть."}</p>
          <div class="mode-acts">
            ${takenName ? '<button class="btn-ghost" id="tofront">В начало сетки</button>' : ""}
            ${takenName ? '<button class="btn-ghost" id="cancelpick">Отменить выбор</button>' : ""}
            <button class="btn-ghost" id="sortoff">Готово</button>
          </div>
        </div>`
      : `<div class="find">
        <input type="search" id="q" placeholder="Артист или название" value="${esc(query)}">
        <select id="gf">
          <option value="">все жанры</option>
          ${CAT.genres.map(g => `<option value="${g}"${genreF === g ? " selected" : ""}>${g}</option>`).join("")}
        </select>
        <button class="btn-ghost" id="sorton" title="Изменить порядок">Порядок</button>
        <button class="btn-ghost" id="ivstart" title="Быстрое интервью по трекам">Интервью</button>
      </div>`}
      ${list.length ? `<div class="grid${sorting ? " sorting" : ""}">${list.map(tile).join("")}</div>`
                    : '<p class="empty">Ничего не нашлось</p>'}`;
  }

  const tile = w => `
    <button class="work${w.hidden || current(w.key, "hidden") ? " hid" : ""}${isEdited(w) || isMoved(w.key) ? " edited" : ""}${picked === w.key ? " picked" : ""}"
            ${sorting ? `data-pick="${esc(w.key)}"` : `data-open="${esc(w.key)}"`}>
      <img src="${w.thumb}" alt="" loading="lazy">
      <span class="art">${esc(w.artist)}</span>
      <span class="ttl">${esc(w.title)}</span>
      <span class="tags">
        <span class="tag">${esc(current(w.key, "genre"))}</span>
        ${w.kind === "album" ? `<span class="tag alb">${w.tracks.length} тр.</span>` : ""}
        ${current(w.key, "award") ? `<span class="tag">${esc(current(w.key, "award"))}</span>` : ""}
        ${current(w.key, "hidden") ? '<span class="tag">спрятан</span>' : ""}
      </span>
    </button>`;

  function viewSheet(key) {
    const w = BY_KEY.get(key);
    const inAlbum = !!w.parent;
    const chips = (field, opts, labels) => opts.map(o => `
      <button data-set="${field}" data-value="${esc(o)}"
              aria-pressed="${current(key, field) === o}">${esc(labels[o] ?? o ?? "—")}</button>`).join("");

    return `<div class="veil" data-close="1"><div class="sheet" role="dialog" aria-modal="true">
      <div class="head">
        <img src="${(w.parent || w).thumb}" alt="">
        <div>
          <h2>${esc(w.title)}</h2>
          <p>${esc(inAlbum ? w.parent.artist + " · " + w.parent.title : w.artist)}</p>
        </div>
      </div>

      <div class="field">
        <span class="lbl">Что мы делали</span>
        <div class="opts">${chips("role", Object.keys(CAT.roles), CAT.roles)}</div>
        ${w.kind === "album" && !inAlbum
          ? `<p class="hint">Ставится всем ${w.tracks.length} трекам альбома. Отдельный трек — в списке ниже.</p>`
          : `<p class="hint">От этого зависит заголовок страницы трека в поиске: «кто свёл» или «кто мастерил».</p>`}
      </div>

      ${inAlbum || w.kind === "track" ? "" : `
      <div class="field">
        <span class="lbl">Треки альбома</span>
        <div class="alb-list">${w.tracks.map(t => `
          <button data-open="${esc(t.key)}">
            <span>${esc(t.title)}${state.edits[t.key] ? " •" : ""}</span>
            <span class="r">${esc(roleWord(current(t.key, "role")))}</span>
          </button>`).join("")}</div>
        <p class="hint">Описание и роль у каждого трека — свои.</p>
      </div>`}

      ${inAlbum ? "" : `
      <div class="field">
        <span class="lbl">Жанр</span>
        <div class="opts">${chips("genre", CAT.genres, {})}</div>
      </div>

      <div class="field">
        <span class="lbl">Награда</span>
        <div class="opts">${chips("award", ["", ...Object.keys(CAT.awards)], { "": "нет", ...CAT.awards })}</div>
      </div>`}

      ${w.kind === "album" && !inAlbum ? "" : `
      <div class="field qa" data-qa-for="${esc(key)}">
        <span class="lbl">Своими словами</span>
        <p class="hint">Ответьте на то, что откликается, — остальное пропустите. Появится на странице
           трека под заголовком, это то, что читают люди и поисковик.</p>
        ${qaBlock(key)}
      </div>`}

      ${inAlbum ? "" : `
      <div class="field">
        <span class="lbl">Показ на сайте</span>
        <div class="opts">
          <button data-set="hidden" data-value="false" aria-pressed="${!current(key, "hidden")}">на сайте</button>
          <button data-set="hidden" data-value="true" aria-pressed="${!!current(key, "hidden")}">спрятать</button>
        </div>
        ${current(key, "hidden")
          ? '<p class="hint">Плитка уйдёт с сетки, страница трека будет удалена. Вернуть можно отсюда же.</p>' : ""}
      </div>`}

      <div class="acts">
        ${inAlbum ? `<button class="btn-ghost" data-open="${esc(w.parent.key)}">← к альбому</button>` : ""}
        <button class="btn-main" data-done="1">Готово</button>
      </div>
    </div></div>`;
  }

  function viewAdd() {
    return `
      <form class="form" id="addf">
        <div class="field">
          <span class="lbl">Ссылка на Spotify</span>
          <input type="url" name="url" required placeholder="https://open.spotify.com/track/…">
          <p class="hint">Трек, альбом или плейлист. Обложку, год и артистов подтянем сами.</p>
        </div>
        <div class="field">
          <span class="lbl">Что мы делали</span>
          <div class="opts" data-radio="role">
            ${Object.entries(CAT.roles).map(([k, v], i) =>
              `<button type="button" data-value="${k}" aria-pressed="${i === 0}">${v}</button>`).join("")}
          </div>
        </div>
        <div class="field">
          <span class="lbl">Жанр</span>
          <div class="opts" data-radio="genre">
            <button type="button" data-value="" aria-pressed="true">определим сами</button>
            ${CAT.genres.map(g => `<button type="button" data-value="${g}" aria-pressed="false">${g}</button>`).join("")}
          </div>
        </div>
        <div class="field">
          <span class="lbl">Заметка</span>
          <textarea name="note" placeholder="Необязательно"></textarea>
        </div>
        <div class="acts"><button class="btn-main" type="submit">В очередь</button></div>
      </form>
      ${state.queue.length ? `<div class="rows">${state.queue.map((q, i) => `
        <div class="row">
          <span class="who">${esc(q.url)}
            <small>${esc(roleWord(q.role))}${q.genre ? " · " + esc(q.genre) : ""}</small></span>
          ${q.note ? `<span class="hint">${esc(q.note)}</span>` : ""}
          <button class="drop" data-drop-q="${i}">убрать из очереди</button>
        </div>`).join("")}</div>` : ""}`;
  }

  function viewSummary() {
    const keys = Object.keys(state.edits);
    if (!keys.length && !state.queue.length && !state.moves.length)
      return '<p class="empty">Пока ничего не поправлено.<br>Откройте работу в каталоге.</p>';

    const label = { role: "Что делали", genre: "Жанр", award: "Награда",
                    note: "Описание", hidden: "Показ на сайте" };
    const show = (field, v) =>
      field === "role" ? roleWord(v)
      : field === "hidden" ? (v ? "спрятан" : "на сайте")
      : field === "award" ? (v ? CAT.awards[v] : "нет")
      : field === "note" ? (v ? (v.length > 90 ? v.slice(0, 90) + "…" : v) : "пусто")
      : (v || "—");

    const rows = keys.map(key => {
      const w = BY_KEY.get(key);
      const title = w.parent ? `${w.parent.artist} — ${w.parent.title}` : `${w.artist} — ${w.title}`;
      return `<div class="row">
        <span class="who">${esc(title)}${w.parent ? `<small>трек «${esc(w.title)}»</small>` : ""}</span>
        <ul>${Object.entries(state.edits[key]).map(([f, v]) => `
          <li><span class="lbl">${label[f]}</span>
              <span class="was">${esc(show(f, original(key, f)))}</span>
              <span class="now">${esc(show(f, v))}</span></li>`).join("")}</ul>
        <button class="drop" data-drop="${esc(key)}">отменить эти правки</button>
      </div>`;
    }).join("");

    const moved = state.moves.length ? `<div class="rows">${state.moves.map(mv => {
      const w = BY_KEY.get(mv.key), a = mv.after ? BY_KEY.get(mv.after) : null;
      if (!w) return "";
      return `<div class="row">
        <span class="who">${esc(w.artist)} — ${esc(w.title)}<small>порядок на сетке</small></span>
        <ul><li><span class="lbl">Встанет</span>
          <span class="now">${a ? "после «" + esc(a.artist + " — " + a.title) + "»" : "в начало сетки"}</span></li></ul>
        <button class="drop" data-drop-m="${esc(mv.key)}">вернуть на место</button>
      </div>`;
    }).join("")}</div>` : "";

    const queued = state.queue.length
      ? `<div class="row"><span class="who">Новых работ в очереди: ${state.queue.length}</span>
         <ul>${state.queue.map(q => `<li>${esc(q.url)}</li>`).join("")}</ul></div>` : "";

    return `${rows}${moved}${queued ? `<div class="rows">${queued}</div>` : ""}
      ${state.ready ? `<div class="ready">
          <p><strong>Отдано в работу</strong> ${esc(new Date(state.ready).toLocaleString("ru-RU"))}.
             Правки применятся и уедут на сайт — это занимает несколько минут.</p>
          <p class="hint">Ничего не произошло за полчаса? Значит сессия Claude была закрыта и
             уведомление никто не увидел — напишите ему обычным сообщением: «песочница credits
             отдана в работу». Правки никуда не денутся, они лежат здесь.</p>
          <p class="hint">Если поправите ещё что-то — отметка снимется, нажмите кнопку снова.</p>
        </div>`
        : `<div class="ready">
          <p>Правки лежат здесь и на сайт сами не уедут. Нажмите, когда закончите — одной кнопкой на всю пачку.</p>
          <div class="acts"><button class="btn-main" id="handoff">Отдать в работу</button></div>
        </div>`}
      ${readOnly ? '<p class="note">Эта копия открыта только на чтение — правки не сохранятся. Откройте песочницу по своей ссылке.</p>' : ""}`;
  }

  /* ── events ────────────────────────────────────────── */
  function wire() {
    root.querySelectorAll("[data-tab]").forEach(b =>
      b.onclick = () => { tab = b.dataset.tab; render(); });

    const q = $("#q"); if (q) { q.oninput = () => { query = q.value; renderKeepFocus(q); }; }
    const gf = $("#gf"); if (gf) gf.onchange = () => { genreF = gf.value; render(); };

    root.querySelectorAll("[data-open]").forEach(b =>
      b.onclick = e => { e.stopPropagation(); open = b.dataset.open; render(); });

    root.querySelectorAll("[data-pick]").forEach(b => b.onclick = () => {
      const key = b.dataset.pick;
      if (!picked) { picked = key; render(); return; }
      if (picked === key) { picked = null; render(); return; }
      moveAfter(picked, key);
      picked = null;
      render(); save();
    });
    const on = $("#sorton"); if (on) on.onclick = () => { sorting = true; picked = null; render(); };
    const iv = $("#ivstart"); if (iv) iv.onclick = () => {
      state.interview = { queue: interviewQueue(), i: 0 }; render();
    };
    const off = $("#sortoff"); if (off) off.onclick = () => { sorting = false; picked = null; render(); };
    const cancel = $("#cancelpick"); if (cancel) cancel.onclick = () => { picked = null; render(); };
    const front = $("#tofront"); if (front) front.onclick = () => {
      moveAfter(picked, ""); picked = null; render(); save();
    };
    root.querySelectorAll("[data-drop-m]").forEach(b => b.onclick = () => {
      state.moves = state.moves.filter(m => m.key !== b.dataset.dropM);
      state.ready = null; rev++; render(); save();
    });

    root.querySelectorAll("[data-set]").forEach(b => b.onclick = () => {
      const v = b.dataset.value;
      setField(open, b.dataset.set, v === "true" ? true : v === "false" ? false : v);
      render();
    });

    const veil = $(".veil");
    if (veil) veil.onclick = e => { if (e.target === veil) closeSheet(); };
    const done = $("[data-done]"); if (done) done.onclick = closeSheet;

    root.querySelectorAll("[data-drop]").forEach(b => b.onclick = () => {
      delete state.edits[b.dataset.drop]; state.ready = null; rev++; render(); save();
    });
    root.querySelectorAll("[data-drop-q]").forEach(b => b.onclick = () => {
      state.queue.splice(+b.dataset.dropQ, 1); state.ready = null; rev++; render(); save();
    });

    root.querySelectorAll("[data-radio]").forEach(group =>
      group.querySelectorAll("button").forEach(b => b.onclick = () => {
        group.querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", x === b));
      }));

    const form = $("#addf");
    if (form) form.onsubmit = e => {
      e.preventDefault();
      const pick = name => {
        const g = form.querySelector(`[data-radio="${name}"] [aria-pressed="true"]`);
        return g ? g.dataset.value : "";
      };
      state.queue.push({
        url: form.url.value.trim(), role: pick("role") || "mix",
        genre: pick("genre"), note: form.note.value.trim(),
      });
      state.ready = null; rev++;
      render(); save();
    };

    const h = $("#handoff");
    if (h) h.onclick = () => {
      state.ready = new Date().toISOString();
      rev++; render(); save();
    };
  }

  // The note textarea is read on close, not on input: publishing reloads the
  // page, and a reload mid-sentence is how the first version lost text.
  function closeSheet() {
    if (root.querySelector(`[data-qa-for="${open}"]`)) setField(open, "note", collectQA());
    open = null;
    render();
    save();
  }

  function renderKeepFocus(input) {
    const pos = input.selectionStart;
    render();
    const next = $("#q");
    if (next) { next.focus(); next.setSelectionRange(pos, pos); }
  }

  document.addEventListener("keydown", e => { if (e.key === "Escape" && open) closeSheet(); });
  render();
})();
