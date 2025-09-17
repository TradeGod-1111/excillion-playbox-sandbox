import csv, os, statistics as stats, random
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data" / "ohlc_sample.csv"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True, parents=True)

def ensure_data():
    """Create minimal OHLC CSV if missing (random walk)."""
    DATA.parent.mkdir(parents=True, exist_ok=True)
    if DATA.exists():
        return
    price = 100.0
    rows = []
    for i in range(120):
        change = random.uniform(-0.8, 0.8)
        o = price
        c = max(1.0, o + change)
        h = max(o, c) + random.uniform(0, 0.5)
        l = min(o, c) - random.uniform(0, 0.5)
        v = random.randint(100, 500)
        rows.append({
            "timestamp": f"T{i:03d}",
            "open": round(o, 4), "high": round(h, 4),
            "low": round(l, 4), "close": round(c, 4),
            "volume": v
        })
        price = c
    with open(DATA, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["timestamp","open","high","low","close","volume"])
        w.writeheader(); w.writerows(rows)

def load_rows(path):
    rows=[]
    with open(path,newline="") as f:
        r=csv.DictReader(f)
        for row in r:
            row={k: (float(v) if k!="timestamp" else v) for k,v in row.items()}
            rows.append(row)
    return rows

def sma(vals, n):
    q=[]; out=[]
    for v in vals:
        q.append(v)
        if len(q)>n: q.pop(0)
        out.append(stats.mean(q) if len(q)==n else None)
    return out

def backtest(rows, fast=10, slow=20):
    closes=[r["close"] for r in rows]
    f=sma(closes, fast); s=sma(closes, slow)
    equity=100000  # cents
    pos=0; entry=0.0
    trades=[]
    for i in range(1, len(rows)):
        if s[i] is None or f[i-1] is None or s[i-1] is None: 
            continue
        cross_up = f[i-1] < s[i-1] and f[i] >= s[i]
        cross_dn = f[i-1] > s[i-1] and f[i] <= s[i]
        price = closes[i]
        if pos==0 and cross_up:
            pos=1; entry=price
            trades.append({"t": rows[i]["timestamp"], "action":"BUY", "price":price})
        elif pos==1 and cross_dn:
            pnl = (price - entry)
            equity += int(pnl*100)
            pos=0
            trades.append({"t": rows[i]["timestamp"], "action":"SELL", "price":price, "pnl":pnl})
    if pos==1:
        price=closes[-1]
        pnl=(price-entry); equity += int(pnl*100)
        trades.append({"t": rows[-1]["timestamp"], "action":"SELL_EOD", "price":price, "pnl":pnl})

    wins=[t["pnl"] for t in trades if "pnl" in t and t["pnl"]>0]
    losses=[t["pnl"] for t in trades if "pnl" in t and t["pnl"]<=0]
    report = {
        "trades": len([t for t in trades if "pnl" in t]),
        "win_rate": round(100*len(wins)/max(1,len(wins)+len(losses)),2),
        "avg_win": round(sum(wins)/max(1,len(wins)),4),
        "avg_loss": round(sum(losses)/max(1,len(losses)),4),
        "ending_equity": equity/100
    }
    with open(OUT/"report.txt","w") as f: f.write(str(report)+"\n")
    with open(OUT/"trades.csv","w",newline="") as f:
        w=csv.DictWriter(f, fieldnames=["t","action","price","pnl"])
        w.writeheader(); [w.writerow(t) for t in trades]

if __name__=="__main__":
    ensure_data()
    rows=load_rows(DATA)
    backtest(rows)
    print("ok - wrote research/out/report.txt and trades.csv")
