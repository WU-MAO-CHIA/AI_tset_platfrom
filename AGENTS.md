# AGENTS.md — Automatic_Test

FastAPI (Python) + Vue 3 (TypeScript) test-automation platform. README.md covers
setup; this file covers what agents get wrong.

## Communication

- Always respond in **Traditional Chinese** (project constitution requirement).

## Shell (Windows PowerShell 5.1)

- No `&&`, `grep`, `head`, `tail`. Chain with `;` / `if ($?) { }`; filter with
  `Select-Object -First N`.
- `npx`/`npm` may be blocked by execution policy in this tool's shell — prefix
  with `cmd /c "..."` (e.g. `cmd /c "cd frontend && npx vitest run ..."`).
- Never `cd` inside commands; use the tool's `workdir` parameter.
- Use dedicated file tools (read/edit/write/glob/grep), never shell for file I/O.

## Backend (`backend/`, run everything with workdir `backend/`)

- Interpreter: `.\.venv\Scripts\python`. Server: `python -m uvicorn src.main:app
  --reload --host 0.0.0.0 --port 8000` (must run from `backend/` — settings use
  **relative paths**: `./data/autotest.db`, `./robot_scripts`, `./data/media`).
- `.env` needs a fixed `JWT_SECRET_KEY`, else every restart invalidates all
  tokens (401s). Seed admin: `python -m scripts.seed_admin`.
- Layering: `api/` → `services/` → `repositories/` → `models/`. Reuse
  `RobotScriptRepository`, `TestCase.robot_script`, existing endpoints before
  adding new ones.
- **Tests must never touch the REAL file DB** (`data/autotest.db`). Contract
  tests are isolated automatically (`tests/contract/conftest.py`). Anywhere
  else, a test that goes through the app must request the `isolated_app`
  fixture from `tests/conftest.py` (in-memory DB seeded with `admin/admin`,
  file writes under `tmp_path`, background robot runs and LLM calls stubbed;
  use `admin_headers` for auth) or override `get_db` itself (see
  `tests/integration/test_sse_stream.py`) — otherwise it hits the real DB.
  Never leave junk rows/files from manual curl verification — clean up
  afterwards.
- `python -m pytest tests/unit tests/contract tests/integration` is safe and
  takes ~15 s; don't run `tests/load`.
- CI (`.github/workflows/ci.yml`) runs these three dirs plus frontend
  `npm test` and `npm run build` on every PR.
- Auth: `Authorization: Bearer` header on all API routes **except** the SSE
  stream (cookie only) and `rf-report/` files (loaded by an `<iframe>`;
  `get_current_user_header_or_cookie` accepts either). Both read the HttpOnly
  `access_token` cookie — FastAPI only binds
  cookies via `Cookie()` annotation (a bare `str | None = None` param binds a
  query param, not the cookie). EventSource cannot send headers.
- Single-worker uvicorn only: explore sessions live in process memory, and
  executions are run by one in-process `ExecutionWorker`
  (`src/execution/worker.py`, started on app startup — not in tests). Trigger
  endpoints only write a `pending` record with a `params` snapshot; the worker
  claims by `priority DESC, queued_at` (trial runs first) up to
  `EXECUTION_MAX_CONCURRENT`. `POST /executions/{id}/cancel` only cancels
  `pending` (conditional UPDATE, so it can't race the worker's claim); running
  returns 409. Execution progress events are in
  the `execution_events` table (`src/execution/events.py`, `EventSink`); the
  SSE route polls it, so tests that stream must point
  `src.api.executions.AsyncSessionLocal` and `src.core.database.AsyncSessionLocal`
  at their test DB (see `tests/integration/test_sse_stream.py`). On startup,
  executions left `running` become `interrupted` (`src/execution/recovery.py`).
  Tests that run the worker loop need a file SQLite DB under `tmp_path`, not
  the in-memory `StaticPool` one: concurrent sessions on one shared connection
  roll back each other's writes (see `tests/unit/test_execution_worker.py`).
- Scheduled runs (spec 004): `ScheduleRunner` (`src/scheduling/runner.py`,
  started on startup unless `SCHEDULE_ENABLED=false`) ticks every 30 s and only
  enqueues via `ExecutionService.run_checklist_parallel(schedule_id=...)`; the
  worker runs it. Schedule datetimes are stored as UTC (SQLite returns them
  naive, so wrap reads in `as_utc`); `time_of_day`/`weekdays` are read in
  `SCHEDULE_TIMEZONE`. Test `tick(now)` directly with a fixed `now`.

## Frontend (`frontend/`, workdir `frontend/`)

- Dev server proxies `/api` → `localhost:8000`, so SSE same-origin works.
- `npx vue-tsc --noEmit` for typecheck (0 errors as of 2026-10; keep it that way).
- `package-lock.json` is committed; install with `npm ci`. Regenerate it with
  npm 11+ (`npx npm@11 install`): npm 10's resolver crashes on this tree
  (`Cannot read properties of null (reading 'edgesOut')`).
- `npm test` runs only `tests/unit/**` (vitest `include`); Playwright e2e is
  `npm run test:e2e`. Monaco imports are aliased to `tests/__mocks__/` in
  `vitest.config.ts`; `tests/__mocks__/setup.ts` polyfills `Blob.arrayBuffer`
  for jsdom.
- Vue Test Utils quirks: `findComponent({ name })` misses `index.vue` SFCs
  without an explicit name — import the component and `findComponent(Comp)`.
  jsdom file inputs can't be set programmatically. Trigger form submit via
  `find('form...').trigger('submit')`, not button click (activation behavior).
  Stubs need every method the parent calls (`?.` on a missing stub method
  throws). Pinia stores in pages need `setActivePinia(createPinia())`.

## Workflow

- Spec-Kit: specs live in `specs/NNN-name/` (`spec.md` → `plan.md` →
  `tasks.md`); feature branches are named `NNN-name`; merge back to `master`,
  push to remote `test_platfrom`.
- Mark `tasks.md` checkboxes `[X]` as work completes.
- Commit/merge/push only when explicitly asked. Never commit `.env`, `*.db`,
  or `data/`.
