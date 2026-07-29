# English Learning DB

Private authority database for English learning materials, ULGA graph, RAZ corpus processing, tag registry, validators, and content authority reports.

## A1FS V1.2.1 Pull-To-Run

Start the packaged local learning system from the repository root:

```powershell
python -m product.a1fs_v1_2_1.runtime_server start
```

This starts A1FS V1.2.1 directly from `product/a1fs_v1_2_1/`. It does not require `REBUILD_A1FS.py`, `UPGRADE_A1FS.py`, an installer, a root rename, or a pending-root activation step. First start creates local state from clean seeds under `product/a1fs_v1_2_1/local_state/`, which is ignored by Git.

## Governance

- [Project Task Expansion Control Policy](docs/governance/PROJECT_TASK_EXPANSION_CONTROL_POLICY.md)
- [English Grammar Project Governance](docs/governance/ENGLISH_GRAMMAR_PROJECT_GOVERNANCE.md)
