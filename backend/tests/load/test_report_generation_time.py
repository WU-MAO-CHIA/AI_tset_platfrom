"""
Load test: SC-005 — 系統在 30 秒內完成含 5 個案例的 HTML 報告生成。
驗證標準：ReportService.export_report() 呼叫耗時 ≤ 30s。
"""
import time

import pytest

from src.services.report_service import ReportService

CASE_COUNT = 5
THRESHOLD_S = 30.0


def _make_execution_data(exec_id: str) -> dict:
    return {
        "id": exec_id,
        "status": "completed",
        "started_at": "2026-06-13T10:00:00",
        "finished_at": "2026-06-13T10:02:30",
        "passed_count": 4,
        "failed_count": 1,
        "total_count": CASE_COUNT,
    }


def _make_case_results(count: int) -> list[dict]:
    results = []
    for i in range(count):
        is_failed = (i == 2)
        results.append({
            "case_name": f"測試案例 {i + 1:03d}",
            "case_number": f"TC-{i + 1:03d}",
            "status": "failed" if is_failed else "passed",
            "elapsed_ms": 3200 + i * 150,
            "failure_message": "Element not found: role=button[name='提交']" if is_failed else None,
            "media": [
                {"id": f"media-{i}-{j}", "media_type": "screenshot", "url": f"/api/v1/media/results/exec-001/screenshots/step{j}.png", "step_index": j}
                for j in range(3)
            ],
        })
    return results


def test_report_generation_within_30s():
    """SC-005: 含 5 個案例的報告生成應在 30 秒內完成。"""
    service = ReportService()
    execution_data = _make_execution_data("exec-load-test-001")
    case_results = _make_case_results(CASE_COUNT)

    start = time.perf_counter()
    html = service.export_report(execution_data, case_results)
    elapsed = time.perf_counter() - start

    print(f"\n報告生成時間: {elapsed * 1000:.1f}ms（含 {CASE_COUNT} 個案例；門檻: {THRESHOLD_S}s）")

    assert elapsed <= THRESHOLD_S, (
        f"報告生成時間 {elapsed:.2f}s 超過門檻 {THRESHOLD_S}s — SC-005 FAIL"
    )
    assert len(html) > 0, "報告 HTML 不應為空"
    assert "執行報告" in html or "exec-load-test-001" in html, "報告內容不包含預期的執行資訊"


def test_report_contains_all_case_results():
    """SC-005: 報告應包含全部 5 個案例的結果資料。"""
    service = ReportService()
    execution_data = _make_execution_data("exec-load-test-002")
    case_results = _make_case_results(CASE_COUNT)

    html = service.export_report(execution_data, case_results)

    for i in range(CASE_COUNT):
        assert f"測試案例 {i + 1:03d}" in html, f"報告缺少案例 {i + 1} 的資料"
