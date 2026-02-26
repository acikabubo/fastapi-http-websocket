# Gunicorn + Uvicorn Workers Guide

## What it is

Gunicorn acts as a **process manager** that spawns multiple Uvicorn worker
processes, one per CPU core.

```
                    ┌─────────────────────────────┐
                    │         Gunicorn             │
                    │      (process manager)       │
                    └──────────┬──────────────────┘
                               │ manages
               ┌───────────────┼───────────────┐
               ▼               ▼               ▼
        Uvicorn Worker   Uvicorn Worker   Uvicorn Worker
          (CPU core 1)    (CPU core 2)    (CPU core N)
```

**Without it (current):** A single Uvicorn process uses only 1 CPU core. Even
if the server has 8 cores, 7 sit idle under load.

**With it:** N workers = N cores utilized = roughly N× throughput for
CPU-bound work.

---

## What you gain

| Scenario | Benefit |
|---|---|
| High concurrent HTTP requests | Requests distributed across workers |
| One worker gets stuck (rare) | Others continue serving |
| CPU-bound tasks (Pydantic validation, JSON serialization) | Parallelized across cores |
| Memory isolation | Each worker is an independent Python process (no GIL contention) |

## What you do NOT gain

- **No benefit for async I/O wait** — `await db.execute(...)`,
  `await redis.get(...)` etc. are already handled efficiently by a single
  Uvicorn process via the event loop. Gunicorn doesn't help here.
- **No shared in-memory state** — each worker is an independent Python
  process. In-memory caches are duplicated per worker.

---

## For this project specifically

Most of the work is async I/O (PostgreSQL, Redis, Keycloak, WebSocket). The
real bottleneck is unlikely to be CPU cores.

**WebSocket sticky-session concern:** WebSocket connections are sticky to the
worker that accepted them. With multiple workers, a client reconnecting may
land on a different worker. Since this project uses Redis for pub/sub,
cross-worker message delivery is already handled — but worth verifying
WebSocket consumer reconnect logic.

---

## Automatic worker calculation

The standard formula is `(2 × CPU cores) + 1`.

### Option 1 — Shell (docker-compose command)

```bash
gunicorn app.main:app \
  --workers $((2 * $(nproc) + 1)) \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Option 2 — `gunicorn.conf.py` (recommended)

```python
import multiprocessing

worker_class = "uvicorn.workers.UvicornWorker"
workers = 2 * multiprocessing.cpu_count() + 1
bind = "0.0.0.0:8000"

timeout = 120          # Worker killed after this many seconds of silence
keepalive = 5          # Keep-alive connections (seconds)
graceful_timeout = 30  # Time to finish in-flight requests on shutdown
```

Place `gunicorn.conf.py` at the project root. Gunicorn picks it up
automatically — no flags needed:

```bash
gunicorn app.main:app
```

In a Docker container, `cpu_count()` reflects the **container's CPU limit**
(set via `cpus:` or `--cpus`), not the host's total cores — which is exactly
what you want.

---

## Docker Compose integration

```yaml
hw-server:
  # Replace: uvicorn app.main:app --host 0.0.0.0 --port 8000
  command: gunicorn app.main:app
  deploy:
    resources:
      limits:
        cpus: "2"   # Gunicorn will see 2 cores → spawn 5 workers
```

Also add `gunicorn` to `pyproject.toml` dependencies before using this.

---

## Bottom line

For this project's async-heavy workload, the gain will be **modest** unless
there are genuinely CPU-bound hot paths. Redis/PostgreSQL connection limits
will likely become the bottleneck before CPU cores do.
