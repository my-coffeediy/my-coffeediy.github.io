import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "news" / "data" / "news.json"

CATEGORY_FOCUS = {
    "国内": "后续重点关注相关部门的正式文件、执行范围、时间节点以及对民生和经济运行的实际影响。",
    "国际": "后续重点关注各方官方表态、局势是否升级，以及对能源、贸易和全球市场的外溢影响。",
    "财经": "后续重点关注政策落地、市场价格反应、资金流向以及对居民和企业成本的影响。",
    "科技": "后续重点关注技术是否真正落地、产业链影响、监管变化和商业化进展。",
    "社会": "后续重点关注主管部门通报、处置进展、影响范围和后续保障措施。",
    "AI": "后续重点关注官方发布、模型/产品能力、上线时间、商业化、监管与行业反馈。",
}


def clean(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def split_sentences(text):
    text = clean(text)
    if not text:
        return []
    parts = re.split(r"(?<=[。！？!?；;])\s*", text)
    out = []
    seen = set()
    for part in parts:
        part = clean(part)
        if not part:
            continue
        if part[-1:] not in "。！？!?；;…":
            part += "。"
        norm = re.sub(r"[^\w\u4e00-\u9fff]", "", part.lower())
        if norm and norm not in seen:
            seen.add(norm)
            out.append(part)
    return out


def why_it_matters(category, title):
    t = title or ""
    if any(k in t for k in ("地震", "台风", "暴雨", "洪涝", "事故", "伤亡", "失联", "救灾", "滑坡", "泥石流")):
        return "直接关系人员安全、交通运行和应急处置，属于需要优先关注的信息。"
    if any(k in t for k in ("央行", "人民银行", "降准", "降息", "利率", "人民币")):
        return "可能影响利率、人民币、楼市、企业融资和资本市场预期。"
    if any(k in t for k in ("国务院", "中共中央", "中央政治局", "财政部", "发改委")):
        return "属于国家层面的政策或治理信息，可能影响后续经济运行和民生安排。"
    if category == "国际":
        return "可能影响国际局势、能源与大宗商品价格、全球贸易或金融市场。"
    if category == "财经":
        return "可能影响市场走势、行业预期、企业经营或居民资产价格。"
    if category == "AI":
        return "可能影响AI行业竞争格局、产品能力、算力需求和监管方向。"
    if category == "科技":
        return "涉及关键技术和产业链变化，可能影响相关行业发展节奏。"
    if category == "社会":
        return "与公共服务、民生保障或社会运行直接相关。"
    return "与国内政策、经济或民生变化相关，值得持续关注后续落地。"


def make_brief(item):
    title = clean(item.get("title"))
    source = clean(item.get("source")) or "新闻来源"
    category = clean(item.get("category")) or "新闻"
    raw = clean(item.get("summary"))

    raw_sentences = split_sentences(raw)
    title_norm = re.sub(r"[^\w\u4e00-\u9fff]", "", title.lower())
    usable = []
    for s in raw_sentences:
        s_norm = re.sub(r"[^\w\u4e00-\u9fff]", "", s.lower())
        if s_norm and s_norm != title_norm and title_norm not in s_norm:
            usable.append(s)

    intro = f"{source}报道，{title}。" if title else f"{source}发布了最新消息。"
    if usable:
        detail = "".join(usable[:3])
        quick = intro + detail
    else:
        quick = intro + "当前公开聚合信息暂未提供更完整正文摘要，以下只整理已确认重点，不补写未经来源支持的细节。"

    if len(quick) > 360:
        quick = quick[:357].rstrip("，,；; ") + "…"

    points = [f"核心事件：{title}" if title else "核心事件：来源发布了新的进展。"]
    for s in usable[:2]:
        text = s.rstrip("。！？!?；;")
        if len(text) > 95:
            text = text[:92].rstrip("，,；; ") + "…"
        points.append(text)
    focus = CATEGORY_FOCUS.get(category, "后续重点关注权威来源的进一步披露和事件实际影响。")
    points.append(focus)

    # 去重并限制 4 条
    uniq = []
    seen = set()
    for p in points:
        n = re.sub(r"[^\w\u4e00-\u9fff]", "", p.lower())
        if n and n not in seen:
            seen.add(n)
            uniq.append(p)
        if len(uniq) >= 4:
            break

    item["quick_summary"] = quick
    item["key_points"] = uniq
    item["why_it_matters"] = item.get("why_it_matters") or why_it_matters(category, title)


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    for items in (data.get("sections") or {}).values():
        for item in items:
            make_brief(item)
    for item in data.get("top5") or []:
        make_brief(item)
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("quick briefs added", DATA)


if __name__ == "__main__":
    main()
