# RAZ-AW-V1 Status Snapshot HTML Export

## 1. Preflight

`RAZ-AW-V1_StatusSnapshotHTMLExport` is a status/export task only.

It exists to make Reading System V1 progress visible, traceable, and reviewable as a static artifact. It does not implement Reading generation, assessment expansion, learner error diagnosis, adaptive sequencing, listening, speaking, writing, or a student-facing app.

## 2. Scope

### In scope

- Build a static HTML status snapshot for `RAZ-AW-V1`.
- Build a machine-readable manifest beside the HTML.
- Record source trace / evidence trace for known repository status and authority files.
- Preserve V1 as the only active target.
- Mark V2-V5 as deferred / not active.
- Emit Gate Metrics and Distance Vector fields.
- Use `UNKNOWN` or `MISSING_SOURCE` when repository evidence is absent.

### Out of scope

- Reading question generation.
- Candidate quiz package generation.
- Cambridge assessment pattern expansion.
- Learner error tagging or weak-point diagnosis.
- Adaptive sequencing or learning path integration.
- Reading-to-writing/listening/speaking bridges.
- Student-facing app or UI framework implementation.

## 3. Files added

- `tools/export_raz_aw_v1_status_snapshot_html.py`
- `docs/status/raz_aw_v1_status_snapshot.html`
- `docs/status/raz_aw_v1_status_snapshot_manifest.json`
- `tests/test_export_raz_aw_v1_status_snapshot_html.py`
- `docs/raz_aw/RAZ_AW_V1_STATUS_SNAPSHOT_HTML_EXPORT.md`

## 4. Output contract

The HTML snapshot must include:

1. Header / project metadata.
2. V1 boundary.
3. V2-V5 deferred boundary.
4. Progress Snapshot.
5. Milestone Status.
6. Source Trace / Evidence Trace.
7. Gate Metrics.
8. Distance Vector.
9. Warnings.

The manifest must include:

```json
{
  "project_id": "English_Learning_DB",
  "epic_id": "RAZ-AW-V1_ReadingSystemV1ProgressAndStatusReporting",
  "subtask_id": "RAZ-AW-V1_StatusSnapshotHTMLExport",
  "active_target": "Reading System V1 = Source-grounded practice generation",
  "deferred_targets": [],
  "source_records": [],
  "progress_areas": [],
  "milestones": [],
  "gate_metrics": {},
  "distance_vector": {},
  "warnings": []
}
```

## 5. Status vocabulary

Progress and milestone status values are intentionally restricted to:

```text
NOT_STARTED
IN_PROGRESS
PARTIAL
COMPLETE
BLOCKED
UNKNOWN
```

If evidence is missing, the export must not infer `COMPLETE`. It must keep the status as `UNKNOWN`, `MISSING_SOURCE`, or another explicit warning field.

## 6. Gate Metrics

Required Gate Metrics:

- `source_files_discovered`
- `source_files_checked`
- `missing_source_count`
- `html_generated`
- `manifest_generated`
- `script_present`
- `test_present`
- `no_v2_v5_scope_creep`
- `reading_generation_changed`
- `adaptive_learning_changed`
- `learner_error_tagging_changed`

For this task, all feature-expansion flags must remain false except `no_v2_v5_scope_creep`, which must remain true.

## 7. Distance Vector

This task contributes to Reading System V1 by improving:

- progress visibility,
- source traceability,
- handoff quality,
- Gate reporting,
- operator review readiness.

It does not reduce the remaining distance by adding Reading content generation. It reduces operational uncertainty around what is complete, partial, blocked, or unknown.

## 8. How to run

```bash
python tools/export_raz_aw_v1_status_snapshot_html.py
```

Expected output:

```text
RAZ-AW V1 status snapshot export: PASS
HTML: docs/status/raz_aw_v1_status_snapshot.html
Manifest: docs/status/raz_aw_v1_status_snapshot_manifest.json
```

## 9. How to test

```bash
pytest tests/test_export_raz_aw_v1_status_snapshot_html.py
```

## 10. Anti-Scope-Creep confirmation

This task is complete when the export script, HTML, manifest, and tests exist and the export can be rebuilt.

The next shortest step is to run the export and use the resulting HTML as the Reading System V1 status readback artifact.
