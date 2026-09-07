import json
import re
import html as html_lib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "news" / "data" / "news.json"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
}

SOURCE_DOMAINS = {
    "新华网": ("news.cn", "xinhuanet.com"), "新华社": ("news.cn", "xinhuanet.com"),
    "人民日报": ("people.com.cn",), "央视新闻": ("cctv.com", "cntv.cn"),
    "央视网": ("cctv.com", "cntv.cn"), "中国政府网": ("gov.cn",),
    "商务部": ("mofcom.gov.cn",), "mofcom.gov.cn": ("mofcom.gov.cn",),
    "财联社": ("cls.cn",), "华尔街见闻": ("wallstreetcn.com",),
    "观察者": ("guancha.cn",), "观察者网": ("guancha.cn",),
    "BBC": ("bbc.com", "bbc.co.uk"), "Reuters": ("reuters.com",),
    "路透": ("reuters.com",), "美联社": ("apnews.com",), "AP": ("apnews.com",),
}

NOISE = (
    "责任编辑", "版权声明", "免责声明", "更多精彩", "点击查看", "阅读全文", "扫码", "微信公众号",
    "本文来源", "未经授权", "广告", "投稿", "打开APP", "下载客户端", "郑重声明", "风险自担",
    "发布于", "官方账号", "字体：", "小 中 大",
)


def clean(x):
    x = html_lib.unescape(str(x or ""))
    x = re.sub(r"<[^>]+>", " ", x)
    return re.sub(r"\s+", " ", x).strip()


def norm(x):
    return re.sub(r"[^\w\u4e00-\u9fff]", "", clean(x).lower())


def sim(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return min(1.0, min(len(a), len(b)) / max(10, max(len(a), len(b))) + 0.35)
    return SequenceMatcher(None, a, b).ratio()


def keyword_coverage(title, text):
    t, x = norm(title), norm(text[:6000])
    if len(t) < 6 or not x:
        return 0.0
    grams = {t[i:i+3] for i in range(len(t)-2)}
    return sum(1 for g in grams if g in x) / len(grams) if grams else 0.0


def parse_date(text):
    text = clean(text)
    if not text:
        return None
    for pat in (
        r"(20\d{2})[-年/.](\d{1,2})[-月/.](\d{1,2})",
        r"(20\d{2})(\d{2})(\d{2})",
    ):
        m = re.search(pat, text)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
            except Exception:
                pass
    try:
        d = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return d.replace(tzinfo=d.tzinfo or timezone.utc)
    except Exception:
        return None


def plausible_date(page_date, published_at):
    if not page_date or not published_at:
        return True
    try:
        p = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        p = p.replace(tzinfo=p.tzinfo or timezone.utc)
        return abs((page_date.astimezone(timezone.utc) - p.astimezone(timezone.utc)).total_seconds()) <= 7 * 86400
    except Exception:
        return True


def page_title(soup):
    for attrs in ({"property": "og:title"}, {"name": "twitter:title"}):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            return clean(tag.get("content"))
    return clean(soup.title.get_text(" ", strip=True)) if soup.title else ""


def published_date(soup, page_text):
    for attrs in (
        {"property": "article:published_time"}, {"name": "publishdate"},
        {"name": "pubdate"}, {"itemprop": "datePublished"},
    ):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            d = parse_date(tag.get("content"))
            if d:
                return d
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.string or tag.get_text(" ", strip=True)
        if raw:
            m = re.search(r'"datePublished"\s*:\s*"([^"]+)', raw)
            if m:
                d = parse_date(m.group(1))
                if d:
                    return d
    return parse_date(page_text[:5000])


def search_bing_html(title, source):
    queries = [f'"{title}" {source}', f'"{title}"']
    best = ("", "", 0.0)
    for query in queries:
        try:
            r = requests.get(
                "https://www.bing.com/search",
                params={"q": query, "setlang": "zh-cn", "count": "10"},
                headers=UA, timeout=8,
            )
            if r.status_code >= 400:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            for li in soup.select("li.b_algo")[:10]:
                a = li.select_one("h2 a")
                if not a or not a.get("href"):
                    continue
                rt = clean(a.get_text(" ", strip=True))
                link = a.get("href")
                cap = li.select_one(".b_caption p")
                snippet = clean(cap.get_text(" ", strip=True)) if cap else ""
                score = sim(title, rt)
                host = urlparse(link).netloc.lower()
                allowed = SOURCE_DOMAINS.get(source, ())
                if allowed and any(host == d or host.endswith("." + d) for d in allowed):
                    score += 0.10
                if score > best[2]:
                    best = (link, snippet, score)
            if best[2] >= 0.88:
                break
        except Exception:
            continue
    if best[2] < 0.66:
        return "", ""
    return best[0], best[1]


def extract_page(url, title, published_at):
    if not url.startswith("http"):
        return "", ""
    try:
        r = requests.get(url, headers=UA, timeout=9, allow_redirects=True)
        if r.status_code >= 400 or "text/html" not in r.headers.get("content-type", ""):
            return "", ""
        soup = BeautifulSoup(r.text[:1_800_000], "html.parser")
        ptitle = page_title(soup)
        raw_text = clean(soup.get_text(" ", strip=True)[:10000])
        title_score = sim(title, ptitle)
        coverage = keyword_coverage(title, ptitle + " " + raw_text)
        if title_score < 0.54 and coverage < 0.38:
            return "", ""
        if not plausible_date(published_date(soup, raw_text), published_at):
            return "", ""

        for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "aside", "form"]):
            tag.decompose()

        chunks = []
        for attrs in ({"property": "og:description"}, {"name": "description"}):
            tag = soup.find("meta", attrs=attrs)
            if tag and tag.get("content") and len(clean(tag.get("content"))) > 45:
                chunks.append(clean(tag.get("content")))

        container = soup.find("article") or soup.find("main") or soup
        paras, total = [], 0
        for p in container.find_all("p"):
            text = clean(p.get_text(" ", strip=True))
            if 28 <= len(text) <= 900 and not any(n in text for n in NOISE):
                paras.append(text)
                total += len(text)
            if total >= 6500:
                break
        if paras:
            chunks.append("。".join(paras))
        text = max(chunks, key=len) if chunks else ""
        if not text:
            return "", ""
        if keyword_coverage(title, text) < 0.15 and title_score < 0.72:
            return "", ""
        return text[:7500], r.url
    except Exception:
        return "", ""


def sentences(text):
    text = clean(text)
    if not text:
        return []
    parts = re.split(r"(?<=[。！？!?；;])\s*", text)
    out, seen = [], set()
    for s in parts:
        s = clean(s).strip(" -—|·")
        if len(s) < 16 or any(n in s for n in NOISE):
            continue
        if len(s) > 175:
            s = s[:172].rstrip("，,；; ") + "…"
        if s[-1:] not in "。！？!?；;…":
            s += "。"
        n = norm(s)
        if n and n not in seen:
            seen.add(n); out.append(s)
    return out


def score_sentence(s, i, title):
    score = max(0, 5 - i * 0.22)
    score += keyword_coverage(title, s) * 5
    if re.search(r"\d", s): score += 1.5
    if any(k in s for k in ("表示", "宣布", "决定", "截至", "其中", "目前", "将", "已", "造成", "根据", "预计")):
        score += 0.8
    return score


def build_detail(title, page_text, snippet):
    pool, seen = [], set()
    for text in (page_text, snippet):
        for s in sentences(text):
            n = norm(s)
            if not n or n in seen or sim(title, s) > 0.90:
                continue
            seen.add(n); pool.append(s)
    ranked = sorted(enumerate(pool), key=lambda x: score_sentence(x[1], x[0], title), reverse=True)[:5]
    return [s for _, s in sorted(ranked, key=lambda x: x[0])]


def source_link_ok(source, url):
    host = urlparse(url).netloc.lower()
    allowed = SOURCE_DOMAINS.get(source, ())
    return bool(allowed and any(host == d or host.endswith("." + d) for d in allowed))


def enrich_story(item):
    title = clean(item.get("title"))
    source = clean(item.get("source")) or "新闻来源"
    if not title:
        return None
    link, snippet = search_bing_html(title, source)
    page_text, final_url = extract_page(link, title, item.get("published_at")) if link else ("", "")
    details = build_detail(title, page_text, snippet)
    if not details:
        return None

    quick = f"{source}这篇报道主要讲的是：{title}。" + "".join(details)
    if len(quick) > 680:
        quick = quick[:677].rstrip("，,；; ") + "…"
    points = [f"核心事件：{title}"]
    for s in details[:4]:
        p = clean(s).strip("。！？!?；; ")
        if len(p) > 115:
            p = p[:112].rstrip("，,；; ") + "…"
        points.append(p)
    result = {"quick_summary": quick, "key_points": points[:5]}
    if final_url and source_link_ok(source, final_url):
        result["url"] = final_url
    return result


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    all_items = []
    for arr in (data.get("sections") or {}).values():
        all_items.extend(arr)
    all_items.extend(data.get("top5") or [])

    # One search per unique headline, then copy the result to duplicates in Top5/sections.
    grouped = {}
    for item in all_items:
        item.pop("why_it_matters", None)
        grouped.setdefault(norm(item.get("title")), []).append(item)

    representatives = [items[0] for key, items in grouped.items() if key]
    results = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(enrich_story, item): norm(item.get("title")) for item in representatives}
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
    print(f"HTML search enrichment: {len(results)}/{len(representatives)} unique stories enriched")


if __name__ == "__main__":
    main()
