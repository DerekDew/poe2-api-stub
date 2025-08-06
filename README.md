# PoE2 Flips API — v12 (Server Alerts)

FastAPI backend with:
- `/deals`, `/history`, `/health` (stub data)
- **Server-side Discord alerts** with toggle endpoints
- Optional Redis for daily de-dupe
- Compatible with Render Web Service + Render Cron Job

## Env
Copy `.env.example` to `.env` and set:
- `ALERTS_ENABLED=true|false`
- `DISCORD_WEBHOOK=<discord url>`
- `ALERTS_MIN_SCORE=100`
- `ALERTS_SECRET=<long random secret>`
- `REDIS_URL=redis://...` (optional, otherwise in-memory)

## Endpoints
- `GET /health`
- `GET /deals?limit=100`
- `GET /history?id=...`
- `GET /alerts/status`
- `POST /alerts/enable` (header `X-Alerts-Secret: <secret>`)
- `POST /alerts/disable` (header `X-Alerts-Secret: <secret>`)
- `POST /alerts/scan?limit=200`  → runs a scan and sends up to 5 alerts

## Render (free) with cron
1) Deploy as a **Web Service** (Python).  
   Build: `pip install -r requirements.txt`  
   Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
2) Set env vars above (especially `DISCORD_WEBHOOK`).
3) Create a **Cron Job** in Render:
   - Runtime: Docker (use this repo; the Dockerfile already includes `curl`)
   - Schedule: `*/2 * * * *` (every 2 minutes)
   - Command: `curl -fsS https://YOUR-SERVICE.onrender.com/alerts/scan`
4) To disable: set `ALERTS_ENABLED=false` **or** call `/alerts/disable` with the secret **or** pause the Cron Job.

