# URL Shortener API

A URL shortener with async click analytics. Not just short links — it tracks who clicked (device, browser, location) without slowing down the redirect. Clicks are logged in the background via Celery, so the redirect fires first.

## Highlights

- **Cache-first redirect** — short code lookup checks Redis first before hitting the database, with cache write-through on a miss (`RedirectToOriginal`). Redirects stay fast even under high click volume.
- **Idempotency key on the create endpoint** — prevents duplicate short URLs on request retries (network timeouts, double-taps, etc.), using `cache.add()` as an atomic lock with a 60-second window.
- **Async click tracking** — every click is dispatched to a Celery task (`track_click.delay()`) *after* the redirect response is sent, so the user isn't waiting on device/browser/geo logging.
- **Three targeted composite indexes for analytics queries** — separate indexes on `(short_url, clicked_at, country_code)`, `(short_url, clicked_at, device_type)`, and `(short_url, clicked_at, referer_domain)`, each covering one filter dimension without the write overhead of a single wide index.

## Tech Stack

- **Backend:** Django 6.0, Django REST Framework
- **Database:** PostgreSQL
- **Cache & Message Broker:** Redis
- **Async Task Queue:** Celery
- **Authentication:** JWT (djangorestframework-simplejwt + dj-rest-auth)
- **API Documentation:** drf-spectacular (OpenAPI/Swagger)
- **Deployment:** Gunicorn + Nginx (VPS)
- **External Integrations:** ip-api.com (geolocation), user-agents (device parsing)

## Architecture Decisions

**Why cache-first redirects instead of always hitting the database**
Redirect is the highest-traffic, most latency-sensitive endpoint in this system — every click depends on it. Short URL lookups are cached in Redis with a 24-hour TTL, checked before any database query. On a cache miss, the result is written back to Redis so subsequent hits skip the database entirely.

**Why idempotency keys instead of relying on a unique constraint alone**
A unique constraint on `short_code` doesn't stop duplicate *creation* attempts from producing two different short URLs for the same request — e.g. a client retrying after a timeout. The `Idempotency-Key` header, combined with `cache.add()`'s atomic "set if not exists" behavior, gives a short (60-second) dedup window without needing a database-level lock.

**Why click tracking is async instead of synchronous**
Device parsing, geolocation lookup (external call to ip-api.com with a 3-second timeout), and the database write for analytics have no business blocking the redirect. `track_click.delay()` hands all of this off to Celery immediately after the redirect response is sent — the user never waits on analytics processing.

**Why three separate indexes instead of one combined index**
Analytics queries filter by `short_url` + `clicked_at` combined with *one* of country, device, or referer at a time — not all three together. Three targeted indexes, each covering a single dimension (`country_code`, `device_type`, `referer_domain`), keep queries fast without the write overhead of a single wide index covering columns that aren't always queried together.

## Features

- **Custom short URLs** — auto-generated short codes
- **Cache-first redirect** — fast lookups via Redis, falls back to the database on a cache miss
- **Click analytics** — device, browser, OS, country, and referer domain logged per click, exposed via a dedicated analytics endpoint
- **Idempotency key** — prevents duplicate short URLs on request retries
- **Soft delete** — short URLs can be deactivated without being removed from the database
- **Email OTP verification** — user registration requires an OTP code sent by email before the account is activated
- **JWT authentication** — login/token refresh via `dj-rest-auth` + `simplejwt`
- **Interactive API docs** — Swagger UI and Redoc auto-generated from the OpenAPI schema (`drf-spectacular`)

## How to run

- clone the repo
```
git clone https://github.com/Iqbal120708/url-shortener
cd url-shortener
```

- Run python environment
```
python -m venv env
source env/bin/activate
```

- install dependencies
```
pip install -r requirements.txt
```

- Create a `.env` file and set the required variables (see .env.example).

- Start PostgreSQL and Redis (via your system service manager, Docker, or manually depending on your setup)

- Run database migrations
```
cd src
python manage.py migrate
```

- Start the Celery worker (in a separate terminal, from the src/ directory)
```
celery -A config worker --loglevel=info
```

- Run the server
```
cd src
python manage.py runserver
```

# API Documentation

Explore the full API documentation by importing the schema file into [Swagger Editor](https://editor.swagger.io):

- Download [`src/docs/schema.yml`](src/docs/schema.yml)
- Open [editor.swagger.io](https://editor.swagger.io)
- Click **File -> Import File** and select the downloaded file

Or if you have the project running locally, access directly:

- **Swagger UI**: `http://localhost:8000/api/docs/`
- **Redoc**: `http://localhost:8000/api/redoc/`