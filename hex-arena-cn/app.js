const DATA_ROOT = new URL("./data/", import.meta.url);

const roleLabels = {
  fighter: "战士",
  mage: "法师",
  assassin: "刺客",
  tank: "坦克",
  marksman: "射手",
  support: "辅助",
};

const qualityMeta = {
  1: { label: "白银", className: "quality-silver" },
  2: { label: "黄金", className: "quality-gold" },
  3: { label: "棱彩", className: "quality-prismatic" },
};

const sortLabels = { winRate: "胜率", pickRate: "选取率", totalMatches: "场次" };
const state = {
  surface: "champions",
  champions: [],
  augments: [],
  items: null,
  manifest: null,
  query: "",
  role: "all",
  sortKey: "winRate",
  quality: 1,
  detailQuality: 1,
  selected: null,
  detail: null,
};

const content = document.querySelector("#content");
const search = document.querySelector("#search");
const sort = document.querySelector("#sort");
const overlay = document.querySelector("#overlay");
const detailContent = document.querySelector("#detail-content");
const compactNumber = new Intl.NumberFormat("zh-CN", { notation: "compact", maximumFractionDigits: 1 });

function escapeHTML(value = "") {
  return String(value).replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[char]);
}

function plainText(value = "") {
  const doc = new DOMParser().parseFromString(String(value).replace(/<br\s*\/?\s*>/gi, " "), "text/html");
  return (doc.body.textContent || "").replace(/%i:[^%]+%/g, "").replace(/\s+/g, " ").trim();
}

function percent(value) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`;
}

function asset(path = "") {
  if (!path) return "";
  if (/^https?:\/\//.test(path)) return path;
  return new URL(path.replace(/^\//, ""), state.manifest?.assetBase || DATA_ROOT).href;
}

function tierBadge(tier = "T4") {
  return `<span class="tier-badge tier-${escapeHTML(tier.toLowerCase())}">${escapeHTML(tier)}</span>`;
}

function winRate(value) {
  const tone = value >= 0.52 ? "positive" : value < 0.48 ? "negative" : "";
  return `<span class="win-rate ${tone}"><span aria-hidden="true">↗</span>${percent(value)}</span>`;
}

function metric(label, value, accent = false) {
  return `<span class="metric"><small>${label}</small><b class="${accent ? "metric-accent" : ""}">${value}</b></span>`;
}

function itemIcon(id, item = {}) {
  const name = item.name || `装备 ${id}`;
  const icon = item.icon || item.iconPath || `/assets/game/item-icons/${id}.png`;
  return `<span class="item-icon-wrap" title="${escapeHTML(name)}"><img src="${escapeHTML(asset(icon))}" alt="${escapeHTML(name)}" loading="lazy"></span>`;
}

function pickRateOf(champion) {
  if (typeof champion.pickRate === "number") return champion.pickRate;
  const totalGames = Math.max(1, state.champions.reduce((sum, item) => sum + item.totalMatches, 0) / 10);
  return champion.totalMatches / totalGames;
}

function sortBy(items, key, pickRate) {
  return [...items].sort((a, b) => {
    const left = key === "pickRate" && pickRate ? pickRate(a) : Number(a[key] || 0);
    const right = key === "pickRate" && pickRate ? pickRate(b) : Number(b[key] || 0);
    return right - left;
  });
}

function renderFilters() {
  const entries = [["all", "全部"], ...Object.entries(roleLabels)];
  return `<div class="filter-scroll" aria-label="英雄分类">${entries.map(([key, label]) => (
    `<button data-role="${key}" class="${state.role === key ? "active" : ""}">${label}</button>`
  )).join("")}</div>`;
}

function filteredChampions() {
  const keyword = state.query.trim().toLowerCase();
  const results = state.champions.filter((champion) => {
    const roleMatch = state.role === "all" || champion.roles.includes(state.role);
    const text = `${champion.title} ${champion.name} ${champion.alias}`.toLowerCase();
    return roleMatch && (!keyword || text.includes(keyword));
  });
  return sortBy(results, state.sortKey, pickRateOf);
}

function renderChampions() {
  const champions = filteredChampions();
  const rows = champions.map((champion, index) => `
    <tr data-champion="${champion.id}" tabindex="0">
      <td class="rank-col">${index + 1}</td>
      <td><span class="champion-name-cell"><img src="${escapeHTML(asset(champion.iconPath))}" alt="" loading="lazy"><span><b>${escapeHTML(champion.title)}</b><small>${escapeHTML(champion.name)}</small></span></span></td>
      <td><span class="role-list">${champion.roles.map((role) => `<i>${roleLabels[role] || role}</i>`).join("")}</span></td>
      <td>${tierBadge(champion.tier)}</td>
      <td>${winRate(champion.winRate)}</td>
      <td>${percent(pickRateOf(champion))}</td>
      <td>${compactNumber.format(champion.totalMatches)}</td>
      <td class="row-arrow">›</td>
    </tr>`).join("");

  const cards = champions.map((champion, index) => `
    <button class="champion-card" data-champion="${champion.id}">
      <span class="mobile-rank">${index + 1}</span>
      <img class="champion-avatar" src="${escapeHTML(asset(champion.iconPath))}" alt="" loading="lazy">
      <span class="champion-card-main"><span class="champion-card-title"><b>${escapeHTML(champion.title)}</b>${tierBadge(champion.tier)}</span><small>${champion.roles.map((role) => roleLabels[role] || role).join(" · ")} · ${compactNumber.format(champion.totalMatches)} 场</small></span>
      <span class="champion-card-metrics"><b>${percent(champion.winRate)}</b><small>选取 ${percent(pickRateOf(champion))}</small></span>
      <span class="row-arrow">›</span>
    </button>`).join("");

  content.innerHTML = `
    ${renderFilters()}
    <div class="result-meta"><span>共 ${champions.length} 位英雄</span><span>点击英雄查看出装与海克斯</span></div>
    ${champions.length ? `
      <section class="desktop-table"><table><thead><tr><th class="rank-col">排名</th><th>英雄</th><th>分类</th><th>强度</th><th>胜率</th><th>选取率</th><th>场次</th><th><span class="sr-only">查看</span></th></tr></thead><tbody>${rows}</tbody></table></section>
      <section class="mobile-list">${cards}</section>` : `<div class="empty-state">没有找到符合条件的英雄</div>`}
  `;
}

function qualityTabs(context, quality) {
  return `<div class="quality-tabs ${context === "detail" ? "compact" : ""}" aria-label="海克斯阶级">${[1, 2, 3].map((value) => {
    const count = context === "global" ? state.augments.filter((item) => item.quality === value).length : "";
    return `<button data-quality="${value}" data-quality-context="${context}" class="${qualityMeta[value].className} ${quality === value ? "active" : ""}"><span class="quality-gem"></span>${qualityMeta[value].label}${context === "global" ? `阶<small>${count}</small>` : ""}</button>`;
  }).join("")}</div>`;
}

function filteredAugments() {
  const keyword = state.query.trim().toLowerCase();
  return sortBy(state.augments.filter((augment) => {
    const text = `${augment.name} ${plainText(augment.description)}`.toLowerCase();
    return augment.quality === state.quality && (!keyword || text.includes(keyword));
  }), state.sortKey);
}

function renderAugments() {
  const augments = filteredAugments();
  const meta = qualityMeta[state.quality];
  content.innerHTML = `
    ${qualityTabs("global", state.quality)}
    <div class="result-meta"><span>${meta.label}阶海克斯 · ${augments.length} 个</span><span>当前按${sortLabels[state.sortKey]}排序</span></div>
    ${augments.length ? `<section class="augment-grid">${augments.map((augment, index) => `
      <article class="augment-card ${meta.className}">
        <span class="augment-rank">#${index + 1}</span>
        <img src="${escapeHTML(asset(augment.iconPath))}" alt="" loading="lazy">
        <div class="augment-copy"><h2>${escapeHTML(augment.name)}</h2><p>${escapeHTML(plainText(augment.description) || "暂无效果说明")}</p><div class="augment-metrics">${metric("胜率", percent(augment.winRate), true)}${metric("选取", percent(augment.pickRate))}${metric("场次", compactNumber.format(augment.totalMatches))}</div></div>
      </article>`).join("")}</section>` : `<div class="empty-state">没有找到符合条件的海克斯</div>`}
  `;
}

function render() {
  if (state.surface === "champions") renderChampions();
  else renderAugments();
}

async function loadJSON(path) {
  const response = await fetch(new URL(path, DATA_ROOT), { cache: "no-cache" });
  if (!response.ok) throw new Error(`数据加载失败（${response.status}）`);
  return response.json();
}

async function openChampion(id) {
  const champion = state.champions.find((item) => item.id === Number(id));
  if (!champion) return;
  state.selected = champion;
  state.detail = null;
  state.detailQuality = 1;
  overlay.hidden = false;
  document.body.classList.add("no-scroll");
  detailContent.innerHTML = renderDetailHeader(champion) + `<div class="detail-loading"><span class="spinner"></span><p>正在读取出装与海克斯数据…</p></div>`;

  try {
    const [detail, items] = await Promise.all([
      loadJSON(`details/${champion.id}.json`),
      state.items ? Promise.resolve(state.items) : loadJSON("items.json"),
    ]);
    state.items = items;
    state.detail = detail;
    renderDetail();
  } catch (error) {
    detailContent.innerHTML = renderDetailHeader(champion) + `<div class="empty-state">${escapeHTML(error.message || "英雄详情暂时无法加载")}</div>`;
  }
}

function renderDetailHeader(champion) {
  return `<header class="detail-header">
    <div class="detail-hero"><img src="${escapeHTML(asset(champion.iconPath))}" alt=""><div><span class="eyebrow">${escapeHTML(champion.name)}</span><h2 id="detail-title">${escapeHTML(champion.title)}</h2><p>${champion.roles.map((role) => roleLabels[role] || role).join(" · ")}</p></div>${tierBadge(champion.tier)}</div>
    <div class="detail-stats">${metric("英雄胜率", percent(champion.winRate), true)}${metric("选取率", percent(pickRateOf(champion)))}${metric("样本场次", compactNumber.format(champion.totalMatches))}</div>
  </header>`;
}

function renderBuildRow(build) {
  return `<div class="build-row"><span class="build-rank">${build.rank}</span><div class="build-items">${build.value.map((item) => itemIcon(item.id, item)).join("")}</div><span class="build-stat"><small>胜率</small><b>${percent(build.winRate)}</b></span><span class="build-stat"><small>选取</small><b>${percent(build.pickRate)}</b></span></div>`;
}

function renderPaths(detail) {
  return [2, 3, 4].map((size) => {
    const combo = detail.itemAnalysis?.combos?.[String(size)]?.[0];
    if (!combo) return "";
    const icons = combo.items.map((id, index) => `<span class="path-item">${index ? `<span class="path-arrow">›</span>` : ""}${itemIcon(id, state.items?.[String(id)] || {})}</span>`).join("");
    return `<div class="path-row"><span class="path-label">${size}件套</span><div class="build-items with-arrows">${icons}</div><span class="build-stat"><small>胜率</small><b>${percent(combo.winRate)}</b></span></div>`;
  }).join("");
}

function renderRecommendations(detail) {
  const meta = qualityMeta[state.detailQuality];
  const augments = (detail.recommendedAugments || []).filter((item) => item.quality === state.detailQuality).sort((a, b) => b.winRate - a.winRate).slice(0, 30);
  return `<section class="detail-section augment-recommendations">
    <div class="section-title"><h3>海克斯选择</h3><span>按胜率排序 · 每阶最多30个</span></div>
    ${qualityTabs("detail", state.detailQuality)}
    <div class="recommendation-list">${augments.map((augment, index) => `<article class="recommendation-row ${meta.className}"><span class="recommendation-rank">${index + 1}</span><img src="${escapeHTML(asset(augment.iconPath))}" alt="" loading="lazy"><span class="recommendation-name"><b>${escapeHTML(augment.name)}</b><small>选取 ${percent(augment.pickRate)}</small></span>${winRate(augment.winRate)}</article>`).join("")}</div>
    ${augments.length ? "" : `<div class="empty-state small">本阶暂无足够样本</div>`}
  </section>`;
}

function renderDetail() {
  const champion = state.selected;
  const detail = state.detail;
  if (!champion || !detail) return;
  const buffs = Object.entries(detail.balanceBuffs || {});
  const boots = (detail.builds?.BOOTS || []).slice(0, 3);
  detailContent.innerHTML = `${renderDetailHeader(champion)}<div class="detail-scroll">
    ${buffs.length ? `<section class="detail-section balance-section"><div class="section-title"><h3>模式平衡调整</h3></div><div class="buff-list">${buffs.map(([key, value]) => `<span>${escapeHTML(key)}<b>${escapeHTML(value)}</b></span>`).join("")}</div></section>` : ""}
    <section class="detail-section"><div class="section-title"><h3>出门装</h3><span>按选取率排列</span></div><div class="build-list">${(detail.startingItems || []).slice(0, 5).map(renderBuildRow).join("")}</div></section>
    <section class="detail-section"><div class="section-title"><h3>后续出装顺序</h3><span>完整成装路径</span></div><div class="path-list">${renderPaths(detail)}</div></section>
    ${boots.length ? `<section class="detail-section"><div class="section-title"><h3>鞋子选择</h3><span>常用前三</span></div><div class="compact-build-grid">${boots.map((build) => { const item = build.value[0]; return `<div class="compact-build">${itemIcon(item.id, item)}<span><b>${escapeHTML(item.name)}</b><small>胜率 ${percent(build.winRate)}</small></span></div>`; }).join("")}</div></section>` : ""}
    <div id="detail-augments">${renderRecommendations(detail)}</div>
  </div>`;
}

function closeDetail() {
  overlay.hidden = true;
  document.body.classList.remove("no-scroll");
  state.selected = null;
  state.detail = null;
}

document.querySelector(".primary-tabs").addEventListener("click", (event) => {
  const button = event.target.closest("[data-surface]");
  if (!button) return;
  state.surface = button.dataset.surface;
  state.query = "";
  state.sortKey = "winRate";
  search.value = "";
  sort.value = "winRate";
  search.placeholder = state.surface === "champions" ? "搜索英雄名称" : "搜索海克斯名称或效果";
  document.querySelectorAll("[data-surface]").forEach((item) => item.classList.toggle("active", item === button));
  render();
});

search.addEventListener("input", () => { state.query = search.value; render(); });
sort.addEventListener("change", () => { state.sortKey = sort.value; render(); });

content.addEventListener("click", (event) => {
  const roleButton = event.target.closest("[data-role]");
  if (roleButton) { state.role = roleButton.dataset.role; render(); return; }
  const qualityButton = event.target.closest('[data-quality-context="global"]');
  if (qualityButton) { state.quality = Number(qualityButton.dataset.quality); render(); return; }
  const champion = event.target.closest("[data-champion]");
  if (champion) openChampion(champion.dataset.champion);
});

content.addEventListener("keydown", (event) => {
  if ((event.key === "Enter" || event.key === " ") && event.target.matches("tr[data-champion]")) openChampion(event.target.dataset.champion);
});

detailContent.addEventListener("click", (event) => {
  const button = event.target.closest('[data-quality-context="detail"]');
  if (!button || !state.detail) return;
  state.detailQuality = Number(button.dataset.quality);
  document.querySelector("#detail-augments").innerHTML = renderRecommendations(state.detail);
});

document.querySelector("#close-detail").addEventListener("click", closeDetail);
overlay.addEventListener("click", (event) => { if (event.target === overlay) closeDetail(); });
document.addEventListener("keydown", (event) => { if (event.key === "Escape" && !overlay.hidden) closeDetail(); });

async function init() {
  try {
    const [manifest, champions, augments] = await Promise.all([
      loadJSON("manifest.json"), loadJSON("champions.json"), loadJSON("augments.json"),
    ]);
    state.manifest = manifest;
    state.champions = champions.items || champions;
    state.augments = augments.items || augments;
    document.querySelector("#version").textContent = `版本 ${manifest.version}`;
    document.querySelector(".version-pill i").classList.add("live");
    const date = new Date(manifest.updatedAt);
    document.querySelector("#updated").textContent = Number.isNaN(date.valueOf()) ? "数据仅供当前版本对局参考" : `数据更新：${date.toLocaleDateString("zh-CN")} · 仅供对局参考`;
    render();
  } catch (error) {
    content.innerHTML = `<div class="fatal-error"><b>数据暂时无法读取</b><p>${escapeHTML(error.message)}</p><button onclick="location.reload()">重新加载</button></div>`;
    document.querySelector("#version").textContent = "加载失败";
  }
}

init();
