import os
import json

def normalize_topic(t):
    if not t:
        return ""
    return " ".join(str(t).lower().replace("-", " ").replace(":", " ").split())

def main():
    # 1. Paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    vocab_json_path = os.path.join(base_dir, "vocabulary", "json", "vocabulary.json")
    
    themes_dir = os.path.join(base_dir, "themes")
    reports_dir = os.path.join(base_dir, "output", "reports")
    
    os.makedirs(themes_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)
    
    # 2. Load vocabulary.json
    with open(vocab_json_path, "r", encoding="utf-8") as f:
        vocab_data = json.load(f)
        
    # 3. Define the 21 Themes
    # Each theme entry includes design parameters
    themes_db = [
        # --- A1 Level (9 themes) ---
        {
            "theme_id": "a1_personal_information_and_greetings",
            "theme_name": "個人資訊與社交問候",
            "level": "A1",
            "parent_theme": "Social Interaction",
            "primary_topics": ["relationships", "people: appearance", "people: personality"],
            "secondary_topics": ["communication", "describing things"],
            "blocked_topics": ["crime", "politics", "work"],
            "preferred_frequency_bands": ["tier_1", "tier_2"],
            "allowed_cefr_levels": ["A1"],
            "exam_alignment": {
                "exam_name": "Cambridge Starters",
                "exam_priority_boost": 2.0,
                "restricted_syllabus": True
            },
            "progression_stage": "A1",
            "description": "自我介紹、問候與描述親友特徵。",
            "prev_theme_id": None,
            "next_theme_id": "a2_socializing_and_discussion"
        },
        {
            "theme_id": "a1_daily_life_and_routines",
            "theme_name": "日常生活與作息",
            "level": "A1",
            "parent_theme": "Daily Life",
            "primary_topics": ["food and drink", "homes and buildings"],
            "secondary_topics": ["people: actions", "describing things"],
            "blocked_topics": ["crime", "politics", "technology"],
            "preferred_frequency_bands": ["tier_1", "tier_2"],
            "allowed_cefr_levels": ["A1"],
            "exam_alignment": {
                "exam_name": "Cambridge Starters",
                "exam_priority_boost": 2.0,
                "restricted_syllabus": True
            },
            "progression_stage": "A1",
            "description": "描述幾點起床、吃三餐等例行公事與時間安排。",
            "prev_theme_id": None,
            "next_theme_id": "a2_daily_transactions_and_local_environment"
        },
        {
            "theme_id": "a1_school_and_classroom",
            "theme_name": "學校與教室情境",
            "level": "A1",
            "parent_theme": "Education",
            "primary_topics": ["education"],
            "secondary_topics": ["communication", "describing things"],
            "blocked_topics": ["crime", "politics", "travel"],
            "preferred_frequency_bands": ["tier_1", "tier_2"],
            "allowed_cefr_levels": ["A1"],
            "exam_alignment": {
                "exam_name": "Cambridge Starters",
                "exam_priority_boost": 2.0,
                "restricted_syllabus": True
            },
            "progression_stage": "A1",
            "description": "聽懂教室指令、指認文具物品、基礎顏色與數字認知。",
            "prev_theme_id": None,
            "next_theme_id": "b2_professional_and_academic_situations"
        },
        {
            "theme_id": "a1_homes_and_neighborhoods",
            "theme_name": "居家與生活環境",
            "level": "A1",
            "parent_theme": "Daily Life",
            "primary_topics": ["homes and buildings", "natural world"],
            "secondary_topics": ["travel", "describing things"],
            "blocked_topics": ["crime", "politics", "work"],
            "preferred_frequency_bands": ["tier_1", "tier_2"],
            "allowed_cefr_levels": ["A1"],
            "exam_alignment": {
                "exam_name": "Cambridge Starters",
                "exam_priority_boost": 2.0,
                "restricted_syllabus": True
            },
            "progression_stage": "A1",
            "description": "描述居住城市、家裡房間配置及簡單指引方向。",
            "prev_theme_id": None,
            "next_theme_id": "a2_daily_transactions_and_local_environment"
        },
        {
            "theme_id": "a1_shopping_and_basic_transactions",
            "theme_name": "購物與基礎交易",
            "level": "A1",
            "parent_theme": "Transactions",
            "primary_topics": ["shopping", "money"],
            "secondary_topics": ["communication", "describing things"],
            "blocked_topics": ["crime", "politics", "education"],
            "preferred_frequency_bands": ["tier_1", "tier_2"],
            "allowed_cefr_levels": ["A1"],
            "exam_alignment": {
                "exam_name": "Cambridge Starters",
                "exam_priority_boost": 2.0,
                "restricted_syllabus": True
            },
            "progression_stage": "A1",
            "description": "基本買賣如買車票、簡單服飾購物與問價錢。",
            "prev_theme_id": None,
            "next_theme_id": "a2_travel_and_consumption"
        },
        {
            "theme_id": "a1_food_and_dining",
            "theme_name": "飲食與餐廳點餐",
            "level": "A1",
            "parent_theme": "Transactions",
            "primary_topics": ["food and drink"],
            "secondary_topics": ["shopping", "describing things"],
            "blocked_topics": ["crime", "politics", "technology"],
            "preferred_frequency_bands": ["tier_1", "tier_2"],
            "allowed_cefr_levels": ["A1"],
            "exam_alignment": {
                "exam_name": "Cambridge Starters",
                "exam_priority_boost": 2.0,
                "restricted_syllabus": True
            },
            "progression_stage": "A1",
            "description": "餐廳點餐、點外賣及表達對食物飲料的喜好。",
            "prev_theme_id": None,
            "next_theme_id": "a2_travel_and_consumption"
        },
        {
            "theme_id": "a1_interests_and_abilities",
            "theme_name": "興趣、休閒與能力",
            "level": "A1",
            "parent_theme": "Personal Life",
            "primary_topics": ["arts and media", "people: actions"],
            "secondary_topics": ["relationships", "describing things"],
            "blocked_topics": ["crime", "politics", "work"],
            "preferred_frequency_bands": ["tier_1", "tier_2"],
            "allowed_cefr_levels": ["A1"],
            "exam_alignment": {
                "exam_name": "Cambridge Starters",
                "exam_priority_boost": 2.0,
                "restricted_syllabus": True
            },
            "progression_stage": "A1",
            "description": "談論常玩的運動與表達自己會與不會的才藝。",
            "prev_theme_id": None,
            "next_theme_id": "b1_personal_expression_and_socializing"
        },
        {
            "theme_id": "a1_travel_and_weather",
            "theme_name": "旅遊、交通與天氣",
            "level": "A1",
            "parent_theme": "Travel",
            "primary_topics": ["travel", "natural world"],
            "secondary_topics": ["describing things", "people: actions"],
            "blocked_topics": ["crime", "politics", "education"],
            "preferred_frequency_bands": ["tier_1", "tier_2"],
            "allowed_cefr_levels": ["A1"],
            "exam_alignment": {
                "exam_name": "Cambridge Starters",
                "exam_priority_boost": 2.0,
                "restricted_syllabus": True
            },
            "progression_stage": "A1",
            "description": "談論簡單旅遊計畫、交通工具與天氣狀況。",
            "prev_theme_id": None,
            "next_theme_id": "a2_travel_and_consumption"
        },
        {
            "theme_id": "a1_health_and_medical",
            "theme_name": "健康與醫療",
            "level": "A1",
            "parent_theme": "Personal Life",
            "primary_topics": ["body and health"],
            "secondary_topics": ["people: actions", "describing things"],
            "blocked_topics": ["crime", "politics", "shopping"],
            "preferred_frequency_bands": ["tier_1", "tier_2"],
            "allowed_cefr_levels": ["A1"],
            "exam_alignment": {
                "exam_name": "Cambridge Starters",
                "exam_priority_boost": 2.0,
                "restricted_syllabus": True
            },
            "progression_stage": "A1",
            "description": "用基礎詞彙簡單描述身體部位與常見健康症狀（如頭痛）。",
            "prev_theme_id": None,
            "next_theme_id": "b1_personal_expression_and_socializing"
        },
        
        # --- A1+ Level (1 theme) ---
        {
            "theme_id": "a1_plus_spiral_expansion",
            "theme_name": "A1 生活情境螺旋擴充",
            "level": "A1_plus",
            "parent_theme": "Daily Life (Bridge)",
            "primary_topics": ["food and drink", "homes and buildings", "travel"],
            "secondary_topics": ["communication", "describing things", "natural world"],
            "blocked_topics": ["crime", "politics", "work"],
            "preferred_frequency_bands": ["tier_1", "tier_2", "tier_3"],
            "allowed_cefr_levels": ["A1", "A2"],
            "exam_alignment": {
                "exam_name": "Cambridge Movers",
                "exam_priority_boost": 2.0,
                "restricted_syllabus": False
            },
            "progression_stage": "A1_plus",
            "description": "維持 A1 的生活情境，但引入「過去發生的事」與「邏輯因果」的語境。交代過去發生的事件與原因。",
            "prev_theme_id": "a1_daily_life_and_routines",
            "next_theme_id": "a2_daily_transactions_and_local_environment"
        },
        
        # --- A2 Level (3 themes) ---
        {
            "theme_id": "a2_daily_transactions_and_local_environment",
            "theme_name": "日常實務與當地環境",
            "level": "A2",
            "parent_theme": "Daily Life",
            "primary_topics": ["natural world", "relationships", "work"],
            "secondary_topics": ["homes and buildings", "communication"],
            "blocked_topics": ["crime", "politics"],
            "preferred_frequency_bands": ["tier_1", "tier_2", "tier_3"],
            "allowed_cefr_levels": ["A1", "A2"],
            "exam_alignment": {
                "exam_name": "Cambridge Movers",
                "exam_priority_boost": 1.5,
                "restricted_syllabus": False
            },
            "progression_stage": "A2",
            "description": "基本個人與家庭背景、當地地理環境、工作就業等相關情境。",
            "prev_theme_id": "a1_daily_life_and_routines",
            "next_theme_id": "b1_work_and_business_environment"
        },
        {
            "theme_id": "a2_travel_and_consumption",
            "theme_name": "出行與消費",
            "level": "A2",
            "parent_theme": "Transactions",
            "primary_topics": ["travel", "shopping", "money"],
            "secondary_topics": ["homes and buildings", "communication"],
            "blocked_topics": ["crime", "politics", "education"],
            "preferred_frequency_bands": ["tier_1", "tier_2", "tier_3"],
            "allowed_cefr_levels": ["A1", "A2"],
            "exam_alignment": {
                "exam_name": "Cambridge Flyers",
                "exam_priority_boost": 1.5,
                "restricted_syllabus": False
            },
            "progression_stage": "A2",
            "description": "在商店、郵局、銀行進行簡單交易，詢問與指引方向、使用大眾交通工具、購買車票、安排住宿與點餐。",
            "prev_theme_id": "a1_food_and_dining",
            "next_theme_id": "b1_travel_and_living_abroad"
        },
        {
            "theme_id": "a2_socializing_and_discussion",
            "theme_name": "社交與討論",
            "level": "A2",
            "parent_theme": "Social Interaction",
            "primary_topics": ["relationships", "people: personality", "communication"],
            "secondary_topics": ["people: actions", "describing things"],
            "blocked_topics": ["crime", "politics", "technology"],
            "preferred_frequency_bands": ["tier_1", "tier_2", "tier_3"],
            "allowed_cefr_levels": ["A1", "A2"],
            "exam_alignment": {
                "exam_name": "A2 Key",
                "exam_priority_boost": 1.5,
                "restricted_syllabus": False
            },
            "progression_stage": "A2",
            "description": "討論週末計畫、提議要去哪裡或做什麼、建立社交聯繫（如邀請、道歉、表達感謝），以及簡單描述自己的過去經驗、習慣與生活條件。",
            "prev_theme_id": "a1_personal_information_and_greetings",
            "next_theme_id": "b1_personal_expression_and_socializing"
        },
        
        # --- A2+ Level (1 theme) ---
        {
            "theme_id": "a2_plus_roleplay_and_skills",
            "theme_name": "生活素養角色扮演",
            "level": "A2_plus",
            "parent_theme": "Social Interaction (Bridge)",
            "primary_topics": ["relationships", "communication", "people: actions"],
            "secondary_topics": ["describing things", "work"],
            "blocked_topics": ["crime", "politics"],
            "preferred_frequency_bands": ["tier_1", "tier_2", "tier_3"],
            "allowed_cefr_levels": ["A1", "A2", "B1"],
            "exam_alignment": {
                "exam_name": "A2 Key",
                "exam_priority_boost": 1.5,
                "restricted_syllabus": False
            },
            "progression_stage": "A2_plus",
            "description": "從單純的短句走向「長句堆疊與生活素養」的產出情境。角色扮演與寫作產出。",
            "prev_theme_id": "a2_socializing_and_discussion",
            "next_theme_id": "b1_personal_expression_and_socializing"
        },
        
        # --- B1 Level (3 themes) ---
        {
            "theme_id": "b1_travel_and_living_abroad",
            "theme_name": "旅遊與海外生活",
            "level": "B1",
            "parent_theme": "Travel",
            "primary_topics": ["travel", "money", "shopping"],
            "secondary_topics": ["communication", "relationships"],
            "blocked_topics": ["politics", "education"],
            "preferred_frequency_bands": ["tier_1", "tier_2", "tier_3"],
            "allowed_cefr_levels": ["A1", "A2", "B1"],
            "exam_alignment": {
                "exam_name": "B1 Preliminary",
                "exam_priority_boost": 1.5,
                "restricted_syllabus": False
            },
            "progression_stage": "B1",
            "description": "處理在英語系國家旅遊時可能遇到的大多數狀況（如安排交通住宿、向權責機關交涉、客訴與退換不滿意的商品）。",
            "prev_theme_id": "a2_travel_and_consumption",
            "next_theme_id": "b2_in_depth_debates_and_meetings"
        },
        {
            "theme_id": "b1_work_and_business_environment",
            "theme_name": "職場與商業環境",
            "level": "B1",
            "parent_theme": "Work",
            "primary_topics": ["work", "money", "technology"],
            "secondary_topics": ["communication", "people: actions"],
            "blocked_topics": ["animals", "clothes"],
            "preferred_frequency_bands": ["tier_1", "tier_2", "tier_3"],
            "allowed_cefr_levels": ["A1", "A2", "B1"],
            "exam_alignment": {
                "exam_name": "B1 Preliminary",
                "exam_priority_boost": 1.5,
                "restricted_syllabus": False
            },
            "progression_stage": "B1",
            "description": "進行簡單的商業溝通與協商、參與團隊腦力激盪與會議、處理客戶詢問與抱怨、撰寫報告與商務信件。",
            "prev_theme_id": "a2_daily_transactions_and_local_environment",
            "next_theme_id": "b2_professional_and_academic_situations"
        },
        {
            "theme_id": "b1_personal_expression_and_socializing",
            "theme_name": "個人表達與社交",
            "level": "B1",
            "parent_theme": "Personal Life",
            "primary_topics": ["arts and media", "relationships", "people: personality"],
            "secondary_topics": ["communication", "describing things"],
            "blocked_topics": ["crime", "politics"],
            "preferred_frequency_bands": ["tier_1", "tier_2", "tier_3"],
            "allowed_cefr_levels": ["A1", "A2", "B1"],
            "exam_alignment": {
                "exam_name": "B1 Preliminary",
                "exam_priority_boost": 1.5,
                "restricted_syllabus": False
            },
            "progression_stage": "B1",
            "description": "描述經驗、事件、夢想與抱負，並能針對抽象或文化主題（如電影、音樂、大眾運輸的優缺點）簡述自己的意見與理由。",
            "prev_theme_id": "a2_socializing_and_discussion",
            "next_theme_id": "b2_native_speed_communication"
        },
        
        # --- B1+ Level (1 theme) ---
        {
            "theme_id": "b1_plus_critical_discussion",
            "theme_name": "觀點論述與思辨",
            "level": "B1_plus",
            "parent_theme": "Critical Thinking (Bridge)",
            "primary_topics": ["communication", "politics", "people: personality"],
            "secondary_topics": ["describing things", "work"],
            "blocked_topics": ["animals", "clothes"],
            "preferred_frequency_bands": ["tier_1", "tier_2", "tier_3", "tier_4"],
            "allowed_cefr_levels": ["A1", "A2", "B1", "B2"],
            "exam_alignment": {
                "exam_name": "B1 Preliminary",
                "exam_priority_boost": 1.5,
                "restricted_syllabus": False
            },
            "progression_stage": "B1_plus",
            "description": "從「生活對話」走向「觀點論述」與高層次思考。思辨與辯論、挑戰「一詞多義（Polysemy）」的深度閱讀，並針對各種廣泛主題闡述利弊。",
            "prev_theme_id": "b1_personal_expression_and_socializing",
            "next_theme_id": "b2_in_depth_debates_and_meetings"
        },
        
        # --- B2 Level (3 themes) ---
        {
            "theme_id": "b2_professional_and_academic_situations",
            "theme_name": "專業與學術情境",
            "level": "B2",
            "parent_theme": "Academic Life",
            "primary_topics": ["education", "work", "technology"],
            "secondary_topics": ["communication", "describing things"],
            "blocked_topics": ["animals", "clothes"],
            "preferred_frequency_bands": ["tier_1", "tier_2", "tier_3", "tier_4"],
            "allowed_cefr_levels": ["A1", "A2", "B1", "B2"],
            "exam_alignment": {
                "exam_name": "General B2",
                "exam_priority_boost": 1.0,
                "restricted_syllabus": False
            },
            "progression_stage": "B2",
            "description": "參與自身專業領域內的技術討論、閱讀當代文學與專業報告、理解電視新聞與紀錄片。",
            "prev_theme_id": "b1_work_and_business_environment",
            "next_theme_id": "c1_advanced_work_and_socializing"
        },
        {
            "theme_id": "b2_in_depth_debates_and_meetings",
            "theme_name": "深入辯論與會議",
            "level": "B2",
            "parent_theme": "Social Interaction",
            "primary_topics": ["politics", "crime", "work"],
            "secondary_topics": ["communication", "describing things"],
            "blocked_topics": ["food and drink", "animals"],
            "preferred_frequency_bands": ["tier_1", "tier_2", "tier_3", "tier_4"],
            "allowed_cefr_levels": ["A1", "A2", "B1", "B2"],
            "exam_alignment": {
                "exam_name": "General B2",
                "exam_priority_boost": 1.0,
                "restricted_syllabus": False
            },
            "progression_stage": "B2",
            "description": "在職場會議 or 社交場合中，能針對社會時事、政治、健康、科技等議題參與正式辯論，流暢地分析各種選項的優缺點並捍衛自己的觀點。",
            "prev_theme_id": "b1_travel_and_living_abroad",
            "next_theme_id": "c1_precise_expression"
        },
        {
            "theme_id": "b2_native_speed_communication",
            "theme_name": "母語人士交流",
            "level": "B2",
            "parent_theme": "Social Interaction",
            "primary_topics": ["communication", "relationships", "people: personality"],
            "secondary_topics": ["describing things", "people: actions"],
            "blocked_topics": ["politics", "crime"],
            "preferred_frequency_bands": ["tier_1", "tier_2", "tier_3", "tier_4"],
            "allowed_cefr_levels": ["A1", "A2", "B1", "B2"],
            "exam_alignment": {
                "exam_name": "General B2",
                "exam_priority_boost": 1.0,
                "restricted_syllabus": False
            },
            "progression_stage": "B2",
            "description": "在正常語速甚至嘈雜的環境下，能與母語人士進行流暢且自然的互動，雙方都不會感到吃力。",
            "prev_theme_id": "b1_personal_expression_and_socializing",
            "next_theme_id": "c1_precise_expression"
        },
        
        # --- B2+ Level (1 theme) ---
        {
            "theme_id": "b2_plus_academic_bridge",
            "theme_name": "學術與專業過渡橋樑",
            "level": "B2_plus",
            "parent_theme": "Academic Life (Bridge)",
            "primary_topics": ["education", "work", "technology", "communication"],
            "secondary_topics": ["describing things", "politics"],
            "blocked_topics": ["animals"],
            "preferred_frequency_bands": ["tier_1", "tier_2", "tier_3", "tier_4"],
            "allowed_cefr_levels": ["A1", "A2", "B1", "B2", "C1"],
            "exam_alignment": {
                "exam_name": "General B2",
                "exam_priority_boost": 1.0,
                "restricted_syllabus": False
            },
            "progression_stage": "B2_plus",
            "description": "邁向 C1 的橋樑，學術與專業字彙擴充、流暢結構化寫作與正式演說，準備應對學術與專業要求。",
            "prev_theme_id": "b2_professional_and_academic_situations",
            "next_theme_id": "c1_advanced_work_and_socializing"
        },
        
        # --- C1 Level (3 themes) ---
        {
            "theme_id": "c1_advanced_work_and_socializing",
            "theme_name": "高難度職場與社交",
            "level": "C1",
            "parent_theme": "Work",
            "primary_topics": ["work", "politics", "money"],
            "secondary_topics": ["communication", "relationships"],
            "blocked_topics": ["animals"],
            "preferred_frequency_bands": ["tier_1", "tier_2", "tier_3", "tier_4"],
            "allowed_cefr_levels": ["A1", "A2", "B1", "B2", "C1"],
            "exam_alignment": {
                "exam_name": "General C1",
                "exam_priority_boost": 1.0,
                "restricted_syllabus": False
            },
            "progression_stage": "C1",
            "description": "能自如地帶領會議、進行複雜且微妙的談判、應對具有敵意或困難的提問，並能彈性切換正式與非正式的語氣與風格。",
            "prev_theme_id": "b2_professional_and_academic_situations",
            "next_theme_id": None
        },
        {
            "theme_id": "c1_implicit_meanings_and_complex_texts",
            "theme_name": "言外之意與複雜文本",
            "level": "C1",
            "parent_theme": "Critical Thinking",
            "primary_topics": ["arts and media", "communication", "people: personality"],
            "secondary_topics": ["describing things", "relationships"],
            "blocked_topics": ["money"],
            "preferred_frequency_bands": ["tier_1", "tier_2", "tier_3", "tier_4"],
            "allowed_cefr_levels": ["A1", "A2", "B1", "B2", "C1"],
            "exam_alignment": {
                "exam_name": "General C1",
                "exam_priority_boost": 1.0,
                "restricted_syllabus": False
            },
            "progression_stage": "C1",
            "description": "能理解隱含意義（如諷刺、幽默、暗示或隱含的批評）、處理超出自己專業領域的長篇複雜文本及充滿俚語的電影。",
            "prev_theme_id": "b2_native_speed_communication",
            "next_theme_id": None
        },
        {
            "theme_id": "c1_precise_expression",
            "theme_name": "精準表達",
            "level": "C1",
            "parent_theme": "Personal Life",
            "primary_topics": ["communication", "describing things", "politics"],
            "secondary_topics": ["people: actions", "work"],
            "blocked_topics": [],
            "preferred_frequency_bands": ["tier_1", "tier_2", "tier_3", "tier_4"],
            "allowed_cefr_levels": ["A1", "A2", "B1", "B2", "C1"],
            "exam_alignment": {
                "exam_name": "General C1",
                "exam_priority_boost": 1.0,
                "restricted_syllabus": False
            },
            "progression_stage": "C1",
            "description": "即使是抽象且陌生的主題，也能毫不費力地流暢表達，精準控制語句的銜接與組織，幾乎不會出現明顯尋找詞彙的停頓。",
            "prev_theme_id": "b2_native_speed_communication",
            "next_theme_id": None
        }
    ]
    
    # 4. Perform vocabulary pool linking calculations for each theme
    # Normalize topics for exact comparisons
    normalized_primary_count_all = 0
    normalized_secondary_count_all = 0
    normalized_blocked_count_all = 0
    
    coverage_report = {}
    
    for theme in themes_db:
        allowed_lvls = [lvl.lower() for lvl in theme["allowed_cefr_levels"]]
        primary_norms = [normalize_topic(t) for t in theme["primary_topics"]]
        secondary_norms = [normalize_topic(t) for t in theme["secondary_topics"]]
        blocked_norms = [normalize_topic(t) for t in theme["blocked_topics"]]
        
        normalized_primary_count_all += len(primary_norms)
        normalized_secondary_count_all += len(secondary_norms)
        normalized_blocked_count_all += len(blocked_norms)
        
        # Word counters
        vocab_count = 0  # matches primary+secondary and allowed_cefr_levels, irrespective of active status
        active_vocab_count = 0  # matches primary+secondary and allowed_cefr_levels, and active=True
        primary_active_count = 0  # matches primary and allowed_cefr_levels and active=True
        secondary_active_count = 0  # matches secondary and allowed_cefr_levels and active=True
        
        for r in vocab_data:
            r_lvl = str(r.get("level", "")).strip().lower()
            r_topic_norm = normalize_topic(r.get("topic", ""))
            
            # Check level allowance
            if r_lvl not in allowed_lvls:
                continue
                
            # Check topic membership
            is_primary = r_topic_norm in primary_norms
            is_secondary = r_topic_norm in secondary_norms
            
            if is_primary or is_secondary:
                vocab_count += 1
                if r.get("active", False):
                    active_vocab_count += 1
                    if is_primary:
                        primary_active_count += 1
                    if is_secondary:
                        secondary_active_count += 1
                        
        # Store resolved counts in theme entry
        theme["vocabulary_count"] = vocab_count
        theme["active_vocabulary_count"] = active_vocab_count
        theme["primary_topic_word_count"] = primary_active_count
        theme["secondary_topic_word_count"] = secondary_active_count
        
        coverage_report[theme["theme_id"]] = {
            "theme_name": theme["theme_name"],
            "level": theme["level"],
            "vocabulary_count": vocab_count,
            "active_vocabulary_count": active_vocab_count,
            "primary_topic_word_count": primary_active_count,
            "secondary_topic_word_count": secondary_active_count
        }

    # 5. Define progression chains explicitly for reporting
    progression_chains = [
        [
            "a1_food_and_dining",
            "a2_travel_and_consumption",
            "b1_travel_and_living_abroad",
            "c1_implicit_meanings_and_complex_texts"
        ],
        [
            "a1_daily_life_and_routines",
            "a2_daily_transactions_and_local_environment",
            "b1_work_and_business_environment",
            "b2_professional_and_academic_situations",
            "c1_advanced_work_and_socializing"
        ],
        [
            "a1_personal_information_and_greetings",
            "a2_socializing_and_discussion",
            "b1_personal_expression_and_socializing",
            "b2_native_speed_communication",
            "c1_precise_expression"
        ],
        [
            "a1_travel_and_weather",
            "a2_travel_and_consumption",
            "b1_travel_and_living_abroad",
            "b2_in_depth_debates_and_meetings",
            "c1_precise_expression"
        ]
    ]

    # 6. Generate output files
    # theme_vocab_mapping.json (full database file)
    theme_vocab_mapping_path = os.path.join(themes_dir, "theme_vocab_mapping.json")
    with open(theme_vocab_mapping_path, "w", encoding="utf-8") as f:
        json.dump({"themes": themes_db}, f, indent=2, ensure_ascii=False)
        
    # theme_catalog.json (clean catalog for user-facing views)
    # Includes IDs, Names, Levels, Parents, Stages, Descriptions, and Counts
    catalog_list = []
    for t in themes_db:
        catalog_list.append({
            "theme_id": t["theme_id"],
            "theme_name": t["theme_name"],
            "level": t["level"],
            "parent_theme": t["parent_theme"],
            "progression_stage": t["progression_stage"],
            "description": t["description"],
            "active_vocabulary_count": t["active_vocabulary_count"]
        })
    theme_catalog_path = os.path.join(themes_dir, "theme_catalog.json")
    with open(theme_catalog_path, "w", encoding="utf-8") as f:
        json.dump({"themes": catalog_list}, f, indent=2, ensure_ascii=False)
        
    # theme_mapping_report.json
    report_data = {
        "total_themes": len(themes_db),
        "total_primary_topic_mappings": normalized_primary_count_all,
        "total_secondary_topic_mappings": normalized_secondary_count_all,
        "blocked_topic_mappings": normalized_blocked_count_all,
        "theme_vocabulary_coverage": coverage_report,
        "progression_chains": progression_chains
    }
    report_path = os.path.join(reports_dir, "theme_mapping_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
        
    print("Theme vocabulary mapping completed successfully.")
    print(f"Total themes mapped: {len(themes_db)}")
    print(f"Total progression chains: {len(progression_chains)}")

if __name__ == "__main__":
    main()
