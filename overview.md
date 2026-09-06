# Distributed Rate Limiter & API Gateway — DRF Edition

Overview for anyone picking up this codebase. Read this before touching `authentication/`,
`ratelimiter/`, `cache/`, or `proxy/`. Merged from the original 5-day scope and the 10-day
component-based implementation plan — this is the current source of truth.

## What this service is

A standalone API gateway on Django REST Framework, behind nginx, running as 3+ stateless
instances. For every request it authenticates the caller, checks their rate limit atomically
against Redis, forwards allowed requests to a backend, and reports everything to Prometheus/Grafana.

There's no meaningful CRUD "business logic" here — the value is entirely in the concurrency
correctness of the auth + rate-limit + proxy path under horizontal scale. Review effort should
go to the Lua scripts, middleware ordering, and the cache-aside/fallback logic before anything else.

## Request lifecycle

```
Client (X-API-Key header)
  |
  v
nginx  ------------------------------------> least_conn across 3+ gateway instances
  |
  v
Gateway instance (Django + DRF)
  |
  1. APIKeyAuthentication
  |     - hash incoming key, look up APIKey (cache-aside: Redis first, Postgres on miss)
  |     - invalid/revoked -> 401
  |     - Redis down -> in-memory LRU fallback, reduced capacity, service stays up
  |
  2. RateLimitMiddleware
  |     - resolve algorithm + limit from the key's tier
  |     - run the matching Lua script against Redis (atomic EVALSHA)
  |     - allow  -> attach X-RateLimit-* headers, continue
  |     - reject -> 429 + Retry-After, short-circuit before the view
  |
  3. ProxyView (httpx, async)
  |     - resolve backend from YAML route config
  |     - forward with retry + exponential backoff
  |     - circuit breaker skips upstreams currently marked unhealthy
  |
  4. Observability middleware
  |     - Prometheus counters/histograms, structured JSON log line, X-Request-ID correlation
  v
Client receives response
```

Ordering is load-bearing: auth before rate-limit before proxy. A request that fails auth or the
rate check must never reach `ProxyView`.

## Why Lua for every rate-limit check

`INCR` + `EXPIRE` as two Redis calls is not atomic — a crash between them leaks the TTL and makes
every subsequent count wrong. `HMGET`+`HMSET` for token bucket has the same problem. Every
algorithm here is one `EVALSHA` call, so read-check-write is atomic from Redis's point of view.
That's what lets 3+ gateway instances share one correct limit instead of each enforcing its own
(too generous) copy.

## Algorithms and tiers

| Tier | Algorithm | Requests/min | Burst |
|---|---|---|---|
| `free` | Token Bucket | 10 | 15 |
| `pro` | Sliding Window Log | 100 | 150 |
| `enterprise` | Fixed Window Counter | 1000 | 1500 |

| Algorithm | Redis structure | Trade-off |
|---|---|---|
| Token bucket | Hash (tokens, last_refill) | Smooth bursts, O(1) memory |
| Fixed window counter | String + TTL (INCR) | Cheapest, boundary-spike risk |
| Sliding window log | Sorted set | Most precise, O(n) memory per window |

Algorithm is a property of the tier, not hardcoded — see `ratelimiter/algorithms/factory.py`.
Current benchmark numbers belong in `docs/BENCHMARKS.md`, not here.

## Module layout

```
rate-limiter/
├── docker-compose.yml            # postgres, redis, gateway, nginx
├── docker-compose.prod.yml
├── Dockerfile
├── Makefile                       # make dev / test / lint
├── requirements/{base,dev,prod}.txt
├── gateway/
│   ├── manage.py
│   ├── config/settings/{base,dev,prod}.py, urls.py, wsgi.py
│   ├── core/                      # HealthCheckView
│   ├── authentication/            # APIKey model, APIKeyAuthentication, tiers, admin
│   ├── ratelimiter/
│   │   ├── algorithms/            # base.py, token_bucket.py, fixed_window.py, sliding_window.py, factory.py
│   │   ├── lua_scripts/           # one .lua per algorithm
│   │   ├── middleware.py, headers.py, config.py, exceptions.py
│   ├── cache/                     # connection.py, key_cache.py, invalidation.py, fallback.py, namespaces.py
│   ├── proxy/                     # views.py (httpx), router.py, retry.py, circuit_breaker.py
│   ├── observability/             # metrics.py, middleware.py, logging_config.py
│   └── utils/                     # exceptions.py, responses.py
├── nginx/nginx.conf
├── monitoring/prometheus/, monitoring/grafana/
├── loadtests/k6/{smoke,load,stress,per_tier}.js
└── docs/{ARCHITECTURE,API,BENCHMARKS,TRADE_OFFS}.md
```

## Key design decisions

| Decision | Why |
|---|---|
| Hash API keys at rest (sha256), store prefix only | A DB leak shouldn't leak usable keys |
| Cache-aside for key lookups, in-memory LRU fallback on Redis outage | Stay up at reduced capacity rather than fail open/closed blindly |
| Lua script per algorithm, never bare Redis commands | Only way to get true atomicity across concurrent instances |
| Algorithm selection is a tier property, not per-route code | New tiers/algorithms are config changes, not code changes |
| Circuit breaker per upstream | One unhealthy backend shouldn't take down the whole gateway |
| Split settings (base/dev/prod) | Env-specific config without env-var sprawl |

## Environment variables

| Variable | Purpose |
|---|---|
| `REDIS_HOST` / `REDIS_PORT` | Shared rate-limit + cache state |
| `DATABASE_URL` | Postgres — API key/tier config |
| `DJANGO_SETTINGS_MODULE` | `config.settings.dev` / `.prod` |
| `UPSTREAM_CONFIG_PATH` | Path to the YAML route → backend mapping |
| `PROMETHEUS_METRICS_ENABLED` | Toggle `/metrics` exposure |

## Running locally

```bash
make dev            # docker-compose up --build: postgres, redis, gateway, nginx
make test            # pytest --cov, gate at 85%
make lint             # ruff, black, mypy
```

Grafana on `:3000`, Prometheus on `:9090`, gateway via nginx on `:80`.

## Load testing

```bash
k6 run loadtests/k6/stress.js   # ramps to 500 RPS, checks p95 < 500ms, 429 p99 < 100ms
```

Always point k6 at nginx (`:80`), not a single gateway instance directly — hitting one instance
bypasses the multi-instance correctness the whole project exists to prove.

## Extending this service

- **New algorithm**: add a `.lua` script under `ratelimiter/lua_scripts/`, implement it in
  `ratelimiter/algorithms/`, register it in `factory.py`, add it as a tier option. Never implement
  a new algorithm as plain Python + separate Redis calls — it will not be atomic.
- **New tier**: add an entry to the tier config dataclass; no middleware change needed.
- **New backend route**: add an entry to `upstream_config.yaml`.
- **New metric**: add it in `observability/metrics.py`, not inline in another middleware — keep
  the auth/rate-limit/proxy path free of anything that isn't the decision itself.
