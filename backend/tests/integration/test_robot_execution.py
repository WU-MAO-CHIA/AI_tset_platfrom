"""Integration tests for Robot Framework subprocess execution.
RED: Tests should fail until execution_service is fully implemented.

Note: These tests use simple RF .robot scripts that don't require Browser/Playwright.
They test the subprocess execution pattern and output.xml parsing.
"""

import os
import pytest
import tempfile
from pathlib import Path

from src.services.execution_service import ExecutionService


SIMPLE_PASS_ROBOT = """\
*** Settings ***
Library    BuiltIn

*** Test Cases ***
Simple Passing Test
    Log    This test passes
    Should Be Equal    1    1
"""

SIMPLE_FAIL_ROBOT = """\
*** Settings ***
Library    BuiltIn

*** Test Cases ***
Simple Failing Test
    Log    This test fails
    Should Be Equal    1    2
"""


@pytest.fixture
def tmp_robot_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


class TestRobotSubprocessExecution:
    async def test_run_passing_robot_returns_pass(self, tmp_robot_dir):
        robot_file = tmp_robot_dir / "pass_test.robot"
        robot_file.write_text(SIMPLE_PASS_ROBOT)
        output_xml = tmp_robot_dir / "output.xml"

        service = ExecutionService(None)
        result = await service._execute_robot_subprocess(
            robot_file=str(robot_file),
            output_xml=str(output_xml),
            timeout_sec=30,
        )
        assert result["status"] == "passed"
        assert output_xml.exists()

    async def test_run_failing_robot_returns_fail(self, tmp_robot_dir):
        robot_file = tmp_robot_dir / "fail_test.robot"
        robot_file.write_text(SIMPLE_FAIL_ROBOT)
        output_xml = tmp_robot_dir / "output.xml"

        service = ExecutionService(None)
        result = await service._execute_robot_subprocess(
            robot_file=str(robot_file),
            output_xml=str(output_xml),
            timeout_sec=30,
        )
        assert result["status"] == "failed"
        assert result["failure_message"] is not None

    async def test_parse_output_xml_after_execution(self, tmp_robot_dir):
        robot_file = tmp_robot_dir / "parse_test.robot"
        robot_file.write_text(SIMPLE_PASS_ROBOT)
        output_xml = tmp_robot_dir / "output.xml"

        service = ExecutionService(None)
        await service._execute_robot_subprocess(
            robot_file=str(robot_file),
            output_xml=str(output_xml),
            timeout_sec=30,
        )

        from src.services.report_service import ReportService
        report = ReportService()
        xml_content = output_xml.read_text(encoding="utf-8")
        parsed = report.parse_xml(xml_content)
        assert parsed["passed_count"] >= 1
