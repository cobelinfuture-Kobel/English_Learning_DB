(() => {
  "use strict";
  let payload;
  let startedAt = new Date().toISOString();
  let storageKey = "r7-m105p05-subject-pronouns-loading";
  const form = document.querySelector("#review-form");
  const status = document.querySelector("#status");
  const learnerRef = document.querySelector("#learner-ref");
  const operatorRef = document.querySelector("#operator-ref");
  const sessionId = document.querySelector("#session-id");
  const itemRoot = document.querySelector("#items");
  const downloadButton = document.querySelector("#download");
  const nowIso = () => new Date().toISOString();

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
  }

  function itemHtml(item, index) {
    const context = Object.entries(item.context || {}).map(([key, value]) => `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd>`).join("");
    const options = (item.options || []).map((value, number) => `<li>${number + 1}. ${escapeHtml(value)}</li>`).join("");
    const material = item.material ? `<p class="material"><strong>${escapeHtml(item.material.label)}:</strong> ${item.material.values.map(escapeHtml).join(" | ")}</p>` : "";
    const answer = item.manual_score_required ? `<textarea class="response" rows="3" required></textarea>` : `<input class="response" required autocomplete="off">`;
    const score = item.manual_score_required ? `<fieldset class="operator"><legend>Operator evaluation</legend><label>Score (0–1)<input class="score" type="number" min="0" max="1" step="0.1" required></label><p>Pass threshold: ${item.minimum_score}</p></fieldset>` : "";
    return `<article class="panel item" data-item-id="${escapeHtml(item.item_id)}" data-mode="${item.manual_score_required ? "manual" : "rule"}" data-attempt-sequence="${item.attempt_sequence}" data-threshold="${item.minimum_score}"><span class="badge">${index + 1}/${payload.item_count} · ${escapeHtml(item.skill)} · ${escapeHtml(item.item_role)} · attempt ${item.attempt_sequence}</span><h2>${escapeHtml(item.prompt)}</h2>${context ? `<dl class="context">${context}</dl>` : ""}${options ? `<ol>${options}</ol>` : ""}${material}<label>Your answer${answer}</label>${score}</article>`;
  }

  function items() { return [...document.querySelectorAll(".item")]; }
  function defaultSessionId() { return `review-${payload.grammar_unit_id.toLowerCase()}-${Date.now()}`; }
  function currentState() {
    return {learner_ref: learnerRef.value.trim(), operator_ref: operatorRef.value.trim(), session_id: sessionId.value.trim(), started_at: startedAt, responses: items().map((item) => ({item_id:item.dataset.itemId, response_text:item.querySelector(".response").value, score:item.dataset.mode === "manual" ? item.querySelector(".score").value : null}))};
  }
  function saveState() { if (payload) localStorage.setItem(storageKey, JSON.stringify(currentState())); }
  function restoreState() {
    sessionId.value = defaultSessionId();
    const raw = localStorage.getItem(storageKey); if (!raw) return;
    try { const state = JSON.parse(raw); learnerRef.value = state.learner_ref || payload.learner_ref; operatorRef.value = state.operator_ref || payload.operator_ref; sessionId.value = state.session_id || sessionId.value; startedAt = state.started_at || startedAt; const byId = new Map((state.responses || []).map((entry) => [entry.item_id, entry])); for (const item of items()) { const saved = byId.get(item.dataset.itemId); if (!saved) continue; item.querySelector(".response").value = saved.response_text || ""; const score = item.querySelector(".score"); if (score && saved.score !== null) score.value = saved.score; } } catch { localStorage.removeItem(storageKey); }
  }
  function validate() {
    const errors=[]; if (!learnerRef.value.trim() || learnerRef.value.includes("@")) errors.push("Learner ref 必須是匿名代碼。"); if (!operatorRef.value.trim()) errors.push("Operator ref 不可空白。");
    for (const item of items()) { if (!item.querySelector(".response").value.trim()) errors.push(`${item.dataset.itemId} 尚未作答。`); if (item.dataset.mode === "manual") { const raw=item.querySelector(".score").value; const score=Number(raw); if (raw==="" || Number.isNaN(score) || score<0 || score>1) errors.push(`${item.dataset.itemId} 需要 0–1 score。`); } }
    return errors;
  }
  function normalizedResponse(item) {
    const raw = item.querySelector(".response").value.trim();
    const itemSpec = payload.items.find((entry) => entry.item_id === item.dataset.itemId);
    const options = itemSpec?.options || [];
    if (options.length && /^\d+$/.test(raw)) {
      const selected = Number(raw);
      if (selected >= 1 && selected <= options.length) return String(options[selected - 1]);
    }
    return raw;
  }
  function buildExport() {
    const sourceRef=`browser-export:${sessionId.value.trim()}`;
    return {import_schema_version:"a1_grammar_text_mode_private_pilot_response_import.v1", session:{session_id:sessionId.value.trim(), learner_ref:learnerRef.value.trim(), operator_ref:operatorRef.value.trim(), started_at:startedAt, completed_at:nowIso(), evidence_source_ref:sourceRef}, responses:items().map((item) => { const record={item_id:item.dataset.itemId,response_text:normalizedResponse(item),attempt_sequence:Number(item.dataset.attemptSequence),submitted_at:nowIso(),evidence_ref:`${sourceRef}/item/${item.dataset.itemId}/attempt/${item.dataset.attemptSequence}`}; if (item.dataset.mode === "manual") { const score=Number(item.querySelector(".score").value); const passed=score>=Number(item.dataset.threshold); Object.assign(record,{score,passed,evaluator_type:"MANUAL",evaluator_ref:operatorRef.value.trim(),error_tags:passed?[]:["ERR_UNCLASSIFIED_GRAMMAR_FAILURE"]}); } return record; })};
  }
  function download(data) { const blob=new Blob([`${JSON.stringify(data,null,2)}\n`],{type:"application/json"}); const url=URL.createObjectURL(blob); const link=document.createElement("a"); link.href=url; link.download=`${data.session.session_id}.json`; document.body.append(link); link.click(); link.remove(); URL.revokeObjectURL(url); }

  document.addEventListener("input", saveState);
  downloadButton.addEventListener("click", () => { const errors=validate(); if (errors.length) { status.textContent=errors.join(" "); return; } const data=buildExport(); saveState(); download(data); status.textContent="JSON 已下載；選項編號已轉成實際答案文字。"; });
  document.querySelector("#clear").addEventListener("click", () => { localStorage.removeItem(storageKey); form.reset(); learnerRef.value=payload.learner_ref; operatorRef.value=payload.operator_ref; sessionId.value=defaultSessionId(); startedAt=nowIso(); status.textContent="本機答案已清除。"; });

  fetch("./next-unit.json", {cache:"no-store"}).then((response) => { if (!response.ok) throw new Error("payload unavailable"); return response.json(); }).then((data) => { payload=data; storageKey=`r7-m105p05-${payload.grammar_unit_id}-targeted`; learnerRef.value=payload.learner_ref; operatorRef.value=payload.operator_ref; document.querySelector("#unit-title").textContent=payload.title_en || payload.grammar_unit_id; document.querySelector("#unit-meta").textContent=`${payload.grammar_unit_id} · targeted review · ${payload.item_count} item`; itemRoot.innerHTML=payload.items.map(itemHtml).join(""); restoreState(); downloadButton.disabled=false; status.textContent="P03 targeted review 已載入。可輸入選項編號或完整文字。"; }).catch((error) => { status.textContent=`載入失敗：${error.message}`; });
})();
