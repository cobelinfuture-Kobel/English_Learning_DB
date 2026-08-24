from pathlib import Path

PROGRAM_ID = "A1FS-V1"
UNIT_ID = "GRAMMAR_REGULAR_PLURAL_NOUNS"
TASK_ID = "A1FS-V1-U02SA01R1_PR536FullSentenceProductionSemanticAdmissionAndCumulativeCloseout"
SCHEMA_VERSION = "a1fs.v1.u02sa01r1.dynamic_authority_sentence_production.v2"
PASS_STATUS = "PASS_A1FS_V1_U02SA01R1_DYNAMIC_AUTHORITY_SENTENCE_PRODUCTION_CLOSEOUT"
DECISION_REF = "OPERATOR_APPROVAL:2026-08-24:U02SA01R1_DYNAMIC_AUTHORITY_FINAL_CLOSEOUT"
NEXT_SHORT_STEP = "A1FS-V1-U02QB03_Unit02CumulativeQuestionBankRuntimeIntegration"

REPO_ROOT = Path(__file__).resolve().parents[3]
SAFE_MANIFEST_SHARD_PATHS = tuple(
    REPO_ROOT / f"ulga/reports/a1fs_v1_u02sa01r1_safe_production_seed_manifest.b64.part{i}"
    for i in range(1, 5)
)
VOCABULARY_PATH = REPO_ROOT / "vocabulary/json/vocabulary.json"

UNIT01_SENTENCE_POOL_SHA256 = "a4c33d7c2a460ad5a81397d7ab184b682bc456359fae7c286d168c352258835d"
UNIT01_DEFER_SHA256 = "1ba08c6afcc20fb78b43f8d5d96def768f77b1e6d4bbf28830efea86aa07136a"
CAMBRIDGE_YLE_SHA256 = "1bc0ceb3453251a119faea8dbe39ea5d7251f84e5820f9475ffd8773a597e2f4"
VOCABULARY_GIT_BLOB_SHA = "f2194583cea4d6128b80fafec6c07df2bb2efe3b"

EXPECTED_UNIT01_SENTENCE_ASSETS = 3805
EXPECTED_UNIT01_EXACT_TEXT_IDENTITIES = 3529
EXPECTED_UNIT01_NORMALIZED_TEXT_IDENTITIES = 3529
EXPECTED_U02_PLAIN_S_TARGETS = 162
EXPECTED_U02_NATIVE_CHUNKS = 26
EXPECTED_NEW_PATTERN_IDS = ("SP_000003", "SP_000004", "SP_000005", "SP_000013")
INHERITED_PLURAL_PATTERN_ID = "SP_000002"
PATTERN_TEMPLATES = {
    INHERITED_PLURAL_PATTERN_ID: "I can see {np}.",
    "SP_000003": "I have {np}.",
    "SP_000004": "I like {np}.",
    "SP_000005": "I don't like {np}.",
    "SP_000013": "Can I have {np}?",
}
CHILD_CONTEXT_RESTRICTED_MORPHOLOGY_TARGETS = ("beer",)
CHILD_CONTEXT_RESTRICTED = {"beer", "wine"}
COUNTABILITY_OR_SENSE_REVIEW = {
    "air", "bread", "breakfast", "butter", "cheese", "clothes", "dinner", "food", "fruit", "fun",
    "grass", "hair", "homework", "information", "meat", "milk", "money", "music", "paint", "people",
    "rain", "rice", "salt", "shopping", "snow", "sugar", "water", "weather", "wind", "work",
}
PROPER_OR_TIME_NAME_REVIEW = {
    "april", "august", "december", "february", "friday", "january", "july", "june", "march", "may",
    "monday", "november", "october", "saturday", "september", "sunday", "thursday", "today", "tomorrow",
    "tuesday", "wednesday",
}
NON_POSSESSABLE_FOR_CHILD_I_HAVE = {
    "airport", "bank", "bridge", "building", "bus station", "bus stop", "café", "castle", "cinema", "college",
    "country", "countryside", "course", "farm", "hospital", "hotel", "library", "mountain", "museum", "park",
    "river", "road", "school", "sea", "station", "street", "sun", "town", "village", "zoo",
}
NON_REQUESTABLE_FOR_CAN_I_HAVE = {
    "adult", "animal", "bank", "bathroom", "beard", "bedroom", "beer", "boy", "brother", "café", "cinema",
    "conversation", "course", "cow", "dad", "daughter", "ear", "end", "eye", "face", "farm", "father", "film",
    "floor", "friend", "garden", "girl", "group", "hand", "head", "home", "horse", "house", "husband", "job",
    "kitchen", "language", "leg", "lesson", "living room", "mother", "mouth", "museum", "mum", "name", "nose",
    "parent", "park", "person", "place", "player", "question", "river", "road", "room", "school", "sea", "sentence",
    "sister", "son", "station", "street", "student", "subject", "sun", "teacher", "toilet", "town", "tree", "village",
    "wife", "wine", "woman", "word", "zoo",
}
