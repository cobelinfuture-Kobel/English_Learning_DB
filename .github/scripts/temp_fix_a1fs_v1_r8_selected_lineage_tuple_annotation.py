from pathlib import Path

path = Path("ulga/builders/run_a1fs_v1_r8_legacy_real_evidence_reconciliation_local.py")
text = path.read_text(encoding="utf-8")
old = "    merged: dict[tuple[str, str], dict[str, Any]] = {}\n"
new = "    merged: dict[tuple[str, str, str], dict[str, Any]] = {}\n"
if text.count(old) != 1:
    raise SystemExit(f"expected one stale tuple annotation, found {text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
