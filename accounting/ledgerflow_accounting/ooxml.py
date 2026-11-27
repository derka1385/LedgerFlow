"""Minimal, read-only OOXML (xlsx) reader. Standard library only.

Used by the accounting rules and the reference verifier. It reads exact cell
snapshots (CellSnapshotV1 shape from docs/DATA_SCHEMAS.md) without openpyxl,
so it never re-serialises the workbook and never shares a parser with
generated code.
"""
from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass
from xml.etree import ElementTree as ET

NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
    "x14": "http://schemas.microsoft.com/office/spreadsheetml/2009/9/main",
    "xm": "http://schemas.microsoft.com/office/excel/2006/main",
}
# ponytail: stdlib ElementTree + size bounds; switch to defusedxml in the
# production verifier (docs/REPOSITORY.md dependency list).
MAX_PART_BYTES = 20 * 1024 * 1024
MAX_TOTAL_BYTES = 100 * 1024 * 1024
CELL_RE = re.compile(r"^([A-Z]{1,3})([0-9]{1,7})$")


class WorkbookError(ValueError):
    """Named refusal (maps to API code UNSUPPORTED_WORKBOOK / ARCHIVE_LIMIT)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Cell:
    """CellSnapshotV1: type in blank|number|text|boolean|error|formula."""

    type: str
    value: str | bool | None
    formula: str | None
    style_id: int | None

    def as_dict(self) -> dict:
        return {"type": self.type, "value": self.value, "formula": self.formula, "style_id": self.style_id}


BLANK = Cell("blank", None, None, None)


def col_to_num(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - 64)
    return n


def num_to_col(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def split_cell(ref: str) -> tuple[str, int]:
    m = CELL_RE.match(ref)
    if not m:
        raise WorkbookError("INVALID_CELL", f"Not a single A1 cell: {ref!r}")
    return m.group(1), int(m.group(2))


def expand_sqref(sqref: str) -> list[str]:
    """'A1:A3 C5' -> ['A1','A2','A3','C5'] (bounded)."""
    out: list[str] = []
    for token in sqref.split():
        a, _, b = token.partition(":")
        b = b or a
        ca, ra = split_cell(a)
        cb, rb = split_cell(b)
        for c in range(col_to_num(ca), col_to_num(cb) + 1):
            for r in range(ra, rb + 1):
                out.append(f"{num_to_col(c)}{r}")
                if len(out) > 100_000:
                    raise WorkbookError("ARCHIVE_LIMIT", "Validation range too large")
    return out


class Workbook:
    """Read-only view of an xlsx package held in memory."""

    def __init__(self, data: bytes):
        self.data = data
        try:
            self.zip = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile as exc:
            raise WorkbookError("UNSUPPORTED_WORKBOOK", "Not an xlsx (zip) package") from exc
        total = 0
        for info in self.zip.infolist():
            if info.file_size > MAX_PART_BYTES:
                raise WorkbookError("ARCHIVE_LIMIT", f"Part too large: {info.filename}")
            total += info.file_size
        if total > MAX_TOTAL_BYTES:
            raise WorkbookError("ARCHIVE_LIMIT", "Package too large when decompressed")
        self.part_names = [i.filename for i in self.zip.infolist()]
        self._strings: list[str] | None = None
        self._sheets: dict[str, str] | None = None
        if "xl/workbook.xml" in self.part_names:
            missing = [p for p in self.sheets.values() if p not in self.part_names]
            if missing:
                raise WorkbookError("PACKAGE_INCOMPLETE", f"Sheet part(s) listed but missing: {missing}")

    def read(self, part: str) -> bytes:
        return self.zip.read(part)

    @property
    def sheets(self) -> dict[str, str]:
        """Ordered {sheet name: part path}."""
        if self._sheets is None:
            wb = ET.fromstring(self.read("xl/workbook.xml"))
            rels = ET.fromstring(self.read("xl/_rels/workbook.xml.rels"))
            targets = {r.get("Id"): r.get("Target") for r in rels.findall("pr:Relationship", NS)}
            out: dict[str, str] = {}
            for s in wb.find("m:sheets", NS).findall("m:sheet", NS):
                target = targets[s.get(f"{{{NS['r']}}}id")].lstrip("/")
                out[s.get("name")] = target if target.startswith("xl/") else "xl/" + target
            self._sheets = out
        return self._sheets

    @property
    def shared_strings(self) -> list[str]:
        if self._strings is None:
            if "xl/sharedStrings.xml" not in self.part_names:
                self._strings = []
            else:
                root = ET.fromstring(self.read("xl/sharedStrings.xml"))
                self._strings = ["".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")) for si in root.findall("m:si", NS)]
        return self._strings

    def cells(self, sheet: str) -> dict[str, Cell]:
        """All non-blank cells (plus styled blanks are skipped) of a sheet."""
        root = ET.fromstring(self.read(self.sheets[sheet]))
        out: dict[str, Cell] = {}
        for c in root.iter(f"{{{NS['m']}}}c"):
            ref = c.get("r")
            style = c.get("s")
            style_id = int(style) if style is not None else None
            t = c.get("t", "n")
            f = c.find("m:f", NS)
            v = c.find("m:v", NS)
            if f is not None:
                out[ref] = Cell("formula", v.text if v is not None else None, f.text or "", style_id)
            elif t == "inlineStr":
                text = "".join(x.text or "" for x in c.iter(f"{{{NS['m']}}}t"))
                out[ref] = Cell("text", text, None, style_id)
            elif v is None:
                continue
            elif t == "s":
                out[ref] = Cell("text", self.shared_strings[int(v.text)], None, style_id)
            elif t == "str":
                out[ref] = Cell("text", v.text or "", None, style_id)
            elif t == "b":
                out[ref] = Cell("boolean", v.text == "1", None, style_id)
            elif t == "e":
                out[ref] = Cell("error", v.text, None, style_id)
            else:
                out[ref] = Cell("number", v.text, None, style_id)
        return out

    def style_ids(self, sheet: str) -> dict[str, int | None]:
        root = ET.fromstring(self.read(self.sheets[sheet]))
        return {c.get("r"): (int(c.get("s")) if c.get("s") is not None else None) for c in root.iter(f"{{{NS['m']}}}c")}

    def list_validation_cells(self, sheet: str) -> set[str]:
        """Cells covered by list data validations (classic or x14 extension)."""
        raw = self.read(self.sheets[sheet]).decode("utf-8")
        cells: set[str] = set()
        for m in re.finditer(r"<x14:dataValidation\b[^>]*type=\"list\".*?<xm:sqref>(.*?)</xm:sqref>", raw, re.S):
            cells.update(expand_sqref(m.group(1)))
        for m in re.finditer(r"<dataValidation\b[^>]*type=\"list\"[^>]*sqref=\"([^\"]+)\"", raw):
            cells.update(expand_sqref(m.group(1)))
        return cells

    def validation_sqrefs(self) -> list[str]:
        """All data-validation sqref tokens across sheets, for preservation checks."""
        out: list[str] = []
        for part in self.sheets.values():
            raw = self.read(part).decode("utf-8")
            out += [t for m in re.finditer(r"<xm:sqref>(.*?)</xm:sqref>", raw) for t in m.group(1).split()]
            out += [t for m in re.finditer(r"<dataValidation\b[^>]*sqref=\"([^\"]+)\"", raw) for t in m.group(1).split()]
        return sorted(out)

    def merged_ranges(self, sheet: str) -> list[str]:
        root = ET.fromstring(self.read(self.sheets[sheet]))
        mc = root.find("m:mergeCells", NS)
        return [] if mc is None else [m.get("ref") for m in mc.findall("m:mergeCell", NS)]
