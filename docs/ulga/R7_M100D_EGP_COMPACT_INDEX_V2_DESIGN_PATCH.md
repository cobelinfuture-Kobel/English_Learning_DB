# R7-M100D EGP Compact Index V2 Design Patch

## Problem

The current compact EGP row index is usable for row-level reference checks, but it is too thin for semantic coverage audit.

Current retained fields:

```text
row_number
source_ref
row_id
level
super_category
sub_category
guideword
```

Missing fields required for semantic audit:

```text
lexical_range
can_do
example
```

## Required v2 artifact

```text
ulga/reports/egp_row_index_compact_v2.json
ulga/reports/egp_row_index_compact_v2_summary.json
```

## Rule

Level-band final closeout must not rely only on guideword matching. Coverage audit may start with v1 row coverage, but semantic confirmation requires v2 rows.

## Status

```text
R7_M100D_STATUS = DESIGN_PATCH_RECORDED
NEXT_SHORT_STEP = R7-M100E_TaskSpecificCIManifestGate
STOP_REASON = NONE
```
