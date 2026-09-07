import json
import re
import html as html_lib
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote, urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "news" / "data" / "news.json"

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
}

FOLLOW_UP = {
    "国内": "后续可继续关注相关部门正式通报、政策执行范围、时间节点以及对民生和经济运行的实际影响。",
    "国际": "后续可继续关注各方官方表态、局势是否升级，以及对能源、贸易和全球市场的外溢影响。",
    "财经": "后续可继续关注政策落地、市场价格反应、资金流向以及对居民和企业成本的影响。",
    "科技": "后续可继续关注技术是否真正落地、产业链影响、监管变化和商业化进展。",
    "社会": "后续可继续关注主管部门通报、处置进展、影响范围和保障措施。",
    "AI": "后续可继续关注官方发布、模型或产品能力、上线时间、商业化、监管与行业反馈。",
}

NOISE = (
    "责任编辑", "版权声明", "免责声明", "更多精彩", "点击查看", "阅读全文", "扫码", "微信公众号",
    "本文来源", "来源：", "原文链接", "未经授权", "广告", "投稿", "打开APP", "下载客户端",
)


def clean(text):
    text = html_lib.unescape(str(text or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def norm(text):
    return re.sub(r"[^\w\u4e00-\u9fff]", "", clean(text).lower())


def split_sentences(text):
    text = clean(text)
    if not text:
        return []
    parts = re.split(r"(?<=[。！？!?；;])\s*|(?<=\.)\s+(?=[A-Z0-9])", text)
    out, seen = [], set()
    for part in parts:
        part = clean(part).strip(" -—|·")
        if len(part) < 12 or any(x in part for x in NOISE):
            continue
        if len(part) > 150:
            part = part[:147].rstrip("，,；; ") + "…"
        if part[-1:] not in "。！？!?；;…":
            part += "。"
        n = norm(part)
        if n and n not in seen:
            seen.add(n)
            out.append(part)
    return out


def bing_direct_url(title):
    """Use Bing News RSS to find a likely publisher URL for the same headline."""
    try:
        url = f"https://www.bing.com/news/search?q={quote(title[:100])}&format=rss&setlang=zh-cn"
        r = requests.get(url, headers=UA, timeout=7)
        if r.status_code >= 400:
            return ""
        root = ET.fromstring(r.content)
        target = norm(title)
        best_link, best_ratio = "", 0.0
        for item in root.findall(".//item")[:10]:
            t = clean(item.findtext("title") or "")
            link = clean(item.findtext("link") or "")
            if not t or not link:
                continue
            ratio = SequenceMatcher(None, target, norm(t)).ratio()
            if ratio > best_ratio:
                best_ratio, best_link = ratio, link
        if best_ratio < 0.32 or not best_link:
            return ""

        # Bing RSS sometimes returns an apiclick URL with the real publisher URL in ?url=
        parsed = urlparse(best_link)
        if "bing.com" in parsed.netloc:
            q = parse_qs(parsed.query)
            for key in ("url", "u", "target"):
                if q.get(key):
                    candidate = unquote(q[key][0])
                    if candidate.startswith("http"):
                        return candidate
        return best_link
    except Exception:
        return ""


def jsonld_article_body(soup):
    bodies = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.string or tag.get_text(" ", strip=True)
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            continue

        stack = obj if isinstance(obj, list) else [obj]
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                body = cur.get("articleBody")
                if isinstance(body, str) and len(clean(body)) >= 80:
                    bodies.append(clean(body))
                for v in cur.values():
                    if isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(cur, list):
                stack.extend(cur)
    return max(bodies, key=len) if bodies else ""


def extract_article(url):
    """Return a compact body candidate and final publisher URL; never store the full page."""
    if not url or not url.startswith("http"):
        return "", ""
    try:
        r = requests.get(url, headers=UA, timeout=8, allow_redirects=True)
        if r.status_code >= 400 or "text/html" not in r.headers.get("content-type", ""):
            return "", r.url if r.url.startswith("http") else ""
        soup = BeautifulSoup(r.text[:1_500_000], "html.parser")
        for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "aside", "form"]):
            tag.decompose()

        candidates = []
        for attrs in (
            {"property": "og:description"}, {"name": "description"},
            {"name": "twitter:description"},
        ):
            tag = soup.find("meta", attrs=attrs)
            if tag and tag.get("content"):
                text = clean(tag.get("content"))
                if len(text) >= 40:
                    candidates.append(text)

        body = jsonld_article_body(soup)
        if body:
            candidates.append(body)

        container = soup.find("article") or soup.find("main") or soup
        paras = []
        for p in container.find_all("p"):
            text = clean(p.get_text(" ", strip=True))
            if 28 <= len(text) <= 900 and not any(x in text for x in NOISE):
                paras.append(text)
            if sum(len(x) for x in paras) > 5000:
                break
        if paras:
            candidates.append("。".join(paras))

        text = max(candidates, key=len) if candidates else ""
        if len(text) > 6500:
            text = text[:6500]
        final_url = r.url if r.url.startswith("http") else url
        return text, final_url
    except Exception:
        return "", ""


def title_keywords(title):
    chunks = re.findall(r"[\u4e00-\u9fffA-Za-z0-9-]{2,}", title or "")
    stop = {"最新", "今日", "消息", "报道", "回应", "宣布", "中国", "美国", "公司", "有关", "关于"}
    return [x.lower() for x in chunks if x not in stop][:8]


def sentence_score(sentence, index, keywords):
    s = sentence.lower()
    score = max(0, 5 - index * 0.35)
    score += min(3, sum(1 for k in keywords if k and k in s)) * 1.3
    if re.search(r"\d", sentence):
        score += 1.5
    if any(k in sentence for k in ("表示", "称", "宣布", "决定", "预计", "截至", "其中", "目前", "将", "已", "发生", "造成")):
        score += 0.7
    return score


def select_details(title, texts, limit=5):
    title_n = norm(title)
    kws = title_keywords(title)
    all_sentences = []
    seen = set()
    for text in texts:
        for s in split_sentences(text):
            n = norm(s)
            if not n or n in seen:
                continue
            seen.add(n)
            # Skip a sentence that is essentially just the title.
            ratio = SequenceMatcher(None, title_n, n).ratio() if title_n else 0
            if ratio > 0.88:
                continue
            all_sentences.append(s)

    ranked = sorted(
        enumerate(all_sentences),
        key=lambda x: sentence_score(x[1], x[0], kws),
        reverse=True,
    )[: max(limit * 2, limit)]
    chosen_indexes = sorted(i for i, _ in ranked[:limit])
    return [all_sentences[i] for i in chosen_indexes]


def compact_sentence(s, max_len=92):
    s = clean(s).strip("。！？!?；; ")
    if len(s) > max_len:
        s = s[: max_len - 1].rstrip("，,；; ") + "…"
    return s


def make_brief(item):
    title = clean(item.get("title"))
    source = clean(item.get("source")) or "新闻来源"
    category = clean(item.get("category")) or "新闻"
    existing = clean(item.get("summary"))

    direct = bing_direct_url(title)
    article_text, final_url = extract_article(direct) if direct else ("", "")
    if final_url and "google.com" not in urlparse(final_url).netloc and "bing.com" not in urlparse(final_url).netloc:
        item["url"] = final_url

    details = select_details(title, [existing, article_text], limit=5)

    intro = f"{source}这篇报道主要讲的是：{title}。" if title else f"{source}发布了新的报道。"
    if details:
        quick = intro + "".join(details)
    elif existing:
        quick = intro + existing
    else:
        quick = intro + "目前公开聚合源没有提供足够正文信息，因此这里只保留已经确认的标题事实，不补写未经来源支持的细节。"

    # Popup summary is deliberately fuller than the card summary, but still compact enough for mobile reading.
    if len(quick) > 560:
        quick = quick[:557].rstrip("，,；; ") + "…"

    points = []
    if title:
        points.append(f"核心事件：{title}")
    for s in details[:4]:
        p = compact_sentence(s)
        if p:
            points.append(p)
    if len(points) < 3:
        points.append(FOLLOW_UP.get(category, "后续可继续关注权威来源的进一步披露和事件实际进展。"))

    uniq, seen = [], set()
    for p in points:
        n = norm(p)
        if n and n not in seen:
            seen.add(n)
            uniq.append(p)
        if len(uniq) >= 5:
            break

    item["quick_summary"] = quick
    item["key_points"] = uniq
    # User prefers a cleaner brief: no separate “why it matters” field.
    item.pop("why_it_matters", None)


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    items = []
    for section_items in (data.get("sections") or {}).values():
        items.extend(section_items)
    items.extend(data.get("top5") or [])

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = [ex.submit(make_brief, item) for item in items]
        for f in as_completed(futures):
            try:
                f.result()
            except Exception:
                pass

    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("detailed quick briefs added", DATA)


if __name__ == "__main__":
    main()
