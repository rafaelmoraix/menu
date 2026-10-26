import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC, OUT, FONT = sys.argv[1], sys.argv[2], sys.argv[3]
W, H = 2560, 1440
SAFE = (507, 508, 2053, 931)
rng = np.random.default_rng(3)

RED = np.array([189, 31, 32], dtype=np.float32)
INK = (22, 18, 20)


def blotch(scale, amp):
    small = rng.normal(0, 1, (H // scale + 2, W // scale + 2)).astype(np.float32)
    im = Image.fromarray(((small * 40) + 128).clip(0, 255).astype(np.uint8))
    im = im.resize((W + 2 * scale, H + 2 * scale), Image.BICUBIC).crop((scale, scale, W + scale, H + scale))
    return (np.asarray(im, dtype=np.float32) - 128) / 40 * amp


# red paper: soft blotches + fine grain + a gentle vignette
tex = blotch(90, 7) + blotch(22, 5) + rng.normal(0, 6, (H, W)).astype(np.float32)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
vig = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
tex -= vig * 14
paper = (RED[None, None, :] + tex[..., None] * np.array([1.0, 0.35, 0.35])).clip(0, 255)
bg = Image.fromarray(paper.astype(np.uint8))

# paper fibres
fd = ImageDraw.Draw(bg, "RGBA")
for _ in range(900):
    x, y = rng.uniform(0, W), rng.uniform(0, H)
    a = rng.uniform(0, np.pi)
    L = rng.uniform(6, 22)
    fd.line((x, y, x + np.cos(a) * L, y + np.sin(a) * L), fill=(235, 120, 110, int(rng.uniform(25, 60))), width=1)

# crow: lift it off its red background by "redness" so it sits on the new paper
crow = Image.open(SRC).convert("RGB")
# the source cuts the body off at its right edge; continue the shoulder line so the
# body runs off the banner instead of ending in a hard vertical edge
src = np.asarray(crow)
EXT = 220
ext = src[:, ::-1][:, :EXT].copy()
ys = np.arange(src.shape[0])[:, None]
ks = np.arange(EXT)[None, :]
outside = ys < 595 + 1.1 * (ks + 1)
ext[outside] = (189, 31, 32)
crow = Image.fromarray(np.concatenate([src, ext], axis=1))
SC = 1.7
crow = crow.resize((int(crow.width * SC), int(crow.height * SC)), Image.LANCZOS)
c = np.asarray(crow, dtype=np.float32)
redness = c[..., 0] - np.maximum(c[..., 1], c[..., 2])
alpha = ((130 - redness) / 70).clip(0, 1)
alpha_im = Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
crow_rgba = crow.copy()
crow_rgba.putalpha(alpha_im)

eye_src = (290, 235)
cx = 1130 - int(22 * SC)
cy = 690 - int(eye_src[1] * SC)
canvas = bg.convert("RGBA")
canvas.alpha_composite(crow_rgba, (cx, cy))

# name
name = "CROW"
font = ImageFont.truetype(FONT, int(sys.argv[4]) if len(sys.argv) > 4 else 300)
txt = Image.new("L", (W, H), 0)
td = ImageDraw.Draw(txt)
bb = td.textbbox((0, 0), name, font=font)
tw, th = bb[2] - bb[0], bb[3] - bb[1]
right_edge = 1085
tx = right_edge - tw - bb[0]
ty = (SAFE[1] + SAFE[3]) // 2 - th // 2 - bb[1] + 10
td.text((tx, ty), name, font=font, fill=255)

# printed look: speckle holes and slightly rough edges
speck = rng.random((H, W)) > 0.06
grain = Image.fromarray((speck * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
txt_a = np.asarray(txt, dtype=np.float32) * (np.asarray(grain, dtype=np.float32) / 255)
txt_a = Image.fromarray(txt_a.clip(0, 255).astype(np.uint8))
ink = Image.new("RGBA", (W, H), INK + (255,))
ink.putalpha(txt_a)
canvas.alpha_composite(ink)

# thin rule + small cream caption-like line under the name
d = ImageDraw.Draw(canvas)
line_y = ty + bb[3] + 26
d.rectangle((tx + bb[0], line_y, right_edge, line_y + 6), fill=INK)

canvas = canvas.convert("RGB")
canvas.save(OUT)
g = canvas.copy()
gd = ImageDraw.Draw(g)
gd.rectangle(SAFE, outline=(255, 255, 255), width=4)
gd.rectangle((0, SAFE[1], W - 1, SAFE[3]), outline=(255, 255, 0), width=3)
g.save(OUT.replace(".png", "_guias.png"))
