from __future__ import annotations

from product.a1fs_v1_2_1 import (
    u01qb18h_r1b_r1_unit01_form01_actual_reading_angle_parity_fullfix as r1,
)


def _document() -> str:
    sections = "".join(
        f'<section class="scene-section"><div>Scene {index}</div></section>'
        for index in range(1, 5)
    )
    return f"<html><head><style>.scene-section{{break-inside:auto}}</style></head><body>{sections}</body></html>"


def test_final_scene_print_integrity_keeps_last_scene_as_one_pagination_unit() -> None:
    rendered = r1._preserve_final_scene_print_integrity(_document())
    assert (
        ".scene-section:last-of-type{break-inside:avoid;page-break-inside:avoid}"
        in rendered
    )
    assert rendered.count(".scene-section:last-of-type") == 1
    assert rendered.count('<section class="scene-section">') == 4


def test_final_scene_print_integrity_is_idempotent() -> None:
    once = r1._preserve_final_scene_print_integrity(_document())
    twice = r1._preserve_final_scene_print_integrity(once)
    assert twice == once


def test_final_scene_print_integrity_does_not_force_one_page_per_scene() -> None:
    rendered = r1._preserve_final_scene_print_integrity(_document())
    assert "break-before:page" not in rendered
    assert ".scene-section{break-inside:auto}" in rendered
