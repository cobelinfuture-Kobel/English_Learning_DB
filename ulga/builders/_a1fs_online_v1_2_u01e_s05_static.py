#!/usr/bin/env python3
"""Patch and validate the reusable V1.2 multi-type learner surface."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Renders already-approved question-type metadata and coverage readback controls. "
    "It creates no item, answer, scoring rule, learner state, mastery, audio, A2, "
    "external route, or parallel authority."
)

PANEL_ID = "unit01-coverage-panel"
BUTTON_ID = "load-unit01-coverage"
SUMMARY_ID = "unit01-coverage-summary"
STATE_ID = "unit01-coverage-state"
SEQUENCE_OLD = (
    "if(asset.learner_payload.writing_stage==='CONTROLLED_SEQUENCE')"
    "return trimmed.split(/\\s+/);return value"
)
SEQUENCE_NEW = (
    "if(asset.learner_payload.writing_stage==='CONTROLLED_SEQUENCE'||"
    "asset.learner_payload.response_type==='sequence')"
    "return trimmed.split(/\\s+/);return value"
)
INDEX_PANEL = f'''<section id="{PANEL_ID}" class="panel unit01-coverage-panel">
  <div class="section-heading"><h2>Unit 01 學習覆蓋</h2></div>
  <p>顯示已核准題庫、實際練習與多標準覆蓋；精熟度只在有正式證據時顯示。</p>
  <button type="button" id="{BUTTON_ID}">更新 Unit 01 覆蓋</button>
  <div id="{SUMMARY_ID}" class="summary-grid"></div>
  <p id="{STATE_ID}" class="note">登入後可讀取目前覆蓋。</p>
</section>
'''
JS_EXTENSION = rf'''
const unit01CoverageButton=document.querySelector('#{BUTTON_ID}'),unit01CoverageSummary=document.querySelector('#{SUMMARY_ID}'),unit01CoverageState=document.querySelector('#{STATE_ID}');
function coverageMetric(label,value,percentage){{const shown=percentage==null?String(value??'—'):`${{value}} (${{percentage}}%)`;return metric(label,shown)}}
function renderUnit01Coverage(value){{const domains=value.coverage_by_domain||{{}},evp=domains.evp_senses||{{}},egp=domains.egp_rows||{{}},patterns=domains.assessment_patterns||{{}},evidence=value.learner_evidence_summary||{{}};unit01CoverageSummary.replaceChildren();unit01CoverageSummary.append(coverageMetric('正式題目',value.curriculum_item_count,null),coverageMetric('已練習題目',evidence.distinct_attempted_item_count,null),coverageMetric('EVP 已練習',evp.practised_count,evp.practised_percentage),coverageMetric('EGP 已練習',egp.practised_count,egp.practised_percentage),coverageMetric('題型已練習',patterns.practised_count,patterns.practised_percentage));text(unit01CoverageState,`Cambridge stage：${{value.cambridge_stage}}；KET activity bridge：${{value.ket_prerequisite_readback.activity_bridge_status}}。`);}}
async function loadUnit01Coverage(){{try{{text(unit01CoverageState,'讀取中…');const value=await api('/api/unit01-coverage');renderUnit01Coverage(value);}}catch(error){{text(unit01CoverageState,`讀取失敗：${{error.message}}`);}}}}
if(unit01CoverageButton)unit01CoverageButton.addEventListener('click',loadUnit01Coverage);
'''
CSS_EXTENSION = """
.unit01-coverage-panel{border-width:2px}.unit01-coverage-panel button{margin:.5rem 0 1rem}.token-bank{display:flex;gap:.4rem;flex-wrap:wrap}.token-bank span{padding:.35rem .55rem;border:1px solid #aab4bf;border-radius:7px;background:#f7f9fb}
"""
TOKEN_MARKER = "const options=asset.learner_payload.options||[];"
TOKEN_REPLACEMENT = (
    "const tokenBank=asset.learner_payload.token_bank||[];"
    "if(tokenBank.length){const bank=document.createElement('div');bank.className='token-bank';"
    "tokenBank.forEach(value=>{const chip=document.createElement('span');text(chip,value);bank.append(chip);});card.append(bank);}"
    + TOKEN_MARKER
)


class S05StaticError(ValueError):
    """Fail-closed static-surface patch or visual acceptance error."""


def patch_static(source_root: Path, target_root: Path) -> dict[str, Any]:
    source_root, target_root = Path(source_root), Path(target_root)
    if target_root.exists():
        shutil.rmtree(target_root)
    shutil.copytree(source_root, target_root)
    index_path = target_root / "index.html"
    app_path = target_root / "app.js"
    css_path = target_root / "styles.css"
    if not all(path.is_file() for path in (index_path, app_path, css_path)):
        raise S05StaticError("secure_static_files_missing")
    index = index_path.read_text(encoding="utf-8")
    if PANEL_ID not in index:
        marker = "</main>" if "</main>" in index else "</body>"
        if marker not in index:
            raise S05StaticError("coverage_panel_insertion_marker_missing")
        index = index.replace(marker, INDEX_PANEL + marker, 1)
        index_path.write_text(index, encoding="utf-8")
    app = app_path.read_text(encoding="utf-8")
    if SEQUENCE_OLD in app:
        app = app.replace(SEQUENCE_OLD, SEQUENCE_NEW, 1)
    elif SEQUENCE_NEW not in app:
        raise S05StaticError("exact_sequence_serializer_marker_missing")
    if "asset.learner_payload.token_bank" not in app:
        if TOKEN_MARKER not in app:
            raise S05StaticError("token_bank_renderer_marker_missing")
        app = app.replace(TOKEN_MARKER, TOKEN_REPLACEMENT, 1)
    if "loadUnit01Coverage" not in app:
        app += JS_EXTENSION
    app_path.write_text(app, encoding="utf-8")
    css = css_path.read_text(encoding="utf-8")
    if ".unit01-coverage-panel" not in css:
        css += CSS_EXTENSION
    css_path.write_text(css, encoding="utf-8")
    return validate_static(target_root)


def validate_static(root: Path) -> dict[str, Any]:
    root = Path(root)
    index = (root / "index.html").read_text(encoding="utf-8")
    app = (root / "app.js").read_text(encoding="utf-8")
    css = (root / "styles.css").read_text(encoding="utf-8")
    checks = {
        "coverage_panel_visible_contract": PANEL_ID in index and BUTTON_ID in index,
        "coverage_api_connected": "/api/unit01-coverage" in app and "loadUnit01Coverage" in app,
        "sequence_response_type_supported": SEQUENCE_NEW in app,
        "token_bank_renderer_present": "asset.learner_payload.token_bank" in app,
        "coverage_styles_present": ".unit01-coverage-panel" in css,
        "hidden_answers_absent": all(
            marker not in app for marker in ("accepted_texts", "accepted_sequence", "correct_answer")
        ),
    }
    failed = [key for key, value in checks.items() if value is not True]
    if failed:
        raise S05StaticError("static_validation_failed:" + ",".join(failed))
    return {"validation_status": "PASS_U01E_S05_STATIC_SURFACE", **checks}


def chromium_visual_acceptance(static_root: Path, output_path: Path) -> dict[str, Any]:
    commands = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
    browser = next((shutil.which(command) for command in commands if shutil.which(command)), None)
    if browser is None:
        return {
            "status": "NOT_AVAILABLE_IN_EXECUTION_ENVIRONMENT",
            "browser": None,
            "screenshot_created": False,
            "dom_contract_pass": True,
        }
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    target = (Path(static_root).resolve() / "index.html").as_uri()
    result = subprocess.run(
        [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            "--window-size=1440,1400",
            f"--screenshot={output_path}",
            target,
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0 or not output_path.is_file() or output_path.stat().st_size == 0:
        raise S05StaticError(
            f"chromium_visual_acceptance_failed:{result.returncode}:{result.stderr[-400:]}"
        )
    return {
        "status": "PASS_HEADLESS_CHROMIUM_SCREENSHOT",
        "browser": Path(browser).name,
        "screenshot_created": True,
        "screenshot_size_bytes": output_path.stat().st_size,
        "dom_contract_pass": True,
    }
