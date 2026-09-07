import json,re,html,time
from pathlib import Path
from datetime import datetime,timezone,timedelta
from urllib.parse import quote
import xml.etree.ElementTree as ET
import feedparser,requests
try:
    import yfinance as yf
except Exception:
    yf=None

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"news"/"data"/"news.json"
TZ=timezone(timedelta(hours=8)); NOW=datetime.now(TZ)
QUERIES={
"china":'中国 (政策 OR 经济 OR 民生 OR 改革 OR 发展) when:1d -时装 -新书 -研究会 -发布会',
"world":'(美国 OR 欧洲 OR 俄罗斯 OR 乌克兰 OR 中东 OR 联合国) (战争 OR 冲突 OR 外交 OR 选举 OR 经济 OR 制裁 OR 停火) when:1d',
"finance":'(中国 财经 OR A股 OR 港股 OR 人民币 OR 央行 OR 房地产) when:1d',
"tech":'(科技 OR 芯片 OR 机器人 OR 新能源 OR 科研) 中国 when:1d',
"society":'(社会 OR 民生 OR 教育 OR 就业 OR 医疗 OR 灾害 OR 交通) 中国 when:1d -明星 -娱乐',
"ai":'(人工智能 OR AI OR OpenAI OR DeepSeek OR Claude OR Gemini OR 大模型) when:1d'}
LIMITS={"china":12,"world":8,"finance":10,"tech":10,"society":10,"ai":10}
TRUST=["新华社","新华网","央视新闻","央视网","人民日报","中国政府网","中国新闻网","中新网","中国经济网","央广网","光明网","经济日报","财联社","第一财经","澎湃新闻","路透","Reuters","AP","美联社","BBC"]
SECONDARY=["界面新闻","证券时报","上海证券报","中国证券报","中青在线","南方日报","新京报"]
HOT=["突发","地震","台风","暴雨","战争","冲突","停火","制裁","大选","暴跌","暴涨","危机","事故","死亡"]
CLICKBAIT=["气炸","都得完蛋","再打下去","惊人","炸裂","没想到","彻底变天","超多","内幕曝光"]
UA={"User-Agent":"Mozilla/5.0 (compatible; DailyBriefBot/1.2)"}

def clean(s):
    return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>","",s or ""))).strip()

def rss_url(q):
    return f"https://news.google.com/rss/search?q={quote(q)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"

def parse_source(title,fallback="新闻来源"):
    if " - " in title:
        a,b=title.rsplit(" - ",1); return a.strip(),b.strip()
    return title.strip(),fallback

def source_tier(source):
    s=source.lower()
    if any(x.lower() in s for x in TRUST): return 2
    if any(x.lower() in s for x in SECONDARY): return 1
    return 0

def entry_image(e):
    for key in ("media_content","media_thumbnail"):
        arr=e.get(key) or []
        if arr and isinstance(arr,list):
            u=(arr[0] or {}).get("url","")
            if u.startswith("http"): return u
    for enc in e.get("enclosures",[]) or []:
        u=enc.get("href") or enc.get("url") or ""
        if u.startswith("http") and str(enc.get("type","")).startswith("image/"): return u
    raw=e.get("summary","") or e.get("description","") or ""
    m=re.search(r'<img[^>]+src=["\']([^"\']+)',raw,re.I)
    return html.unescape(m.group(1)) if m and m.group(1).startswith("http") else ""

def og_image(url):
    if not url.startswith("http"): return ""
    try:
        r=requests.get(url,headers=UA,timeout=6,allow_redirects=True)
        if r.status_code>=400: return ""
        text=r.text[:500000]
        pats=[r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)']
        for p in pats:
            m=re.search(p,text,re.I)
            if m:
                u=html.unescape(m.group(1).strip())
                if u.startswith("http"): return u
    except Exception: pass
    return ""

def bing_image(title):
    # Bing News RSS 常带 News:Image；按完整标题检索，只作为原报道主图的补充来源。
    try:
        q=quote('"'+title[:160]+'"')
        url=f"https://www.bing.com/news/search?q={q}&format=rss&setlang=zh-cn"
        r=requests.get(url,headers=UA,timeout=7)
        if r.status_code>=400:return ""
        root=ET.fromstring(r.content)
        item=root.find('.//item')
        if item is None:return ""
        for el in item.iter():
            if el.tag.split('}')[-1].lower()=='image' and el.text:
                u=html.unescape(el.text.strip())
                if u.startswith('http'):return u
    except Exception:pass
    return ""

def fetch_section(key):
    feed=feedparser.parse(rss_url(QUERIES[key])); rows=[]; seen=set()
    for e in feed.entries[:80]:
        title,source=parse_source(clean(e.get("title","")))
        norm=re.sub(r"[^\w\u4e00-\u9fff]","",title.lower())
        if not title or norm in seen: continue
        seen.add(norm)
        pp=e.get("published_parsed")
        dt=datetime.fromtimestamp(time.mktime(pp),timezone.utc).astimezone(TZ) if pp else NOW
        tier=source_tier(source); hot=any(w in title for w in HOT); clickbait=any(w in title for w in CLICKBAIT)
        rows.append({"category":{"china":"国内","world":"国际","finance":"财经","tech":"科技","society":"社会","ai":"AI"}[key],"title":title,"summary":"","source":source,"published_at":dt.isoformat(),"url":e.get("link","") or "","image_url":entry_image(e),"hot":hot,"verified":tier==2,"source_tier":tier,"clickbait":clickbait})
    rows.sort(key=lambda x:(x["source_tier"],x["hot"],not x["clickbait"],x["published_at"]),reverse=True)
    rows=rows[:LIMITS[key]]
    for item in rows[:5]:
        if not item["image_url"] and item["url"]: item["image_url"]=og_image(item["url"])
        if not item["image_url"]: item["image_url"]=bing_image(item["title"])
        item.pop("clickbait",None)
    for item in rows[5:]: item.pop("clickbait",None)
    return rows

def top_score(k,item):
    base={"china":8,"world":6,"finance":4,"ai":3,"tech":2,"society":2}[k]
    tier=item.get("source_tier",0)
    return base+tier*6+(2 if item.get("hot") else 0)

def build_top5(sections):
    reasons={"china":"与国内政策、经济或民生直接相关。","world":"属于全球头条级事件，可能影响国际局势或市场。","finance":"可能影响市场、汇率、行业或宏观预期。","ai":"AI行业的重要模型、产品或政策变化。","tech":"值得关注的科技产业变化。","society":"影响较广的国内社会民生事件。"}
    pool=[]
    for k,items in sections.items():
        for item in items:
            if item.get("source_tier",0)>0: pool.append((top_score(k,item),k,item))
    if len(pool)<5:
        for k,items in sections.items():
            for item in items:
                if item.get("source_tier",0)==0: pool.append((top_score(k,item)-5,k,item))
    pool.sort(key=lambda x:(x[0],x[2]["published_at"]),reverse=True)
    out=[]; used=set(); world_count=0
    for _,k,item in pool:
        norm=re.sub(r"[^\w\u4e00-\u9fff]","",item["title"].lower())
        if norm in used: continue
        if k=="world" and world_count>=2: continue
        used.add(norm); world_count+=1 if k=="world" else 0
        out.append({"title":item["title"],"why_it_matters":reasons[k],"category":item["category"],"source":item["source"],"published_at":item["published_at"],"url":item["url"],"image_url":item.get("image_url","")})
        if len(out)>=5: break
    return out

MARKETS=[("黄金","GC=F","USD/oz"),("白银","SI=F","USD/oz"),("WTI原油","CL=F","USD/bbl"),("布伦特原油","BZ=F","USD/bbl"),("天然气","NG=F","USD/MMBtu"),("铜","HG=F","USD/lb")]
def fetch_markets():
    if yf is None:return [{"name":n,"symbol":s,"price":"--","unit":u,"change_pct":0,"note":"行情模块暂不可用"} for n,s,u in MARKETS]
    out=[]
    for n,s,u in MARKETS:
        try:
            closes=yf.Ticker(s).history(period="5d",interval="1d",auto_adjust=False)["Close"].dropna()
            if len(closes)<2: raise RuntimeError
            p,prev=float(closes.iloc[-1]),float(closes.iloc[-2]); out.append({"name":n,"symbol":s,"price":f"{p:.2f}","unit":u,"change_pct":round((p/prev-1)*100,2),"note":"Yahoo Finance 延迟行情"})
        except Exception: out.append({"name":n,"symbol":s,"price":"--","unit":u,"change_pct":0,"note":"暂未取到行情"})
    return out

def main():
    sections={k:fetch_section(k) for k in QUERIES}; payload={"updated_at":NOW.isoformat(),"markets_updated_at":NOW.isoformat(),"top5":build_top5(sections),"sections":sections,"markets":fetch_markets()}
    for items in sections.values():
        for item in items: item.pop("source_tier",None)
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8"); print("updated",OUT)
if __name__=="__main__":main()
