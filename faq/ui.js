/* Progressive enhancement: every answer remains in HTML without JavaScript. */
(() => {
  const root = document.querySelector('.faq-page');
  if (!root) return;
  const details = [...root.querySelectorAll('.flow details')];
  const heads = [...root.querySelectorAll('.flow h2')];
  const input = root.querySelector('#faq-search');
  const status = root.querySelector('.faq-status');
  const empty = root.querySelector('.faq-empty');
  const expand = root.querySelector('#faq-expand');
  const normalize = s => s.toLocaleLowerCase().normalize('NFKC').replace(/ё/g, 'е');
  const index = details.map(node => ({node, text:normalize(node.textContent)}));
  let saved = null;
  function filter() {
    const words = normalize(input.value).trim().split(/\s+/).filter(Boolean);
    if (words.length && !saved) saved = new Map(details.map(d => [d,d.open]));
    let count = 0;
    index.forEach(({node,text}) => {
      node.hidden = !words.every(w => text.includes(w));
      if (!node.hidden) count++;
      if (words.length) node.open = !node.hidden;
      else if (saved) node.open = saved.get(node);
    });
    if (!words.length) saved = null;
    heads.forEach(h => {
      let next = h.nextElementSibling, visible = false;
      while (next && next.tagName !== 'H2') {
        if (next.tagName === 'DETAILS' && !next.hidden) visible = true;
        next = next.nextElementSibling;
      }
      h.hidden = !visible;
    });
    status.textContent = words.length ? `${count} / ${details.length}` : '';
    empty.hidden = count > 0;
    sync();
  }
  function sync() {expand.setAttribute('aria-pressed', String(details.filter(d=>!d.hidden).every(d=>d.open)));}
  expand.addEventListener('click', () => {
    const open = expand.getAttribute('aria-pressed') !== 'true';
    details.filter(d=>!d.hidden).forEach(d => {d.open = open;}); sync();
  });
  input.addEventListener('input',filter);
  root.querySelector('#faq-reset').addEventListener('click',()=>{input.value='';filter();input.focus();});
  root.querySelectorAll('.toc a').forEach(a=>a.addEventListener('click',()=>{input.value='';filter();}));
  function revealHash() {
    let id; try {id=decodeURIComponent(location.hash.slice(1));} catch {return;}
    const node = document.getElementById(id);
    if (node && node.tagName === 'DETAILS') {
      input.value='';filter();node.open=true;
      requestAnimationFrame(()=>node.scrollIntoView({block:'start'}));
    }
  }
  window.addEventListener('hashchange',revealHash);
  details.forEach(d=>d.addEventListener('toggle',sync));
  root.querySelector('.faq-tools').hidden = false;
  revealHash();sync();
})();
