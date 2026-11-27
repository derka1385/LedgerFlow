"""LedgerFlow deterministic accounting rules (frontend/product owner's package).

Modules: ooxml (read-only xlsx), tacc (T-account engine), admit (TransactionV1 ->
EntryV1), checks (entry semantics), verify (reference independent verifier),
reference_writer (test/mock writer only). Standard library only.
"""
from .admit import DEFAULT_POLICY, REVIEW_CODES, admit, admit_settlement
from .checks import check as check_entry
from .ooxml import Workbook, WorkbookError
from .tacc import allocate, baseline, detect_mapping, minor_to_excel, parse_lines, to_minor, trial_balance
from .verify import verify

__all__ = ["DEFAULT_POLICY", "REVIEW_CODES", "admit", "admit_settlement", "check_entry", "Workbook", "WorkbookError",
           "allocate", "baseline", "detect_mapping", "minor_to_excel", "parse_lines", "to_minor", "trial_balance", "verify"]
