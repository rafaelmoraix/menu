"""Thumbnail C (no mascot): a giant match igniting in the dark, procedural flame, red classic-serif headline."""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = sys.argv[1]
TEXT = sys.argv[2] if len(sys.argv) > 2 else "NÃO ERA PRA|EXISTIR"
FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
W, H = 1280, 720
rng = np.random.default_rng(12)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)


def noise(scale, seed):
    r = np.random.default_rng(seed)
    small = r.normal(0, 1, (H // scale + 3, W // scale + 3)).astype(np.float32)
    im = Image.fromarray(((small * 40) + 128).clip(0, 255).astype(np.uint8)).resize((W + 2 * scale, H + 2 * scale), Image.BICUBIC)
    return (np.asarray(im.crop((scale, scale, W + scale, H + scale)), np.float32) - 128) / 40


HEAD = (1010, 430)         # match head position
FB = (HEAD[0] + 2, HEAD[1] - 46)   # flame base

# ---- background: black, deep red bloom around the flame, smoke texture
bloom = np.exp(-(((xx - FB[0]) / 600) ** 2 + ((yy - FB[1] + 60) / 440) ** 2))
sm = noise(70, 1) * 0.5 + noise(25, 2) * 0.3
bg = np.stack([8 + 120 * bloom * (0.85 + 0.15 * sm), 4 + 26 * bloom, 6 + 12 * bloom], -1)
vig = ((xx - W * 0.55) / (W * 0.62)) ** 2 + ((yy - H * 0.5) / (H * 0.62)) ** 2
bg *= (1 - 0.65 * np.clip(vig, 0, 1.3))[..., None]
canvas = bg

# ---- the match stick (cylinder shading + grain), rotated around the head
SW, SL = 64, 760
u = np.linspace(-1, 1, SW)[None, :]
shade = 0.45 + 0.55 * np.sqrt(np.clip(1 - u ** 2, 0, 1)) + 0.25 * np.clip(-u, 0, 1)  # lit from the flame side
grain = np.asarray(Image.fromarray(((np.random.default_rng(3).normal(0, 1, (SL // 8, SW)) * 40) + 128).clip(0, 255).astype(np.uint8))
                   .resize((SW, SL), Image.BICUBIC), np.float32)[..., None] / 255
wood = np.array([210, 160, 104], np.float32)[None, None] * shade[..., None] * (0.82 + 0.3 * grain)
along = np.linspace(0, 1, SL)[:, None, None]
char = np.clip(1 - along / 0.2, 0, 1) ** 0.7                 # charred near the head
wood = wood * (1 - 0.85 * char) + np.array([30, 16, 10]) * char
ember = np.clip(1 - along / 0.05, 0, 1) * (0.5 + 0.5 * np.clip(-u, 0, 1))[..., None]
wood += ember * np.array([255, 120, 30]) * 0.9
warm = np.exp(-along / 0.35)                                 # firelight on the upper stick
wood += warm * np.array([90, 40, 0]) * shade[..., None]
stick = np.concatenate([wood.clip(0, 255), np.full((SL, SW, 1), 255, np.float32)], -1).astype(np.uint8)
stick = Image.fromarray(stick, "RGBA")
m = Image.new("L", (SW, SL), 0)
ImageDraw.Draw(m).rounded_rectangle((0, 0, SW - 1, SL + 40), 30, fill=255)
stick.putalpha(m)
# head: rounded red bulb, lit from above by the flame, glowing cracks
hw, hh = 108, 132
yy_h, xx_h = np.mgrid[0:hh, 0:hw].astype(np.float32)
ex_ = (xx_h - hw / 2) / (hw / 2)
ey_ = (yy_h - hh / 2) / (hh / 2)
inside = (ex_ ** 2 + ey_ ** 2) <= 1
nz = np.sqrt(np.clip(1 - ex_ ** 2 - ey_ ** 2, 0, 1))
lit = np.clip(0.35 + 0.65 * (-ey_ * 0.7 + nz * 0.5), 0, 1.2)          # light comes from the top
hc = np.array([150, 34, 22], np.float32) * lit[..., None]
hc += np.clip(-ey_ - 0.35, 0, 1)[..., None] * np.array([255, 150, 60]) * 0.9   # fiery top
hc += (np.random.default_rng(5).normal(0, 10, (hh, hw, 1)))
head = Image.fromarray(np.concatenate([hc.clip(0, 255), (inside * 255)[..., None]], -1).astype(np.uint8), "RGBA")
hd = ImageDraw.Draw(head)
for _ in range(10):
    x, y = rng.uniform(20, hw - 20), rng.uniform(10, hh * 0.55)
    hd.line((x, y, x + rng.uniform(-12, 12), y + rng.uniform(4, 16)), fill=(255, 190, 70, 255), width=2)
head = head.filter(ImageFilter.GaussianBlur(0.7))
match = Image.new("RGBA", (max(SW, hw) + 20, SL + hh // 2), (0, 0, 0, 0))
match.alpha_composite(stick, ((match.width - SW) // 2, hh // 2))
match.alpha_composite(head, ((match.width - hw) // 2, 0))
pivot = (match.width / 2, hh / 2)
ANG = 38    # degrees (counter-clockwise); the stick runs down to the bottom-right corner
big = Image.new("RGBA", (match.height * 2 + 40, match.height * 2 + 40), (0, 0, 0, 0))
off = (big.width // 2 - int(pivot[0]), big.height // 2 - int(pivot[1]))
big.alpha_composite(match, off)
big = big.rotate(ANG, resample=Image.BICUBIC, center=(big.width / 2, big.height / 2))
layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
layer.alpha_composite(big, (int(HEAD[0] - big.width / 2), int(HEAD[1] - big.height / 2)))
la = np.asarray(layer, np.float32)
canvas = canvas * (1 - la[..., 3:] / 255) + la[..., :3] * (la[..., 3:] / 255)

# ---- procedural flame (rises straight up regardless of the stick angle)
FH, FWID = 380, 112
v = (FB[1] - yy) / FH                                        # 0 at base, 1 at tip
turb = noise(18, 7) * 0.5 + noise(8, 8) * 0.25
lean = 26 * np.clip(v, 0, 1) ** 1.6 + 30 * turb * np.clip(v, 0, 1)
width = FWID * np.where(v < 0.12, np.sqrt(np.clip(v + 0.06, 0, 1) / 0.18), (1 - np.clip(v, 0, 1)) ** 0.85 * 1.05)
ux = (xx - FB[0] - lean) / np.maximum(width, 1)
dens = np.exp(-(ux ** 2) * 2.2) * np.clip(1 - v, 0, 1) ** 0.6 * (v > -0.06) * (1 + 0.25 * turb)
dens *= np.clip((v + 0.06) / 0.08, 0, 1)
core = np.exp(-(ux ** 2) * 6) * np.clip(1 - v / 0.55, 0, 1) * (v > -0.02)
stops = [(0.0, (0, 0, 0)), (0.18, (120, 20, 4)), (0.38, (230, 80, 14)), (0.6, (255, 150, 34)), (0.8, (255, 214, 110)), (1.0, (255, 250, 230))]
d = np.clip(dens * 1.15 + core * 0.55, 0, 1)
col = np.zeros((H, W, 3), np.float32)
for (a0, c0), (a1, c1) in zip(stops[:-1], stops[1:]):
    msk = (d >= a0) & (d <= a1)
    t = ((d - a0) / (a1 - a0))[..., None]
    col = np.where(msk[..., None], np.array(c0) * (1 - t) + np.array(c1) * t, col)
blue = np.exp(-(((xx - FB[0]) / 34) ** 2 + ((yy - FB[1] - 6) / 18) ** 2)) * 0.8
col = col * (1 - blue[..., None]) + np.array([70, 120, 255]) * blue[..., None]
alpha = np.clip(d * 1.6, 0, 1)[..., None]
canvas = 255 - (255 - canvas) * (1 - col * alpha / 255)          # screen blend
# heat glow around the flame
glow = np.exp(-(((xx - FB[0]) / 230) ** 2 + ((yy - FB[1] + 160) / 300) ** 2))
canvas = 255 - (255 - canvas) * (1 - np.array([255, 130, 40]) / 255 * 0.55 * glow[..., None])

img = Image.fromarray(canvas.clip(0, 255).astype(np.uint8)).convert("RGBA")
dr = ImageDraw.Draw(img)
# embers rising, with short motion streaks
for _ in range(110):
    ex = FB[0] + rng.normal(0, 140) + 20
    ey = FB[1] - abs(rng.normal(0, 260)) - 60
    L = rng.uniform(4, 16)
    c = (255, int(rng.uniform(130, 220)), 50, int(rng.uniform(120, 255)))
    dr.line((ex, ey, ex - L * 0.3, ey + L), fill=c, width=int(rng.uniform(1, 4)))
# faint smoke above the flame
smoke = Image.new("L", (W, H), 0)
sd = ImageDraw.Draw(smoke)
for k in range(40):
    sx = FB[0] + 30 + math.sin(k * 0.45) * 40 + k * 2
    sy = FB[1] - FH - k * 6 + 40
    r = 20 + k * 2.2
    sd.ellipse((sx - r, sy - r, sx + r, sy + r), fill=26)
sm_im = Image.new("RGBA", (W, H), (150, 140, 140, 255))
sm_im.putalpha(smoke.filter(ImageFilter.GaussianBlur(26)))
img.alpha_composite(sm_im)

# ---- headline (left): red classic serif with soft dark shadow and top-light gradient
f = ImageFont.truetype(f"{FD}/Cinzel.ttf", 112)
f.set_variation_by_name("Bold")
lines = TEXT.split("|")
txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sh = Image.new("L", (W, H), 0)
td, sdw = ImageDraw.Draw(txt), ImageDraw.Draw(sh)
heights = [td.textbbox((0, 0), ln, font=f) for ln in lines]
total = sum(b[3] - b[1] for b in heights) + 26 * (len(lines) - 1)
y = H / 2 - total / 2 - 10
for ln, bb in zip(lines, heights):
    x = 56 - bb[0]
    sdw.text((x + 5, y - bb[1] + 7), ln, font=f, fill=255)
    td.text((x, y - bb[1]), ln, font=f, fill=(214, 24, 24, 255))
    y += (bb[3] - bb[1]) + 26
shadow = Image.new("RGBA", (W, H), (0, 0, 0, 255))
shadow.putalpha(sh.filter(ImageFilter.GaussianBlur(10)).point(lambda q: min(255, int(q * 1.7))))
img.alpha_composite(shadow)
ta = np.asarray(txt, np.float32)
ta[..., :3] = (ta[..., :3] * np.linspace(1.15, 0.7, H)[:, None, None]).clip(0, 255)
img.alpha_composite(Image.fromarray(ta.astype(np.uint8), "RGBA"))

out = (np.asarray(img.convert("RGB"), np.float32) + rng.normal(0, 6, (H, W, 1))).clip(0, 255).astype(np.uint8)
Image.fromarray(out).save(OUT)
Image.fromarray(out).resize((320, 180), Image.LANCZOS).save(OUT.replace(".png", "_pequena.png"))
