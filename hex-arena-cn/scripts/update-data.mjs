import { mkdir, readdir, unlink, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const DATA_DIR = join(ROOT, "data");
const DETAILS_DIR = join(DATA_DIR, "details");
const ENTRY_URL = "https://www.bilibili.com/toy/resg/index.html";
const FALLBACK_BASE = "https://www.bilibilitoy.com/toy/resg/19226257645568-v12014/";

function parseModule(text) {
  return JSON.parse(text.replace(/^\s*export\s+default\s+/, "").replace(/;\s*$/, "").trim());
}

async function requestText(url) {
  const response = await fetch(url, {
    headers: { "user-agent": "Mozilla/5.0 HexArenaStaticUpdater/1.0" },
    signal: AbortSignal.timeout(30_000),
  });
  if (!response.ok) throw new Error(`${url} 返回 ${response.status}`);
  return response.text();
}

async function requestModule(url) {
  return parseModule(await requestText(url));
}

async function resolveBase() {
  if (process.env.RESG_BASE_URL) return new URL("./", process.env.RESG_BASE_URL).href;
  try {
    const html = await requestText(ENTRY_URL);
    const source = html.match(/<iframe[^>]+src=["']([^"']+)["']/i)?.[1];
    if (!source) return FALLBACK_BASE;
    return new URL("./", new URL(source, ENTRY_URL)).href;
  } catch {
    return FALLBACK_BASE;
  }
}

function normalizeAssets(value, base) {
  if (Array.isArray(value)) return value.map((item) => normalizeAssets(item, base));
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => {
      const isAsset = (key === "iconPath" || key === "icon") && typeof item === "string" && !/^https?:\/\//.test(item);
      return [key, isAsset ? new URL(item.replace(/^\//, ""), base).href : normalizeAssets(item, base)];
    }));
  }
  return value;
}

function leanAugment(item) {
  return {
    id: item.id,
    name: item.name,
    description: item.description,
    iconPath: item.iconPath,
    totalMatches: item.totalMatches,
    winRate: item.winRate,
    pickRate: item.pickRate,
    tier: item.tier,
    quality: item.quality,
  };
}

function leanDetail(detail) {
  const recommendations = [1, 2, 3].flatMap((quality) =>
    (detail.recommendedAugments || [])
      .filter((item) => item.quality === quality)
      .sort((a, b) => b.winRate - a.winRate)
      .slice(0, 30)
      .map(leanAugment),
  );
  return {
    balanceBuffs: detail.balanceBuffs || {},
    startingItems: (detail.startingItems || []).slice(0, 5),
    builds: { BOOTS: (detail.builds?.BOOTS || []).slice(0, 3) },
    recommendedAugments: recommendations,
    itemAnalysis: {
      combos: Object.fromEntries([2, 3, 4].map((size) => [String(size), (detail.itemAnalysis?.combos?.[String(size)] || []).slice(0, 1)])),
    },
  };
}

async function writeJSON(path, value) {
  await writeFile(path, JSON.stringify(value));
}

async function mapConcurrent(items, concurrency, worker) {
  let cursor = 0;
  const runners = Array.from({ length: Math.min(concurrency, items.length) }, async () => {
    while (cursor < items.length) {
      const index = cursor++;
      await worker(items[index], index);
    }
  });
  await Promise.all(runners);
}

const base = await resolveBase();
const versions = await requestModule(new URL("api/v1/versions.js", base));
const version = versions?.[0]?.version;
if (!version) throw new Error("数据源未返回有效版本号");

const [championsRaw, augmentsRaw, itemsRaw] = await Promise.all([
  requestModule(new URL(`api/v1/versions/${version}/champions.js`, base)),
  requestModule(new URL(`api/v1/versions/${version}/augments.js`, base)),
  requestModule(new URL("api/v1/items-detail.js", base)),
]);

const champions = normalizeAssets(championsRaw, base);
const normalizedAugments = normalizeAssets(augmentsRaw, base);
const augments = {
  ...normalizedAugments,
  items: (normalizedAugments.items || normalizedAugments).map(leanAugment),
};
const items = normalizeAssets(itemsRaw, base);
const championList = champions.items || champions;

await mkdir(DETAILS_DIR, { recursive: true });
for (const filename of await readdir(DETAILS_DIR)) {
  if (/^\d+\.json$/.test(filename)) await unlink(join(DETAILS_DIR, filename));
}

await Promise.all([
  writeJSON(join(DATA_DIR, "champions.json"), champions),
  writeJSON(join(DATA_DIR, "augments.json"), augments),
  writeJSON(join(DATA_DIR, "items.json"), items),
]);

let completed = 0;
await mapConcurrent(championList, 24, async (champion) => {
  const detail = await requestModule(new URL(`api/v1/versions/${version}/champions/${champion.id}.js`, base));
  await writeJSON(join(DETAILS_DIR, `${champion.id}.json`), leanDetail(normalizeAssets(detail, base)));
  completed += 1;
  process.stdout.write(`\r英雄详情 ${completed}/${championList.length}`);
});

await writeJSON(join(DATA_DIR, "manifest.json"), {
  version,
  updatedAt: new Date().toISOString(),
  assetBase: base,
  championCount: championList.length,
  augmentCount: (augments.items || augments).length,
});

process.stdout.write(`\n完成：版本 ${version}，${championList.length} 位英雄，${(augments.items || augments).length} 个海克斯。\n`);
