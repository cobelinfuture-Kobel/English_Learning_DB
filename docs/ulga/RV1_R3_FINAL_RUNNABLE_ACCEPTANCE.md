# RV1 R3 Final Runnable Acceptance

## Scope

R3 validates Reading V1 as a local runnable system.

It does not change production state, learner state, authority promotion, auto pathing, or commercial export.

## Preconditions

```text
R1 = Static worksheet web page DONE
R2 = Localhost RAZ full local mode CLOSED_LOCALHOST_RAZ_READ_ONLY
RAZ_FULL = LOCALHOST_ONLY
```

## Local run command

From repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_reading_v1.ps1
```

The script runs the R1/R2 test set, then opens:

```text
http://127.0.0.1:8765/site/rv1/index.html
```

It also starts the read-only local RAZ API:

```text
http://127.0.0.1:8781/api/status
http://127.0.0.1:8781/api/pack
http://127.0.0.1:8781/api/probe
```

## Expected readback

Tests:

```text
tests.site.test_reading_v1_static_site = OK
tests.tools.test_r2_local = OK
tests.tools.test_r2_pick = OK
```

Browser:

```text
Reading V1 Local RAZ title is visible.
Worksheet items load from /api/pack when the API is running.
Show/hide answer works.
Print dialog opens.
```

API:

```text
/api/status returns status ok and host 127.0.0.1.
/api/pack returns natural reading text in items[].q.
/api/probe returns linked_texts for bridge candidate sources.
```

## Acceptance rule

R3 can close only after operator readback confirms:

```text
R3A final local run script PASS
R3B final browser/API readback PASS
R3C final acceptance marker APPROVED
```

## Boundaries

```text
NO_PRODUCTION
NO_STATE_WRITE
NO_AUTO_PATH
NO_AUTH_PROMOTION
NO_COMMERCIAL_EXPORT
RAZ_FULL = LOCALHOST_ONLY
```
