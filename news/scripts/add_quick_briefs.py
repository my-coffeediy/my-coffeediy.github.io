import json
import re
import html as html_lib
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
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
    "发布于", "官方账号", "郑重声明", "风险自担", "字体：", "小 中 大",
)

GENERIC_SUMMARY_MARKERS = (
    "目前可确认的信息以相关部门和权威媒体后续发布为准",
    "事件仍在发展，后续需关注各方官方表态与权威媒体的交叉确认",
    "后续影响将取决于政策执行、市场反应和相关数据变化",
    "后续重点关注官方披露、产业链反应和实际落地情况",
    "后续重点关注主管部门通报、处置进展和实际影响范围",
    "后续重点关注官方发布、产品落地、监管变化与行业反馈",
)

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


def clean(text):
    text = html_lib.unescape(str(text or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def norm(text):
    return re.sub(r"[^\w\u4e00-\u9fff]", "", clean(text).lower())


def title_similarity(a, b):
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    if na in nb or nb in na:
        return min(1.0, min(len(na), len(nb)) / max(10, max(len(na), len(nb))) + 0.35)
    return SequenceMatcher(None, na, nb).ratio()


def split_sentences(text):
    text = clean(text)
    if not text:
        return []
    parts = re.split(r"(?<=[。！？!?；;])\s*|(?<=\.)\s+(?=[A-Z0-9])", text)
    out, seen = [], set()
    for part in parts:
        part = clean(part).strip(" -—|·")
        if len(part) < 14 or any(x in part for x in NOISE):
            continue
        if len(part) > 170:
            part = part[:167].rstrip("，,；; ") + "…"
        if part[-1:] not in "。！？!?；;…":
            part += "。"
        n = norm(part)
        if n and n not in seen:
            seen.add(n)
            out.append(part)
    return out


def decode_bing_link(link):
    parsed = urlparse(link)
    if "bing.com" not in parsed.netloc:
        return link
    q = parse_qs(parsed.query)
    for key in ("url", "u", "target"):
        if q.get(key):
            candidate = unquote(q[key][0])
            if candidate.startswith("http"):
                return candidate
    return link


def rss_best_result(search_url, title, source=""):
    try:
        r = requests.get(search_url, headers=UA, timeout=7)
        if r.status_code >= 400:
            return "", "", 0.0
        root = ET.fromstring(r.content)
        best = ("", "", 0.0)
        for item in root.findall(".//item")[:15]:
            t = clean(item.findtext("title") or "")
            link = clean(item.findtext("link") or "")
            desc = clean(item.findtext("description") or "")
            if not t or not link:
                continue
            score = title_similarity(title, t)
            result_source = clean(item.findtext("source") or "")
            if source and result_source and (source.lower() in result_source.lower() or result_source.lower() in source.lower()):
                score += 0.08
            if score > best[2]:
                best = (decode_bing_link(link), desc, score)
        return best
    except Exception:
        return "", "", 0.0


def bing_candidate(title, source):
    """Try Bing News first, then Bing web RSS; only accept close headline matches."""
    query = f'"{title[:105]}" {source}' if source else f'"{title[:105]}"'
    q = quote(query)
    urls = [
        f"https://www.bing.com/news/search?q={q}&format=rss&setlang=zh-cn",
        f"https://www.bing.com/search?q={q}&format=rss&setlang=zh-cn",
    ]
    best = ("", "", 0.0)
    for url in urls:
        result = rss_best_result(url, title, source)
        if result[2] > best[2]:
            best = result
        if best[2] >= 0.90:
            break
    if best[2] < 0.68:
        return "", ""
    return best[0], best[1]


def walk_jsonld(soup):
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
                yield cur
                for v in cur.values():
                    if isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(cur, list):
                stack.extend(cur)


def jsonld_article_body(soup):
    bodies = []
    for cur in walk_jsonld(soup):
        body = cur.get("articleBody")
        if isinstance(body, str) and len(clean(body)) >= 80:
            bodies.append(clean(body))
    return max(bodies, key=len) if bodies else ""


def parse_date(value):
    value = clean(value)
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass
    m = re.search(r"(20\d{2})[-年/.](\d{1,2})[-月/.](\d{1,2})", value)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def page_date(soup, text_prefix=""):
    for attrs in (
        {"property": "article:published_time"}, {"property": "og:published_time"},
        {"name": "publishdate"}, {"name": "pubdate"}, {"itemprop": "datePublished"},
    ):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            dt = parse_date(tag.get("content"))
            if dt:
                return dt
    for cur in walk_jsonld(soup):
        for key in ("datePublished", "dateCreated", "dateModified"):
            if cur.get(key):
                dt = parse_date(cur.get(key))
                if dt:
                    return dt
    return parse_date(text_prefix[:6000])


def publisher_title(soup):
    for attrs in ({"property": "og:title"}, {"name": "twitter:title"}):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            return clean(tag.get("content"))
    return clean(soup.title.get_text(" ", strip=True)) if soup.title else ""


def date_is_plausible(page_dt, item_iso):
    if not page_dt or not item_iso:
        return True
    try:
        item_dt = datetime.fromisoformat(item_iso.replace("Z", "+00:00"))
        if item_dt.tzinfo is None:
            item_dt = item_dt.replace(tzinfo=timezone.utc)
        return abs((page_dt.astimezone(timezone.utc) - item_dt.astimezone(timezone.utc)).total_seconds()) <= 7 * 86400
    except Exception:
        return True


def keyword_coverage(title, text):
    t = norm(title)
    x = norm(text[:5000])
    if len(t) < 6 or not x:
        return 0.0
    grams = {t[i:i+3] for i in range(len(t)-2)}
    return sum(1 for g in grams if g in x) / len(grams) if grams else 0.0


def extract_article(url, expected_title, item_iso):
    """Extract body only when page title/content/date plausibly match the current story."""
    if not url or not url.startswith("http"):
        return "", ""
    try:
        r = requests.get(url, headers=UA, timeout=8, allow_redirects=True)
        if r.status_code >= 400 or "text/html" not in r.headers.get("content-type", ""):
            return "", ""
        soup = BeautifulSoup(r.text[:1_500_000], "html.parser")
        ptitle = publisher_title(soup)
        page_text = clean(soup.get_text(" ", strip=True)[:9000])
        title_match = title_similarity(expected_title, ptitle)
        coverage = keyword_coverage(expected_title, ptitle + " " + page_text)
        if title_match < 0.52 and coverage < 0.38:
            return "", ""
        if not date_is_plausible(page_date(soup, page_text), item_iso):
            return "", ""

        for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "aside", "form"]):
            tag.decompose()

        candidates = []
        for attrs in ({"property": "og:description"}, {"name": "description"}, {"name": "twitter:description"}):
            tag = soup.find("meta", attrs=attrs)
            if tag and tag.get("content"):
                text = clean(tag.get("content"))
                if len(text) >= 45:
                    candidates.append(text)
        body = jsonld_article_body(soup)
        if body:
            candidates.append(body)

        container = soup.find("article") or soup.find("main") or soup
        paras, total = [], 0
        for p in container.find_all("p"):
            text = clean(p.get_text(" ", strip=True))
            if 30 <= len(text) <= 900 and not any(x in text for x in NOISE):
                paras.append(text)
                total += len(text)
            if total > 6000:
                break
        if paras:
            candidates.append("。".join(paras))

        text = max(candidates, key=len) if candidates else ""
        if text and keyword_coverage(expected_title, text) < 0.16 and title_match < 0.70:
            return "", ""
        if len(text) > 7000:
            text = text[:7000]
        return text, (r.url if r.url.startswith("http") else url)
    except Exception:
        return "", ""


def can_replace_source_url(source, url):
    host = urlparse(url).netloc.lower()
    allowed = SOURCE_DOMAINS.get(source)
    return bool(allowed and any(host == d or host.endswith("." + d) for d in allowed))


def informative_existing(text, title):
    text = clean(text)
    if not text or any(x in text for x in GENERIC_SUMMARY_MARKERS):
        return ""
    useful = []
    for s in split_sentences(text):
        if title_similarity(title, s) > 0.80:
            continue
        useful.append(s)
    return "".join(useful)


def informative_snippet(text, title):
    text = clean(text)
    if len(text) < 35 or any(x in text for x in GENERIC_SUMMARY_MARKERS):
        return ""
    if keyword_coverage(title, text) < 0.10 and title_similarity(title, text) < 0.45:
        return ""
    return text


def title_keywords(title):
    ascii_words = re.findall(r"[A-Za-z0-9][A-Za-z0-9.-]{1,}", title or "")
    chinese_chunks = re.findall(r"[\u4e00-\u9fff]{2,8}", title or "")
    return [x.lower() for x in (ascii_words + chinese_chunks)][:14]


def sentence_score(sentence, index, keywords):
    s = sentence.lower()
    score = max(0, 5 - index * 0.25)
    score += min(4, sum(1 for k in keywords if k and k in s)) * 1.15
    if re.search(r"\d", sentence):
        score += 1.7
    if any(k in sentence for k in ("表示", "称", "宣布", "决定", "预计", "截至", "其中", "目前", "将", "已", "发生", "造成", "自", "根据")):
        score += 0.8
    return score


def select_details(title, texts, limit=5):
    title_n = norm(title)
    kws = title_keywords(title)
    all_sentences, seen = [], set()
    for text in texts:
        for s in split_sentences(text):
            n = norm(s)
            if not n or n in seen:
                continue
            seen.add(n)
            if title_n and title_similarity(title, s) > 0.88:
                continue
            all_sentences.append(s)
    ranked = sorted(enumerate(all_sentences), key=lambda x: sentence_score(x[1], x[0], kws), reverse=True)
    chosen_indexes = sorted(i for i, _ in ranked[:limit])
    return [all_sentences[i] for i in chosen_indexes]


def compact_sentence(s, max_len=110):
    s = clean(s).strip("。！？!?；; ")
    if len(s) > max_len:
        s = s[:max_len - 1].rstrip("，,；; ") + "…"
    return s


def make_brief(item):
    title = clean(item.get("title"))
    source = clean(item.get("source")) or "新闻来源"
    category = clean(item.get("category")) or "新闻"
    existing = informative_existing(item.get("summary"), title)

    direct, search_snippet = bing_candidate(title, source)
    search_snippet = informative_snippet(search_snippet, title)
    article_text, final_url = extract_article(direct, title, item.get("published_at")) if direct else ("", "")
    if final_url and can_replace_source_url(source, final_url):
        item["url"] = final_url

    details = select_details(title, [article_text, search_snippet, existing], limit=5)
    intro = f"{source}这篇报道主要讲的是：{title}。" if title else f"{source}发布了新的报道。"
    if details:
        quick = intro + "".join(details)
    else:
        quick = intro + "目前能稳定核实到的正文信息有限，因此这里暂不补写未经来源支持的细节；可通过原报道继续查看完整内容。"

    if len(quick) > 650:
        quick = quick[:647].rstrip("，,；; ") + "…"

    points = [f"核心事件：{title}"] if title else []
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
    print("validated detailed quick briefs added", DATA)


if __name__ == "__main__":
    main()
