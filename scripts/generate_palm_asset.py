from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

WIDTH = 1600
HEIGHT = 1000
OUT = Path(__file__).resolve().parents[1] / "frontend" / "public" / "palm-lens-art.png"


def blend(base: tuple[int, int, int], top: tuple[int, int, int], alpha: float) -> tuple[int, int, int]:
    alpha = max(0.0, min(1.0, alpha))
    return tuple(int(base[i] * (1 - alpha) + top[i] * alpha) for i in range(3))


def ellipse_value(x: float, y: float, cx: float, cy: float, rx: float, ry: float, angle: float = 0.0) -> float:
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    dx = x - cx
    dy = y - cy
    xr = dx * cos_a + dy * sin_a
    yr = -dx * sin_a + dy * cos_a
    return (xr / rx) ** 2 + (yr / ry) ** 2


def inside_hand(x: int, y: int) -> float:
    shapes = [
        (880, 575, 190, 245, -0.08, 1.0),
        (720, 740, 98, 230, 0.22, 0.78),
        (660, 470, 55, 250, -0.18, 0.76),
        (780, 390, 58, 305, -0.08, 0.92),
        (905, 370, 58, 325, 0.02, 1.0),
        (1030, 400, 55, 300, 0.12, 0.88),
        (1140, 455, 52, 250, 0.22, 0.76),
        (630, 585, 82, 150, -0.55, 0.68),
    ]
    value = 0.0
    for cx, cy, rx, ry, angle, weight in shapes:
        dist = ellipse_value(x, y, cx, cy, rx, ry, angle)
        if dist < 1.0:
            value = max(value, (1.0 - dist) ** 0.55 * weight)
        elif dist < 1.12:
            value = max(value, (1.12 - dist) / 0.12 * 0.22 * weight)
    return min(1.0, value)


def line_alpha(x: int, y: int) -> float:
    nx = (x - 880) / 260
    ny = (y - 575) / 280
    palm_gate = math.exp(-(nx * nx + ny * ny) * 1.35)
    if palm_gate < 0.03:
        return 0.0

    curves = [
        y - (545 + 46 * math.sin((x - 720) / 122) + 0.10 * (x - 880)),
        y - (615 + 28 * math.sin((x - 820) / 96) - 0.16 * (x - 900)),
        y - (500 + 34 * math.sin((x - 760) / 88) - 0.24 * (x - 880)),
        x - (870 + 24 * math.sin((y - 500) / 78)),
        x - (955 + 20 * math.sin((y - 520) / 74)),
    ]
    alpha = 0.0
    for curve in curves:
        alpha = max(alpha, math.exp(-(curve * curve) / 18.0))
    return alpha * palm_gate


def topographic_alpha(x: int, y: int) -> float:
    wave = math.sin((x * 0.018) + math.sin(y * 0.012) * 2.4) + math.cos((y * 0.017) - 1.1)
    ridge = abs((wave % 0.58) - 0.29)
    return max(0.0, 1.0 - ridge * 18.0) * 0.13


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def write_png(path: Path, width: int, height: int, pixels: bytearray) -> None:
    rows = bytearray()
    stride = width * 3
    for y in range(height):
        rows.append(0)
        rows.extend(pixels[y * stride : (y + 1) * stride])

    data = b"\x89PNG\r\n\x1a\n"
    data += png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    data += png_chunk(b"IDAT", zlib.compress(bytes(rows), 9))
    data += png_chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def main() -> None:
    pixels = bytearray(WIDTH * HEIGHT * 3)
    for y in range(HEIGHT):
        v = y / (HEIGHT - 1)
        for x in range(WIDTH):
            u = x / (WIDTH - 1)
            base = (
                int(239 + 9 * (1 - v) - 18 * u),
                int(246 - 22 * v + 6 * math.sin(u * math.pi)),
                int(232 - 8 * u + 20 * v),
            )

            sweep = 0.5 + 0.5 * math.sin((u * 3.1 + v * 2.2) * math.pi)
            color = blend(base, (191, 224, 211), 0.24 * sweep)
            color = blend(color, (244, 208, 111), topographic_alpha(x, y))

            h = inside_hand(x, y)
            if h > 0:
                hand_color = blend((227, 137, 114), (142, 183, 169), 0.18 + 0.18 * math.sin((x + y) * 0.006))
                color = blend(color, hand_color, 0.18 + h * 0.52)

            la = line_alpha(x, y)
            if la > 0:
                color = blend(color, (105, 63, 70), min(0.62, la * 0.62))

            # A quiet scan band gives the image a product-lab feel without becoming a UI element.
            band = math.exp(-((y - (320 + 0.18 * x)) ** 2) / 1200)
            color = blend(color, (255, 255, 255), band * 0.12)

            idx = (y * WIDTH + x) * 3
            pixels[idx : idx + 3] = bytes(max(0, min(255, c)) for c in color)

    write_png(OUT, WIDTH, HEIGHT, pixels)
    print(OUT)


if __name__ == "__main__":
    main()

