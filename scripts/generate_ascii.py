#!/usr/bin/env python3
"""
Convert Tabish Khan's photo into a fine, high-fidelity animated ASCII portrait.
- Cleans background and removes the chair artifact.
- Uses CLAHE, unsharp masking, and edge-blending for crisp eyes, lips, jawline, and hair.
- Employs a calibrated 32-character monospace density ramp for photographic halftone rendering.
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

    # Crop tightly centered on head, face, neck, and upper chest
    # Face center is around x=386, y=255.
    cropped = img[35:675, 125:645]
    ch, cw = cropped.shape[:2]

    # Grabcut segmentation to cleanly isolate portrait from background and chair
    mask = np.zeros((ch, cw), np.uint8)
    mask[:, :] = cv2.GC_PR_BGD

    # Explicit Background Seeds
    mask[:45, :] = cv2.GC_BGD               # Top background
    mask[:, :40] = cv2.GC_BGD               # Left border
    mask[:, cw-40:] = cv2.GC_BGD            # Right border
    mask[40:340, :135] = cv2.GC_BGD         # Left restaurant background fixtures
    mask[40:340, cw-135:] = cv2.GC_BGD      # Right background
    mask[140:390, cw-115:] = cv2.GC_BGD     # Chair back behind right shoulder!

    # Explicit Foreground Seeds
    mask[120:300, 185:335] = cv2.GC_FGD     # Face
    mask[45:120, 200:320] = cv2.GC_FGD      # Hair
    mask[380:580, 180:340] = cv2.GC_FGD     # Chest / white shirt

    # Probable Foreground
    mask[45:ch-10, 45:cw-45] = np.where(
        mask[45:ch-10, 45:cw-45] == cv2.GC_PR_BGD,
        cv2.GC_PR_FGD,
        mask[45:ch-10, 45:cw-45]
    )

    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)
    cv2.grabCut(cropped, mask, None, bgdModel, fgdModel, 6, cv2.GC_INIT_WITH_MASK)

    fg_mask = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype("uint8")

    # Isolate single largest connected contour (removes any stray chair/background specs)
    contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        clean_mask = np.zeros_like(fg_mask)
        cv2.drawContours(clean_mask, [largest], -1, 1, thickness=cv2.FILLED)
        # Morphological smoothing on mask boundary
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        clean_mask = cv2.morphologyEx(clean_mask, cv2.MORPH_CLOSE, kernel)
    else:
        clean_mask = fg_mask

    # Image enhancement for fine facial and hair details
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)

    # CLAHE to balance face highlights, shadows, and hair texture
    clahe = cv2.createCLAHE(clipLimit=2.6, tileGridSize=(8, 8))
    cl = clahe.apply(gray)

    # Unsharp mask for crisp facial micro-contrast
    gaussian = cv2.GaussianBlur(cl, (0, 0), 1.5)
    unsharp = cv2.addWeighted(cl, 1.6, gaussian, -0.6, 0)

    # Edge detection for crisp eyes, eyelids, nose contours, lips, smile, and collar
    edges = cv2.Canny(gray, 35, 105)
    edges_fg = cv2.bitwise_and(edges, edges, mask=clean_mask)
    edges_fg = cv2.dilate(edges_fg, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2)))

    # Blend edge intensity into image (darkens key facial lines)
    blended = unsharp.astype(np.float32)
    blended[edges_fg > 0] = np.clip(blended[edges_fg > 0] * 0.42, 0, 255)
    blended = np.clip(blended, 0, 255).astype(np.uint8)

    # Target grid resolution: 110 rows x 176 cols for ultra-fine fidelity
    target_rows = 110
    target_cols = 176

    small_gray = cv2.resize(blended, (target_cols, target_rows), interpolation=cv2.INTER_AREA)
    small_mask = cv2.resize(clean_mask, (target_cols, target_rows), interpolation=cv2.INTER_NEAREST) == 1

    # Calibrated 32-character density ramp (from darkest ink @ to lightest paper ' ')
    # Ordered by optical pixel fill in monospace fonts
    RAMP = "@$#%&8BWMZO0QLCJUXzcvunxrjft/|()1{}[]?-_+~=i!lI;:,^'. "
    ramp_len = len(RAMP)

    # Contrast adjustment across foreground
    fg_vals = small_gray[small_mask]
    p_low = np.percentile(fg_vals, 2)
    p_high = np.percentile(fg_vals, 98)
    norm = np.clip((small_gray.astype(float) - p_low) / (p_high - p_low + 1e-5) * 255, 0, 255).astype(np.uint8)

    lines = []
    for r in range(target_rows):
        line = []
        for c in range(target_cols):
            if not small_mask[r, c]:
                line.append(" ")
            else:
                v = norm[r, c]
                idx = int(v / 256.0 * ramp_len)
                idx = min(idx, ramp_len - 1)
                line.append(RAMP[idx])
        lines.append("".join(line))

    # Build animated SVG tabish-ascii.svg
    total_w = 840.0
    total_h = 880.0
    header_h = 30.0
    footer_h = 35.0
    content_h = total_h - header_h - footer_h - 10
    row_h = content_h / target_rows
    y0 = header_h + 8.0
    text_y0 = y0 + row_h * 0.75
    font_size = row_h * 0.92

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{total_h}" viewBox="0 0 {total_w} {total_h}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#111722"/><stop offset="1" stop-color="#0d1117"/></linearGradient></defs>',
        f'<rect width="{total_w}" height="{total_h}" rx="12" fill="url(#bg)"/>',
        f'<rect x="0.5" y="0.5" width="{total_w - 1}" height="{total_h - 1}" rx="12" fill="none" stroke="#30363d" stroke-width="1"/>',
        f'<line x1="0" y1="{header_h}" x2="{total_w}" y2="{header_h}" stroke="#30363d"/>',
        '<circle cx="20" cy="15.0" r="5" fill="#ff5f56"/>',
        '<circle cx="36" cy="15.0" r="5" fill="#ffbd2e"/>',
        '<circle cx="52" cy="15.0" r="5" fill="#27c93f"/>',
        f'<text x="{total_w / 2}" y="19.0" fill="#7d8590" font-size="12" text-anchor="middle">tabish@github: ~$ ./portrait.sh</text>'
    ]

    dur = 0.04
    for i, line_txt in enumerate(lines):
        y_clip = y0 + i * row_h
        y_text = text_y0 + i * row_h
        t_begin = i * dur
        t_end = t_begin + dur
        safe_txt = line_txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        svg_parts.append(
            f'<clipPath id="r{i}"><rect x="20" y="{y_clip:.2f}" height="{row_h:.2f}" width="0">'
            f'<animate attributeName="width" from="0" to="800.0" begin="{t_begin:.3f}s" dur="{dur}s" fill="freeze"/></rect></clipPath>'
        )
        svg_parts.append(
            f'<g clip-path="url(#r{i})"><text xml:space="preserve" x="20" y="{y_text:.2f}" fill="#c9d1d9" font-size="{font_size:.2f}" textLength="800.0" lengthAdjust="spacing">{safe_txt}</text></g>'
        )
        svg_parts.append(
            f'<rect y="{y_clip + 0.5:.2f}" width="4.55" height="{row_h - 1:.2f}" fill="#c9d1d9" opacity="0">'
            f'<animate attributeName="x" from="20" to="820.0" begin="{t_begin:.3f}s" dur="{dur}s" fill="freeze"/>'
            f'<set attributeName="opacity" to="0.85" begin="{t_begin:.3f}s"/><set attributeName="opacity" to="0" begin="{t_end:.3f}s"/></rect>'
        )

    footer_y = total_h - footer_h
    svg_parts.append(f'<line x1="0" y1="{footer_y}" x2="{total_w}" y2="{footer_y}" stroke="#30363d"/>')
    svg_parts.append(f'<text x="20" y="{footer_y + 20}" fill="#7d8590" font-size="13">tabish@github:~$ whoami <tspan fill="#c9d1d9">Muhammad Tabish Khan</tspan></text>')
    svg_parts.append(f'<rect x="330.0" y="{footer_y + 8}" width="8" height="14" fill="#c9d1d9"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" dur="1s" repeatCount="indefinite"/></rect>')
    svg_parts.append("</svg>")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("".join(svg_parts))

    print(f"Generated refined {OUT_PATH} successfully! ({len(lines)} rows, {len(lines[0])} cols)")

if __name__ == "__main__":
    generate()
