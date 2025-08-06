# PoE2 Flips API (Stub)

FastAPI backend stub for the PoE2 flipping dashboard.

## Endpoints
- `GET /health` → `{ "status": "ok", "time": <epoch> }`
- `GET /deals?limit=100` → `{ "items": [ { "listing": {...}, "score": <float> } ] }`
- `GET /history?id=<listing_id>` → `{ "id": "...", "points": [float...] }` (mock 60 pts)

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```
Open http://localhost:8000/docs for the OpenAPI UI.

## Deploy on Render (free)
- Environment: **Python 3**
- Build command:
```
pip install -r requirements.txt
```
- Start command:
```
uvicorn main:app --host 0.0.0.0 --port $PORT
```
- Env var:
```
CORS_ORIGINS=https://YOUR-NETLIFY-SITE.netlify.app
```
