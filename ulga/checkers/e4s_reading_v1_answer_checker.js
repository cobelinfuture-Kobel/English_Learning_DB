/*
 * E4S Reading V1 Answer Checker
 *
 * Task:
 *   E4S-P1-S4_ReadingAnswerChecker_Implementation
 *
 * Scope:
 *   Evaluate existing Reading V1 answer_model structures only.
 *
 * Explicitly not implemented here:
 *   - evidence runtime
 *   - source trace validation
 *   - package validation
 *   - question generation
 *   - learner state
 *   - adaptive diagnosis
 *   - promotion
 *   - persistence
 *   - network fetch
 *   - DOM rendering
 *
 * Contract source:
 *   docs/ulga/E4S_P1_READING_QUESTION_PACKAGE_CONTRACT.md
 */

'use strict';

const E4S_READING_V1_ANSWER_CHECKER_VERSION = 'E4S_READING_V1_ANSWER_CHECKER_V1';

const SUPPORTED_ANSWER_TYPES = Object.freeze([
  'short_text',
  'boolean',
  'ordered_list',
  'cloze_text',
  'multiple_choice'
]);

const SUPPORTED_SCORING_POLICIES = Object.freeze([
  'exact_or_accepted_match',
  'boolean_match',
  'ordered_list_exact',
  'cloze_exact',
  'choice_key_match'
]);

const BLOCKED_SCOPE_AUDIT = Object.freeze({
  evidence_runtime_created: false,
  generator_created: false,
  validator_created: false,
  learner_state_used: false,
  adaptive_diagnosis_created: false,
  promotion_performed: false,
  persistence_used: false,
  network_fetch_used: false,
  dom_rendering_used: false
});

function normalizeScalar(value, options = {}) {
  if (value === null || value === undefined) return '';
  const text = String(value).trim().replace(/\s+/g, ' ');
  return options.caseSensitive ? text : text.toLowerCase();
}

function normalizeBoolean(value) {
  if (typeof value === 'boolean') return value;
  if (typeof value === 'number') {
    if (value === 1) return true;
    if (value === 0) return false;
  }
  if (typeof value === 'string') {
    const normalized = normalizeScalar(value);
    if (['true', 't', 'yes', 'y', '1'].includes(normalized)) return true;
    if (['false', 'f', 'no', 'n', '0'].includes(normalized)) return false;
  }
  return undefined;
}

function normalizeList(value, options = {}) {
  if (Array.isArray(value)) {
    return value.map((entry) => normalizeScalar(entry, options));
  }
  if (typeof value === 'string') {
    return value
      .split('|')
      .map((entry) => normalizeScalar(entry, options))
      .filter((entry) => entry.length > 0);
  }
  return [];
}

function ensureAnswerModel(answerModel) {
  const errors = [];

  if (!answerModel || typeof answerModel !== 'object' || Array.isArray(answerModel)) {
    return {
      ok: false,
      errors: ['ANSWER_MODEL_NOT_OBJECT']
    };
  }

  if (!SUPPORTED_ANSWER_TYPES.includes(answerModel.answer_type)) {
    errors.push('UNSUPPORTED_ANSWER_TYPE');
  }

  if (!SUPPORTED_SCORING_POLICIES.includes(answerModel.scoring_policy)) {
    errors.push('UNSUPPORTED_SCORING_POLICY');
  }

  if (!Object.prototype.hasOwnProperty.call(answerModel, 'canonical_answer')) {
    errors.push('CANONICAL_ANSWER_MISSING');
  }

  if (answerModel.accepted_answers !== undefined && !Array.isArray(answerModel.accepted_answers)) {
    errors.push('ACCEPTED_ANSWERS_NOT_ARRAY');
  }

  if (typeof answerModel.exact_match_required !== 'boolean') {
    errors.push('EXACT_MATCH_REQUIRED_NOT_BOOLEAN');
  }

  if (answerModel.case_sensitive !== undefined && typeof answerModel.case_sensitive !== 'boolean') {
    errors.push('CASE_SENSITIVE_NOT_BOOLEAN');
  }

  if (answerModel.order_sensitive !== undefined && typeof answerModel.order_sensitive !== 'boolean') {
    errors.push('ORDER_SENSITIVE_NOT_BOOLEAN');
  }

  return {
    ok: errors.length === 0,
    errors
  };
}

function candidateAnswers(answerModel) {
  const accepted = Array.isArray(answerModel.accepted_answers) ? answerModel.accepted_answers : [];
  return [answerModel.canonical_answer, ...accepted];
}

function checkExactOrAcceptedMatch(answerModel, learnerAnswer) {
  const options = { caseSensitive: Boolean(answerModel.case_sensitive) };
  const normalizedLearner = normalizeScalar(learnerAnswer, options);
  const normalizedAccepted = candidateAnswers(answerModel).map((entry) => normalizeScalar(entry, options));
  return normalizedAccepted.includes(normalizedLearner);
}

function checkBooleanMatch(answerModel, learnerAnswer) {
  const expected = normalizeBoolean(answerModel.canonical_answer);
  const actual = normalizeBoolean(learnerAnswer);
  if (expected === undefined || actual === undefined) return false;
  return actual === expected;
}

function checkOrderedListExact(answerModel, learnerAnswer) {
  const options = { caseSensitive: Boolean(answerModel.case_sensitive) };
  const expected = normalizeList(answerModel.canonical_answer, options);
  const actual = normalizeList(learnerAnswer, options);
  if (expected.length !== actual.length) return false;
  return expected.every((entry, index) => entry === actual[index]);
}

function checkClozeExact(answerModel, learnerAnswer) {
  const options = { caseSensitive: Boolean(answerModel.case_sensitive) };
  const normalizedLearner = normalizeScalar(learnerAnswer, options);
  const normalizedAccepted = candidateAnswers(answerModel).map((entry) => normalizeScalar(entry, options));
  return normalizedAccepted.includes(normalizedLearner);
}

function checkChoiceKeyMatch(answerModel, learnerAnswer) {
  const options = { caseSensitive: Boolean(answerModel.case_sensitive) };
  const normalizedLearner = normalizeScalar(learnerAnswer, options);
  const normalizedAccepted = candidateAnswers(answerModel).map((entry) => normalizeScalar(entry, options));
  return normalizedAccepted.includes(normalizedLearner);
}

function scoreAnswer(answerModel, learnerAnswer) {
  const preflight = ensureAnswerModel(answerModel);
  if (!preflight.ok) {
    return {
      checker_version: E4S_READING_V1_ANSWER_CHECKER_VERSION,
      status: 'invalid_answer_model',
      correct: false,
      score: 0,
      errors: preflight.errors,
      audit: BLOCKED_SCOPE_AUDIT
    };
  }

  let correct = false;

  switch (answerModel.scoring_policy) {
    case 'exact_or_accepted_match':
      correct = checkExactOrAcceptedMatch(answerModel, learnerAnswer);
      break;
    case 'boolean_match':
      correct = checkBooleanMatch(answerModel, learnerAnswer);
      break;
    case 'ordered_list_exact':
      correct = checkOrderedListExact(answerModel, learnerAnswer);
      break;
    case 'cloze_exact':
      correct = checkClozeExact(answerModel, learnerAnswer);
      break;
    case 'choice_key_match':
      correct = checkChoiceKeyMatch(answerModel, learnerAnswer);
      break;
    default:
      correct = false;
  }

  return {
    checker_version: E4S_READING_V1_ANSWER_CHECKER_VERSION,
    status: 'checked',
    correct,
    score: correct ? 1 : 0,
    errors: [],
    scoring_policy: answerModel.scoring_policy,
    answer_type: answerModel.answer_type,
    exact_match_required: answerModel.exact_match_required,
    case_sensitive: Boolean(answerModel.case_sensitive),
    order_sensitive: Boolean(answerModel.order_sensitive),
    audit: BLOCKED_SCOPE_AUDIT
  };
}

function scoreItemAnswer(item, learnerAnswer) {
  if (!item || typeof item !== 'object' || Array.isArray(item)) {
    return {
      checker_version: E4S_READING_V1_ANSWER_CHECKER_VERSION,
      status: 'invalid_item',
      correct: false,
      score: 0,
      errors: ['ITEM_NOT_OBJECT'],
      audit: BLOCKED_SCOPE_AUDIT
    };
  }

  if (!item.answer_model) {
    return {
      checker_version: E4S_READING_V1_ANSWER_CHECKER_VERSION,
      status: 'invalid_item',
      item_id: item.item_id || null,
      correct: false,
      score: 0,
      errors: ['ITEM_ANSWER_MODEL_MISSING'],
      audit: BLOCKED_SCOPE_AUDIT
    };
  }

  const result = scoreAnswer(item.answer_model, learnerAnswer);
  return {
    ...result,
    item_id: item.item_id || null,
    item_type: item.item_type || null
  };
}

function scorePackageAnswers(packageData, learnerAnswersByItemId) {
  if (!packageData || typeof packageData !== 'object' || !Array.isArray(packageData.items)) {
    return {
      checker_version: E4S_READING_V1_ANSWER_CHECKER_VERSION,
      status: 'invalid_package_for_answer_checking',
      score: 0,
      max_score: 0,
      item_results: [],
      errors: ['PACKAGE_ITEMS_MISSING'],
      audit: BLOCKED_SCOPE_AUDIT
    };
  }

  const answers = learnerAnswersByItemId && typeof learnerAnswersByItemId === 'object'
    ? learnerAnswersByItemId
    : {};

  const itemResults = packageData.items.map((item) => {
    const learnerAnswer = Object.prototype.hasOwnProperty.call(answers, item.item_id)
      ? answers[item.item_id]
      : undefined;
    return scoreItemAnswer(item, learnerAnswer);
  });

  const score = itemResults.reduce((total, result) => total + result.score, 0);
  const maxScore = itemResults.length;

  return {
    checker_version: E4S_READING_V1_ANSWER_CHECKER_VERSION,
    status: 'checked',
    package_id: packageData.package_id || null,
    score,
    max_score: maxScore,
    percent: maxScore === 0 ? 0 : Math.round((score / maxScore) * 100),
    item_results: itemResults,
    errors: [],
    audit: BLOCKED_SCOPE_AUDIT,
    p1_distance_after_this_artifact: {
      current_subtask: 'E4S-P1-S4_ReadingAnswerChecker_Implementation',
      subtask_status: 'COMPLETED',
      p1_completed_tasks: 5,
      p1_total_tasks: 9,
      p1_task_count_progress: '56%',
      d_p1: 4,
      remaining_p1_tasks: [
        'E4S-P1-S5_ReadingEvidenceDisplay_Implementation',
        'E4S-P1-S6_SourceGroundedQuestionGenerator_Implementation',
        'E4S-P1-S7_ReadingV1Validator_Implementation',
        'E4S-P1-S8_ReadingV1ExportTestReadback_QA'
      ]
    },
    next_shortest_step: {
      task_id: 'E4S-P1-S5_ReadingEvidenceDisplay_Implementation',
      only_next_allowed_action: 'Create evidence display wiring for existing source_trace and source_evidence structures only; do not create generator, validator, learner state, adaptive diagnosis, or promotion artifacts.',
      expected_next_artifact_class: 'review_only_evidence_display',
      stop_condition: 'Stop after evidence display creation; do not create generator, validator, learner state, adaptive diagnosis, or promotion artifacts until their explicit P1 tasks are started.'
    }
  };
}

const E4SReadingV1AnswerChecker = Object.freeze({
  version: E4S_READING_V1_ANSWER_CHECKER_VERSION,
  supportedAnswerTypes: SUPPORTED_ANSWER_TYPES,
  supportedScoringPolicies: SUPPORTED_SCORING_POLICIES,
  audit: BLOCKED_SCOPE_AUDIT,
  normalizeScalar,
  normalizeBoolean,
  normalizeList,
  ensureAnswerModel,
  scoreAnswer,
  scoreItemAnswer,
  scorePackageAnswers
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = E4SReadingV1AnswerChecker;
}

if (typeof window !== 'undefined') {
  window.E4SReadingV1AnswerChecker = E4SReadingV1AnswerChecker;
}
