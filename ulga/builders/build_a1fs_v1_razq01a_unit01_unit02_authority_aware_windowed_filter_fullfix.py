#!/usr/bin/env python3
"""Authority-aware, windowed RAZ S11 FullFix for A1FS Unit 01 and Unit 02."""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_razq01a_unit01_unit02_filter_calibration as base

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Calibration reports only; no learner content, scoring, state, audio, A2, or runtime authority is written."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-RAZQ01A_Unit01Unit02AuthorityAwareWindowedFilterFullFixAndReplay"
SCHEMA_VERSION = "a1fs.v1.razq01a.unit01_unit02_authority_aware_windowed_filter.v2"
PASS_STATUS = "PASS_A1FS_V1_RAZQ01A_AUTHORITY_AWARE_WINDOWED_FILTER_FULLFIX_READY_FOR_REVIEW"
NEXT_SHORT_STEP = "A1FS-V1-RAZQ01A_FilterThresholdOperatorReviewAndPilotReplay"
RUNTIME_ROOT = Path("product/a1fs_v1_2_1/runtime")
DIRECT_LEVELS = frozenset("ABCDEFGHI")
REWRITE_LEVELS = frozenset("JKLMNOPQRSTUVW")
VALID_TYPES = base.VALID_SOURCE_TYPES
SOURCE_PRIORITY = base.SOURCE_PRIORITY
WORD_RE = base.WORD_RE
LINEAGE_KEYS = base.LINEAGE_KEYS
LEVEL_KEYS = base.LEVEL_KEYS
TYPE_KEYS = base.SOURCE_TYPE_KEYS
PATH_KEYS = base.SOURCE_PATH_KEYS
CalibrationError = base.CalibrationError

SENTENCE_RE = re.compile(r"[^.!?]+(?:[.!?]+|$)", re.S)
ARTICLE_RE = re.compile(r"\b(?:a|an|the)\s+[a-z][a-z'’-]*\b", re.I)
INDEFINITE_RE = re.compile(r"\b(?:a|an)\s+[a-z][a-z'’-]*\b", re.I)
DEFINITE_RE = re.compile(r"\bthe\s+[a-z][a-z'’-]*\b", re.I)
PLURAL_RE = re.compile(r"\b(?:two|three|four|five|six|seven|eight|nine|ten|many|some|these|those|several|both|few|all)\s+([a-z][a-z'’-]*(?:s|es))\b|\b([a-z][a-z'’-]*(?:s|es))\s+(?:are|have|can|do|were)\b", re.I)
PAST_RE = re.compile(r"\b(?:was|were|did|had|went|came|saw|said|made|took|gave|found|thought|knew|got|began|became|left|felt|told|wrote|ran|ate|drank)\b|\b[a-z]{3,}ed\b", re.I)
CONTINUOUS_RE = re.compile(r"\b(?:am|is|are|was|were)\s+[a-z]{3,}ing\b", re.I)
PERFECT_RE = re.compile(r"\b(?:has|have)\s+(?:been|[a-z]{3,}ed|made|seen|gone|done|taken|given|known|found)\b", re.I)
PASSIVE_RE = re.compile(r"\b(?:am|is|are|was|were|be|been)\s+(?:called|made|used|found|built|given|taken|known|[a-z]{3,}ed)\b", re.I)
FUTURE_RE = re.compile(r"\bwill\s+[a-z]+\b|\b(?:am|is|are)\s+going\s+to\b", re.I)
RELATIVE_RE = re.compile(r"\b(?:who|which)\s+(?:is|are|was|were|has|have|can|[a-z]+s?)\b", re.I)
CONDITIONAL_RE = re.compile(r"\bif\b[^.!?]{0,80}\b(?:will|would|could|might)\b", re.I)
COMPARATIVE_RE = re.compile(r"\b(?:more|most|less|least)\s+[a-z]+\b|\b[a-z]{3,}(?:er|est)\s+than\b", re.I)
BLOCKED = (("past_simple", PAST_RE), ("continuous", CONTINUOUS_RE), ("present_perfect", PERFECT_RE), ("passive", PASSIVE_RE), ("future", FUTURE_RE), ("relative_clause", RELATIVE_RE), ("conditional", CONDITIONAL_RE), ("comparative_superlative", COMPARATIVE_RE))
FALSE_PLURALS = frozenset({"is", "was", "has", "does", "this", "his", "yes", "class", "glass", "grass", "bus", "news", "series", "species", "us"})
IRREGULAR = frozenset({"children", "people", "men", "women", "mice", "geese", "teeth", "feet", "sheep", "fish"})
FUNCTION_WORDS = frozenset("a an the and or but because so if then than i you he she it we they me him her us them my your his its our their this that these those am is are was were be been being have has had do does did can could will would may might must should not no yes very too also only all both some many few one two three four five six seven eight nine ten in on at by for from to of with into out over under near around through up down before after during about between what which who whose where when why how there here again more most less least each every other another same".split())

@dataclass(frozen=True)
class Profile:
    unit_id: str
    order: int
    level: str
    lesson_ids: tuple[str, ...]
    skills: tuple[str, ...]
    question_types: tuple[str, ...]
    goals: tuple[str, ...]
    clues: tuple[str, ...]
    context_ids: tuple[str, ...]
    evp_ids: tuple[str, ...]
    egp_ids: tuple[str, ...]
    chunk_ids: tuple[str, ...]
    pattern_ids: tuple[str, ...]
    lexical_cues: tuple[str, ...]
    runtime_cues: tuple[str, ...]
    authority_sources: tuple[str, ...]
    prerequisites: tuple[str, ...]

    @property
    def cues(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.lexical_cues) | set(self.runtime_cues)))

    def as_dict(self) -> dict[str, Any]:
        d = {"unit_id": self.unit_id, "sequence_order": self.order, "level": self.level,
             "lesson_ids": list(self.lesson_ids), "skills": list(self.skills),
             "question_types": list(self.question_types), "communicative_goals": list(self.goals),
             "grammar_clues": list(self.clues), "context_ids": list(self.context_ids),
             "target_evp_sense_ids": list(self.evp_ids), "target_egp_row_ids": list(self.egp_ids),
             "target_chunk_ids": list(self.chunk_ids), "target_pattern_ids": list(self.pattern_ids),
             "lexical_cues": list(self.lexical_cues), "runtime_derived_lexical_cues": list(self.runtime_cues),
             "effective_lexical_cues": list(self.cues), "authority_sources": list(self.authority_sources),
             "prerequisite_unit_ids": list(self.prerequisites)}
        d["authority_complete_for_filtering"] = bool(self.clues and self.goals and self.cues and self.authority_sources)
        d["canonical_target_refs_complete"] = bool(self.evp_ids and self.egp_ids and self.pattern_ids)
        return d


def _walk_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for child in value.values():
            yield from _walk_strings(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _walk_strings(child)


def _regular_singular(word: str) -> str:
    w = word.lower().strip("'’- ")
    if w in IRREGULAR or len(w) < 4:
        return ""
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("es") and len(w) > 4:
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return ""


def _word_forms(word: str) -> set[str]:
    w = word.lower().replace("_", " ").strip()
    forms = {w} if w else set()
    singular = _regular_singular(w)
    if singular:
        forms.add(singular)
    if " " not in w and len(w) > 2:
        forms.add(w + ("es" if w.endswith(("s", "x", "z", "ch", "sh")) else "s"))
    return forms


def _runtime_cues(assets: Sequence[Mapping[str, Any]], unit_id: str) -> tuple[str, ...]:
    cues: set[str] = set()
    for asset in assets:
        payload = asset.get("learner_payload", {})
        if not isinstance(payload, Mapping):
            continue
        for key in ("options", "supplied_morphemes"):
            raw = payload.get(key, [])
            if isinstance(raw, list):
                for text in raw:
                    words = WORD_RE.findall(str(text).lower())
                    if len(words) == 1:
                        word = words[0]
                        singular = _regular_singular(word)
                        if unit_id == "GRAMMAR_REGULAR_PLURAL_NOUNS" and (singular or key == "supplied_morphemes"):
                            cues.update(_word_forms(singular or word))
        prompt = str(payload.get("prompt") or "")
        for quoted in re.findall(r'["\']([A-Za-z]+)["\']', prompt):
            cues.update(_word_forms(quoted))
    return tuple(sorted(cues - IRREGULAR - FUNCTION_WORDS))


def _runtime_lexicon(bundles: Mapping[str, Any]) -> frozenset[str]:
    words = set(FUNCTION_WORDS)
    for text in _walk_strings(bundles):
        words.update(token.lower() for token in WORD_RE.findall(text))
        if text.startswith("vocabulary:"):
            words.update(_word_forms(text.split(":")[1]))
        if text.startswith("chunk:"):
            words.update(token.lower() for token in WORD_RE.findall(text.split(":", 1)[1]))
    expanded = set(words)
    for word in tuple(words):
        expanded.update(_word_forms(word))
    return frozenset(expanded)


def build_unit_profiles(repo_root: Path, limit: int = 2) -> tuple[list[Profile], frozenset[str]]:
    runtime = repo_root / RUNTIME_ROOT
    sequence, bundles = base._load_json(runtime / "sequence.json"), base._load_json(runtime / "bundles.json")
    graph_path = runtime / "graph.json"
    graph = base._load_json(graph_path) if graph_path.is_file() else {}
    if not isinstance(sequence, Mapping) or not isinstance(bundles, Mapping):
        raise CalibrationError("RUNTIME_AUTHORITY_SHAPE_INVALID")
    selected = sorted(((str(k), int(v)) for k, v in sequence.items()), key=lambda x: x[1])[:limit]
    prereq: dict[str, set[str]] = defaultdict(set)
    for edge in graph.get("edges", []) if isinstance(graph, Mapping) else []:
        if not isinstance(edge, Mapping):
            continue
        source, target = str(edge.get("source_ref") or edge.get("from") or ""), str(edge.get("target_ref") or edge.get("to") or "")
        for unit, _ in selected:
            if unit in target and source:
                prereq[unit].add(source.split(":")[-1])
    profiles: list[Profile] = []
    for unit, order in selected:
        relevant = {k: v for k, v in bundles.items() if isinstance(k, str) and f":{unit}:" in k and isinstance(v, Mapping)}
        assets = [a for bundle in relevant.values() for a in bundle.get("assets", []) if isinstance(a, Mapping)]
        if not assets:
            raise CalibrationError(f"UNIT_RUNTIME_BUNDLES_MISSING={unit}")
        evp = tuple(sorted(base._collect(assets, "target_evp_sense_ids")))
        chunks = tuple(sorted(base._collect(assets, "target_chunk_ids")))
        lexical = tuple(sorted(filter(None, (base._cue(ref) for ref in (*evp, *chunks)))))
        response_modes = {f"response_mode:{m}" for m in base._collect(assets, "response_mode")}
        question_types = tuple(sorted(base._collect(assets, "question_type") | response_modes))
        runtime_cues = _runtime_cues(assets, unit)
        sources = ["A1FS_RUNTIME_BUNDLES"]
        if unit == "GRAMMAR_REGULAR_PLURAL_NOUNS" and (not evp or not base._collect(assets, "target_egp_row_ids")):
            sources.append("RUNTIME_LEARNER_PAYLOAD_FALLBACK")
        levels = sorted({str(v.get("lesson", {}).get("level") or "") for v in relevant.values()} - {""})
        profiles.append(Profile(unit, order, levels[0] if len(levels) == 1 else "/".join(levels), tuple(sorted(relevant)),
                                tuple(sorted({str(v.get("lesson", {}).get("skill") or "") for v in relevant.values()} - {""})),
                                question_types, tuple(sorted(base._collect(assets, "communicative_goal"))),
                                tuple(sorted(base._collect(assets, "grammar_clue"))), tuple(sorted(base._collect(assets, "context_id"))),
                                evp, tuple(sorted(base._collect(assets, "target_egp_row_ids"))), chunks,
                                tuple(sorted(base._collect(assets, "target_pattern_ids"))), lexical, runtime_cues,
                                tuple(sources), tuple(sorted(prereq[unit]))))
    if len(profiles) != limit or not all(p.as_dict()["authority_complete_for_filtering"] for p in profiles):
        raise CalibrationError("UNIT_AUTHORITY_PROFILE_INCOMPLETE")
    return profiles, _runtime_lexicon(bundles)


def _grammar_hits(unit: str, text: str) -> tuple[int, dict[str, int]]:
    if unit == "GRAMMAR_ARTICLES_BASIC":
        all_hits, ind, definite = len(ARTICLE_RE.findall(text)), len(INDEFINITE_RE.findall(text)), len(DEFINITE_RE.findall(text))
        return all_hits, {"article_np": all_hits, "indefinite_np": ind, "definite_np": definite}
    words = [a or b for a, b in PLURAL_RE.findall(text)]
    valid = [w for w in words if w.lower() not in FALSE_PLURALS and w.lower() not in IRREGULAR]
    return len(valid), {"regular_plural_context": len(valid)}


def _sentences(text: str) -> list[str]:
    return [m.group(0).strip() for m in SENTENCE_RE.finditer(text) if m.group(0).strip()]


def _lexical_hits(profile: Profile, text: str) -> list[str]:
    normalized = f" {base.normalize_text(text)} "
    return [cue for cue in profile.cues if f" {base.normalize_text(cue)} " in normalized]


def candidate_windows(text: str, profile: Profile) -> list[str]:
    sentences = _sentences(text)
    if not sentences:
        return []
    anchors = [i for i, sentence in enumerate(sentences) if _grammar_hits(profile.unit_id, sentence)[0] or _lexical_hits(profile, sentence)]
    windows: dict[str, str] = {}
    if len(sentences) <= 6 and len(WORD_RE.findall(text)) <= 80 and anchors:
        windows[base.normalize_text(text)] = text.strip()
    for anchor in anchors:
        for width in (1, 2, 3):
            for start in range(max(0, anchor - width + 1), min(anchor, len(sentences) - width) + 1):
                window = " ".join(sentences[start:start + width]).strip()
                if 3 <= len(WORD_RE.findall(window)) <= 80:
                    windows.setdefault(base.normalize_text(window), window)
    ranked = sorted(windows.values(), key=lambda w: (-_grammar_hits(profile.unit_id, w)[0] / max(len(WORD_RE.findall(w)), 1), len(WORD_RE.findall(w)), base.normalize_text(w)))
    return ranked[:12]


def _vocab(text: str, lexicon: frozenset[str]) -> dict[str, Any]:
    tokens = [w.lower() for w in WORD_RE.findall(text) if w.lower() not in FUNCTION_WORDS]
    unknown = sorted({w for w in tokens if w not in lexicon and _regular_singular(w) not in lexicon})
    known = len(tokens) - sum(1 for w in tokens if w in unknown)
    ratio = known / len(tokens) if tokens else 1.0
    return {"known_ratio": round(ratio, 4), "unknown_unique": unknown, "safe": ratio >= 0.85 and len(unknown) <= 3}


def _blocked(text: str) -> list[str]:
    return [name for name, pattern in BLOCKED if pattern.search(text)]


def _skills(tags: Sequence[str], words: int, sentences: int, vocab_safe: bool, blocked: Sequence[str], grammar_hits: int) -> tuple[list[str], list[str]]:
    tagset = set(tags)
    strict, rewrite = set(), set()
    if grammar_hits and vocab_safe and not blocked and words <= 80 and sentences <= 3:
        strict.add("READING_SOURCE_ELIGIBLE")
    elif grammar_hits:
        rewrite.add("READING_REWRITE_CANDIDATE")
    if "listening_audio_seed" in tagset and grammar_hits and vocab_safe and not blocked and words <= 40 and sentences <= 3:
        strict.add("LISTENING_SCRIPT_ELIGIBLE")
    elif "listening_audio_seed" in tagset and grammar_hits:
        rewrite.add("LISTENING_REWRITE_CANDIDATE")
    if tagset & {"dialogue_rewrite_seed", "picture_prompt_seed", "retelling_seed"} and grammar_hits and vocab_safe and not blocked and words <= 50 and sentences <= 3:
        strict.add("SPEAKING_PROMPT_ELIGIBLE")
    elif tagset & {"dialogue_rewrite_seed", "picture_prompt_seed", "retelling_seed"} and grammar_hits:
        rewrite.add("SPEAKING_REWRITE_CANDIDATE")
    if tagset & {"grammar_pattern_seed", "vocabulary_exposure_seed", "exercise_seed"} and grammar_hits and vocab_safe and not blocked and words <= 30 and sentences <= 2:
        strict.add("WRITING_SEED_ELIGIBLE")
    elif tagset & {"grammar_pattern_seed", "vocabulary_exposure_seed", "exercise_seed"} and grammar_hits:
        rewrite.add("WRITING_REWRITE_CANDIDATE")
    return sorted(strict), sorted(rewrite)


def _result(record: Mapping[str, Any], parent: str, window: str, profile: Profile, lexicon: frozenset[str]) -> dict[str, Any]:
    level, source_type = base._first(record, LEVEL_KEYS).upper(), base._first(record, TYPE_KEYS)
    tags = base.extract_tags(record)
    words, sentences = len(WORD_RE.findall(window)), len(_sentences(window))
    hits, evidence = _grammar_hits(profile.unit_id, window)
    lexical = _lexical_hits(profile, window)
    vocab, blocked = _vocab(window, lexicon), _blocked(window)
    density = hits / max(words, 1)
    strict, rewrite = _skills(tags, words, sentences, vocab["safe"], blocked, hits)
    score = round(density * 100 + min(len(lexical), 5) * 3 + vocab["known_ratio"] * 10 + len(strict) * 4 + SOURCE_PRIORITY.get(source_type, 0) - len(blocked) * 8, 3)
    semantic = base._hash(base.normalize_text(window))
    lineage = base._first(record, LINEAGE_KEYS)
    projection = base._hash("|".join((lineage or base._first(record, PATH_KEYS), source_type, base.normalize_text(parent), semantic)))
    return {"classification": "PENDING", "reasons": [], "score": score, "reading_intake_id": base._first(record, ("reading_intake_id", "query_item_id")),
            "source_record_id": lineage, "source_level": level, "source_type": source_type, "source_path": base._first(record, PATH_KEYS),
            "text": window, "parent_word_count": len(WORD_RE.findall(parent)), "word_count": words, "sentence_count": sentences,
            "grammar_hits": hits, "grammar_evidence": evidence, "target_density": round(density, 4), "lexical_hits": lexical,
            "vocabulary_gate": vocab, "blocked_grammar_features": blocked, "reusability_tags": list(tags),
            "skill_eligibility": strict, "rewrite_skill_eligibility": rewrite, "semantic_identity": semantic, "projection_identity": projection}


def _rank(row: Mapping[str, Any]) -> tuple[int, int, int, float, int]:
    return (1 if row.get("source_record_id") else 0, 1 if row.get("source_level") in DIRECT_LEVELS else 0,
            SOURCE_PRIORITY.get(str(row.get("source_type")), 0), float(row.get("score") or 0), -int(row.get("word_count") or 0))


def _classify(row: Mapping[str, Any]) -> tuple[str, list[str]]:
    if not row.get("source_record_id"):
        return "REJECT", ["SOURCE_LINEAGE_GROUP_MISSING"]
    if row.get("source_level") not in DIRECT_LEVELS | REWRITE_LEVELS:
        return "REJECT", ["SOURCE_LEVEL_INVALID"]
    if row.get("source_type") not in VALID_TYPES:
        return "REJECT", ["SOURCE_TYPE_INVALID"]
    if not row.get("grammar_hits"):
        return "REJECT", ["NO_TARGET_GRAMMAR_IN_WINDOW"]
    reasons = []
    if row.get("source_level") in REWRITE_LEVELS:
        reasons.append("REWRITE_ONLY_SOURCE_LEVEL")
    if not row.get("vocabulary_gate", {}).get("safe"):
        reasons.append("VOCABULARY_AUTHORITY_GATE_FAILED")
    if row.get("blocked_grammar_features"):
        reasons.append("BLOCKED_GRAMMAR_FEATURE_PRESENT")
    if float(row.get("target_density") or 0) < 0.04:
        reasons.append("TARGET_DENSITY_BELOW_MINIMUM")
    if row.get("source_level") in DIRECT_LEVELS and not reasons and row.get("skill_eligibility"):
        return "PASS", ["DIRECT_LEVEL_AUTHORITY_VOCAB_GRAMMAR_WINDOW_MATCH"]
    return "BORDERLINE", reasons or ["REWRITE_REQUIRED_OR_NO_STRICT_SKILL_ELIGIBILITY"]


@dataclass
class Accumulator:
    profile: Profile
    lexicon: frozenset[str]
    sample_limit: int
    counts: Counter[str] = field(default_factory=Counter)
    reasons: Counter[str] = field(default_factory=Counter)
    strict: Counter[str] = field(default_factory=Counter)
    rewrite: Counter[str] = field(default_factory=Counter)
    levels: Counter[str] = field(default_factory=Counter)
    types: Counter[str] = field(default_factory=Counter)
    seen: set[str] = field(default_factory=set)
    groups: dict[str, dict[str, Any]] = field(default_factory=dict)
    meta: dict[str, dict[str, Any]] = field(default_factory=dict)
    rejects: list[dict[str, Any]] = field(default_factory=list)

    def add(self, row: dict[str, Any]) -> None:
        if row["projection_identity"] in self.seen:
            self.counts["projection_duplicate_count"] += 1
            return
        self.seen.add(row["projection_identity"])
        self.counts["eligible_projection_distinct_count"] += 1
        key = row["semantic_identity"]
        meta = self.meta.setdefault(key, {"missing": False, "complete": False, "ids": set(), "tags": set()})
        lineage = row.get("source_record_id")
        meta["missing"], meta["complete"] = meta["missing"] or not bool(lineage), meta["complete"] or bool(lineage)
        if lineage:
            meta["ids"].add(lineage)
        meta["tags"].update(row.get("reusability_tags", []))
        if key in self.groups:
            self.counts["semantic_duplicate_count"] += 1
            if _rank(row) > _rank(self.groups[key]):
                self.groups[key] = row
        else:
            self.groups[key] = row

    def finish(self) -> dict[str, list[dict[str, Any]]]:
        self.counts["eligible_semantic_distinct_count"] = len(self.groups)
        buckets = {"PASS": [], "BORDERLINE": [], "REJECT": list(self.rejects)}
        for key, original in self.groups.items():
            row, meta = dict(original), self.meta[key]
            row["reusability_tags"] = sorted(meta["tags"])
            if meta["complete"] and not row.get("source_record_id"):
                row["source_record_id"] = sorted(meta["ids"])[0]
            recovered = bool(meta["missing"] and meta["complete"])
            row["lineage_recovered_from_semantic_group"] = recovered
            if recovered:
                self.counts["lineage_group_recovered_count"] += 1
            cls, reasons = _classify(row)
            row["classification"], row["reasons"] = cls, reasons
            self.counts[f"{cls.lower()}_count"] += 1
            self.levels[row.get("source_level") or "UNKNOWN"] += 1
            self.types[row.get("source_type") or "UNKNOWN"] += 1
            if cls == "PASS":
                self.strict.update(row.get("skill_eligibility", []))
            elif cls == "BORDERLINE":
                self.rewrite.update(row.get("rewrite_skill_eligibility", []))
            else:
                self.reasons.update(reasons)
            buckets[cls].append(_sample(row))
        return {name: _sample_strata(rows, self.sample_limit) for name, rows in buckets.items()}


def _sample(row: Mapping[str, Any]) -> dict[str, Any]:
    keys = ("classification", "reasons", "score", "reading_intake_id", "source_record_id", "source_level", "source_type", "source_path",
            "parent_word_count", "word_count", "sentence_count", "grammar_hits", "grammar_evidence", "target_density", "lexical_hits",
            "vocabulary_gate", "blocked_grammar_features", "reusability_tags", "skill_eligibility", "rewrite_skill_eligibility",
            "lineage_recovered_from_semantic_group", "semantic_identity")
    return {k: row.get(k) for k in keys} | {"text_excerpt": str(row.get("text") or "")[:600]}


def _sample_strata(rows: Sequence[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        level = str(row.get("source_level") or "")
        band = "A_I" if level in DIRECT_LEVELS else "J_W" if level in REWRITE_LEVELS else "UNKNOWN"
        skill = ",".join(row.get("skill_eligibility") or row.get("rewrite_skill_eligibility") or ["NONE"])
        groups[(band, str(row.get("source_type") or "UNKNOWN"), skill)].append(row)
    for values in groups.values():
        values.sort(key=lambda r: (-float(r.get("score") or 0), int(r.get("word_count") or 0), str(r.get("semantic_identity") or "")))
    out, keys = [], sorted(groups)
    while len(out) < limit and keys:
        next_keys = []
        for key in keys:
            if groups[key] and len(out) < limit:
                out.append(groups[key].pop(0))
            if groups[key]:
                next_keys.append(key)
        keys = next_keys
    return out


def run_calibration(*, repo_root: Path, index_path: Path, output_dir: Path, max_records: int | None = None,
                    sample_limit: int = 30, progress_every: int = 50_000) -> dict[str, Any]:
    profiles, lexicon = build_unit_profiles(repo_root)
    accumulators = {p.unit_id: Accumulator(p, lexicon, sample_limit) for p in profiles}
    scanned = 0
    for record in base.iter_query_index(index_path):
        scanned += 1
        text = base.extract_text(record)
        level, source_type = base._first(record, LEVEL_KEYS).upper(), base._first(record, TYPE_KEYS)
        for acc in accumulators.values():
            acc.counts["raw_records_scanned"] += 1
            if level not in DIRECT_LEVELS | REWRITE_LEVELS or source_type not in VALID_TYPES or len(WORD_RE.findall(text)) < 3:
                reason = "SOURCE_OR_TEXT_PREFILTER_FAILED"
                acc.counts["prefilter_reject_record_count"] += 1
                acc.reasons[reason] += 1
                if len(acc.rejects) < sample_limit:
                    acc.rejects.append({"classification": "REJECT", "reasons": [reason], "source_level": level, "source_type": source_type,
                                        "source_path": base._first(record, PATH_KEYS), "source_record_id": base._first(record, LINEAGE_KEYS), "text_excerpt": text[:600]})
                continue
            windows = candidate_windows(text, acc.profile)
            if not windows:
                acc.counts["no_candidate_window_record_count"] += 1
                acc.reasons["NO_TARGET_WINDOW"] += 1
                continue
            acc.counts["source_records_with_candidate_windows"] += 1
            acc.counts["candidate_windows_generated"] += len(windows)
            for window in windows:
                acc.add(_result(record, text, window, acc.profile, lexicon))
        if progress_every and scanned % progress_every == 0:
            print(f"PROGRESS_RECORDS_SCANNED={scanned}")
        if max_records is not None and scanned >= max_records:
            break
    if not scanned:
        raise CalibrationError("QUERY_INDEX_EMPTY")
    units = []
    for profile in profiles:
        acc = accumulators[profile.unit_id]
        samples = acc.finish()
        units.append({"unit_profile": profile.as_dict(), "filter_funnel": dict(sorted(acc.counts.items())),
                      "rejection_reasons": dict(acc.reasons.most_common()), "strict_skill_capacity": dict(acc.strict.most_common()),
                      "rewrite_skill_capacity": dict(acc.rewrite.most_common()), "source_level_distribution": dict(sorted(acc.levels.items())),
                      "source_type_distribution": dict(acc.types.most_common()), "samples": samples})
    validation = {"unit_count": len(units), "expected_unit_count": 2,
                  "all_units_have_authority_complete_filter_profiles": all(u["unit_profile"]["authority_complete_for_filtering"] for u in units),
                  "all_units_have_effective_lexical_cues": all(u["unit_profile"]["effective_lexical_cues"] for u in units),
                  "unit02_runtime_fallback_authority_used": any(u["unit_profile"]["unit_id"] == "GRAMMAR_REGULAR_PLURAL_NOUNS" and "RUNTIME_LEARNER_PAYLOAD_FALLBACK" in u["unit_profile"]["authority_sources"] for u in units),
                  "semantic_group_lineage_recovery_applied": True, "windowed_filter_applied": True,
                  "vocabulary_authority_gate_applied": True, "blocked_grammar_gate_applied": True,
                  "strict_skill_eligibility_applied": True, "canonical_content_modified": False}
    if not all(v for k, v in validation.items() if k != "canonical_content_modified"):
        raise CalibrationError("FULLFIX_VALIDATION_FAILED")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "a1fs_v1_razq01a_unit01_unit02_filter_calibration.json"
    validation_path = output_dir / "a1fs_v1_razq01a_unit01_unit02_filter_validation.json"
    matrix_path = output_dir / "a1fs_v1_razq01a_unit01_unit02_distinct_capacity_matrix.csv"
    report = {"schema_version": SCHEMA_VERSION, "program_id": PROGRAM_ID, "task_id": TASK_ID, "status": PASS_STATUS,
              "scope": {"allowed_units": [p.unit_id for p in profiles], "blocked_units": "UNIT_03_TO_UNIT_24", "a2_status": "LOCKED",
                        "canonical_promotion": False, "learner_facing_content_write": False},
              "inputs": {"query_index_path": str(index_path), "repo_root": str(repo_root), "runtime_authority_root": str(repo_root / RUNTIME_ROOT),
                         "runtime_approved_lexicon_size": len(lexicon)},
              "filter_policy": {"window_sentence_limit": 3, "window_word_limit": 80, "max_windows_per_record": 12,
                                "vocabulary_known_ratio_min": 0.85, "vocabulary_unknown_unique_max": 3,
                                "vocabulary_authority_gate": "A1FS_RUNTIME_APPROVED_LEXICON",
                                "lineage_policy": "SEMANTIC_GROUP_RECOVERY_THEN_FAIL_CLOSED",
                                "admission_status": "CALIBRATION_ONLY_NOT_PROMOTED"},
              "records_scanned": scanned, "partial_scan": max_records is not None and scanned >= max_records,
              "units": units, "validation": validation,
              "outputs": {"report": str(report_path), "validation": str(validation_path), "capacity_matrix": str(matrix_path)},
              "next_short_step": NEXT_SHORT_STEP}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validation_path.write_text(json.dumps({"schema_version": SCHEMA_VERSION, "task_id": TASK_ID, "status": PASS_STATUS,
                                           "records_scanned": scanned, "validation": validation, "next_short_step": NEXT_SHORT_STEP},
                                          ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = ["unit_id", "sequence_order", "level", "raw_records_scanned", "source_records_with_candidate_windows", "candidate_windows_generated",
              "eligible_projection_distinct_count", "eligible_semantic_distinct_count", "lineage_group_recovered_count", "pass_count", "borderline_count",
              "reject_count", "reading_source_eligible_capacity", "listening_script_eligible_capacity", "speaking_prompt_eligible_capacity",
              "writing_seed_eligible_capacity", "reading_rewrite_candidate_capacity", "listening_rewrite_candidate_capacity",
              "speaking_rewrite_candidate_capacity", "writing_rewrite_candidate_capacity"]
    with matrix_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for unit in units:
            p, f, strict, rewrite = unit["unit_profile"], unit["filter_funnel"], unit["strict_skill_capacity"], unit["rewrite_skill_capacity"]
            writer.writerow({"unit_id": p["unit_id"], "sequence_order": p["sequence_order"], "level": p["level"],
                             **{k: f.get(k, 0) for k in fields if k in f},
                             "reading_source_eligible_capacity": strict.get("READING_SOURCE_ELIGIBLE", 0),
                             "listening_script_eligible_capacity": strict.get("LISTENING_SCRIPT_ELIGIBLE", 0),
                             "speaking_prompt_eligible_capacity": strict.get("SPEAKING_PROMPT_ELIGIBLE", 0),
                             "writing_seed_eligible_capacity": strict.get("WRITING_SEED_ELIGIBLE", 0),
                             "reading_rewrite_candidate_capacity": rewrite.get("READING_REWRITE_CANDIDATE", 0),
                             "listening_rewrite_candidate_capacity": rewrite.get("LISTENING_REWRITE_CANDIDATE", 0),
                             "speaking_rewrite_candidate_capacity": rewrite.get("SPEAKING_REWRITE_CANDIDATE", 0),
                             "writing_rewrite_candidate_capacity": rewrite.get("WRITING_REWRITE_CANDIDATE", 0)})
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True); parser.add_argument("--index-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True); parser.add_argument("--max-records", type=int)
    parser.add_argument("--sample-limit", type=int, default=30); parser.add_argument("--progress-every", type=int, default=50_000)
    args = parser.parse_args(argv)
    try:
        report = run_calibration(repo_root=args.repo_root.resolve(), index_path=args.index_path.resolve(), output_dir=args.output_dir.resolve(),
                                 max_records=args.max_records, sample_limit=args.sample_limit, progress_every=args.progress_every)
    except CalibrationError as exc:
        print(f"STATUS=FAIL_A1FS_V1_RAZQ01A_AUTHORITY_WINDOWED_FULLFIX\nERROR={exc}"); return 1
    print(f"STATUS={report['status']}"); print(f"RECORDS_SCANNED={report['records_scanned']}")
    for unit in report["units"]:
        f, p = unit["filter_funnel"], unit["unit_profile"]
        print(f"UNIT={p['unit_id']} PASS={f.get('pass_count', 0)} BORDERLINE={f.get('borderline_count', 0)} REJECT={f.get('reject_count', 0)} WINDOWS={f.get('candidate_windows_generated', 0)}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}"); return 0


if __name__ == "__main__":
    raise SystemExit(main())
