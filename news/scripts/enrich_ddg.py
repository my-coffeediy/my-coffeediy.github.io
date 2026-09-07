import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup

from enrich_quick_briefs import (
    UA, clean, norm, sim, extract_page, build_detail, source_link_ok
)

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "news" / "data" / "news.json"
LIMITED = "目前能稳定核实到的正文信息有限"


def decode_ddg_href(href):
    if not href:
        return ""
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc:
        q = parse_qs(parsed.query)
        if q.get("uddg"):
            return unquote(q["uddg"][0])
    return href


def search_ddg(title, source):
    best = ("", "", 0.0)
    for query in (f'"{title}" {source}', f'"{title}"'):
        try:
            r = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query}, headers=UA, timeout=10,
            )
            if r.status_code >= 400:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            for result in soup.select(".result")[:10]:
                a = result.select_one(".result__a")
                if not a:
                    continue
                rt = clean(a.get_text(" ", strip=True))
                href = decode_ddg_href(a.get("href", ""))
                if not href.startswith("http"):
                    continue
                snippet_tag = result.select_one(".result__snippet")
                snippet = clean(snippet_tag.get_text(" ", strip=True)) if snippet_tag else ""
                score = sim(title, rt)
                if score > best[2]:
                    best = (href, snippet, score)
            if best[2] >= 0.88:
                break
        except Exception:
            continue
    return (best[0], best[1]) if best[2] >= 0.66 else ("", "")


def enrich_one(item):
    title = clean(item.get("title"))
    source = clean(item.get("source")) or "新闻来源"
    if not title:
        return None
    link, snippet = search_ddg(title, source)
    if not link:
        return None
    page_text, final_url = extract_page(link, title, item.get("published_at"))
    details = build_detail(title, page_text, snippet)
    if not details:
        return None
    quick = f"{source}这篇报道主要讲的是：{title}。" + "".join(details)
    if len(quick) > 720:
        quick = quick[:717].rstrip("，,；; ") + "…"
    points = [f"核心事件：{title}"]
    for s in details[:4]:
        p = clean(s).strip("。！？!?；; ")
        if len(p) > 120:
            p = p[:117].rstrip("，,；; ") + "…"
        points.append(p)
    out = {"quick_summary": quick, "key_points": points[:5]}
    if final_url and source_link_ok(source, final_url):
        out["url"] = final_url
    return out


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    all_items = []
    for arr in (data.get("sections") or {}).values():
        all_items.extend(arr)
    all_items.extend(data.get("top5") or [])

    grouped = {}
    for item in all_items:
        item.pop("why_it_matters", None)
        if LIMITED in clean(item.get("quick_summary")):
            grouped.setdefault(norm(item.get("title")), []).append(item)

    reps = [arr[0] for k, arr in grouped.items() if k]
    results = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(enrich_one, item): norm(item.get("title")) for item in reps}
        for f in as_completed(futures):
            key = futures[f]
            try:
                result = f.result()
                if result:
                    results[key] = result
            except Exception:
                pass

    for key, result in results.items():
        for item in grouped.get(key, []):
            item.update(result)
            item.pop("why_it_matters", None)

    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"DuckDuckGo detail enrichment: {len(results)}/{len(reps)} remaining stories enriched")


if __name__ == "__main__":
    main()
