# Spec Quality Checklist: 自動化測試平台

**Purpose**: 以「需求文件單元測試」的視角，驗證 spec.md 的完整性、清晰度、一致性與可測量性，作為 PR review 標準門檻
**Created**: 2026-05-21
**Feature**: [spec.md](../spec.md)
**Depth**: Standard PR review gate
**Focus**: 規格完整性 & 一致性（含 /speckit-analyze 發現的 6 項已知問題）

---

## Requirement Completeness（需求完整性）

- [ ] CHK001 - 每條功能需求（FR-001 至 FR-022）是否都能在至少一個 User Story 的驗收情境（Acceptance Scenario）中找到對應的使用者動作？ [Completeness, Spec §US1-US5]
- [ ] CHK002 - FR-001 所列的測試案例表單欄位（編號、名稱、說明…版本號）是否在 spec.md 正文中明確列舉，而非僅依賴 data-model.md 推導？ [Completeness, Spec §FR-001]
- [x] CHK003 - FR-014（刪除測試案例）的需求是否完整涵蓋以下三種狀態：未被引用、已被引用、執行中？ [Completeness, Spec §FR-014]
- [ ] CHK004 - FR-017（立即試跑）的需求是否明確說明試跑結果的儲存期限或清理策略，避免資料無限累積？ [Completeness, Gap]
- [ ] CHK005 - spec.md 是否定義了全域導覽列（FR-022）在行動裝置或小螢幕下的行為（摺疊、隱藏、漢堡選單）？ [Completeness, Gap, Spec §FR-022]

---

## Requirement Clarity（需求清晰度）

- [ ] CHK006 - FR-009「即時進度」是否量化了最低更新頻率或推送延遲上限（如每秒至少一次事件）？ [Clarity, Spec §FR-009]
- [ ] CHK007 - SC-006「不出現效能衰退」是否以可測量的指標定義（如 p95 回應時間 ≤ X ms），而非模糊的質化描述？ [Clarity, Ambiguity, Spec §SC-006]
- [x] CHK008 - FR-012「至少兩種主流 LLM 模型」是否明確列舉初期必須支援的模型名稱，而非留待實作自行決定？ [Clarity, Spec §FR-012]
- [ ] CHK009 - FR-016「AI 自動將自然語言步驟翻譯為可執行的自動化測試代碼」是否定義了可接受的代碼格式或框架（Robot Framework）？ [Clarity, Spec §FR-016]
- [ ] CHK010 - FR-018 的「欄位對應機制」是否描述了當標頭無法對應時的預期行為（拒絕匯入 vs. 允許跳過 vs. 提示手動選擇）？ [Clarity, Spec §FR-018]

---

## Requirement Consistency（需求一致性）

- [x] CHK011 - SC-010「AI 代碼生成 ≤ 30 秒」是否已更新為 35 秒以符合 T082 的實作逾時設定？【已知問題 I1 — 必須修正】 [Inconsistency, Spec §SC-010]
- [x] CHK012 - FR-006b（清單執行歷史顯示）是否已合併至 FR-006，消除重複定義？【已知問題 A1 — 必須修正】 [Duplication, Spec §FR-006, FR-006b]
- [x] CHK013 - Clarifications 段落中的 FR-022 引用塊是否已刪除，避免與 Functional Requirements 中的正式定義重複？【已知問題 A2 — 必須修正】 [Redundancy, Spec §Clarifications]
- [x] CHK014 - constitution.md 第 51 行「Use Python 3.14」是否已修正為「Python 3.11+」以符合 plan.md 的技術選型？【已知問題 D1 — CRITICAL，必須修正】 [Constitution Conflict, constitution.md:51]
- [ ] CHK015 - SC-005「30 秒內可供查閱或下載」的「30 秒」是否同時涵蓋頁面載入（查閱）與下載觸發兩種操作，或需分別定義各自的時間門檻？ [Clarity, Consistency, Spec §SC-005]
- [ ] CHK016 - Clarifications 段落中的 Q&A 條目是否都能在 Functional Requirements 中找到對應的正式定義（一對一可追溯）？ [Traceability, Spec §Clarifications]

---

## Success Criteria Quality（成功標準品質）

- [ ] CHK017 - SC-006（10 位使用者同時操作）是否存在對應的可建構負載測試？【已知問題 E1 — T116 待執行】 [Coverage, Spec §SC-006]
- [ ] CHK018 - SC-009（平行執行縮短 ≥ 40%）是否存在對應的可建構基準測試，且基準情境（≥ 10 個案例）已在 spec 中明確定義？【已知問題 E2 — T117 待執行】 [Coverage, Measurability, Spec §SC-009]
- [ ] CHK019 - SC-002（篩選結果 ≤ 2 秒）、SC-007（AI 補齊 ≤ 15 秒）、SC-011（試跑 ≤ 60 秒）、SC-012（解析 ≤ 5 秒）、SC-013（結果頁 ≤ 10 秒）是否各自指定了量測條件（環境規格、資料量、網路狀態）？ [Measurability, Spec §SC-002 to SC-013]
- [ ] CHK020 - SC-001（5 分鐘內完成建立案例）與 SC-004（90% 測試人員首次成功）是否定義了可重現的量測方法（如使用者測試協議），而非僅為主觀斷言？ [Measurability, Spec §SC-001, SC-004]
- [ ] CHK021 - 所有量化 SC（SC-002、SC-005、SC-007 等）是否一致採用相同的量測視角（使用者感知時間 vs. 系統內部耗時）？ [Consistency, Spec §SC-002 to SC-014]

---

## Edge Case & Scenario Coverage（邊界情境覆蓋）

- [ ] CHK022 - 是否定義了在執行進行中嘗試刪除「執行中清單所引用的測試案例」的行為？ [Edge Case, Spec §Edge Cases]
- [x] CHK023 - 是否定義了「同一測試案例的試跑已在執行中，使用者再次觸發試跑」的處理方式（拒絕 vs. 排隊 vs. 取消舊跑）？ [Edge Case, Gap]
- [x] CHK024 - 是否定義了 Excel/CSV 匯入時，測試案例已有既有測試資料的覆蓋策略（追加 vs. 取代 vs. 使用者選擇）？ [Coverage, Spec §FR-018, Gap]
- [x] CHK025 - 是否定義了兩位使用者同時執行同一份測試清單的行為（允許並行 vs. 排隊 vs. 拒絕第二次）？ [Coverage, Gap]
- [ ] CHK026 - Robot Framework subprocess 在執行途中崩潰（非逾時）的恢復需求是否在規格中明確定義？ [Coverage, Spec §Edge Cases]

---

## Assumptions & Dependencies（假設與依賴）

- [ ] CHK027 - LLM API 金鑰由管理員設定的假設是否在規格中明確說明使用者角色分界，以免開發人員對 API 金鑰存取策略做出錯誤假設？ [Assumption, Spec §Assumptions]
- [ ] CHK028 - headless Chromium 必須預先安裝於後端伺服器的部署前提條件，是否在 spec.md（而非僅 STARTUP.md）中正式記錄為系統需求？ [Dependency, Gap]
- [ ] CHK029 - DBConnection.connection_string 的加密儲存需求是否在 spec.md 中正式定義為安全需求，而非僅出現在 data-model.md 的技術說明？ [Completeness, Gap]
- [ ] CHK030 - 「使用者身份驗證屬於現有系統，不在本規格範圍內」的假設是否說明了當驗證系統不存在時的降級行為（所有人可存取 vs. 需設定代理）？ [Assumption, Spec §Assumptions]

---

## Notes

- 勾選完成項目：`- [x]`
- 發現問題時在項目後方加上具體說明
- 標注 **【必須修正】** 的項目（CHK011–CHK014）必須在合併前解決，對應 Phase 10 任務 T112–T115
- 標注 **【已知問題】** 的項目來源為 `/speckit-analyze`，對應任務已在 tasks.md Phase 10 建立
