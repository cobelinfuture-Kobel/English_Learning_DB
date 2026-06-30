# Theme Vocabulary Topic Analysis (THEME_DB_S0)

This document analyzes the 21 English Vocabulary Profile (EVP) topics based on their active-ready word counts and semantic domains. This analysis informs how topics are mapped to communicative themes.

---

## 1. Quantitative Topic Overview (Active Counts)

Based on the import audit from `output/reports/vocab_import_report.json`, the active-ready counts for the 21 topics are:

1.  **communication:** 1,194 words — Largest topic. Represents conversational exchange, discourse connectors, and opinion verbs.
2.  **describing things:** 1,144 words — General adjectives and descriptive adverbs.
3.  **people: actions** (including hyphenated raw values): 1,112 words — Active verbs and actions performed by individuals.
4.  **people: personality** (including hyphenated raw values): 975 words — Personality descriptors, feelings, and character traits.
5.  **body and health:** 317 words — Body parts, medical terms, and illness descriptors.
6.  **natural world:** 280 words — Environment, weather, and science terms.
7.  **food and drink:** 273 words — Ingredients, meals, cooking verbs, and restaurant terms.
8.  **arts and media:** 264 words — Literature, movies, media, music, and performance terms.
9.  **travel:** 258 words — Transportation, geography, and vacation terms.
10. **work:** 228 words — Jobs, office interactions, and professional tasks.
11. **shopping:** 226 words — Prices, consumer goods, transactions, and retail locations.
12. **technology:** 188 words — Computers, data, internet, and devices.
13. **homes and buildings:** 181 words — Rooms, architectural features, furniture, and houses.
14. **money:** 177 words — Finance, costs, payments, and banking.
15. **relationships:** 168 words — Family, friends, social connections, and conflict.
16. **people: appearance:** 104 words — Hair, height, clothes accessories, and grooming descriptors.
17. **animals:** 102 words — Pets, wildlife, and animal descriptions.
18. **clothes:** 102 words — Clothing items and styling descriptors.
19. **education:** 100 words — Subjects, courses, schools, and grades.
20. **crime:** 86 words — Law enforcement, illegal actions, and court terms.
21. **politics:** 58 words — Governments, voting, and societal structures.

---

## 2. Semantic Domain Grouping

To map these topics to communicative themes, we group the 21 topics into 6 core semantic domains:

### A. Personal & Social Life
*   *Topics:* `relationships`, `people: personality`, `people: appearance`, `animals`, `clothes`.
*   *Primary Theme Mapping:* Personal details, families, greeting interactions, and describing friends.

### B. Daily Routines & Transactions
*   *Topics:* `food and drink`, `homes and buildings`, `shopping`, `money`.
*   *Primary Theme Mapping:* Daily routines, buying tickets, eating in restaurants, and shopping in banks/shops.

### C. Syntactic & Discourse Frameworks
*   *Topics:* `communication`, `describing things`, `people: actions`.
*   *Primary Theme Mapping:* These serve as **Universal Secondary Topics** for almost all themes. Conjunctions from `communication` and descriptors from `describing things` are necessary to formulate sentences across all topics.

### D. Travel, Weather & Nature
*   *Topics:* `travel`, `natural world`.
*   *Primary Theme Mapping:* Describing weather, planning trips, local directions, and transport.

### E. Professional, Work & Crime
*   *Topics:* `work`, `crime`, `politics`, `technology`.
*   *Primary Theme Mapping:* Business letters, corporate meetings, legal contexts, and abstract debates.

### F. Academic & Creative
*   *Topics:* `education`, `arts and media`.
*   *Primary Theme Mapping:* School routines, reading novels, media critique, and technical fields.
