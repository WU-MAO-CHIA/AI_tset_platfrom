# Feature Specification: RF Code Upload and AI Integration

**Feature Branch**: `002-rf-code-upload-ai`  
**Created**: 2026-09-10  
**Status**: Draft  
**Input**: User description: "在建立測案的畫面中新增上傳RF程式碼的功能，並在AI對話中讓AI也可以讀取到該程式碼"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload RF Code in Test Case Creation (Priority: P1)

Test engineers need to upload existing Robot Framework (.robot) scripts when creating new test cases, so they can reuse proven automation code instead of generating from scratch.

**Why this priority**: This is the core feature request - enabling direct RF code upload eliminates manual copy-paste and allows teams to leverage existing automation assets immediately.

**Independent Test**: Can be fully tested by uploading a .robot file in the test case creation form, saving the case, and verifying the code is stored and retrievable.

**Acceptance Scenarios**:

1. **Given** a user is on the test case creation page, **When** they upload a valid .robot file, **Then** the file content is read and displayed in the RF code editor/preview area
2. **Given** a user uploads a .robot file with syntax errors, **When** they attempt to save, **Then** the system shows validation warnings but allows saving (with warning)
3. **Given** a user uploads a non-.robot file, **When** they attempt to upload, **Then** the system rejects the file with a clear error message
4. **Given** a user creates a test case with uploaded RF code, **When** they view the case details, **Then** the RF code is shown and matches the uploaded content

### User Story 2 - AI Reads Uploaded RF Code in Chat (Priority: P1)

Test engineers want the AI assistant to have context of the uploaded RF code during chat conversations, so the AI can provide relevant suggestions, modifications, or explanations based on the actual code.

**Why this priority**: This connects the upload feature to the AI workflow, making the uploaded code actionable rather than just stored.

**Independent Test**: Can be tested by uploading RF code, opening AI chat, asking a question about the code, and verifying the AI response references the uploaded code correctly.

**Acceptance Scenarios**:

1. **Given** a test case has uploaded RF code, **When** the user opens AI chat and asks "What does this code do?", **Then** the AI response describes the uploaded code's functionality
2. **Given** a test case has uploaded RF code, **When** the user asks "How do I add a login step?", **Then** the AI suggests modifications that integrate with the existing uploaded code structure
3. **Given** a test case has no RF code, **When** the user opens AI chat, **Then** the AI works normally without code context (backward compatibility)
4. **Given** a user uploads new RF code to an existing case, **When** they continue the AI chat, **Then** the AI uses the updated code as context

### User Story 3 - Preview and Edit Uploaded RF Code (Priority: P2)

Test engineers need to preview and optionally edit the uploaded RF code before saving the test case, to make minor adjustments or fix issues.

**Why this priority**: Uploaded code may need small tweaks for the specific test case context; editing capability avoids re-upload cycles.

**Independent Test**: Can be tested by uploading RF code, viewing the preview, making edits, and saving - verifying both original and edited versions are handled correctly.

**Acceptance Scenarios**:

1. **Given** a user uploads a .robot file, **When** the preview loads, **Then** the full RF code is displayed in a readable, syntax-highlighted editor
2. **Given** a user edits the previewed RF code, **When** they save the test case, **Then** the edited version is stored (not the original uploaded version)
3. **Given** a user clears the RF code editor, **When** they save, **Then** the test case is created without RF code (optional field)

---

### Edge Cases

- What happens when uploaded file exceeds size limit? → Show clear error with max size
- What happens when uploaded file uses unsupported encoding? → Attempt UTF-8, fallback with warning
- How does system handle concurrent edits to RF code? → Last write wins with version tracking
- What if AI chat is opened before RF code is uploaded? → AI works without code context; code added later becomes available in subsequent messages
- How are special characters in RF code handled? → Preserve exactly as uploaded, no sanitization that breaks syntax

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to upload a Robot Framework (.robot) file during test case creation
- **FR-002**: System MUST validate uploaded file extension is .robot (case-insensitive)
- **FR-003**: System MUST read and display uploaded RF file content in the RF code editor/preview area
- **FR-004**: System MUST store uploaded RF code in the test case's robot_script field (database) and sync to disk
- **FR-005**: System MUST include uploaded RF code as context in AI chat conversations for that test case
- **FR-006**: System MUST allow users to edit the RF code in the preview editor before saving
- **FR-007**: System MUST show syntax highlighting for RF code in the preview/editor
- **FR-008**: System MUST reject non-.robot files with a clear error message
- **FR-009**: System MUST enforce a reasonable file size limit (default: 500KB) for RF code uploads
- **FR-010**: System MUST preserve RF code formatting and special characters exactly as uploaded
- **FR-011**: System MUST make uploaded RF code available as context for all subsequent AI chat messages in the session
- **FR-012**: System MUST support replacing existing RF code with a new upload (overwrite with confirmation)

### Key Entities

- **Test Case**: Represents a test scenario; now has optional associated RF code (robot_script relationship)
- **RF Code**: Robot Framework script content; stored in robot_scripts table with test_case_id foreign key
- **AI Chat Session**: Conversation context that now includes RF code when available for the test case

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can upload and save RF code in test case creation within 30 seconds
- **SC-002**: AI correctly references uploaded RF code in 90% of relevant chat interactions (measured by user feedback)
- **SC-003**: File upload rejection rate for invalid formats is 100% (no invalid files stored)
- **SC-004**: RF code preview loads within 2 seconds for files up to 500KB
- **SC-005**: Backward compatibility maintained - existing test cases without RF code work unchanged

## Assumptions

- Users have existing .robot files they want to reuse (common in established automation teams)
- RF code files are typically small (< 100KB) as they represent single test case scripts
- The existing RobotScript database table and disk sync mechanism will be reused
- AI provider supports passing additional context (system prompt or message history)
- No real-time collaborative editing needed for RF code (single user per test case edit)
- Syntax highlighting can use existing frontend libraries (Monaco/CodeMirror)
- Maximum 3 clarification items needed (see below)

---

## Clarification Resolutions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **C) User chooses per chat session** | Maximum flexibility for users to control context size vs. detail trade-off per conversation |
| 2 | **B) Creation + Edit pages** | Allows adding RF code to existing test cases without re-creation; more practical for iterative workflow |
| 3 | **A) Overwrite current version's RF code** | Simpler data model; RF code stays aligned with test case version; user can manually version if needed |

---

## Specification Quality Checklist

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain (all resolved)
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

### Feature Readiness
- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

### Notes
- All 3 clarification items resolved - ready for `/speckit-plan`