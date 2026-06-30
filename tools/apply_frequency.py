import os
import json
import re
import openpyxl

def clean_val(val):
    return str(val).strip() if val is not None else ""

def normalize_word_basic(word):
    """
    Apply basic normalization: lowercase, strip outer spaces, 
    and remove punctuation except hyphen and apostrophe.
    """
    w = str(word).strip().lower()
    w = re.sub(r"[^\w\s'-]", "", w)
    return w

def apply_spelling_rules(w):
    """
    Apply suffix and infix rules to recover UK-to-US spelling variations.
    """
    # 1. -our -> -or (colour -> color)
    if w.endswith("our"):
        w = w[:-3] + "or"
    elif "our" in w:
        w = w.replace("our", "or")
        
    # 2. -re -> -er (centre -> center, theatre -> theater, fibre -> fiber)
    # Avoid applying to words ending in e.g., -ure or -ore
    if w.endswith("re") and len(w) > 2 and w[-3] not in "aeiouy":
        w = w[:-2] + "er"
        
    # 3. -ise -> -ize, -isation -> -ization
    if w.endswith("ise"):
        w = w[:-3] + "ize"
    elif w.endswith("ises"):
        w = w[:-4] + "izes"
    elif w.endswith("ised"):
        w = w[:-4] + "ized"
    elif w.endswith("ising"):
        w = w[:-5] + "izing"
    elif "isation" in w:
        w = w.replace("isation", "ization")
        
    # 4. Double L spellings (travelling -> traveling)
    if w.endswith("lling"):
        w = w[:-5] + "ling"
    elif w.endswith("lled"):
        w = w[:-4] + "led"
    elif w.endswith("llor"):
        w = w[:-4] + "lor"
        
    # 5. -ogue -> -og (catalogue -> catalog, dialogue -> dialog)
    if w.endswith("ogue"):
        w = w[:-4] + "og"
        
    # 6. -ence -> -ens / -ense (defence -> defense, licence -> license)
    if w in ["defence", "licence", "offence", "pretence"]:
        w = w[:-4] + "ense"
        
    # 7. -oe- -> -e- (diarrhoea -> diarrhea)
    if "oe" in w and w not in ["shoe", "shoes", "toe", "toes", "does"]:
        w = w.replace("oe", "e")
        
    return w

def main():
    # 1. Paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    vocab_json_path = os.path.join(base_dir, "vocabulary", "json", "vocabulary.json")
    xlsx_path = os.path.join(base_dir, "vocabulary", "source", "NGSL+with+SFI+(31K).xlsx")
    
    mapping_dir = os.path.join(base_dir, "vocabulary", "mapping")
    reports_dir = os.path.join(base_dir, "reports")
    output_reports_dir = os.path.join(base_dir, "output", "reports")
    
    os.makedirs(mapping_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(output_reports_dir, exist_ok=True)
    
    # 2. Load vocabulary.json
    print(f"Loading vocabulary: {vocab_json_path}")
    with open(vocab_json_path, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    # 3. Load and parse NGSL workbook
    print(f"Loading NGSL workbook: {xlsx_path}")
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    sheet = wb["SFI adj"]
    
    # Read rows and filter out empty ones
    clean_rows = []
    for row in list(sheet.iter_rows(values_only=True))[1:]:
        if row and row[0] is not None:
            clean_rows.append(row)
            
    # Sort non-empty rows by SFI descending to assign continuous, dispersion-aware ranks
    sorted_rows = sorted(clean_rows, key=lambda r: r[3] if r[3] is not None else -1, reverse=True)
    
    # Build lemma lookup database
    # In case of duplicates, keep the highest SFI / lowest rank
    ngsl_data = {}
    for rank_idx, row in enumerate(sorted_rows, 1):
        lemma = normalize_word_basic(row[0])
        sfi = row[3] if row[3] is not None else 0.0
        wordlist = clean_val(row[1])
        
        if lemma not in ngsl_data or sfi > ngsl_data[lemma]["sfi"]:
            ngsl_data[lemma] = {
                "rank": rank_idx,
                "sfi": sfi,
                "wordlist": wordlist
            }
            
    print(f"Parsed {len(ngsl_data)} unique normalized NGSL lemmas.")
    
    # 4. Advanced Normalization mappings
    irregular_verbs = {
        "broken": "break", "frozen": "freeze", "fed": "feed", "lost": "lose",
        "hidden": "hide", "grown": "grow", "born": "bear", "chosen": "choose",
        "drawn": "draw", "fallen": "fall", "forgotten": "forget", "known": "know",
        "seen": "see", "shaken": "shake", "spoken": "speak", "stolen": "steal",
        "taken": "take", "thrown": "throw", "written": "write", "done": "do",
        "gone": "go", "been": "be", "had": "have", "made": "make",
        "said": "say", "told": "tell", "spent": "spend", "built": "build",
        "bought": "buy", "brought": "bring", "caught": "catch", "thought": "think",
        "taught": "teach", "sung": "sing", "drunk": "drink", "begun": "begin",
        "led": "lead", "heard": "hear", "held": "hold", "met": "meet",
        "paid": "pay", "sent": "send", "slept": "sleep", "swept": "sweep",
        "kept": "keep", "left": "leave", "felt": "feel", "meant": "mean",
        "spelt": "spell", "learnt": "learn", "burnt": "burn", "dreamt": "dream",
        "lent": "lend", "bent": "bend", "clichéd": "cliché"
    }
    
    spelling_map = {
        "grey": "gray", "cosy": "cozy", "disc": "disk", "discs": "disks",
        "fulfilment": "fulfillment", "instalment": "installment",
        "pyjamas": "pajamas", "yoghurt": "yogurt", "yoghurts": "yogurt",
        "chilli": "chili", "chillies": "chili"
    }
    
    ordinal_map = {
        "first": "one", "second": "two", "third": "three", "fourth": "four",
        "fifth": "five", "sixth": "six", "seventh": "seven", "eighth": "eight",
        "ninth": "nine", "tenth": "ten", "twelfth": "twelve", "twentieth": "twenty"
    }
    
    manual_map = {
        "cd": "disc", "cd-rom": "disc", "dvd": "video", "tv": "television", "pc": "computer",
        "a.m.": "am", "p.m.": "pm", "am": "morning", "pm": "afternoon",
        "cv": "resume", "dj": "musician", "dr": "doctor", "dna": "gene", "ok": "okay"
    }
    
    def lookup_lemma(w, depth=0):
        """
        Advanced recursive normalization pipeline.
        Returns: (matched_lemma, recovery_method) or (None, None)
        """
        if depth > 3:  # recursion guard
            return None, None
            
        w = w.strip().lower()
        w = re.sub(r"[^\w\s'-]", "", w)
        if not w:
            return None, None
            
        # A. Direct Match
        if w in ngsl_data:
            return w, "direct_match"
            
        # B. Irregular Verb Mapping
        if w in irregular_verbs:
            mapped = irregular_verbs[w]
            res_lemma, _ = lookup_lemma(mapped, depth + 1)
            if res_lemma:
                return res_lemma, "participle_normalization"
                
        # C. Manual Abbreviation Whitelist
        if w in manual_map:
            mapped = manual_map[w]
            res_lemma, _ = lookup_lemma(mapped, depth + 1)
            if res_lemma:
                return res_lemma, "abbreviation_normalization"
                
        # D. Specific spelling map (UK -> US exceptions)
        if w in spelling_map:
            mapped = spelling_map[w]
            res_lemma, _ = lookup_lemma(mapped, depth + 1)
            if res_lemma:
                return res_lemma, "spelling_normalization"
                
        # E. General UK-to-US spelling suffix/infix rules
        w_rule = apply_spelling_rules(w)
        if w_rule != w:
            res_lemma, _ = lookup_lemma(w_rule, depth + 1)
            if res_lemma:
                return res_lemma, "spelling_normalization"
                
        # F. Ordinals-to-Cardinals map
        if w in ordinal_map:
            mapped = ordinal_map[w]
            res_lemma, _ = lookup_lemma(mapped, depth + 1)
            if res_lemma:
                return res_lemma, "ordinal_normalization"
                
        # G. Hyphenated word check (look up first element recursively)
        if "-" in w:
            parts = w.split("-")
            first_part = parts[0]
            if first_part in spelling_map:
                first_part = spelling_map[first_part]
            res_lemma, _ = lookup_lemma(first_part, depth + 1)
            if res_lemma:
                return res_lemma, "hyphenated_normalization"
                
        # H. Plurals check (ending in s/ies/es)
        if w.endswith("ies") and len(w) > 4:
            cand = w[:-3] + "y"
            res_lemma, _ = lookup_lemma(cand, depth + 1)
            if res_lemma:
                return res_lemma, "plural_normalization"
        if w.endswith("es") and len(w) > 3:
            # check stripping 'es' (boxes -> box)
            cand1 = w[:-2]
            res_lemma1, _ = lookup_lemma(cand1, depth + 1)
            if res_lemma1:
                return res_lemma1, "plural_normalization"
            # check stripping just 's' (ages -> age)
            cand2 = w[:-1]
            res_lemma2, _ = lookup_lemma(cand2, depth + 1)
            if res_lemma2:
                return res_lemma2, "plural_normalization"
        if w.endswith("s") and len(w) > 2:
            cand = w[:-1]
            res_lemma, _ = lookup_lemma(cand, depth + 1)
            if res_lemma:
                return res_lemma, "plural_normalization"
                
        # I. Participle / Verb check (ending in ed/ing)
        if w.endswith("ing") and len(w) > 4:
            # camping -> camp
            cand1 = w[:-3]
            # baking -> bake
            cand2 = w[:-3] + "e"
            # running -> run (check if ending double L/N/P/T, w[-4] == w[-5])
            cand3 = w[:-4] if len(w) > 5 and w[-4] == w[-5] else ""
            
            for cand in [cand1, cand2, cand3]:
                if cand:
                    res_lemma, _ = lookup_lemma(cand, depth + 1)
                    if res_lemma:
                        return res_lemma, "participle_normalization"
                        
        if w.endswith("ed") and len(w) > 3:
            # closed -> close
            cand1 = w[:-1]
            # started -> start
            cand2 = w[:-2]
            # carried -> carry
            cand3 = w[:-3] + "y" if w.endswith("ied") else ""
            # stopped -> stop (check if ending double L/N/P/T, w[-3] == w[-4])
            cand4 = w[:-3] if len(w) > 4 and w[-3] == w[-4] else ""
            
            for cand in [cand1, cand2, cand3, cand4]:
                if cand:
                    res_lemma, _ = lookup_lemma(cand, depth + 1)
                    if res_lemma:
                        return res_lemma, "participle_normalization"
                        
        return None, None

    # 5. Process matches
    direct_matches_cnt = 0
    direct_phrase_matches_cnt = 0
    normalization_recoveries_cnt = 0
    phrase_fallback_matches_cnt = 0
    unmatched_records_cnt = 0
    
    # Store temporary scoring metadata for sorting
    processed_records = []
    level_order = {"a1": 0, "a1_plus": 1, "a2": 2, "a2_plus": 3, "b1": 4, "b1_plus": 5, "b2": 6, "b2_plus": 7, "c1": 8, "c2": 9}
    
    for r in records:
        w_raw = r["word"]
        pos = str(r.get("part_of_speech", "")).lower()
        is_phrase = " " in w_raw or pos in ["phrase", "phrasal verb"]
        lvl = str(r["level"]).strip().lower()
        lvl_val = level_order.get(lvl, 99)
        
        # Default initialization
        resolved_sfi = 0.0
        resolved_rank = 999999
        recovery_method = "tier_5_fallback"
        
        if is_phrase:
            # Phrase Resolution Order:
            # 1. Exact phrase lookup
            w_norm = normalize_word_basic(w_raw)
            lemma, method = lookup_lemma(w_norm)
            
            if lemma:
                resolved_sfi = ngsl_data[lemma]["sfi"]
                resolved_rank = ngsl_data[lemma]["rank"]
                if method == "direct_match":
                    recovery_method = "direct_match"
                    direct_phrase_matches_cnt += 1
                else:
                    recovery_method = method
                    normalization_recoveries_cnt += 1
            else:
                # 2. Phrase Headword lookup
                words_in_phrase = w_raw.split()
                head_word = words_in_phrase[0] if words_in_phrase else ""
                head_lemma, head_method = lookup_lemma(head_word)
                if head_lemma:
                    # Scale score to 20% of headword, and multiply rank by 5
                    resolved_sfi = ngsl_data[head_lemma]["sfi"] * 0.2
                    resolved_rank = ngsl_data[head_lemma]["rank"] * 5
                    recovery_method = "phrase_headword_fallback"
                    phrase_fallback_matches_cnt += 1
                else:
                    # 3. Fallback
                    resolved_sfi = 0.0
                    resolved_rank = 999999
                    recovery_method = "tier_5_fallback"
                    unmatched_records_cnt += 1
        else:
            # Word lookup
            w_norm = normalize_word_basic(w_raw)
            lemma, method = lookup_lemma(w_norm)
            
            if lemma:
                resolved_sfi = ngsl_data[lemma]["sfi"]
                resolved_rank = ngsl_data[lemma]["rank"]
                if method == "direct_match":
                    recovery_method = "direct_match"
                    direct_matches_cnt += 1
                else:
                    recovery_method = method
                    normalization_recoveries_cnt += 1
            else:
                resolved_sfi = 0.0
                resolved_rank = 999999
                recovery_method = "tier_5_fallback"
                unmatched_records_cnt += 1
                
        processed_records.append({
            "record": r,
            "lvl_val": lvl_val,
            "lvl": lvl,
            "sfi": resolved_sfi,
            "ngsl_rank": resolved_rank,
            "method": recovery_method,
            "is_phrase": is_phrase
        })
        
    # 6. Apply Hybrid Sorting Key:
    # 1. CEFR Level ascending
    # 2. NGSL SFI descending (higher SFI comes first)
    # 3. Alphabetical order (lowercase)
    processed_records.sort(key=lambda x: (
        x["lvl_val"], 
        -x["sfi"], 
        x["record"]["word"].lower()
    ))
    
    # 7. Assign continuous ranks and bands
    # Thresholds:
    # Tier 1: 1-1000
    # Tier 2: 1001-3000
    # Tier 3: 3001-7000
    # Tier 4: 7001-11500
    # Tier 5: 11501+
    
    CEFR_CEILINGS = {
        "a1": "tier_1", "a1_plus": "tier_1",
        "a2": "tier_1", "a2_plus": "tier_1",
        "b1": "tier_2", "b1_plus": "tier_2",
        "b2": "tier_3", "b2_plus": "tier_3",
        "c1": "tier_4", "c1_plus": "tier_4",
        "c2": "tier_5"
    }
    
    TIER_VALUES = {
        "tier_1": 1, "tier_2": 2, "tier_3": 3, "tier_4": 4, "tier_5": 5
    }
    
    tier_distribution = {"tier_1": 0, "tier_2": 0, "tier_3": 0, "tier_4": 0, "tier_5": 0}
    words_frequency = {}
    
    for rank_idx, item in enumerate(processed_records, 1):
        if rank_idx <= 1000:
            band = "tier_1"
        elif rank_idx <= 3000:
            band = "tier_2"
        elif rank_idx <= 7000:
            band = "tier_3"
        elif rank_idx <= 11500:
            band = "tier_4"
        else:
            band = "tier_5"
            
        # Mandatory Phrase Tier Capping Logic:
        # A phrase-derived frequency tier MUST NOT exceed its CEFR-level ceiling
        if item["is_phrase"]:
            ceiling_band = CEFR_CEILINGS.get(item["lvl"], "tier_5")
            if TIER_VALUES[band] < TIER_VALUES[ceiling_band]:
                band = ceiling_band
                
        # Map fields back to the original dictionary record
        r = item["record"]
        r["frequency_score"] = round(item["sfi"], 4)
        r["frequency_band"] = band
        r["corpus_rank"] = rank_idx
        r["frequency_recovery_method"] = item["method"]
        
        tier_distribution[band] += 1
        
        # Build lookup for frequency_mapping.json (keep highest score / lowest rank)
        w_norm = normalize_word_basic(r["word"])
        if w_norm not in words_frequency or rank_idx < words_frequency[w_norm]["corpus_rank"]:
            words_frequency[w_norm] = {
                "frequency_score": round(item["sfi"], 4),
                "frequency_band": band,
                "corpus_rank": rank_idx
            }
            
    # 8. Overwrite vocabulary.json
    print(f"Writing vocabulary.json: {vocab_json_path}")
    with open(vocab_json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
        
    # 9. Overwrite frequency_mapping.json
    mapping_path = os.path.join(mapping_dir, "frequency_mapping.json")
    print(f"Writing frequency_mapping.json: {mapping_path}")
    mapping_data = {"words": words_frequency}
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(mapping_data, f, indent=2, ensure_ascii=False)
        
    # 10. Generate reports
    total_records = len(records)
    total_matched = total_records - unmatched_records_cnt
    coverage_percentage = round((total_matched / total_records) * 100, 2)
    
    report = {
        "total_records": total_records,
        "direct_matches": direct_matches_cnt,
        "phrase_matches": direct_phrase_matches_cnt,
        "normalization_recoveries": normalization_recoveries_cnt,
        "fallback_matches": phrase_fallback_matches_cnt,
        "unmatched_records": unmatched_records_cnt,
        "coverage_percentage": coverage_percentage,
        "tier_distribution": tier_distribution
    }
    
    # Save the report to all required paths
    report_paths = [
        os.path.join(reports_dir, "ngsl_frequency_upgrade_report.json"),
        os.path.join(output_reports_dir, "ngsl_frequency_upgrade_report.json"),
        # Backward compatibility paths
        os.path.join(reports_dir, "frequency_implementation_report.json"),
        os.path.join(output_reports_dir, "frequency_implementation_report.json")
    ]
    
    for p in report_paths:
        print(f"Writing report: {p}")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
    print("\nVocabulary Frequency Authority Upgrade complete!")
    print(f"Total: {total_records}, Matched: {total_matched}, Unmatched: {unmatched_records_cnt}")
    print(f"Coverage: {coverage_percentage}%")
    print(f"Tiers: {tier_distribution}")

if __name__ == "__main__":
    main()
