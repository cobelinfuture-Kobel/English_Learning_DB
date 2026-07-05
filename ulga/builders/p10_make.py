from __future__ import annotations


def make_release(release_id, guide, sample):
    return {
        "schema_version": "p10_ok.v1",
        "release_id": release_id,
        "guide": guide,
        "sample": sample,
        "local_user": True,
        "public_ready": False,
    }


def make_synthetic_release():
    return make_release(
        "p10_release_001",
        "Run tests, open the local page card, and print for private local use.",
        "p8_page_001",
    )
