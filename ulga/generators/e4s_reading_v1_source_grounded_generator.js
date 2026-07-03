/*
 * E4S Reading V1 Source-Grounded Question Generator
 *
 * Task:
 *   E4S-P1-S6_SourceGroundedQuestionGenerator_Implementation
 *
 * Scope:
 *   Create candidate Reading V1 items from already supplied source_trace,
 *   source_evidence, and item candidate inputs.
 *
 * Explicitly not implemented here:
 *   - validator
 *   - learner state
 *   - adaptive diagnosis
 *   - promotion
 *   - public learner-facing output
 *   - source payload extraction
 *   - network fetch
 *   - persistence
 *   - evidence runtime
 *   - answer checking
 *
 * Contract source:
 *   docs/ulga/E4S_P1_READING_QUESTION_PACKAGE_CONTRACT.md
 */

'use strict';

const E4S_READING_V1_GENERATOR_VERSION = 'E4S_READING_V1_SOURCE_GROUNDED_GENERATOR_V1';

const ALLOWED_ITEM_TYPES = Object.freeze([
  'literal_who',
  'literal_what',
  'literal_where',
  'true_false',
  'sentence_ordering',
  'cloze_vocabulary'
]);

const ITEM_TYPE_DEFAULTS = Object.freeze({
  literal_who: Object.freeze({
    answer_type: 'short_text',
    scoring_policy: 'exact_or_accepted_match',
    order_sensitive: false
  }),
  literal_what: Object.freeze({
    answer_type: 'short_text',
    scoring_policy: 'exact_or_accepted_match',
    order_sensitive: false
  }),
  literal_where: Object.freeze({
    answer_type: 'short_text',
    scoring_policy: 'exact_or_accepted_match',
    order_sensitive: false
  }),
  true_false: Object.freeze({
    answer_type: 'boolean',
    scoring_policy: 'boolean_match',
    order_sensitive: false
  }),
  sentence_ordering: Object.freeze({
    answer_type: 'ordered_list',
    scoring_policy: 'ordered_list_exact',
    order_sensitive: true
  }),
  cloze_vocabulary: Object.freeze({
    answer_type: 'cloze_text',
    scoring_policy: 'cloze_exact',
    order_sensitive: false
  })
});

const GENERATOR_AUDIT = Object.freeze({
  generator_created: true,
  source_grounded_only: true,
  accepted_input_requires_existing_source_trace: true,
  accepted_input_requires_existing_source_evidence: true,
  validator_created: false,
  learner_state_used: false,
  adaptive_diagnosis_created: false,
  promotion_performed: false,
  public_learner_facing_output_created: false,
  source_payload_extraction_performed: false,
  network_fetch_used: false,
  persistence_used: false,
  evidence_runtime_created: false,
  answer_checker_created: false
});

function isPlainObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function safeText(value) {
  if (value === null || value === undefined) return '';
  return String(value).trim();
}

function slug(value) {
  return safeText(value)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '') || 'unit';
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

function defaultBlockedUse() {
  return [
    'learner_facing_publication_without_validator',
    'promotion_without_review',
    'adaptive_diagnosis',
    'unsupported_item_type_expansion'
  ];
}

function packageBlockedUse() {
  return [
    'learner_facing_publication',
    'final_authority_promotion',
    'adaptive_recommendation',
    'learner_diagnosis',
    'source_payload_redistribution',
    'listening_output',
    'speaking_output',
    'writing_output'
  ];
}

function allowedItemType(itemType) {
  return ALLOWED_ITEM_TYPES.includes(itemType);
}

function hasRequiredSourceTrace(sourceTrace) {
  return isPlainObject(sourceTrace)
    && Boolean(safeText(sourceTrace.source_id))
    && Boolean(safeText(sourceTrace.source_family))
    && Boolean(safeText(sourceTrace.source_manifest_ref))
    && Boolean(safeText(sourceTrace.source_unit_id))
    && Boolean(safeText(sourceTrace.source_unit_type));
}

function hasRequiredSourceEvidence(sourceEvidence) {
  return isPlainObject(sourceEvidence)
    && Boolean(safeText(sourceEvidence.evidence_span))
    && Object.prototype.hasOwnProperty.call(sourceEvidence, 'answer_span')
    && sourceEvidence.evidence_is_direct === true
    && sourceEvidence.inference_required === false
    && safeText(sourceEvidence.copyright_policy) === 'no_source_payload_redistribution';
}

function sourceTraceForCandidate(sourceUnit, candidate) {
  const baseTrace = isPlainObject(sourceUnit && sourceUnit.source_trace)
    ? sourceUnit.source_trace
    : {};
  const traceOverride = isPlainObject(candidate && candidate.source_trace)
    ? candidate.source_trace
    : {};
  return {
    ...cloneJson(baseTrace),
    ...cloneJson(traceOverride)
  };
}

function sourceEvidenceForCandidate(sourceUnit, candidate) {
  const candidateEvidence = isPlainObject(candidate && candidate.source_evidence)
    ? candidate.source_evidence
    : {};
  const sourceEvidence = isPlainObject(sourceUnit && sourceUnit.source_evidence)
    ? sourceUnit.source_evidence
    : {};
  return {
    ...cloneJson(sourceEvidence),
    ...cloneJson(candidateEvidence),
    evidence_is_direct: candidateEvidence.evidence_is_direct === undefined
      ? sourceEvidence.evidence_is_direct === true
      : candidateEvidence.evidence_is_direct === true,
    inference_required: candidateEvidence.inference_required === undefined
      ? sourceEvidence.inference_required === true
      : candidateEvidence.inference_required === true,
    copyright_policy: safeText(candidateEvidence.copyright_policy || sourceEvidence.copyright_policy || 'no_source_payload_redistribution')
  };
}

function answerModelForCandidate(candidate) {
  const itemType = safeText(candidate && candidate.item_type);
  const defaults = ITEM_TYPE_DEFAULTS[itemType];
  if (!defaults) return null;

  const canonicalAnswer = Object.prototype.hasOwnProperty.call(candidate, 'canonical_answer')
    ? candidate.canonical_answer
    : candidate.answer;

  const acceptedAnswers = Array.isArray(candidate.accepted_answers)
    ? candidate.accepted_answers
    : [canonicalAnswer].filter((value) => value !== undefined && value !== null);

  return {
    answer_type: candidate.answer_type || defaults.answer_type,
    canonical_answer: canonicalAnswer,
    accepted_answers: acceptedAnswers,
    case_sensitive: Boolean(candidate.case_sensitive),
    order_sensitive: defaults.order_sensitive,
    exact_match_required: candidate.exact_match_required === undefined
      ? true
      : Boolean(candidate.exact_match_required),
    scoring_policy: candidate.scoring_policy || defaults.scoring_policy,
    distractors: Array.isArray(candidate.distractors) ? candidate.distractors : []
  };
}

function buildValidatorReadableFields(sourceTrace, sourceEvidence, itemType) {
  return {
    item_type_allowed: allowedItemType(itemType),
    source_trace_present: hasRequiredSourceTrace(sourceTrace),
    evidence_present: hasRequiredSourceEvidence(sourceEvidence),
    answer_model_present: true,
    evidence_is_direct: sourceEvidence.evidence_is_direct === true,
    inference_required: sourceEvidence.inference_required === true,
    blocked_scope_absent: true,
    learner_state_absent: true,
    promotion_status_not_promoted: true,
    source_family_allowed_for_reading: safeText(sourceTrace.source_family).length > 0,
    status_artifact_not_used_as_source: safeText(sourceTrace.source_family) !== 'status_artifact',
    generated_content_not_used_as_authority: safeText(sourceTrace.source_family) !== 'generated_content_candidate'
  };
}

function candidateIsGenerationEligible(sourceTrace, sourceEvidence, candidate) {
  const itemType = safeText(candidate && candidate.item_type);
  const answerModel = answerModelForCandidate(candidate || {});
  const reasons = [];

  if (!allowedItemType(itemType)) reasons.push('ITEM_TYPE_NOT_ALLOWED');
  if (!hasRequiredSourceTrace(sourceTrace)) reasons.push('SOURCE_TRACE_INCOMPLETE');
  if (!hasRequiredSourceEvidence(sourceEvidence)) reasons.push('SOURCE_EVIDENCE_INCOMPLETE_OR_NOT_DIRECT');
  if (!answerModel) reasons.push('ANSWER_MODEL_UNAVAILABLE');
  if (answerModel && answerModel.canonical_answer === undefined) reasons.push('CANONICAL_ANSWER_MISSING');
  if (!safeText(candidate && candidate.prompt_text)) reasons.push('PROMPT_TEXT_MISSING');
  if (safeText(sourceTrace.source_family) === 'status_artifact') reasons.push('STATUS_ARTIFACT_BLOCKED_AS_SOURCE');
  if (safeText(sourceTrace.source_family) === 'generated_content_candidate') reasons.push('GENERATED_CONTENT_BLOCKED_AS_AUTHORITY');

  return {
    eligible: reasons.length === 0,
    reasons
  };
}

function buildItemId(itemType, sourceTrace, sequence) {
  return [
    slug(itemType),
    slug(sourceTrace.source_unit_id || sourceTrace.source_page_or_location || 'source'),
    String(sequence).padStart(3, '0')
  ].join('_');
}

function buildPrompt(candidate) {
  return {
    prompt_text: safeText(candidate.prompt_text),
    prompt_language: safeText(candidate.prompt_language || 'en'),
    display_mode: safeText(candidate.display_mode || 'text_only'),
    choices: Array.isArray(candidate.choices) ? cloneJson(candidate.choices) : [],
    requires_audio: false,
    requires_image: false
  };
}

function generateItemFromCandidate(sourceUnit, candidate, sequence) {
  const safeCandidate = isPlainObject(candidate) ? candidate : {};
  const itemType = safeText(safeCandidate.item_type);
  const sourceTrace = sourceTraceForCandidate(sourceUnit, safeCandidate);
  const sourceEvidence = sourceEvidenceForCandidate(sourceUnit, safeCandidate);
  const eligibility = candidateIsGenerationEligible(sourceTrace, sourceEvidence, safeCandidate);

  if (!eligibility.eligible) {
    return {
      generated: false,
      reasons: eligibility.reasons,
      candidate_type: itemType || null,
      source_unit_id: safeText(sourceTrace.source_unit_id) || null
    };
  }

  const answerModel = answerModelForCandidate(safeCandidate);
  const validatorFields = buildValidatorReadableFields(sourceTrace, sourceEvidence, itemType);

  return {
    generated: true,
    item: {
      item_id: safeText(safeCandidate.item_id) || buildItemId(itemType, sourceTrace, sequence),
      item_type: itemType,
      prompt: buildPrompt(safeCandidate),
      source_trace: sourceTrace,
      source_evidence: sourceEvidence,
      answer_model: answerModel,
      validator_fields: validatorFields,
      blocked_use: defaultBlockedUse(),
      review_status: 'not_reviewed'
    }
  };
}

function collectCandidatesFromSourceUnits(sourceUnits) {
  const units = Array.isArray(sourceUnits) ? sourceUnits : [];
  const collected = [];

  units.forEach((sourceUnit, unitIndex) => {
    const candidates = Array.isArray(sourceUnit && sourceUnit.item_candidates)
      ? sourceUnit.item_candidates
      : [];
    candidates.forEach((candidate, candidateIndex) => {
      collected.push({
        sourceUnit,
        candidate,
        original_order: [unitIndex, candidateIndex]
      });
    });
  });

  return collected;
}

function generateItemsFromSourceUnits(sourceUnits, options = {}) {
  const maxItems = Number.isInteger(options.max_items) ? options.max_items : 10;
  const collected = collectCandidatesFromSourceUnits(sourceUnits);
  const generatedItems = [];
  const skippedCandidates = [];

  collected.forEach(({ sourceUnit, candidate }) => {
    if (generatedItems.length >= maxItems) {
      skippedCandidates.push({
        generated: false,
        reasons: ['MAX_ITEMS_REACHED'],
        candidate_type: safeText(candidate && candidate.item_type) || null
      });
      return;
    }

    const result = generateItemFromCandidate(sourceUnit, candidate, generatedItems.length + 1);
    if (result.generated) {
      generatedItems.push(result.item);
    } else {
      skippedCandidates.push(result);
    }
  });

  return {
    items: generatedItems,
    skipped_candidates: skippedCandidates
  };
}

function buildPackageScope(options = {}) {
  return {
    skill: 'reading',
    supported_item_types: Array.isArray(options.supported_item_types)
      ? options.supported_item_types.filter(allowedItemType)
      : ALLOWED_ITEM_TYPES.slice(),
    allowed_item_type_universe: ALLOWED_ITEM_TYPES.slice(),
    level_claim_policy: 'source_claim_only_until_validated',
    source_unit_policy: 'single_source_unit_or_explicit_multi_unit',
    max_items: Number.isInteger(options.max_items) ? options.max_items : 10,
    requires_direct_evidence: true,
    allows_inference_items: false,
    generator_scope_note: 'Items are generated only from supplied source_trace, source_evidence, and item_candidates. No source payload extraction or free-form question invention is performed.'
  };
}

function generateCandidatePackage(input = {}) {
  const sourceUnits = Array.isArray(input.source_units) ? input.source_units : [];
  const packageScope = buildPackageScope(input.package_scope || input);
  const generated = generateItemsFromSourceUnits(sourceUnits, { max_items: packageScope.max_items });

  return {
    schema_version: 'E4S_READING_QUESTION_PACKAGE_V1',
    package_id: safeText(input.package_id || 'reading_pkg_generated_candidate_0001'),
    package_version: 'v1',
    package_class: 'reading_practice_candidate_package',
    target_phase: 'E4S-P1_ReadingV1SourceGroundedPractice',
    created_by_task: 'E4S-P1-S6_SourceGroundedQuestionGenerator_Implementation',
    source_manifest_refs: Array.isArray(input.source_manifest_refs)
      ? cloneJson(input.source_manifest_refs)
      : [],
    package_scope: packageScope,
    items: generated.items,
    review_status: 'not_reviewed',
    promotion_status: 'not_promoted',
    learner_facing_status: 'blocked_until_validator_pass',
    blocked_use: packageBlockedUse(),
    validator_summary: {
      validator_implemented: false,
      expected_validator_task: 'E4S-P1-S7_ReadingV1Validator_Implementation',
      item_count: generated.items.length,
      skipped_candidate_count: generated.skipped_candidates.length,
      formal_validation_performed: false,
      all_items_candidate_generated: true,
      source_payload_extraction_performed: false,
      learner_facing_output_created: false,
      promotion_performed: false
    },
    generator_summary: {
      generator_version: E4S_READING_V1_GENERATOR_VERSION,
      source_unit_count: sourceUnits.length,
      candidate_count: collectCandidatesFromSourceUnits(sourceUnits).length,
      generated_item_count: generated.items.length,
      skipped_candidates: generated.skipped_candidates,
      deterministic_order: 'source_units_order_then_item_candidates_order'
    },
    audit: {
      ...GENERATOR_AUDIT,
      created_by_task: 'E4S-P1-S6_SourceGroundedQuestionGenerator_Implementation',
      contract_source: 'docs/ulga/E4S_P1_READING_QUESTION_PACKAGE_CONTRACT.md',
      build_mode: 'static_offline_candidate_generator',
      candidate_package_only: true
    },
    p1_distance_after_this_artifact: {
      current_subtask: 'E4S-P1-S6_SourceGroundedQuestionGenerator_Implementation',
      subtask_status: 'COMPLETED',
      p1_completed_tasks: 7,
      p1_total_tasks: 9,
      p1_task_count_progress: '78%',
      d_p1: 2,
      remaining_p1_tasks: [
        'E4S-P1-S7_ReadingV1Validator_Implementation',
        'E4S-P1-S8_ReadingV1ExportTestReadback_QA'
      ]
    },
    next_shortest_step: {
      task_id: 'E4S-P1-S7_ReadingV1Validator_Implementation',
      only_next_allowed_action: 'Create a validator for Reading V1 package and item contracts; do not create learner state, adaptive diagnosis, promotion artifacts, or public learner-facing output.',
      expected_next_artifact_class: 'reading_v1_validator',
      stop_condition: 'Stop after validator creation; do not create learner state, adaptive diagnosis, promotion artifacts, or public learner-facing output until their explicit tasks are started.'
    }
  };
}

const E4SReadingV1SourceGroundedGenerator = Object.freeze({
  version: E4S_READING_V1_GENERATOR_VERSION,
  allowedItemTypes: ALLOWED_ITEM_TYPES,
  itemTypeDefaults: ITEM_TYPE_DEFAULTS,
  audit: GENERATOR_AUDIT,
  allowedItemType,
  hasRequiredSourceTrace,
  hasRequiredSourceEvidence,
  answerModelForCandidate,
  buildValidatorReadableFields,
  candidateIsGenerationEligible,
  generateItemFromCandidate,
  generateItemsFromSourceUnits,
  generateCandidatePackage
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = E4SReadingV1SourceGroundedGenerator;
}

if (typeof window !== 'undefined') {
  window.E4SReadingV1SourceGroundedGenerator = E4SReadingV1SourceGroundedGenerator;
}
