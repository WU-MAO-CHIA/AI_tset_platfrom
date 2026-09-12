# Data Model: RF Code Upload and AI Integration

**Feature**: RF Code Upload and AI Integration  
**Date**: 2026-09-10

## Entities

### TestCase (Extended)
**Existing entity** - extends with RF code relationship

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID (string) | PK, not null | Unique identifier |
| case_number | string(50) | Unique, not null, index | Human-readable case number (e.g., TC-001) |
| name | string(255) | Not null, index | Test case name |
| description | text | Nullable | Detailed description |
| precondition_steps | text | Nullable | Precondition steps |
| main_steps | text | Not null | Main test steps |
| system_category | string(100) | Nullable, index | System category |
| tags | JSON array | Default [] | Tags for filtering |
| version | integer | Default 1, not null | Version number |
| created_by | string(100) | Not null | Creator username |
| modified_by | string(100) | Nullable | Last modifier username |
| is_deleted | boolean | Default false, index | Soft delete flag |
| deleted_by | string(100) | Nullable | Deleter username |
| created_at | datetime | Auto | Creation timestamp |
| updated_at | datetime | Auto | Last update timestamp |

**Relationships:**
- `test_data` → TestData (one-to-many, cascade delete)
- `attachments` → MediaAttachment (one-to-many, cascade delete)
- `chat_messages` → CaseChatMessage (one-to-many, cascade delete, ordered by created_at)
- `robot_script` → RobotScript (one-to-one, cascade delete, **NEW**)

---

### RobotScript (Existing - Reused)
**No new table needed** - existing model in `backend/src/models/robot_script.py`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID (string) | PK, not null | Unique identifier |
| test_case_id | UUID (string) | FK to test_cases.id, unique, not null, index | Owning test case |
| rf_code | text | Not null | Robot Framework script content |
| saved_by | string(100) | Nullable | Username who saved |
| created_at | datetime | Auto | Creation timestamp |
| updated_at | datetime | Auto | Last update timestamp |

**Relationships:**
- `test_case` → TestCase (many-to-one, back_populates="robot_script")

---

### CaseChatMessage (Extended Context)
**Existing entity** - AI chat messages now include RF code context reference

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID (string) | PK, not null | Unique identifier |
| case_id | UUID (string) | FK to test_cases.id, not null, index | Associated test case |
| role | enum | Not null | user / assistant / system |
| type | enum | Not null | CHAT / TRIAL_RUN_RESULT / ... |
| content | text | Not null | Message content |
| created_at | datetime | Auto, index | Creation timestamp |

**Note**: RF code context is **not stored** in messages - it's injected at request time from the associated RobotScript.

---

### AI Chat Session Context (Runtime)
**Not persisted** - computed at request time

| Property | Type | Description |
|----------|------|-------------|
| case_id | string | Test case identifier |
| rf_code | string \| null | Full RF code from RobotScript |
| rf_context_mode | enum | "full" / "summary" / "none" (user choice) |
| rf_summary | string \| null | Generated summary when mode="summary" |

---

## Validation Rules

### RobotScript
- `rf_code`: Must be valid UTF-8 text
- `rf_code`: Max 500KB (enforced at API layer)
- `test_case_id`: Must reference existing non-deleted TestCase
- File extension validation: `.robot` (case-insensitive) at upload

### TestCase (for RF upload)
- User must have editor role or above (existing `require_editor_or_above` dependency)
- Case must not be soft-deleted
- On edit: RF code overwrites existing (per clarification Q3=A)

---

## State Transitions

### RF Code Lifecycle
```
[No RF Code] 
    │
    ├─ Upload .robot file → [RF Code Stored in DB + Disk]
    │       │
    │       ├─ Edit in Monaco → [RF Code Updated in DB + Disk]
    │       │
    │       ├─ Clear editor → [No RF Code] (delete RobotScript)
    │       │
    │       └─ New upload → [RF Code Overwritten] (confirmation required)
    │
    └─ AI Chat with context → [Context injected at request time]
```

### AI Chat Context
```
[Chat Session Started]
    │
    ├─ Case has RF code + mode != "none" → [Inject RF code in system prompt]
    │       │
    │       ├─ mode = "full" → [Full RF code]
    │       ├─ mode = "summary" → [Generated summary]
    │       └─ mode = "none" → [No RF context]
    │
    └─ Case has no RF code → [Standard chat without RF context]
```

---

## Indexes (Existing)

```sql
-- RobotScript table
CREATE UNIQUE INDEX ix_robot_scripts_test_case_id ON robot_scripts(test_case_id);
CREATE INDEX ix_robot_scripts_saved_by ON robot_scripts(saved_by);

-- TestCase table (existing)
CREATE UNIQUE INDEX ix_test_cases_case_number ON test_cases(case_number);
CREATE INDEX ix_test_cases_name ON test_cases(name);
CREATE INDEX ix_test_cases_system_category ON test_cases(system_category);
CREATE INDEX ix_test_cases_is_deleted ON test_cases(is_deleted);
```

---

## Migration Notes

**No database migration required** - all tables and relationships already exist:
- `robot_scripts` table created in previous migrations
- `TestCase.robot_script` relationship defined in `backend/src/models/test_case.py`
- `RobotScriptRepository` with `upsert`/`get_by_case_id` methods exist

Only code changes needed in:
- API endpoints for upload
- AI service for context injection
- Frontend components