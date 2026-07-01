# ULGA-AUX-S0B Large Artifact Inventory and Git Policy QA

## 1. Preflight

Executed:

```powershell
git status -sb
git diff --cached --name-only
```

Confirmed unrelated pre-existing changes remain untouched:

```text
ulga/graph/static_candidate_ranking*.json
ulga/graph/corpus_source_inventory.json
ulga/reports/corpus_source_inventory_summary.json
ulga/reports/raz_downstream_discovery_drift_validation.json
docs/drive_manifest_guide.md
reports/raz/drive_manifest_hydration_plan.status.json
tests/test_drive_manifest_manager.py
tools/drive_manifest_manager.py
```

No staged files were present during S0B execution.

## 2. Files Inspected

```text
docs/ulga/ULGA_AUX_S0B_LARGE_ARTIFACT_INVENTORY_AND_GIT_POLICY_QA_PROMPT.md
.gitignore
git status -sb
git ls-files
git ls-files --others --exclude-standard
git ls-files --others --ignored --exclude-standard
```

## 3. Commands Executed

```powershell
git status -sb
Get-Content -Raw .gitignore
git ls-files | ForEach-Object { ... } | Where-Object { $_.MB -ge 25 } | Sort-Object MB -Descending
git ls-files --others --exclude-standard | ForEach-Object { ... } | Where-Object { $_.MB -ge 25 } | Sort-Object MB -Descending
git ls-files --others --ignored --exclude-standard | ForEach-Object { ... } | Where-Object { $_.MB -ge 25 } | Sort-Object MB -Descending
git diff --cached --name-only
Select-String -Path .gitignore -Pattern 'ulga/graph/raz_reading_authority_intake_candidates.json'
```

All scans used file metadata only. No large artifact content was read or rewritten.

## 4. Tracked Large-file Inventory

Tracked files >=25 MB:

```text
40.07 MB  ulga/graph/vocabulary_theme_edges.refined.json
37.77 MB  ulga/reports/vocabulary_theme_refinement_removed_edges.json
29.36 MB  ulga/graph/ulga_graph.vocabulary_morphology_layer.json
```

Assessment:

```text
tracked_count = 3
tracked_over_100mb_count = 0
```

## 5. Untracked Non-ignored Large-file Inventory

Untracked non-ignored files >=25 MB:

```text
none
```

Assessment:

```text
untracked_not_ignored_count = 0
untracked_not_ignored_over_25mb_count = 0
must_fix_count = 0
```

## 6. Ignored Large-file Inventory

Ignored files >=25 MB:

```text
619.32 MB  ulga/graph/raz_reading_authority_intake_candidates.json
163.00 MB  ulga/graph/ulga_graph.vocabulary_theme_layer.json
137.10 MB  ulga/graph/vocabulary_theme_edges.json
126.63 MB  raz_output_jsons/linkage/Level_W/raz_W_authority_linkage_view.json
121.56 MB  raz_output_jsons/linkage/Level_V/raz_V_authority_linkage_view.json
101.38 MB  raz_output_jsons/linkage/Level_S/raz_S_authority_linkage_view.json
96.57 MB   raz_output_jsons/linkage/Level_U/raz_U_authority_linkage_view.json
95.27 MB   raz_output_jsons/linkage/Level_T/raz_T_authority_linkage_view.json
76.82 MB   raz_output_jsons/linkage/Level_R/raz_R_authority_linkage_view.json
61.49 MB   raz_output_jsons/linkage/Level_Q/raz_Q_authority_linkage_view.json
60.53 MB   ulga/graph/ulga_graph.vocabulary_theme_layer.refined.json
59.23 MB   raz_output_jsons/linkage/Level_P/raz_P_authority_linkage_view.json
58.56 MB   raz_output_jsons/linkage/Level_O/raz_O_authority_linkage_view.json
45.44 MB   raz_output_jsons/linkage/Level_N/raz_N_authority_linkage_view.json
45.12 MB   raz_output_jsons/linkage/Level_M/raz_M_authority_linkage_view.json
37.19 MB   raz_output_jsons/linkage/Level_K/raz_K_authority_linkage_view.json
34.52 MB   raz_output_jsons/linkage/Level_L/raz_L_authority_linkage_view.json
31.90 MB   raz_output_jsons/linkage/Level_J/raz_J_authority_linkage_view.json
```

Assessment:

```text
ignored_count = 18
ignored_large_artifacts_confirmed = true
```

## 7. Artifact Size Policy

Implemented repository-wide thresholds:

```text
<25 MB      keep_git
25-50 MB    watch_size
50-100 MB   externalize_with_manifest preferred for generated graph/linkage/index artifacts
>=100 MB    do_not_commit_full_artifact
>=500 MB    local_only_or_external_storage_required
```

Additional policy:

```text
generated report >=25 MB => summary_only preferred
untracked_not_ignored >=25 MB => must_fix_gitignore_or_policy
large source artifacts => externalize_with_manifest plus hash/path recording
```

## 8. Artifact Classification Summary

Summary by recommended policy:

```text
watch_size = 7
summary_only = 1
externalize_with_manifest = 12
local_only = 1
manual_review = 0
```

Key classifications:

```text
ulga/graph/raz_reading_authority_intake_candidates.json => query_index, local_only
ulga/graph/ulga_graph.vocabulary_theme_layer.json => generated_graph, externalize_with_manifest
ulga/graph/vocabulary_theme_edges.json => generated_graph, externalize_with_manifest
raz_output_jsons/linkage/Level_{J-W}/*authority_linkage_view.json => linkage_view, watch_size or externalize_with_manifest by size band
ulga/reports/vocabulary_theme_refinement_removed_edges.json => generated_report, summary_only
```

## 9. Git Policy Validation

Validation result:

```text
status = PASS
blocking_error_count = 0
tracked_over_100mb_count = 0
untracked_not_ignored_over_25mb_count = 0
known_619mb_artifact_policy_status = PASS
```

No blocking conditions were found:

```text
no tracked file >=100 MB
no untracked non-ignored file >=25 MB
known 619 MB candidate artifact remains ignored and protected
no attempt to stage ignored/local-only large artifacts
```

## 10. .gitignore Coverage

Confirmed `.gitignore` includes:

```text
ulga/graph/raz_reading_authority_intake_candidates.json
```

The file also appeared in the authoritative ignored >=25 MB scan, so policy coverage is active rather than merely documented.

## 11. Risks and Deferred Work

Residual risks:

```text
tracked 25-50 MB graph/report artifacts may continue to grow past the watch band
ignored large linkage views and graph payloads currently rely on path-based ignore policy without manifest-level inventory
future shard/index work should avoid creating new tracked >50 MB generated artifacts without an explicit manifest strategy
```

Deferred work:

```text
manifest-driven governance for non-RAZ large local-only graph artifacts
future compact indexes for linkage_view and graph artifacts
S11 RAZ query-index shard build under this repository-wide policy
```

## 12. Git Scope Confirmation

Created only:

```text
ulga/reports/large_artifact_inventory.json
ulga/reports/artifact_size_policy.json
ulga/reports/large_artifact_git_policy_validation.json
docs/ulga/ULGA_AUX_S0B_LARGE_ARTIFACT_INVENTORY_AND_GIT_POLICY_QA.md
```

No large artifact was deleted, moved, rewritten, or staged.

## 13. Final Verdict

```text
ULGA-AUX-S0B_LargeArtifactInventoryAndGitPolicyQA = PASS
```

## 14. Recommended Next Task

```text
RAZ-AW-S11_ReadingAuthorityIntake_QueryIndexBuilderImplementation
```

Reason:

```text
S11 can build RAZ query-index shards under a repository-wide large-artifact policy instead of treating the 619 MB intake candidate file as a one-off exception.
```
