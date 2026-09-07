import json,re,html,time,math
from pathlib import Path
from datetime import datetime,timezone,timedelta
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
import xml.etree.ElementTree as ET
import feedparser,requests

try:
    import yfinance as yf
except Exception:
    yf=None

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"news"/"data"/"news.json"
TZ=timezone(timedelta(hours=8))
NOW=datetime.now(TZ)

QUERIES={
    "china":'(中国 OR 国内) (国务院 OR 中央 OR 政策 OR 经济 OR 民生 OR 就业 OR 房地产 OR 教育 OR 医疗 OR 应急 OR 台风 OR 地震 OR 暴雨 OR 外交) when:1d -明星 -娱乐 -时装 -新书 -研究会',
    "world":'(美国 OR 欧洲 OR 俄罗斯 OR 乌克兰 OR 中东 OR 联合国 OR 日本 OR 韩国) (战争 OR 冲突 OR 外交 OR 选举 OR 经济 OR 制裁 OR 停火 OR 央行 OR 灾害) when:1d',
    "finance":'(中国 财经 OR A股 OR 港股 OR 人民币 OR 央行 OR 房地产 OR 财政 OR 外贸 OR CPI OR GDP) when:1d -基金营销',
    "tech":'(科技 OR 芯片 OR 机器人 OR 新能源 OR 航天 OR 科研) 中国 when:1d',
    "society":'(社会 OR 民生 OR 教育 OR 就业 OR 医疗 OR 灾害 OR 交通 OR 食品安全) 中国 when:1d -明星 -娱乐',
    "ai":'(人工智能 OR AI OR OpenAI OR DeepSeek OR Claude OR Gemini OR 大模型 OR 智谱 OR 通义 OR 豆包) when:1d'
}

TOPIC_FEEDS={"china":"NATION","world":"WORLD","finance":"BUSINESS","tech":"TECHNOLOGY","society":"NATION"}

LIMITS={"china":14,"world":9,"finance":10,"tech":10,"society":10,"ai":10}

# 4 = 第一优先；3 = 主要权威；2 = 优质媒体；1 = 其他
SOURCE_TIER_4=["新华社","新华网","央视新闻","央视网","人民日报","中国政府网","国务院","gov.cn","mem.gov.cn","mof.gov.cn","pbc.gov.cn","ndrc.gov.cn","stats.gov.cn","mfa.gov.cn","moe.gov.cn","mohrss.gov.cn","samr.gov.cn"]
SOURCE_TIER_3=["中国新闻网","中新网","央广网","国际在线","经济日报","中国经济网","财联社","第一财经","澎湃新闻","thepaper.cn","证券时报","上海证券报","中国证券报","路透","Reuters","AP","美联社","BBC"]
SOURCE_TIER_2=["界面新闻","新京报","中青在线","南方日报","北京日报","解放日报","21世纪经济报道","每日经济新闻","联合早报","华尔街日报","cn.wsj.com","纽约时报中文网","日经中文网","彭博","Bloomberg","华尔街见闻"]

HOT=["突发","地震","台风","暴雨","洪涝","战争","冲突","停火","制裁","大选","暴跌","暴涨","危机","事故","伤亡","死亡","紧急"]

CLICKBAIT=["气炸","都得完蛋","再打下去","惊人","炸裂","没想到","彻底变天","超多","内幕曝光","吓坏","懵了","罕见一幕","重磅猛料"]

CHINA_ANCHORS=["中国","我国","国内","中共中央","中央政治局","国务院","全国人大","全国政协","财政部","教育部","人社部","公安部","应急管理部","央行","人民银行","发改委","国家统计局","商务部","市场监管总局","福建","江西","湖南","湖北","广东","广西","北京","上海","天津","重庆","海南","新疆","西藏","内蒙古","香港","澳门","台湾","人民币","A股","港股"]
FOREIGN_MARKERS=["俄罗斯","俄外交部","俄军","乌克兰","乌军","美国","美军","伊朗","以色列","也门","日本","韩国","英国","法国","德国","加拿大","特朗普","普京","泽连斯基","高市","欧盟","北约"]

LOW_VALUE=[
    ("新书",12),("研究会",10),("会员代表大会",10),("时装周",9),("圆满举办",8),
    ("宣传周",8),("宣传月",7),("论坛举行",6),("大会举行",5),("在京举行",4),
    ("启动仪式",5),("发布会",4),("限时优惠",7),("现金激励",7),("ETF",5),
    ("午评",4),("涨幅居前",4),("产品发布",3)
]

IMPORTANT={
    "china":{
        "习近平":10,"中共中央":9,"中央政治局":10,"国务院":9,"李强":6,"全国人大":7,
        "央行":8,"人民银行":8,"财政部":7,"发改委":7,"国家统计局":7,"商务部":6,"外交部":6,
        "降准":9,"降息":9,"利率":6,"人民币":6,"GDP":8,"CPI":6,"PPI":5,"外贸":6,
        "就业":6,"社保":5,"医保":5,"养老金":6,"房地产":5,"楼市":5,"教育":4,"高考":6,
        "台风":8,"地震":10,"暴雨":7,"洪涝":8,"事故":8,"伤亡":10,"应急":6,"出台":4,"新规":4
    },
    "world":{
        "特朗普":5,"美联储":8,"普京":6,"泽连斯基":5,"联合国":5,"战争":9,"冲突":8,
        "停火":9,"制裁":7,"核":7,"导弹":7,"袭击":8,"大选":7,"选举":6,"政变":9,
        "地震":8,"海啸":9,"油价":5,"关税":6,"利率":6
    },
    "finance":{
        "央行":9,"人民银行":9,"降准":10,"降息":10,"利率":8,"人民币":8,"财政部":7,
        "A股":6,"港股":6,"上证":5,"创业板":4,"科创板":4,"房地产":5,"外贸":6,"中国出口":5,
        "GDP":8,"CPI":6,"PPI":5,"美联储":7,"黄金":5,"原油":5,"暴跌":8,"暴涨":7
    },
    "tech":{
        "芯片":7,"半导体":7,"机器人":6,"航天":8,"卫星":7,"量子":8,"新能源":5,
        "突破":7,"首个":4,"首次":5,"国产":4,"出口管制":7,"制裁":6
    },
    "society":{
        "地震":10,"台风":9,"暴雨":8,"洪涝":9,"事故":9,"伤亡":10,"失联":9,"救援":7,
        "食品安全":7,"教育":5,"高考":7,"就业":6,"医保":6,"社保":5,"交通":4,"铁路":4,"紧急转移":10,"山体":7,"滑坡":8,"泥石流":9,"灾害":7
    },
    "ai":{
        "OpenAI":7,"DeepSeek":8,"Claude":6,"Gemini":6,"大模型":5,"发布":3,"开源":5,
        "AGI":8,"芯片":5,"训练":4,"推理":4,"智能体":5,"监管":6,"融资":4,"并购":5,
        "阿里":3,"腾讯":3,"字节":3,"华为":4,"智谱":4,"通义":4,"豆包":3
    }
}

UA={"User-Agent":"Mozilla/5.0 (compatible; DailyBriefBot/2.0; +https://github.com/my-coffeediy/my-coffeediy.github.io)"}

def clean(s):
    return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>","",s or ""))).strip()

def norm_text(s):
    return re.sub(r"[^\w\u4e00-\u9fff]","",clean(s).lower())

def rss_url(q):
    return f"https://news.google.com/rss/search?q={quote(q)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"

def google_topic_url(topic):
    return f"https://news.google.com/rss/headlines/section/topic/{topic}?hl=zh-CN&gl=CN&ceid=CN:zh-Hans"

def parse_source(title,fallback="新闻来源"):
    if " - " in title:
        a,b=title.rsplit(" - ",1)
        return a.strip(),b.strip()
    return title.strip(),fallback

def source_tier(source):
    s=(source or "").lower()
    if any(x.lower() in s for x in SOURCE_TIER_4): return 4
    if any(x.lower() in s for x in SOURCE_TIER_3): return 3
    if any(x.lower() in s for x in SOURCE_TIER_2): return 2
    return 1

def entry_image(e):
    for key in ("media_content","media_thumbnail"):
        arr=e.get(key) or []
        if isinstance(arr,list):
            for obj in arr[:3]:
                if isinstance(obj,dict):
                    u=obj.get("url","")
                    if u.startswith("http"): return u
    for enc in e.get("enclosures",[]) or []:
        u=enc.get("href") or enc.get("url") or ""
        if u.startswith("http") and str(enc.get("type","")).startswith("image/"):
            return u
    raw=e.get("summary","") or e.get("description","") or ""
    m=re.search(r'<img[^>]+src=["\']([^"\']+)',raw,re.I)
    return html.unescape(m.group(1)) if m and m.group(1).startswith("http") else ""

def entry_summary(e,title):
    raw=e.get("summary","") or e.get("description","") or ""
    text=clean(raw)
    if not text: return ""
    nt,nx=norm_text(title),norm_text(text)
    if not nx or (nt and (nx==nt or nx.startswith(nt) or nt.startswith(nx))):
        return ""
    if len(text)>150: text=text[:147].rstrip()+"…"
    return text

def og_image(url):
    if not url.startswith("http"): return ""
    try:
        r=requests.get(url,headers=UA,timeout=5,allow_redirects=True)
        if r.status_code>=400:return ""
        text=r.text[:450000]
        pats=[
            r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image(?::secure_url)?["\']',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']'
        ]
        for p in pats:
            m=re.search(p,text,re.I)
            if m:
                u=html.unescape(m.group(1).strip())
                if u.startswith("http"): return u
    except Exception:
        pass
    return ""

def image_from_xml_item(item):
    for el in item.iter():
        tag=el.tag.split("}")[-1].lower()
        if any(k in tag for k in ("image","thumbnail","content")):
            for attr in ("url","src","href"):
                u=el.attrib.get(attr,"")
                if u.startswith("http"): return html.unescape(u)
            txt=(el.text or "").strip()
            if txt.startswith("http"): return html.unescape(txt)
    desc=""
    for name in ("description","summary"):
        el=item.find(name)
        if el is not None and el.text:
            desc=el.text
            break
    if desc:
        m=re.search(r'<img[^>]+src=["\']([^"\']+)',desc,re.I)
        if m and m.group(1).startswith("http"):
            return html.unescape(m.group(1))
    return ""

def bing_image_thumbnail(title):
    try:
        q=quote(title[:72])
        url=f"https://www.bing.com/images/search?q={q}&setlang=zh-cn"
        r=requests.get(url,headers=UA,timeout=6)
        if r.status_code>=400:return ""
        text=html.unescape(r.text)
        for pat in (r'(https://ts[0-9]+\.mm\.bing\.net/th\?[^"<>\s]+)',r'(https://tse[0-9]+\.mm\.bing\.net/th[^"<>\s]+)'):
            m=re.search(pat,text,re.I)
            if m:
                u=html.unescape(m.group(1)).replace('\\u0026','&').replace('\\/','/')
                if u.startswith('http'):return u
    except Exception:
        pass
    return ""

def bing_html_thumbnail(title):
    try:
        q=quote('"'+title[:72]+'"')
        r=requests.get(f"https://www.bing.com/news/search?q={q}&setlang=zh-cn",headers=UA,timeout=6)
        if r.status_code>=400:return ""
        text=html.unescape(r.text)
        pats=[
            r'(https://th\.bing\.com/th\?id=[^"\'<> ]+)',
            r'"thumbnailUrl"\s*:\s*"(https:[^"\]+)',
            r'(https://[^"\'<> ]+\.mm\.bing\.net/[^"\'<> ]+)'
        ]
        for pat in pats:
            m=re.search(pat,text,re.I)
            if m:
                u=html.unescape(m.group(1)).replace('\\u0026','&').replace('\\/','/')
                if u.startswith('http'):return u
    except Exception:
        pass
    return ""

def bing_news_details(title):
    try:
        query=title[:80]
        url=f"https://www.bing.com/news/search?q={quote(query)}&format=rss&setlang=zh-cn"
        r=requests.get(url,headers=UA,timeout=6)
        if r.status_code>=400:return bing_html_thumbnail(title) or bing_image_thumbnail(title),""
        root=ET.fromstring(r.content)
        target=norm_text(title)
        best=None; best_ratio=0
        for item in root.findall(".//item")[:8]:
            t=clean(item.findtext("title") or "")
            ratio=SequenceMatcher(None,target,norm_text(t)).ratio() if t else 0
            if ratio>best_ratio:
                best_ratio=ratio; best=item
        if best is None or best_ratio<0.34:return bing_html_thumbnail(title) or bing_image_thumbnail(title),""
        img=image_from_xml_item(best)
        desc=clean(best.findtext("description") or "")
        if desc and len(desc)>150: desc=desc[:147].rstrip()+"…"
        if desc and norm_text(desc)==target: desc=""
        if not img:
            link=clean(best.findtext("link") or "")
            if link: img=og_image(link)
        if not img: img=bing_html_thumbnail(title) or bing_image_thumbnail(title)
        return img,desc
    except Exception:
        return bing_html_thumbnail(title) or bing_image_thumbnail(title),""

def recency_bonus(iso):
    try:
        dt=datetime.fromisoformat(iso)
        hours=max(0,(NOW-dt).total_seconds()/3600)
        if hours<=2:return 3
        if hours<=6:return 2
        if hours<=12:return 1
    except Exception:
        pass
    return 0

def importance_score(key,item):
    title=item["title"]
    score={"china":5,"world":4,"finance":3,"tech":2,"society":3,"ai":3}[key]
    score+=source_tier(item.get("source",""))*3
    score+=recency_bonus(item.get("published_at",""))
    if item.get("hot"):score+=3
    for kw,w in IMPORTANT[key].items():
        if kw.lower() in title.lower():
            score+=w
    for kw,p in LOW_VALUE:
        if kw.lower() in title.lower():
            score-=p
    if any(w in title for w in CLICKBAIT):
        score-=14
    if len(title)>55: score-=2
    if len(title)>85: score-=4
    return score

def feed_sources(key):
    out=[]
    if key in TOPIC_FEEDS:
        out.append((google_topic_url(TOPIC_FEEDS[key]),5))
    out.append((rss_url(QUERIES[key]),0))
    if key=="china":
        for q in ("site:news.cn when:1d","site:gov.cn when:1d","site:people.com.cn when:1d","site:cctv.com when:1d","site:chinanews.com.cn when:1d"):
            out.append((rss_url(q),7))
    elif key=="world":
        for q in ("site:reuters.com world when:1d","site:apnews.com world when:1d","site:bbc.com world when:1d"):
            out.append((rss_url(q),5))
    return out

def fetch_section(key):
    best={}
    for url,feed_bonus in feed_sources(key):
        feed=feedparser.parse(url)
        for e in feed.entries[:90]:
            title,source=parse_source(clean(e.get("title","")))
            if key=="china" and any(w in title for w in FOREIGN_MARKERS) and not any(w in title for w in CHINA_ANCHORS):
                continue
            norm=norm_text(title)
            if not title or not norm:continue
            pp=e.get("published_parsed")
            dt=datetime.fromtimestamp(time.mktime(pp),timezone.utc).astimezone(TZ) if pp else NOW
            tier=source_tier(source)
            hot=any(w in title for w in HOT)
            item={
                "category":{"china":"国内","world":"国际","finance":"财经","tech":"科技","society":"社会","ai":"AI"}[key],
                "title":title,"summary":entry_summary(e,title),"source":source,
                "published_at":dt.isoformat(),"url":e.get("link","") or "",
                "image_url":entry_image(e),"hot":hot,"verified":tier>=3,
                "_tier":tier,"_feed_bonus":feed_bonus
            }
            item["_score"]=importance_score(key,item)+feed_bonus
            prev=best.get(norm)
            if prev is None or (item["_score"],item["_tier"],item["published_at"])>(prev["_score"],prev["_tier"],prev["published_at"]):
                best[norm]=item
    rows=list(best.values())
    rows.sort(key=lambda x:(x["_score"],x["_tier"],x["published_at"]),reverse=True)
    clean_rows=[x for x in rows if not any(w in x["title"] for w in CLICKBAIT)]
    if len(clean_rows)>=LIMITS[key]: rows=clean_rows
    return rows[:LIMITS[key]]

def enrich_one(item):
    if item.get("image_url") and item.get("summary"):
        return
    img,desc=bing_news_details(item["title"])
    if not item.get("image_url") and img:
        item["image_url"]=img
    if not item.get("summary") and desc:
        item["summary"]=desc

def enrich_images_and_summaries(sections):
    items=[]
    for arr in sections.values():
        items.extend(arr[:8])
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs=[ex.submit(enrich_one,item) for item in items if not item.get("image_url") or not item.get("summary")]
        for f in as_completed(futs):
            try:f.result()
            except Exception:pass

def reason_for(key,title):
    t=title
    if any(k in t for k in ("地震","台风","暴雨","洪涝","事故","伤亡","失联")):
        return "直接关系人员安全、交通运行和应急处置，属于当天优先关注的信息。"
    if any(k in t for k in ("央行","人民银行","降准","降息","利率","人民币")):
        return "可能影响利率、人民币、楼市及资本市场预期。"
    if any(k in t for k in ("国务院","中共中央","中央政治局","全国人大","财政部","发改委")):
        return "属于国家层面的政策或治理信息，可能影响后续经济和民生安排。"
    if key=="world":
        return "属于全球头条级事件，可能影响国际局势、能源价格或全球市场。"
    if key=="finance":
        return "可能影响市场走势、行业预期或居民资产价格。"
    if key=="ai":
        return "属于AI模型、产品或监管的重要变化，可能影响行业竞争格局。"
    if key=="tech":
        return "涉及关键科技产业或重大技术进展，值得持续关注。"
    if key=="society":
        return "与国内民生和公共服务直接相关。"
    return "与国内政策、经济或民生直接相关。"

def pack_top(key,item):
    return {
        "title":item["title"],
        "why_it_matters":reason_for(key,item["title"]),
        "category":item["category"],
        "source":item["source"],
        "published_at":item["published_at"],
        "url":item["url"],
        "image_url":item.get("image_url","")
    }

def choose_unique(candidates,used):
    for item in candidates:
        n=norm_text(item["title"])
        if n not in used:
            used.add(n)
            return item
    return None

TOP_BLOCK=["新书","研究会","会员代表大会","时装周","圆满举办","宣传周","宣传月","启动仪式","限时优惠","现金激励","ETF","减持","质押","保荐","违规被罚","实干样本","品牌活动","视频","研讨会","交流活动","道歉","市场汇价","开学典礼","体育","比赛","白鹭","早报","大赛","决赛","启幕","执法检查组","本周","日程","周历"]
TOP_MAJOR={
    "china":["中共中央","中央政治局","国务院","全国人大","全国政协","央行","人民银行","财政部","发改委","国家统计局","商务部","外交部","国防部","降准","降息","人民币","GDP","CPI","PPI","外贸","就业","社保","医保","养老金","房地产","楼市","高考","台风","地震","暴雨","洪涝","事故","伤亡","应急","国家主席","总书记","教育部","人社部","公安部","市场监管总局"],
    "world":["战争","冲突","停火","制裁","大选","选举","美联储","特朗普","普京","泽连斯基","联合国","北约","地震","海啸","袭击","导弹","关税","油价","核武","政变"],
    "finance":["央行","人民银行","降准","降息","利率","人民币","财政部","A股","港股","GDP","CPI","PPI","外贸","出口","美联储","黄金","原油","暴跌","暴涨"],
    "tech":["芯片","半导体","机器人","航天","卫星","量子","突破","国产","出口管制","制裁"],
    "society":["地震","台风","暴雨","洪涝","事故","伤亡","失联","救援","食品安全","高考","就业","医保","社保"],
    "ai":["OpenAI","DeepSeek","Claude","Gemini","大模型","AGI","开源","智能体","监管","芯片","融资","并购","智谱","通义","豆包"]
}

def is_top_candidate(key,item,strict=True):
    title=item["title"]
    if any(w in title for w in CLICKBAIT+TOP_BLOCK):return False
    major=any(w.lower() in title.lower() for w in TOP_MAJOR[key])
    if key=="world":
        if item.get("_tier",1)<2 and not (item.get("_feed_bonus",0)>=5 and major):return False
    else:
        if item.get("_tier",1)<2:return False
    if key=="ai" and item.get("_tier",1)<3:return False
    if strict and not major:return False
    return True

def build_top5(sections):
    used=set(); chosen=[]
    def add_best(key,strict=True):
        for x in sections[key]:
            n=norm_text(x["title"])
            if n in used:continue
            if is_top_candidate(key,x,strict):
                used.add(n); chosen.append((key,x)); return True
        return False
    for _ in range(2):
        if not add_best("china",True):add_best("china",False)
    if not add_best("world",True):add_best("world",False)
    block=[]
    for k in ("society","finance"):
        for x in sections[k]:
            if is_top_candidate(k,x,True):block.append((x["_score"],k,x))
    block.sort(key=lambda z:(z[0],z[2]["_tier"],z[2]["published_at"]),reverse=True)
    for _,k,x in block:
        n=norm_text(x["title"])
        if n not in used:
            used.add(n);chosen.append((k,x));break
    block=[]
    for k in ("ai","tech","finance","society"):
        for x in sections[k]:
            if is_top_candidate(k,x,True):
                bonus=2 if k=="ai" else (1 if k=="tech" else 0)
                block.append((x["_score"]+bonus,k,x))
    block.sort(key=lambda z:(z[0],z[2]["_tier"],z[2]["published_at"]),reverse=True)
    for _,k,x in block:
        n=norm_text(x["title"])
        if n not in used:
            used.add(n);chosen.append((k,x));break
    if len(chosen)<5:
        pool=[]
        for k in ("china","world","society","finance","tech","ai"):
            for x in sections[k]:
                if is_top_candidate(k,x,False):pool.append((x["_score"],k,x))
        pool.sort(key=lambda z:(z[0],z[2]["_tier"],z[2]["published_at"]),reverse=True)
        for _,k,x in pool:
            n=norm_text(x["title"])
            if n in used:continue
            used.add(n);chosen.append((k,x))
            if len(chosen)>=5:break
    return [pack_top(k,x) for k,x in chosen[:5]]

MARKETS=[
    ("黄金","GC=F","USD/oz"),
    ("白银","SI=F","USD/oz"),
    ("WTI原油","CL=F","USD/bbl"),
    ("布伦特原油","BZ=F","USD/bbl"),
    ("天然气","NG=F","USD/MMBtu"),
    ("铜","HG=F","USD/lb")
]

def fetch_markets():
    if yf is None:
        return [{"name":n,"symbol":s,"price":"--","unit":u,"change_pct":0,"note":"行情模块暂不可用"} for n,s,u in MARKETS]
    out=[]
    for n,s,u in MARKETS:
        try:
            closes=yf.Ticker(s).history(period="5d",interval="1d",auto_adjust=False)["Close"].dropna()
            if len(closes)<2:raise RuntimeError
            p,prev=float(closes.iloc[-1]),float(closes.iloc[-2])
            out.append({
                "name":n,"symbol":s,"price":f"{p:.2f}","unit":u,
                "change_pct":round((p/prev-1)*100,2),
                "note":"Yahoo Finance 延迟行情"
            })
        except Exception:
            out.append({"name":n,"symbol":s,"price":"--","unit":u,"change_pct":0,"note":"暂未取到行情"})
    return out

def main():
    sections={k:fetch_section(k) for k in QUERIES}
    enrich_images_and_summaries(sections)
    top5=build_top5(sections)
    payload={
        "updated_at":NOW.isoformat(),
        "markets_updated_at":NOW.isoformat(),
        "top5":top5,
        "sections":sections,
        "markets":fetch_markets()
    }
    for items in sections.values():
        for item in items:
            item.pop("_tier",None)
            item.pop("_score",None)
            item.pop("_feed_bonus",None)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print("updated",OUT)

if __name__=="__main__":
    main()
