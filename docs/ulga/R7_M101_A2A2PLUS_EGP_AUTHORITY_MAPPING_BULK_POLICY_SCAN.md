# R7-M101 A2/A2_PLUS Bulk Policy Scan

A1/A1_PLUS is closed for the current pass.

Next level-band:

```text
level_band = A2 + A2_PLUS
mode = bulk EGP authority mapping
source_nodes = ulga/grammar/grammar_nodes.json
source_index = ulga/reports/egp_row_index_compact.json
canonical_write = false
```

Required next artifacts:

```text
A2/A2_PLUS bulk inventory
refined search queue
candidate resolver
selection plan
```

Status:

```text
R7_M101_STATUS = PASS
NEXT_SHORT_STEP = R7-M102_A2A2PLUSBulkInventoryBuilder
STOP_REASON = NONE
```
