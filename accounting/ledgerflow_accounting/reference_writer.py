"""Reference OOXML cell writer (tests, fixtures and the dev mock API only).

The production writer is Codex's `ledgerflow_workbook` helper in the execution
image (docs/REPOSITORY.md "Writer helper contract"). This one exists so the
verifier and UI can be exercised on real bytes tonight. Technique verified on
2026-11-26/27 (product/WORKBOOK_ANALYSIS.md §8): replace the target <c> element
in place, keep its style attribute, write text as inlineStr so sharedStrings.xml
stays byte-identical, copy every other zip entry unchanged. Excel opened the
result without a repair prompt.
"""
from __future__ import annotations

import io
import re
import zipfile
from xml.sax.saxutils import escape

from .ooxml import Workbook, WorkbookError, split_cell


def _cell_xml(ref: str, style: str, after: dict) -> str:
    if after["type"] == "text":
        return f'<c r="{ref}"{style} t="inlineStr"><is><t>{escape(after["value"])}</t></is></c>'
    if after["type"] == "number":
        if not re.fullmatch(r"-?\d+(\.\d{1,2})?", after["value"]):
            raise WorkbookError("INVALID_VALUE", f"Not an exact decimal: {after['value']!r}")
        return f'<c r="{ref}"{style}><v>{after["value"]}</v></c>'
    raise WorkbookError("INVALID_VALUE", f"Unsupported after type {after['type']}")


def patch_cells(data: bytes, sheet: str, writes: dict[str, dict]) -> bytes:
    """writes: {"K64": {"type": "text", "value": "[1940]"}, "L64": {"type": "number", "value": "1000"}}"""
    wb = Workbook(data)
    part = wb.sheets[sheet]
    xml = wb.read(part).decode("utf-8")
    for ref, after in writes.items():
        split_cell(ref)
        pat = re.compile(r'<c r="' + ref + r'"((?: s="\d+")?)(?:/>|(?: t="[a-zA-Z]+")?>(?:(?!</c>).)*</c>)', re.S)
        m = pat.search(xml)
        if not m:
            raise WorkbookError("CELL_NOT_PRESENT", f"{ref} has no existing <c> element; P0 writes only existing styled cells")
        if "<v>" in m.group(0) or "<is>" in m.group(0) or "<f>" in m.group(0):
            raise WorkbookError("NO_SAFE_SLOTS", f"{ref} is not blank")
        xml = xml[:m.start()] + _cell_xml(ref, m.group(1), after) + xml[m.end():]
    src = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as dst:
        for info in src.infolist():
            dst.writestr(info, xml.encode("utf-8") if info.filename == part else src.read(info.filename))
    return out.getvalue()
