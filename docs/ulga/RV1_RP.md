# RV1 Runnable Plan

Base:

```text
P6_P10 = PASS
REAL_USER_OUTPUT = READY_STATIC_BROWSER
```

Big tasks:

```text
R1 = Static worksheet web page DONE
R2 = Localhost RAZ full local mode
R3 = Final runnable acceptance
```

R1 mid tasks:

```text
R1A = site files DONE
R1B = sample data DONE
R1C = browser print DONE
R1D = static checks PASS
R1E = user run readback PASS
```

R1 small tasks:

```text
R1A1 site/rv1/index.html DONE
R1A2 site/rv1/app.js DONE
R1A3 site/rv1/style.css DONE
R1B1 site/rv1/d.json DONE
R1C1 print button DONE
R1D1 tests/site/test_reading_v1_static_site.py PASS
R1E1 page opens PASS
R1E2 data loads PASS
R1E3 answer toggle PASS
R1E4 print dialog PASS
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
R2A1
```
