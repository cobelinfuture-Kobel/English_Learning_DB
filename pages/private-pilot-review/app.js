(() => {
  "use strict";

  const STORAGE_KEY = "r7-m105r1-regular-plurals-review-v1";
  const form = document.querySelector("#review-form");
  const status = document.querySelector("#status");
  const learnerRef = document.querySelector("#learner-ref");
  const operatorRef = document.querySelector("#operator-ref");
  const sessionId = document.querySelector("#session-id");
  const items = [...document.querySelectorAll(".item")];

  const nowIso = () => new Date().toISOString();
  const defaultSessionId = () => `review-regular-plurals-${Date.now()}`;

  function currentState() {
    return {
      learner_ref: learnerRef.value.trim(),
      operator_ref: operatorRef.value.trim(),
      session_id: sessionId.value.trim(),
      responses: items.map((item) => ({
        item_id: item.dataset.itemId,
        response_text: item.querySelector(".response").value,
        score: item.dataset.mode === "manual" ? item.querySelector(".score").value : null,
      })),
    };
  }

  function saveState() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(currentState()));
  }

  function restoreState() {
    sessionId.value = defaultSessionId();
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    try {
      const state = JSON.parse(raw);
      learnerRef.value = state.learner_ref || learnerRef.value;
      operatorRef.value = state.operator_ref || operatorRef.value;
      sessionId.value = state.session_id || sessionId.value;
      const byId = new Map((state.responses || []).map((entry) => [entry.item_id, entry]));
      for (const item of items) {
        const saved = byId.get(item.dataset.itemId);
        if (!saved) continue;
        item.querySelector(".response").value = saved.response_text || "";
        const score = item.querySelector(".score");
        if (score && saved.score !== null && saved.score !== undefined) score.value = saved.score;
      }
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
  }

  function validate() {
    const errors = [];
    if (!learnerRef.value.trim() || learnerRef.value.includes("@")) errors.push("Learner ref 必須是非 email 的匿名代碼。");
    if (!operatorRef.value.trim()) errors.push("Operator ref 不可空白。");
    if (!sessionId.value.trim()) errors.push("Session ID 不可空白。");
    for (const item of items) {
      const answer = item.querySelector(".response").value.trim();
      if (!answer) errors.push(`${item.dataset.itemId} 尚未作答。`);
      if (item.dataset.mode === "manual") {
        const raw = item.querySelector(".score").value;
        const score = Number(raw);
        if (raw === "" || Number.isNaN(score) || score < 0 || score > 1) errors.push(`${item.dataset.itemId} 需要 0–1 operator score。`);
      }
    }
    return errors;
  }

  function buildExport() {
    const startedAt = nowIso();
    const sourceRef = `browser-export:${sessionId.value.trim()}`;
    const responses = items.map((item) => {
      const record = {
        item_id: item.dataset.itemId,
        response_text: item.querySelector(".response").value.trim(),
        attempt_sequence: 2,
        submitted_at: nowIso(),
        evidence_ref: `${sourceRef}/item/${item.dataset.itemId}/attempt/2`,
      };
      if (item.dataset.mode === "manual") {
        const score = Number(item.querySelector(".score").value);
        const passed = score >= 0.8;
        record.score = score;
        record.passed = passed;
        record.evaluator_type = "MANUAL";
        record.evaluator_ref = operatorRef.value.trim();
        record.error_tags = passed ? [] : ["ERR_UNCLASSIFIED_GRAMMAR_FAILURE"];
      }
      return record;
    });
    return {
      import_schema_version: "a1_grammar_text_mode_private_pilot_response_import.v1",
      session: {
        session_id: sessionId.value.trim(),
        learner_ref: learnerRef.value.trim(),
        operator_ref: operatorRef.value.trim(),
        started_at: startedAt,
        completed_at: nowIso(),
        evidence_source_ref: sourceRef,
      },
      responses,
    };
  }

  function download(payload) {
    const blob = new Blob([`${JSON.stringify(payload, null, 2)}\n`], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${payload.session.session_id}.json`;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  document.addEventListener("input", saveState);
  document.querySelector("#download").addEventListener("click", () => {
    const errors = validate();
    if (errors.length) {
      status.textContent = errors.join(" ");
      status.focus?.();
      return;
    }
    const payload = buildExport();
    saveState();
    download(payload);
    status.textContent = "JSON 已下載。答案仍只保存在此瀏覽器，未送往 GitHub。";
  });

  document.querySelector("#clear").addEventListener("click", () => {
    localStorage.removeItem(STORAGE_KEY);
    form.reset();
    learnerRef.value = "learner-local-01";
    operatorRef.value = "operator-local-01";
    sessionId.value = defaultSessionId();
    status.textContent = "本機答案已清除。";
  });

  restoreState();
})();
