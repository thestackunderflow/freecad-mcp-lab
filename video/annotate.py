"""Frame 0 for the video and the Short: the clean replay's no-op cut (video/frames/sc-noop-cut-iso.png) with
red dashed circles where the holes should be (X 20/60, Z 35, D 5, on the back plate's outer face Y = 0), faint red
circles where the cut went (Z = -35, below the part: inspect_design of the replay), and the cut's logged reply
(out/runs/solidcraft-3 seq 31: ok: true, changed_bodies: []). The iso projection of the Y = 0 face is affine:
pixel = O + X*ex + Z*ez, fitted to the render's edges; check.png draws the same circles on the fixed part."""
import math, sys
from PIL import Image, ImageDraw, ImageFont

O, EX, EZ = (125.0, 677.0), (5.94, 3.41), (0.0, -6.84)     # px at X=0,Z=0; px per mm along X; px per mm along Z
RED = (220, 38, 38)
F = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

def px(x, z):
    return (O[0] + x * EX[0] + z * EZ[0], O[1] + x * EX[1] + z * EZ[1])

def ring(d, x, z, r, width, dash, color):
    pts = [px(x + r * math.cos(t), z + r * math.sin(t)) for t in [i * 2 * math.pi / 72 for i in range(73)]]
    for i in range(72):
        if not dash or (i // 4) % 2 == 0:
            d.line([pts[i], pts[i + 1]], fill=color, width=width)

def annotate(src, dst, pad=200, labels=True):
    im = Image.open(src).convert('RGB')
    w, h = im.size
    out = Image.new('RGB', (w, h + pad), im.getpixel((w // 2, h - 1)))
    out.paste(im, (0, 0))
    d = ImageDraw.Draw(out)
    for x in (20, 60):
        ring(d, x, 35, 2.5 * 1.6, 5, True, RED)                # drawn 1.6x the hole size so it reads on a phone
        ring(d, x, -35, 2.5 * 1.6, 4, True, (239, 120, 120))
    if labels:
        f = ImageFont.truetype(F, 34); fs = ImageFont.truetype(F, 30)
        a = px(60, 35); d.text((a[0] + 40, a[1] - 20), 'holes should be here', font=f, fill=RED)
        b = px(60, -35); d.text((b[0] + 40, b[1] - 20), 'the cut went here:\n35 mm below the part', font=fs, fill=(200, 60, 60))
        tag = 'cut: "ok": true   "changed_bodies": []'
        tb = d.textbbox((0, 0), tag, font=f)
        d.rounded_rectangle((30, 30, 30 + tb[2] + 36, 30 + tb[3] + 28), 14, fill=RED)
        d.text((48, 42), tag, font=f, fill='white')
    out.save(dst)

if __name__ == '__main__':
    annotate('/work/video/frames/sc-noop-cut-iso.png', '/work/video/frames/sc-noop-cut-annotated.png')
    annotate('/work/video/frames/sc-fixed-iso.png', '/work/out/annotate-check.png', labels=False)
    print('ok')
