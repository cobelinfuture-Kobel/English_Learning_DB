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

The independent validator is:

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

## 7. Change Procedure

A policy change requires all of the following in the same pull request:

1. Update this governance document when the operator-facing rule changes.
2. Update the machine-readable contract.
3. Update the independent validator.
4. Update or add adversarial regression tests.
5. Pass the dedicated GitHub Actions workflow.

No content population, Excel export, or image generation milestone may override this policy by implication.