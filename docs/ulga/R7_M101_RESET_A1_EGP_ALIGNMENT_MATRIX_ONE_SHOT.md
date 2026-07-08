# R7-M101 RESET A1 EGP Alignment Matrix One-Shot

## Why this record exists

A1/A1_PLUS node evidence mapping was incorrectly treated as level-band completion before source-centric EGP A1 rule coverage was audited.

## Current authoritative state

```text
A1/A1_PLUS node evidence mapping = PARTIAL_PASS_WITH_DEFERRED
EGP A1 rows = 109
covered EGP A1 rows = 17
missing EGP A1 rows = 92
coverage = 0.155963
prior closeout = PREMATURE_CLOSEOUT_INVALIDATED
final closeout allowed = false
A2/A2_PLUS progression allowed = false
```

## Required next task

```text
R7-M101_RESET_A1_EGPAlignmentMatrixOneShot
```

Required outputs:

```text
EGP A1 rule clusters
cluster to existing node mapping
missing node candidates
wrong-level or bridge refs
PATCH / DEFER / CREATE_NODE / OUT_OF_SCOPE decisions
```

## Validation mode

```text
local_validation_required = true
ci_gate_required = false
```

The machine-readable source of truth is:

```text
ulga/reports/a1_a1plus_alignment_reset_status.json
```
