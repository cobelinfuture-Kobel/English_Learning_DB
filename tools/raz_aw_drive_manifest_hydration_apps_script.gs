/**
 * RAZ A-W Drive manifest hydration QA.
 *
 * This script runs inside Google Apps Script with Drive access. It consumes the
 * Drive-side manifest.json file-id map and shallow-parses selected raw JSON files
 * by file ID. It emits sanitized report JSON only and must not emit sentence,
 * page, audio trace, or other raw text payloads.
 */

const RAZ_AW_MANIFEST_FILE_ID = '1gNIiNgh8uyohMVhFl1wqJEPJpqrLkYkY';
const OUTPUT_FOLDER_ID = '15P1dahD12t9Hsht1cPKIEj8K0oPc6Noz';
const RAW_PATH_RE = /^raz_output_jsons\/Level_([A-W])\/raz_([A-W])_([0-9]+)_audio_timeline_extract\.json$/;
const EXPECTED_LEVELS = 'ABCDEFGHIJKLMNOPQRSTUVW'.split('');
const MAX_PARSE_BYTES = 10 * 1024 * 1024;

/**
 * Run a small deterministic sample: first/middle/last raw JSON per level.
 */
function hydrateRazAwManifestSample() {
  return hydrateRazAwManifest_({ mode: 'sample', samplePerLevel: 3 });
}

/**
 * Run one level only, for example hydrateRazAwManifestLevel('A').
 */
function hydrateRazAwManifestLevel(level) {
  return hydrateRazAwManifest_({ mode: 'level', level: String(level || '').toUpperCase() });
}

/**
 * Run the full A-W raw-level JSON shallow hydration. This may take time.
 */
function hydrateRazAwManifestFull() {
  return hydrateRazAwManifest_({ mode: 'full' });
}

function hydrateRazAwManifest_(options) {
  const manifestFile = DriveApp.getFileById(RAZ_AW_MANIFEST_FILE_ID);
  const manifest = JSON.parse(manifestFile.getBlob().getDataAsString('UTF-8'));
  if (!manifest.files || typeof manifest.files !== 'object') {
    throw new Error('Manifest missing files mapping.');
  }

  const rawRecords = Object.keys(manifest.files)
    .map(function(relativePath) {
      const match = RAW_PATH_RE.exec(relativePath);
      if (!match) return null;
      const levelFromFolder = match[1];
      const levelFromFilename = match[2];
      const bookId = match[3];
      return {
        relative_path: relativePath,
        drive_file_id: String(manifest.files[relativePath]),
        level: levelFromFolder,
        level_from_filename: levelFromFilename,
        book_id_from_filename: bookId,
        filename_pattern_status: levelFromFolder === levelFromFilename ? 'PASS' : 'FAIL'
      };
    })
    .filter(function(record) { return record !== null; })
    .sort(function(a, b) {
      if (a.level !== b.level) return a.level < b.level ? -1 : 1;
      return Number(a.book_id_from_filename) - Number(b.book_id_from_filename);
    });

  const selected = selectRecords_(rawRecords, options || {});
  const hydrated = selected.map(function(record) { return hydrateOneRecord_(record); });
  const parseCounts = {};
  hydrated.forEach(function(record) {
    const key = record.json_parse_status || 'UNKNOWN';
    parseCounts[key] = (parseCounts[key] || 0) + 1;
  });

  const report = {
    task_id: 'RAZ-AW-S2C_DriveManifestHydrationTooling',
    report_type: 'drive_manifest_hydration_result',
    status: hydrated.some(function(record) { return record.fetch_status !== 'PASS'; }) ? 'PASS_WITH_WARNINGS' : 'PASS',
    sanitized: true,
    contains_raw_text: false,
    raw_mutation: false,
    raw_commit_allowed: false,
    authority_promotion: false,
    tag_registry_promotion: false,
    source_surface: 'google_apps_script_drive_file_id_hydration',
    mode: options.mode,
    manifest_file_id: RAZ_AW_MANIFEST_FILE_ID,
    raw_manifest_record_count: rawRecords.length,
    selected_record_count: selected.length,
    fetch_success_count: hydrated.filter(function(record) { return record.fetch_status === 'PASS'; }).length,
    json_parse_status_counts: parseCounts,
    records: hydrated,
    safety_notes: [
      'Only shallow schema metadata and counts are emitted.',
      'No sentence/page/audio trace/raw text fields are emitted.',
      'Raw JSON files remain external to GitHub and are not committed.'
    ]
  };

  const outputName = makeOutputName_(options);
  DriveApp.getFolderById(OUTPUT_FOLDER_ID).createFile(outputName, JSON.stringify(report, null, 2), MimeType.PLAIN_TEXT);
  Logger.log('Wrote ' + outputName + ' with ' + hydrated.length + ' records.');
  return report;
}

function selectRecords_(records, options) {
  if (options.mode === 'full') {
    return records;
  }
  if (options.mode === 'level') {
    const level = options.level;
    if (EXPECTED_LEVELS.indexOf(level) < 0) throw new Error('Invalid level: ' + level);
    return records.filter(function(record) { return record.level === level; });
  }
  const samplePerLevel = Number(options.samplePerLevel || 3);
  const out = [];
  EXPECTED_LEVELS.forEach(function(level) {
    const levelRecords = records.filter(function(record) { return record.level === level; });
    if (!levelRecords.length) return;
    const indexes = samplePerLevel <= 1
      ? [0]
      : samplePerLevel === 2
        ? [0, levelRecords.length - 1]
        : unique_([0, Math.floor(levelRecords.length / 2), levelRecords.length - 1]);
    indexes.forEach(function(index) { out.push(levelRecords[index]); });
  });
  return out;
}

function hydrateOneRecord_(record) {
  const out = Object.assign({}, record, {
    fetch_status: 'NOT_RUN',
    json_parse_status: 'NOT_RUN',
    raw_text_in_report: false
  });
  try {
    const file = DriveApp.getFileById(record.drive_file_id);
    out.title = file.getName();
    out.size_bytes = file.getSize();
    out.mime_type = file.getMimeType();
    out.fetch_status = 'PASS';
    if (file.getSize() > MAX_PARSE_BYTES) {
      out.json_parse_status = 'SKIPPED_TOO_LARGE';
      return out;
    }
    const obj = JSON.parse(file.getBlob().getDataAsString('UTF-8'));
    if (!obj || typeof obj !== 'object' || Array.isArray(obj)) {
      out.json_parse_status = 'FAIL';
      out.json_parse_error = 'top_level_json_is_not_object';
      return out;
    }
    const book = isObject_(obj.book_metadata) ? obj.book_metadata : {};
    const clean = isObject_(obj.clean_summary) ? obj.clean_summary : {};
    out.json_parse_status = 'PASS';
    out.source_type = scalar_(obj.source_type);
    out.extraction_method = scalar_(obj.extraction_method);
    out.extractor_version = scalar_(obj.extractor_version);
    out.level_from_json = scalar_(book.level || clean.level);
    out.book_id = scalar_(book.book_id || clean.book_id);
    out.book_title = scalar_(book.title || clean.title);
    out.story_page_start = scalar_(book.story_page_start);
    out.story_page_end = scalar_(book.story_page_end);
    out.story_page_count = scalar_(book.story_page_count || clean.actual_story_page_count);
    out.sentence_candidate_count = arrayCount_(obj.sentence_candidates);
    out.page_unit_count = arrayCount_(obj.page_units);
    out.reuse_candidate_count = arrayCount_(obj.reuse_unit_candidates);
    out.excluded_item_count = arrayCount_(obj.excluded_items);
    out.legacy_story_sentence_count = arrayCount_(obj.legacy_story_sentences);
    out.authority_status = scalar_(clean.authority_status);
    out.generated_content = typeof clean.generated_content === 'boolean' ? clean.generated_content : null;
    return dropNulls_(out);
  } catch (err) {
    out.fetch_status = out.fetch_status === 'PASS' ? 'PASS' : 'FAIL';
    out.json_parse_status = out.fetch_status === 'PASS' ? 'FAIL' : 'NOT_RUN';
    out.error = String(err).slice(0, 200);
    return out;
  }
}

function makeOutputName_(options) {
  const timestamp = Utilities.formatDate(new Date(), 'UTC', 'yyyyMMdd_HHmmss');
  if (options.mode === 'full') return 'drive_manifest_hydration_full_' + timestamp + '.json';
  if (options.mode === 'level') return 'drive_manifest_hydration_level_' + options.level + '_' + timestamp + '.json';
  return 'drive_manifest_hydration_sample_' + timestamp + '.json';
}

function unique_(values) {
  const seen = {};
  const out = [];
  values.forEach(function(value) {
    if (!seen[value]) {
      seen[value] = true;
      out.push(value);
    }
  });
  return out;
}

function isObject_(value) {
  return value && typeof value === 'object' && !Array.isArray(value);
}

function arrayCount_(value) {
  return Array.isArray(value) ? value.length : null;
}

function scalar_(value) {
  if (value === null || value === undefined) return null;
  if (['string', 'number', 'boolean'].indexOf(typeof value) >= 0) return String(value);
  return null;
}

function dropNulls_(obj) {
  const out = {};
  Object.keys(obj).forEach(function(key) {
    if (obj[key] !== null && obj[key] !== undefined) out[key] = obj[key];
  });
  return out;
}
