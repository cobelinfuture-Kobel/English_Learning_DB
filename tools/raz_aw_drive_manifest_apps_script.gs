/**
 * RAZ A-W Google Drive manifest generator.
 *
 * Run this in Google Apps Script with access to the shared Drive folder.
 * It enumerates files and writes a sanitized manifest JSON file. It must not
 * emit full sentence/page text.
 */

const RAZ_AW_ROOT_FOLDER_ID = '15P1dahD12t9Hsht1cPKIEj8K0oPc6Noz';
const OUTPUT_FILENAME = 'raw_aw_drive_file_manifest.json';
const MAX_PARSE_BYTES = 5 * 1024 * 1024;
const EXPECTED_LEVELS = 'ABCDEFGHIJKLMNOPQRSTUVW'.split('');
const MEDIA_EXTENSIONS = ['.pdf', '.mp3', '.mp4', '.wav', '.m4a', '.jpg', '.jpeg', '.png', '.webp'];
const ARCHIVE_EXTENSIONS = ['.zip', '.7z', '.rar', '.tar', '.gz'];

function generateRazAwDriveFileManifest() {
  const root = DriveApp.getFolderById(RAZ_AW_ROOT_FOLDER_ID);
  const records = [];
  const unexpectedFiles = [];
  const mediaFiles = [];
  const archiveFiles = [];
  const levelsPresent = {};

  walkFolder_(root, [], records, unexpectedFiles, mediaFiles, archiveFiles, levelsPresent);

  const levelList = Object.keys(levelsPresent).sort();
  const missing = EXPECTED_LEVELS.filter(function(level) { return !levelsPresent[level]; });
  const fileCountByLevel = {};
  EXPECTED_LEVELS.forEach(function(level) { fileCountByLevel[level] = 0; });
  records.forEach(function(record) {
    if (record.level && fileCountByLevel.hasOwnProperty(record.level)) {
      fileCountByLevel[record.level] += 1;
    }
  });

  const manifest = {
    task_id: 'RAZ-AW-S1C_RawAWDriveManifestGeneration',
    manifest_type: 'google_drive_sanitized_manifest',
    manifest_status: 'GENERATED',
    sanitized: true,
    contains_raw_text: false,
    raw_mutation: false,
    raw_commit_allowed: false,
    source_surface: 'google_drive_apps_script',
    drive_root: {
      folder_id: RAZ_AW_ROOT_FOLDER_ID,
      folder_title: root.getName(),
      url: root.getUrl()
    },
    levels_requested: EXPECTED_LEVELS,
    levels_present: levelList,
    levels_missing: missing,
    file_count_total: records.length,
    file_count_by_level: fileCountByLevel,
    unexpected_file_count: unexpectedFiles.length,
    media_file_count: mediaFiles.length,
    archive_file_count: archiveFiles.length,
    raw_text_in_manifest: false,
    records: records
  };

  root.createFile(OUTPUT_FILENAME, JSON.stringify(manifest, null, 2), MimeType.PLAIN_TEXT);
  Logger.log('Wrote ' + OUTPUT_FILENAME + ' with ' + records.length + ' records.');
}

function walkFolder_(folder, pathParts, records, unexpectedFiles, mediaFiles, archiveFiles, levelsPresent) {
  const currentParts = pathParts.concat([folder.getName()]);

  const files = folder.getFiles();
  while (files.hasNext()) {
    const file = files.next();
    const name = file.getName();
    const lowerName = name.toLowerCase();
    const ext = extensionOf_(lowerName);
    const level = inferLevel_(currentParts, name);
    if (level) {
      levelsPresent[level] = true;
    }

    const base = {
      level: level,
      folder_title: level ? 'Level_' + level : null,
      filename: name,
      drive_file_id: file.getId(),
      drive_url: file.getUrl(),
      size_bytes: file.getSize(),
      mime_type: file.getMimeType(),
      json_parse_status: 'NOT_JSON',
      raw_text_in_manifest: false
    };

    if (MEDIA_EXTENSIONS.indexOf(ext) >= 0) {
      mediaFiles.push(base);
      continue;
    }
    if (ARCHIVE_EXTENSIONS.indexOf(ext) >= 0) {
      archiveFiles.push(base);
      continue;
    }
    if (ext !== '.json') {
      unexpectedFiles.push(base);
      continue;
    }

    const parsed = shallowParseJson_(file);
    const record = Object.assign({}, base, parsed);
    records.push(dropNulls_(record));
  }

  const folders = folder.getFolders();
  while (folders.hasNext()) {
    walkFolder_(folders.next(), currentParts, records, unexpectedFiles, mediaFiles, archiveFiles, levelsPresent);
  }
}

function shallowParseJson_(file) {
  const size = file.getSize();
  if (size > MAX_PARSE_BYTES) {
    return { json_parse_status: 'SKIPPED_TOO_LARGE' };
  }
  try {
    const obj = JSON.parse(file.getBlob().getDataAsString('UTF-8'));
    if (!obj || typeof obj !== 'object' || Array.isArray(obj)) {
      return { json_parse_status: 'FAIL', json_parse_error: 'top_level_json_is_not_object' };
    }
    const book = isObject_(obj.book_metadata) ? obj.book_metadata : {};
    const clean = isObject_(obj.clean_summary) ? obj.clean_summary : {};
    return dropNulls_({
      json_parse_status: 'PASS',
      source_type: scalar_(obj.source_type),
      extraction_method: scalar_(obj.extraction_method),
      extractor_version: scalar_(obj.extractor_version),
      book_id: scalar_(book.book_id || clean.book_id),
      book_title: scalar_(book.title || clean.title),
      level_from_json: scalar_(book.level || clean.level),
      story_page_start: scalar_(book.story_page_start),
      story_page_end: scalar_(book.story_page_end),
      story_page_count: scalar_(book.story_page_count || clean.actual_story_page_count),
      sentence_candidate_count: arrayCount_(obj.sentence_candidates),
      page_unit_count: arrayCount_(obj.page_units),
      reuse_candidate_count: arrayCount_(obj.reuse_unit_candidates),
      excluded_item_count: arrayCount_(obj.excluded_items),
      legacy_story_sentence_count: arrayCount_(obj.legacy_story_sentences),
      authority_status: scalar_(clean.authority_status),
      generated_content: typeof clean.generated_content === 'boolean' ? clean.generated_content : null
    });
  } catch (err) {
    return { json_parse_status: 'FAIL', json_parse_error: String(err).slice(0, 200) };
  }
}

function inferLevel_(pathParts, filename) {
  for (let i = 0; i < pathParts.length; i++) {
    const match = /^Level_([A-W])$/.exec(pathParts[i]);
    if (match) return match[1];
  }
  const fileMatch = /raz_([A-W])_/.exec(filename);
  return fileMatch ? fileMatch[1] : null;
}

function extensionOf_(name) {
  const index = name.lastIndexOf('.');
  return index >= 0 ? name.slice(index) : '';
}

function arrayCount_(value) {
  return Array.isArray(value) ? value.length : null;
}

function isObject_(value) {
  return value && typeof value === 'object' && !Array.isArray(value);
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
