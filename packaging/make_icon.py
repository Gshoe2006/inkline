#!/usr/bin/env python3
"""Generates Inkline's app icon (inkline.svg), the PNG sizes desktops use (icons/hicolor/NxN/apps), and the icon
file managers show for a project file (icons/hicolor/scalable/mimetypes/application-x-inkline-project.svg).

Run from anywhere: python3 packaging/make_icon.py   (PNG export needs rsvg-convert, from librsvg)
"""
import math
import os
import shutil
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INK, PAPER, FOLD, CYAN = "#16181d", "#ffffff", "#cfd5dc", "#26b0dc"
CX, CY, R = 128, 126, 50          # the emblem circle on the sheet


def halftone_dots():
    """Dots on a 45°-style offset grid, growing darker toward the left edge, like a real halftone screen."""
    out, step = [], 9.0
    y, row = CY - R - step, 0
    while y < CY + R + step:
        x = CX - R - step + (step / 2 if row % 2 else 0)
        while x < CX + 2:
            dark = min(1.0, max(0.0, (CX - x) / R)) ** 0.9 * (0.8 + 0.2 * (y - (CY - R)) / (2 * R))
            r = 5.1 * math.sqrt(dark)
            if r > 0.6:
                out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}"/>')
            x += step
        y += step * 0.866
        row += 1
    return "\n      ".join(out)


def line_half():
    """Concentric arcs and petal spokes on the right half: the 'make one up' line-art side."""
    parts = []
    for r in (R - 2, 37, 24):
        parts.append(f'<path d="M{CX},{CY - r} A{r},{r} 0 0 1 {CX},{CY + r}"/>')
    for k in range(1, 6):                 # petals between the two inner rings
        a = -math.pi / 2 + k * math.pi / 6
        x1, y1 = CX + 24 * math.cos(a), CY + 24 * math.sin(a)
        x2, y2 = CX + 37 * math.cos(a), CY + 37 * math.sin(a)
        parts.append(f'<path d="M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}"/>')
    for k in range(6):                    # beads in the outer band
        a = -math.pi / 2 + (k + 0.5) * math.pi / 6
        parts.append(f'<circle cx="{CX + 42.5 * math.cos(a):.1f}" cy="{CY + 42.5 * math.sin(a):.1f}" r="2.6"/>')
    return "\n      ".join(parts)


SHEET = "M70,34 H166 L198,66 V214 a8,8 0 0 1 -8,8 H70 a8,8 0 0 1 -8,-8 V42 a8,8 0 0 1 8,-8 Z"

SVG = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <title>Inkline</title>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#2a2e36"/>
      <stop offset="1" stop-color="#121418"/>
    </linearGradient>
    <clipPath id="left"><path d="M{CX},{CY - R} A{R},{R} 0 0 0 {CX},{CY + R} Z"/></clipPath>
  </defs>
  <rect x="8" y="8" width="240" height="240" rx="56" fill="url(#bg)"/>
  <rect x="9" y="9" width="238" height="238" rx="55" fill="none" stroke="#ffffff" stroke-opacity=".14" stroke-width="2"/>
  <g transform="rotate(-5 128 128)">
    <path d="{SHEET}" fill="#000" opacity=".35" transform="translate(3 6)"/>
    <path d="{SHEET}" fill="{PAPER}"/>
    <path d="M166,34 V58 a8,8 0 0 0 8,8 H198 Z" fill="{FOLD}"/>
    <g clip-path="url(#left)" fill="{INK}">
      {halftone_dots()}
    </g>
    <g fill="none" stroke="{INK}" stroke-width="4.5" stroke-linecap="round">
      {line_half()}
    </g>
    <circle cx="{CX}" cy="{CY}" r="{R}" fill="none" stroke="{INK}" stroke-width="5"/>
    <path d="M{CX},{CY - R} V{CY + R}" stroke="{INK}" stroke-width="3"/>
    <circle cx="{CX}" cy="{CY}" r="8" fill="{INK}"/>
    <g fill="{INK}">
      <circle cx="86" cy="200" r="7"/><circle cx="104" cy="200" r="5.6"/><circle cx="120" cy="200" r="4.3"/>
      <circle cx="134" cy="200" r="3.1"/><circle cx="146" cy="200" r="2"/><circle cx="156" cy="200" r="1.1"/>
    </g>
    <g stroke="{CYAN}" stroke-width="3" fill="none">
      <circle cx="84" cy="56" r="7"/><path d="M84,44 V68 M72,56 H96"/>
    </g>
  </g>
</svg>
'''


SMALL = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a2e36"/><stop offset="1" stop-color="#121418"/></linearGradient></defs>
  <rect x="8" y="8" width="240" height="240" rx="56" fill="url(#bg)"/>
  <rect x="9" y="9" width="238" height="238" rx="55" fill="none" stroke="#ffffff" stroke-opacity=".18" stroke-width="4"/>
  <path d="M60,28 H170 L206,64 V220 a10,10 0 0 1 -10,10 H60 a10,10 0 0 1 -10,-10 V38 a10,10 0 0 1 10,-10 Z" fill="{PAPER}"/>
  <path d="M170,28 V56 a8,8 0 0 0 8,8 H206 Z" fill="{FOLD}"/>
  <path d="M128,64 A64,64 0 0 0 128,192 Z" fill="{INK}"/>
  <circle cx="128" cy="128" r="64" fill="none" stroke="{INK}" stroke-width="14"/>
  <path d="M128,94 A34,34 0 0 1 128,162" fill="none" stroke="{INK}" stroke-width="14"/>
</svg>
'''


# A project file: a sheet of paper with the emblem on it (no app tile: file managers show documents as pages).
PROJECT = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <title>Inkline project</title>
  <path d="M60,20 H170 L210,60 V226 a10,10 0 0 1 -10,10 H60 a10,10 0 0 1 -10,-10 V30 a10,10 0 0 1 10,-10 Z" fill="#000" opacity=".18" transform="translate(2 4)"/>
  <path d="M60,20 H170 L210,60 V226 a10,10 0 0 1 -10,10 H60 a10,10 0 0 1 -10,-10 V30 a10,10 0 0 1 10,-10 Z" fill="{PAPER}" stroke="#9aa3ad" stroke-width="4"/>
  <path d="M170,20 V50 a10,10 0 0 0 10,10 H210 Z" fill="{FOLD}" stroke="#9aa3ad" stroke-width="4" stroke-linejoin="round"/>
  <path d="M130,78 A52,52 0 0 0 130,182 Z" fill="{INK}"/>
  <circle cx="130" cy="130" r="52" fill="none" stroke="{INK}" stroke-width="12"/>
  <path d="M130,102 A28,28 0 0 1 130,158" fill="none" stroke="{INK}" stroke-width="12"/>
  <path d="M84,206 H176" stroke="{CYAN}" stroke-width="10" stroke-linecap="round"/>
</svg>
'''


def main():
    svg_path = os.path.join(ROOT, "inkline.svg")
    with open(svg_path, "w") as f:
        f.write(SVG)
    print("wrote", svg_path)
    project_path = os.path.join(ROOT, "icons", "hicolor", "scalable", "mimetypes", "application-x-inkline-project.svg")
    os.makedirs(os.path.dirname(project_path), exist_ok=True)
    with open(project_path, "w") as f:
        f.write(PROJECT)
    print("wrote", project_path)
    if not shutil.which("rsvg-convert"):
        print("rsvg-convert not found, skipped PNG sizes")
        return
    small_path = os.path.join(ROOT, "icons", "inkline-small.svg")   # simplified drawing, legible at 16-32 px
    os.makedirs(os.path.dirname(small_path), exist_ok=True)
    with open(small_path, "w") as f:
        f.write(SMALL)
    for n in (16, 22, 24, 32, 48, 64, 128, 256, 512):
        d = os.path.join(ROOT, "icons", "hicolor", f"{n}x{n}", "apps")
        os.makedirs(d, exist_ok=True)
        src = small_path if n <= 32 else svg_path
        subprocess.run(["rsvg-convert", "-w", str(n), "-h", str(n), "-o", os.path.join(d, "inkline.png"), src], check=True)
    print("wrote PNG sizes to icons/hicolor")


if __name__ == "__main__":
    main()
