#!/usr/bin/env python3
"""Materialize the exact Unit01 Writing production slots from the admitted 3805 pool.

R2R2 reads the installed U01QB13 240-row blueprint and replaces exactly the 48
PF13/PF14/PF15 base items with sentence-backed, exact-scene items.  The source
SQLite database is never mutated; a disposable backup is reconciled instead.

Vocabulary lineage is deliberately two-tiered.  A target keeps a canonical A1
vocabulary authority only when S01 exposes a unique authority id (selected or
OBSERVED_IN_MATERIAL_ONLY).  Every target also keeps the admitted sentence-pool
entity id.  A sentence-pool entity therefore never masquerades as an EVP/A1
vocabulary authority when none is uniquely available.
"""
# blob-backed replacement staged in commit 7ca15b227b3d58a35140165cecb9288f68a6a25e
