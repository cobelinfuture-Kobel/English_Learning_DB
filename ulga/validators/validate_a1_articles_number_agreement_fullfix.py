#!/usr/bin/env python3
"""Full-fix the A1 article-number agreement gate used by the canonical dispatcher.

This remains an offline deterministic prototype. It adds an explicit guard for
obvious plural noun heads after a/an while preserving the existing a/an sound
check and allowing definite the with singular or plural noun phrases.
"""

from __future__ import annotations

from ulga.validators.validate_a1_canonical_executable_batch_01 import Decision, no, words, yes

TASK_ID = "R7-M105N_A1ArticlesNumberAgreementValidatorFullFix"
GRAMMAR_ID = "GRAMMAR_ARTICLES_BASIC"

IRREGULAR_PLURAL_NOUNS = {
    "children",
    "people",
    "men",
    "women",
    "feet",
    "teeth",
    "mice",
    "geese",
}

# Closed A1 exceptions for singular nouns that end in s. This is intentionally
# conservative because the validator is not a production parser.
SINGULAR_S_ENDING_NOUNS = {
    "address",
    "bus",
    "class",
    "dress",
    "glass",
    "grass",
    "maths",
    "news",
    "physics",
    "tennis",
}


def _looks_obviously_plural(token: str) -> bool:
    value = token.lower()
    if value in IRREGULAR_PLURAL_NOUNS:
        return True
    if value in SINGULAR_S_ENDING_NOUNS:
        return False
    if value.endswith(("ss", "us", "is")):
        return False
    if value.endswith(("ies", "ves", "ches", "shes", "xes", "zes", "ses")):
        return True
    return len(value) > 2 and value.endswith("s")


def classify_articles_number_agreement(text: str) -> Decision:
    tokens = words(text)
    if len(tokens) < 2 or tokens[0] not in {"a", "an", "the"}:
        return no("missing_article_noun_phrase")

    article = tokens[0]
    following_word = tokens[1]
    if article == "a" and following_word[0] in "aeiou":
        return no("a_an_phonology_gate")
    if article == "an" and following_word[0] not in "aeiou":
        return no("a_an_phonology_gate")

    # For this closed A1 policy, the final lexical token is treated as the noun
    # head candidate. This correctly handles simple adjective+noun phrases while
    # remaining fail-closed for obvious regular and irregular plurals.
    if article in {"a", "an"} and _looks_obviously_plural(tokens[-1]):
        return no("article_number_agreement_gate")

    primitive = (
        "ARTICLE_DEFINITE_THE_NOUN_PHRASE"
        if article == "the"
        else "ARTICLE_INDEFINITE_A_AN_SINGULAR_COUNT_NOUN"
    )
    return yes(primitive, "article_plus_number_compatible_noun_phrase")


__all__ = [
    "GRAMMAR_ID",
    "IRREGULAR_PLURAL_NOUNS",
    "SINGULAR_S_ENDING_NOUNS",
    "TASK_ID",
    "classify_articles_number_agreement",
]
