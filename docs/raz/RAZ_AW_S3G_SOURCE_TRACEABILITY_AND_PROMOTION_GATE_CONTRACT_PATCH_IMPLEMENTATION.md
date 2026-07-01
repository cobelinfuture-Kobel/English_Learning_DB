# RAZ-AW-S3G Source Traceability and Promotion Gate Contract Patch Implementation

## Preflight

Task:

```text
RAZ-AW-S3G1_AuthorityLinkageContractValidator_LocalImplementation
```

Mode:

```text
Local implementation
Sanitized report only
No corpus mutation
No authority promotion
```

Authority contract used:

```text
schemas/raz/raz_authority_linkage_contract.schema.json
docs/raz/RAZ_AW_S3F_SOURCE_TRACEABILITY_AND_PROMOTION_GATE_CONTRACT_PATCH_DESIGN_SCAN.md
```

Risk level:

```text
Medium
```

Reason:

```text
The validator scans all local normalized/enriched derived artifacts and emits a new report.
It does not change raw corpus, derived corpus, runtime, or authority state.
```

## Files Changed

```text
tools/raz_aw_validate_authority_linkage_contract.py
docs/raz/RAZ_AW_S3G_SOURCE_TRACEABILITY_AND_PROMOTION_GATE_CONTRACT_PATCH_IMPLEMENTATION.md
reports/raz/raz_authority_linkage_contract_validation.json
```

## Scope Completed

Implemented local validator:

```text
tools/raz_aw_validate_authority_linkage_contract.py
```

Validator behavior:

```text
1. Scans raz_output_jsons/derived/Level_*/normalized/*.json
2. Scans raz_output_jsons/derived/Level_*/enriched/*.json
3. Infers artifact type and artifact layer from current legacy file shapes
4. Applies fail-closed checks for contract-required authority-linkage fields
5. Emits sanitized report only:
   reports/raz/raz_authority_linkage_contract_validation.json
6. Does not emit sentence text, page text, raw_text, full_raw_json, or full derived records into the report
```

Implemented fail-closed checks:

```text
missing source_traceability
missing promotion_status
missing generated_content
missing derived_from_original_text
missing allowed_authority_targets
missing blocked_authority_targets
candidate_only marked promoted
reuse_unit_candidate direct promotion
generated content promoted without review
AssessmentAuthority allowed without answer_key / scoring_rule / error diagnosis fields
```

## Safety Boundaries Preserved

```text
No raw corpus modified.
No derived corpus modified.
No Authority promotion performed.
No runtime/API/scheduler/orchestrator change performed.
No text-bearing report emitted.
```

## Local Run Result

Executed command:

```powershell
python tools/raz_aw_validate_authority_linkage_contract.py
```

Observed result:

```text
status: IMPLEMENTED_WITH_BLOCKED_LEGACY_GAPS
files_scanned_count: 161
```

Artifact record counts:

```text
normalized_books: 1959
normalized_sentences: 201993
normalized_page_units: 22632
normalized_reuse_units: 19332
enriched_books: 1959
enriched_sentences: 201993
enriched_units: 41964
```

Blocking legacy gap counts:

```text
RAZ_LINK_MISSING_SOURCE_TRACEABILITY: 491832
RAZ_LINK_MISSING_PROMOTION_STATUS: 491832
RAZ_LINK_MISSING_GENERATED_CONTENT: 491832
RAZ_LINK_MISSING_DERIVED_FROM_ORIGINAL_TEXT: 491832
RAZ_LINK_MISSING_ALLOWED_AUTHORITY_TARGETS: 491832
RAZ_LINK_MISSING_BLOCKED_AUTHORITY_TARGETS: 491832
RAZ_LINK_MISSING_REQUIRED_REVIEW_BEFORE_PROMOTION: 491832
RAZ_LINK_MISSING_AUTHORITY_STATUS: 245916
```

Blockers:

```text
authority_linkage_contract_violations
```

Interpretation:

```text
The validator implementation itself is complete and runnable.
The current local derived corpus is legacy-shaped and does not yet contain the S3F/S3G contract fields.
Because the validator is fail-closed, it correctly blocks authority-linkage readiness instead of inferring or auto-filling missing promotion/traceability fields.
```

## Legacy Gap Notes

Observed legacy shape behavior:

```text
Current normalized records still expose source_ref / authority_status / content_authority_status / review_status,
but do not expose the supplemental S3G contract fields.

Current enriched records still expose authority_linkage_status / review_status / validation_status,
but do not expose the supplemental S3G contract fields either.
```

Important controlled limitation:

```text
This validator intentionally does not mutate the derived corpus to backfill missing contract fields.
It reports the gaps only.
```

## Minimal-Change Recommendation

Next minimal patch should update the normalized/enriched builders or a dedicated bridge-layer emitter to add:

```text
source_traceability
promotion_status
generated_content
derived_from_original_text
allowed_authority_targets
blocked_authority_targets
required_review_before_promotion
```

Do not patch the validator to silently infer promotion-safe defaults into the report output.

Reason:

```text
Silent inference would hide real corpus contract gaps and weaken fail-closed safety.
```

## Final Status

```text
IMPLEMENTED_WITH_BLOCKED_LEGACY_GAPS
```

Reason:

```text
The local validator is implemented and runnable,
but the scanned legacy normalized/enriched artifacts do not yet satisfy the authority-linkage contract.
```
