# Implementation Plan: RF Code Upload and AI Integration

**Branch**: `002-rf-code-upload-ai` | **Date**: 2026-09-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-rf-code-upload-ai/spec.md`

## Summary

This feature adds Robot Framework (.robot) file upload capability in the test case creation and edit pages, and integrates the uploaded RF code as context for AI chat conversations. The feature leverages existing infrastructure: the `RobotScript` database table, disk sync mechanism, and AI service with LLM providers.

**Primary Requirement**: Allow users to upload .robot files during test case creation/editing, preview/edit the code with syntax highlighting, store it in the database (synced to disk), and make it available as context for AI chat sessions.

**Technical Approach**: 
- Backend: Extend existing test case API endpoints to handle multipart file upload for .robot files, reuse `RobotScriptRepository` for persistence
- Frontend: Add file upload component in test case create/edit forms, integrate Monaco Editor for syntax-highlighted preview/editing
- AI Integration: Modify `AIService.chat_and_generate_rf` to include RF code context when available, with user-controllable context scope (per clarification Q1)

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript 5.6+ (frontend)  
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, Vue 3.5, Pinia, Axios, Monaco Editor  
**Storage**: SQLite (async SQLAlchemy), local filesystem for RF script sync  
**Testing**: pytest (backend), Vitest (frontend unit), Playwright (e2e)  
**Target Platform**: Web application (browser-based)  
**Project Type**: Web application (frontend + backend)  
**Performance Goals**: File upload < 2s for 500KB, RF code preview load < 2s, AI context injection < 500ms overhead  
**Constraints**: File size limit 500KB, .robot extension validation, UTF-8 encoding, backward compatibility with existing test cases  
**Scale/Scope**: Single file upload per test case, ~100KB typical RF scripts, existing user base with test cases

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| I. Library-First | Feature extends existing libraries (case_service, ai_service, robot_script_repo) rather than creating new ones | ✅ Pass |
| II. CLI Interface | Backend exposes REST API; no new CLI needed for this feature | ✅ Pass |
| III. Test-First | Tests will be written before implementation (unit + integration) | ✅ Pass |
| IV. Integration Testing | Required for AI service integration with RF code context | ✅ Pass |
| V. Simplicity | Reuses existing RobotScript table, disk sync, and AI service; minimal new code | ✅ Pass |
| VI. Development Principles | Uses existing Service/Repository patterns, Python 3.11+, TypeScript/Vue | ✅ Pass |

## Project Structure

### Documentation (this feature)

```text
specs/002-rf-code-upload-ai/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── api.md           # API contracts
│   └── sse.md           # SSE events (if changed)
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
# Web application structure (Option 2)
backend/
├── src/
│   ├── models/
│   │   ├── robot_script.py        # Existing - RobotScript model
│   │   └── test_case.py           # Existing - TestCase model
│   ├── services/
│   │   ├── case_service.py        # Existing - will extend for RF upload
│   │   ├── ai_service.py          # Existing - will extend for RF context
│   │   └── file_parser_service.py # Existing - can reuse for .robot parsing
│   ├── repositories/
│   │   ├── test_case_repo.py      # Existing
│   │   └── robot_script_repo.py   # Existing - RobotScriptRepository
│   └── api/
│       ├── cases.py               # Existing - will add upload endpoint
│       └── auth.py                # Existing

frontend/
├── src/
│   ├── components/
│   │   ├── RFCodeUpload.vue       # NEW - file upload + preview component
│   │   ├── RFCodeEditor.vue       # NEW - Monaco Editor wrapper
│   │   └── AIChatPanel.vue        # Existing - will pass RF context
│   ├── pages/
│   │   ├── TestCaseForm.vue       # Existing - will integrate RF upload
│   │   └── TestCaseDetail.vue     # Existing - will show RF code
│   ├── services/
│   │   ├── caseApi.ts             # Existing - will add upload method
│   │   └── aiApi.ts               # Existing - will pass RF context
│   └── stores/
│       └── caseStore.ts           # Existing - may need RF code state
└── tests/
    ├── unit/
    │   ├── RFCodeUpload.spec.ts
    │   └── RFCodeEditor.spec.ts
    └── e2e/
        └── rf-code-upload.spec.ts
```

**Structure Decision**: Web application (Option 2) - matches existing backend/frontend structure. New components for RF code upload/editing, extending existing API endpoints and services.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | All principles satisfied by reusing existing infrastructure | N/A |

## Phase 0: Research

### Unknowns to Resolve

1. **Monaco Editor Integration**: How to integrate Monaco Editor for Robot Framework syntax highlighting in Vue 3
2. **AI Context Injection**: Best approach to inject RF code into AI chat context (system prompt vs message history)
3. **File Upload Handling**: FastAPI multipart handling for .robot files with size/extension validation
4. **RF Code Context Scope Selection**: UI for user to choose context scope per chat session (per clarification Q1=C)

### Research Tasks

- Research Monaco Editor Robot Framework language support and Vue 3 integration patterns
- Research AI context injection patterns for LLM conversations (system prompt vs user message)
- Research FastAPI file upload best practices with validation
- Research existing codebase patterns for file upload (media_service, file_parser_service)

## Phase 1: Design & Contracts

### Data Model (data-model.md)

Extends existing `RobotScript` model (already defined in `backend/src/models/robot_script.py`):
- No new tables needed - reuses existing `robot_scripts` table
- Existing fields: `id`, `test_case_id`, `rf_code`, `saved_by`, `created_at`, `updated_at`
- Relationship: `TestCase.robot_script` (one-to-one, cascade delete)

### API Contracts (contracts/api.md)

**New/Modified Endpoints:**

1. `POST /api/v1/cases/{case_id}/robot-script/upload` - Upload .robot file
   - Request: multipart/form-data with `file` field
   - Response: `{ rf_code: string, case_number: string, file_path: string }`
   - Validation: .robot extension, 500KB limit, UTF-8 decode

2. `PUT /api/v1/cases/{case_id}/robot-script` (existing) - Save edited RF code
   - Already exists, will be used for saving edited preview

3. `GET /api/v1/cases/{case_id}/robot-script` (existing) - Get RF code
   - Already exists, returns from DB or disk fallback

4. `POST /api/v1/cases/{case_id}/chat` (existing) - AI chat
   - Modified: Request body adds optional `rf_context_mode` field (full/summary/user_choice)
   - Response includes RF code context when available

### Quickstart (quickstart.md)

Document how to test the feature end-to-end:
1. Create test case with RF file upload
2. Preview and edit RF code in Monaco Editor
3. Save test case
4. Open AI chat, verify RF code context
5. Test context scope selection (full/summary)

## Phase 2: Task Generation

Tasks will be generated by `/speckit-tasks` command after plan approval.