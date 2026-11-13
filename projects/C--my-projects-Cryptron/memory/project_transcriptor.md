---
name: project-transcriptor
description: Transcriptor — home assignment (media→transcription service) for a defense-sector Backend Developer role.
metadata: 
  node_type: memory
  type: project
  originSessionId: 53fc5808-962f-462b-8aa9-19a1d12cfd84
---

Transcriptor (in `C:\my_projects\Transcriptor`) is a **home assignment** for a
Backend Developer job application — defense/intelligence-data sector, stack:
Apache Spark, Python, Docker, K8s, Airflow, CI/CD. Goal: a service that uploads a
media file and returns a transcription using a Hugging Face (Whisper) model.

Docs live in `Transcriptor/docs/`: `DESIGN.md`, `IMPLEMENTATION_PLAN.md`,
`DECISIONS.md`, `SUMMARY.md`.

**Status (2026-07-04): Stage A implemented and VERIFIED end-to-end** (no Docker/
Redis). FastAPI app under `app/` (config, models, logging, auth, api/, core/
chunking+reassembly+scheduler+pipeline, backends/ local+hosted+factory, store/
memory), `web/` UI (**Tailwind via Play CDN**, no build step), `tests/`. 12 unit
tests green; real local `whisper-tiny` path verified (decode→model→2 workers→
in-order reassembly+overlap dedup→lineage→done). Uses `.venv` at project root.

Note: initial torch install was corrupt (DLL load fail) — fixed with
`pip install --force-reinstall --no-cache-dir --no-deps torch`. CPU inference is
slow (tens of seconds/chunk on tiny) — inherent, not a bug.

**Stage B started (2026-07-04): Redis-backed async implemented, no Docker.**
`REDIS_URL` set ⇒ async jobs go to a Redis list drained by separate
`python -m app.worker.worker` processes; state/lineage in Redis (`RedisStateStore`/
`RedisQueue` in `app/store/redis_store.py` — NOT `redis.py`, avoids shadowing).
Sync stays in-process. Verified with `fakeredis` (shared server) integration test —
13 unit tests green. Real multi-process demo needs a Redis: no native Windows redis;
WSL2 present (Ubuntu 20.04) but redis not installed (needs sudo apt). Options for
user: WSL `apt install redis-server`, or Memurai. Still deferred: Docker/compose,
CI, Splunk HEC. Static assets are cache-busted via `app.js?v=N`.

UI evolved during testing (all in `web/`): **multi-file upload → one result card per
file** (title + live transcript + per-chunk lineage table showing `job_id` and
`chunk_id`/index); lineage refreshes live during a job. Docs reconciled 2026-07-04:
DESIGN §6/§13, SUMMARY, DECISIONS **D20** (between-job scheduling is arrival-order
backfill — workers 100% utilised, later file backfills the instant a worker frees;
fair-share scheduler considered + deferred as out-of-scope for a take-home).
Careful: HF free credits got depleted (402) by large-v3 test runs — do NOT run jobs
against the user's HF token without asking.

Docker/CI added later (by "antigravity", another agent) and reviewed OK (fixed
editable-install order, CPU-torch in CI, ruff lint, redis healthcheck, .dockerignore).
Then added an **optional shared inference server** (D21): `app/model_server.py`
(FastAPI, loads model once, reuses LocalBackend) + `app/backends/model_server.py`
(thin HTTP client); factory swaps local→model-server when `MODEL_SERVER_URL` set;
compose has a `model-server` service so api/workers are thin clients (one model in
RAM, not per worker). Verified end-to-end locally. 14 unit tests green, ruff clean.

Locked design points: chunk is the core unit (called `chunk` in code, "atom" only
as prose metaphor); sync=real-time SSE in-order / async=queued+polled; models
local=`whisper-tiny`, remote=`whisper-large-v3` (HF free serverless only serves the
large model for ASR); strong⇒remote. Remote backend calls the HF router directly
over HTTP (`router.huggingface.co/hf-inference/...`, FLAC + Content-Type) because
`huggingface_hub` 1.x `provider="auto"` throws StopIteration for Whisper — verified
working end-to-end 2026-07-04; shared model +
priority thread pool; ordering: strict chunk order WITHIN a job, priority/reorder
only BETWEEN jobs (sync preempts async); `MAX_CONCURRENT_CHUNKS` admission-control
semaphore (rate limit/backpressure) distinct from cross-pod load balancing;
in-memory store (Stage A) → Redis (Stage B); JSON logs keyed by
job_id/chunk_id/worker_id (Splunk-ready); static-token auth; WER e2e test from
user's own recording.

Constraints: user's box is 16GB, **won't run scaled**, Docker is heavy for them
(maybe run once). **Dev-first:** build Stage A (UI + sync, `pip install`+`uvicorn`,
no Docker/Redis) first, stop at the browser milestone (A4) for review; Stage B
(Redis/async/Docker) after. Still needed from user: the test recording.
See [[feedback-document-decisions]].
