import json
from pathlib import Path

import yfinance as yf

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "news" / "data" / "news.json"

TROY_OUNCE_GRAMS = 31.1034768
LB_PER_KG = 2.20462262185

# factor means: USD source price * USD/CNY * factor = RMB display price
MARKET_RULES = {
    "GC=F": {"name": "黄金", "unit": "元/克", "factor": 1 / TROY_OUNCE_GRAMS, "digits": 2},
    "SI=F": {"name": "白银", "unit": "元/千克", "factor": 1000 / TROY_OUNCE_GRAMS, "digits": 2},
    "CL=F": {"name": "WTI原油", "unit": "元/桶", "factor": 1.0, "digits": 2},
    "BZ=F": {"name": "布伦特原油", "unit": "元/桶", "factor": 1.0, "digits": 2},
    "NG=F": {"name": "天然气", "unit": "元/百万英热单位", "factor": 1.0, "digits": 2},
    "HG=F": {"name": "铜", "unit": "元/千克", "factor": LB_PER_KG, "digits": 2},
}


def closes(symbol):
    hist = yf.Ticker(symbol).history(period="5d", interval="1d", auto_adjust=False)
    series = hist["Close"].dropna()
    if len(series) < 2:
        raise RuntimeError(f"not enough market data for {symbol}")
    return float(series.iloc[-1]), float(series.iloc[-2])


def fmt(value, digits):
    return f"{value:.{digits}f}"


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))

    fx_now, fx_prev = closes("CNY=X")  # USD/CNY
    localized = []

    for item in data.get("markets", []):
        symbol = item.get("symbol", "")
        rule = MARKET_RULES.get(symbol)
        if not rule:
            localized.append(item)
            continue

        try:
            usd_now, usd_prev = closes(symbol)
        except Exception:
            # update_news.py has already fetched the same market. If a second request
            # fails, reuse that current quote and reconstruct the previous quote from
            # its percentage change rather than dropping the RMB display entirely.
            try:
                usd_now = float(item.get("price"))
                old_pct = float(item.get("change_pct") or 0)
                usd_prev = usd_now / (1 + old_pct / 100) if old_pct > -100 else usd_now
            except Exception:
                item.update({
                    "price": "--",
                    "previous_price": "--",
                    "unit": rule["unit"],
                    "currency": "CNY",
                    "change_pct": 0,
                    "note": "人民币行情暂未取到",
                })
                localized.append(item)
                continue

        current_cny = usd_now * fx_now * rule["factor"]
        previous_cny = usd_prev * fx_prev * rule["factor"]
        change_pct = (current_cny / previous_cny - 1) * 100 if previous_cny else 0

        item.update({
            "name": rule["name"],
            "price": fmt(current_cny, rule["digits"]),
            "previous_price": fmt(previous_cny, rule["digits"]),
            "unit": rule["unit"],
            "currency": "CNY",
            "change_pct": round(change_pct, 2),
            "note": f"人民币换算 · 美元兑人民币 {fx_now:.4f} · Yahoo Finance 延迟行情",
        })
        localized.append(item)

    data["markets"] = localized
    data["market_currency"] = "CNY"
    data["usd_cny"] = round(fx_now, 4)
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"localized {len(localized)} market quotes to RMB; USD/CNY={fx_now:.4f}")


if __name__ == "__main__":
    main()
