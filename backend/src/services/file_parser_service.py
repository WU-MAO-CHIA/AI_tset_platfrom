import csv
import io
import uuid
from typing import Optional


class FileParserService:
    def _generate_import_token(self) -> str:
        return str(uuid.uuid4())

    async def parse_excel(self, data: bytes) -> dict:
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

        headers = [str(h) if h is not None else "" for h in rows[0]]
        data_rows = [
            {headers[i]: (str(v) if v is not None else "") for i, v in enumerate(row)}
            for row in rows[1:]
            if any(v is not None for v in row)
        ]

        preview = data_rows[:10]
        return {
            "columns": headers,
            "preview": preview,
            "total_rows": len(data_rows),
            "warnings": [],
            "import_token": self._generate_import_token(),
            "_rows": data_rows,
        }

    async def parse_csv(self, data: bytes, delimiter: str = ",") -> dict:
        if not data:
            raise ValueError("empty_file")

        text = data.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        headers = reader.fieldnames or []
        data_rows = [dict(row) for row in reader]

        preview = data_rows[:10]
        return {
            "columns": list(headers),
            "preview": preview,
            "total_rows": len(data_rows),
            "warnings": [],
            "import_token": self._generate_import_token(),
            "_rows": data_rows,
        }

    async def parse_text(self, data: bytes, delimiter: Optional[str] = None) -> dict:
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
