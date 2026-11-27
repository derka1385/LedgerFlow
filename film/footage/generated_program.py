import hashlib
import json
import sys
from ledgerflow_workbook import Workbook, patch_cells


def main():
    # Read inputs
    with open("/input/source.xlsx", "rb") as f:
        source_bytes = f.read()

    with open("/input/plan.json", "r") as f:
        plan = json.load(f)

    # Step 1: Verify SHA256
    sha = hashlib.sha256(source_bytes).hexdigest()
    if sha != plan["base_sha256"]:
        print(
            f"SHA256 mismatch: expected {plan['base_sha256']}, got {sha}",
            file=sys.stderr,
        )
        sys.exit(2)

    # Group operations by sheet
    sheets = {}
    for op in plan["operations"]:
        sheet = op["sheet"]
        cell = op["cell"]
        if sheet not in sheets:
            sheets[sheet] = {}
        sheets[sheet][cell] = op

    # Step 2: Check every target cell is blank in the source
    wb_src = Workbook(source_bytes)
    for sheet, cells in sheets.items():
        source_cells = wb_src.cells(sheet)
        for cell in cells:
            if cell in source_cells:
                print(
                    f"Cell {sheet}!{cell} is not blank in source",
                    file=sys.stderr,
                )
                sys.exit(2)

    # Step 3: Call patch_cells (once per sheet; all cells of one sheet in one call)
    result_bytes = source_bytes
    for sheet, cells in sheets.items():
        writes = {}
        for cell, op in cells.items():
            writes[cell] = {
                "type": op["after"]["type"],
                "value": op["after"]["value"],
            }
        result_bytes = patch_cells(result_bytes, sheet, writes)

    # Step 4: Re-open the output and confirm every written cell holds the planned value
    wb_out = Workbook(result_bytes)
    for sheet, cells in sheets.items():
        out_cells = wb_out.cells(sheet)
        for cell, op in cells.items():
            if cell not in out_cells:
                print(
                    f"Verification failed: {sheet}!{cell} is blank after patch",
                    file=sys.stderr,
                )
                sys.exit(2)
            snapshot = out_cells[cell]
            expected_type = op["after"]["type"]
            expected_value = op["after"]["value"]
            if snapshot.type != expected_type:
                print(
                    f"Verification failed: {sheet}!{cell} type is {snapshot.type}, "
                    f"expected {expected_type}",
                    file=sys.stderr,
                )
                sys.exit(2)
            if expected_type == "number":
                if float(snapshot.value) != float(expected_value):
                    print(
                        f"Verification failed: {sheet}!{cell} value is "
                        f"{snapshot.value}, expected {expected_value}",
                        file=sys.stderr,
                    )
                    sys.exit(2)
            else:
                if snapshot.value != expected_value:
                    print(
                        f"Verification failed: {sheet}!{cell} value is "
                        f"{snapshot.value}, expected {expected_value}",
                        file=sys.stderr,
                    )
                    sys.exit(2)

    # Step 5: Print one line per written cell
    for op in plan["operations"]:
        print(
            f"{op['sheet']}!{op['cell']} = {op['after']['value']} "
            f"({op['after']['type']})"
        )

    # Step 6: Write /work/candidate.xlsx
    with open("/work/candidate.xlsx", "wb") as f:
        f.write(result_bytes)


if __name__ == "__main__":
    main()
