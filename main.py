import os, time, random, datetime, asyncio
from typing import List, Optional
from fastapi import FastAPI, Query, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_settings import BaseSettings

try:
    import httpx
except Exception:
    httpx = None

# ---------- Settings ----------
class Settings(BaseSettings):
    CORS_ORIGINS: str = "*"
    PORT: int = 8000
    ALERTS_ENABLED: bool = True
    ALERTS_MIN_SCORE: float = 100.0
    DISCORD_WEBHOOK: str = ""
    ALERTS_SECRET: str = "change-me"
    REDIS_URL: str = ""  # optional

    class Config:
        env_file = ".env"

settings = Settings()

# ---------- App ----------
app = FastAPI(title="POE2 Flips API", version="0.12.0",
              description="Stub API + server-side Discord alerts.")

origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Redis (optional) ----------
_redis_client = None
if settings.REDIS_URL:
    try:
        import redis
        _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        _redis_client.ping()
    except Exception as e:
        _redis_client = None
        print("Redis disabled:", e)

def sent_key_for_today()->str:
    d = datetime.datetime.utcnow().date()
    return f"sent:{d.isoformat()}"

def mark_sent(item_id: str):
    # keep dedupe per-day
    if _redis_client:
        _redis_client.hset(sent_key_for_today(), item_id, 1)
        _redis_client.expire(sent_key_for_today(), 60*60*36)  # 36h
    else:
        _inmem_sent[sent_key_for_today()][item_id] = 1

def was_sent(item_id: str)->bool:
    if _redis_client:
        return _redis_client.hexists(sent_key_for_today(), item_id)
    return item_id in _inmem_sent.setdefault(sent_key_for_today(), {})

_inmem_sent = {}

# ---------- Models ----------
class Listing(BaseModel):
    id: str
    name: str
    slot: str
    price_chaos: float
    market_chaos: float
    seller: str
    listed_ago_min: int
    ilvl: Optional[int] = None
    url: Optional[str] = None

class ScoredItem(BaseModel):
    listing: Listing
    score: float

class DealsResponse(BaseModel):
    items: List[ScoredItem]

class Health(BaseModel):
    status: str
    time: float

class HistoryResponse(BaseModel):
    id: str
    points: list[float]

class AlertsStatus(BaseModel):
    enabled: bool
    min_score: float
    webhook_set: bool
    sent_today: int

# ---------- Scoring ----------
def margin_pct(market: float, price: float)->float:
    if not market or market <= 0: return 0.0
    return max(0.0, (market - price) / market * 100.0)

def compute_score(l: Listing, w_margin=100.0, w_spread=0.5, w_vel=20.0)->float:
    m = margin_pct(l.market_chaos, l.price_chaos)
    spread = max(0.0, l.market_chaos - l.price_chaos)
    vel = w_vel if l.listed_ago_min <= 5 else (w_vel-10 if l.listed_ago_min <= 15 else (w_vel-15 if l.listed_ago_min<=60 else 0))
    return m*w_margin + spread*w_spread + max(0.0, vel)

# ---------- Mock data ----------
MOCK_NAMES = [
    ("Ritual Fang Axe of the Bear","weapon"), ("Emerald Loop Ring","ring"),
    ("Dragonheart Scale Vest","chest"), ("Zephyr Touch Gloves","gloves"),
    ("Viper Talisman Amulet","amulet"), ("Gale Stride Boots","boots"),
    ("Quartz Flask of Light","flask"), ("Crown of Thorns","helmet"),
    ("Volcanic Fissure (20/20)","gem")
]

def mock_listing(i:int)->Listing:
    name, slot = random.choice(MOCK_NAMES)
    market = round(random.uniform(10, 140), 2)
    price = round(max(1.0, market - random.uniform(1, market*0.7)), 2)
    return Listing(
        id=f"m{i}-{int(time.time()*1000)}",
        name=name, slot=slot,
        price_chaos=price, market_chaos=market,
        seller=random.choice(["ExileHub","ChaosCorner","MapDaddy","GemVault","HarbingerJoe"]),
        listed_ago_min=random.randint(1, 180),
        ilvl=random.randint(60, 86),
        url="#"
    )

def mock_deals(n:int)->List[ScoredItem]:
    arr = [ScoredItem(listing=mock_listing(i), score=0.0) for i in range(n)]
    for s in arr: s.score = compute_score(s.listing)
    arr.sort(key=lambda x: x.score, reverse=True)
    return arr

# ---------- Routes ----------
@app.get("/health", response_model=Health)
def health():
    return Health(status="ok", time=time.time())

@app.get("/deals", response_model=DealsResponse)
def deals(limit: int = Query(100, ge=1, le=500)):
    items = mock_deals(limit)
    return DealsResponse(items=items)

@app.get("/history", response_model=HistoryResponse)
def history(id: str):
    base = random.uniform(10, 120)
    pts = [round(max(1.0, base + random.uniform(-0.12,0.12)*base),2) for _ in range(60)]
    return HistoryResponse(id=id, points=pts)

# ---------- Alerts ----------
async def send_discord(content: str):
    if not settings.DISCORD_WEBHOOK or httpx is None:
        return
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            await client.post(settings.DISCORD_WEBHOOK, json={"content": content})
        except Exception as e:
            print("Discord send failed:", e)

def check_secret(x_secret: Optional[str]):
    if (settings.ALERTS_SECRET or "") and x_secret != settings.ALERTS_SECRET:
        raise HTTPException(status_code=401, detail="Invalid secret")

@app.get("/alerts/status", response_model=AlertsStatus)
def alerts_status():
    key = sent_key_for_today()
    sent_count = 0
    if _redis_client:
        sent_count = _redis_client.hlen(key) or 0
    else:
        sent_count = len(_inmem_sent.get(key, {}))
    return AlertsStatus(
        enabled = settings.ALERTS_ENABLED,
        min_score = float(settings.ALERTS_MIN_SCORE),
        webhook_set = bool(settings.DISCORD_WEBHOOK),
        sent_today = sent_count
    )

@app.post("/alerts/enable")
def alerts_enable(x_alerts_secret: Optional[str] = Header(None, convert_underscores=False)):
    check_secret(x_alerts_secret)
    settings.ALERTS_ENABLED = True
    return {"ok": True, "enabled": True}

@app.post("/alerts/disable")
def alerts_disable(x_alerts_secret: Optional[str] = Header(None, convert_underscores=False)):
    check_secret(x_alerts_secret)
    settings.ALERTS_ENABLED = False
    return {"ok": True, "enabled": False}

@app.post("/alerts/scan")
async def alerts_scan(limit: int = Query(200, ge=1, le=500)):
    if not settings.ALERTS_ENABLED:
        return {"ok": True, "sent": 0, "reason": "disabled"}
    if not settings.DISCORD_WEBHOOK:
        return {"ok": True, "sent": 0, "reason": "no_webhook"}
    items = mock_deals(limit)
    min_score = float(settings.ALERTS_MIN_SCORE or 0)
    to_send = []
    for s in items:
        it = s.listing
        if s.score >= min_score and not was_sent(it.id):
            to_send.append((it, s.score))
        if len(to_send) >= 5:
            break
    for it, sc in to_send:
        msg = f"💥 **{it.name}** | Score **{sc:.1f}** | Margin **{margin_pct(it.market_chaos,it.price_chaos):.1f}%** | Spread **{(it.market_chaos-it.price_chaos):.1f}c** | Price **{it.price_chaos}c** | Market **{it.market_chaos}c**"
        await send_discord(msg)
        mark_sent(it.id)
    return {"ok": True, "sent": len(to_send)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)
