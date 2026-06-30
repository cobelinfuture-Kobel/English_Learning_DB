# Vocabulary Topic Recovery Audit (VOCAB_DB_S1)

This document contains a quality-assurance sample audit of the vocabulary topic recovery pipeline. For each of the five recovery methods, 20 sampled records are audited, classified, and analyzed.

---

## 1. topic_sheet_reconciliation Sample Audit

| Word | Guideword | Level | Raw Topic | Recovered Topic | Confidence | Verdict | Notes |
| :--- | :--- | :---: | :---: | :--- | :---: | :---: | :--- |
| cattle | | B1 | *empty* | animals | High | **PASS** | Match from topic sheet `animal`. |
| clothes | | A1 | *empty* | clothes | High | **PASS** | Match from topic sheet `clothes`. |
| although | BUT | B1 | *empty* | communication | High | **PASS** | Match from topic sheet `communication`. |
| although | DESPITE | B1 | *empty* | communication | High | **PASS** | Match from topic sheet `communication`. |
| and | ALSO | A1 | *empty* | communication | High | **PASS** | Match from topic sheet `communication`. |
| and | AFTER | A1 | *empty* | communication | High | **PASS** | Match from topic sheet `communication`. |
| and | AFTER VERB | A2 | *empty* | communication | High | **PASS** | Match from topic sheet `communication`. |
| and | EMPHASIZE | B1 | *empty* | communication | High | **PASS** | Match from topic sheet `communication`. |
| as | BECAUSE | A2 | *empty* | communication | High | **PASS** | Match from topic sheet `communication`. |
| because | | A1 | *empty* | communication | High | **PASS** | Match from topic sheet `communication`. |
| but | DIFFERENT STATEMENT | A1 | *empty* | communication | High | **PASS** | Match from topic sheet `communication`. |
| close | | B1 | *empty* | describing things | High | **PASS** | Match from topic sheet `describing things`. |
| as | JOB | A1 | *empty* | work | High | **PASS** | Match from topic sheet `work`. |
| drink | ALCOHOL | A2 | *empty* | food and drink | High | **PASS** | Match from topic sheet `food and drink`. |
| crash | VEHICLE | B1 | *empty* | travel | High | **PASS** | Match from topic sheet `travel`. |
| drink | LIQUID | A1 | *empty* | food and drink | High | **PASS** | Match from topic sheet `food and drink`. |
| export | | B2 | *empty* | shopping | High | **PASS** | Match from topic sheet `shopping`. |
| enough | NECESSARY AMOUNT | A2 | *empty* | describing things | High | **PASS** | Match from topic sheet `describing things`. |
| highlight | | B2 | *empty* | communication | High | **PASS** | Match from topic sheet `communication`. |
| fluid | | C2 | *empty* | describing things | High | **PASS** | Match from topic sheet `describing things`. |

---

## 2. same_word_guideword_exact Sample Audit

| Word | Guideword | Level | Raw Topic | Recovered Topic | Confidence | Verdict | Notes |
| :--- | :--- | :---: | :---: | :--- | :---: | :---: | :--- |
| that | | A2 | *empty* | describing things | High | **PASS** | Same-word matching has a single topic in sheet. |
| care | WORRY | C2 | *empty* | people: personality | High | **PASS** | Semantic sense matches correctly. |
| brake | | B2 | *empty* | travel | High | **PASS** | "Brake" naturally refers to transport/travel. |
| address | BUILDING DETAILS | C2 | *empty* | homes and buildings | High | **PASS** | Address details align with housing topic. |
| alert | | C2 | *empty* | people: personality | High | **PASS** | Personality/mental state mapping is correct. |
| characteristic | | C2 | *empty* | describing things | High | **PASS** | Structural description match is valid. |
| between | SPACE | C1 | *empty* | describing things | High | **PASS** | Spatial prepositions map here. |
| cheer | | C2 | *empty* | communication | High | **PASS** | Expressive speech maps to communication. |
| desire | | C1 | *empty* | people: personality | High | **PASS** | Internal feelings map to personality. |
| designer | | B1 | *empty* | clothes | High | **PASS** | Clothing designers align with clothes. |
| expert | | B1 | *empty* | people: personality | High | **PASS** | Person description maps correctly. |
| comb | | B1 | *empty* | people: appearance | High | **PASS** | Grooming aligns with appearance. |
| concern | WORRY | C1 | *empty* | people: personality | High | **PASS** | Mental worries align with personality. |
| draft | | C1 | *empty* | communication | High | **PASS** | Written drafts align with communication. |
| cool | | B2 | *empty* | communication | High | **PASS** | Speech exclamation maps to communication. |
| double | | B2 | *empty* | describing things | High | **PASS** | Multipliers map to describing things. |
| download | | A2 | *empty* | technology | High | **PASS** | Data download maps to technology. |
| coin | | C2 | *empty* | money | High | **PASS** | Coins map to financial transactions. |
| inferior | | C2 | *empty* | describing things | High | **PASS** | Evaluative adjectives map to describing things. |
| fine | | B1 | *empty* | describing things | High | **PASS** | Evaluative adjectives map to describing things. |

---

## 3. unanimous_word_majority Sample Audit

| Word | Guideword | Level | Raw Topic | Recovered Topic | Confidence | Verdict | Notes |
| :--- | :--- | :---: | :---: | :--- | :---: | :---: | :--- |
| after | | B1 | *empty* | describing things | High | **PASS** | Extrapolated from other "after" entries. |
| and | NUMBERS | A1 | *empty* | communication | High | **PASS** | Extrapolated from other "and" entries. |
| before | EARLIER | A2 | *empty* | describing things | High | **PASS** | Prepositions describing sequence. |
| before | TO AVOID SOMETHING | B1 | *empty* | describing things | High | **PASS** | Prepositions describing sequence. |
| before | UNTIL | B1 | *empty* | describing things | High | **PASS** | Prepositions describing sequence. |
| but | EXPLAINING WHY | B1 | *empty* | communication | High | **PASS** | Contrastive conjunctions map here. |
| like | | B1 | *empty* | people: personality | High | **PASS** | "Like" as verb maps to personality/affection. |
| or | REASON | C1 | *empty* | communication | High | **PASS** | Logical connectors map to communication. |
| so | REASON | A2 | *empty* | communication | High | **PASS** | Logical connectors map to communication. |
| zero | NUMBER | A2 | *empty* | natural world | High | **PASS** | Zero in temperature/weather contexts. |
| while | DURING | A2 | *empty* | communication | High | **PASS** | Temporal connectors. |
| carrot | REWARD | C2 | *empty* | food and drink | High | **PASS** | Food word matches base topic. |
| bunch | PEOPLE | B1 | *empty* | describing things | High | **PASS** | Quantifier word maps to describing things. |
| click | IDEA | C2 | *empty* | relationships | High | **PASS** | Metaphorical "click" maps to social relations. |
| birth | BEGINNING | C1 | *empty* | body and health | High | **PASS** | Birth/medical events align here. |
| approval | GOOD OPINION | B2 | *empty* | communication | High | **PASS** | Expressing opinions maps to communication. |
| addition | NEW THING | B2 | *empty* | describing things | High | **PASS** | Accumulative descriptors. |
| ambition | HOPE | B1 | *empty* | people: personality | High | **PASS** | Internal personality traits. |
| application | REQUEST | B1 | *empty* | technology | High | **PASS** | Tech/mobile apps dominate this term. |
| attraction | THING TO SEE OR DO | B1 | *empty* | relationships | High | **PASS** | Tourist attractions map to travel/relationships. |

---

## 4. guideword_heuristics Sample Audit (Regex Substring Matching)

This section demonstrates the high false-positive risk of regex keyword search on generic guidewords.

| Word | Guideword | Level | Raw Topic | Recovered Topic | Confidence | Verdict | Notes |
| :--- | :--- | :---: | :---: | :--- | :---: | :---: | :--- |
| amateur | **NO SKILL** | C1 | *empty* | body and health | High | **REVIEW_REQUIRED** | False positive: guideword contains `skill` which has substring `ill` -> mapped to body and health. |
| battle | **PROBLEMS/ILLNESS** | B2 | *empty* | body and health | High | **PASS** | Correct: maps to health due to `illness`. |
| bonus | **EXTRA MONEY** | B2 | *empty* | money | High | **PASS** | Correct: maps to money. |
| branch | **BUSINESS** | B1 | *empty* | travel | High | **REVIEW_REQUIRED** | False positive: guideword contains `business` which has substring `bus` -> mapped to travel. |
| charge | **CRIME** | C1 | *empty* | crime | High | **PASS** | Correct: maps to crime. |
| charge | **MONEY** | B1 | *empty* | money | High | **PASS** | Correct: maps to money. |
| allow | **TIME/MONEY** | C1 | *empty* | money | High | **PASS** | Correct: maps to money. |
| chew | **EAT** | B2 | *empty* | food and drink | High | **PASS** | Correct: maps to food and drink. |
| all right | **WITHOUT PROBLEMS** | A1 | *empty* | crime | High | **REVIEW_REQUIRED** | False positive: guideword contains `problems` which has substring `rob` -> mapped to crime. |
| alright | **WITHOUT PROBLEMS** | A2 | *empty* | crime | High | **REVIEW_REQUIRED** | False positive: guideword contains `problems` which has substring `rob` -> mapped to crime. |
| clean | **NO CRIME** | C2 | *empty* | crime | High | **PASS** | Correct: maps to crime. |
| discriminate | **TREAT UNFAIRLY** | C1 | *empty* | food and drink | High | **REVIEW_REQUIRED** | False positive: guideword contains `treat` which has substring `eat` -> mapped to food and drink. |
| construction | **BUILDING WORK** | B2 | *empty* | work | High | **PASS** | Correct: maps to work. |
| difficulty | **PROBLEM** | B2 | *empty* | crime | High | **REVIEW_REQUIRED** | False positive: guideword contains `problem` which has substring `rob` -> mapped to crime. |
| component | **FEATURE** | C1 | *empty* | food and drink | High | **REVIEW_REQUIRED** | False positive: guideword contains `feature` which has substring `eat` -> mapped to food and drink. |
| control | **LAW** | B2 | *empty* | crime | High | **PASS** | Correct: maps to crime. |
| danger | **THREAT** | B1 | *empty* | food and drink | High | **REVIEW_REQUIRED** | False positive: guideword contains `threat` which has substring `eat` -> mapped to food and drink. |
| empire | **BUSINESSES** | C1 | *empty* | travel | High | **REVIEW_REQUIRED** | False positive: guideword contains `businesses` which has substring `bus` -> mapped to travel. |
| credit | **PAYMENT** | B1 | *empty* | money | High | **PASS** | Correct: maps to money. |

---

## 5. closed_class_mapping Sample Audit

| Word | Guideword | Level | Raw Topic | Recovered Topic | Confidence | Verdict | Notes |
| :--- | :--- | :---: | :---: | :--- | :---: | :---: | :--- |
| albeit | | C2 | *empty* | describing things | Medium | **WARNING** | Function word mapped to describing things (acceptable syntax mapping). |
| as | USE | A2 | *empty* | describing things | Medium | **PASS** | Comparison function word. |
| as | BEING OR APPEARING | B1 | *empty* | describing things | Medium | **PASS** | Comparison function word. |
| as | WHILE | B1 | *empty* | describing things | Medium | **PASS** | Contrastive function word. |
| as | LIKE | B1 | *empty* | describing things | Medium | **PASS** | Conjunction. |
| eight | | A1 | *empty* | describing things | Medium | **PASS** | Numbers map to describing things (quantifiers). |
| eighteen | | A1 | *empty* | describing things | Medium | **PASS** | Numbers map to describing things (quantifiers). |
| eighth | | A2 | *empty* | describing things | Medium | **PASS** | Numbers map to describing things (quantifiers). |
| eighty | | A2 | *empty* | describing things | Medium | **PASS** | Numbers map to describing things (quantifiers). |
| eleven | | A1 | *empty* | describing things | Medium | **PASS** | Numbers map to describing things (quantifiers). |
| fifteen | | A1 | *empty* | describing things | Medium | **PASS** | Numbers map to describing things (quantifiers). |
| fifty | | A2 | *empty* | describing things | Medium | **PASS** | Numbers map to describing things (quantifiers). |
| five | | A1 | *empty* | describing things | Medium | **PASS** | Numbers map to describing things (quantifiers). |
| forty | NUMBER | A2 | *empty* | describing things | Medium | **PASS** | Numbers map to describing things (quantifiers). |
| four | | A1 | *empty* | describing things | Medium | **PASS** | Numbers map to describing things (quantifiers). |
| fourteen | | A1 | *empty* | describing things | Medium | **PASS** | Numbers map to describing things (quantifiers). |
| fourth | | A2 | *empty* | describing things | Medium | **PASS** | Numbers map to describing things (quantifiers). |
| however | | C2 | *empty* | describing things | Medium | **WARNING** | Adversative connector mapped to describing things. |
| hundred | NUMBER | A2 | *empty* | describing things | Medium | **PASS** | Quantifier maps to describing things. |
| if | DEPENDING | A2 | *empty* | describing things | Medium | **PASS** | Conditional conjunction. |
