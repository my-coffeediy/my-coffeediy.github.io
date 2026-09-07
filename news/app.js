const state = { data: null, briefMap: new Map(), briefSeq: 0 };
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];

function fmtDate(iso) {
  const d = new Date(iso);
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit',
    hour12: false, timeZone: 'Asia/Shanghai'
  }).format(d);
}

function esc(s = '') {
  return String(s).replace(/[&<>"']/g, (m) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
  }[m]));
}

function safeUrl(u = '') {
  try {
    const x = new URL(u, location.href);
    return /^https?:$/.test(x.protocol) ? x.href : '';
  } catch { return ''; }
}

function registerBrief(item) {
  const id = `brief-${++state.briefSeq}`;
  state.briefMap.set(id, item);
  return id;
}

function quickSummary(n) {
  if (n.quick_summary) return n.quick_summary;
  if (n.summary) return n.summary;
  return `${n.source || '新闻来源'}报道了“${n.title || '这条新闻'}”。当前聚合源暂未提供足够正文信息，快速概要只展示已确认内容，不补写未经来源支持的细节。`;
}

function quickPoints(n) {
  if (Array.isArray(n.key_points) && n.key_points.length) return n.key_points;
  return [
    `核心事件：${n.title || '来源发布了新的进展。'}`,
    '当前可确认信息以新闻来源已经公开的标题、摘要和正文信息为准。',
    '如需全部原始细节，可继续查看原报道及权威来源后续更新。'
  ];
}

function ensureBriefModal() {
  if ($('#briefModal')) return;
  const wrap = document.createElement('div');
  wrap.id = 'briefModal';
  wrap.className = 'brief-modal';
  wrap.setAttribute('aria-hidden', 'true');
  wrap.innerHTML = `
    <div class="brief-backdrop" data-close-brief></div>
    <section class="brief-sheet" role="dialog" aria-modal="true" aria-labelledby="briefModalTitle">
      <div class="brief-sheet-handle"></div>
      <div class="brief-sheet-head">
        <div><div class="eyebrow">QUICK BRIEF</div><h3 id="briefModalTitle"></h3></div>
        <button class="brief-close" type="button" data-close-brief aria-label="关闭">×</button>
      </div>
      <div class="brief-sheet-meta" id="briefModalMeta"></div>
      <div class="brief-block">
        <div class="brief-block-label">详细概要</div>
        <div class="brief-copy" id="briefModalSummary"></div>
      </div>
      <div class="brief-block">
        <div class="brief-block-label">重点信息</div>
        <ul class="brief-points" id="briefModalPoints"></ul>
      </div>
      <div class="brief-sheet-actions" id="briefModalActions"></div>
      <div class="brief-note">快速概要会尽量覆盖事件背景、关键事实、数字/时间、主要进展和后续关注点；若来源未开放足够正文，则只整理已经确认的信息。</div>
    </section>`;
  document.body.appendChild(wrap);
}

function openBriefModal(n) {
  ensureBriefModal();
  const modal = $('#briefModal');
  $('#briefModalTitle').textContent = n.title || '新闻概要';
  $('#briefModalMeta').textContent = `${n.category || '新闻'} · ${n.source || '来源未知'}${n.published_at ? ' · ' + fmtDate(n.published_at) : ''}`;
  $('#briefModalSummary').textContent = quickSummary(n);
  $('#briefModalPoints').innerHTML = quickPoints(n).slice(0, 5).map((p) => `<li>${esc(p)}</li>`).join('');
  const url = safeUrl(n.url || '');
  $('#briefModalActions').innerHTML = url
    ? `<a class="brief-source-link" href="${esc(url)}" target="_blank" rel="noopener">查看完整原报道 ↗</a>`
    : '<span class="brief-source-disabled">暂无可用原文链接</span>';
  modal.classList.add('open');
  modal.setAttribute('aria-hidden', 'false');
  document.body.classList.add('modal-open');
}

function closeBriefModal() {
  const modal = $('#briefModal');
  if (!modal) return;
  modal.classList.remove('open');
  modal.setAttribute('aria-hidden', 'true');
  document.body.classList.remove('modal-open');
}

function bindImgErrors() {
  document.querySelectorAll('.js-news-img').forEach((img) => {
    img.addEventListener('error', () => {
      const wrap = img.closest('.news-thumb');
      if (wrap) wrap.classList.add('img-failed');
      img.remove();
    }, { once: true });
  });
  const hero = $('.js-hero-img');
  if (hero) hero.addEventListener('error', () => hero.remove(), { once: true });
}

function newsCard(n) {
  const img = safeUrl(n.image_url || '');
  const briefId = registerBrief(n);
  const trust = n.verified
    ? '<span class="badge verified">权威来源</span>'
    : '<span class="badge caution">待交叉核实</span>';
  const badges = [
    n.hot ? '<span class="badge hot">热点</span>' : '',
    trust,
    `<span class="badge">${esc(n.category || '新闻')}</span>`
  ].join('');

  return `<article class="news-card ${img ? '' : 'no-image'}">
    <div class="news-body">
      <div class="news-top">${badges}</div>
      <div class="news-title">${esc(n.title)}</div>
      ${n.summary ? `<div class="news-summary">${esc(n.summary)}</div>` : ''}
      <div class="news-meta"><span>${esc(n.source || '来源未知')} · ${fmtDate(n.published_at)}</span>${n.url ? `<a href="${esc(n.url)}" target="_blank" rel="noopener">来源 ↗</a>` : ''}</div>
      <button class="brief-btn" type="button" data-brief-id="${briefId}"><span class="brief-btn-icon">≡</span> 快速概要</button>
    </div>
    ${img ? `<div class="news-thumb"><img class="js-news-img" src="${esc(img)}" alt="" loading="lazy" referrerpolicy="no-referrer"></div>` : ''}
  </article>`;
}

function renderList(id, arr) {
  $(id).innerHTML = (arr || []).map(newsCard).join('') || '<div class="empty-card">暂无数据</div>';
}

function heroCard(x) {
  if (!x) return '<div class="empty-card">暂无头条</div>';
  const img = safeUrl(x.image_url || '');
  const briefId = registerBrief(x);
  return `<article class="hero-card">
    <div class="hero-media">${img ? `<img class="js-hero-img" src="${esc(img)}" alt="" referrerpolicy="no-referrer">` : '<div class="hero-fallback"></div>'}</div>
    <div class="hero-content">
      <div class="hero-kicker"><span class="badge hot">今日头条</span>${x.category ? `<span class="badge">${esc(x.category)}</span>` : ''}</div>
      <div class="hero-title">${esc(x.title)}</div>
      ${x.summary ? `<div class="hero-summary"><span>摘要</span>${esc(x.summary)}</div>` : ''}
      <div class="top-actions">
        <button class="brief-btn compact" type="button" data-brief-id="${briefId}">快速概要</button>
        ${x.url ? `<a class="detail-link" href="${esc(x.url)}" target="_blank" rel="noopener">查看原报道 ↗</a>` : ''}
      </div>
      <div class="hero-meta"><span>${esc(x.source || '重点新闻')}${x.published_at ? ' · ' + fmtDate(x.published_at) : ''}</span></div>
    </div>
  </article>`;
}

function top5Card(x, i) {
  const url = safeUrl(x.url || '');
  const briefId = registerBrief(x);
  return `<article class="top-item">
    <div class="top-num">${i + 1}</div>
    <div>
      <div class="top-title">${esc(x.title)}</div>
      ${x.summary ? `<div class="top-summary"><span>摘要</span>${esc(x.summary)}</div>` : ''}
      <div class="top-actions">
        <button class="brief-btn compact" type="button" data-brief-id="${briefId}">快速概要</button>
        ${url ? `<a class="detail-link" href="${esc(url)}" target="_blank" rel="noopener">查看详细报道 ↗</a>` : ''}
      </div>
    </div>
  </article>`;
}

function marketMini(m) {
  const cls = m.change_pct > 0 ? 'up' : m.change_pct < 0 ? 'down' : 'flat';
  const arrow = m.change_pct > 0 ? '▲' : m.change_pct < 0 ? '▼' : '•';
  return `<div class="market-mini"><div class="market-name">${esc(m.name)}</div><div class="market-price">${esc(m.price)} ${esc(m.unit || '')}</div><div class="market-change ${cls}">${arrow} ${Math.abs(m.change_pct || 0).toFixed(2)}%</div></div>`;
}

function marketCard(m) {
  const cls = m.change_pct > 0 ? 'up' : m.change_pct < 0 ? 'down' : 'flat';
  const arrow = m.change_pct > 0 ? '▲' : m.change_pct < 0 ? '▼' : '•';
  return `<div class="market-card"><div class="name">${esc(m.name)}</div><div class="price">${esc(m.price)} <small>${esc(m.unit || '')}</small></div><div class="change ${cls}">${arrow} ${(m.change_pct || 0).toFixed(2)}%</div><div class="sub">${esc(m.symbol || '')} · ${esc(m.note || '延迟行情')}</div></div>`;
}

function render(data) {
  state.data = data;
  state.briefMap = new Map();
  state.briefSeq = 0;
  $('#updatedAt').textContent = `最近更新：${fmtDate(data.updated_at)}（北京时间）`;
  $('#marketTime').textContent = `更新 ${fmtDate(data.markets_updated_at || data.updated_at)}`;

  const top = data.top5 || [];
  $('#heroStory').innerHTML = heroCard(top[0]);
  $('#top5').innerHTML = top.slice(0, 5).map(top5Card).join('');
  renderList('#chinaPreview', (data.sections.china || []).slice(0, 4));
  renderList('#worldPreview', (data.sections.world || []).slice(0, 4));
  renderList('#aiPreview', (data.sections.ai || []).slice(0, 4));
  for (const key of ['china', 'world', 'finance', 'tech', 'society', 'ai']) renderList(`#${key}List`, data.sections[key] || []);
  $('#marketStrip').innerHTML = (data.markets || []).slice(0, 6).map(marketMini).join('');
  $('#marketsGrid').innerHTML = (data.markets || []).map(marketCard).join('');
  bindImgErrors();
}

async function load() {
  $('#updatedAt').textContent = '正在读取最新数据…';
  try {
    const r = await fetch(`./data/news.json?t=${Date.now()}`);
    if (!r.ok) throw new Error('读取失败');
    render(await r.json());
  } catch (e) {
    $('#updatedAt').textContent = '数据读取失败，请稍后刷新';
  }
}

document.addEventListener('click', (e) => {
  const brief = e.target.closest('[data-brief-id]');
  if (brief) {
    e.preventDefault();
    e.stopPropagation();
    const item = state.briefMap.get(brief.dataset.briefId);
    if (item) openBriefModal(item);
    return;
  }
  if (e.target.closest('[data-close-brief]')) closeBriefModal();
});

document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeBriefModal(); });

$$('.tab').forEach((btn) => btn.addEventListener('click', () => {
  $$('.tab').forEach((x) => x.classList.remove('active'));
  $$('.tab-panel').forEach((x) => x.classList.remove('active'));
  btn.classList.add('active');
  document.querySelector(`[data-panel="${btn.dataset.tab}"]`).classList.add('active');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}));

$('#refreshBtn').addEventListener('click', load);
const now = new Date();
$('#todayDate').textContent = new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric', month: 'long', day: 'numeric', weekday: 'long', timeZone: 'Asia/Shanghai'
}).format(now);

ensureBriefModal();
load();
