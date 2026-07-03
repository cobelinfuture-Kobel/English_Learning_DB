/*
 * E4S Reading V1 Evidence Display
 *
 * Task:
 *   E4S-P1-S5_ReadingEvidenceDisplay_Implementation
 *
 * Scope:
 *   Display existing source_trace and source_evidence structures for review-only use.
 *
 * Explicitly not implemented here:
 *   - source validation
 *   - answer checking
 *   - question generation
 *   - package validation
 *   - learner state
 *   - adaptive diagnosis
 *   - promotion
 *   - persistence
 *   - network fetch
 *   - source payload extraction
 *
 * Input contract:
 *   ulga/graph/e4s_reading_v1_sample_question_package.json
 *   docs/ulga/E4S_P1_READING_QUESTION_PACKAGE_CONTRACT.md
 */

'use strict';

const E4S_READING_V1_EVIDENCE_DISPLAY_VERSION = 'E4S_READING_V1_EVIDENCE_DISPLAY_V1';

const EVIDENCE_DISPLAY_AUDIT = Object.freeze({
  source_validation_created: false,
  answer_checker_created: false,
  generator_created: false,
  validator_created: false,
  learner_state_used: false,
  adaptive_diagnosis_created: false,
  promotion_performed: false,
  persistence_used: false,
  network_fetch_used: false,
  source_payload_extraction_performed: false
});

function safeText(value) {
  if (value === null || value === undefined) return '';
  return String(value);
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function summarizeSourceTrace(sourceTrace) {
  const trace = isPlainObject(sourceTrace) ? sourceTrace : {};
  return {
    source_id: safeText(trace.source_id),
    source_family: safeText(trace.source_family),
    source_manifest_ref: safeText(trace.source_manifest_ref),
    source_path_or_reference: safeText(trace.source_path_or_reference),
    source_level_claim: safeText(trace.source_level_claim),
    source_level_claim_status: safeText(trace.source_level_claim_status),
    source_unit_id: safeText(trace.source_unit_id),
    source_unit_type: safeText(trace.source_unit_type),
    source_sentence_ids: Array.isArray(trace.source_sentence_ids)
      ? trace.source_sentence_ids.map(safeText)
      : [],
    source_page_or_location: safeText(trace.source_page_or_location)
  };
}

function summarizeSourceEvidence(sourceEvidence) {
  const evidence = isPlainObject(sourceEvidence) ? sourceEvidence : {};
  return {
    evidence_text: safeText(evidence.evidence_text),
    evidence_span: safeText(evidence.evidence_span),
    answer_span: safeText(evidence.answer_span),
    source_sentence_quote_policy: safeText(evidence.source_sentence_quote_policy),
    evidence_is_direct: evidence.evidence_is_direct === true,
    inference_required: evidence.inference_required === true,
    evidence_transform: safeText(evidence.evidence_transform),
    copyright_policy: safeText(evidence.copyright_policy)
  };
}

function buildEvidenceDisplayModelForItem(item) {
  const safeItem = isPlainObject(item) ? item : {};
  return {
    item_id: safeText(safeItem.item_id),
    item_type: safeText(safeItem.item_type),
    review_status: safeText(safeItem.review_status || 'not_reviewed'),
    prompt_text: safeText(safeItem.prompt && safeItem.prompt.prompt_text),
    source_trace: summarizeSourceTrace(safeItem.source_trace),
    source_evidence: summarizeSourceEvidence(safeItem.source_evidence),
    evidence_controls: {
      display_mode: 'review_only',
      direct_evidence_expected: true,
      inference_display_allowed: false,
      source_payload_redistribution_allowed: false,
      validation_performed: false,
      answer_checking_performed: false
    },
    blocked_use: Array.isArray(safeItem.blocked_use)
      ? safeItem.blocked_use.map(safeText)
      : []
  };
}

function buildEvidenceDisplayModel(packageData) {
  const pkg = isPlainObject(packageData) ? packageData : {};
  const items = Array.isArray(pkg.items) ? pkg.items : [];
  return {
    display_version: E4S_READING_V1_EVIDENCE_DISPLAY_VERSION,
    artifact_class: 'review_only_evidence_display',
    package_id: safeText(pkg.package_id),
    package_class: safeText(pkg.package_class),
    review_status: safeText(pkg.review_status || 'not_reviewed'),
    promotion_status: safeText(pkg.promotion_status || 'not_promoted'),
    learner_facing_status: safeText(pkg.learner_facing_status || 'blocked_until_validator_pass'),
    source_manifest_refs: Array.isArray(pkg.source_manifest_refs)
      ? pkg.source_manifest_refs.map((ref) => ({
          source_id: safeText(ref && ref.source_id),
          source_family: safeText(ref && ref.source_family),
          manifest_path: safeText(ref && ref.manifest_path),
          allowed_use_ref: safeText(ref && ref.allowed_use_ref),
          authority_role: safeText(ref && ref.authority_role),
          promotion_rule: safeText(ref && ref.promotion_rule)
        }))
      : [],
    items: items.map(buildEvidenceDisplayModelForItem),
    audit: EVIDENCE_DISPLAY_AUDIT,
    p1_distance_after_this_artifact: {
      current_subtask: 'E4S-P1-S5_ReadingEvidenceDisplay_Implementation',
      subtask_status: 'COMPLETED',
      p1_completed_tasks: 6,
      p1_total_tasks: 9,
      p1_task_count_progress: '67%',
      d_p1: 3,
      remaining_p1_tasks: [
        'E4S-P1-S6_SourceGroundedQuestionGenerator_Implementation',
        'E4S-P1-S7_ReadingV1Validator_Implementation',
        'E4S-P1-S8_ReadingV1ExportTestReadback_QA'
      ]
    },
    next_shortest_step: {
      task_id: 'E4S-P1-S6_SourceGroundedQuestionGenerator_Implementation',
      only_next_allowed_action: 'Create a source-grounded question generator for existing Reading V1 item types and package contract only; do not create validator, learner state, adaptive diagnosis, promotion artifacts, or public learner-facing output.',
      expected_next_artifact_class: 'source_grounded_candidate_generator',
      stop_condition: 'Stop after generator creation; do not create validator, learner state, adaptive diagnosis, promotion artifacts, or public learner-facing output until their explicit P1 tasks are started.'
    }
  };
}

function createElement(documentRef, tagName, className, textContent) {
  const element = documentRef.createElement(tagName);
  if (className) element.className = className;
  if (textContent !== undefined) element.textContent = safeText(textContent);
  return element;
}

function appendKeyValueList(documentRef, root, values) {
  const list = createElement(documentRef, 'dl', 'e4s-evidence-kv');
  values.forEach(([key, value]) => {
    const dt = createElement(documentRef, 'dt', null, key);
    const dd = createElement(documentRef, 'dd', null, Array.isArray(value) ? value.join(', ') : value);
    list.appendChild(dt);
    list.appendChild(dd);
  });
  root.appendChild(list);
  return list;
}

function renderEvidenceDisplay(container, packageData) {
  if (!container || !container.ownerDocument) {
    return {
      status: 'render_skipped',
      reason: 'CONTAINER_MISSING',
      model: buildEvidenceDisplayModel(packageData),
      audit: EVIDENCE_DISPLAY_AUDIT
    };
  }

  const documentRef = container.ownerDocument;
  const model = buildEvidenceDisplayModel(packageData);
  container.textContent = '';

  const root = createElement(documentRef, 'section', 'e4s-evidence-display');
  const title = createElement(documentRef, 'h2', null, 'Reading V1 Evidence Display');
  root.appendChild(title);

  const boundary = createElement(documentRef, 'p', 'e4s-evidence-boundary', 'Review-only display. No source validation, answer checking, generation, learner state, or promotion is performed.');
  root.appendChild(boundary);

  appendKeyValueList(documentRef, root, [
    ['Package ID', model.package_id],
    ['Package class', model.package_class],
    ['Review status', model.review_status],
    ['Promotion status', model.promotion_status],
    ['Learner-facing status', model.learner_facing_status]
  ]);

  model.items.forEach((item, index) => {
    const article = createElement(documentRef, 'article', 'e4s-evidence-item');
    article.appendChild(createElement(documentRef, 'h3', null, `${index + 1}. ${item.item_id}`));
    article.appendChild(createElement(documentRef, 'p', 'e4s-evidence-prompt', item.prompt_text));

    const evidenceTitle = createElement(documentRef, 'h4', null, 'Source Evidence');
    article.appendChild(evidenceTitle);
    appendKeyValueList(documentRef, article, [
      ['Evidence text', item.source_evidence.evidence_text],
      ['Evidence span', item.source_evidence.evidence_span],
      ['Answer span', item.source_evidence.answer_span],
      ['Quote policy', item.source_evidence.source_sentence_quote_policy],
      ['Evidence is direct', String(item.source_evidence.evidence_is_direct)],
      ['Inference required', String(item.source_evidence.inference_required)],
      ['Copyright policy', item.source_evidence.copyright_policy]
    ]);

    const traceTitle = createElement(documentRef, 'h4', null, 'Source Trace');
    article.appendChild(traceTitle);
    appendKeyValueList(documentRef, article, [
      ['Source ID', item.source_trace.source_id],
      ['Source family', item.source_trace.source_family],
      ['Manifest ref', item.source_trace.source_manifest_ref],
      ['Source path/reference', item.source_trace.source_path_or_reference],
      ['Level claim', item.source_trace.source_level_claim],
      ['Level claim status', item.source_trace.source_level_claim_status],
      ['Source unit ID', item.source_trace.source_unit_id],
      ['Source unit type', item.source_trace.source_unit_type],
      ['Source sentence IDs', item.source_trace.source_sentence_ids],
      ['Source page/location', item.source_trace.source_page_or_location]
    ]);

    root.appendChild(article);
  });

  container.appendChild(root);

  return {
    status: 'rendered',
    model,
    audit: EVIDENCE_DISPLAY_AUDIT
  };
}

const E4SReadingV1EvidenceDisplay = Object.freeze({
  version: E4S_READING_V1_EVIDENCE_DISPLAY_VERSION,
  audit: EVIDENCE_DISPLAY_AUDIT,
  summarizeSourceTrace,
  summarizeSourceEvidence,
  buildEvidenceDisplayModelForItem,
  buildEvidenceDisplayModel,
  renderEvidenceDisplay
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = E4SReadingV1EvidenceDisplay;
}

if (typeof window !== 'undefined') {
  window.E4SReadingV1EvidenceDisplay = E4SReadingV1EvidenceDisplay;
}
