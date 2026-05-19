"""Unit tests for ReportService.
RED: Tests should fail until the service is implemented.
"""

import pytest

from src.services.report_service import ReportService

SAMPLE_OUTPUT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<robot generator="Robot 7.0" rpa="false" schemaversion="5">
<suite name="Test Suite" source="/tmp/test.robot">
<test id="s1-t1" name="Login Test">
  <kw name="Log" library="BuiltIn">
    <msg timestamp="20260519 10:00:00.100" level="INFO">Hello</msg>
    <status status="PASS" starttime="20260519 10:00:00.100" endtime="20260519 10:00:00.150"/>
  </kw>
  <status status="PASS" starttime="20260519 10:00:00.100" endtime="20260519 10:00:00.200"/>
</test>
<status status="PASS" starttime="20260519 10:00:00.000" endtime="20260519 10:00:00.200"/>
</suite>
<statistics>
<total><stat pass="1" fail="0" skip="0">All Tests</stat></total>
</statistics>
<errors/>
</robot>
"""

FAILED_OUTPUT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<robot generator="Robot 7.0" rpa="false" schemaversion="5">
<suite name="Test Suite" source="/tmp/test.robot">
<test id="s1-t1" name="Failing Test">
  <kw name="Should Be Equal" library="BuiltIn">
    <msg timestamp="20260519 10:00:00.100" level="FAIL">1 != 2</msg>
    <status status="FAIL" starttime="20260519 10:00:00.100" endtime="20260519 10:00:00.150"/>
  </kw>
  <status status="FAIL" starttime="20260519 10:00:00.100" endtime="20260519 10:00:00.200"/>
</test>
<status status="FAIL" starttime="20260519 10:00:00.000" endtime="20260519 10:00:00.200"/>
</suite>
<statistics>
<total><stat pass="0" fail="1" skip="0">All Tests</stat></total>
</statistics>
<errors/>
</robot>
"""


class TestXMLParsing:
    def test_parse_passing_test(self):
        service = ReportService()
        result = service.parse_xml(SAMPLE_OUTPUT_XML)
        assert result["status"] == "passed"
        assert result["passed_count"] == 1
        assert result["failed_count"] == 0

    def test_parse_failing_test(self):
        service = ReportService()
        result = service.parse_xml(FAILED_OUTPUT_XML)
        assert result["status"] == "failed"
        assert result["failed_count"] == 1
        assert result["failure_message"] is not None

    def test_parse_elapsed_ms(self):
        service = ReportService()
        result = service.parse_xml(SAMPLE_OUTPUT_XML)
        assert isinstance(result["elapsed_ms"], int)
        assert result["elapsed_ms"] >= 0


class TestStatusMapping:
    def test_pass_maps_to_passed(self):
        service = ReportService()
        assert service._map_status("PASS") == "passed"

    def test_fail_maps_to_failed(self):
        service = ReportService()
        assert service._map_status("FAIL") == "failed"

    def test_skip_maps_to_skipped(self):
        service = ReportService()
        assert service._map_status("SKIP") == "skipped"


class TestMediaPathExtraction:
    def test_extract_screenshot_paths(self):
        xml = """<?xml version="1.0"?>
<robot generator="Robot 7.0"><suite name="S"><test id="s1-t1" name="T">
  <kw name="Take Screenshot">
    <msg timestamp="20260519 10:00:00.100" level="INFO">screenshot-001.png</msg>
    <status status="PASS" starttime="20260519 10:00:00.100" endtime="20260519 10:00:00.200"/>
  </kw>
  <status status="PASS" starttime="20260519 10:00:00.100" endtime="20260519 10:00:00.200"/>
</test><status status="PASS" starttime="20260519 10:00:00.000" endtime="20260519 10:00:00.200"/>
</suite><statistics><total><stat pass="1" fail="0" skip="0">All Tests</stat></total></statistics>
<errors/></robot>"""
        service = ReportService()
        paths = service.extract_media_paths(xml)
        assert any("screenshot" in p.lower() or ".png" in p.lower() for p in paths)


class TestExportReport:
    def test_export_returns_html_string(self):
        service = ReportService()
        execution_data = {
            "id": "exec-001",
            "status": "completed",
            "passed_count": 3,
            "failed_count": 1,
            "total_count": 4,
            "elapsed_ms": 5000,
        }
        case_results = [
            {"case_name": "Test 1", "status": "passed", "elapsed_ms": 1200, "failure_message": None, "media": []},
            {"case_name": "Test 2", "status": "failed", "elapsed_ms": 800, "failure_message": "Assertion failed", "media": []},
        ]
        html = service.export_report(execution_data, case_results)
        assert "<html" in html.lower()
        assert "exec-001" in html
        assert "passed" in html.lower() or "failed" in html.lower()
