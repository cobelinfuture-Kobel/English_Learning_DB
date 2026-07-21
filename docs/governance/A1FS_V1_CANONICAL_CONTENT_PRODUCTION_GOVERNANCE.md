# A1FS-V1 Canonical Content Production Governance

## 1. Scope

This policy governs A1 / A1+ content production for the four-skill learning system.

It applies to:

- sentence, dialogue, passage, question, and task generation
- semantic and answerability validation
- scene-contract and image production
- Listening, Speaking, Reading, and Writing task projections
- runtime consumption
- designer-facing Excel exports

A2 remains locked unless a separate approved milestone changes the level scope.

## 2. Hard Rules

```text
CANONICAL_SOURCE = APPROVED_CANONICAL_JSON
FOUR_SKILL_SOURCE = VALIDATED_APPROVED_JSON
EXCEL_ROLE = DERIVED_REFERENCE_ONLY
EXCEL_EXPORT_DIRECTION = JSON_TO_EXCEL_ONLY
EXCEL_TO_CANONICAL_WRITEBACK = FORBIDDEN
UNVALIDATED_JSON_LEARNER_FACING_USE = FORBIDDEN
VALIDATOR_GENERATES_CANDIDATE_CONTENT = FORBIDDEN
POLICY_BOUND_ARTIFACT_REQUIRED = TRUE
```

The builder or generator produces candidate JSON. The validator does not author candidate content. The admission gate decides whether validated candidate JSON may become approved canonical JSON.

No Excel workbook, CSV export, review sheet, preview, generated image, or runtime cache may become a canonical content authority.

## 3. Authority and Production Chain

The required text-content chain is:

```text
Authority Query
-> Candidate JSON Build
-> Schema Validation
-> A1 / A1+ Level Validation
-> Grammar / Vocabulary / Chunk / Pattern Validation
-> Semantic Validation
-> Answerability Validation
-> Admission Decision
-> Approved Canonical JSON
-> Four-Skill Projection JSON
-> Runtime Consumption
-> Excel Reference Export
```

The required multimodal chain is:

```text
Approved Canonical JSON
-> Visualizability Validation
-> Scene Contract JSON
-> Image Generation
-> Image / Scene Consistency Validation
-> Approved Media Manifest JSON
-> Four-Skill Projection JSON
-> Runtime Consumption
-> Excel Reference Export
```

Image generation is prohibited until semantic, answerability, and visualizability gates pass.

A generated image is prohibited from learner-facing use until image / scene consistency validation passes.

## 4. Canonical Artifact Roles

### Candidate JSON

Candidate JSON is generated content awaiting validation and admission. It is not canonical and is not learner-facing by default.

### Approved Canonical JSON

Approved canonical JSON is the sole content authority consumed by four-skill builders and runtime systems.

### Four-Skill Projection JSON

Listening, Speaking, Reading, and Writing projections must derive from approved canonical JSON. Each projection retains its own:

- skill
- prompt
- response mode
- support level
- initiative level
- scoring contract
- evidence level
- source and content identity bindings

### Excel

Excel is generated last from approved JSON for designers, reviewers, coverage inspection, and question-author reference.

Excel is not an editing authority. A finding discovered in Excel must create a revision request that returns to the candidate JSON, validation, and admission flow.

## 5. Forbidden Flows

```text
Excel -> Canonical JSON
CSV -> Canonical JSON
Preview -> Canonical JSON
Generated Image -> Canonical Content Authority
Unvalidated Candidate JSON -> Four-Skill Runtime
Failed Candidate JSON -> Four-Skill Projection
Validator -> Candidate Content Generation
```

## 6. Enforcement

The machine-readable contract is:

```text
ulga/contracts/a1fs_v1_canonical_content_production_policy.json
```

The governance validator is:

```text
ulga/validators/validate_a1fs_v1_canonical_content_production_policy.py
```

The regression tests are:

```text
tests/ulga/test_a1fs_v1_canonical_content_production_policy.py
```

The GitHub Actions gate is:

```text
.github/workflows/a1fs-v1-canonical-content-governance.yml
```

A pull request that changes this policy, the contract, validator, test, workflow, canonical content builders, projection builders, media builders, or Excel exporters must pass the governance workflow before merge.

## 7. Builder Policy Binding and Artifact Validation

Every newly created or modified A1FS-V1, E4S-A1V1, or A1/A1+ builder must explicitly declare one of:

```text
A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
```

A `POLICY_BOUND` builder must import and call the shared transition builder:

```text
ulga/builders/build_a1fs_v1_policy_bound_content_artifact.py
```

It must produce one of the closed policy-bound artifact roles:

```text
CANDIDATE_JSON
APPROVED_CANONICAL_JSON
FOUR_SKILL_PROJECTION_JSON
APPROVED_MEDIA_MANIFEST_JSON
EXCEL_REFERENCE_EXPORT_MANIFEST
```

The independent artifact validator is:

```text
ulga/validators/validate_a1fs_v1_policy_bound_content_artifact.py
```

The closed envelope schema is:

```text
ulga/schemas/a1fs_v1_policy_bound_content_artifact.schema.json
```

The artifact regression suite is:

```text
tests/ulga/test_a1fs_v1_policy_bound_content_artifact.py
```

A `NOT_CONTENT_PRODUCER` builder must declare a non-empty `A1FS_CONTENT_POLICY_EXEMPTION` explaining why it cannot create canonical, projection, media, or Excel artifacts.

The governance CI compares changed builder paths with `main` and fails when a protected builder has no mode declaration, no policy transition binding, or an invalid exemption.

## 8. Change Procedure

A policy change requires all of the following in the same pull request:

1. Update this governance document when the operator-facing rule changes.
2. Update the machine-readable contract.
3. Update the independent governance validator.
4. Update the policy-bound artifact builder, validator, schema, or tests when their contract changes.
5. Update or add adversarial regression tests.
6. Pass the dedicated GitHub Actions workflow.

No content population, Excel export, or image generation milestone may override this policy by implication.
