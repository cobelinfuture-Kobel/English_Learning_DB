# RAZ-AW-S2D Drive Manifest Hydration Sample QA

## 1. Preflight

Task:

```text
RAZ-AW-S2D_DriveManifestHydrationSampleQA
```

Scope:

```text
CLOUD HYDRATION SAMPLE READBACK QA
SANITIZED REPORT READBACK ONLY
NO RAW RAZ JSON MUTATION
NO RAW RAZ JSON COMMIT
NO FULL RAW TEXT IN REPORTS
NO AUTHORITY PROMOTION
NO TAG REGISTRY PROMOTION
NO NORMALIZER IMPLEMENTATION
NO GENERATED READING / DIALOGUE / EXERCISE CONTENT
NO RUNTIME / API / SCHEDULER / DASHBOARD CHANGE
```

Repository:

```text
cobelinfuture-Kobel/English_Learning_DB
branch: main
```

Upstream dependency:

```text
RAZ-AW-S2C_DriveManifestHydrationTooling
```

Required cloud input:

```text
Google Apps Script output from hydrateRazAwManifestSample()
```

Expected Drive output filename pattern:

```text
drive_manifest_hydration_sample_<timestamp>.json
```

Files created by this task:

```text
docs/raz/RAZ_AW_S2D_DRIVE_MANIFEST_HYDRATION_SAMPLE_QA.md
reports/raz/drive_manifest_hydration_sample_qa.status.json
```

Risk level:

```text
Low
```

---

## 2. S2D Result

Current status:

```text
BLOCKED_WAITING_FOR_CLOUD_SAMPLE_OUTPUT
```

Reason:

```text
No Drive sample hydration output URL was provided, and the connector search did not find a discoverable drive_manifest_hydration_sample_*.json file.
```

This does not invalidate S2C. It only means S2D cannot perform readback QA until the cloud sample output exists.

---

## 3. Required Operator Action

Open Google Apps Script containing:

```text
tools/raz_aw_drive_manifest_hydration_apps_script.gs
```

Run:

```javascript
hydrateRazAwManifestSample()
```

Expected output in Drive:

```text
drive_manifest_hydration_sample_<timestamp>.json
```

Then provide the generated Drive file URL.

---

## 4. What S2D Will Check After Output Exists

S2D will verify:

```text
status is PASS or PASS_WITH_WARNINGS
sanitized = true
contains_raw_text = false
raw_mutation = false
raw_commit_allowed = false
selected_record_count > 0
fetch_success_count == selected_record_count
json_parse_status_counts are present
records include A-W sample coverage
no raw sentence/page/audio text appears in report
```

Expected sample scope:

```text
first / middle / last raw JSON per A-W level
```

Expected sample count:

```text
up to 69 records
```

Reason:

```text
23 RAZ levels × 3 sample files per level = 69 sample fetches.
```

---

## 5. Current Verdict

```text
RAZ-AW-S2D verdict: BLOCKED_WAITING_FOR_CLOUD_SAMPLE_OUTPUT
```

Next step:

```text
Run hydrateRazAwManifestSample() and provide the generated Drive output URL.
```
