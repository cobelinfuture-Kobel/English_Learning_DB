from __future__ import annotations

import subprocess
import sys
from textwrap import dedent


def test_operator_optimizer_does_not_create_reentrant_canonical_instance() -> None:
    script = dedent(
        r'''
        import importlib
        import importlib.util
        import sys
        from pathlib import Path

        target_name = (
            "ulga.builders."
            "build_a1fs_v1_u01qb15_unit01_context_stratified_question_bank_"
            "replacement_and_per_scene_runtime_capacity_fullfix"
        )
        optimizer_name = "ulga.builders._u01qb15_fast_context_assignment_optimizer"
        validator_name = (
            "ulga.validators."
            "validate_a1fs_v1_u01qb15_unit01_context_stratified_question_bank_"
            "replacement_and_per_scene_runtime_capacity_fullfix"
        )

        target = importlib.import_module(target_name)
        optimizer_path = Path(
            "ulga/builders/_u01qb15_fast_context_assignment_optimizer.py"
        ).resolve()
        spec = importlib.util.spec_from_file_location(
            "u01qb15_operator_main_instance", optimizer_path
        )
        assert spec is not None and spec.loader is not None
        operator_optimizer = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = operator_optimizer
        spec.loader.exec_module(operator_optimizer)
        operator_optimizer.install()

        assert target.build_payload.__name__ == "build_payload_fast"
        assert optimizer_name not in sys.modules

        # Admission imports the validator after the operator instance has already
        # installed the optimized builder. The validator must reuse that state
        # rather than importing a second canonical optimizer instance.
        importlib.import_module(validator_name)
        assert optimizer_name not in sys.modules

        final_items = target.build_context_stratified_u01qb12_items()[0]
        first = operator_optimizer.adaptive_base_only_scene_runtime_capacity_proof(
            final_items
        )
        second = operator_optimizer.adaptive_base_only_scene_runtime_capacity_proof(
            final_items
        )
        for proof in (first, second):
            assert proof["runtime_capacity_aware_spiral_reuse_selection"] is True
            assert "U01-C3-PICNIC-FOOD" in proof[
                "runtime_capacity_reuse_excluded_scene_refs"
            ]
            assert "U01-C3-PICNIC-FOOD" not in proof[
                "runtime_capacity_reuse_selected_scene_refs"
            ]
            assert proof["runtime_capacity_reuse_selected_scene_count"] == 17
        '''
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
