import os, asyncio, math, random, time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    CORS_ORIGINS: str = "*"
    PORT: int = 8000
    class Config:
        env_file = ".env"

settings = Settings()

app = FastAPI(title="POE2 Flips API", version="0.1.0",
              description="Stub API for the PoE2 flipping dashboard. Replace fetcher with real source.")

origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------- Models -------------------
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

# ----------------- Score formula -----------------
def margin_pct(market: float, price: float)->float:
    if not market or market <= 0: return 0.0
    return max(0.0, (market - price) / market * 100.0)

def compute_score(listing: Listing, w_margin=100.0, w_spread=0.5, w_vel=20.0)->float:
    m = margin_pct(listing.market_chaos, listing.price_chaos)
    spread = max(0.0, listing.market_chaos - listing.price_chaos)
    vel = w_vel if listing.listed_ago_min <= 5 else (w_vel-10 if listing.listed_ago_min <= 15 else (w_vel-15 if listing.listed_ago_min<=60 else 0))
    return m*w_margin + spread*w_spread + max(0.0, vel)

# ------------------- Mock store -------------------
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
        name=name,
        slot=slot,
        price_chaos=price,
        market_chaos=market,
        seller=random.choice(["ExileHub","ChaosCorner","MapDaddy","GemVault","HarbingerJoe"]),
        listed_ago_min=random.randint(1, 180),
        ilvl=random.randint(60, 86),
        url="#"
    )

def mock_deals(n:int)->List[ScoredItem]:
    out = []
    for i in range(n):
        l = mock_listing(i)
        out.append(ScoredItem(listing=l, score=compute_score(l)))
    # sort by score desc
    out.sort(key=lambda x: x.score, reverse=True)
    return out

# ------------------- Routes -------------------
@app.get("/health", response_model=Health)
async def health():
    return Health(status="ok", time=time.time())

@app.get("/deals", response_model=DealsResponse)
async def deals(limit: int = Query(100, ge=1, le=500)):
    # TODO: replace with cached fetcher results
    items = mock_deals(limit)
    return DealsResponse(items=items)

class HistoryResponse(BaseModel):
    id: str
    points: List[float]

@app.get("/history", response_model=HistoryResponse)
async def history(id: str):
    base = random.uniform(10, 120)
    pts = [round(max(1.0, base + random.uniform(-0.12,0.12)*base),2) for _ in range(60)]
    return HistoryResponse(id=id, points=pts)

# ---------- Development entry ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)
