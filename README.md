# API Request Inspector & Replay Tool

A local debugging proxy for support engineers who spend their day staring at
failed API calls. Instead of pasting a curl command into a chat and guessing
why a customer's integration is broken, send the request through the
inspector: it forwards the call to the real API, captures the full
request/response pair, and translates the raw status code and headers into a
plain-language diagnosis — what failed, why, and what to check next. Every
call is stored, so you can scroll back through a session's history, and any
failed request can be tweaked and replayed in place without leaving the tool.

## Architecture

```
┌────────┐     ┌──────────────┐     ┌───────┐     ┌───────────┐
│ Client │────▶│  POST /proxy │────▶│ httpx │────▶│  Real API │
└────────┘     └──────────────┘     └───────┘     └───────────┘
    ▲                  │                                │
    │                  ▼                                │
    │           ┌──────────────┐                        │
    │           │  analyzer.py │◀───────────────────────┘
    │           └──────────────┘
    │                  │
    │                  ▼
    │           ┌──────────────┐
    │           │    SQLite    │
    │           └──────────────┘
    │                  │
    │                  ▼
    │           ┌──────────────┐
    └───────────│ WebSocket /ws│
     live push   └──────────────┘
```

The frontend also polls `GET /requests` on load and whenever the filter
changes, then stays in sync via the WebSocket for anything captured after
that.

## Setup

```bash
cd backend && python -m venv venv && venv/Scripts/pip install -r requirements.txt && venv/Scripts/uvicorn main:app --reload
```

```bash
cd frontend && npm install && npm run dev
```

The backend defaults to `http://localhost:8000`, the frontend dev server to
`http://localhost:5173`. Copy `.env.example` to `.env` in `backend/` if you
want to change the DB path, host, port, or default timeout. If your backend
runs somewhere other than `localhost:8000`, set `VITE_API_BASE` in the
frontend environment before running `npm run dev`.

## Testing scenarios with curl

```bash
# Test 401 - missing auth
curl -X POST http://localhost:8000/proxy \
  -H "Content-Type: application/json" \
  -d '{"target_url":"https://httpbin.org/status/401","method":"GET","headers":{},"body":null}'

# Test 429 - rate limit
curl -X POST http://localhost:8000/proxy \
  -H "Content-Type: application/json" \
  -d '{"target_url":"https://httpbin.org/status/429","method":"GET","headers":{"Retry-After":"30"},"body":null}'

# Test 422 - validation error
curl -X POST http://localhost:8000/proxy \
  -H "Content-Type: application/json" \
  -d '{"target_url":"https://httpbin.org/status/422","method":"POST","headers":{"Content-Type":"application/json"},"body":{"amount":"not-a-number"}}'

# Real Stripe test (needs key)
curl -X POST http://localhost:8000/proxy \
  -H "Content-Type: application/json" \
  -d '{"target_url":"https://api.stripe.com/v1/customers","method":"GET","headers":{"Authorization":"Bearer sk_test_YOUR_KEY"},"body":null}'
```

Every call above returns the full captured record, including the
`severity`, `error_code`, `explanation`, `suggestion`, and `detected_issues`
fields produced by the analyzer — the same data the Analysis tab renders in
the UI.

## Using replay

Every captured request shows a **Replay request** button on its Analysis
tab. Clicking it opens a modal pre-filled with the original target URL,
headers, and body — edit whatever you suspect was wrong (say, fix a
malformed `Authorization` header) and hit **Send replay**. The tool fires the
modified request, shows the result inline in the modal, and adds it to the
feed as a new entry linked back to the original via `parent_id` so you can
compare the before/after side by side.

The same replay behavior is available directly via the API:

```bash
curl -X POST http://localhost:8000/requests/1/replay \
  -H "Content-Type: application/json" \
  -d '{"headers":{"Authorization":"Bearer sk_test_valid_key"}}'
```

Any field you omit (`target_url`, `headers`, `body`, `query_params`) falls
back to the value stored on the original request.

## Capturing real site traffic (transparent reverse proxy)

`POST /proxy` is opt-in — you tell it what to send. For watching everything
your own site's frontend is already sending to your own backend (a dev/staging
instance, not production), point your frontend at the inspector instead of
your backend, and it forwards every request through transparently:

```
Browser ──▶ http://localhost:8000/capture/<path>
                        │
                        ▼  forwards as-is, any method/path/body
              UPSTREAM_BASE_URL (your real backend)
                        │
                        ▼
              captured, analyzed, stored, broadcast — same as /proxy
                        │
                        ▼
Browser ◀── the real response, unmodified
```

Set `UPSTREAM_BASE_URL` in `backend/.env` to your staging backend, e.g.:

```
UPSTREAM_BASE_URL=http://localhost:3000
```

Then repoint your storefront's frontend at the inspector instead of your
backend directly. The easiest way is usually your dev server's proxy config
(Vite, webpack-dev-server, etc.) — change the existing API proxy target from
`http://localhost:3000` to `http://localhost:8000/capture`, so it stays
same-origin from the browser's point of view and every add-to-cart, checkout,
and inventory call gets captured with zero changes to your application code.

This is a plain reverse proxy (no TLS interception, no certificates) — it
works for HTTP or HTTPS upstreams since the inspector talks to your real
backend over its own connection, but the browser always talks plain HTTP to
`localhost:8000`. Do not point this at a production instance handling real
customer payments: request/response bodies are stored as-is in SQLite,
unencrypted, for inspection.
