# Research: RF Code Upload and AI Integration

**Feature**: RF Code Upload and AI Integration  
**Date**: 2026-09-10

## Research Summary

This document consolidates findings for implementing RF code upload and AI context integration.

---

## 1. Monaco Editor Integration for Robot Framework

### Decision
Use `@monaco-editor/loader` with `monaco-editor` package for Vue 3 integration. Robot Framework language support via custom language registration.

### Rationale
- Monaco Editor is already a mature code editor used in VS Code
- Vue 3 integration via `monaco-editor` npm package with loader
- Robot Framework syntax highlighting can be added via `monaco.languages.register` and `monaco.languages.setMonarchTokensProvider`
- Lighter than full VS Code web implementation

### Alternatives Considered
- **CodeMirror 6**: Good but less familiar to team; Monaco has better TypeScript support
- **Simple textarea + PrismJS**: No editing capabilities (linting, autocomplete, bracket matching)
- **Custom implementation**: Too much effort for syntax highlighting alone

### Implementation Approach
```typescript
// Register Robot Framework language
monaco.languages.register({ id: 'robotframework' });
monaco.languages.setMonarchTokensProvider('robotframework', {
  // Robot Framework tokenization rules
});
monaco.languages.setLanguageConfiguration('robotframework', {
  // Brackets, comments, auto-close pairs
});
```

### Key Files
- `frontend/src/components/RFCodeEditor.vue` - Monaco wrapper component
- `frontend/src/components/RFCodeUpload.vue` - Upload + preview component

---

## 2. AI Context Injection Patterns

### Decision
Inject RF code as a system message prefix in the chat conversation, with user-controllable scope (full code / summary / none) per session.

### Rationale
- System messages are processed with higher priority by LLMs
- Allows dynamic context without modifying message history
- User can choose scope per clarification Q1=C
- Works with all supported providers (Anthropic, OpenAI, Ollama)

### Implementation Approach
```python
# In AIService.chat_and_generate_rf
async def chat_and_generate_rf(
    self,
    messages: list[dict],
    user_message: str,
    llm_model: str,
    rf_code: Optional[str] = None,
    rf_context_mode: str = "full",  # full, summary, none
    timeout_sec: float = 35.0,
) -> dict:
    system_prompt = _CHAT_SYSTEM_PROMPT
    
    if rf_code and rf_context_mode != "none":
        if rf_context_mode == "summary":
            rf_code = self._generate_rf_summary(rf_code)
        context_block = f"\n\n---UPLOADED RF CODE---\n{rf_code}\n---END RF CODE---"
        system_prompt += context_block
    
    # ... rest of existing logic
```

### Alternatives Considered
- **Message history injection**: Adds RF code as user message - pollutes conversation history
- **Separate context parameter**: Requires provider-specific support
- **Embedding/vector search**: Overkill for single file context

---

## 3. FastAPI File Upload with Validation

### Decision
Use FastAPI's `UploadFile` with custom validation dependency for .robot files.

### Rationale
- FastAPI native support for multipart/form-data
- Can enforce size limit via `File(..., max_size=500*1024)`
- Extension validation in dependency
- UTF-8 decoding with fallback handling

### Implementation Approach
```python
# In cases.py
@router.post("/{case_id}/robot-script/upload")
async def upload_robot_script(
    case_id: str,
    file: UploadFile = File(..., description="Robot Framework .robot file"),
    session: AsyncSession = Depends(get_db),
):
    # Validate extension
    if not file.filename.lower().endswith('.robot'):
        raise HTTPException(400, detail={"error": "invalid_extension", "message": "只接受 .robot 檔案"})
    
    # Read and validate content
    content = await file.read()
    if len(content) > 500 * 1024:
        raise HTTPException(413, detail={"error": "file_too_large", "message": "檔案超過 500KB 限制"})
    
    try:
        rf_code = content.decode('utf-8')
    except UnicodeDecodeError:
        # Try fallback encodings
        for encoding in ['utf-8-sig', 'big5', 'gbk']:
            try:
                rf_code = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise HTTPException(400, detail={"error": "encoding_error", "message": "無法解碼檔案內容"})
    
    # Store via RobotScriptRepository
    # ... existing upsert logic
```

### Alternatives Considered
- **Base64 in JSON**: Increases payload size ~33%, less efficient
- **Separate upload service**: Over-engineering for single file type

---

## 4. Existing Codebase Patterns

### File Upload Patterns (from `media_service.py`, `file_parser_service.py`)
- `MediaService.upload_attachment()` handles file saving with size limits
- `FileParserService` validates file sizes before parsing
- Pattern: Service layer handles business logic, API layer handles HTTP concerns

### AI Service Patterns (from `ai_service.py`)
- `AIService` wraps LLM providers with caching
- `chat_and_generate_rf` handles structured chat responses
- Provider abstraction via `LLMProvider` protocol

### RF Code Storage Patterns (from `cases.py`, `robot_script_repo.py`)
- `RobotScriptRepository.upsert()` handles DB + disk sync
- `cases.py:583-639` has existing save/get endpoints for RF code
- Disk sync at `robot_scripts/{case_number}.robot`

---

## 5. UI/UX Considerations

### Upload Component Flow
1. User clicks "Upload RF Code" button in test case form
2. File picker filters for `.robot` files
3. On selection: validate client-side (extension, size)
4. Upload via API, show progress
5. On success: populate Monaco Editor with content
6. User can edit, then save test case (saves edited version)

### Context Scope Selector (per Q1=C)
- Dropdown in AI Chat header: "RF Code Context: Full / Summary / None"
- Default: "Full" (matches current behavior expectation)
- Persists per chat session (localStorage or session state)

---

## 6. Testing Strategy

### Unit Tests
- `RFCodeEditor.vue`: Monaco initialization, language registration, content sync
- `RFCodeUpload.vue`: File validation, upload handling, error states
- `ai_service.py`: Context injection with different modes
- `case_service.py`: Upload handling, validation, storage

### Integration Tests
- API: Upload → save → retrieve → chat with context
- AI: Verify RF code appears in provider requests

### E2E Tests
- Full flow: Create case → upload .robot → edit → save → chat → verify context

---

## 7. Dependencies

### New Dependencies
```json
// frontend/package.json
{
  "dependencies": {
    "monaco-editor": "^0.50.0",
    "@monaco-editor/loader": "^1.4.0"
  }
}
```

### No New Backend Dependencies
- Reuses existing: FastAPI, SQLAlchemy, aiofiles

---

## 8. Migration Notes

- No database migration needed (uses existing `robot_scripts` table)
- No breaking API changes (new endpoint additive, existing chat endpoint backward compatible)
- Frontend: New components, existing pages extended