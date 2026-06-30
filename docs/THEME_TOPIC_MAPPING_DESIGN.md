# Theme ↔ Topic Mapping Design (THEME_DB_S0)

This document designs the mapping rules between communicative themes (A1, A2, B1, B2, C1) and vocabulary topics. These rules ensure that generators pull vocabulary that is semantically relevant to the topic while blocking unrelated words.

---

## 1. Mapping Rules for A1 Themes

### A1-T1: 個人資訊與社交問候 (Personal Details)
*   **Primary Topics:** `relationships`, `people: appearance`, `people: personality`.
*   **Secondary Topics:** `communication`, `describing things`.
*   **Blocked Topics:** `crime`, `politics`, `work`.

### A1-T2: 日常生活與作息 (Daily Routines)
*   **Primary Topics:** `food and drink`, `homes and buildings`.
*   **Secondary Topics:** `people: actions`, `describing things`.
*   **Blocked Topics:** `crime`, `politics`, `technology`.

### A1-T3: 學校與教室情境 (School & Classroom)
*   **Primary Topics:** `education`.
*   **Secondary Topics:** `communication`, `describing things`.
*   **Blocked Topics:** `crime`, `politics`, `travel`.

### A1-T4: 居家與生活環境 (Homes & Neighborhoods)
*   **Primary Topics:** `homes and buildings`, `natural world`.
*   **Secondary Topics:** `travel`, `describing things`.
*   **Blocked Topics:** `crime`, `politics`, `work`.

### A1-T5: 購物與基礎交易 (Shopping & Transactions)
*   **Primary Topics:** `shopping`, `money`.
*   **Secondary Topics:** `communication`, `describing things`.
*   **Blocked Topics:** `crime`, `politics`, `education`.

### A1-T6: 飲食與餐廳點餐 (Food & Dining)
*   **Primary Topics:** `food and drink`.
*   **Secondary Topics:** `shopping`, `describing things`.
*   **Blocked Topics:** `crime`, `politics`, `technology`.

### A1-T7: 興趣、休閒與能力 (Interests & Hobbies)
*   **Primary Topics:** `arts and media`, `people: actions`.
*   **Secondary Topics:** `relationships`, `describing things`.
*   **Blocked Topics:** `crime`, `politics`, `work`.

### A1-T8: 旅遊、交通與天氣 (Travel & Weather)
*   **Primary Topics:** `travel`, `natural world`.
*   **Secondary Topics:** `describing things`, `people: actions`.
*   **Blocked Topics:** `crime`, `politics`, `education`.

### A1-T9: 健康與醫療 (Health & Symptoms)
*   **Primary Topics:** `body and health`.
*   **Secondary Topics:** `people: actions`, `describing things`.
*   **Blocked Topics:** `crime`, `politics`, `shopping`.

---

## 2. Mapping Rules for A2 Themes

### A2-T1: 日常實務與當地環境 (Daily Transactions & Geography)
*   **Primary Topics:** `natural world`, `relationships`, `work`.
*   **Secondary Topics:** `homes and buildings`, `communication`.
*   **Blocked Topics:** `crime`, `politics`.

### A2-T2: 出行與消費 (Travel & Finance)
*   **Primary Topics:** `travel`, `shopping`, `money`.
*   **Secondary Topics:** `homes and buildings`, `communication`.
*   **Blocked Topics:** `crime`, `politics`, `education`.

### A2-T3: 社交與討論 (Socializing & Habits)
*   **Primary Topics:** `relationships`, `people: personality`, `communication`.
*   **Secondary Topics:** `people: actions`, `describing things`.
*   **Blocked Topics:** `crime`, `politics`, `technology`.

---

## 3. Mapping Rules for B1 Themes

### B1-T1: 旅遊與海外生活 (Travel & Living Abroad)
*   **Primary Topics:** `travel`, `money`, `shopping`.
*   **Secondary Topics:** `communication`, `relationships`.
*   **Blocked Topics:** `politics`, `education`.

### B1-T2: 職場與商業環境 (Work & Business)
*   **Primary Topics:** `work`, `money`, `technology`.
*   **Secondary Topics:** `communication`, `people: actions`.
*   **Blocked Topics:** `animals`, `clothes`.

### B1-T3: 個人表達與社交 (Personal Expression & Culture)
*   **Primary Topics:** `arts and media`, `relationships`, `people: personality`.
*   **Secondary Topics:** `communication`, `describing things`.
*   **Blocked Topics:** `crime`, `politics`.

---

## 4. Mapping Rules for B2 Themes

### B2-T1: 專業與學術情境 (Professional & Academic)
*   **Primary Topics:** `education`, `work`, `technology`.
*   **Secondary Topics:** `communication`, `describing things`.
*   **Blocked Topics:** `animals`, `clothes`.

### B2-T2: 深入辯論與會議 (Formal Debates & Meetings)
*   **Primary Topics:** `politics`, `crime`, `work`.
*   **Secondary Topics:** `communication`, `describing things`.
*   **Blocked Topics:** `food and drink`, `animals`.

### B2-T3: 母語人士交流 (Natural Speed Discourse)
*   **Primary Topics:** `communication`, `relationships`, `people: personality`.
*   **Secondary Topics:** `describing things`, `people: actions`.
*   **Blocked Topics:** *None (Advanced level permits open discussion).*

---

## 5. Mapping Rules for C1 Themes

### C1-T1: 高難度職場與社交 (Advanced Negotiation)
*   **Primary Topics:** `work`, `politics`, `money`.
*   **Secondary Topics:** `communication`, `relationships`.
*   **Blocked Topics:** `animals`.

### C1-T2: 言外之意與複雜文本 (Sarcasm & Culture)
*   **Primary Topics:** `arts and media`, `communication`, `people: personality`.
*   **Secondary Topics:** `describing things`, `relationships`.
*   **Blocked Topics:** `money`.

### C1-T3: 精準表達 (Abstract Cohesive Speech)
*   **Primary Topics:** `communication`, `describing things`, `politics`.
*   **Secondary Topics:** `people: actions`, `work`.
*   **Blocked Topics:** *None (C1 requires full structural access).*
