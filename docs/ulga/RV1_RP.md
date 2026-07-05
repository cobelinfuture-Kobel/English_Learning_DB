# RV1 Runnable Plan

Base:

```text
P6_P10 = PASS
REAL_USER_OUTPUT = NOT_READY
```

Big tasks:

```text
R1 = Static worksheet web page
R2 = Localhost RAZ full local mode
R3 = Final runnable acceptance
```

R1 mid tasks:

```text
R1A = site files
R1B = sample data
R1C = browser print
R1D = static checks
R1E = user run readback
```

R1 small tasks:

```text
R1A1 site/reading-v1/index.html
R1A2 site/reading-v1/app.js
R1A3 site/reading-v1/style.css
R1B1 site/reading-v1/data/sample_pack.json
R1C1 print button
R1D1 tests/site/test_reading_v1_static_site.py
R1E1 operator opens page and prints
```

R2 mid tasks:

```text
R2A localhost server
R2B local RAZ read only data access
R2C level/book selector
R2D local worksheet generation
R2E local acceptance
```

R2 small tasks:

```text
R2A1 localhost app entry
R2B1 path config
R2B2 read only scan
R2C1 level list
R2D1 generate local pack
R2E1 operator local run
```

Rules:

```text
NO_PRODUCTION
NO_STATE_WRITE
NO_AUTO_PATH
NO_AUTH_PROMOTION
NO_COMMERCIAL_EXPORT
RAZ_FULL = LOCALHOST_ONLY
```

Next:

```text
R1A1
```
