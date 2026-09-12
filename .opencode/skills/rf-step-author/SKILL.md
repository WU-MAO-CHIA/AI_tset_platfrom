---
name: rf-step-author
description: Generate Robot Framework keywords and steps from natural-language checklist items, following this project's locator and library conventions. Trigger when editing .robot files, files under backend/robot_scripts/ or backend/templates/, when the user mentions "RF step", "robot framework", "checklist 轉換", or when generating test scripts from a Checklist record.
---

# Robot Framework Step Author

Specialised expertise for producing high-quality Robot Framework test scripts in this project.

## Project Context

- **Test runtime**: Robot Framework 7.1 + `robotframework-browser` (Playwright-based)
- **Scripts location**: `backend/robot_scripts/` (generated outputs) and `backend/templates/` (Jinja2 templates)
- **Source**: RF scripts are generated from Checklist items by the LLM service in `backend/src/services/`
- **Execution**: Async pipeline triggered from the FastAPI executor; results stored back to DB

## Conventions

1. **Library choice**: Prefer **Browser** library (`Library  Browser`) over SeleniumLibrary for new scripts. Do not mix both in a single suite.
2. **Locator strategy** (in order of preference):
   - `role=button[name="送出"]` / `role=textbox[name="..."]` — Browser library `GetByRole`
   - `text="可見文字"` — when role is ambiguous
   - `id=*`, `data-testid=*` — for stable hooks
   - **Avoid**: brittle XPath (`//div[3]/span[1]`), absolute CSS paths
3. **Waits**: every interaction MUST be preceded by an explicit wait or use Browser's auto-wait keywords (`Click`, `Fill Text`). Never use `Sleep` to wait for UI.
4. **Resource files**: repeated 3+ step sequences become a user keyword in a `*.resource` file under `backend/robot_scripts/resources/`.
5. **Variables**: page URLs, timeouts, and credentials go in `*** Variables ***` section or `${ENV}` injected from `.env` via Robot CLI args.

## Step Generation Workflow

When converting a Checklist item to RF steps:

1. **Read** the related Checklist (`backend/src/models/checklist.py`) and TestCase to understand pre-conditions.
2. **Identify** the page object — find the matching `.vue` page under `frontend/src/pages/` to extract real locators.
3. **Draft** Settings / Variables / Test Cases sections following the skeleton:
   ```robot
   *** Settings ***
   Library     Browser
   Resource    resources/common.resource
   Test Setup       Open Browser To Login Page
   Test Teardown    Close Browser

   *** Variables ***
   ${BASE_URL}      http://localhost:5173

   *** Test Cases ***
   <case name>
       [Documentation]    <one-line summary from checklist>
       [Tags]    <feature-tag>
       <Given step>
       <When step>
       <Then step>
   ```
4. **Verify** each locator against the actual Vue component (Grep the page file for the role/text/id).
5. **Self-review** before returning: pass each step through the checklist below.

## Quality Checklist (always run before returning)

- [ ] No `Sleep` statements
- [ ] No absolute XPath
- [ ] Each `*** Test Cases ***` entry has `[Documentation]` and `[Tags]`
- [ ] Repeated step sequences extracted into `.resource` file
- [ ] Variables are not hard-coded secrets
- [ ] Library declared exactly once
- [ ] Locators verified against the actual frontend code

## Anti-patterns (refuse to emit)

- Mixing SeleniumLibrary and Browser
- Using `Run Keyword If` for trivial branching (prefer keyword decomposition)
- Hard-coded `localhost:port` URLs (use `${BASE_URL}`)
- Login credentials embedded inline (use `${USERNAME}` / `${PASSWORD}` variables)
