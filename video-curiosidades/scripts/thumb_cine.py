"""Cinematic thumbnail in the style of the reference channel: dark scene, one subject with dramatic light,
short red serif headline. The channel crow is lit by a burning match."""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

CROW_SRC, OUT = sys.argv[1], sys.argv[2]
TEXT = sys.argv[3] if len(sys.argv) > 3 else "FOI SEM QUERER"
FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
W, H = 1280, 720
rng = np.random.default_rng(4)

# ---- background: near-black, deep red glow behind the crow, smoky texture, vignette
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
glow = np.exp(-(((xx - 930) / 430) ** 2 + ((yy - 300) / 340) ** 2))
small = rng.normal(0, 1, (H // 60 + 2, W // 60 + 2)).astype(np.float32)
smoke = np.asarray(Image.fromarray(((small * 40) + 128).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) / 255
base = np.stack([12 + 150 * glow * (0.8 + 0.4 * smoke), 6 + 14 * glow, 8 + 12 * glow], -1)
vig = (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
base *= (1 - 0.55 * np.clip(vig, 0, 1.4))[..., None]
base += rng.normal(0, 3, base.shape)
img = Image.fromarray(base.clip(0, 255).astype(np.uint8)).convert("RGBA")

# ---- the crow (no props: serious look), cut from its red background
c = Image.open(CROW_SRC).convert("RGB")
a = np.asarray(c, np.float32)
red = a[..., 0] - np.maximum(a[..., 1], a[..., 2])
alpha = Image.fromarray(((130 - red) / 70 * 255).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
ImageDraw.Draw(alpha).rectangle((205, 320, 236, 362), fill=0)
S = 1.0
crow = c.convert("RGBA")
crow.putalpha(alpha)
crow = crow.resize((int(crow.width * S), int(crow.height * S)), Image.LANCZOS)
# warm key light from the match (left), cool falloff to the right
cw, ch = crow.size
lx = np.linspace(1, 0, cw)[None, :] ** 1.6
ly = np.exp(-((np.arange(ch)[:, None] - 240 * S) / (300 * S)) ** 2)
light = (lx * ly)[..., None]
ca = np.asarray(crow, np.float32)
rgb = ca[..., :3] * (0.85 + 0.0 * light) + light * np.array([150, 70, 10]) * (ca[..., :3].mean(-1, keepdims=True) / 255 + 0.25)
crow = Image.fromarray(np.concatenate([rgb.clip(0, 255), ca[..., 3:]], -1).astype(np.uint8), "RGBA")
CX, CY = 1280 - cw + 70, 720 - ch + 40
# rim light: an orange halo along the crow's front edge
rim = crow.getchannel("A").filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(6))
rim_a = np.asarray(rim, np.float32) * (lx[0][None, :] * 0.9 + 0.1)
rim_im = Image.new("RGBA", crow.size, (255, 140, 50, 255))
rim_im.putalpha(Image.fromarray(rim_a.clip(0, 255).astype(np.uint8)))
img.alpha_composite(rim_im, (CX - 6, CY))
img.alpha_composite(crow, (CX, CY))

# ---- the burning match, in front of the beak
HX, HY = 290, 330               # match head
MX, MY = HX + 6, HY - 90        # flame centre
halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
hd = ImageDraw.Draw(halo)
for r, col in ((340, (255, 120, 30, 55)), (200, (255, 150, 50, 95)), (90, (255, 200, 110, 150))):
    hd.ellipse((MX - r, MY - r, MX + r, MY + r), fill=col)
img = Image.alpha_composite(img, halo.filter(ImageFilter.GaussianBlur(60)))
d = ImageDraw.Draw(img)
ang = math.radians(-24)           # stick goes down and to the left
L = 200
ex, ey = HX + math.sin(ang) * L, HY + math.cos(ang) * L
d.line((HX, HY, ex, ey), fill=(196, 146, 92, 255), width=22)
d.line((HX + 5, HY, ex + 5, ey), fill=(226, 184, 130, 255), width=6)
cx_, cy_ = HX + math.sin(ang) * 46, HY + math.cos(ang) * 46
d.line((HX, HY, cx_, cy_), fill=(46, 26, 18, 255), width=23)            # charred wood under the head
d.ellipse((HX - 21, HY - 24, HX + 21, HY + 20), fill=(60, 16, 12, 255))
d.ellipse((HX - 12, HY - 16, HX + 4, HY + 0), fill=(140, 44, 28, 255))


def teardrop(cx, base, w, h, lean):
    pts = []
    for k in range(41):
        u = k / 40 * math.pi * 2
        x = math.sin(u) * w / 2 * (1 - 0.0 * math.cos(u))
        y = -math.cos(u)
        if y > 0:   # upper part narrows to a curved tip
            yy = base - y * h
            x = x * (1 - y) ** 0.9 + lean * y ** 2
        else:
            yy = base - y * w * 0.45
        pts.append((cx + x, yy))
    return pts


flame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
fd = ImageDraw.Draw(flame)
fbase = HY - 26
for w_, h_, col in ((92, 230, (255, 100, 20, 220)), (66, 170, (255, 160, 40, 240)), (40, 112, (255, 228, 140, 255)), (20, 60, (255, 252, 230, 255))):
    fd.polygon(teardrop(HX + 4, fbase, w_, h_, 14), fill=col)
fd.ellipse((HX - 16, fbase - 6, HX + 22, fbase + 18), fill=(90, 140, 255, 160))
img.alpha_composite(flame.filter(ImageFilter.GaussianBlur(4)))
# embers drifting up
d = ImageDraw.Draw(img)
for _ in range(60):
    ex, ey = MX + rng.normal(0, 110), MY - abs(rng.normal(0, 220)) - 20
    r = rng.uniform(1, 3.4)
    d.ellipse((ex - r, ey - r, ex + r, ey + r), fill=(255, int(rng.uniform(140, 220)), 60, int(rng.uniform(120, 255))))

# ---- headline: red classic serif, dark soft shadow (no cartoon outline)
f = ImageFont.truetype(f"{FD}/Cinzel.ttf", 118)
f.set_variation_by_name("Bold")
lines = TEXT.split("|")
txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sh = Image.new("L", (W, H), 0)
tdraw, sdraw = ImageDraw.Draw(txt), ImageDraw.Draw(sh)
y = 520 if len(lines) == 1 else 470
for line in lines:
    bb = tdraw.textbbox((0, 0), line, font=f)
    x = 50 - bb[0]
    sdraw.text((x + 4, y + 6), line, font=f, fill=255)
    tdraw.text((x, y), line, font=f, fill=(206, 22, 22, 255))
    y += (bb[3] - bb[1]) + 18
shadow = Image.new("RGBA", (W, H), (0, 0, 0, 255))
shadow.putalpha(sh.filter(ImageFilter.GaussianBlur(9)).point(lambda v: min(255, int(v * 1.6))))
img.alpha_composite(shadow)
# subtle vertical gradient inside the letters (brighter top, darker bottom)
ta = np.asarray(txt, np.float32)
grad = np.linspace(1.1, 0.72, H)[:, None, None]
ta[..., :3] = (ta[..., :3] * grad).clip(0, 255)
img.alpha_composite(Image.fromarray(ta.astype(np.uint8), "RGBA"))

# film grain
g = rng.normal(0, 7, (H, W, 1))
out = (np.asarray(img.convert("RGB"), np.float32) + g).clip(0, 255).astype(np.uint8)
Image.fromarray(out).save(OUT)
Image.fromarray(out).resize((320, 180), Image.LANCZOS).save(OUT.replace(".png", "_pequena.png"))
