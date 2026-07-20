from pathlib import Path

path = Path("tests/ulga/test_a1fs_v1_r8_legacy_real_evidence_reconciliation_local_runner.py")
text = path.read_text(encoding="utf-8")
broken = '+ "\n",\n'
fixed = '+ "\\n",\n'
count = text.count(broken)
if count != 3:
    raise SystemExit(f"expected 3 broken newline literals, found {count}")
path.write_text(text.replace(broken, fixed), encoding="utf-8")
