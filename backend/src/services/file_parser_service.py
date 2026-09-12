import csv
import io
import uuid
from typing import Optional


class FileParserService:
    # Default 10MB limit, can be overridden per call
    MAX_FILE_SIZE = 10 * 1024 * 1024
    MAX_ROWS = 5000
    MAX_COLS = 50

    def _generate_import_token(self) -> str:
        return str(uuid.uuid4())

    def _sanitize_rows(self, data_rows: list[dict]) -> tuple[list[dict], list[str]]:
        """截斷超大匯入並對 Excel 公式前綴發出警告（防 CSV formula injection）。"""
        warnings: list[str] = []
        if len(data_rows) > self.MAX_ROWS:
            warnings.append(f"rows_truncated: only first {self.MAX_ROWS} rows kept")
            data_rows = data_rows[: self.MAX_ROWS]
        for row in data_rows:
            if len(row) > self.MAX_COLS:
                warnings.append("cols_truncated: too many columns")
                break
        has_formula = any(
            isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "|")
            for row in data_rows[:100]
            for v in row.values()
        )
        if has_formula:
            warnings.append("formula_cells: cells starting with =,+,-,@,| are kept as text; review before opening in Excel")
        return data_rows, warnings

    def _check_file_size(self, data: bytes) -> None:
        if len(data) > self.MAX_FILE_SIZE:
            raise ValueError(f"file_too_large: File size {len(data)} bytes exceeds limit {self.MAX_FILE_SIZE} bytes")

    async def parse_excel(self, data: bytes) -> dict:
        self._check_file_size(data)
        try:
            import openpyxl
        except ImportError as e:
            raise ImportError("openpyxl is required for Excel parsing") from e

        if not data:
            raise ValueError("empty_file")

        try:
            wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True)
        except Exception as e:
            raise ValueError("invalid_format") from e

        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            raise ValueError("empty_file")
        if len(rows) > self.MAX_ROWS + 1:
            rows = rows[: self.MAX_ROWS + 1]

        headers = [str(h) if h is not None else "" for h in rows[0]][: self.MAX_COLS]
        data_rows = [
            {headers[i]: (str(v) if v is not None else "") for i, v in enumerate(row[: self.MAX_COLS])}
            for row in rows[1:]
            if any(v is not None for v in row)
        ]
        data_rows, warnings = self._sanitize_rows(data_rows)

        preview = data_rows[:10]
        return {
            "columns": headers,
            "preview": preview,
            "total_rows": len(data_rows),
            "warnings": warnings,
            "import_token": self._generate_import_token(),
            "_rows": data_rows,
        }

    async def parse_csv(self, data: bytes, delimiter: str = ",") -> dict:
        self._check_file_size(data)
        if not data:
            raise ValueError("empty_file")

        text = data.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        headers = list(reader.fieldnames or [])[: self.MAX_COLS]
        data_rows = []
        for row in reader:
            data_rows.append({k: row.get(k, "") for k in headers})
            if len(data_rows) >= self.MAX_ROWS:
                break
        data_rows, warnings = self._sanitize_rows(data_rows)

        preview = data_rows[:10]
        return {
            "columns": list(headers),
            "preview": preview,
            "total_rows": len(data_rows),
            "warnings": warnings,
            "import_token": self._generate_import_token(),
            "_rows": data_rows,
        }

    async def parse_text(self, data: bytes, delimiter: Optional[str] = None) -> dict:
        self._check_file_size(data)
        if not data:
            raise ValueError("empty_file")
        auto_delimiter = "\t" if b"\t" in data else ","
        return await self.parse_csv(data, delimiter=delimiter or auto_delimiter)

    async def parse_file(self, filename: str, data: bytes) -> dict:
        lower = filename.lower()
        if lower.endswith(".xlsx") or lower.endswith(".xls"):
            return await self.parse_excel(data)
        if lower.endswith(".csv"):
            return await self.parse_csv(data)
        return await self.parse_text(data)
