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
- **Tests hit the REAL file DB** (`data/autotest.db`) unless overridden —
  contract tests pollute production data. For new tests use the in-memory
  pattern: `create_async_engine("sqlite+aiosqlite://")` + `StaticPool` +
  override `get_db` (see `tests/integration/test_sse_stream.py`). Never leave
  junk rows/files from manual curl verification — clean up afterwards.
- Run focused suites, not the whole tree:
  `python -m pytest tests/unit/test_x.py tests/integration/test_y.py`.
- Auth: `Authorization: Bearer` header on all API routes **except** the SSE
  stream, which reads the HttpOnly `access_token` cookie — FastAPI only binds
  cookies via `Cookie()` annotation (a bare `str | None = None` param binds a
  query param, not the cookie). EventSource cannot send headers.
- Single-worker uvicorn only: execution queues and explore sessions live in
  process memory.

## Frontend (`frontend/`, workdir `frontend/`)

- Dev server proxies `/api` → `localhost:8000`, so SSE same-origin works.
- `npx vue-tsc --noEmit` for typecheck (7 pre-existing errors as of 2026-09 —
  don't chase them; just add none).
- Vitest has no `include` filter, so **it also collects `tests/e2e/*.spec.ts`
  (Playwright) and fails**. Always run unit paths explicitly, e.g.
  `npx vitest run tests/unit/AIChatPanel.spec.ts`; never bare `npm test` for
  verification. Monaco imports are aliased to `tests/__mocks__/` in
  `vitest.config.ts`.
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
