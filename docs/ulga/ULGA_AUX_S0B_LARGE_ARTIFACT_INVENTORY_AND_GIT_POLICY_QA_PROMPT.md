# ULGA-AUX-S0B Large Artifact Inventory and Git Policy QA Prompt

Use this prompt in Codex/local repo execution.

## 1. Task

`ULGA-AUX-S0B_LargeArtifactInventoryAndGitPolicyQA`

## 2. Objective

Establish a repository-wide large artifact inventory and Git policy layer for English_Learning_DB.

This task must verify which large artifacts are:

```text
tracked by Git
untracked but not ignored
ignored / local-only
```

and classify each large file by artifact role, Git policy, externalization need, and sharding/index need.

This is a governance / QA task. It must not rewrite existing builders, mutate generated artifacts, build new full indexes, or delete local artifacts.

## 3. Background Evidence

Recent local scans showed:

Tracked files >=25 MB:

```text
40.07 MB  ulga/graph/vocabulary_theme_edges.refined.json
37.77 MB  ulga/reports/vocabulary_theme_refinement_removed_edges.json
29.36 MB  ulga/graph/ulga_graph.vocabulary_morphology_layer.json
```

Ignored/local-only large files >=25 MB include:

```text
619.32 MB  ulga/graph/raz_reading_authority_intake_candidates.json
163 MB     ulga/graph/ulga_graph.vocabulary_theme_layer.json
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

S9/S10/S10A already established a local-only policy for:

```text
ulga/graph/raz_reading_authority_intake_candidates.json
```

S0B should generalize this into a reusable policy for all large artifacts.

## 4. Strict Scope

Allowed:

```text
repo-local large-file scanning
tracked / untracked / ignored file inventory
artifact-size policy report
Git policy validation report
.gitignore coverage analysis
large artifact classification
recommendations for future sharding / externalization
small helper script if useful
small tests if useful
S0B documentation
```

Forbidden:

```text
deleting large files
moving large files
rewriting large artifacts
building full query indexes
building RAZ S11 shards
changing RAZ intake candidates
changing vocabulary-theme graph artifacts
changing linkage view artifacts
Reading Authority promotion
query-layer approved-level expansion
runtime changes
learner state changes
planner changes
API/dashboard/scheduler changes
committing ignored/local-only large artifacts
```

## 5. Required Preflight

Run:

```powershell
git status -sb
```

Confirm unrelated pre-existing changes, if still present, are not touched:

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

Confirm `.gitignore` covers at minimum:

```text
ulga/graph/raz_reading_authority_intake_candidates.json
```

Do not modify `.gitignore` unless the task clearly documents the exact missing rule and adds only the required exclusion.

## 6. Required Scans

### 6.1 Tracked large files

Run:

```powershell
git ls-files | ForEach-Object {
  $f = Get-Item $_ -ErrorAction SilentlyContinue
  if ($f) {
    [PSCustomObject]@{
      MB = [math]::Round($f.Length / 1MB, 2)
      Bytes = $f.Length
      Path = $_
      GitState = "tracked"
    }
  }
} | Where-Object { $_.MB -ge 25 } |
  Sort-Object MB -Descending |
  Format-Table -AutoSize
```

### 6.2 Untracked non-ignored large files

Run:

```powershell
git ls-files --others --exclude-standard | ForEach-Object {
  $f = Get-Item $_ -ErrorAction SilentlyContinue
  if ($f) {
    [PSCustomObject]@{
      MB = [math]::Round($f.Length / 1MB, 2)
      Bytes = $f.Length
      Path = $_
      GitState = "untracked_not_ignored"
    }
  }
} | Where-Object { $_.MB -ge 25 } |
  Sort-Object MB -Descending |
  Format-Table -AutoSize
```

### 6.3 Ignored large files

Run:

```powershell
git ls-files --others --ignored --exclude-standard | ForEach-Object {
  $f = Get-Item $_ -ErrorAction SilentlyContinue
  if ($f) {
    [PSCustomObject]@{
      MB = [math]::Round($f.Length / 1MB, 2)
      Bytes = $f.Length
      Path = $_
      GitState = "ignored"
    }
  }
} | Where-Object { $_.MB -ge 25 } |
  Sort-Object MB -Descending |
  Format-Table -AutoSize
```

### 6.4 Optional full filesystem large-file scan

Run only if needed:

```powershell
Get-ChildItem -Recurse -File |
  Where-Object { $_.FullName -notmatch "\\.git\\" } |
  Sort-Object Length -Descending |
  Select-Object -First 80 `
    @{Name="MB";Expression={[math]::Round($_.Length / 1MB, 2)}},
    @{Name="Bytes";Expression={$_.Length}},
    FullName
```

Do not use this optional scan as the only source of truth for Git policy. The tracked/untracked/ignored scans are authoritative for Git state.

## 7. Artifact Size Policy

Create a project policy using these thresholds unless local evidence justifies stricter values:

```text
< 25 MB      normal_git_candidate
25-50 MB     watch_size
50-100 MB    externalize_or_shard_recommended
>=100 MB     do_not_commit_full_artifact
>=500 MB     local_only_or_external_storage_required
```

For generated artifacts:

```text
>=25 MB generated report/detail = prefer summary + external full detail
>=50 MB generated graph/output = prefer manifest + compact index / shard
>=100 MB generated artifact = do not commit full file
```

For source artifacts:

```text
large source PDFs / Excel / zip / audio / image bundles = source manifest + hash + external/local path
```

## 8. Artifact Role Classification

Classify every >=25 MB artifact into one of:

```text
source
raw_extracted_output
derived_artifact
generated_graph
generated_report
linkage_view
query_index
cache
unknown
```

Suggested path-based heuristics:

```text
raz_output_jsons/linkage/** = linkage_view
raz_output_jsons/derived/** = derived_artifact
ulga/graph/** = generated_graph or query_index
ulga/reports/** = generated_report
vocabulary/json/** = source_or_canonical_json
*.xlsx / *.pdf / *.zip / *.7z / *.mp3 / *.wav / *.png / *.jpg = source
```

If a file cannot be confidently classified, set:

```text
artifact_role = unknown
classification_confidence = low
recommended_action = manual_review
```

## 9. Git Policy Classification

Assign one policy to each artifact:

```text
keep_git
watch_size
externalize
externalize_with_manifest
shard_or_index
summary_only
local_only
manual_review
```

Recommended decisions:

```text
tracked 25-50 MB generated graph = watch_size
tracked 25-50 MB generated report detail = summary_only recommended
tracked >=50 MB generated artifact = externalize or shard recommended
untracked_not_ignored >=25 MB = must_fix_gitignore_or_policy
ignored >=100 MB = confirm local_only/externalized policy
ignored RAZ linkage views = keep ignored + manifest recommended
ignored RAZ intake candidates = local_only + query_index_builder path
```

## 10. Required Outputs

Create:

```text
ulga/reports/large_artifact_inventory.json
ulga/reports/artifact_size_policy.json
ulga/reports/large_artifact_git_policy_validation.json
docs/ulga/ULGA_AUX_S0B_LARGE_ARTIFACT_INVENTORY_AND_GIT_POLICY_QA.md
```

Optional if useful:

```text
ulga/tools/build_large_artifact_inventory.py
ulga/validators/validate_large_artifact_inventory.py
tests/ulga/test_large_artifact_inventory.py
```

Do not create or modify large generated artifacts.

## 11. Inventory Contract

`ulga/reports/large_artifact_inventory.json` should include:

```json
{
  "task": "ULGA-AUX-S0B_LargeArtifactInventoryAndGitPolicyQA",
  "status": "PASS",
  "threshold_mb": 25,
  "generated_at": "<ISO8601 or null>",
  "scan_sources": ["tracked", "untracked_not_ignored", "ignored"],
  "summary": {
    "tracked_count": 0,
    "untracked_not_ignored_count": 0,
    "ignored_count": 0,
    "tracked_over_100mb_count": 0,
    "untracked_not_ignored_over_25mb_count": 0,
    "must_fix_count": 0,
    "watch_count": 0,
    "externalize_recommended_count": 0,
    "shard_or_index_recommended_count": 0
  },
  "artifacts": []
}
```

Each artifact should include:

```json
{
  "path": "ulga/graph/example.json",
  "size_bytes": 0,
  "size_mb": 0.0,
  "git_state": "tracked | untracked_not_ignored | ignored",
  "artifact_role": "generated_graph",
  "classification_confidence": "high | medium | low",
  "current_git_policy": "tracked | ignored | untracked_not_ignored",
  "recommended_policy": "watch_size",
  "recommended_action": "keep_tracked_but_watch_size",
  "shard_or_index_candidate": false,
  "externalization_candidate": false,
  "summary_only_candidate": false,
  "blocking": false,
  "notes": []
}
```

## 12. Size Policy Contract

`ulga/reports/artifact_size_policy.json` should include:

```json
{
  "task": "ULGA-AUX-S0B_LargeArtifactInventoryAndGitPolicyQA",
  "policy_version": "large_artifact_policy.v1",
  "thresholds_mb": {
    "normal_git_candidate_max": 25,
    "watch_size_min": 25,
    "externalize_or_shard_recommended_min": 50,
    "do_not_commit_full_artifact_min": 100,
    "local_only_or_external_storage_required_min": 500
  },
  "rules": [],
  "known_local_only_artifacts": [
    "ulga/graph/raz_reading_authority_intake_candidates.json"
  ]
}
```

## 13. Validation Contract

`ulga/reports/large_artifact_git_policy_validation.json` should include:

```json
{
  "task": "ULGA-AUX-S0B_LargeArtifactInventoryAndGitPolicyQA",
  "status": "PASS",
  "blocking_error_count": 0,
  "must_fix_count": 0,
  "tracked_over_100mb_count": 0,
  "untracked_not_ignored_over_25mb_count": 0,
  "ignored_large_artifacts_confirmed": true,
  "known_619mb_artifact_policy_status": "PASS",
  "notes": []
}
```

Blocking conditions:

```text
tracked file >=100 MB
untracked_not_ignored file >=25 MB
known 619 MB candidate artifact not ignored / not protected
.gitignore missing ulga/graph/raz_reading_authority_intake_candidates.json
attempt to stage ignored/local-only large artifacts
```

## 14. Documentation Structure

Create:

```text
docs/ulga/ULGA_AUX_S0B_LARGE_ARTIFACT_INVENTORY_AND_GIT_POLICY_QA.md
```

Include:

```text
1. Preflight
2. Files inspected
3. Commands executed
4. Tracked large-file inventory
5. Untracked non-ignored large-file inventory
6. Ignored large-file inventory
7. Artifact size policy
8. Artifact classification summary
9. Git policy validation
10. .gitignore coverage
11. Risks and deferred work
12. Git scope confirmation
13. Final verdict
14. Recommended next task
```

## 15. Expected Initial Classification Guidance

Based on current observed local evidence, expect something like:

```text
tracked >=25 MB:
- ulga/graph/vocabulary_theme_edges.refined.json => watch_size
- ulga/reports/vocabulary_theme_refinement_removed_edges.json => summary_only recommended
- ulga/graph/ulga_graph.vocabulary_morphology_layer.json => watch_size

ignored >=100 MB:
- ulga/graph/raz_reading_authority_intake_candidates.json => local_only, already governed by S9/S10/S10A, S11 query-index source
- ulga/graph/ulga_graph.vocabulary_theme_layer.json => externalize_with_manifest / future graph index candidate
- ulga/graph/vocabulary_theme_edges.json => externalize_with_manifest / future graph index candidate
- raz_output_jsons/linkage/Level_W/... => ignored linkage_view, future linkage index candidate
- raz_output_jsons/linkage/Level_V/... => ignored linkage_view, future linkage index candidate
- raz_output_jsons/linkage/Level_S/... => ignored linkage_view, future linkage index candidate
```

Do not hardcode these values without running the scans.

## 16. Required Commands to Run

Run at minimum:

```powershell
git status -sb
# tracked large files
# untracked non-ignored large files
# ignored large files
```

If helper scripts / validators are created, run:

```powershell
python ulga/validators/validate_large_artifact_inventory.py
python -m pytest tests/ulga/test_large_artifact_inventory.py -q
```

If no helper scripts are created, the task may still PASS using documented PowerShell scan results and JSON reports.

Do not report broad `tests/ulga` PASS unless it actually completed.

## 17. Acceptance Criteria

S0B is PASS only if:

```text
tracked >=25 MB files are inventoried
untracked_not_ignored >=25 MB files are inventoried and must_fix_count=0, or blockers are explicit
ignored >=25 MB files are inventoried
known 619 MB RAZ intake artifact remains protected
no tracked file >=100 MB exists, or blockers are explicit
artifact_size_policy.json exists
large_artifact_inventory.json exists
large_artifact_git_policy_validation.json exists
S0B documentation exists
no large artifact is moved, deleted, rewritten, or staged
no unrelated existing changes are touched
```

## 18. Final Verdict Format

Use:

```text
ULGA-AUX-S0B_LargeArtifactInventoryAndGitPolicyQA = PASS
```

or:

```text
ULGA-AUX-S0B_LargeArtifactInventoryAndGitPolicyQA = BLOCKED_<REASON>
```

## 19. Recommended Next Task

If S0B passes, recommend returning to:

```text
RAZ-AW-S11_ReadingAuthorityIntake_QueryIndexBuilderImplementation
```

Reason:

```text
S11 can then build the RAZ query index shards under a repository-wide artifact policy instead of a one-off 619 MB exception.
```
