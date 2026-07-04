# ReadingV1 Local Runtime In-Memory Source Pipeline Design Scan

## 1. Current State

Task:
ReadingV1_LocalRuntimeInMemorySourcePipeline_DesignScan

Scope:
Define the local/private runtime source locator and in-memory source resolution contract for ReadingV1 private homework rendering.

Allowed files:
- docs/ulga/READING_V1_LOCAL_RUNTIME_IN_MEMORY_SOURCE_PIPELINE_DESIGN_SCAN.md

Forbidden files:
- runtime code
- builders
- validators
- tests
- generated JSON artifacts
- generated overlay artifacts
- learner-facing HTML
- public export artifacts
- RAZ raw text, full passage text, or full book text committed to GitHub
- source payload cache files
- promotion artifacts

Current-task blockers:
- Overlay items currently carry display_text_ref / source locator references but no contract for resolving them in local/private runtime.
- Future HTML export needs a display payload source, but source payload must not be copied to GitHub.
- The system needs a strict boundary between locator references, ephemeral in-memory source text, reviewed display snippets, and persisted artifacts.

Warning policy:
- Documentation-only warnings are acceptable if the local runtime contract is fully defined.
- Any implementation, source adapter, cache writer, renderer, or source import is classified as FUTURE_WORK.
- Any requirement to store source text in GitHub is a blocker and must remain forbidden.

Generated artifact policy:
- No generated source payload, cache, overlay, PracticeBank, or HTML artifact is allowed in this task.
- This task writes one design document only.

Runtime impact:
- None.

Promotion impact:
- None.
- Local resolver output is not authority promotion.
- Resolved source text is ephemeral and not a candidate artifact unless a later task explicitly defines reviewed snippet promotion.

Stop condition:
- Stop after defining source locator types, resolver lifecycle, in-memory display payload contract, blocked persistence policy, resolver gate, Gate PASS checklist, deferred issues, and next task.
- Do not implement resolver code.
- Do not generate HTML.
- Do not read or copy RAZ raw text into GitHub.
- Do not create source payload cache artifacts.

Deferred issues register:
- P1-M6 implementation is deferred unless separately approved.
- P1-M7 Private Homework Output Gate is deferred.
- P1-M8 HTML Practice Export is deferred.
- P1-M9 P1 Closeout QA is deferred.

---

## 2. Problem Definition

P1-M4 and P1-M5 established that ReadingV1 can carry:

```text
source_locator
source_unit_ref
source_sentence_ref
display_text_ref
answer_evidence_ref
```

But the future private homework renderer still needs a way to display reading text to the learner.

The risk is:

```text
PracticeBank / Overlay / HTML export accidentally becomes a source-text storage layer.
```

This task prevents that by defining a local runtime resolver that may read private source material only at runtime and only in memory.

---

## 3. Core Principle

```text
GitHub stores locator contracts.
Local runtime resolves display text in memory.
HTML export receives only policy-approved private display payload.
No raw source corpus is persisted to GitHub.
```

The resolver is allowed to produce transient display text for private/local homework rendering, but the resolved text must not be committed as a durable source cache, authority artifact, public preview, or commercial worksheet.

---

## 4. Source Locator Model

A ReadingV1 source locator must identify where private runtime can find the source without copying source text into repo.

### 4.1 Locator Object

```json
{
  "locator_id": "RV1_LOC_000001",
  "locator_type": "local_private_source_ref",
  "source_family": "reading_source",
  "source_system": "raz_or_reading_authority_query_index",
  "source_level": "RAZ-C",
  "source_book_ref": "book_ref_or_private_manifest_id",
  "source_unit_ref": "unit_ref_or_page_unit_id",
  "source_sentence_refs": ["sentence_ref_001"],
  "source_page_ref": "page_ref_or_private_page_locator",
  "source_path_hint": null,
  "source_uri_hint": null,
  "payload_policy": {
    "raw_source_text_persisted": false,
    "full_passage_text_persisted": false,
    "source_payload_copied_to_repo": false,
    "cache_allowed": false,
    "private_runtime_only": true
  }
}
```

### 4.2 Allowed Locator Types

```text
local_private_source_ref
private_manifest_ref
query_index_ref
reviewed_display_snippet_ref
synthetic_contract_fixture_ref
```

### 4.3 Blocked Locator Types

```text
public_url_to_copyrighted_payload
raw_text_blob
full_passage_blob
full_book_blob
github_source_payload_path
public_export_payload_ref
commercial_distribution_payload_ref
```

---

## 5. Resolver Lifecycle

The local runtime resolver follows this lifecycle:

```text
1. receive overlay item with display_text_ref / source_locator
2. resolve locator against private local source index or operator-provided private source folder
3. load only the required unit / sentence / display segment into memory
4. apply P1 display policy
5. return transient display payload to renderer
6. discard raw source payload after render session
```

Strict lifecycle constraints:

```text
no source payload is written to GitHub
no source payload is written to generated repo artifacts
no full passage cache is created
no raw page text is persisted
no book-level text is persisted
no public preview artifact is created
```

---

## 6. In-Memory Display Payload Contract

A resolver may return an in-memory display payload with this shape:

```json
{
  "display_payload_id": "RV1_DISPLAY_SESSION_000001",
  "source_locator_id": "RV1_LOC_000001",
  "source_item_id": "RV1_ITEM_000001",
  "display_text": "runtime-only text supplied by private resolver",
  "display_text_scope": "sentence_or_short_unit_only",
  "display_text_origin": "private_runtime_resolver",
  "persistable": false,
  "git_commit_allowed": false,
  "public_export_allowed": false,
  "commercial_distribution_allowed": false,
  "source_payload_stored": false,
  "raw_source_text_cache_created": false,
  "full_passage_cache_created": false,
  "expires_after_render_session": true
}
```

Important:

```text
display_text may exist only in memory during private runtime.
If written to disk for debugging, it becomes a policy violation unless explicitly approved as a later private local-only artifact outside GitHub.
```

---

## 7. Reviewed Display Snippet Exception

A later task may define reviewed display snippets, but this DesignScan does not implement them.

Allowed future exception shape:

```json
{
  "reviewed_display_snippet_id": "RV1_SNIP_000001",
  "source_locator_id": "RV1_LOC_000001",
  "snippet_text": "short reviewed sentence or micro-unit",
  "review_status": "operator_reviewed",
  "persistable": "policy_dependent",
  "public_export_allowed": false,
  "private_homework_only": true
}
```

This exception requires separate operator approval because it changes persistence behavior.

Current task decision:

```text
reviewed_display_snippet persistence = DEFERRED
```

---

## 8. Resolver Input Contract

The future resolver input should be an overlay item:

```json
{
  "overlay_item_id": "RV1_OVERLAY_ITEM_000001",
  "source_item_id": "RV1_ITEM_000001",
  "student_view": {
    "display_text_ref": "synthetic://reading_v1/RV1_ITEM_000001",
    "display_text_inline": null
  },
  "source_trace_view": {
    "source_locator": "synthetic://reading_v1/RV1_ITEM_000001",
    "source_unit_ref": "synthetic_unit_001",
    "source_payload_stored": false,
    "raw_source_text_visible": false,
    "full_passage_text_visible": false
  },
  "policy_flags": {
    "private_homework_only": true,
    "public_ready": false,
    "not_for_public_export": true,
    "not_for_commercial_distribution": true,
    "raw_raz_text_persisted": false,
    "full_passage_text_persisted": false,
    "source_payload_copied_to_repo": false
  }
}
```

Input preconditions:

```text
overlay validator status == PASS
overlay_ready == true
source_payload_stored == false
display_text_inline == null
private_homework_only == true
public_ready == false
```

---

## 9. Resolver Output Contract

The resolver output is not a repository artifact by default.

Allowed only in memory:

```json
{
  "resolver_status": "PASS",
  "overlay_item_id": "RV1_OVERLAY_ITEM_000001",
  "display_payload": {
    "display_text": "runtime-only private text",
    "persistable": false,
    "expires_after_render_session": true
  },
  "policy_result": {
    "private_runtime_only": true,
    "public_export_allowed": false,
    "git_commit_allowed": false,
    "source_payload_cache_created": false
  }
}
```

Blocked persisted outputs:

```text
resolved_source_payload.json
resolved_raz_text.json
resolved_full_passage.json
source_cache.json
public_preview_payload.json
commercial_worksheet_payload.json
```

---

## 10. Resolver Gate Requirements

Future resolver validator must check:

```text
overlay_item exists
overlay item validator status PASS
overlay_ready == true
source_locator or display_text_ref exists
display_text_inline == null before runtime
private_homework_only == true
public_ready == false
not_for_public_export == true
not_for_commercial_distribution == true
raw_raz_text_persisted == false
full_passage_text_persisted == false
source_payload_copied_to_repo == false
resolved payload persistable == false
resolved payload git_commit_allowed == false
resolved payload public_export_allowed == false
resolved payload expires_after_render_session == true
```

---

## 11. Blocking Error Codes for Future Resolver Validator

```text
RV1_SRC_ERR_OVERLAY_NOT_PASS
RV1_SRC_ERR_OVERLAY_READY_FALSE
RV1_SRC_ERR_SOURCE_LOCATOR_MISSING
RV1_SRC_ERR_DISPLAY_TEXT_INLINE_PREEXISTS
RV1_SRC_ERR_PRIVATE_HOMEWORK_FALSE
RV1_SRC_ERR_PUBLIC_READY_TRUE
RV1_SRC_ERR_PUBLIC_EXPORT_ALLOWED
RV1_SRC_ERR_COMMERCIAL_DISTRIBUTION_ALLOWED
RV1_SRC_ERR_RAW_SOURCE_TEXT_PERSISTED
RV1_SRC_ERR_FULL_PASSAGE_PERSISTED
RV1_SRC_ERR_SOURCE_PAYLOAD_COPIED_TO_REPO
RV1_SRC_ERR_RESOLVED_PAYLOAD_PERSISTABLE
RV1_SRC_ERR_RESOLVED_PAYLOAD_GIT_COMMIT_ALLOWED
RV1_SRC_ERR_RESOLVED_PAYLOAD_PUBLIC_EXPORT_ALLOWED
RV1_SRC_ERR_RESOLVED_PAYLOAD_CACHE_CREATED
RV1_SRC_ERR_REVIEWED_SNIPPET_PERSISTENCE_UNAPPROVED
```

Allowed warnings:

```text
RV1_SRC_WARN_PRIVATE_SOURCE_MISSING_AT_RUNTIME
RV1_SRC_WARN_DISPLAY_SEGMENT_TOO_LONG_FOR_SINGLE_SCREEN
RV1_SRC_WARN_SOURCE_UNIT_REQUIRES_OPERATOR_REVIEW
RV1_SRC_WARN_REVIEWED_SNIPPET_POLICY_DEFERRED
```

Warnings do not imply output gate readiness.

---

## 12. Relationship to P1-M7 Output Gate

P1-M6 does not decide whether homework can be exported.

It only defines how source text can be resolved safely.

P1-M7 must later decide:

```text
whether every overlay item has safe display payload
whether every payload is private-runtime-only
whether the package can enter HTML rendering
whether answer keys are hidden from student view
whether parent/teacher view remains local/private
whether public export remains blocked
```

P1-M7 should use P1-M6 resolver policy as one of its input gates.

---

## 13. Future File Layout Recommendation

This is not implemented in the current task.

```text
ulga/schemas/reading_v1_source_locator.schema.json
ulga/validators/validate_reading_v1_source_locator.py
ulga/runtime/resolve_reading_v1_private_source.py
ulga/reports/reading_v1_source_resolution_policy_report.json
```

Generated reports, if any, must not include resolved source text.

---

## 14. Reading System Progress Update

| Dimension | Before | After This DesignScan |
|---|---|---|
| Source Authority | PARTIAL | unchanged |
| Content Authority | PARTIAL | unchanged |
| Query Layer | PARTIAL | unchanged |
| Validation Layer | overlay validator scaffold implemented | source resolver contract defined |
| Reading Generation | synthetic scaffold only | unchanged |
| Reading Practice | private homework overlay schema + validator + builder implemented | source display resolution policy defined |
| Reading Assessment | NOT_STARTED | unchanged; P2 deferred |
| Production Readiness | NOT_STARTED | unchanged |
| Private Homework Overlay | PASS_WITH_LOCAL_SCRATCH_VALIDATION | unchanged |
| Local Runtime Source Pipeline | NOT_STARTED | DESIGN_DEFINED |

Estimated P1 readiness after this task:

```text
P1-M0 Governance / Scope Lock ............ PARTIAL_DONE
P1-M1 Policy & Private Homework Safety ... MOSTLY_DONE
P1-M2 Cambridge Spiral Scope ............. COMPLETED_BY_DESIGN
P1-M3 PracticeBank Contract .............. COMPLETED_BY_DESIGN
P1-M4 PracticeBank Implementation ........ PASS_WITH_LOCAL_SCRATCH_VALIDATION
P1-M5 Private Homework Overlay ........... PASS_WITH_LOCAL_SCRATCH_VALIDATION
P1-M6 Local Runtime Pipeline ............. COMPLETED_BY_DESIGN
P1-M7 Output Gate ........................ NOT_STARTED
P1-M8 HTML Practice Export ............... NOT_STARTED
P1-M9 P1 Closeout QA ..................... NOT_STARTED
```

---

## 15. Gate PASS Checklist

| Gate | Result | Evidence |
|---|---|---|
| Required task header exists | PASS | Section 1 |
| Stop condition exists | PASS | Section 1 |
| Source locator model defined | PASS | Section 4 |
| Allowed / blocked locator types defined | PASS | Section 4 |
| Resolver lifecycle defined | PASS | Section 5 |
| In-memory display payload contract defined | PASS | Section 6 |
| Reviewed snippet exception deferred | PASS | Section 7 |
| Resolver input contract defined | PASS | Section 8 |
| Resolver output contract defined | PASS | Section 9 |
| Future resolver gate requirements defined | PASS | Section 10 |
| Future blocking errors defined | PASS | Section 11 |
| P1-M7 relationship defined | PASS | Section 12 |
| No resolver code implemented | PASS | Documentation-only task |
| No generated artifact committed | PASS | Documentation-only task |
| No HTML generated | PASS | Documentation-only task |
| No RAZ raw text stored | PASS | Documentation-only task |
| No full passage stored | PASS | Documentation-only task |
| No promotion performed | PASS | candidate-only / private runtime boundary |

Task status:

```text
ReadingV1_LocalRuntimeInMemorySourcePipeline_DesignScan -> COMPLETED_BY_DESIGN
```

---

## 16. Deferred Issues Register

### D1

issue_id:
P1-M6_LocalRuntimeInMemorySourcePipeline_Implementation

severity:
required_later_step

affected_file_or_artifact:
ulga/schemas, ulga/validators, ulga/runtime, tests

classification:
FUTURE_WORK

why_deferred:
This task defines source locator and in-memory resolver contract only.

recommended_future_task:
ReadingV1_LocalRuntimeInMemorySourcePipeline_Implementation

blocks_current_task:
no

### D2

issue_id:
P1-M7_PrivateHomeworkOutputGate

severity:
required_next_step

affected_file_or_artifact:
output gate schema / validator / policy checker

classification:
FUTURE_WORK

why_deferred:
Output gate must use PracticeBank, overlay, and source resolver readiness contracts.

recommended_future_task:
ReadingV1_PrivateHomeworkOutputGate_DesignScan

blocks_current_task:
no

### D3

issue_id:
P1-M8_HTMLPracticeExport

severity:
required_later_step

affected_file_or_artifact:
HTML renderer / private homework export artifacts

classification:
FUTURE_WORK

why_deferred:
HTML export must wait for output gate.

recommended_future_task:
ReadingV1_HTMLPracticeExport_Implementation

blocks_current_task:
no

### D4

issue_id:
ReviewedDisplaySnippetPersistence

severity:
operator_policy_required

affected_file_or_artifact:
reviewed snippets / display payload persistence policy

classification:
FUTURE_WORK

why_deferred:
Persisting reviewed snippets changes the source-payload policy and requires explicit operator approval.

recommended_future_task:
ReadingV1_ReviewedDisplaySnippetPolicy_DesignScan

blocks_current_task:
no

---

## 17. Next Shortest Step

NEXT_SHORT_STEP:

```text
ReadingV1_PrivateHomeworkOutputGate_DesignScan
```

唯一執行動作:

```text
定義 private homework package 進入 HTML export 前的總閘門；整合 PracticeBank PASS、overlay_ready、source resolver policy、private-only flags。
```

Next task boundary:

```text
Define output gate contract only.
Do not implement HTML renderer.
Do not generate HTML.
Do not persist source payload.
Do not enter public export or promotion.
```
