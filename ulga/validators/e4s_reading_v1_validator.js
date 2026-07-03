/*
 * E4S Reading V1 Validator
 *
 * Task:
 *   E4S-P1-S7_ReadingV1Validator_Implementation
 *
 * Scope:
 *   Validate Reading V1 candidate package and item contracts.
 *
 * Explicitly not implemented here:
 *   - learner state
 *   - adaptive diagnosis
 *   - promotion
 *   - public learner-facing output
 *   - source payload extraction
 *   - network fetch
 *   - persistence
 *   - question generation
 *   - answer checking
 *   - evidence runtime
 *
 * Contract source:
 *   docs/ulga/E4S_P1_READING_QUESTION_PACKAGE_CONTRACT.md
 */

'use strict';

const E4S_READING_V1_VALIDATOR_VERSION = 'E4S_READING_V1_VALIDATOR_V1';

const PACKAGE_SCHEMA_VERSION = 'E4S_READING_QUESTION_PACKAGE_V1';
const PACKAGE_CLASS = 'reading_practice_candidate_package';
const TARGET_PHASE = 'E4S-P1_ReadingV1SourceGroundedPractice';

const ALLOWED_ITEM_TYPES = Object.freeze([
  'literal_who',
  'literal_what',
  'literal_where',
  'true_false',
  'sentence_ordering',
  'cloze_vocabulary'
]);

const ALLOWED_ANSWER_TYPES = Object.freeze([
  'short_text',
  'boolean',
  'ordered_list',
  'cloze_text',
  'multiple_choice'
]);

const ALLOWED_SCORING_POLICIES = Object.freeze([
  'exact_or_accepted_match',
  'boolean_match',
  'ordered_list_exact',
  'cloze_exact',
  'choice_key_match'
]);

const ITEM_TYPE_ANSWER_RULES = Object.freeze({
  literal_who: Object.freeze({
    answer_types: Object.freeze(['short_text', 'multiple_choice']),
    scoring_policies: Object.freeze(['exact_or_accepted_match', 'choice_key_match']),
    order_sensitive: false
  }),
  literal_what: Object.freeze({
    answer_types: Object.freeze(['short_text', 'multiple_choice']),
    scoring_policies: Object.freeze(['exact_or_accepted_match', 'choice_key_match']),
    order_sensitive: false
  }),
  literal_where: Object.freeze({
    answer_types: Object.freeze(['short_text', 'multiple_choice']),
    scoring_policies: Object.freeze(['exact_or_accepted_match', 'choice_key_match']),
    order_sensitive: false
  }),
  true_false: Object.freeze({
    answer_types: Object.freeze(['boolean']),
    scoring_policies: Object.freeze(['boolean_match']),
    order_sensitive: false
  }),
  sentence_ordering: Object.freeze({
    answer_types: Object.freeze(['ordered_list']),
    scoring_policies: Object.freeze(['ordered_list_exact']),
    order_sensitive: true
  }),
  cloze_vocabulary: Object.freeze({
    answer_types: Object.freeze(['cloze_text']),
    scoring_policies: Object.freeze(['cloze_exact']),
    order_sensitive: false
  })
});

const ALLOWED_REVIEW_STATUSES = Object.freeze([
  'not_reviewed',
  'validator_reviewed',
  'human_reviewed',
  'blocked'
]);

const ALLOWED_PROMOTION_STATUSES = Object.freeze([
  'not_promoted',
  'blocked'
]);

const ALLOWED_LEARNER_FACING_STATUSES = Object.freeze([
  'blocked_until_validator_pass',
  'blocked_until_human_review',
  'blocked'
]);

const REQUIRED_PACKAGE_BLOCKED_USE = Object.freeze([
  'learner_facing_publication',
  'final_authority_promotion',
  'adaptive_recommendation',
  'learner_diagnosis',
  'source_payload_redistribution',
  'listening_output',
  'speaking_output',
  'writing_output'
]);

const REQUIRED_ITEM_BLOCKED_USE = Object.freeze([
  'learner_facing_publication_without_validator',
  'promotion_without_review',
  'adaptive_diagnosis',
  'unsupported_item_type_expansion'
]);

const REQUIRED_VALIDATOR_FIELDS = Object.freeze([
  'item_type_allowed',
  'source_trace_present',
  'evidence_present',
  'answer_model_present',
  'evidence_is_direct',
  'inference_required',
  'blocked_scope_absent',
  'learner_state_absent',
  'promotion_status_not_promoted',
  'source_family_allowed_for_reading',
  'status_artifact_not_used_as_source',
  'generated_content_not_used_as_authority'
]);

const PROHIBITED_KEYS = Object.freeze([
  'learner_id',
  'learner_profile',
  'learner_state',
  'adaptive_state',
  'mastery_state',
  'diagnosis',
  'promotion_decision',
  'published_url',
  'public_release'
]);

const VALIDATOR_AUDIT = Object.freeze({
  validator_created: true,
  package_contract_validation_created: true,
  item_contract_validation_created: true,
  learner_state_used: false,
  adaptive_diagnosis_created: false,
  promotion_performed: false,
  public_learner_facing_output_created: false,
  source_payload_extraction_performed: false,
  network_fetch_used: false,
  persistence_used: false,
  question_generator_created: false,
  answer_checker_created: false,
  evidence_runtime_created: false
});

function isPlainObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function safeText(value) {
  if (value === null || value === undefined) return '';
  return String(value).trim();
}

function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

function hasOwn(obj, key) {
  return Object.prototype.hasOwnProperty.call(obj, key);
}

function pushError(errors, code, path, message, severity = 'error') {
  errors.push({ code, path, message, severity });
}

function arrayIncludesAll(actual, required) {
  return Array.isArray(actual) && required.every((entry) => actual.includes(entry));
}

function collectProhibitedKeyPaths(value, basePath = '$', paths = []) {
  if (Array.isArray(value)) {
    value.forEach((entry, index) => collectProhibitedKeyPaths(entry, `${basePath}[${index}]`, paths));
    return paths;
  }

  if (!isPlainObject(value)) return paths;

  Object.keys(value).forEach((key) => {
    const nextPath = `${basePath}.${key}`;
    if (PROHIBITED_KEYS.includes(key)) paths.push(nextPath);
    collectProhibitedKeyPaths(value[key], nextPath, paths);
  });

  return paths;
}

function sourceIdsFromRefs(sourceManifestRefs) {
  if (!Array.isArray(sourceManifestRefs)) return new Set();
  return new Set(
    sourceManifestRefs
      .map((ref) => safeText(ref && ref.source_id))
      .filter(Boolean)
  );
}

function validatePackageShell(pkg, errors) {
  if (!isPlainObject(pkg)) {
    pushError(errors, 'FAIL_PACKAGE_NOT_OBJECT', '$', 'Package must be a plain object.');
    return false;
  }

  if (pkg.schema_version !== PACKAGE_SCHEMA_VERSION) {
    pushError(errors, 'FAIL_SCHEMA_VERSION_INVALID', '$.schema_version', `schema_version must equal ${PACKAGE_SCHEMA_VERSION}.`);
  }

  if (!isNonEmptyString(pkg.package_id)) {
    pushError(errors, 'FAIL_PACKAGE_ID_MISSING', '$.package_id', 'package_id is required.');
  }

  if (!isNonEmptyString(pkg.package_version)) {
    pushError(errors, 'FAIL_PACKAGE_VERSION_MISSING', '$.package_version', 'package_version is required.');
  }

  if (pkg.package_class !== PACKAGE_CLASS) {
    pushError(errors, 'FAIL_PACKAGE_CLASS_INVALID', '$.package_class', `package_class must equal ${PACKAGE_CLASS}.`);
  }

  if (pkg.target_phase !== TARGET_PHASE) {
    pushError(errors, 'FAIL_TARGET_PHASE_INVALID', '$.target_phase', `target_phase must equal ${TARGET_PHASE}.`);
  }

  if (!isNonEmptyString(pkg.created_by_task)) {
    pushError(errors, 'FAIL_CREATED_BY_TASK_MISSING', '$.created_by_task', 'created_by_task is required.');
  }

  if (!Array.isArray(pkg.source_manifest_refs) || pkg.source_manifest_refs.length === 0) {
    pushError(errors, 'FAIL_SOURCE_MANIFEST_REFS_MISSING', '$.source_manifest_refs', 'At least one source_manifest_ref is required.');
  }

  if (!isPlainObject(pkg.package_scope)) {
    pushError(errors, 'FAIL_PACKAGE_SCOPE_MISSING', '$.package_scope', 'package_scope is required.');
  }

  if (!Array.isArray(pkg.items)) {
    pushError(errors, 'FAIL_ITEMS_MISSING', '$.items', 'items must be an array.');
  }

  if (!ALLOWED_REVIEW_STATUSES.includes(pkg.review_status)) {
    pushError(errors, 'FAIL_REVIEW_STATUS_INVALID', '$.review_status', 'review_status is invalid.');
  }

  if (!ALLOWED_PROMOTION_STATUSES.includes(pkg.promotion_status)) {
    pushError(errors, 'FAIL_PROMOTION_STATUS_NOT_ALLOWED', '$.promotion_status', 'promotion_status must remain not_promoted or blocked.');
  }

  if (!ALLOWED_LEARNER_FACING_STATUSES.includes(pkg.learner_facing_status)) {
    pushError(errors, 'FAIL_LEARNER_FACING_STATUS_NOT_ALLOWED', '$.learner_facing_status', 'learner_facing_status must remain blocked.');
  }

  if (!arrayIncludesAll(pkg.blocked_use, REQUIRED_PACKAGE_BLOCKED_USE)) {
    pushError(errors, 'FAIL_PACKAGE_BLOCKED_USE_INCOMPLETE', '$.blocked_use', 'Package blocked_use is missing required blocked uses.');
  }

  return true;
}

function validatePackageScope(packageScope, errors) {
  if (!isPlainObject(packageScope)) return;

  if (packageScope.skill !== 'reading') {
    pushError(errors, 'FAIL_PACKAGE_SCOPE_SKILL_INVALID', '$.package_scope.skill', 'package_scope.skill must be reading.');
  }

  if (!Array.isArray(packageScope.supported_item_types)) {
    pushError(errors, 'FAIL_SUPPORTED_ITEM_TYPES_MISSING', '$.package_scope.supported_item_types', 'supported_item_types must be an array.');
  } else {
    packageScope.supported_item_types.forEach((itemType, index) => {
      if (!ALLOWED_ITEM_TYPES.includes(itemType)) {
        pushError(errors, 'FAIL_SUPPORTED_ITEM_TYPE_NOT_ALLOWED', `$.package_scope.supported_item_types[${index}]`, 'Unsupported Reading V1 item type.');
      }
    });
  }

  if (packageScope.requires_direct_evidence !== true) {
    pushError(errors, 'FAIL_REQUIRES_DIRECT_EVIDENCE_FALSE', '$.package_scope.requires_direct_evidence', 'requires_direct_evidence must be true.');
  }

  if (packageScope.allows_inference_items !== false) {
    pushError(errors, 'FAIL_ALLOWS_INFERENCE_ITEMS_TRUE', '$.package_scope.allows_inference_items', 'allows_inference_items must be false for Reading V1.');
  }
}

function validateSourceManifestRefs(sourceManifestRefs, errors) {
  if (!Array.isArray(sourceManifestRefs)) return;

  sourceManifestRefs.forEach((ref, index) => {
    const path = `$.source_manifest_refs[${index}]`;
    if (!isPlainObject(ref)) {
      pushError(errors, 'FAIL_SOURCE_MANIFEST_REF_NOT_OBJECT', path, 'source_manifest_ref must be an object.');
      return;
    }

    if (!isNonEmptyString(ref.source_id)) pushError(errors, 'FAIL_SOURCE_REF_ID_MISSING', `${path}.source_id`, 'source_id is required.');
    if (!isNonEmptyString(ref.source_family)) pushError(errors, 'FAIL_SOURCE_REF_FAMILY_MISSING', `${path}.source_family`, 'source_family is required.');
    if (ref.manifest_schema_version !== 'E4S_SOURCE_MANIFEST_V1') pushError(errors, 'FAIL_SOURCE_REF_SCHEMA_INVALID', `${path}.manifest_schema_version`, 'manifest_schema_version must be E4S_SOURCE_MANIFEST_V1.');
    if (!isNonEmptyString(ref.manifest_path)) pushError(errors, 'FAIL_SOURCE_REF_MANIFEST_PATH_MISSING', `${path}.manifest_path`, 'manifest_path is required.');
    if (safeText(ref.source_family) === 'status_artifact') pushError(errors, 'FAIL_STATUS_ARTIFACT_USED_AS_SOURCE', `${path}.source_family`, 'status_artifact cannot be used as Reading source.');
    if (safeText(ref.source_family) === 'generated_content_candidate') pushError(errors, 'FAIL_GENERATED_CONTENT_USED_AS_AUTHORITY', `${path}.source_family`, 'generated content cannot be used as direct authority.');
  });
}

function validatePrompt(prompt, itemPath, errors) {
  if (!isPlainObject(prompt)) {
    pushError(errors, 'FAIL_PROMPT_MISSING', `${itemPath}.prompt`, 'prompt is required.');
    return;
  }

  if (!isNonEmptyString(prompt.prompt_text)) pushError(errors, 'FAIL_PROMPT_TEXT_MISSING', `${itemPath}.prompt.prompt_text`, 'prompt_text is required.');
  if (prompt.prompt_language !== 'en') pushError(errors, 'FAIL_PROMPT_LANGUAGE_INVALID', `${itemPath}.prompt.prompt_language`, 'prompt_language must be en.');
  if (prompt.display_mode !== 'text_only') pushError(errors, 'FAIL_PROMPT_DISPLAY_MODE_INVALID', `${itemPath}.prompt.display_mode`, 'display_mode must be text_only for V1.');
  if (prompt.requires_audio !== false) pushError(errors, 'FAIL_PROMPT_REQUIRES_AUDIO', `${itemPath}.prompt.requires_audio`, 'requires_audio must be false.');
  if (prompt.requires_image !== false) pushError(errors, 'FAIL_PROMPT_REQUIRES_IMAGE', `${itemPath}.prompt.requires_image`, 'requires_image must be false unless future image evidence is approved.');
}

function validateSourceTrace(sourceTrace, itemPath, sourceIds, errors) {
  const path = `${itemPath}.source_trace`;
  if (!isPlainObject(sourceTrace)) {
    pushError(errors, 'FAIL_SOURCE_TRACE_MISSING', path, 'source_trace is required.');
    return;
  }

  const requiredFields = [
    'source_id',
    'source_family',
    'source_manifest_ref',
    'source_path_or_reference',
    'source_level_claim',
    'source_level_claim_status',
    'source_unit_id',
    'source_unit_type',
    'source_page_or_location'
  ];

  requiredFields.forEach((field) => {
    if (!isNonEmptyString(sourceTrace[field])) {
      pushError(errors, 'FAIL_SOURCE_TRACE_FIELD_MISSING', `${path}.${field}`, `${field} is required.`);
    }
  });

  if (!sourceIds.has(safeText(sourceTrace.source_id))) {
    pushError(errors, 'FAIL_SOURCE_TRACE_REF_NOT_IN_PACKAGE', `${path}.source_id`, 'source_trace.source_id must match a package-level source_manifest_refs.source_id.');
  }

  if (!Array.isArray(sourceTrace.source_sentence_ids)) {
    pushError(errors, 'FAIL_SOURCE_SENTENCE_IDS_MISSING', `${path}.source_sentence_ids`, 'source_sentence_ids must be an array.');
  }

  if (safeText(sourceTrace.source_family) === 'status_artifact') {
    pushError(errors, 'FAIL_STATUS_ARTIFACT_USED_AS_SOURCE', `${path}.source_family`, 'status_artifact cannot be used as Reading source.');
  }

  if (safeText(sourceTrace.source_family) === 'generated_content_candidate') {
    pushError(errors, 'FAIL_GENERATED_CONTENT_USED_AS_AUTHORITY', `${path}.source_family`, 'generated content cannot be used as direct authority.');
  }
}

function validateSourceEvidence(sourceEvidence, itemType, itemPath, errors) {
  const path = `${itemPath}.source_evidence`;
  if (!isPlainObject(sourceEvidence)) {
    pushError(errors, 'FAIL_EVIDENCE_MISSING', path, 'source_evidence is required.');
    return;
  }

  if (!hasOwn(sourceEvidence, 'evidence_text')) pushError(errors, 'FAIL_EVIDENCE_TEXT_MISSING', `${path}.evidence_text`, 'evidence_text is required unless future quote policy says otherwise.');
  if (!isNonEmptyString(sourceEvidence.evidence_span)) pushError(errors, 'FAIL_EVIDENCE_SPAN_MISSING', `${path}.evidence_span`, 'evidence_span is required.');

  if (['literal_who', 'literal_what', 'literal_where', 'cloze_vocabulary'].includes(itemType) && !isNonEmptyString(sourceEvidence.answer_span)) {
    pushError(errors, 'FAIL_ANSWER_SPAN_MISSING', `${path}.answer_span`, 'answer_span is required for literal and cloze items.');
  }

  if (sourceEvidence.evidence_is_direct !== true) {
    pushError(errors, 'FAIL_EVIDENCE_NOT_DIRECT', `${path}.evidence_is_direct`, 'evidence_is_direct must be true.');
  }

  if (sourceEvidence.inference_required !== false) {
    pushError(errors, 'FAIL_INFERENCE_REQUIRED_NOT_ALLOWED', `${path}.inference_required`, 'inference_required must be false for Reading V1.');
  }

  if (safeText(sourceEvidence.copyright_policy) !== 'no_source_payload_redistribution') {
    pushError(errors, 'FAIL_COPYRIGHT_POLICY_INVALID', `${path}.copyright_policy`, 'copyright_policy must block source payload redistribution.');
  }
}

function validateAnswerModel(answerModel, itemType, itemPath, errors) {
  const path = `${itemPath}.answer_model`;
  if (!isPlainObject(answerModel)) {
    pushError(errors, 'FAIL_ANSWER_MODEL_MISSING', path, 'answer_model is required.');
    return;
  }

  const rules = ITEM_TYPE_ANSWER_RULES[itemType];
  if (!ALLOWED_ANSWER_TYPES.includes(answerModel.answer_type)) {
    pushError(errors, 'FAIL_ANSWER_TYPE_NOT_ALLOWED', `${path}.answer_type`, 'answer_type is not allowed.');
  }

  if (!ALLOWED_SCORING_POLICIES.includes(answerModel.scoring_policy)) {
    pushError(errors, 'FAIL_SCORING_POLICY_NOT_ALLOWED', `${path}.scoring_policy`, 'scoring_policy is not allowed.');
  }

  if (rules) {
    if (!rules.answer_types.includes(answerModel.answer_type)) {
      pushError(errors, 'FAIL_ANSWER_TYPE_ITEM_TYPE_MISMATCH', `${path}.answer_type`, 'answer_type does not match item_type.');
    }
    if (!rules.scoring_policies.includes(answerModel.scoring_policy)) {
      pushError(errors, 'FAIL_SCORING_POLICY_ITEM_TYPE_MISMATCH', `${path}.scoring_policy`, 'scoring_policy does not match item_type.');
    }
    if (answerModel.order_sensitive !== rules.order_sensitive) {
      pushError(errors, 'FAIL_ORDER_SENSITIVE_ITEM_TYPE_MISMATCH', `${path}.order_sensitive`, 'order_sensitive does not match item_type.');
    }
  }

  if (!hasOwn(answerModel, 'canonical_answer')) {
    pushError(errors, 'FAIL_CANONICAL_ANSWER_MISSING', `${path}.canonical_answer`, 'canonical_answer is required.');
  }

  if (!Array.isArray(answerModel.accepted_answers)) {
    pushError(errors, 'FAIL_ACCEPTED_ANSWERS_NOT_ARRAY', `${path}.accepted_answers`, 'accepted_answers must be an array.');
  }

  if (typeof answerModel.case_sensitive !== 'boolean') {
    pushError(errors, 'FAIL_CASE_SENSITIVE_NOT_BOOLEAN', `${path}.case_sensitive`, 'case_sensitive must be boolean.');
  }

  if (typeof answerModel.order_sensitive !== 'boolean') {
    pushError(errors, 'FAIL_ORDER_SENSITIVE_NOT_BOOLEAN', `${path}.order_sensitive`, 'order_sensitive must be boolean.');
  }

  if (typeof answerModel.exact_match_required !== 'boolean') {
    pushError(errors, 'FAIL_EXACT_MATCH_REQUIRED_NOT_BOOLEAN', `${path}.exact_match_required`, 'exact_match_required must be boolean.');
  }

  if (answerModel.distractors !== undefined && !Array.isArray(answerModel.distractors)) {
    pushError(errors, 'FAIL_DISTRACTORS_NOT_ARRAY', `${path}.distractors`, 'distractors must be an array when present.');
  }
}

function validateValidatorFields(validatorFields, itemPath, errors) {
  const path = `${itemPath}.validator_fields`;
  if (!isPlainObject(validatorFields)) {
    pushError(errors, 'FAIL_VALIDATOR_FIELDS_MISSING', path, 'validator_fields are required.');
    return;
  }

  REQUIRED_VALIDATOR_FIELDS.forEach((field) => {
    if (typeof validatorFields[field] !== 'boolean') {
      pushError(errors, 'FAIL_VALIDATOR_FIELD_NOT_BOOLEAN', `${path}.${field}`, `${field} must be explicit boolean.`);
    }
  });

  const mustBeTrue = [
    'item_type_allowed',
    'source_trace_present',
    'evidence_present',
    'answer_model_present',
    'evidence_is_direct',
    'blocked_scope_absent',
    'learner_state_absent',
    'promotion_status_not_promoted',
    'source_family_allowed_for_reading',
    'status_artifact_not_used_as_source',
    'generated_content_not_used_as_authority'
  ];

  mustBeTrue.forEach((field) => {
    if (validatorFields[field] !== true) {
      pushError(errors, 'FAIL_BLOCKING_VALIDATOR_FIELD_FALSE', `${path}.${field}`, `${field} must be true.`);
    }
  });

  if (validatorFields.inference_required !== false) {
    pushError(errors, 'FAIL_VALIDATOR_INFERENCE_FLAG_NOT_FALSE', `${path}.inference_required`, 'inference_required validator field must be false.');
  }
}

function validateItem(item, index, sourceIds, errors) {
  const path = `$.items[${index}]`;
  if (!isPlainObject(item)) {
    pushError(errors, 'FAIL_ITEM_NOT_OBJECT', path, 'Item must be a plain object.');
    return;
  }

  if (!isNonEmptyString(item.item_id)) pushError(errors, 'FAIL_ITEM_ID_MISSING', `${path}.item_id`, 'item_id is required.');

  if (!ALLOWED_ITEM_TYPES.includes(item.item_type)) {
    pushError(errors, 'FAIL_ITEM_TYPE_NOT_ALLOWED', `${path}.item_type`, 'item_type is not allowed for Reading V1.');
  }

  validatePrompt(item.prompt, path, errors);
  validateSourceTrace(item.source_trace, path, sourceIds, errors);
  validateSourceEvidence(item.source_evidence, item.item_type, path, errors);
  validateAnswerModel(item.answer_model, item.item_type, path, errors);
  validateValidatorFields(item.validator_fields, path, errors);

  if (!arrayIncludesAll(item.blocked_use, REQUIRED_ITEM_BLOCKED_USE)) {
    pushError(errors, 'FAIL_ITEM_BLOCKED_USE_INCOMPLETE', `${path}.blocked_use`, 'Item blocked_use is missing required blocked uses.');
  }

  if (!ALLOWED_REVIEW_STATUSES.includes(item.review_status)) {
    pushError(errors, 'FAIL_ITEM_REVIEW_STATUS_INVALID', `${path}.review_status`, 'item review_status is invalid.');
  }
}

function validateNoProhibitedKeys(pkg, errors) {
  collectProhibitedKeyPaths(pkg).forEach((path) => {
    pushError(errors, 'FAIL_PROHIBITED_KEY_PRESENT', path, 'Learner state, adaptive diagnosis, promotion, or publication fields are prohibited in Reading V1 package.', 'error');
  });
}

function validateReadingV1Package(pkg) {
  const errors = [];
  const warnings = [];

  if (!validatePackageShell(pkg, errors)) {
    return buildValidationResult(pkg, errors, warnings);
  }

  validateNoProhibitedKeys(pkg, errors);
  validatePackageScope(pkg.package_scope, errors);
  validateSourceManifestRefs(pkg.source_manifest_refs, errors);

  const sourceIds = sourceIdsFromRefs(pkg.source_manifest_refs);
  if (Array.isArray(pkg.items)) {
    const seenItemIds = new Set();
    pkg.items.forEach((item, index) => {
      if (item && seenItemIds.has(item.item_id)) {
        pushError(errors, 'FAIL_DUPLICATE_ITEM_ID', `$.items[${index}].item_id`, 'item_id must be unique within package.');
      }
      if (item && item.item_id) seenItemIds.add(item.item_id);
      validateItem(item, index, sourceIds, errors);
    });
  }

  if (Array.isArray(pkg.items) && pkg.items.length === 0) {
    pushError(warnings, 'WARN_EMPTY_ITEM_LIST', '$.items', 'Package has no items.', 'warning');
  }

  return buildValidationResult(pkg, errors, warnings);
}

function buildValidationResult(pkg, errors, warnings) {
  const valid = errors.length === 0;
  return {
    validator_version: E4S_READING_V1_VALIDATOR_VERSION,
    status: valid ? 'pass' : 'fail',
    valid,
    package_id: isPlainObject(pkg) ? (pkg.package_id || null) : null,
    error_count: errors.length,
    warning_count: warnings.length,
    errors,
    warnings,
    audit: VALIDATOR_AUDIT,
    p1_distance_after_this_artifact: {
      current_subtask: 'E4S-P1-S7_ReadingV1Validator_Implementation',
      subtask_status: 'COMPLETED',
      p1_completed_tasks: 8,
      p1_total_tasks: 9,
      p1_task_count_progress: '89%',
      d_p1: 1,
      remaining_p1_tasks: [
        'E4S-P1-S8_ReadingV1ExportTestReadback_QA'
      ]
    },
    next_shortest_step: {
      task_id: 'E4S-P1-S8_ReadingV1ExportTestReadback_QA',
      only_next_allowed_action: 'Create an export/test/readback QA artifact for the Reading V1 package, renderer, answer checker, evidence display, generator, and validator; do not create learner state, adaptive diagnosis, promotion artifacts, or public learner-facing output.',
      expected_next_artifact_class: 'reading_v1_export_test_readback_qa',
      stop_condition: 'Stop after QA readback artifact creation; do not create learner state, adaptive diagnosis, promotion artifacts, or public learner-facing output.'
    }
  };
}

const E4SReadingV1Validator = Object.freeze({
  version: E4S_READING_V1_VALIDATOR_VERSION,
  packageSchemaVersion: PACKAGE_SCHEMA_VERSION,
  packageClass: PACKAGE_CLASS,
  targetPhase: TARGET_PHASE,
  allowedItemTypes: ALLOWED_ITEM_TYPES,
  allowedAnswerTypes: ALLOWED_ANSWER_TYPES,
  allowedScoringPolicies: ALLOWED_SCORING_POLICIES,
  itemTypeAnswerRules: ITEM_TYPE_ANSWER_RULES,
  requiredPackageBlockedUse: REQUIRED_PACKAGE_BLOCKED_USE,
  requiredItemBlockedUse: REQUIRED_ITEM_BLOCKED_USE,
  requiredValidatorFields: REQUIRED_VALIDATOR_FIELDS,
  prohibitedKeys: PROHIBITED_KEYS,
  audit: VALIDATOR_AUDIT,
  validateReadingV1Package,
  validatePackageShell,
  validatePackageScope,
  validateSourceManifestRefs,
  validateItem,
  validatePrompt,
  validateSourceTrace,
  validateSourceEvidence,
  validateAnswerModel,
  validateValidatorFields
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = E4SReadingV1Validator;
}

if (typeof window !== 'undefined') {
  window.E4SReadingV1Validator = E4SReadingV1Validator;
}
