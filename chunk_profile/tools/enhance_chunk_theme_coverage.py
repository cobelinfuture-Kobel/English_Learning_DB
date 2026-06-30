import os
import json
import re

def main():
    # Define directories
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_dir = os.path.join(base_dir, "json")
    reports_dir = os.path.join(base_dir, "reports")
    
    # Input paths
    safe_chunks_path = os.path.join(json_dir, "chunks_generator_safe.json")
    original_mapping_path = os.path.join(json_dir, "chunk_theme_hint_mapping.json")
    usage_class_path = os.path.join(json_dir, "chunk_usage_class_mapping.json")
    priority_path = os.path.join(json_dir, "chunk_priority_mapping.json")
    chunks_path = os.path.join(json_dir, "chunks.json")
    
    # Load inputs
    with open(safe_chunks_path, "r", encoding="utf-8") as f:
        safe_chunks = json.load(f)
    with open(original_mapping_path, "r", encoding="utf-8") as f:
        original_theme_mapping = json.load(f)
    with open(usage_class_path, "r", encoding="utf-8") as f:
        usage_class_mapping = json.load(f)
    with open(priority_path, "r", encoding="utf-8") as f:
        priority_mapping = json.load(f)
    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)
        
    print(f"Loaded {len(safe_chunks)} safe chunks and {len(chunks)} raw chunks.")
    
    # Theme Set
    THEME_SET = ["Personal", "DailyRoutine", "School", "Home", "Shopping", "Food", "Hobbies", "Travel", "Health", "General"]

    # Lexical patterns definition
    lexical_patterns = {
        "Food": [
            "food", "drink", "beverage", "eat", "consume", "taste", "smell", "cook", "bake", "fry", "boil", "steam", 
            "grill", "roast", "prepare", "serve", "restaurant", "cafe", "pub", "bar", "canteen", "kitchen", "menu", 
            "bill", "tip", "chef", "cooker", "waiter", "waitress", "guest", "meal", "breakfast", "brunch", "lunch", 
            "dinner", "supper", "snack", "picnic", "feast", "recipe", "ingredients", "water", "milk", "juice", "tea", 
            "coffee", "soda", "coke", "lemonade", "beer", "wine", "alcohol", "bread", "butter", "cheese", "egg", 
            "potato", "tomato", "onion", "garlic", "rice", "pasta", "noodle", "soup", "salad", "sandwich", "burger", 
            "pizza", "meat", "beef", "pork", "chicken", "fish", "seafood", "fruit", "apple", "banana", "orange", 
            "lemon", "strawberry", "grape", "peach", "pear", "vegetable", "carrot", "cabbage", "lettuce", "cucumber", 
            "pepper", "salt", "sugar", "honey", "chocolate", "cake", "cookie", "ice cream", "dessert", "sweet", "candy"
        ],
        "Home": [
            "home", "house", "room", "bedroom", "bathroom", "kitchen", "living room", "dining room", "bed", "chair", 
            "table", "sofa", "door", "window", "wall", "floor", "garden", "garage", "upstairs", "downstairs", "flat", 
            "apartment", "rent", "building", "roof", "stairs", "ceiling", "carpet", "curtain", "mirror", "desk", 
            "clock", "lamp", "light", "shower", "bath", "toilet", "sink", "fridge", "oven", "stove", "washing machine", 
            "heating", "key", "lock", "gate", "yard", "chimney", "balcony", "basement", "attic", "furniture", 
            "cushion", "sheet", "blanket", "towel", "soap", "fire"
        ],
        "School": [
            "school", "classroom", "class", "lesson", "homework", "exam", "test", "grade", "mark", "score", 
            "teacher", "student", "pupil", "principal", "professor", "lecturer", "tutor", "subject", "math", 
            "mathematics", "science", "physics", "chemistry", "biology", "history", "geography", "literature", 
            "language", "grammar", "vocabulary", "spelling", "pronunciation", "dictionary", "encyclopedia", "book", 
            "textbook", "notebook", "paper", "page", "pencil", "pen", "ruler", "eraser", "desk", "chair", "blackboard", 
            "whiteboard", "marker", "chalk", "computer", "laptop", "calculator", "library", "laboratory", "gym", 
            "playground", "university", "college", "academy", "course", "degree", "diploma", "certificate", 
            "scholarship", "term", "semester", "break", "read", "write", "spell", "learn", "study", "translate", "practice",
            "noun", "verb", "adjective", "adverb", "pronoun", "preposition", "conjunction", "interjection", "tense", 
            "singular", "plural", "sentence", "phrase", "clause", "paragraph", "syllable", "alphabet", "letter",
            "force", "army", "navy", "police", "officer", "soldier", "guard", "law", "rights", "court", "judge", "legal",
            "intelligence", "intelligent", "intellectual", "sense", "reason", "logic", "effect", "affect", "impact",
            "symbol", "sign", "mark"
        ],
        "Travel": [
            "bus", "train", "car", "taxi", "plane", "airport", "station", "ticket", "passport", "hotel", "map", 
            "road", "street", "trip", "journey", "travel", "traffic", "transport", "go to", "get to", "get on", 
            "get off", "flight", "bicycle", "bike", "motorcycle", "subway", "metro", "underground", "tram", 
            "helicopter", "truck", "van", "lorry", "drive", "ride", "fly", "sail", "passenger", "driver", "pilot", 
            "luggage", "baggage", "suitcase", "route", "direction", "north", "south", "east", "west", "tour", 
            "tourist", "vacation", "holiday", "reservation", "booking", "check in", "check out", "departure", 
            "arrival", "visit", "abroad", "foreign", "destination", "boat", "ship", "ferry", "yacht", "sailing"
        ],
        "Health": [
            "doctor", "nurse", "dentist", "pharmacist", "surgeon", "patient", "hospital", "clinic", "pharmacy", 
            "surgery", "medicine", "drug", "pill", "tablet", "capsule", "syrup", "ointment", "bandage", "plaster", 
            "injection", "prescription", "treatment", "cure", "therapy", "operation", "health", "illness", "disease", 
            "sickness", "infection", "virus", "bacteria", "flu", "cold", "cough", "sneeze", "fever", "temperature", 
            "pain", "ache", "headache", "toothache", "stomach ache", "earache", "backache", "sore throat", "dizzy", 
            "sick", "ill", "weak", "tired", "exhausted", "blind", "deaf", "injured", "wounded", "broken", "cut", 
            "bruise", "bleed", "blood", "heart", "lungs", "stomach", "brain", "bones", "muscles", "skin", "body", 
            "head", "face", "eye", "ear", "nose", "mouth", "tooth", "teeth", "neck", "shoulder", "arm", "hand", 
            "finger", "leg", "foot", "feet", "toe", "chest", "back", "throat", "knee", "elbow", "wrist", "ankle", 
            "breath", "breathe", "breathless", "pressure"
        ],
        "Shopping": [
            "shop", "store", "market", "supermarket", "mall", "shopping center", "price", "cost", "value", "money", 
            "cash", "coin", "bill", "note", "credit card", "debit card", "wallet", "purse", "pocket", "buy", "purchase", 
            "sell", "pay", "spend", "save", "lend", "borrow", "expensive", "cheap", "free", "sale", "discount", 
            "receipt", "refund", "exchange", "guarantee", "customer", "buyer", "seller", "cashier", "clerk", "brand", 
            "size", "color", "style", "clothes", "clothing", "wear", "try on", "fit", "suit", "shirt", "t-shirt", 
            "blouse", "top", "sweater", "jumper", "jacket", "coat", "suit", "dress", "skirt", "pants", "trousers", 
            "jeans", "shorts", "underwear", "socks", "shoes", "boots", "sneakers", "sandals", "slippers", "hat", 
            "cap", "scarf", "gloves", "belt", "tie", "bag", "handbag", "backpack", "umbrella", "glasses", "sunglasses", 
            "jewelry", "ring", "necklace", "bracelet", "earrings", "watch"
        ],
        "Hobbies": [
            "game", "sport", "football", "soccer", "basketball", "baseball", "tennis", "golf", "cricket", "rugby", 
            "hockey", "volleyball", "badminton", "swimming", "running", "cycling", "climbing", "hiking", "camping", 
            "fishing", "hunting", "sailing", "skiing", "skating", "surfing", "dancing", "singing", "playing", "painting", 
            "drawing", "gardening", "cooking", "reading", "writing", "watching", "listening", "collecting", "sewing", 
            "knitting", "chess", "cards", "board game", "puzzle", "toy", "doll", "ball", "music", "song", "singer", 
            "band", "concert", "instrument", "guitar", "piano", "violin", "drums", "flute", "movie", "film", "cinema", 
            "theater", "play", "show", "actor", "actress", "director", "television", "TV", "radio", "podcast", "video", 
            "camera", "photo", "photograph", "picture", "art", "exhibition", "museum", "gallery", "book", "novel", 
            "story", "poem", "writer", "author", "swim", "run", "jog", "climb", "hike", "camp", "nature", "forest", 
            "lake", "sea", "ocean", "animal", "pet", "dog", "cat", "bird", "fish", "horse", "cow", "pig", "sheep", 
            "chicken", "duck", "rabbit", "mouse", "lion", "tiger", "bear", "elephant", "monkey", "snake", "spider", 
            "insect", "bee", "butterfly", "tree", "flower", "plant", "grass", "leaf", "beach", "park", "mountain", 
            "river", "lake", "ocean", "forest", "wood", "garden", "club", "party", "festival", "model", "role",
            "disc", "disk", "air"
        ],
        "Personal": [
            "name", "age", "family", "friend", "mother", "father", "brother", "sister", "happy", "sad", "angry", 
            "tired", "scared", "excited", "like", "love", "want", "need", "feel", "birthday", "hair", "parent", 
            "child", "children", "son", "daughter", "baby", "grandfather", "grandmother", "uncle", "aunt", "cousin", 
            "husband", "wife", "marry", "wedding", "emotions", "feeling", "smile", "cry", "laugh", "fear", "worry", 
            "hope", "wish", "honest", "kind", "nice", "friendly", "lonely", "alone", "personal", "myself", "yourself", 
            "himself", "herself", "man", "woman", "boy", "girl", "people", "person", "kid", "neighbor", "address", 
            "phone", "email", "single", "married", "born", "die", "message", "text", "call", "letter", "mail", "post", 
            "attention", "human", "role"
        ],
        "DailyRoutine": [
            "morning", "afternoon", "evening", "night", "midnight", "noon", "dawn", "dusk", "day", "date", "today", 
            "tomorrow", "yesterday", "every day", "daily", "routine", "schedule", "time", "clock", "watch", "hour", 
            "minute", "second", "wake up", "get up", "go to bed", "sleep", "dream", "rest", "relax", "nap", "wash", 
            "shower", "bath", "brush", "comb", "shave", "dress", "put on", "take off", "breakfast", "lunch", "dinner", 
            "clean", "sweep", "dust", "tidy", "wash up", "laundry", "iron", "cook", "monday", "tuesday", "wednesday", 
            "thursday", "friday", "saturday", "sunday", "weekend"
        ]
    }

    weak_keywords = {
        "go to", "get to", "get on", "get off", "like", "love", "want", "need", "feel", "car", "play", "art", "card",
        "cost", "pay", "face", "care", "day", "night", "room", "head", "hand", "foot", "date", "today", "tomorrow",
        "yesterday", "every day", "morning", "afternoon", "evening", "take care", "look like", "run", "read", "swim", "clean",
        "rest", "time", "wash", "brush"
    }

    phrasal_verb_rules = {
        "Travel": ["get on", "get off", "set off", "go away", "come back", "check in", "take off"],
        "Home / DailyRoutine": ["get up", "wake up", "put on", "clean up", "wash up"],
        "School": ["hand in", "look up", "write down", "read out"],
        "Shopping": ["pay for", "sell out", "pick out"],
        "Health": ["pass out", "throw up", "get over"],
        "Personal / Social": ["grow up", "get along", "fall out", "cheer up"]
    }

    topic_rules = {
        "food and drink": ["Food"],
        "body and health": ["Health"],
        "education": ["School"],
        "homes and buildings": ["Home"],
        "shopping": ["Shopping"],
        "travel": ["Travel"],
        "technology": ["School", "General"],
        "communication": ["Personal", "School", "General"],
        "clothes": ["Personal", "Shopping"],
        "arts and media": ["Hobbies"],
        "animals": ["Hobbies"],
        "natural world": ["Hobbies", "Travel"],
        "people: actions": ["General"],
        "people: appearance": ["Personal"],
        "people: personality": ["Personal"],
        "money": ["Shopping"],
        "work": ["School", "General"],
        "relationships": ["Personal"]
    }

    def check_match(norm_chunk, pat):
        cleaned_chunk = re.sub(r'[^a-z\s]', ' ', norm_chunk.lower())
        
        if ' ' in pat:
            cleaned_pat = re.sub(r'[^a-z\s]', ' ', pat.lower())
            cleaned_pat = ' '.join(cleaned_pat.split())
            cleaned_chunk_collapsed = ' '.join(cleaned_chunk.split())
            return re.search(r'\b' + re.escape(cleaned_pat) + r'\b', cleaned_chunk_collapsed) is not None
            
        words = cleaned_chunk.split()
        for w in words:
            if w == pat:
                return True
            if len(pat) >= 3:
                if w == pat + 's' or w == pat + 'es' or w == pat + 'ed' or w == pat + 'ing':
                    return True
                if pat.endswith('y') and w == pat[:-1] + 'ies':
                    return True
                if len(pat) >= 5 and w.startswith(pat):
                    return True
        return False

    def enhance_chunk_func(c):
        cid = c["canonical_chunk_id"] if "canonical_chunk_id" in c else c["id"]
        norm = c["normalized_chunk"].lower().strip()
        orig_themes = original_theme_mapping[cid]["theme_hint"]
        uc = usage_class_mapping[cid]["usage_class"]
        chunk_type = c["chunk_type"]
        level = c["level"]
        topic = c.get("topic")
        guideword = c.get("guideword") or ""
        
        matched_rules = []
        new_themes = set()
        confidence = "low"
        
        # 1. Lexical patterns
        matched_lexical_by_theme = {}
        for theme, patterns in lexical_patterns.items():
            matched_pats = []
            for pat in patterns:
                if check_match(norm, pat):
                    matched_pats.append(pat)
            if matched_pats:
                matched_lexical_by_theme[theme] = matched_pats
                
        # 2. Topic rules
        matched_topic_themes = []
        if topic:
            topic_clean = topic.lower().strip()
            if topic_clean in topic_rules:
                matched_topic_themes = topic_rules[topic_clean]
                matched_rules.append(f"topic_{topic_clean.replace(':', '').replace(' ', '_')}")
                
        # 3. Phrasal verb rules
        matched_pv_theme = None
        if chunk_type == "phrasal verb":
            for theme, pvs in phrasal_verb_rules.items():
                for pv in pvs:
                    if re.search(r'\b' + re.escape(pv) + r'\b', norm):
                        if pv == "take off":
                            context = (guideword + " " + c.get("details", "")).lower()
                            if any(x in context for x in ["clothe", "shoe", "remove", "wear"]):
                                matched_pv_theme = "Home" if theme == "Home / DailyRoutine" else "DailyRoutine"
                            else:
                                matched_pv_theme = "Travel"
                        else:
                            if "/" in theme:
                                matched_pv_theme = theme.split(" / ")[0]
                            else:
                                matched_pv_theme = theme
                        matched_rules.append(f"phrasal_verb_{pv.replace(' ', '_')}")
                        break
                        
        # Apply lexical matches
        if matched_lexical_by_theme:
            for theme in matched_lexical_by_theme:
                new_themes.add(theme)
                matched_rules.append(f"lexical_{theme.lower()}")
                
        # Apply topic rules
        if matched_topic_themes:
            for theme in matched_topic_themes:
                new_themes.add(theme)
                
        # Apply phrasal verb rules
        if matched_pv_theme:
            new_themes.add(matched_pv_theme)
            
        if not matched_lexical_by_theme:
            if uc == "greeting":
                new_themes.update(["Personal", "DailyRoutine"])
                matched_rules.append("usage_class_greeting")
            elif uc == "classroom_language":
                new_themes.add("School")
                matched_rules.append("usage_class_classroom_language")
            elif uc == "daily_routine":
                new_themes.add("DailyRoutine")
                matched_rules.append("usage_class_daily_routine")
            elif uc == "place_phrase":
                new_themes.update(["Home", "Travel", "School"])
                matched_rules.append("usage_class_place_phrase")
            elif uc == "time_phrase":
                new_themes.update(["DailyRoutine", "General"])
                matched_rules.append("usage_class_time_phrase")
            elif uc == "quantity_phrase":
                new_themes.update(["Shopping", "Food", "General"])
                matched_rules.append("usage_class_quantity_phrase")
            elif uc == "request_expression":
                new_themes.update(["Personal", "School", "Shopping"])
                matched_rules.append("usage_class_request_expression")
            elif uc == "opinion_expression":
                new_themes.update(["Personal", "School"])
                matched_rules.append("usage_class_opinion_expression")
            elif uc == "emotion_expression":
                new_themes.add("Personal")
                matched_rules.append("usage_class_emotion_expression")
            elif uc == "social_expression":
                new_themes.add("Personal")
                matched_rules.append("usage_class_social_expression")
            elif uc == "grammar_term":
                new_themes.add("School")
                matched_rules.append("usage_class_grammar_term")
            elif uc == "compound_adjective":
                new_themes.update(["Personal", "General"])
                matched_rules.append("usage_class_compound_adjective")
            elif uc == "compound_noun":
                if matched_topic_themes:
                    new_themes.update(matched_topic_themes)
                else:
                    new_themes.add("General")
            elif uc in ["prepositional_phrase", "general_phrase"]:
                new_themes.add("General")
                
        # If we didn't add anything new, fallback to General
        if not new_themes:
            new_themes.add("General")
            
        # Guard rules / Negative rules
        has_placeholder = any(x in norm.split() or x in norm for x in ["sb", "sth", "someone", "something", "somebody"])
        if has_placeholder and not matched_lexical_by_theme:
            new_themes = {"General"}
            matched_rules.append("guard_placeholder_no_lexical")
            
        if guideword.upper() == "IDIOM" and not matched_lexical_by_theme:
            new_themes = {"General"}
            matched_rules.append("guard_idiom_no_lexical")
            
        if level in ["C1", "C2"] and matched_lexical_by_theme and not matched_topic_themes and not matched_pv_theme:
            all_matched_keywords = []
            for t, kw_list in matched_lexical_by_theme.items():
                all_matched_keywords.extend(kw_list)
            if len(all_matched_keywords) == 1 and all_matched_keywords[0] in weak_keywords:
                new_themes = {"General"}
                matched_rules.append("guard_advanced_weak_keyword")
                
        if uc == "grammar_term":
            new_themes = {"School"}
            if "General" in new_themes:
                new_themes.remove("General")
            matched_rules.append("guard_grammar_term")
            
        if uc == "discourse_marker":
            has_personal_social = any(t in new_themes for t in ["Personal", "DailyRoutine"])
            if not has_personal_social:
                new_themes = {"General"}
                matched_rules.append("guard_discourse_marker")
                
        if uc == "modal_expression":
            new_themes = {"General"}
            matched_rules.append("guard_modal_expression")
            
        abstract_words = ["relation", "aspect", "extent", "manner", "basis", "regard", "context", "concept", "theory"]
        if any(aw in norm for aw in abstract_words):
            new_themes = {"General"}
            matched_rules.append("guard_abstract_words")
            
        if len(new_themes) > 1 and "General" in new_themes:
            keep_general = False
            if topic and topic.lower().strip() in ["technology", "communication", "work"]:
                keep_general = True
            if uc in ["time_phrase", "quantity_phrase", "compound_adjective"]:
                keep_general = True
            if not keep_general:
                new_themes.remove("General")
                
        is_broad_topic = topic and topic.lower().strip() in ["communication", "technology", "natural world"]
        
        # Check lexical patterns type
        has_strong_lexical = False
        has_weak_lexical = False
        all_lex_keywords = []
        if matched_lexical_by_theme:
            for t, kws in matched_lexical_by_theme.items():
                for kw in kws:
                    all_lex_keywords.append(kw)
                    if kw in weak_keywords:
                        has_weak_lexical = True
                    else:
                        has_strong_lexical = True
                        
        if uc == "grammar_term":
            confidence = "high"
        elif topic and topic.lower().strip() in topic_rules and not is_broad_topic:
            confidence = "high"
        elif has_strong_lexical and not has_placeholder:
            confidence = "high"
        elif matched_pv_theme:
            confidence = "medium"
        elif matched_lexical_by_theme and any(r.startswith("usage_class_") for r in matched_rules):
            confidence = "medium"
        elif len(all_lex_keywords) >= 2:
            confidence = "medium"
        elif is_broad_topic:
            confidence = "low"
        elif has_weak_lexical:
            confidence = "low"
        else:
            confidence = "low"
            
        orig_is_general = (orig_themes == ["General"])
        if confidence == "low" and not orig_is_general:
            final_themes = set(orig_themes)
        else:
            final_themes = new_themes
            
        final_themes_list = sorted(list(final_themes))
        changed = (final_themes_list != sorted(orig_themes))
        
        return final_themes_list, confidence, matched_rules, changed

    # 1. Build chunk_theme_hint_enhanced_mapping.json for all raw chunks
    enhanced_mapping = {}
    for c in chunks:
        cid = c["id"]
        # Format the chunk object so enhance_chunk_func can use it directly
        # It needs level, normalized_chunk, chunk_type, topic, guideword, details
        # Let's map it using the function
        themes, confidence, rules, changed = enhance_chunk_func(c)
        enhanced_mapping[cid] = {
            "original_theme_hint": original_theme_mapping[cid]["theme_hint"],
            "enhanced_theme_hint": themes,
            "confidence": confidence,
            "matched_rules": rules,
            "changed": changed
        }
        
    # 2. Build chunks_generator_safe_theme_enhanced.json
    chunks_generator_safe_theme_enhanced = []
    top_changed_examples = []
    changed_total = 0
    confidence_counts = {"high": 0, "medium": 0, "low": 0}
    
    a1_a2_general_before = 0
    a1_a2_general_after = 0
    
    # Theme counts
    theme_counts_before = {t: 0 for t in THEME_SET}
    theme_counts_after = {t: 0 for t in THEME_SET}
    
    for sc in safe_chunks:
        cid = sc["canonical_chunk_id"]
        orig_themes = sc["theme_hint"]
        
        # Increment before counts
        for ot in orig_themes:
            theme_counts_before[ot] += 1
            
        # Get enhanced mapping details
        mapped_details = enhanced_mapping[cid]
        themes = mapped_details["enhanced_theme_hint"]
        confidence = mapped_details["confidence"]
        rules = mapped_details["matched_rules"]
        changed = mapped_details["changed"]
        
        # Increment after counts
        for nt in themes:
            theme_counts_after[nt] += 1
            
        # Count high/medium/low
        confidence_counts[confidence] += 1
        
        if changed:
            changed_total += 1
            if len(top_changed_examples) < 20:
                top_changed_examples.append({
                    "chunk": sc["chunk"],
                    "before": orig_themes,
                    "after": themes,
                    "confidence": confidence,
                    "rules": rules
                })
                
        if sc["level"] in ["A1", "A2"]:
            if orig_themes == ["General"]:
                a1_a2_general_before += 1
            if themes == ["General"]:
                a1_a2_general_after += 1
                
        # Build safe enhanced chunk
        enhanced_sc = sc.copy()
        enhanced_sc["theme_hint_original"] = orig_themes
        enhanced_sc["theme_hint_enhanced"] = themes
        enhanced_sc["theme_enhancement_confidence"] = confidence
        enhanced_sc["theme_enhancement_rules"] = rules
        chunks_generator_safe_theme_enhanced.append(enhanced_sc)
        
    # 3. Build Rulebook
    rulebook = {
        "version": "S3",
        "theme_set": THEME_SET,
        "topic_rules": topic_rules,
        "usage_class_rules": {
            "greeting": ["Personal", "DailyRoutine"],
            "classroom_language": ["School"],
            "daily_routine": ["DailyRoutine"],
            "place_phrase": ["Home", "Travel", "School"],
            "time_phrase": ["DailyRoutine", "General"],
            "quantity_phrase": ["Shopping", "Food", "General"],
            "discourse_marker": ["General"],
            "request_expression": ["Personal", "School", "Shopping"],
            "opinion_expression": ["Personal", "School"],
            "emotion_expression": ["Personal"],
            "social_expression": ["Personal"],
            "phrasal_verb": ["General"],
            "idiom": ["General"],
            "collocation": ["General"],
            "compound_noun": ["use_lexical_pattern_first_then_topic"],
            "compound_adjective": ["Personal", "General"],
            "prepositional_phrase": ["use_lexical_pattern_first_then_general"],
            "modal_expression": ["General"],
            "grammar_term": ["School"],
            "general_phrase": ["use_lexical_pattern_first_then_general"]
        },
        "lexical_pattern_rules": [
            {"theme": t, "patterns": lexical_patterns[t]} for t in lexical_patterns
        ],
        "negative_rules": [
            "placeholder_guard_force_general",
            "idiom_guard_force_general",
            "advanced_weak_keyword_guard_keep_general",
            "grammar_term_guard_force_school",
            "discourse_marker_guard_force_general",
            "modal_expression_guard_force_general",
            "abstract_words_guard_force_general"
        ],
        "confidence_rules": {
            "high": ["topic_direct_match", "strong_lexical_pattern_match", "grammar_term_to_school"],
            "medium": ["usage_class_plus_lexical_pattern", "phrasal_verb_semantic_rule", "multiple_weak_rules_agree"],
            "low": ["weak_lexical_pattern_only", "broad_topic_match"]
        }
    }
    
    # 4. Build Coverage Delta
    general_only_before = theme_counts_before["General"]
    general_only_after = theme_counts_after["General"]
    
    # Wait, general only means exactly ["General"]
    general_only_before = sum(1 for c in safe_chunks if c["theme_hint"] == ["General"])
    general_only_after = sum(1 for c in chunks_generator_safe_theme_enhanced if c["theme_hint_enhanced"] == ["General"])
    
    delta = {}
    for t in THEME_SET:
        delta[t] = theme_counts_after[t] - theme_counts_before[t]
        
    coverage_delta = {
        "before": theme_counts_before,
        "after": theme_counts_after,
        "delta": delta,
        "general_only_before": general_only_before,
        "general_only_after": general_only_after,
        "general_only_ratio_before": round(general_only_before / len(safe_chunks), 4),
        "general_only_ratio_after": round(general_only_after / len(safe_chunks), 4)
    }
    
    # 5. Build Policy
    policy = {
        "policy_name": "EVP Chunk Theme Coverage Enhancement Policy",
        "version": "S3",
        "source": "CHUNK_DB_S3_ThemeCoverageEnhancement_DesignScan",
        "rules": {
            "raw_chunks_are_immutable": True,
            "s2_safe_layer_is_immutable": True,
            "theme_enhancement_is_derived": True,
            "do_not_modify_cefr": True,
            "do_not_modify_priority": True,
            "do_not_modify_usage_class": True,
            "low_confidence_must_not_override_existing_non_general": True,
            "general_is_allowed_when_theme_unknown": True,
            "generator_may_use_enhanced_theme_filter": True,
            "validator_theme_matching_must_remain_optional": True
        }
    }
    
    # 6. Build Report
    # Verdict criteria:
    # STRONG_PASS: general_only_ratio_after <= 0.60
    # PASS: general_only_ratio_after <= 0.70
    # WARNING: general_only_ratio_after > 0.70
    ratio_after = general_only_after / len(safe_chunks)
    if ratio_after <= 0.60:
        verdict = "STRONG_PASS"
    elif ratio_after <= 0.70:
        verdict = "PASS"
    else:
        verdict = "WARNING"
        
    report = {
        "input_safe_chunks_total": len(safe_chunks),
        "general_only_before": general_only_before,
        "general_only_after": general_only_after,
        "general_only_ratio_before": round(general_only_before / len(safe_chunks), 4),
        "general_only_ratio_after": round(ratio_after, 4),
        "theme_counts_before": theme_counts_before,
        "theme_counts_after": theme_counts_after,
        "changed_total": changed_total,
        "confidence_counts": confidence_counts,
        "top_changed_examples": top_changed_examples,
        "a1_a2_general_before": a1_a2_general_before,
        "a1_a2_general_after": a1_a2_general_after,
        "warnings": [],
        "verdict": verdict
    }
    
    # Write all JSONs
    def write_json(obj, filename, folder):
        filepath = os.path.join(folder, filename)
        with open(filepath, "w", encoding="utf-8") as out:
            json.dump(obj, out, indent=2, ensure_ascii=False)
        print(f"Saved {filepath}")
        
    write_json(enhanced_mapping, "chunk_theme_hint_enhanced_mapping.json", json_dir)
    write_json(chunks_generator_safe_theme_enhanced, "chunks_generator_safe_theme_enhanced.json", json_dir)
    write_json(rulebook, "chunk_theme_rulebook.json", json_dir)
    write_json(coverage_delta, "chunk_theme_coverage_delta.json", json_dir)
    write_json(policy, "chunk_theme_enhancement_policy.json", json_dir)
    write_json(report, "chunk_theme_coverage_enhancement_report.json", reports_dir)
    
    print("All chunk theme coverage enhancement files written successfully.")

if __name__ == "__main__":
    main()
