import os
import json
import re
import pandas as pd

def clean_val(val):
    if pd.isna(val):
        return ""
    return str(val).strip()

def norm(val):
    if pd.isna(val):
        return ""
    return str(val).strip().lower()

def main():
    # 1. Paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    excel_path = os.path.join(base_dir, "vocabulary", "source", "English Vocabulary Profile Online.xlsx")
    
    json_dir = os.path.join(base_dir, "vocabulary", "json")
    mapping_dir = os.path.join(base_dir, "vocabulary", "mapping")
    report_dir = os.path.join(base_dir, "output", "reports")
    
    os.makedirs(json_dir, exist_ok=True)
    os.makedirs(mapping_dir, exist_ok=True)
    os.makedirs(report_dir, exist_ok=True)
    
    # 2. Read sheets
    xl = pd.ExcelFile(excel_path)
    df_total = pd.read_excel(excel_path, sheet_name="total(15696)")
    df_total.columns = [c.strip() for c in df_total.columns]
    
    # Clean strings in total sheet
    df_total['word_norm'] = df_total['Base Word'].map(norm)
    df_total['guide_norm'] = df_total['Guideword'].map(norm)
    df_total['level_norm'] = df_total['Level'].map(norm)
    df_total['pos_norm'] = df_total['Part of Speech'].map(norm)
    df_total['topic_norm'] = df_total['Topic'].map(norm)
    
    # Pre-build lookup dictionaries from total sheet populated rows
    pop_pos = df_total[df_total['pos_norm'] != '']
    word_pos_all = {}
    word_guide_pos = {}
    for idx, r in pop_pos.iterrows():
        w, g, p = r['word_norm'], r['guide_norm'], str(r['Part of Speech']).strip()
        if w not in word_pos_all:
            word_pos_all[w] = set()
        word_pos_all[w].add(p)
        
        k = (w, g)
        if k not in word_guide_pos:
            word_guide_pos[k] = set()
        word_guide_pos[k].add(p)
        
    word_pos_unique = {}
    word_pos_majority = {}
    for w, ps in word_pos_all.items():
        if len(ps) == 1:
            word_pos_unique[w] = list(ps)[0]
        # Calculate majority POS (>50%)
        # Filter all occurrences of this word that have POS populated
        gp_pos = pop_pos[pop_pos['word_norm'] == w]['Part of Speech']
        if not gp_pos.empty:
            counts = gp_pos.value_counts()
            if counts.iloc[0] / len(gp_pos) > 0.5:
                word_pos_majority[w] = counts.index[0]

    pop_topic = df_total[df_total['topic_norm'] != '']
    word_topic_all = {}
    word_guide_topic = {}
    for idx, r in pop_topic.iterrows():
        w, g, t = r['word_norm'], r['guide_norm'], str(r['Topic']).strip()
        if w not in word_topic_all:
            word_topic_all[w] = set()
        word_topic_all[w].add(t)
        
        k = (w, g)
        if k not in word_guide_topic:
            word_guide_topic[k] = set()
        word_guide_topic[k].add(t)
        
    word_topic_unique = {}
    word_topic_majority = {}
    for w, ts in word_topic_all.items():
        if len(ts) == 1:
            word_topic_unique[w] = list(ts)[0]
        # Calculate majority topic (>50%)
        gp_topic = pop_topic[pop_topic['word_norm'] == w]['Topic']
        if not gp_topic.empty:
            counts = gp_topic.value_counts()
            if counts.iloc[0] / len(gp_topic) > 0.5:
                word_topic_majority[w] = counts.index[0]

    # Load topic sheets for reconciliation lookup
    # Key: (word_norm, guide_norm, level_norm) -> (pos, topic)
    topic_sheet_lookup = {}
    for sheet in xl.sheet_names:
        if sheet == "total(15696)":
            continue
        df_sheet = pd.read_excel(excel_path, sheet_name=sheet)
        df_sheet.columns = [c.strip() for c in df_sheet.columns]
        topic_name = sheet.split('(')[0].strip()
        
        for idx, r in df_sheet.iterrows():
            w = norm(r.get('Base Word'))
            g = norm(r.get('Guideword'))
            lvl = norm(r.get('Level'))
            p = str(r.get('Part of Speech')).strip()
            t = str(r.get('Topic')).strip()
            
            k = (w, g, lvl)
            if k not in topic_sheet_lookup:
                topic_sheet_lookup[k] = {}
            if p and not pd.isna(r.get('Part of Speech')):
                topic_sheet_lookup[k]['pos'] = p
            if t and not pd.isna(r.get('Topic')):
                topic_sheet_lookup[k]['topic'] = topic_name
            else:
                # If topic column is missing or empty in sheet, the sheet name itself is the topic!
                topic_sheet_lookup[k]['topic'] = topic_name

    # Whitelist definition for POS
    numbers_set = {'eight', 'eighteen', 'eighth', 'eighty', 'eleven', 'fifteen', 'fifth', 'fifty', 'five', 'forty', 'four', 'fourteen', 'fourth', 'hundred', 'million', 'thousand', 'nine', 'nineteen', 'ninety', 'ninth', 'one', 'two', 'three', 'seventy', 'seventeen', 'seventh', 'six', 'sixteen', 'sixth', 'sixty', 'ten', 'twelve', 'twenty', 'third', 'thirteen', 'thirty', 'zero', 'second'}
    conjunctions_set = {'albeit', 'although', 'and', 'as', 'because', 'but', 'however', 'if', 'insofar as', 'or', 'provided (that)', 'once', 'since', 'so', 'that', 'while', 'whereas', 'though', 'till', 'unless', 'until', 'when', 'whenever', 'where', 'wherever', 'whether', 'yet'}
    prepositions_set = {'after', 'before', 'like', 'to', 'plus'}

    records = []
    
    # Performance tracking
    recovered_topic_count = 0
    recovered_pos_count = 0
    
    topic_method_counts = {}
    pos_method_counts = {}
    
    # 3. Process every row
    for idx, row in df_total.iterrows():
        excel_row_num = idx + 2
        vocab_id = f"v_{excel_row_num}"
        
        word = clean_val(row.get("Base Word"))
        guideword = clean_val(row.get("Guideword"))
        level = clean_val(row.get("Level"))
        raw_topic = clean_val(row.get("Topic"))
        raw_pos = clean_val(row.get("Part of Speech"))
        details = clean_val(row.get("Details"))
        
        w_norm = norm(word)
        g_norm = norm(guideword)
        lvl_norm = norm(level)
        
        # --- POS Recovery Pipeline ---
        pos_resolved = raw_pos
        pos_status = "natively_populated" if raw_pos else "unmapped"
        pos_recovery_method = "none"
        pos_recovery_confidence = "none"
        pos_review_required = False
        
        if not pos_resolved:
            # A. topic_sheet_reconciliation
            k_reconcile = (w_norm, g_norm, lvl_norm)
            if k_reconcile in topic_sheet_lookup and 'pos' in topic_sheet_lookup[k_reconcile]:
                pos_resolved = topic_sheet_lookup[k_reconcile]['pos']
                pos_status = "recovered"
                pos_recovery_method = "topic_sheet_reconciliation"
                pos_recovery_confidence = "high"
            # B. same_word_guideword_exact
            elif (w_norm, g_norm) in word_guide_pos and len(word_guide_pos[(w_norm, g_norm)]) == 1:
                pos_resolved = list(word_guide_pos[(w_norm, g_norm)])[0]
                pos_status = "recovered"
                pos_recovery_method = "same_word_guideword_exact"
                pos_recovery_confidence = "high"
            # C. closed_class_whitelist
            elif w_norm in numbers_set:
                pos_resolved = "determiner"
                pos_status = "recovered"
                pos_recovery_method = "closed_class_whitelist"
                pos_recovery_confidence = "high"
            elif w_norm in conjunctions_set:
                pos_resolved = "conjunction"
                pos_status = "recovered"
                pos_recovery_method = "closed_class_whitelist"
                pos_recovery_confidence = "high"
            elif w_norm in prepositions_set:
                pos_resolved = "preposition"
                pos_status = "recovered"
                pos_recovery_method = "closed_class_whitelist"
                pos_recovery_confidence = "high"
            elif w_norm in {'cattle', 'clothes'}:
                pos_resolved = "noun"
                pos_status = "recovered"
                pos_recovery_method = "closed_class_whitelist"
                pos_recovery_confidence = "high"
            elif w_norm == 'close':
                pos_resolved = "adjective"
                pos_status = "recovered"
                pos_recovery_method = "closed_class_whitelist"
                pos_recovery_confidence = "high"
            elif w_norm in {'politically', 'only'}:
                pos_resolved = "adverb"
                pos_status = "recovered"
                pos_recovery_method = "closed_class_whitelist"
                pos_recovery_confidence = "high"
            # D. unique_word_pos
            elif w_norm in word_pos_unique:
                pos_resolved = word_pos_unique[w_norm]
                pos_status = "recovered"
                pos_recovery_method = "unique_word_pos"
                pos_recovery_confidence = "high"
            # E. majority_pos_vote
            elif w_norm in word_pos_majority:
                pos_resolved = word_pos_majority[w_norm]
                pos_status = "recovered"
                pos_recovery_method = "majority_pos_vote"
                pos_recovery_confidence = "medium"
                pos_review_required = True
                
            if pos_status == "recovered":
                recovered_pos_count += 1
                
        # --- Topic Recovery Pipeline ---
        topic_resolved = raw_topic
        topic_status = "natively_populated" if raw_topic else "unmapped"
        topic_recovery_method = "none"
        topic_recovery_confidence = "none"
        topic_review_required = False
        
        if not topic_resolved:
            # A. topic_sheet_reconciliation
            k_reconcile = (w_norm, g_norm, lvl_norm)
            if k_reconcile in topic_sheet_lookup and 'topic' in topic_sheet_lookup[k_reconcile]:
                topic_resolved = topic_sheet_lookup[k_reconcile]['topic']
                topic_status = "recovered"
                topic_recovery_method = "topic_sheet_reconciliation"
                topic_recovery_confidence = "high"
            # B. same_word_guideword_exact
            elif (w_norm, g_norm) in word_guide_topic and len(word_guide_topic[(w_norm, g_norm)]) == 1:
                topic_resolved = list(word_guide_topic[(w_norm, g_norm)])[0]
                topic_status = "recovered"
                topic_recovery_method = "same_word_guideword_exact"
                topic_recovery_confidence = "high"
            # C. unanimous_word_majority
            # If word_topic_unique matches, it is high confidence.
            # If word_topic_majority matches, it is medium confidence.
            elif w_norm in word_topic_unique:
                topic_resolved = word_topic_unique[w_norm]
                topic_status = "recovered"
                topic_recovery_method = "unanimous_word_majority"
                topic_recovery_confidence = "high"
            elif w_norm in word_topic_majority:
                topic_resolved = word_topic_majority[w_norm]
                topic_status = "recovered"
                topic_recovery_method = "unanimous_word_majority"
                topic_recovery_confidence = "medium"
                topic_review_required = True
            # D. guideword_heuristics
            elif 'money' in g_norm or 'cash' in g_norm or 'pay' in g_norm:
                topic_resolved = "money"
                topic_status = "recovered"
                topic_recovery_method = "guideword_heuristics"
                topic_recovery_confidence = "high"
            elif 'animal' in g_norm or 'pet' in g_norm or 'dog' in g_norm or 'cat' in g_norm:
                topic_resolved = "animals"
                topic_status = "recovered"
                topic_recovery_method = "guideword_heuristics"
                topic_recovery_confidence = "high"
            elif 'clothes' in g_norm or 'wear' in g_norm:
                topic_resolved = "clothes"
                topic_status = "recovered"
                topic_recovery_method = "guideword_heuristics"
                topic_recovery_confidence = "high"
            elif 'health' in g_norm or 'ill' in g_norm or 'sick' in g_norm or 'doctor' in g_norm or 'medical' in g_norm:
                topic_resolved = "body and health"
                topic_status = "recovered"
                topic_recovery_method = "guideword_heuristics"
                topic_recovery_confidence = "high"
            elif 'food' in g_norm or 'drink' in g_norm or 'eat' in g_norm or 'restaurant' in g_norm:
                topic_resolved = "food and drink"
                topic_status = "recovered"
                topic_recovery_method = "guideword_heuristics"
                topic_recovery_confidence = "high"
            elif 'travel' in g_norm or 'trip' in g_norm or 'fly' in g_norm or 'airport' in g_norm or 'train' in g_norm or 'bus' in g_norm:
                topic_resolved = "travel"
                topic_status = "recovered"
                topic_recovery_method = "guideword_heuristics"
                topic_recovery_confidence = "high"
            elif 'work' in g_norm or 'job' in g_norm or 'office' in g_norm or 'employ' in g_norm:
                topic_resolved = "work"
                topic_status = "recovered"
                topic_recovery_method = "guideword_heuristics"
                topic_recovery_confidence = "high"
            elif 'crime' in g_norm or 'police' in g_norm or 'law' in g_norm or 'steal' in g_norm or 'rob' in g_norm or 'murder' in g_norm:
                topic_resolved = "crime"
                topic_status = "recovered"
                topic_recovery_method = "guideword_heuristics"
                topic_recovery_confidence = "high"
            # E. closed_class_mapping
            elif pos_resolved in ['determiner', 'pronoun', 'preposition', 'conjunction', 'modal verb', 'auxiliary verb']:
                topic_resolved = "describing things"
                topic_status = "recovered"
                topic_recovery_method = "closed_class_mapping"
                topic_recovery_confidence = "medium"
                topic_review_required = True
                
            if topic_status == "recovered":
                recovered_topic_count += 1
                
        # Resolve overall recovery method and confidence to store in records
        # If both recovered, we can document the methods/confidence.
        # Since fields are single, we document topic recovery details or combine them.
        # The prompt asks for: recovery_method, recovery_confidence, review_required
        # We can set recovery_method to the topic recovery method if recovered, or POS recovery method if POS recovered, or a combined string.
        # To be clean, let's store them as:
        # If topic was recovered: use topic's recovery method.
        # If only POS was recovered: use POS's recovery method.
        # If neither was recovered: "none".
        rec_method = "none"
        rec_confidence = "none"
        rec_review = False
        
        if topic_status == "recovered":
            rec_method = topic_recovery_method
            rec_confidence = topic_recovery_confidence
            rec_review = topic_review_required
        elif pos_status == "recovered":
            rec_method = pos_recovery_method
            rec_confidence = pos_recovery_confidence
            rec_review = pos_review_required
            
        if topic_recovery_method != "none":
            topic_method_counts[topic_recovery_method] = topic_method_counts.get(topic_recovery_method, 0) + 1
        if pos_recovery_method != "none":
            pos_method_counts[pos_recovery_method] = pos_method_counts.get(pos_recovery_method, 0) + 1

        # Determine lexical_type
        # If POS is phrase/phrasal verb, or word contains space
        p_resolved_norm = pos_resolved.lower()
        if p_resolved_norm in ["phrase", "phrasal verb"] or " " in word:
            lexical_type = "phrase"
        else:
            lexical_type = "word"

        # Create record
        rec = {
            "vocab_id": vocab_id,
            "word": word,
            "guideword": guideword,
            "level": level,
            "details": details,
            "raw_topic": raw_topic,
            "raw_pos": raw_pos,
            "topic": topic_resolved,
            "topic_status": topic_status,
            "part_of_speech": pos_resolved,
            "pos_status": pos_status,
            "duplicate_status": "canonical", # placeholder, will be resolved next
            "recovery_method": rec_method,
            "recovery_confidence": rec_confidence,
            "review_required": rec_review,
            "lexical_type": lexical_type,
            "frequency_band": "",
            "exam_tags": [],
            "theme_candidates": [],
            "active": False, # placeholder, resolved next
            "excel_row": excel_row_num,
            "topic_recovery_method": topic_recovery_method,
            "pos_recovery_method": pos_recovery_method
        }
        records.append(rec)
        
    # --- Duplicate Policy Resolution ---
    # Key: (word_norm, guide_norm, level_norm, pos_norm, topic_norm) using resolved values!
    # Group records by duplicate key
    dup_groups = {}
    for idx, r in enumerate(records):
        key = (
            norm(r["word"]),
            norm(r["guideword"]),
            norm(r["level"]),
            norm(r["part_of_speech"]),
            norm(r["topic"])
        )
        if key not in dup_groups:
            dup_groups[key] = []
        dup_groups[key].append(idx)
        
    canonical_count = 0
    redundant_count = 0
    
    for key, indices in dup_groups.items():
        # First index is canonical
        first_idx = indices[0]
        records[first_idx]["duplicate_status"] = "canonical"
        canonical_count += 1
        
        # All subsequent indices are redundant
        for other_idx in indices[1:]:
            records[other_idx]["duplicate_status"] = "redundant"
            redundant_count += 1
            
        # Combine Excel row numbers in canonical row for traceability
        combined_rows = [records[i]["excel_row"] for i in indices]
        records[first_idx]["source_rows"] = combined_rows
        
        for other_idx in indices[1:]:
            records[other_idx]["source_rows"] = [records[other_idx]["excel_row"]]

    # --- Active Status Determination ---
    # active = true only if:
    # - canonical
    # - level != C2
    # - topic resolved
    # - pos resolved
    active_rows_count = 0
    active_counts_by_level = {"A1": 0, "A2": 0, "B1": 0, "B2": 0, "C1": 0}
    
    for r in records:
        is_canonical = r["duplicate_status"] == "canonical"
        is_not_c2 = norm(r["level"]) != "c2"
        is_topic_resolved = r["topic"] != "" and r["topic_status"] != "unmapped"
        is_pos_resolved = r["part_of_speech"] != "" and r["pos_status"] != "unmapped"
        
        if is_canonical and is_not_c2 and is_topic_resolved and is_pos_resolved:
            r["active"] = True
            active_rows_count += 1
            lvl = r["level"]
            if lvl in active_counts_by_level:
                active_counts_by_level[lvl] += 1
        else:
            r["active"] = False

    # Clean temporary helper keys from records before writing
    for r in records:
        r.pop("excel_row", None)
        # We can keep topic_recovery_method and pos_recovery_method since they are useful details, or pop them
        # Let's keep them as they are very helpful for traceability!

    # 4. Write normalized vocabulary JSON
    vocabulary_json_path = os.path.join(json_dir, "vocabulary.json")
    with open(vocabulary_json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
        
    # 5. Write mapping files
    # vocabulary_level_mapping.json
    vocab_level_mapping = {
        "mappings": {
            "A1": {
                "target_level": "A1",
                "active": True
            },
            "A2": {
                "target_level": "A2 candidate pool",
                "active": True
            },
            "B1": {
                "target_level": "B1 candidate pool",
                "active": True
            },
            "B2": {
                "target_level": "B2 candidate pool",
                "active": True
            },
            "C1": {
                "target_level": "C1 candidate pool",
                "active": True
            },
            "C2": {
                "target_level": "C2",
                "active": False,
                "exclusion_reason": "excluded from active generation by default"
            }
        },
        "plus_level_splits": {
            "A1_plus": "pending S3",
            "A2_plus": "pending S3",
            "B1_plus": "pending S3",
            "B2_plus": "pending S3"
        }
    }
    vocab_level_mapping_path = os.path.join(mapping_dir, "vocabulary_level_mapping.json")
    with open(vocab_level_mapping_path, "w", encoding="utf-8") as f:
        json.dump(vocab_level_mapping, f, indent=2, ensure_ascii=False)
        
    # topic_mapping.json
    topic_mapping = {
        "topics": [
            "animals",
            "arts and media",
            "body and health",
            "clothes",
            "communication",
            "crime",
            "describing things",
            "education",
            "food and drink",
            "homes and buildings",
            "money",
            "natural world",
            "people: actions",
            "relationships",
            "travel",
            "people: appearance",
            "people: personality",
            "shopping",
            "technology",
            "politics",
            "work"
        ],
        "theme_mapping": {
            "animals": "animals",
            "arts and media": "arts_and_media",
            "body and health": "health_and_medical",
            "clothes": "clothes",
            "communication": "social_and_communication",
            "crime": "crime",
            "describing things": "describing_things",
            "education": "education",
            "food and drink": "food_and_drink",
            "homes and buildings": "homes_and_buildings",
            "money": "money",
            "natural world": "natural_world",
            "people: actions": "people_actions",
            "relationships": "relationships",
            "travel": "travel_and_weather",
            "people: appearance": "people_appearance",
            "people: personality": "people_personality",
            "shopping": "shopping_and_transactions",
            "technology": "technology",
            "politics": "politics",
            "work": "work_and_jobs"
        }
    }
    topic_mapping_path = os.path.join(mapping_dir, "topic_mapping.json")
    with open(topic_mapping_path, "w", encoding="utf-8") as f:
        json.dump(topic_mapping, f, indent=2, ensure_ascii=False)
        
    # 6. Write Report
    report = {
        "total_rows": len(df_total),
        "imported_rows": len(records),
        "active_rows": active_rows_count,
        "recovered_topic_count": recovered_topic_count,
        "recovered_pos_count": recovered_pos_count,
        "canonical_count": canonical_count,
        "redundant_count": redundant_count,
        "active_counts_by_level": active_counts_by_level,
        "recovery_method_breakdown": {
            "topic": topic_method_counts,
            "pos": pos_method_counts
        }
    }
    report_path = os.path.join(report_dir, "vocab_import_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    print("Vocabulary import completed successfully.")
    print(f"Total rows: {len(df_total)}")
    print(f"Active rows: {active_rows_count}")
    print(f"Recovered topics: {recovered_topic_count}")
    print(f"Recovered POS: {recovered_pos_count}")

if __name__ == "__main__":
    main()
