import os
import json
import re
import pandas as pd

def clean_val(val):
    if pd.isna(val):
        return ""
    return str(val).strip()

def clean_lexical_range(val):
    if pd.isna(val):
        return ""
    try:
        # If it's a float like 2.0, convert to integer first
        return int(float(val))
    except (ValueError, TypeError):
        return str(val).strip()

def main():
    # 1. Paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    excel_path = os.path.join(base_dir, "grammar_profile", "source", "English Grammar Profile Online.xlsx")
    theme_path = os.path.join(base_dir, "docs", "A1_C1_情境.txt")
    
    grammar_json_dir = os.path.join(base_dir, "grammar_profile", "json")
    level_mapping_dir = os.path.join(base_dir, "grammar_profile", "mapping")
    theme_mapping_dir = os.path.join(base_dir, "themes")
    report_dir = os.path.join(base_dir, "output", "reports")
    
    # Create directories if they do not exist
    os.makedirs(grammar_json_dir, exist_ok=True)
    os.makedirs(level_mapping_dir, exist_ok=True)
    os.makedirs(theme_mapping_dir, exist_ok=True)
    os.makedirs(report_dir, exist_ok=True)
    
    # 2. Read grammar profile source Excel
    df = pd.read_excel(excel_path, sheet_name="Data")
    
    records = []
    level_distribution = {}
    duplicate_ids = set()
    seen_ids = set()
    
    missing_can_do_count = 0
    missing_example_count = 0
    warning_rows_info = []
    
    for idx, row in df.iterrows():
        excel_row_num = idx + 2 # Header is row 1, data starts at row 2
        
        raw_id = clean_val(row.get("id"))
        raw_super = clean_val(row.get("SuperCategory"))
        raw_sub = clean_val(row.get("SubCategory"))
        raw_level = clean_val(row.get("Level"))
        raw_lexical = clean_lexical_range(row.get("Lexical Range"))
        raw_guideword = clean_val(row.get("Guideword"))
        raw_cando = clean_val(row.get("Can-do statement"))
        raw_example = clean_val(row.get("Example"))
        
        # Track duplicate IDs
        if raw_id in seen_ids:
            duplicate_ids.add(raw_id)
        seen_ids.add(raw_id)
        
        # Count levels
        if raw_level:
            level_distribution[raw_level] = level_distribution.get(raw_level, 0) + 1
            
        # Check warnings
        warnings = []
        is_missing_cando = not raw_cando
        is_missing_example = not raw_example
        
        if is_missing_cando:
            warnings.append("missing Can-do statement")
            missing_can_do_count += 1
        if is_missing_example:
            warnings.append("missing Example")
            missing_example_count += 1
            
        if warnings:
            warning_rows_info.append({
                "row": excel_row_num,
                "id": raw_id,
                "level": raw_level,
                "guideword": raw_guideword,
                "warnings": warnings
            })
            
        # Construct record
        rec = {
            "id": raw_id,
            "super_category": raw_super,
            "sub_category": raw_sub,
            "level": raw_level,
            "lexical_range": raw_lexical,
            "guideword": raw_guideword,
            "can_do_statement": raw_cando,
            "example": raw_example,
            "source_sheet": "Data",
            "source_row": excel_row_num,
            "import_warnings": warnings
        }
        records.append(rec)
        
    # Write normalized grammar JSON
    grammar_profile_path = os.path.join(grammar_json_dir, "grammar_profile.json")
    with open(grammar_profile_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
        
    # Write import report
    report = {
        "total_rows": len(df),
        "imported_rows": len(records),
        "level_distribution": level_distribution,
        "duplicate_id_count": len(duplicate_ids),
        "missing_can_do_count": missing_can_do_count,
        "missing_example_count": missing_example_count,
        "warning_rows": warning_rows_info
    }
    report_path = os.path.join(report_dir, "source_import_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    # 3. Create level mapping draft
    level_mapping = {
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
                "exclusion_reason": "excluded from active A1-C1 generation by default"
            }
        },
        "plus_level_splits": {
            "A1_plus": "pending S3",
            "A2_plus": "pending S3",
            "B1_plus": "pending S3",
            "B2_plus": "pending S3"
        }
    }
    level_mapping_path = os.path.join(level_mapping_dir, "level_mapping.json")
    with open(level_mapping_path, "w", encoding="utf-8") as f:
        json.dump(level_mapping, f, indent=2, ensure_ascii=False)
        
    # 4. Parse theme categories from docs/A1_C1_情境.txt
    theme_mapping = {}
    level_normalizer = {
        "A1": "A1",
        "A1+": "A1_plus",
        "A2": "A2",
        "A2+": "A2_plus",
        "B1": "B1",
        "B1+": "B1_plus",
        "B2": "B2",
        "B2+": "B2_plus",
        "C1": "C1"
    }
    
    # Initialize all target levels in the theme mapping
    for lvl in level_normalizer.values():
        theme_mapping[lvl] = {
            "mapping_status": "mapped",
            "notes": [],
            "categories": []
        }
        
    if os.path.exists(theme_path):
        with open(theme_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        current_raw_level = None
        for i, line in enumerate(lines, 1):
            line_str = line.strip()
            if not line_str:
                continue
            
            # Check for level header like **A1:**
            lvl_match = re.match(r'^\*\*(.*?)\*\*\s*$', line_str)
            if lvl_match:
                current_raw_level = lvl_match.group(1).rstrip(':').strip()
                continue
                
            if current_raw_level:
                normalized_lvl = level_normalizer.get(current_raw_level)
                if not normalized_lvl:
                    continue
                    
                # Check for category match
                # e.g., 1. **個人資訊與社交問候**：自我介紹... or * **日常實務與當地環境**：基本個人...
                cat_match = re.match(r'^\s*(?:\d+\.|\*)\s*\*\*(.*?)\*\*[:：]\s*(.*)$', line_str)
                if cat_match:
                    cat_name = cat_match.group(1).strip()
                    cat_desc = cat_match.group(2).strip()
                    theme_mapping[normalized_lvl]["categories"].append({
                        "name": cat_name,
                        "description": cat_desc,
                        "source_line": i
                    })
                else:
                    theme_mapping[normalized_lvl]["notes"].append(line_str)
                    
        # Apply special rules for plus levels
        # If explicit categories are missing for plus levels, set mapping_status to descriptive_only
        for lvl in ["A1_plus", "A2_plus", "B1_plus", "B2_plus"]:
            if not theme_mapping[lvl]["categories"]:
                theme_mapping[lvl]["mapping_status"] = "descriptive_only"
                
    theme_mapping_path = os.path.join(theme_mapping_dir, "theme_mapping.json")
    with open(theme_mapping_path, "w", encoding="utf-8") as f:
        json.dump(theme_mapping, f, indent=2, ensure_ascii=False)
        
    print("Source import completed successfully.")
    print(f"Grammar records: {len(records)}")
    print(f"Warnings: {len(warning_rows_info)}")

if __name__ == "__main__":
    main()
