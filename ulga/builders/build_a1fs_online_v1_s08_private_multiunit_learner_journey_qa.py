#!/usr/bin/env python3
"""S08 learner-surface contract adapter over the frozen S08 journey core.

The core remains the sole S08 materialization/runtime implementation.  This
adapter corrects the learner-visible S08 bootstrap identity and navigation
state without creating a parallel state, scoring, curriculum, or content
engine.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ulga.builders import _a1fs_online_v1_s08_private_multiunit_learner_journey_qa_core as _core

# Re-export the frozen implementation surface for existing imports, validators,
# the artifact authority runner, and the established CLI contract.
for _name, _value in vars(_core).items():
    if not _name.startswith("__"):
        globals()[_name] = _value

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Adapts the existing S08 learner surface to expose the correct S08 runtime identity, "
    "lock navigation while a session is active or awaiting resume, and render selected "
    "Unit/Skill state. It authors no curriculum, learner content, answers, mastery, audio, "
    "public delivery, database schema, state engine, or scoring engine."
)


class JourneyWorkbenchApplication(_core.JourneyWorkbenchApplication):
    """S08 identity and learner-journey controls over the S07 runtime source."""

    def bootstrap(self) -> dict[str, Any]:
        value = super().bootstrap()
        value.update({
            "task_id": TASK_ID,
            "validation_status": PASS_STATUS,
            "product_status": PRODUCT_STATUS,
            "release_profile": RELEASE_PROFILE,
            "source_runtime": {
                "task_id": _core.s07.TASK_ID,
                "validation_status": _core.s07.PASS_STATUS,
                "product_status": _core.s07.PRODUCT_STATUS,
            },
            "journey_controls": {
                "active_session_readback": True,
                "resume_after_restart": True,
                "abandon_active_session": True,
                "navigation_locked_while_active": True,
            },
        })
        return value


def _write_static(static_root: Path) -> None:
    """Write the S08 learner surface with deterministic navigation state."""
    static_root = Path(static_root)
    static_root.mkdir(parents=True, exist_ok=True)

    index = """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'">
  <title>A1FS Learner Journey Workbench</title>
  <link rel="stylesheet" href="/styles.css">
</head>
<body>
  <main>
    <h1>A1FS 多單元學習旅程工作台</h1>
    <p id="status" aria-live="polite">載入中</p>
    <section id="active-panel" hidden>
      <h2>目前進行中的技能</h2>
      <p id="active-label"></p>
      <button id="resume">繼續</button>
      <button id="abandon">放棄目前技能</button>
    </section>
    <nav id="units" aria-label="學習單元"></nav>
    <nav id="lanes" aria-label="技能"></nav>
    <section id="items"></section>
    <button id="complete" hidden>完成目前技能</button>
    <section class="progress">
      <h2>學習進度</h2>
      <button id="refresh-progress">更新進度</button>
      <pre id="progress" aria-live="polite"></pre>
    </section>
  </main>
  <script src="/app.js"></script>
</body>
</html>"""

    css = """body{font-family:system-ui,sans-serif;margin:0;background:#f4f4f4;color:#181818}
main{max-width:980px;margin:auto;padding:24px}
button,input,textarea{font:inherit}
.unit,.lane,.submit,#complete,#refresh-progress,#resume,#abandon{margin:4px;padding:10px 14px}
.selected{font-weight:700;border-width:2px}
.card,.progress,#active-panel{background:white;padding:16px;margin:12px 0;border-radius:8px}
.options{display:grid;gap:8px}
textarea{width:100%;min-height:90px}
pre{white-space:pre-wrap;overflow-wrap:anywhere}
.result{font-weight:700}
button:disabled{opacity:.55;cursor:not-allowed}
#abandon{border-color:#9a2b2b}
"""

    js = r"""'use strict';
let state = null;
let currentUnit = null;
let currentLane = null;
let active = null;
let pendingResume = null;

const status = document.querySelector('#status');
const units = document.querySelector('#units');
const lanes = document.querySelector('#lanes');
const items = document.querySelector('#items');
const complete = document.querySelector('#complete');
const progress = document.querySelector('#progress');
const refresh = document.querySelector('#refresh-progress');
const activePanel = document.querySelector('#active-panel');
const activeLabel = document.querySelector('#active-label');
const resume = document.querySelector('#resume');
const abandon = document.querySelector('#abandon');

const text = (node, value) => { node.textContent = value ?? ''; };
const navigationLocked = () => Boolean(active || pendingResume);

async function api(path, body) {
  const hasBody = body !== undefined;
  const response = await fetch(path, {
    method: hasBody ? 'POST' : 'GET',
    headers: hasBody ? {'Content-Type': 'application/json'} : {},
    body: hasBody ? JSON.stringify(body) : undefined,
  });
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || 'request_failed');
  return value;
}

async function loadProgress() {
  text(progress, JSON.stringify(await api('/api/progress'), null, 2));
}

function findLane(lessonId) {
  for (const unit of state.units) {
    for (const lane of unit.lanes) {
      if (lane.lesson_id === lessonId) return {unit, lane};
    }
  }
  return null;
}

function updateActivePanel() {
  activePanel.hidden = !pendingResume;
  text(
    activeLabel,
    pendingResume
      ? pendingResume.grammar_unit_id + ' / ' + pendingResume.session.skill
      : '',
  );
}

function renderUnits() {
  units.replaceChildren();
  for (const unit of state.units) {
    const button = document.createElement('button');
    button.className = 'unit';
    button.classList.toggle(
      'selected',
      Boolean(currentUnit && currentUnit.grammar_unit_id === unit.grammar_unit_id),
    );
    button.disabled = navigationLocked();
    text(button, unit.grammar_unit_id);
    button.addEventListener('click', () => {
      try { chooseUnit(unit); } catch (error) { text(status, error.message); }
    });
    units.append(button);
  }
}

function renderLanes() {
  lanes.replaceChildren();
  if (!currentUnit) return;
  for (const lane of currentUnit.lanes) {
    const button = document.createElement('button');
    button.className = 'lane';
    button.classList.toggle(
      'selected',
      Boolean(currentLane && currentLane.lesson_id === lane.lesson_id),
    );
    button.disabled = navigationLocked();
    text(button, lane.skill);
    button.addEventListener('click', () => {
      begin(lane).catch(error => text(status, error.message));
    });
    lanes.append(button);
  }
}

function chooseUnit(unit) {
  if (navigationLocked()) throw new Error('請先繼續或放棄目前技能');
  currentUnit = unit;
  currentLane = null;
  items.replaceChildren();
  renderUnits();
  renderLanes();
}

function responseFor(card, asset) {
  const options = asset.learner_payload.options || [];
  if (options.length) {
    const checked = card.querySelector('input[type=radio]:checked');
    if (!checked) throw new Error('請先選擇答案');
    return checked.value;
  }
  const area = card.querySelector('textarea');
  if (!area || !area.value.trim()) throw new Error('請先輸入答案');
  return area.value;
}

async function expose(asset) {
  const result = await api('/api/exposure', {
    session_id: active.session_id,
    asset_key: asset.asset_key,
    expected_session_version: active.session_version,
  });
  active.session_version = result.session_version;
  return result;
}

function renderLane(lane) {
  currentLane = lane;
  renderUnits();
  renderLanes();
  items.replaceChildren();
  for (const asset of lane.assets) {
    const card = document.createElement('article');
    card.className = 'card';
    const prompt = document.createElement('p');
    text(prompt, asset.learner_payload.prompt);
    card.append(prompt);

    const options = asset.learner_payload.options || [];
    if (options.length) {
      const box = document.createElement('div');
      box.className = 'options';
      for (const option of options) {
        const label = document.createElement('label');
        const input = document.createElement('input');
        input.type = 'radio';
        input.name = asset.asset_key;
        input.value = option;
        label.append(input, document.createTextNode(' ' + option));
        box.append(label);
      }
      card.append(box);
    } else if (asset.learner_payload.response_capture_enabled) {
      const area = document.createElement('textarea');
      area.setAttribute('aria-label', '回答');
      card.append(area);
    }

    const button = document.createElement('button');
    const result = document.createElement('p');
    button.className = 'submit';
    result.className = 'result';

    if (asset.learner_payload.response_capture_enabled) {
      text(button, '送出回答');
      button.addEventListener('click', async () => {
        try {
          button.disabled = true;
          await expose(asset);
          const scored = await api('/api/response', {
            session_id: active.session_id,
            asset_key: asset.asset_key,
            response: responseFor(card, asset),
            expected_session_version: active.session_version,
          });
          active.session_version = scored.session_version;
          text(result, scored.outcome);
          await loadProgress();
        } catch (error) {
          text(status, error.message);
        } finally {
          button.disabled = false;
        }
      });
    } else {
      text(button, '標記已練習');
      button.addEventListener('click', async () => {
        try {
          button.disabled = true;
          await expose(asset);
          text(result, 'RECORDED');
          await loadProgress();
        } catch (error) {
          text(status, error.message);
        } finally {
          button.disabled = false;
        }
      });
    }
    card.append(button, result);
    items.append(card);
  }
}

async function begin(lane) {
  if (navigationLocked()) throw new Error('請先繼續或放棄目前技能');
  active = await api('/api/session/start', {lesson_id: lane.lesson_id});
  pendingResume = null;
  updateActivePanel();
  complete.hidden = false;
  renderLane(lane);
  text(status, lane.lesson_id + ' started');
}

function restore(snapshot) {
  const match = findLane(snapshot.session.lesson_id);
  if (!match) throw new Error('active_session_bundle_missing');
  pendingResume = null;
  active = snapshot.session;
  currentUnit = match.unit;
  currentLane = match.lane;
  updateActivePanel();
  complete.hidden = false;
  renderLane(match.lane);
  text(status, match.lane.lesson_id + ' resumed');
}

async function finish(path) {
  if (!active) return;
  const done = await api(path, {
    session_id: active.session_id,
    expected_session_version: active.session_version,
  });
  text(status, done.session_state);
  active = null;
  pendingResume = null;
  currentLane = null;
  updateActivePanel();
  complete.hidden = true;
  items.replaceChildren();
  renderUnits();
  renderLanes();
  await loadProgress();
}

complete.addEventListener('click', () => {
  finish('/api/session/complete').catch(error => text(status, error.message));
});

abandon.addEventListener('click', async () => {
  try {
    if (!pendingResume && !active) return;
    if (!active) active = pendingResume.session;
    await finish('/api/session/abandon');
  } catch (error) {
    text(status, error.message);
  }
});

resume.addEventListener('click', () => {
  try { if (pendingResume) restore(pendingResume); }
  catch (error) { text(status, error.message); }
});

refresh.addEventListener('click', () => {
  loadProgress().catch(error => text(status, error.message));
});

async function start() {
  state = await api('/api/bootstrap');
  text(status, state.product_status);
  const snapshot = await api('/api/session/active');
  if (snapshot.active) {
    pendingResume = snapshot;
    const match = findLane(snapshot.session.lesson_id);
    if (!match) throw new Error('active_session_bundle_missing');
    currentUnit = match.unit;
    currentLane = match.lane;
    updateActivePanel();
    renderUnits();
    renderLanes();
  } else if (state.units.length) {
    chooseUnit(state.units[0]);
  } else {
    renderUnits();
    renderLanes();
  }
  await loadProgress();
}

start().catch(error => text(status, error.message));
"""

    (static_root / "index.html").write_text(index + "\n", encoding="utf-8")
    (static_root / "styles.css").write_text(css, encoding="utf-8")
    (static_root / "app.js").write_text(js, encoding="utf-8")


# Patch the frozen core's global lookup targets so all existing materialize,
# serve, validator, and CLI call paths use this single corrected surface.
_core.JourneyWorkbenchApplication = JourneyWorkbenchApplication
_core._write_static = _write_static


def main() -> int:
    return _core.main()


if __name__ == "__main__":
    raise SystemExit(main())
