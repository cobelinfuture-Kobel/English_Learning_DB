"""Bounded equivalent optimizer for U01QB15 context source assignment.

This module changes no U01QB15 policy or authority. It replaces only the
combinatorial search strategy used to find the same quota/pair solution:
PF04=A, PF05+PF08=H, PF09=D. Writing depends on A/H/D, so D and the later PF05 /
PF08 split can be solved independently once A/H is fixed. The canonical builder
still constructs the bank, validates all denominators, and runs the exact final
288-base U01QB14R1 capacity proof.
"""
from __future__ import annotations

import itertools
from copy import deepcopy
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_v1_u01qb15_unit01_context_stratified_question_bank_replacement_and_per_scene_runtime_capacity_fullfix
    as target,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Search-strategy optimization only; delegates all U01QB15 content construction, "
    "validation, runtime-capacity proof, and migration to the canonical U01QB15 builder."
)

_ASSIGNMENT_CACHE: dict[str, dict[str, tuple[tuple[str, str], ...]]] | None = None
_QUOTA_CACHE: dict[str, dict[str, int]] | None = None
_LOCAL_CACHE: dict[
    tuple[str, tuple[int, int, int, int]],
    dict[str, tuple[tuple[str, str], ...]] | None,
] = {}


def _context_assignment_fast(
    *,
    context: str,
    quotas: Mapping[str, int],
    scenes: Sequence[Mapping[str, Any]],
    legal_nouns: Sequence[str],
    phrase_nouns: set[str],
    word_nouns: set[str],
    error_nouns: set[str],
) -> dict[str, tuple[tuple[str, str], ...]] | None:
    f04, f05, f08 = target.READING_REPLACEMENT_FAMILIES
    f09 = target.WRITING_CONTEXT_REPLACEMENT_FAMILY
    q04, q05, q08, q09 = (int(quotas[family]) for family in (f04, f05, f08, f09))
    h_count = q05 + q08
    noun_count = len(legal_nouns)
    if q04 + h_count > noun_count:
        return None
    if noun_count - q05 < target.U01QB12_REFERENCE_CONTEXT_QUOTA[context]:
        return None

    pairs = tuple((context, noun) for noun in legal_nouns)
    d_options = tuple(itertools.combinations(pairs, q09))
    write_cache: dict[tuple[frozenset[str], frozenset[str]], tuple[tuple[str, str], ...] | None] = {}
    read_cache: dict[
        tuple[frozenset[str], frozenset[str]],
        tuple[tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]] | None,
    ] = {}

    for a_pairs in itertools.combinations(pairs, q04):
        a_set = set(a_pairs)
        a_nouns = frozenset(pair[1] for pair in a_pairs)
        remaining = tuple(pair for pair in pairs if pair not in a_set)
        for h_pairs in itertools.combinations(remaining, h_count):
            h_nouns = frozenset(pair[1] for pair in h_pairs)
            ah_key = (a_nouns, h_nouns)

            if ah_key not in write_cache:
                chosen_d = None
                for d_pairs in d_options:
                    d_nouns = {pair[1] for pair in d_pairs}
                    retained_pf09 = set(legal_nouns) - d_nouns
                    if all(
                        target._writing_scene_feasible(
                            scene,
                            phrase_nouns=phrase_nouns,
                            word_nouns=word_nouns,
                            retained_pf09=retained_pf09,
                            pf13=set(a_nouns),
                            pf14=set(h_nouns),
                            pf15=d_nouns,
                        )
                        for scene in scenes
                    ):
                        chosen_d = tuple(d_pairs)
                        break
                write_cache[ah_key] = chosen_d
            d_choice = write_cache[ah_key]
            if d_choice is None:
                continue

            read_key = ah_key
            if read_key not in read_cache:
                chosen_split = None
                for b_pairs in itertools.combinations(h_pairs, q05):
                    b_set = set(b_pairs)
                    c_pairs = tuple(pair for pair in h_pairs if pair not in b_set)
                    b_nouns = {pair[1] for pair in b_pairs}
                    c_nouns = {pair[1] for pair in c_pairs}
                    final_pf05, pf16 = target._reference_split_nouns(
                        legal_nouns=legal_nouns,
                        retired_pf05=b_nouns,
                        context=context,
                    )
                    final_pf04 = set(legal_nouns) - set(a_nouns)
                    final_pf08 = set(legal_nouns) - c_nouns
                    if all(
                        target._reading_scene_feasible(
                            scene,
                            pf04=final_pf04,
                            pf05=final_pf05,
                            pf08=final_pf08,
                            pf16=pf16,
                            error_nouns=error_nouns,
                        )
                        for scene in scenes
                    ):
                        chosen_split = (tuple(b_pairs), tuple(c_pairs))
                        break
                read_cache[read_key] = chosen_split
            split = read_cache[read_key]
            if split is None:
                continue
            b_pairs, c_pairs = split
            return {
                f04: tuple(a_pairs),
                f05: b_pairs,
                f08: c_pairs,
                f09: d_choice,
            }
    return None


def production_assignment_by_context_fast(
    items: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, tuple[tuple[str, str], ...]]]:
    global _ASSIGNMENT_CACHE, _QUOTA_CACHE
    if _ASSIGNMENT_CACHE is not None:
        return deepcopy(_ASSIGNMENT_CACHE)

    f04 = target.READING_REPLACEMENT_FAMILIES[0]
    grouped = target._group_context_rows(items, f04)
    scenes = target._scene_requirements()
    phrase_nouns, word_nouns, error_nouns = target._fixed_noun_sets()
    contexts = list(target.u01qb10.seed.CONTEXT_IDS)
    context_order = sorted(
        contexts,
        key=lambda context: (
            -sum(len(row["form_ordinals"]) for row in scenes.get(context, [])),
            -len(scenes.get(context, [])),
            context,
        ),
    )
    families = target.REPLACEMENT_FAMILIES
    vectors = sorted(
        itertools.product(
            range(target.MIN_CONTEXT_QUOTA, target.MAX_CONTEXT_QUOTA + 1),
            repeat=len(families),
        ),
        key=lambda values: (sum(abs(value - 2.4) for value in values), values),
    )
    chosen: dict[str, dict[str, tuple[tuple[str, str], ...]]] = {}
    chosen_quotas: dict[str, dict[str, int]] = {}
    remaining = {family: target.CONTEXT_REPLACEMENT_COUNT for family in families}

    def solve(index: int) -> bool:
        if index == len(context_order):
            return all(value == 0 for value in remaining.values())
        context = context_order[index]
        future = len(context_order) - index - 1
        legal_nouns = tuple(target._pair_key(row)[1] for row in grouped.get(context, []))
        for values in vectors:
            quotas = dict(zip(families, values))
            feasible_totals = True
            for family, quota in quotas.items():
                after = remaining[family] - quota
                if after < target.MIN_CONTEXT_QUOTA * future or after > target.MAX_CONTEXT_QUOTA * future:
                    feasible_totals = False
                    break
            if not feasible_totals:
                continue
            key = (context, values)
            if key not in _LOCAL_CACHE:
                _LOCAL_CACHE[key] = _context_assignment_fast(
                    context=context,
                    quotas=quotas,
                    scenes=scenes.get(context, []),
                    legal_nouns=legal_nouns,
                    phrase_nouns=phrase_nouns,
                    word_nouns=word_nouns,
                    error_nouns=error_nouns,
                )
            local = _LOCAL_CACHE[key]
            if local is None:
                continue
            chosen[context] = local
            chosen_quotas[context] = quotas
            for family, quota in quotas.items():
                remaining[family] -= quota
            if solve(index + 1):
                return True
            for family, quota in quotas.items():
                remaining[family] += quota
            del chosen[context]
            del chosen_quotas[context]
        return False

    if not solve(0):
        raise target.ContextStratifiedFullFixError(
            "GLOBAL_CONTEXT_QUOTA_AND_SCENE_TASK_ASSIGNMENT_UNSAT"
        )
    _ASSIGNMENT_CACHE = {context: chosen[context] for context in contexts}
    _QUOTA_CACHE = {context: chosen_quotas[context] for context in contexts}
    return deepcopy(_ASSIGNMENT_CACHE)


def quota_by_family_fast() -> dict[str, dict[str, int]]:
    if _QUOTA_CACHE is None:
        production_assignment_by_context_fast(target.u01qb10.seed_bank()[1])
    assert _QUOTA_CACHE is not None
    return {
        family: {
            context: int(_QUOTA_CACHE[context][family])
            for context in target.u01qb10.seed.CONTEXT_IDS
        }
        for family in target.REPLACEMENT_FAMILIES
    }


def install() -> None:
    """Install the equivalent search implementation into canonical U01QB15."""
    global _ASSIGNMENT_CACHE, _QUOTA_CACHE
    _ASSIGNMENT_CACHE = None
    _QUOTA_CACHE = None
    _LOCAL_CACHE.clear()
    target._ASSIGNMENT_CACHE = None
    target._QUOTA_CACHE = None
    target._PAYLOAD_CACHE = None
    target._production_assignment_by_context = production_assignment_by_context_fast
    target._quota_by_family = quota_by_family_fast
