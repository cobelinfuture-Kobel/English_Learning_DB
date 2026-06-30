"""RAZ-S4 normalized text and tagging pipeline.

Reads RAZ raw extraction JSON files and produces derived normalized/enriched
outputs without mutating raw evidence files.

Default input:
    raz_output_jsons/Level_{LEVEL}/raz_{LEVEL}_{BOOK_ID}_audio_timeline_extract.json

Default output:
    raz_output_jsons/derived/Level_{LEVEL}/normalized/
    raz_output_jsons/derived/Level_{LEVEL}/enriched/
    raz_output_jsons/derived/reports/

Boundary rules:
    - raw JSON remains the source evidence layer.
    - derived normalized/enriched text outputs must not contain audio fields.
    - all records remain candidate_only in this stage.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from ulga.builders import build_raz_level_discovery as level_discovery

AUDIO_KEYS = {
    "section_audio",
    "audio_trace",
    "audio_url",
    "cue_start_ms",
    "cue_end_ms",
}

CONTENT_UNIT_TYPES = {
    "sentence",
    "page_unit",
    "multi_sentence_unit",
    "section_heading",
    "book_title",
    "author_credit",
    "illustrator_credit",
    "front_matter",
    "back_matter",
    "non_story_excluded",
    "reuse_unit",
    "unknown_text_unit",
}

MAPPED_THEMES = {
    "Personal",
    "DailyRoutine",
    "School",
    "Home",
    "Shopping",
    "Food",
    "Hobbies",
    "Travel",
    "Health",
    "Animals",
    "Community",
    "Nature",
    "StoryFable",
    "Math",
    "Money",
    "Weather",
    "Pets",
    "Transportation",
    "Science",
    "Feelings",
    "Actions",
    "Clothing",
    "Body",
    "Holidays",
    "Sports",
    "General",
    "Unknown",
}

SKILL_AREAS = {
    "reading",
    "listening",
    "speaking",
    "writing",
    "grammar",
    "vocabulary",
    "phonics",
    "sentence_structure",
    "comprehension",
    "retelling",
}

QUESTION_TYPES = {
    "multiple_choice",
    "fill_blank",
    "matching",
    "true_false",
    "short_answer",
    "sentence_ordering",
    "word_ordering",
    "error_correction",
    "reading_comprehension",
    "picture_description",
    "listening_choice",
    "dictation",
    "writing_prompt",
    "speaking_response",
    "retelling_prompt",
}

REUSABILITY_TAGS = {
    "short_reading_seed",
    "writing_model_seed",
    "dialogue_rewrite_seed",
    "exercise_seed",
    "sequencing_seed",
    "picture_prompt_seed",
    "listening_audio_seed",
    "comprehension_question_seed",
    "grammar_pattern_seed",
    "vocabulary_exposure_seed",
    "assessment_seed",
    "retelling_seed",
    "future_unknown_use",
}

AUTHORITY_STATUSES = {
    "raw_evidence",
    "candidate_only",
    "reviewed_candidate",
    "promoted",
    "rejected",
}

PROMOTION_STATUSES = {
    "not_promoted",
    "promotion_candidate",
    "promoted",
    "blocked",
    "rejected",
}

REVIEW_STATUSES = {
    "pending",
    "auto_reviewed",
    "human_review_required",
    "human_reviewed",
    "rejected",
}

TAGGING_STATUSES = {
    "not_tagged",
    "auto_tagged",
    "partially_tagged",
    "validated",
    "failed",
}

WARNING_TYPES = {
    "low_theme_confidence",
    "unknown_theme",
    "unknown_grammar",
    "unknown_vocabulary",
    "unknown_pattern",
    "section_heading_detected",
    "possible_non_sentence_text",
    "audio_field_present_in_enriched_output",
    "raw_link_missing",
    "page_unit_link_missing",
    "reuse_unit_link_missing",
    "invalid_enum_value",
    "promotion_not_allowed",
}

KNOWN_HEADINGS = {
    "introduction",
    "conclusion",
    "communication",
    "keeping people healthy",
    "keeping people safe",
    "words to know",
    "glossary",
    "index",
    "connections",
    "writing",
    "writing and art",
    "social studies",
    "science",
    "math",
}

IRREGULAR_PAST_MARKERS = {
    "said",
    "did",
    "had",
    "was",
    "were",
    "went",
    "came",
    "made",
    "got",
    "saw",
    "ran",
    "took",
    "gave",
    "ate",
    "fell",
    "found",
    "thought",
    "brought",
    "bought",
    "told",
    "knew",
}

SUBJECT_PRONOUNS = {"i", "you", "he", "she", "it", "we", "they"}
OBJECT_PRONOUNS = {"me", "you", "him", "her", "it", "us", "them"}
PLACE_PREPOSITIONS = {"in", "on", "under", "near", "at", "by", "beside", "behind", "between", "over", "inside", "outside"}
MODALS = {"can", "could", "should", "would", "will", "may", "might", "must"}
BE_FORMS = {"am", "is", "are", "was", "were", "be", "been", "being"}
DECLARATIVE_LINKING_VERBS = BE_FORMS | {"seem", "seems", "seemed", "become", "becomes", "became", "remain", "remains", "remained", "look", "looks", "looked", "feel", "feels", "felt"}
DECLARATIVE_AUXILIARIES = DECLARATIVE_LINKING_VERBS | {"do", "does", "did", "has", "have", "had"}
DECLARATIVE_START_BLOCKERS = {"and", "then", "but", "or", "so"}
DECLARATIVE_BASE_VERBS = {
    "go",
    "grow",
    "help",
    "live",
    "look",
    "play",
    "protect",
    "run",
    "sing",
    "sit",
    "stand",
    "stay",
    "swim",
    "thank",
    "wave",
    "work",
}

IMPERATIVE_STARTERS = {
    "beware",
    "cover",
    "dig",
    "do",
    "don't",
    "drop",
    "fill",
    "find",
    "get",
    "go",
    "help",
    "let",
    "listen",
    "look",
    "make",
    "move",
    "never",
    "pat",
    "please",
    "roll",
    "run",
    "stop",
    "use",
}

THEME_KEYWORDS: list[tuple[str, str, set[str]]] = [
    ("Health", "Health", {"flu", "sick", "sneeze", "sneezing", "cough", "coughing", "doctor", "healthy", "health", "thermometer", "hospital", "hurt", "ache", "aching", "fever", "medicine", "dentist", "teeth", "tooth", "muscle", "muscles", "exercise", "safe", "safety"}),
    ("Animals", "Animals", {"animal", "animals", "wolf", "pig", "pigs", "dog", "dogs", "cat", "cats", "bird", "birds", "bear", "bears", "horse", "cow", "sheep", "duck", "ducks", "fish", "fishes", "worm", "earthworm", "earthworms", "zebra", "lion", "tiger", "rabbit", "rabbits", "bunny", "kitten", "kittens", "butterfly", "insect", "lizard", "raccoon", "bee", "bees", "rooster", "crow", "frog", "snake", "hamster", "pet", "pets"}),
    ("Pets and Animal Care", "Pets", {"pet", "pets", "jupe", "hamster", "fishtank", "tank", "fish", "dog", "cat", "kitten", "bunny", "raccoon", "feed", "care", "cage"}),
    ("Food", "Food", {"food", "eat", "eats", "ate", "taste", "tastes", "tasting", "sweet", "sour", "salty", "rice", "milk", "water", "bread", "cake", "apple", "banana", "fruit", "vegetable", "vegetables", "salad", "pizza", "cookie", "cookies", "sundae", "lunch", "dinner", "breakfast", "picnic", "restaurant", "bake", "baking", "cook", "cooking"}),
    ("Home", "Home", {"home", "house", "apartment", "building", "door", "room", "bedroom", "kitchen", "bathroom", "table", "chair", "bed", "sofa", "family", "mom", "dad", "grandparent", "grandparents", "brother", "sister"}),
    ("School", "School", {"school", "teacher", "student", "class", "classroom", "book", "books", "pencil", "desk", "read", "reads", "write", "writing", "library", "homework", "lesson"}),
    ("Shopping", "Shopping", {"shop", "shopping", "store", "mall", "buy", "card", "cards", "bag", "market"}),
    ("Money and Finance", "Money", {"money", "save", "saves", "spend", "spending", "dime", "dimes", "penny", "pennies", "nickel", "nickels", "quarter", "quarters", "coin", "coins", "price", "cost", "costs", "pay"}),
    ("Travel", "Travel", {"travel", "trip", "camping", "places", "place", "city", "country", "mountain", "mountains", "beach", "park", "road", "street"}),
    ("Transportation", "Transportation", {"bus", "car", "cars", "truck", "trucks", "trucking", "train", "plane", "airplane", "airplanes", "boat", "sled", "sleds", "bike", "bicycle", "ride", "rides", "driver", "drive", "drives", "wheels"}),
    ("Community", "Community", {"community", "worker", "workers", "doctor", "firefighter", "mail", "carrier", "hose", "deliver", "helper", "helpers", "neighborhood", "neighbor", "neighbors", "town", "city"}),
    ("Nature", "Nature", {"earth", "cave", "caves", "tree", "trees", "plant", "plants", "flower", "flowers", "forest", "pond", "rain", "sky", "sun", "moon", "river", "mountain", "mountains", "water", "spring", "fall", "garden", "leaf", "leaves"}),
    ("Weather and Seasons", "Weather", {"weather", "season", "seasons", "spring", "summer", "fall", "winter", "rain", "rainstorm", "snow", "snowball", "sunny", "cloud", "cloudy", "wind", "windy", "storm", "hot", "cold", "float", "sink"}),
    ("Science", "Science", {"science", "fossil", "fossils", "dinosaur", "dinosaurs", "rock", "rocks", "soil", "sink", "float", "magnet", "magnets", "material", "materials", "light", "sound", "sounds", "smell", "smells", "look", "looks", "feel", "feels", "insect", "lizard", "muscles", "body"}),
    ("Math and Numbers", "Math", {"math", "number", "numbers", "count", "counts", "counting", "how", "many", "all", "twelve", "double", "doubles", "half", "halves", "more", "less", "opposite", "opposites", "shape", "shapes", "pattern", "patterns", "same", "different"}),
    ("Daily Routine", "DailyRoutine", {"wake", "sleep", "bedtime", "wash", "brush", "dress", "dressed", "ready", "table", "bake", "play", "walk", "run", "go", "come", "clean", "push", "pull", "pack"}),
    ("Actions and Movement", "Actions", {"run", "runs", "running", "walk", "walks", "jump", "jumps", "move", "moves", "moving", "push", "pull", "kick", "row", "ride", "skate", "fly", "laugh", "smile", "draw", "write", "make", "build", "building"}),
    ("Hobbies", "Hobbies", {"game", "games", "ball", "sport", "sports", "athlete", "athletes", "kick", "swim", "ride", "row", "draw", "paint", "pirate", "pirates", "kite", "blocks", "music"}),
    ("Sports", "Sports", {"sport", "sports", "athlete", "athletes", "run", "runs", "running", "kick", "ball", "swim", "skate", "sled", "sleds", "bike", "ride"}),
    ("Personal", "Personal", {"name", "face", "faces", "boy", "girl", "mother", "father", "mom", "dad", "brother", "sister", "friend", "friends", "grandparent", "grandparents", "baby"}),
    ("Body and Senses", "Body", {"body", "face", "faces", "hair", "eye", "eyes", "ear", "ears", "nose", "mouth", "hand", "hands", "foot", "feet", "leg", "legs", "arm", "arms", "smell", "smells", "taste", "tastes", "feel", "feels", "look", "looks", "sound", "sounds"}),
    ("Clothing", "Clothing", {"clothes", "clothing", "dress", "dressed", "shirt", "shoes", "shoe", "hat", "coat", "pants", "socks", "jacket"}),
    ("Feelings and Character", "Feelings", {"happy", "sad", "mad", "scared", "scary", "nice", "kind", "funny", "laugh", "smile", "love", "like", "likes", "dream", "dreams", "easy", "hard", "safe"}),
    ("Holidays and Events", "Holidays", {"halloween", "thanksgiving", "christmas", "easter", "holiday", "parade", "pumpkin", "pumpkins", "cookies", "eggs", "birthday"}),
]

TITLE_THEME_OVERRIDES: list[tuple[str, str, str, list[str]]] = [
    ("amazing mummies", "Science and Nature Nonfiction", "Science", ["science", "nonfiction", "preservation", "mummies"]),
    ("my bones", "Body and Senses", "Body", ["body", "bones", "nonfiction"]),
    ("our five senses", "Body and Senses", "Body", ["body", "senses", "nonfiction"]),
    ("what lives in this hole", "Science and Nature Nonfiction", "Nature", ["nature", "animals", "habitats"]),
    ("statues in the ice", "Science and Nature Nonfiction", "Science", ["science", "ice", "preservation"]),
    ("statues in the sand", "Science and Nature Nonfiction", "Nature", ["nature", "sand", "landforms"]),
    ("nature stinks", "Science and Nature Nonfiction", "Science", ["science", "nature", "adaptation"]),
    ("the grand canyon", "Science and Nature Nonfiction", "Nature", ["nature", "landforms", "landmarks"]),
    ("weird bird beaks", "Animal Nonfiction", "Animals", ["animals", "birds", "nonfiction"]),
    ("legs, wings, fins, and flippers", "Animal Nonfiction", "Animals", ["animals", "body_parts", "nonfiction"]),
    ("what built this", "Science and Nature Nonfiction", "Science", ["science", "structures", "nonfiction"]),
    ("abigail adams", "History and Civics", "Community", ["history", "biography", "civics"]),
    ("american symbols", "History and Civics", "Community", ["history", "symbols", "civics"]),
    ("a president's day", "History and Civics", "Community", ["history", "holiday", "civics"]),
    ("dr. king's memorial", "History and Civics", "Community", ["history", "memorial", "civics"]),
    ("harriet tubman", "History and Civics", "Community", ["history", "biography", "civics"]),
    ("miles the nile crocodile", "Animal Nonfiction", "Animals", ["animals", "reptiles", "nonfiction"]),
    ("elephants: giant mammals", "Animal Nonfiction", "Animals", ["animals", "mammals", "nonfiction"]),
    ("scorpions", "Animal Nonfiction", "Animals", ["animals", "insects", "nonfiction"]),
    ("cockroaches", "Animal Nonfiction", "Animals", ["animals", "insects", "nonfiction"]),
    ("flies", "Animal Nonfiction", "Animals", ["animals", "insects", "nonfiction"]),
    ("city falcons", "Animal Nonfiction", "Animals", ["animals", "birds", "nonfiction"]),
    ("condors: giant birds", "Animal Nonfiction", "Animals", ["animals", "birds", "nonfiction"]),
    ("wiggly worms", "Animal Nonfiction", "Animals", ["animals", "worms", "nonfiction"]),
    ("rapunzel", "Folktale and Fairy Tale", "StoryFable", ["folktale", "fairy_tale"]),
    ("the empty pot", "Folktale and Fairy Tale", "StoryFable", ["folktale", "moral_story"]),
    ("troll bridge", "Folktale and Fairy Tale", "StoryFable", ["folktale", "troll"]),
    ("the stonecutter", "Folktale and Fairy Tale", "StoryFable", ["folktale", "fairy_tale"]),
    ("cinderella", "Folktale and Fairy Tale", "StoryFable", ["fairy_tale"]),
    ("the goat and the singing wolf", "Folktale and Fairy Tale", "StoryFable", ["fable", "animal_story"]),
    ("billy gets lost", "Social and Emotional Learning", "Feelings", ["social_emotional", "problem_solving"]),
    ("gordon finds his way", "Social and Emotional Learning", "Feelings", ["social_emotional", "problem_solving"]),
    ("rude robot", "Social and Emotional Learning", "Feelings", ["manners", "social_emotional"]),
    ("new rule!", "Social and Emotional Learning", "Feelings", ["self_regulation", "social_emotional"]),
    ("doing the right thing", "Social and Emotional Learning", "Feelings", ["moral_choice", "social_emotional"]),
    ("cool as a cuke", "Social and Emotional Learning", "Feelings", ["self_regulation", "feelings"]),
    ("tag-along goat", "Social and Emotional Learning", "Feelings", ["friendship", "social_emotional"]),
    ("the day i needed help", "Social and Emotional Learning", "Feelings", ["helping", "social_emotional"]),
    ("being a leftie", "Social and Emotional Learning", "Feelings", ["identity", "social_emotional"]),
    ("peace and quiet", "Social and Emotional Learning", "Feelings", ["relationships", "social_emotional"]),
    ("molly's new home", "Social and Emotional Learning", "Feelings", ["change", "social_emotional"]),
    ("mystery valentine", "Culture and Holiday Traditions", "Holidays", ["valentine", "holiday"]),
    ("the legend of nian", "Culture and Holiday Traditions", "Holidays", ["tradition", "holiday"]),
    ("nami's gifts", "Culture and Holiday Traditions", "Holidays", ["tradition", "gift_giving"]),
    ("sam's fourth of july", "Culture and Holiday Traditions", "Holidays", ["holiday", "celebration"]),
    ("my eid al-fitr", "Culture and Holiday Traditions", "Holidays", ["eid", "holiday"]),
    ("welcome to turkey", "Culture and Holiday Traditions", "Travel", ["culture", "country"]),
    ("wing's visit to singapore", "Culture and Holiday Traditions", "Travel", ["culture", "country"]),
    ("club monster", "Fantasy and Monster Story", "StoryFable", ["monster_story", "fantasy"]),
    ("pip, the monster princess", "Fantasy and Monster Story", "StoryFable", ["monster_story", "royalty"]),
    ("monsters' stormy day", "Fantasy and Monster Story", "StoryFable", ["monster_story", "fantasy"]),
    ("monster halloween", "Fantasy and Monster Story", "StoryFable", ["monster_story", "holiday_story"]),
    ("monsters on wheels", "Fantasy and Monster Story", "StoryFable", ["monster_story", "fantasy"]),
    ("a monster fish tale", "Fantasy and Monster Story", "StoryFable", ["monster_story", "fantasy"]),
    ("stormingo!", "Fantasy and Monster Story", "StoryFable", ["fantasy", "imaginary_character"]),
    ("the little red hen", "Folktale and Fairy Tale", "StoryFable", ["folktale", "moral_story"]),
    ("pedro's burro", "Folktale and Fairy Tale", "StoryFable", ["folktale", "animal_story"]),
    ("opposites", "Math and Concepts", "Math", ["opposites", "concept_words"]),
    ("double it", "Math and Numbers", "Math", ["doubling"]),
    ("spending dimes", "Money and Finance", "Money", ["coins", "spending"]),
    ("one at a time", "Math and Numbers", "Math", ["counting", "quantity"]),
    ("how many", "Math and Numbers", "Math", ["counting", "quantity"]),
    ("number", "Math and Numbers", "Math", ["numbers"]),
    ("count", "Math and Numbers", "Math", ["counting"]),
    ("shapes", "Math and Geometry", "Math", ["shapes"]),
    ("pet for jupe", "Pets and Animal Care", "Pets", ["pet", "animal_care"]),
    ("fishtank", "Pets and Animal Care", "Pets", ["pet_fish", "animal_care"]),
    ("hamster", "Pets and Animal Care", "Pets", ["pet", "animal_care"]),
    ("changing seasons", "Weather and Seasons", "Weather", ["seasons"]),
    ("weather", "Weather and Seasons", "Weather", ["weather"]),
    ("snowball", "Weather and Seasons", "Weather", ["snow"]),
    ("rainstorm", "Weather and Seasons", "Weather", ["rain"]),
    ("winter", "Weather and Seasons", "Weather", ["winter"]),
    ("trucking", "Transportation", "Transportation", ["trucks"]),
    ("bus", "Transportation", "Transportation", ["bus"]),
    ("airplane", "Transportation", "Transportation", ["airplane"]),
    ("sled", "Transportation", "Transportation", ["sled"]),
    ("fossils", "Science", "Science", ["fossils"]),
    ("sink or float", "Science", "Science", ["physical_science"]),
    ("taste this", "Body and Senses", "Body", ["taste", "senses"]),
    ("this tastes", "Body and Senses", "Body", ["taste", "senses"]),
    ("this smells", "Body and Senses", "Body", ["smell", "senses"]),
    ("this sounds", "Body and Senses", "Body", ["sound", "senses"]),
    ("this feels", "Body and Senses", "Body", ["touch", "senses"]),
    ("this looks", "Body and Senses", "Body", ["sight", "senses"]),
    ("my hair", "Body and Senses", "Body", ["hair"]),
    ("my face", "Body and Senses", "Body", ["face"]),
    ("my body", "Body and Senses", "Body", ["body"]),
    ("getting dressed", "Clothing", "Clothing", ["clothing"]),
    ("shoes", "Clothing", "Clothing", ["shoes"]),
    ("scaredy", "Feelings and Character", "Feelings", ["fear", "character"]),
    ("scary", "Feelings and Character", "Feelings", ["fear"]),
    ("happy", "Feelings and Character", "Feelings", ["emotion"]),
    ("nice", "Feelings and Character", "Feelings", ["character_trait"]),
    ("lost and found", "Daily Routine", "DailyRoutine", ["lost_found", "everyday_life"]),
    ("getting ready", "Daily Routine", "DailyRoutine", ["routine"]),
    ("wake up", "Daily Routine", "DailyRoutine", ["routine"]),
    ("bedtime", "Daily Routine", "DailyRoutine", ["routine"]),
    ("halloween", "Holidays and Events", "Holidays", ["halloween"]),
    ("thanksgiving", "Holidays and Events", "Holidays", ["thanksgiving"]),
    ("christmas", "Holidays and Events", "Holidays", ["christmas"]),
    ("easter", "Holidays and Events", "Holidays", ["easter"]),
    ("pizza", "Food", "Food", ["food_preparation"]),
    ("salad", "Food", "Food", ["food_preparation"]),
    ("bake", "Food", "Food", ["food_preparation"]),
    ("cookies", "Food", "Food", ["food"]),
    ("picnic", "Food", "Food", ["food", "outing"]),
    ("community workers", "Community", "Community", ["workers"]),
    ("neighborhood", "Community", "Community", ["community"]),
    ("camping", "Travel", "Travel", ["camping"]),
    ("mountains", "Nature", "Nature", ["mountains"]),
    ("forest", "Nature", "Nature", ["forest"]),
    ("pond", "Nature", "Nature", ["pond"]),
    ("flowers", "Nature", "Nature", ["flowers"]),
]

STORY_FABLE_TITLE_KEYWORDS = {
    "three little pigs",
    "mitten",
    "sky is falling",
    "zots",
    "fairy",
    "tale",
    "scaredy crow",
    "runaway snowball",
}


def is_narrow_imperative_sentence(text: str, *, is_heading: bool = False) -> bool:
    normalized = normalize_spacing(text)
    if not normalized or is_heading:
        return False
    if normalized.endswith("?") or detect_direct_speech(normalized):
        return False
    words = [normalize_word(token) for token in tokenize(normalized)]
    if len(words) < 2:
        return False
    first = words[0]
    if first not in IMPERATIVE_STARTERS:
        return False
    if first == "do" and not normalized.lower().startswith(("do not ", "don't ")):
        return False
    if first == "let" and not normalized.lower().startswith("let's "):
        return False
    return True

CHUNK_PATTERNS: list[tuple[str, str, str]] = [
    ("once upon a time", "once upon a time", "story_opening"),
    ("let me", "let me", "request_expression"),
    ("come in", "come in", "phrasal_or_fixed_expression"),
    ("a lot of", "a lot of", "quantity_phrase"),
    ("has the flu", "has the flu", "health_phrase"),
    ("put out", "put out", "phrasal_verb"),
    ("go to", "go to", "movement_phrase"),
    ("in the", "in the", "prepositional_phrase"),
    ("on the", "on the", "prepositional_phrase"),
]

@dataclass
class WarningRecord:
    warning_type: str
    severity: str
    record_id: str
    message: str
    level: str | None = None
    book_id: str | None = None
    raw_file_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "warning_type": self.warning_type,
            "severity": self.severity,
            "record_id": self.record_id,
            "message": self.message,
            "level": self.level,
            "book_id": self.book_id,
            "raw_file_path": self.raw_file_path,
        }


def append_warning_record(
    warnings: list[WarningRecord],
    *,
    warning_type: str,
    severity: str,
    record_id: str,
    message: str,
    level: str | None,
    book_id: str | None,
    raw_file_path: str | None,
) -> None:
    for warning in warnings:
        if warning.record_id == record_id and warning.warning_type == warning_type:
            return
    warnings.append(
        WarningRecord(
            warning_type=warning_type,
            severity=severity,
            record_id=record_id,
            message=message,
            level=level,
            book_id=book_id,
            raw_file_path=raw_file_path,
        )
    )


@dataclass
class PipelineResult:
    normalized_sentences: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    normalized_page_units: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    normalized_reuse_units: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    sentence_enriched: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    page_unit_enriched: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    reuse_unit_enriched: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    warnings: list[WarningRecord] = field(default_factory=list)
    by_book: list[dict[str, Any]] = field(default_factory=list)
    raw_files_seen: int = 0


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_spacing(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text)


def normalize_word(word: str) -> str:
    return word.lower().strip("'\".,!?;:()[]{}")


def has_forbidden_audio_keys(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in AUDIO_KEYS:
                return True
            if has_forbidden_audio_keys(nested):
                return True
    elif isinstance(value, list):
        return any(has_forbidden_audio_keys(item) for item in value)
    return False


def strip_audio_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: strip_audio_keys(nested)
            for key, nested in value.items()
            if key not in AUDIO_KEYS
        }
    if isinstance(value, list):
        return [strip_audio_keys(item) for item in value]
    return value


def detect_direct_speech(text: str) -> bool:
    return any(mark in text for mark in ['"', "“", "”", "‘", "’"])


def detect_heading(text: str) -> bool:
    t = normalize_spacing(text)
    if not t:
        return False
    lower = t.lower()
    if lower in KNOWN_HEADINGS:
        return True
    if re.search(r"[.!?]$", t):
        return False
    words = tokenize(t)
    if not (1 <= len(words) <= 5):
        return False
    if len(words) == 1 and words[0][0].isupper():
        return True
    major_words = [w for w in words if normalize_word(w) not in {"and", "or", "of", "the", "a", "an", "to", "in"}]
    return bool(major_words) and all(w[:1].isupper() for w in major_words)


def infer_content_unit_tags_for_sentence(text: str) -> dict[str, Any]:
    text = normalize_spacing(text)
    is_heading = detect_heading(text)
    is_question = text.endswith("?")
    is_direct_speech = detect_direct_speech(text)
    is_imperative = (
        not is_heading
        and len(tokenize(text)) >= 2
        and bool(re.match(r"^(Look|Listen|Go|Come|Run|Stop|Help|Let)\b", text))
    )
    content_unit_type = "section_heading" if is_heading else "sentence"
    return {
        "content_unit_type": content_unit_type,
        "sentence_authority_eligible": content_unit_type == "sentence",
        "is_story_sentence": content_unit_type == "sentence",
        "is_heading": is_heading,
        "is_direct_speech": is_direct_speech,
        "is_question": is_question,
        "is_imperative": is_imperative,
        "sentence_count": 1,
    }


def infer_content_unit_tags_for_page(text: str, sentence_count: int) -> dict[str, Any]:
    has_heading = any(detect_heading(line) for line in str(text or "").splitlines() if normalize_spacing(line))
    return {
        "content_unit_type": "multi_sentence_unit" if sentence_count >= 2 else "page_unit",
        "sentence_count": sentence_count,
        "has_multi_sentence_unit": sentence_count >= 2,
        "has_direct_speech": detect_direct_speech(str(text or "")),
        "has_sequence": bool(re.search(r"\b(first|then|next|finally|now|after|before|yet)\b", str(text or ""), re.I)),
        "has_heading": has_heading,
    }


def infer_theme(text: str, title: str) -> dict[str, Any]:
    title_lower = normalize_spacing(title).lower()
    text_lower = normalize_spacing(text).lower()
    combined = f"{title_lower} {text_lower}"
    words = {normalize_word(w) for w in tokenize(combined)}

    for pattern, primary, mapped, subthemes in TITLE_THEME_OVERRIDES:
        if pattern in title_lower:
            return {
                "primary_theme": primary,
                "mapped_theme": mapped,
                "subthemes": subthemes,
                "theme_confidence": 0.92,
                "theme_source": "title_override_map_v2",
            }

    if any(keyword in title_lower for keyword in STORY_FABLE_TITLE_KEYWORDS):
        return {
            "primary_theme": "Fairy Tale",
            "mapped_theme": "StoryFable",
            "subthemes": ["story", "fable"],
            "theme_confidence": 0.88,
            "theme_source": "rule_based_title",
        }

    best: tuple[str, str, int, set[str]] | None = None
    for primary, mapped, keywords in THEME_KEYWORDS:
        score = len(words & keywords)
        if score and (best is None or score > best[2]):
            best = (primary, mapped, score, keywords)

    if best:
        primary, mapped, score, keywords = best
        matched = sorted(words & keywords)
        confidence = min(0.95, 0.64 + 0.07 * score)
        return {
            "primary_theme": primary,
            "mapped_theme": mapped,
            "subthemes": matched[:6],
            "theme_confidence": round(confidence, 2),
            "theme_source": "expanded_rule_based_title_and_vocabulary_v2",
        }

    return {
        "primary_theme": "Unknown",
        "mapped_theme": "Unknown",
        "subthemes": [],
        "theme_confidence": 0.25,
        "theme_source": "fallback_unknown",
    }


def infer_grammar_tags(text: str) -> list[str]:
    lower = text.lower()
    words = [normalize_word(w) for w in tokenize(text)]
    word_set = set(words)
    tags: set[str] = set()
    is_heading = detect_heading(text)

    if re.search(r"\bthere\s+is\b", lower):
        tags.add("there_is")
    if re.search(r"\bthere\s+are\b", lower):
        tags.add("there_are")
    if word_set & BE_FORMS:
        tags.add("be_verb")
    if re.search(r"\b(am|is|are|was|were)\s+\w+ing\b", lower):
        tags.add("present_continuous")
    if word_set & MODALS:
        if "can" in word_set:
            tags.add("modal_can")
        else:
            tags.add("modal_other")
    if re.match(r"^(what|where|when|who|why|how)\b", lower):
        tags.add("question_wh")
    elif text.strip().endswith("?"):
        tags.add("question_yes_no")
    if detect_direct_speech(text):
        tags.add("direct_speech")
    if is_narrow_imperative_sentence(text, is_heading=is_heading):
        tags.add("imperative_procedural")
    if re.search(r"\bsaid\b", lower):
        tags.add("reported_speech_marker")
    if word_set & PLACE_PREPOSITIONS:
        tags.add("preposition_place")
    if word_set & SUBJECT_PRONOUNS:
        tags.add("pronoun_subject")
    if word_set & OBJECT_PRONOUNS:
        tags.add("pronoun_object")
    if re.search(r"\b\w+'s\b", lower):
        tags.add("possessive_s")
    if any(w in IRREGULAR_PAST_MARKERS or re.search(r"ed$", w) for w in words):
        tags.add("past_simple")
    if any(w.endswith("s") and len(w) > 3 for w in words):
        tags.add("plural_noun")
    if not tags:
        tags.add("unknown_grammar")

    return sorted(tags)


def has_pronunciation_annotation(text: str) -> bool:
    return "[" in text and "]" in text


def has_poetic_or_repetitive_pattern(text: str) -> bool:
    lower = text.lower()
    if lower.count(",") >= 2:
        return True
    if re.search(r"\b(\w+)\b(?:,\s*\1){1,}", lower):
        return True
    if re.search(r"\b(\w+)\b\s+\1\b", lower):
        return True
    return any(marker in lower for marker in {"pea-green", "piggy-wig", "pong-tree"})


def has_narrative_inversion_pattern(text: str) -> bool:
    stripped = normalize_spacing(text)
    return bool(re.match(r"^(And there|Then hand in hand|Away\b|Down\b)", stripped))


def find_simple_declarative_verb_index(words: list[str]) -> int | None:
    for index, word in enumerate(words[1:7], start=1):
        if word in DECLARATIVE_AUXILIARIES or word in MODALS or word in IRREGULAR_PAST_MARKERS:
            return index
        if word.endswith("ed"):
            return index
        if word.endswith("s") and len(word) > 3 and word not in {"this", "his", "was"}:
            return index
        if word in DECLARATIVE_BASE_VERBS:
            return index
    return None


def infer_simple_declarative_pattern(text: str, content_unit_tags: dict[str, Any] | None = None) -> str | None:
    normalized = normalize_spacing(text)
    if not normalized or content_unit_tags is None:
        return None
    if content_unit_tags.get("content_unit_type") == "section_heading" or content_unit_tags.get("is_heading"):
        return None
    if content_unit_tags.get("is_direct_speech") or content_unit_tags.get("is_question") or content_unit_tags.get("is_imperative"):
        return None
    if not normalized.endswith(".") or normalized.endswith("..."):
        return None
    if '"' in normalized or "'" in normalized[:1]:
        return None
    if any(mark in normalized for mark in [";", ":", "(", ")"]):
        return None
    if normalized.count(",") > 1:
        return None
    if has_pronunciation_annotation(normalized) or has_poetic_or_repetitive_pattern(normalized) or has_narrative_inversion_pattern(normalized):
        return None

    words = [normalize_word(token) for token in tokenize(normalized)]
    if not (3 <= len(words) <= 18):
        return None
    if words[0] in DECLARATIVE_START_BLOCKERS:
        return None
    if not (words[0] in SUBJECT_PRONOUNS or words[0] in {"the", "a", "an"} or normalized[:1].isupper()):
        return None

    verb_index = find_simple_declarative_verb_index(words)
    if verb_index is None or verb_index >= len(words) - 0:
        return None

    if words[verb_index] in DECLARATIVE_LINKING_VERBS:
        return "simple_declarative_svc"
    return "simple_declarative_svo"


def infer_sentence_patterns(text: str, content_unit_tags: dict[str, Any] | None = None) -> list[str]:
    lower = text.lower()
    patterns: list[str] = []

    if re.search(r"\bthere\s+is\b", lower):
        patterns.append("There is ___.")
    if re.search(r"\bthere\s+are\b", lower):
        patterns.append("There are ___.")
    if re.search(r"\b(am|is|are)\s+\w+ing\b", lower):
        patterns.append("___ is ___ing.")
    if re.search(r"\bshould\s+not\b", lower):
        patterns.append("___ should not ___.")
    if re.search(r"\bhas\s+the\s+flu\b", lower):
        patterns.append("___ has the flu.")
    if re.search(r"\bknocked\s+on\s+the\s+door\b", lower):
        patterns.append("___ knocked on the door.")
    if detect_direct_speech(text) and "said" in lower:
        patterns.append("\"___,\" said ___.")
    declarative_pattern = infer_simple_declarative_pattern(text, content_unit_tags)
    if declarative_pattern:
        patterns.append(declarative_pattern)
    if not patterns and len(tokenize(text)) <= 8:
        patterns.append("simple_sentence_candidate")
    return patterns


def infer_pos(word: str) -> str:
    w = normalize_word(word)
    if w in SUBJECT_PRONOUNS or w in OBJECT_PRONOUNS:
        return "pronoun"
    if w in BE_FORMS:
        return "verb"
    if w in PLACE_PREPOSITIONS:
        return "preposition"
    if w in MODALS:
        return "modal"
    if w.endswith("ing") or w.endswith("ed"):
        return "verb"
    if w.endswith("ly"):
        return "adverb"
    if w in {"a", "an", "the"}:
        return "article"
    return "unknown"


def infer_vocabulary_tags(text: str) -> list[dict[str, Any]]:
    tags: list[dict[str, Any]] = []
    seen: set[str] = set()
    for token in tokenize(text):
        normalized = normalize_word(token)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        tags.append({
            "word": token,
            "normalized_word": normalized,
            "pos": infer_pos(normalized),
            "cefr": None,
            "topic": None,
            "lookup_status": "not_linked_in_s4",
            "source": "rule_based_tokenization",
        })
    return tags


def infer_chunk_tags(text: str) -> list[dict[str, Any]]:
    lower = text.lower()
    tags: list[dict[str, Any]] = []
    for surface, normalized, usage_class in CHUNK_PATTERNS:
        if surface in lower:
            tags.append({
                "chunk": surface,
                "normalized_chunk": normalized,
                "usage_class": usage_class,
                "source": "rule_based_phrase_match",
            })
    return tags


def infer_linguistic_tags(text: str, raz_level: str, content_unit_tags: dict[str, Any] | None = None) -> dict[str, Any]:
    grammar_tags = infer_grammar_tags(text)
    pattern_tags = infer_sentence_patterns(text, content_unit_tags)
    return {
        "cefr_estimate": None,
        "raz_level": raz_level,
        "grammar_tags": grammar_tags,
        "sentence_pattern_tags": pattern_tags,
        "vocabulary_tags": infer_vocabulary_tags(text),
        "chunk_tags": infer_chunk_tags(text),
    }


def infer_pedagogical_tags(content_unit_tags: dict[str, Any], audio_valid: bool = False) -> dict[str, Any]:
    sentence_count = int(content_unit_tags.get("sentence_count") or 1)
    has_direct_speech = bool(content_unit_tags.get("has_direct_speech") or content_unit_tags.get("is_direct_speech"))
    is_heading = bool(content_unit_tags.get("is_heading"))

    skill_area: set[str] = {"reading", "vocabulary"}
    question_types: set[str] = {"reading_comprehension"}

    if not is_heading:
        skill_area.add("grammar")
        question_types.update({"fill_blank", "word_ordering"})

    if sentence_count >= 2:
        skill_area.update({"comprehension", "retelling"})
        question_types.update({"sentence_ordering", "short_answer", "retelling_prompt"})

    if has_direct_speech:
        skill_area.add("speaking")
        question_types.add("speaking_response")

    if audio_valid:
        skill_area.add("listening")
        question_types.update({"listening_choice", "dictation"})

    return {
        "skill_area": sorted(skill_area),
        "question_type_candidates": sorted(question_types),
        "exercise_seed": not is_heading,
        "assessment_seed": not is_heading,
    }


def infer_reuse_tags(content_unit_tags: dict[str, Any], level: str, audio_valid: bool = False) -> dict[str, Any]:
    sentence_count = int(content_unit_tags.get("sentence_count") or 1)
    has_direct_speech = bool(content_unit_tags.get("has_direct_speech") or content_unit_tags.get("is_direct_speech"))
    is_heading = bool(content_unit_tags.get("is_heading"))
    tags: set[str] = {"future_unknown_use"}
    potential = {
        "short_reading": "none",
        "writing_model": "none",
        "dialogue_rewrite": "none",
        "exercise_generation": "possible",
        "listening_audio": "possible" if audio_valid else "unknown",
    }

    if not is_heading:
        tags.update({"exercise_seed", "vocabulary_exposure_seed", "grammar_pattern_seed"})
    if level in {"A", "B"} and not is_heading:
        tags.add("picture_prompt_seed")
    if sentence_count >= 2:
        tags.update({"short_reading_seed", "sequencing_seed", "comprehension_question_seed", "retelling_seed", "assessment_seed"})
        potential["short_reading"] = "high"
        potential["writing_model"] = "medium"
        potential["exercise_generation"] = "high"
    if has_direct_speech:
        tags.add("dialogue_rewrite_seed")
        potential["dialogue_rewrite"] = "possible"
    if audio_valid:
        tags.add("listening_audio_seed")

    return {
        "is_reusable_unit": bool(tags),
        "reusability_tags": sorted(tags),
        "derivation_potential": potential,
    }


def infer_audio_valid(candidate: dict[str, Any]) -> bool:
    trace = candidate.get("audio_trace") or {}
    start = trace.get("cue_start_ms")
    end = trace.get("cue_end_ms")
    return isinstance(start, int) and isinstance(end, int) and end > start >= 0


def make_source_tags(raw: dict[str, Any], candidate: dict[str, Any] | None, raw_file_path: str) -> dict[str, Any]:
    metadata = raw.get("book_metadata") or {}
    return {
        "source": "RAZ",
        "source_type": raw.get("source_type"),
        "extraction_method": raw.get("extraction_method"),
        "extractor_version": raw.get("extractor_version"),
        "raz_level": metadata.get("level") or (candidate or {}).get("level"),
        "book_id": str(metadata.get("book_id") or (candidate or {}).get("book_id") or ""),
        "book_title": metadata.get("title") or (candidate or {}).get("title"),
        "page_number": (candidate or {}).get("page_number"),
        "page_unit_id": (candidate or {}).get("page_unit_id"),
        "candidate_id": (candidate or {}).get("candidate_id"),
        "raw_file_path": raw_file_path,
    }


def make_qa_tags(
    *,
    record_id: str,
    content_unit_tags: dict[str, Any],
    theme_tags: dict[str, Any],
    linguistic_tags: dict[str, Any] | None,
    warnings: list[WarningRecord],
    level: str,
    book_id: str,
    raw_file_path: str,
) -> dict[str, Any]:
    warning_labels: list[str] = []
    is_heading = bool(content_unit_tags.get("is_heading") or content_unit_tags.get("content_unit_type") == "section_heading")

    if is_heading:
        warning_labels.append("section_heading_detected")
        append_warning_record(
            warnings,
            warning_type="section_heading_detected",
            severity="warn",
            record_id=record_id,
            message="Text looks like a nonfiction heading and is not sentence authority eligible by default.",
            level=level,
            book_id=book_id,
            raw_file_path=raw_file_path,
        )

    theme_confidence = float(theme_tags.get("theme_confidence") or 0.0)
    if theme_tags.get("mapped_theme") == "Unknown":
        warning_labels.append("unknown_theme")
        append_warning_record(
            warnings,
            warning_type="unknown_theme",
            severity="warn",
            record_id=record_id,
            message="Theme could not be confidently mapped.",
            level=level,
            book_id=book_id,
            raw_file_path=raw_file_path,
        )
    elif theme_confidence < 0.55:
        warning_labels.append("low_theme_confidence")
        append_warning_record(
            warnings,
            warning_type="low_theme_confidence",
            severity="warn",
            record_id=record_id,
            message=f"Theme confidence is low: {theme_confidence}.",
            level=level,
            book_id=book_id,
            raw_file_path=raw_file_path,
        )

    grammar_confidence = 0.55
    pattern_confidence = 0.55
    if linguistic_tags:
        grammar_tags = set(linguistic_tags.get("grammar_tags") or [])
        pattern_tags = linguistic_tags.get("sentence_pattern_tags") or []
        grammar_confidence = 0.58 if "unknown_grammar" in grammar_tags else 0.82
        pattern_confidence = 0.68 if pattern_tags else 0.4
        if "unknown_grammar" in grammar_tags:
            warning_labels.append("unknown_grammar")
            append_warning_record(
                warnings,
                warning_type="unknown_grammar",
                severity="info",
                record_id=record_id,
                message="No specific grammar tag was inferred by S4 rule-based tagger.",
                level=level,
                book_id=book_id,
                raw_file_path=raw_file_path,
            )
        if not pattern_tags:
            warning_labels.append("unknown_pattern")
            append_warning_record(
                warnings,
                warning_type="unknown_pattern",
                severity="info",
                record_id=record_id,
                message="No sentence pattern tag was confidently inferred by S4 rule-based tagger.",
                level=level,
                book_id=book_id,
                raw_file_path=raw_file_path,
            )

    needs_human_review = is_heading or theme_tags.get("mapped_theme") == "Unknown"
    review_status = "human_review_required" if needs_human_review else "pending"
    if needs_human_review:
        append_warning_record(
            warnings,
            warning_type="human_review_required",
            severity="warn",
            record_id=record_id,
            message="Record requires human review due to QA warning flags.",
            level=level,
            book_id=book_id,
            raw_file_path=raw_file_path,
        )

    return {
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
        "review_status": review_status,
        "tagging_status": "auto_tagged",
        "needs_human_review": needs_human_review,
        "final_eligible": False,
        "confidence": {
            "content_unit_type": 0.95,
            "theme": theme_confidence,
            "grammar": grammar_confidence,
            "vocabulary": 0.72,
            "pattern": pattern_confidence,
        },
        "warnings": warning_labels,
    }


def join_sentence_texts(sentence_ids: Iterable[str], candidate_by_id: dict[str, dict[str, Any]]) -> str:
    texts: list[str] = []
    for candidate_id in sentence_ids:
        text = normalize_spacing((candidate_by_id.get(candidate_id) or {}).get("cleaned_candidate"))
        if text:
            texts.append(text)
    return "\n".join(texts)


def normalized_sentence_record(raw: dict[str, Any], candidate: dict[str, Any], raw_file_path: str) -> dict[str, Any]:
    source_tags = make_source_tags(raw, candidate, raw_file_path)
    return {
        "candidate_id": candidate.get("candidate_id"),
        "source_page_unit_id": candidate.get("page_unit_id"),
        "text": normalize_spacing(candidate.get("cleaned_candidate")),
        "word_count": candidate.get("word_count"),
        "candidate_order": candidate.get("candidate_order"),
        "text_type": candidate.get("text_type"),
        "source_tags": source_tags,
        "source_traceability": strip_audio_keys(candidate.get("source_traceability") or {}),
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
        "review_status": "pending",
    }


def enrich_sentence(raw: dict[str, Any], candidate: dict[str, Any], raw_file_path: str, warnings: list[WarningRecord]) -> dict[str, Any]:
    level = str((raw.get("book_metadata") or {}).get("level") or candidate.get("level") or "")
    book_id = str((raw.get("book_metadata") or {}).get("book_id") or candidate.get("book_id") or "")
    title = str((raw.get("book_metadata") or {}).get("title") or candidate.get("title") or "")
    text = normalize_spacing(candidate.get("cleaned_candidate"))
    source_tags = make_source_tags(raw, candidate, raw_file_path)
    content_unit_tags = infer_content_unit_tags_for_sentence(text)
    theme_tags = infer_theme(text, title)
    linguistic_tags = infer_linguistic_tags(text, level, content_unit_tags)
    audio_valid = infer_audio_valid(candidate)
    pedagogical_tags = infer_pedagogical_tags(content_unit_tags, audio_valid=audio_valid)
    reuse_tags = infer_reuse_tags(content_unit_tags, level, audio_valid=audio_valid)
    qa_tags = make_qa_tags(
        record_id=str(candidate.get("candidate_id")),
        content_unit_tags=content_unit_tags,
        theme_tags=theme_tags,
        linguistic_tags=linguistic_tags,
        warnings=warnings,
        level=level,
        book_id=book_id,
        raw_file_path=raw_file_path,
    )

    return {
        "candidate_id": candidate.get("candidate_id"),
        "source_page_unit_id": candidate.get("page_unit_id"),
        "text": text,
        "source_tags": source_tags,
        "content_unit_tags": content_unit_tags,
        "theme_tags": theme_tags,
        "linguistic_tags": linguistic_tags,
        "pedagogical_tags": pedagogical_tags,
        "reuse_tags": reuse_tags,
        "qa_tags": qa_tags,
    }


def normalize_page_unit(
    raw: dict[str, Any],
    page_unit: dict[str, Any],
    candidate_by_id: dict[str, dict[str, Any]],
    raw_file_path: str,
) -> dict[str, Any]:
    metadata = raw.get("book_metadata") or {}
    sentence_ids = list(page_unit.get("sentence_candidate_ids") or page_unit.get("source_sentence_candidate_ids") or [])
    if not sentence_ids:
        page_unit_id = page_unit.get("page_unit_id")
        sentence_ids = [
            cid for cid, candidate in candidate_by_id.items()
            if candidate.get("page_unit_id") == page_unit_id
        ]
    text = normalize_spacing(page_unit.get("clean_text") or page_unit.get("text"))
    if not text:
        text = join_sentence_texts(sentence_ids, candidate_by_id)
    return {
        "page_unit_id": page_unit.get("page_unit_id"),
        "book_id": str(page_unit.get("book_id") or metadata.get("book_id") or ""),
        "level": page_unit.get("level") or metadata.get("level"),
        "title": page_unit.get("title") or metadata.get("title"),
        "page_number": page_unit.get("page_number"),
        "sentence_candidate_ids": sentence_ids,
        "sentence_count": int(page_unit.get("sentence_count") or len(sentence_ids) or 0),
        "text": text,
        "source_tags": {
            "source": "RAZ",
            "source_type": raw.get("source_type"),
            "extraction_method": raw.get("extraction_method"),
            "extractor_version": raw.get("extractor_version"),
            "raz_level": page_unit.get("level") or metadata.get("level"),
            "book_id": str(page_unit.get("book_id") or metadata.get("book_id") or ""),
            "book_title": page_unit.get("title") or metadata.get("title"),
            "page_number": page_unit.get("page_number"),
            "page_unit_id": page_unit.get("page_unit_id"),
            "raw_file_path": raw_file_path,
        },
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
        "review_status": "pending",
    }


def enrich_page_unit(normalized: dict[str, Any], warnings: list[WarningRecord]) -> dict[str, Any]:
    level = str(normalized.get("level") or "")
    book_id = str(normalized.get("book_id") or "")
    title = str(normalized.get("title") or "")
    record_id = str(normalized.get("page_unit_id"))
    raw_file_path = str((normalized.get("source_tags") or {}).get("raw_file_path") or "")
    content_unit_tags = infer_content_unit_tags_for_page(normalized.get("text") or "", int(normalized.get("sentence_count") or 0))
    theme_tags = infer_theme(str(normalized.get("text") or ""), title)
    pedagogical_tags = infer_pedagogical_tags(content_unit_tags, audio_valid=False)
    reuse_tags = infer_reuse_tags(content_unit_tags, level, audio_valid=False)
    qa_tags = make_qa_tags(
        record_id=record_id,
        content_unit_tags=content_unit_tags,
        theme_tags=theme_tags,
        linguistic_tags=None,
        warnings=warnings,
        level=level,
        book_id=book_id,
        raw_file_path=raw_file_path,
    )
    return {
        **normalized,
        "content_unit_tags": content_unit_tags,
        "theme_tags": theme_tags,
        "pedagogical_tags": pedagogical_tags,
        "reuse_tags": reuse_tags,
        "qa_tags": qa_tags,
    }


def normalize_reuse_unit(
    raw: dict[str, Any],
    reuse_unit: dict[str, Any],
    candidate_by_id: dict[str, dict[str, Any]],
    raw_file_path: str,
    fallback_index: int,
) -> dict[str, Any]:
    metadata = raw.get("book_metadata") or {}
    source_page_unit_id = reuse_unit.get("source_page_unit_id") or reuse_unit.get("page_unit_id")
    sentence_ids = list(reuse_unit.get("source_sentence_candidate_ids") or reuse_unit.get("sentence_candidate_ids") or [])
    text = normalize_spacing(reuse_unit.get("clean_text") or reuse_unit.get("text"))
    if not text and sentence_ids:
        text = join_sentence_texts(sentence_ids, candidate_by_id)
    reuse_unit_id = reuse_unit.get("reuse_unit_id") or f"RAZ_{metadata.get('level')}_{metadata.get('book_id')}_REUSE_{fallback_index:06d}"
    page_number = reuse_unit.get("page_number")
    if page_number is None and sentence_ids:
        page_number = (candidate_by_id.get(sentence_ids[0]) or {}).get("page_number")
    return {
        "reuse_unit_id": reuse_unit_id,
        "source_page_unit_id": source_page_unit_id,
        "book_id": str(reuse_unit.get("book_id") or metadata.get("book_id") or ""),
        "level": reuse_unit.get("level") or metadata.get("level"),
        "title": reuse_unit.get("title") or metadata.get("title"),
        "page_number": page_number,
        "source_sentence_candidate_ids": sentence_ids,
        "clean_text": text,
        "sentence_count": int(reuse_unit.get("sentence_count") or len(sentence_ids) or 0),
        "source_tags": {
            "source": "RAZ",
            "source_type": raw.get("source_type"),
            "extraction_method": raw.get("extraction_method"),
            "extractor_version": raw.get("extractor_version"),
            "raz_level": reuse_unit.get("level") or metadata.get("level"),
            "book_id": str(reuse_unit.get("book_id") or metadata.get("book_id") or ""),
            "book_title": reuse_unit.get("title") or metadata.get("title"),
            "page_number": page_number,
            "page_unit_id": source_page_unit_id,
            "raw_file_path": raw_file_path,
        },
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
        "review_status": "pending",
    }


def enrich_reuse_unit(normalized: dict[str, Any], warnings: list[WarningRecord]) -> dict[str, Any]:
    level = str(normalized.get("level") or "")
    book_id = str(normalized.get("book_id") or "")
    title = str(normalized.get("title") or "")
    record_id = str(normalized.get("reuse_unit_id"))
    raw_file_path = str((normalized.get("source_tags") or {}).get("raw_file_path") or "")
    content_unit_tags = infer_content_unit_tags_for_page(normalized.get("clean_text") or "", int(normalized.get("sentence_count") or 0))
    content_unit_tags["content_unit_type"] = "reuse_unit"
    theme_tags = infer_theme(str(normalized.get("clean_text") or ""), title)
    pedagogical_tags = infer_pedagogical_tags(content_unit_tags, audio_valid=False)
    reuse_tags = infer_reuse_tags(content_unit_tags, level, audio_valid=False)
    qa_tags = make_qa_tags(
        record_id=record_id,
        content_unit_tags=content_unit_tags,
        theme_tags=theme_tags,
        linguistic_tags=None,
        warnings=warnings,
        level=level,
        book_id=book_id,
        raw_file_path=raw_file_path,
    )
    return {
        **normalized,
        "content_unit_tags": content_unit_tags,
        "theme_tags": theme_tags,
        "pedagogical_tags": pedagogical_tags,
        "reuse_tags": reuse_tags,
        "qa_tags": qa_tags,
    }


def process_raw_file(path: Path, input_root: Path, result: PipelineResult) -> None:
    raw = json.loads(path.read_text(encoding="utf-8"))
    metadata = raw.get("book_metadata") or {}
    level = str(metadata.get("level") or "Unknown")
    book_id = str(metadata.get("book_id") or path.stem)
    title = str(metadata.get("title") or "")
    raw_file_path = path.relative_to(input_root.parent).as_posix() if input_root.parent in path.parents else path.as_posix()
    candidates = list(raw.get("sentence_candidates") or [])
    page_units = list(raw.get("page_units") or [])
    reuse_units = list(raw.get("reuse_unit_candidates") or [])
    candidate_by_id = {str(c.get("candidate_id")): c for c in candidates if c.get("candidate_id")}

    result.raw_files_seen += 1

    sentence_heading_count = 0
    for candidate in candidates:
        normalized = normalized_sentence_record(raw, candidate, raw_file_path)
        enriched = enrich_sentence(raw, candidate, raw_file_path, result.warnings)
        if enriched["content_unit_tags"].get("is_heading"):
            sentence_heading_count += 1
        result.normalized_sentences[level].append(normalized)
        result.sentence_enriched[level].append(enriched)

    for page_unit in page_units:
        normalized_page = normalize_page_unit(raw, page_unit, candidate_by_id, raw_file_path)
        result.normalized_page_units[level].append(normalized_page)
        result.page_unit_enriched[level].append(enrich_page_unit(normalized_page, result.warnings))

    for index, reuse_unit in enumerate(reuse_units, 1):
        normalized_reuse = normalize_reuse_unit(raw, reuse_unit, candidate_by_id, raw_file_path, index)
        result.normalized_reuse_units[level].append(normalized_reuse)
        result.reuse_unit_enriched[level].append(enrich_reuse_unit(normalized_reuse, result.warnings))

    result.by_book.append({
        "level": level,
        "book_id": book_id,
        "title": title,
        "raw_file_path": raw_file_path,
        "sentence_candidate_count": len(candidates),
        "page_unit_count": len(page_units),
        "reuse_unit_count": len(reuse_units),
        "section_heading_candidate_count": sentence_heading_count,
    })


def discover_raw_files(
    input_root: Path,
    levels: list[str] | None,
    limit_per_level: int | None,
    derived_root: Path | None = None,
) -> list[Path]:
    if levels:
        level_dirs = [input_root / f"Level_{level}" for level in levels]
    else:
        discovery_rows = level_discovery.discover_raz_levels(
            raw_root=input_root,
            derived_root=derived_root or (input_root / "derived"),
        )
        discovered_levels = [
            row["normalized_level"]
            for row in discovery_rows
            if row.get("normalized_level")
            and row.get("pipeline_capabilities", {}).get("can_build_sentence_candidates") is True
            and row.get("status") != level_discovery.INVALID_FORMAT
        ]
        level_dirs = [input_root / f"Level_{level}" for level in discovered_levels]

    files: list[Path] = []
    for level_dir in level_dirs:
        level_files = sorted(level_dir.glob("raz_*_audio_timeline_extract.json"))
        if limit_per_level is not None:
            level_files = level_files[:limit_per_level]
        files.extend(level_files)
    return files


def validate_records(result: PipelineResult) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    checked = Counter()

    def add_error(record_id: str, error_type: str, message: str) -> None:
        errors.append({
            "record_id": record_id,
            "error_type": error_type,
            "message": message,
        })

    for level, records in result.sentence_enriched.items():
        for record in records:
            checked["sentence_enriched"] += 1
            record_id = str(record.get("candidate_id"))
            if has_forbidden_audio_keys(record):
                add_error(record_id, "audio_field_present_in_enriched_output", "Audio fields are forbidden in sentence_enriched output.")
            content_type = (record.get("content_unit_tags") or {}).get("content_unit_type")
            if content_type not in CONTENT_UNIT_TYPES:
                add_error(record_id, "invalid_content_unit_type", f"Invalid content_unit_type: {content_type}")
            mapped_theme = (record.get("theme_tags") or {}).get("mapped_theme")
            if mapped_theme not in MAPPED_THEMES:
                add_error(record_id, "invalid_mapped_theme", f"Invalid mapped_theme: {mapped_theme}")
            qa = record.get("qa_tags") or {}
            if qa.get("authority_status") != "candidate_only":
                add_error(record_id, "promotion_not_allowed", "S4 must keep authority_status=candidate_only.")
            for skill in (record.get("pedagogical_tags") or {}).get("skill_area") or []:
                if skill not in SKILL_AREAS:
                    add_error(record_id, "invalid_skill_area", f"Invalid skill_area: {skill}")
            for question_type in (record.get("pedagogical_tags") or {}).get("question_type_candidates") or []:
                if question_type not in QUESTION_TYPES:
                    add_error(record_id, "invalid_question_type", f"Invalid question_type: {question_type}")
            for tag in (record.get("reuse_tags") or {}).get("reusability_tags") or []:
                if tag not in REUSABILITY_TAGS:
                    add_error(record_id, "invalid_reusability_tag", f"Invalid reusability_tag: {tag}")

    for level, records in result.page_unit_enriched.items():
        for record in records:
            checked["page_unit_enriched"] += 1
            record_id = str(record.get("page_unit_id"))
            if has_forbidden_audio_keys(record):
                add_error(record_id, "audio_field_present_in_enriched_output", "Audio fields are forbidden in page_unit_enriched output.")
            if not record.get("sentence_candidate_ids"):
                add_error(record_id, "page_unit_link_missing", "Page unit has no sentence_candidate_ids.")

    for level, records in result.reuse_unit_enriched.items():
        for record in records:
            checked["reuse_unit_enriched"] += 1
            record_id = str(record.get("reuse_unit_id"))
            if has_forbidden_audio_keys(record):
                add_error(record_id, "audio_field_present_in_enriched_output", "Audio fields are forbidden in reuse_unit_enriched output.")
            if not record.get("source_page_unit_id"):
                add_error(record_id, "reuse_unit_link_missing", "Reuse unit has no source_page_unit_id.")

    return {
        "status": "PASS" if not errors else "FAIL",
        "checked": dict(checked),
        "error_count": len(errors),
        "errors": errors,
    }


def build_summary(result: PipelineResult, input_root: Path, output_root: Path, dry_run: bool) -> dict[str, Any]:
    by_level: dict[str, dict[str, Any]] = {}
    levels = sorted(set(result.sentence_enriched) | set(result.page_unit_enriched) | set(result.reuse_unit_enriched))
    for level in levels:
        headings = sum(
            1 for record in result.sentence_enriched[level]
            if (record.get("content_unit_tags") or {}).get("is_heading")
        )
        by_level[level] = {
            "sentence_enriched_count": len(result.sentence_enriched[level]),
            "page_unit_enriched_count": len(result.page_unit_enriched[level]),
            "reuse_unit_enriched_count": len(result.reuse_unit_enriched[level]),
            "section_heading_candidate_count": headings,
        }

    return {
        "task": "RAZ-S4_NormalizedTextAndTaggingPipeline_Implementation",
        "generated_at": utc_now_iso(),
        "dry_run": dry_run,
        "input_root": str(input_root),
        "output_root": str(output_root),
        "raw_files_seen": result.raw_files_seen,
        "totals": {
            "sentence_enriched_count": sum(len(v) for v in result.sentence_enriched.values()),
            "page_unit_enriched_count": sum(len(v) for v in result.page_unit_enriched.values()),
            "reuse_unit_enriched_count": sum(len(v) for v in result.reuse_unit_enriched.values()),
            "warning_count": len(result.warnings),
        },
        "by_level": by_level,
        "by_book": result.by_book,
        "authority_status": "candidate_only",
        "raw_mutation": False,
        "audio_policy": "audio_fields_removed_from_normalized_and_enriched_text_outputs",
    }


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + ("\n" if records else ""), encoding="utf-8")


def write_outputs(result: PipelineResult, output_root: Path, summary: dict[str, Any], validation: dict[str, Any]) -> None:
    for level in sorted(result.sentence_enriched):
        level_root = output_root / f"Level_{level}"
        write_jsonl(level_root / "normalized" / f"raz_{level}_sentence_normalized.jsonl", result.normalized_sentences[level])
        write_json(level_root / "normalized" / f"raz_{level}_page_unit_normalized.json", result.normalized_page_units[level])
        write_json(level_root / "normalized" / f"raz_{level}_reuse_unit_normalized.json", result.normalized_reuse_units[level])
        write_jsonl(level_root / "enriched" / f"raz_{level}_sentence_enriched.jsonl", result.sentence_enriched[level])
        write_json(level_root / "enriched" / f"raz_{level}_page_unit_enriched.json", result.page_unit_enriched[level])
        write_json(level_root / "enriched" / f"raz_{level}_reuse_unit_enriched.json", result.reuse_unit_enriched[level])

    reports_root = output_root / "reports"
    write_json(reports_root / "raz_tagging_summary.json", summary)
    write_json(reports_root / "raz_tagging_warnings.json", [warning.as_dict() for warning in result.warnings])
    write_json(reports_root / "raz_tagging_schema_validation.json", validation)


def run_pipeline(
    *,
    input_root: Path,
    output_root: Path,
    levels: list[str] | None = None,
    limit_per_level: int | None = None,
    dry_run: bool = False,
) -> tuple[PipelineResult, dict[str, Any], dict[str, Any]]:
    result = PipelineResult()
    raw_files = discover_raw_files(input_root, levels, limit_per_level, derived_root=output_root)
    for path in raw_files:
        process_raw_file(path, input_root, result)
    validation = validate_records(result)
    summary = build_summary(result, input_root, output_root, dry_run)
    if not dry_run:
        write_outputs(result, output_root, summary, validation)
    return result, summary, validation


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build RAZ normalized and enriched tagging outputs.")
    parser.add_argument("--input-root", default="raz_output_jsons", help="Root containing Level_A, Level_B, ... raw folders.")
    parser.add_argument("--output-root", default="raz_output_jsons/derived", help="Derived output root.")
    parser.add_argument("--levels", nargs="*", help="Optional levels to process, e.g. A B C.")
    parser.add_argument("--limit-per-level", type=int, default=None, help="Optional cap for smoke testing.")
    parser.add_argument("--dry-run", action="store_true", help="Process and validate without writing derived files.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_root = Path(args.input_root)
    output_root = Path(args.output_root)
    levels = [level.upper() for level in args.levels] if args.levels else None
    result, summary, validation = run_pipeline(
        input_root=input_root,
        output_root=output_root,
        levels=levels,
        limit_per_level=args.limit_per_level,
        dry_run=args.dry_run,
    )
    print(json.dumps({
        "summary": summary,
        "validation": {
            "status": validation["status"],
            "error_count": validation["error_count"],
        },
        "warning_count": len(result.warnings),
    }, ensure_ascii=False, indent=2))
    return 0 if validation["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
