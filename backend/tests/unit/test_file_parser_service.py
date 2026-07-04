"""Unit tests for FileParserService.
RED: Tests should fail until FileParserService is implemented.
"""

import io
import pytest


@pytest.fixture
def parser_service():
    from src.services.file_parser_service import FileParserService
    return FileParserService()


class TestExcelParsing:
    async def test_parse_excel_returns_preview_and_columns(self, parser_service):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["username", "password"])
        ws.append(["user1@example.com", "pass1"])
        ws.append(["user2@example.com", "pass2"])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        result = await parser_service.parse_excel(buf.read())
        assert result["columns"] == ["username", "password"]
        assert len(result["preview"]) == 2
        assert result["total_rows"] == 2


class TestCSVParsing:
    async def test_parse_csv_returns_correct_rows(self, parser_service):
        csv_data = b"username,password\nuser1@example.com,pass1\nuser2@example.com,pass2\n"
        result = await parser_service.parse_csv(csv_data)
        assert result["columns"] == ["username", "password"]
        assert result["total_rows"] == 2
        assert result["preview"][0]["username"] == "user1@example.com"

    async def test_parse_tsv_tab_separated(self, parser_service):
        tsv_data = b"username\tpassword\nuser1@example.com\tpass1\n"
        result = await parser_service.parse_csv(tsv_data, delimiter="\t")
        assert result["columns"] == ["username", "password"]
        assert result["total_rows"] == 1


class TestFormatErrors:
    async def test_empty_file_raises_error(self, parser_service):
        with pytest.raises(ValueError, match="empty_file"):
            await parser_service.parse_csv(b"")

    async def test_invalid_excel_raises_error(self, parser_service):
        with pytest.raises(ValueError, match="invalid_format"):
            await parser_service.parse_excel(b"not an excel file at all")
