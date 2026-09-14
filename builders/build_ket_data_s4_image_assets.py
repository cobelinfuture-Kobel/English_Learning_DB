from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from builders.ket_s4_image_codec import RENDER_DPI, RENDER_ENGINE_VERSION, canonical_rgb_png, crop_rgb, pixel_box, png_sha256
from builders.ket_s4_structural import S4Error, build_structural_inventory


def _source_pdf(folder: Path, a: dict) -> Path:
    for p in (folder / a["source_file_name"], folder / a["drive_file_id"], folder / f"{a['drive_file_id']}.pdf"):
        if p.is_file(): return p
    raise S4Error(f"PRIVATE_SOURCE_PDF_MISSING:{a['source_id']}")


def materialize_private_assets(source_dir, output_dir, root=None, write_pngs=True, structural_manifest=None) -> dict:
    try: import fitz
    except ImportError as exc: raise S4Error("PRIVATE_EXTRACTION_REQUIRES_PYMUPDF_1_26_7") from exc
    version = getattr(fitz, "VersionBind", None) or getattr(fitz, "__version__", None)
    if version != RENDER_ENGINE_VERSION: raise S4Error(f"PYMUPDF_VERSION_DRIFT:{version}")
    m = structural_manifest or build_structural_inventory(root)
    if m.get("materialization_mode") != "STRUCTURAL_INDEX": raise S4Error("STRUCTURAL_MANIFEST_MODE")
    source_dir, output_dir = Path(source_dir), Path(output_dir)
    if write_pngs: output_dir.mkdir(parents=True, exist_ok=True)
    groups = defaultdict(list)
    for a in m["assets"]: groups[a["source_id"]].append(a)
    for sid in sorted(groups):
        rows = groups[sid]
        with fitz.open(_source_pdf(source_dir, rows[0])) as doc:
            for a in rows:
                page = doc[a["source_page_number"] - 1]
                pix = page.get_pixmap(matrix=fitz.Matrix(RENDER_DPI / 72.0, RENDER_DPI / 72.0), colorspace=fitz.csRGB, alpha=False)
                if pix.n != 3: raise S4Error(f"PIXMAP_NOT_RGB:{a['image_asset_id']}")
                box = pixel_box(a["source_bbox"], a["source_page_size"], pix.width, pix.height)
                rgb, w, h = crop_rgb(pix.samples, pix.width, box)
                png = canonical_rgb_png(rgb, w, h); a["image_hash"] = png_sha256(png)
                if write_pngs: (output_dir / f"{a['image_asset_id']}.png").write_bytes(png)
    m["materialization_mode"] = "PRIVATE_FULL"
    return m


def public_projection(m: dict) -> dict:
    keys = ("image_asset_id", "source_id", "page_ref", "question_refs", "crop_index", "image_hash", "storage_role", "reuse_status", "binding_precision")
    out = {k: v for k, v in m.items() if k != "assets"}; out["assets"] = [{k: a[k] for k in keys} for a in m["assets"]]
    return out


def main() -> None:
    p = argparse.ArgumentParser(); p.add_argument("--root"); p.add_argument("--source-dir"); p.add_argument("--output-dir"); p.add_argument("--manifest-out", required=True); p.add_argument("--structural-only", action="store_true"); p.add_argument("--structural-manifest-in"); p.add_argument("--no-write-pngs", action="store_true"); a = p.parse_args()
    if a.structural_only: m = build_structural_inventory(a.root)
    else:
        if not a.source_dir or not a.output_dir: raise SystemExit("source/output dirs required")
        sm = json.loads(Path(a.structural_manifest_in).read_text(encoding="utf-8")) if a.structural_manifest_in else None
        m = materialize_private_assets(a.source_dir, a.output_dir, a.root, not a.no_write_pngs, sm)
    Path(a.manifest_out).write_text(json.dumps(public_projection(m), ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

if __name__ == "__main__": main()
