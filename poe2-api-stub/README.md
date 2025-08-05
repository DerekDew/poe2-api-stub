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
Visit http://localhost:8000/docs for OpenAPI.

## Deploy options
### Heroku
```
heroku create poe2-api-stub
heroku config:set CORS_ORIGINS=https://YOUR_NETLIFY_SITE.netlify.app
git push heroku main
```
### Render.com
- New Web Service → Python → start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Add env var: `CORS_ORIGINS=https://YOUR_NETLIFY_SITE.netlify.app`

### Docker
```
docker build -t poe2-api .
docker run -p 8000:8000 poe2-api
```
