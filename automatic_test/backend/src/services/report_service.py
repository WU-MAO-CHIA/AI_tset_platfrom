import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from pathlib import Path


def _parse_rf_timestamp(ts: str) -> Optional[datetime]:
    """Parse Robot Framework timestamp: 20260519 10:00:00.100"""
    try:
        return datetime.strptime(ts.strip(), "%Y%m%d %H:%M:%S.%f")
    except (ValueError, AttributeError):
        return None


def _ts_diff_ms(start: str, end: str) -> int:
    s = _parse_rf_timestamp(start)
    e = _parse_rf_timestamp(end)
    if s and e:
        return max(0, int((e - s).total_seconds() * 1000))
    return 0


class ReportService:
    def parse_xml(self, xml_content: str) -> dict:
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError:
            return {"status": "error", "passed_count": 0, "failed_count": 0, "elapsed_ms": 0, "failure_message": "Invalid XML"}

        stats_el = root.find(".//statistics/total/stat")
        if stats_el is not None:
            passed = int(stats_el.get("pass", "0"))
            failed = int(stats_el.get("fail", "0"))
        else:
            passed = failed = 0

        status = "passed" if failed == 0 and passed > 0 else ("failed" if failed > 0 else "error")

        suite_status = root.find(".//suite/status")
        elapsed = 0
        if suite_status is not None:
            start = suite_status.get("starttime", "")
            end = suite_status.get("endtime", "")
            elapsed = _ts_diff_ms(start, end)

        # Extract failure message from first failed test
        failure_message = None
        for test in root.findall(".//test"):
            test_status = test.find("status")
            if test_status is not None and test_status.get("status") == "FAIL":
                for msg in test.findall(".//msg[@level='FAIL']"):
                    failure_message = msg.text
                    break
                if failure_message:
                    break

        return {
            "status": status,
            "passed_count": passed,
            "failed_count": failed,
            "elapsed_ms": elapsed,
            "failure_message": failure_message,
        }

    def _map_status(self, rf_status: str) -> str:
        mapping = {"PASS": "passed", "FAIL": "failed", "SKIP": "skipped"}
        return mapping.get(rf_status.upper(), "error")

    def extract_media_paths(self, xml_content: str) -> list[str]:
        paths = []
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError:
            return paths

        screenshot_kws = {"take screenshot", "capture page screenshot", "screenshot"}
        for kw in root.findall(".//kw"):
            kw_name = (kw.get("name") or "").lower()
            if any(s in kw_name for s in screenshot_kws):
                for msg in kw.findall("msg"):
                    text = msg.text or ""
                    if re.search(r"\.(png|jpg|jpeg|webp)$", text.strip(), re.IGNORECASE):
                        paths.append(text.strip())
        return paths

    def export_report(self, execution_data: dict, case_results: list[dict]) -> str:
        templates_dir = Path(__file__).parent.parent / "templates"
        if templates_dir.exists():
            env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=True)
            try:
                template = env.get_template("report.html.j2")
                return template.render(execution=execution_data, results=case_results)
            except Exception:
                pass

        # Inline fallback template
        passed = sum(1 for r in case_results if r.get("status") == "passed")
        failed = len(case_results) - passed
        rows = ""
        for r in case_results:
            status_class = "pass" if r.get("status") == "passed" else "fail"
            rows += (
                f"<tr class='{status_class}'>"
                f"<td>{r.get('case_name', '')}</td>"
                f"<td>{r.get('status', '')}</td>"
                f"<td>{r.get('elapsed_ms', 0)}ms</td>"
                f"<td>{r.get('failure_message', '') or ''}</td>"
                f"</tr>"
            )
        return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head><meta charset="UTF-8"><title>執行報告 {execution_data.get('id', '')}</title></head>
<body>
<h1>執行報告</h1>
<p>執行 ID：{execution_data.get('id', '')}</p>
<p>狀態：{execution_data.get('status', '')} | 通過：{passed} | 失敗：{failed}</p>
<table border="1">
<thead><tr><th>案例名稱</th><th>狀態</th><th>耗時</th><th>失敗訊息</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</body>
</html>"""
