"""
Load test: SC-012 — CSV/Excel 解析 1000 筆資料應在 5 秒內完成。
驗證標準：FileParserService.parse_excel() 處理真實 1000 列 .xlsx 檔案耗時 ≤ 5s。
"""
import asyncio
import io
import time

import pytest

from src.services.file_parser_service import FileParserService

ROW_COUNT = 1000
THRESHOLD_S = 5.0


def generate_excel_bytes(row_count: int) -> bytes:
    """生成含 row_count 列測試資料的真實 .xlsx 檔案（使用 openpyxl）。"""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["username", "password", "email", "role", "department"])

    for i in range(row_count):
        ws.append([
            f"user{i:04d}",
            f"P@ss{i:04d}!",
            f"user{i:04d}@company.example.com",
            "tester" if i % 3 != 0 else "admin",
            f"Dept-{i % 10:02d}",
        ])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_excel_parse_1000_rows_within_5s():
    """SC-012: 解析 1000 列 Excel 資料應在 5 秒內完成。"""
    service = FileParserService()
    excel_data = generate_excel_bytes(ROW_COUNT)

    start = time.perf_counter()
    result = await service.parse_excel(excel_data)
    elapsed = time.perf_counter() - start

    print(
        f"\nExcel 解析時間: {elapsed * 1000:.1f}ms"
        f"（{ROW_COUNT} 筆資料，5 欄；門檻: {THRESHOLD_S}s）"
    )

    assert elapsed <= THRESHOLD_S, (
        f"Excel 解析時間 {elapsed:.3f}s 超過門檻 {THRESHOLD_S}s — SC-012 FAIL"
    )
    assert result["total_rows"] == ROW_COUNT, (
        f"解析結果應為 {ROW_COUNT} 列，實際: {result['total_rows']}"
    )
    assert len(result["columns"]) == 5, (
        f"應解析出 5 個欄位，實際: {len(result['columns'])}"
    )
    assert "username" in result["columns"], "應包含 'username' 欄位"


@pytest.mark.asyncio
async def test_excel_parse_preview_contains_first_10_rows():
    """SC-012: parse_excel 回傳的 preview 應包含前 10 列資料。"""
    service = FileParserService()
    excel_data = generate_excel_bytes(ROW_COUNT)

    result = await service.parse_excel(excel_data)

    assert len(result["preview"]) <= 10, "preview 最多回傳 10 列"
    assert len(result["preview"]) > 0, "preview 不應為空"
    first_row = result["preview"][0]
    assert "username" in first_row, "preview 第一列應包含 'username' 欄位"
    assert first_row["username"] == "user0000", "第一筆資料的 username 應為 user0000"


@pytest.mark.asyncio
async def test_csv_parse_1000_rows_within_5s():
    """SC-012: 解析 1000 列 CSV 資料應在 5 秒內完成。"""
    service = FileParserService()

    lines = ["username,password,email,role,department"]
    for i in range(ROW_COUNT):
        lines.append(
            f"user{i:04d},P@ss{i:04d}!,user{i:04d}@company.example.com,"
            f"{'admin' if i % 3 == 0 else 'tester'},Dept-{i % 10:02d}"
        )
    csv_data = "\n".join(lines).encode("utf-8")

    start = time.perf_counter()
    result = await service.parse_csv(csv_data)
    elapsed = time.perf_counter() - start

    print(
        f"\nCSV 解析時間: {elapsed * 1000:.1f}ms"
        f"（{ROW_COUNT} 筆資料；門檻: {THRESHOLD_S}s）"
    )

    assert elapsed <= THRESHOLD_S, (
        f"CSV 解析時間 {elapsed:.3f}s 超過門檻 {THRESHOLD_S}s — SC-012 FAIL"
    )
    assert result["total_rows"] == ROW_COUNT
