# Quickstart: RF Code Upload and AI Integration

**Feature**: RF Code Upload and AI Integration  
**Date**: 2026-09-10

## Prerequisites

- Backend running: `cd backend && python -m src.main`
- Frontend running: `cd frontend && npm run dev`
- User with editor role logged in
- Existing test case or permission to create new ones

---

## Test Scenario 1: Upload RF Code in Test Case Creation

### Steps
1. Navigate to **測試案例** → **新增測試案例**
2. Fill in required fields:
   - 名稱: `登入功能測試`
   - 系統分類: `Web`
   - 主要步驟: `1. 開啟登入頁面\n2. 輸入帳號密碼\n3. 點擊登入\n4. 驗證登入成功`
3. Click **上傳 RF 程式碼** button
4. Select a `.robot` file (e.g., `login_test.robot`)
5. Verify:
   - File name shows in upload area
   - Monaco Editor opens with file content
   - Syntax highlighting works (keywords, strings, comments colored)
6. Optionally edit the code in the editor
7. Click **儲存** to create test case
8. Verify success toast/message
9. Navigate to case detail, verify RF code displays correctly

### Expected Result
- Test case created with RF code stored in database
- RF code synced to `robot_scripts/TC-XXX.robot` on disk
- Monaco Editor shows uploaded content with Robot Framework syntax highlighting

---

## Test Scenario 2: Add RF Code to Existing Test Case

### Steps
1. Navigate to existing test case detail page
2. Click **編輯** button
3. Click **上傳 RF 程式碼** in the edit form
4. Select `.robot` file
5. Verify preview loads in Monaco Editor
6. Make a small edit (e.g., add a comment line)
7. Click **更新** to save
8. Verify RF code updated (check case detail or GET `/robot-script`)

### Expected Result
- Existing test case now has RF code
- RF code overwrites any previous version (per Q3=A)
- Disk file updated at `robot_scripts/TC-XXX.robot`

---

## Test Scenario 3: AI Chat with RF Code Context

### Steps
1. Open test case that has RF code uploaded
2. Click **AI 對話** button to open chat panel
3. Verify RF context indicator shows (e.g., "RF 程式碼: 完整模式")
4. Send message: `這段 RF 代碼的主要功能是什麼？`
5. Verify AI response references the uploaded code
6. Send message: `如何加入登入前的前置條件？`
7. Verify AI suggests modifications integrating with existing code
8. Change context mode to **摘要模式** via dropdown
9. Send message: `請用一句話說明這段代碼`
10. Verify AI uses summary context

### Expected Result
- AI correctly references uploaded RF code
- Context mode selector works (完整/摘要/無)
- Backward compatibility: cases without RF code work normally

---

## Test Scenario 4: File Validation

### Steps
1. Try uploading `.txt` file → Verify rejection with "只接受 .robot 檔案"
2. Try uploading 1MB `.robot` file → Verify rejection with "檔案超過 500KB 限制"
3. Try uploading `.robot` file with Big5 encoding → Verify fallback decoding works
4. Try uploading empty `.robot` file → Verify handled gracefully

### Expected Result
- Clear error messages for each validation failure
- No invalid files stored in database

---

## Test Scenario 5: Clear RF Code

### Steps
1. Edit test case with existing RF code
2. Clear Monaco Editor content (Select All → Delete)
3. Save test case
4. Verify RF code removed (GET `/robot-script` returns 404)
5. Disk file `robot_scripts/TC-XXX.robot` should be deleted

### Expected Result
- RF code optional field can be cleared
- Database record deleted, disk file removed

---

## API Testing (curl)

### Upload RF Script
```bash
curl -X POST "http://localhost:8000/api/v1/cases/{CASE_ID}/robot-script/upload" \
  -H "Authorization: Bearer {TOKEN}" \
  -F "file=@login_test.robot"
```

### Save Edited RF Code
```bash
curl -X PUT "http://localhost:8000/api/v1/cases/{CASE_ID}/robot-script" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"rf_code": "*** Settings ***\nLibrary    Browser\n\n*** Test Cases ***\n測試案例\n    Log    Hello World"}'
```

### AI Chat with Context
```bash
curl -X POST "http://localhost:8000/api/v1/cases/{CASE_ID}/chat" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"message": "解釋這段代碼", "rf_context_mode": "full"}'
```

---

## Verification Checklist

- [ ] File upload accepts only `.robot` files
- [ ] File size limit enforced (500KB)
- [ ] UTF-8 decoding with fallback works
- [ ] Monaco Editor loads with syntax highlighting
- [ ] Edited code saves correctly (not original upload)
- [ ] RF code stored in DB and synced to disk
- [ ] AI chat receives RF context in system prompt
- [ ] Context mode selector (full/summary/none) works
- [ ] Cases without RF code work unchanged
- [ ] Clear RF code removes DB record and disk file
- [ ] Proper error messages for all failure cases
- [ ] Editor role required for upload/save