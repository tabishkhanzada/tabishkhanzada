#!/usr/bin/env python3
"""
Convert Tabish Khan's photo into an animated ASCII portrait SVG (tabish-ascii.svg)
and format it for embedding in hero.svg.
"""
import os
import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
PHOTO_PATH = r"C:\Users\WINDOWS10\.gemini\antigravity\brain\af45ab30-dd73-4951-9c65-06d2a1c2ca52\.user_uploaded\media_1795030180746_5960bfa0.jpg"
OUT_PATH = os.path.join(ROOT, "tabish-ascii.svg")

def generate():
    img = cv2.imread(PHOTO_PATH)
    if img is None:
        raise FileNotFoundError(f"Could not load image at {PHOTO_PATH}")

    # Crop tightly centered on hair, face, neck, and upper shirt
    # Original is 770 x 900. Face is around x=289, y=158
    cropped = img[40:780, 110:660]
    ch, cw = cropped.shape[:2]

    # Grabcut segmentation to cleanly isolate portrait from background
    mask = np.zeros((ch, cw), np.uint8)
    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)
    rect = (20, 10, cw - 40, ch - 20)
    cv2.grabCut(cropped, mask, rect, bgdModel, fgdModel, 4, cv2.GC_INIT_WITH_RECT)
    fg_mask = np.where((mask == 2) | (mask == 0), 0, 1).astype("uint8")

    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    target_cols = 180
    target_rows = 96

    small = cv2.resize(gray, (target_cols, target_rows), interpolation=cv2.INTER_AREA)
    fg_small = cv2.resize(fg_mask, (target_cols, target_rows), interpolation=cv2.INTER_NEAREST) == 1

    # Contrast enhancement on foreground
    fg_pixels = small[fg_small]
    p5 = np.percentile(fg_pixels, 3)
    p95 = np.percentile(fg_pixels, 97)
    norm = np.clip((small.astype(float) - p5) / (p95 - p5 + 1e-5) * 255, 0, 255).astype(np.uint8)

    # Monospace density ramp
    RAMP = "@%#*+=-:. "
    lines = []
    for r in range(target_rows):
        line = []
        for c in range(target_cols):
            if not fg_small[r, c]:
                line.append(" ")
            else:
                v = norm[r, c]
                idx = int(v / 256.0 * len(RAMP))
                idx = min(idx, len(RAMP) - 1)
                line.append(RAMP[idx])
        lines.append("".join(line))

    # Build animated terminal window tabish-ascii.svg
    svg_parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="840.0" height="880.0" viewBox="0 0 840.0 880.0" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#111722"/><stop offset="1" stop-color="#0d1117"/></linearGradient></defs>',
        '<rect width="840.0" height="880.0" rx="12" fill="url(#bg)"/>',
        '<rect x="0.5" y="0.5" width="839.0" height="879.0" rx="12" fill="none" stroke="#30363d" stroke-width="1"/>',
        '<line x1="0" y1="30" x2="840.0" y2="30" stroke="#30363d"/>',
        '<circle cx="20" cy="15.0" r="5" fill="#ff5f56"/>',
        '<circle cx="36" cy="15.0" r="5" fill="#ffbd2e"/>',
        '<circle cx="52" cy="15.0" r="5" fill="#27c93f"/>',
        '<text x="420.0" y="19.0" fill="#7d8590" font-size="12" text-anchor="middle">tabish@github: ~$ ./portrait.sh</text>'
    ]

    row_h = 8.333333333333334
    y0 = 37.0
    text_y0 = 43.2
    dur = 0.06
    for i, line_txt in enumerate(lines):
        y_clip = y0 + i * row_h
        y_text = text_y0 + i * row_h
        t_begin = i * dur
        t_end = t_begin + dur
        safe_txt = line_txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        svg_parts.append(f'<clipPath id="r{i}"><rect x="20" y="{y_clip:.1f}" height="{row_h:.1f}" width="0"><animate attributeName="width" from="0" to="800.0" begin="{t_begin:.3f}s" dur="{dur}s" fill="freeze"/></rect></clipPath>')
        svg_parts.append(f'<g clip-path="url(#r{i})"><text xml:space="preserve" x="20" y="{y_text:.1f}" fill="#c9d1d9" font-size="7.2" textLength="800.0" lengthAdjust="spacing">{safe_txt}</text></g>')
        svg_parts.append(f'<rect y="{y_clip + 1:.1f}" width="4.44" height="{row_h - 2:.1f}" fill="#c9d1d9" opacity="0"><animate attributeName="x" from="20" to="820.0" begin="{t_begin:.3f}s" dur="{dur}s" fill="freeze"/><set attributeName="opacity" to="0.85" begin="{t_begin:.3f}s"/><set attributeName="opacity" to="0" begin="{t_end:.3f}s"/></rect>')

    svg_parts.append('<line x1="0" y1="837.0" x2="840.0" y2="837.0" stroke="#30363d"/>')
    svg_parts.append('<text x="20" y="856.0" fill="#7d8590" font-size="13">tabish@github:~$ whoami <tspan fill="#c9d1d9">Muhammad Tabish Khan</tspan></text>')
    svg_parts.append('<rect x="330.0" y="844.0" width="8" height="14" fill="#c9d1d9"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" dur="1s" repeatCount="indefinite"/></rect>')
    svg_parts.append("</svg>")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("".join(svg_parts))

    print(f"Generated {OUT_PATH} successfully! ({os.path.getsize(OUT_PATH)} bytes)")

if __name__ == "__main__":
    generate()
