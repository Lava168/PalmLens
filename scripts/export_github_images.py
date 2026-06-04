"""Export images under docs/images/ for GitHub README and repo gallery."""

from __future__ import annotations

import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import cv2
import numpy as np

from app.analyzer import analyze_palm_image  # noqa: E402

SAMPLE = ROOT / "frontend" / "public" / "palm-lens-art.png"
OUT_DIR = ROOT / "docs" / "images"
HERO_WIDTH = 1200
GALLERY_HEIGHT = 420


def save_data_url(path: Path, data_url: str) -> None:
    prefix = "base64,"
    if prefix not in data_url:
        raise ValueError(f"Unexpected data URL in {path.name}")
    raw = base64.b64decode(data_url.split(prefix, 1)[1])
    path.write_bytes(raw)


def read_png(path: Path) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(path.read_bytes(), np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not decode {path}")
    return image


def resize_width(image: np.ndarray, width: int) -> np.ndarray:
    height = max(1, int(image.shape[0] * width / image.shape[1]))
    return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)


def resize_height(image: np.ndarray, height: int) -> np.ndarray:
    width = max(1, int(image.shape[1] * height / image.shape[0]))
    return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)


def write_png(path: Path, image: np.ndarray) -> None:
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise ValueError(f"Could not encode {path}")
    path.write_bytes(encoded.tobytes())


def labeled_tile(image: np.ndarray, label: str, height: int) -> np.ndarray:
    tile = resize_height(image, height)
    bar = np.full((44, tile.shape[1], 3), (238, 244, 238), dtype=np.uint8)
    cv2.putText(
        bar,
        label,
        (14, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.72,
        (23, 34, 31),
        2,
        cv2.LINE_AA,
    )
    return np.vstack([bar, tile])


def build_gallery(paths: list[tuple[str, Path]]) -> np.ndarray:
    tiles = [labeled_tile(read_png(path), label, GALLERY_HEIGHT) for label, path in paths]
    max_h = max(tile.shape[0] for tile in tiles)
    padded = []
    for tile in tiles:
        if tile.shape[0] < max_h:
            pad = np.full((max_h - tile.shape[0], tile.shape[1], 3), 245, dtype=np.uint8)
            tile = np.vstack([tile, pad])
        padded.append(tile)
    gap = np.full((max_h, 12, 3), 245, dtype=np.uint8)
    row = padded[0]
    for tile in padded[1:]:
        row = np.hstack([row, gap, tile])
    return row


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    hero_src = SAMPLE.read_bytes()
    report = analyze_palm_image(hero_src)
    image = report["image"]
    save_data_url(OUT_DIR / "overlay.png", image["overlay_image"])
    save_data_url(OUT_DIR / "line-enhanced.png", image["line_enhanced_image"])
    save_data_url(OUT_DIR / "red-heatmap.png", image["red_heatmap_image"])

    write_png(OUT_DIR / "hero-banner.png", resize_width(read_png(SAMPLE), HERO_WIDTH))

    gallery = build_gallery(
        [
            ("Sample palm", SAMPLE),
            ("Overlay", OUT_DIR / "overlay.png"),
            ("Palm lines", OUT_DIR / "line-enhanced.png"),
            ("Red heatmap", OUT_DIR / "red-heatmap.png"),
        ]
    )
    write_png(OUT_DIR / "analysis-gallery.png", gallery)

    print(f"Wrote images to {OUT_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
