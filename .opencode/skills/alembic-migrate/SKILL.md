---
name: alembic-migrate
description: Create and apply Alembic migrations for the async SQLAlchemy models in backend/src/models/. Use when adding/changing DB columns, renaming tables, or syncing schema with model changes. Has side effects (writes migration files, touches the SQLite DB).
disable-model-invocation: true
---

# Alembic Migration Helper (Async SQLAlchemy)

Generate and apply database migrations for the autotest backend.

## Project Context

- **ORM**: SQLAlchemy 2.0 in async mode (`sqlalchemy[asyncio]`)
- **Driver**: `aiosqlite` (SQLite at `backend/data/autotest.db`)
- **Migration tool**: Alembic 1.13 (config at `backend/alembic.ini`, env at `backend/alembic/env.py`)
- **Models location**: `backend/src/models/`

## Pre-flight checks (run first)

```powershell
cd backend
# 1. Make sure venv is active and deps installed
.\.venv\Scripts\Activate.ps1
# 2. Confirm Alembic sees current head
alembic current
# 3. Confirm working tree has no in-progress migrations
git status backend/alembic/versions
```

If `alembic current` shows a revision that is NOT in `backend/alembic/versions/`, stop and investigate — DB is ahead of the codebase.

## Workflow: add a new migration

1. **Edit the model** under `backend/src/models/<entity>.py` first. Do NOT hand-write migration SQL before the model change.

2. **Ensure metadata import** in `backend/alembic/env.py` includes the new/changed model — autogenerate only sees what is imported.

3. **Generate the revision**:
   ```powershell
   cd backend
   alembic revision --autogenerate -m "<short_snake_case_summary>"
   ```

4. **Review the generated file** under `backend/alembic/versions/`:
   - Verify `op.add_column` / `op.alter_column` / `op.create_table` match the intended change.
   - **SQLite caveat**: ALTER COLUMN is limited. If the autogen produced `batch_alter_table`, keep it — that pattern is required.
   - Delete spurious `op.drop_*` operations the autogen may produce against tables it does not know about.

5. **Apply** in a sandbox first:
   ```powershell
   alembic upgrade head
   # If something goes wrong:
   alembic downgrade -1
   ```

6. **Test rollback** before committing:
   ```powershell
   alembic downgrade -1
   alembic upgrade head
   ```

7. **Commit** both the model change and the new revision file in the same commit.

## Common pitfalls

- **Forgetting to import the model in `env.py`** → autogen produces an empty migration. Fix: import the new model into the metadata module.
- **Renaming a column** → autogen treats it as drop+add and loses data. Fix: hand-edit the revision to use `op.alter_column(... new_column_name=...)`.
- **Changing a NOT NULL column with existing rows** → upgrade fails. Fix: add the column nullable, backfill in a data migration, then alter to NOT NULL in a second revision.
- **SQLite + index changes** → some operations require `with op.batch_alter_table(...)`. Trust the autogen here.

## When NOT to use this skill

- Pure SELECT changes (no schema impact) — no migration needed.
- Renaming a Python attribute that maps to the same column name — no migration needed.
- Production DB migrations on PostgreSQL — this skill assumes SQLite dev DB; production paths need a separate review.
