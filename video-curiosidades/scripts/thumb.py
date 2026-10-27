"""YouTube thumbnail (1280x720): red paper, crow professor, 'FOI SEM QUERER?!', the video's inventions as stickers."""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crow_prof

CROW_SRC, SPOON_SRC, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
W, H = 1280, 720
rng = np.random.default_rng(9)
INK, CREAM, YEL, RED = (20, 16, 18), (250, 244, 230), (255, 214, 40), (196, 30, 34)
font = lambda f, s: ImageFont.truetype(f"{FD}/{f}", s)


def blotch(scale, amp):
    small = rng.normal(0, 1, (H // scale + 2, W // scale + 2)).astype(np.float32)
    im = Image.fromarray(((small * 40) + 128).clip(0, 255).astype(np.uint8))
    im = im.resize((W + 2 * scale, H + 2 * scale), Image.BICUBIC).crop((scale, scale, W + scale, H + scale))
    return (np.asarray(im, dtype=np.float32) - 128) / 40 * amp


# red paper background, darker toward the edges, brighter behind the text
tex = blotch(80, 8) + blotch(18, 5) + rng.normal(0, 6, (H, W)).astype(np.float32)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
tex -= (((xx - W * 0.45) / (W * 0.6)) ** 2 + ((yy - H * 0.45) / (H * 0.7)) ** 2) * 38
bg = (np.array([196, 32, 34], np.float32)[None, None] + tex[..., None] * np.array([1.0, 0.35, 0.35])).clip(0, 255)
img = Image.fromarray(bg.astype(np.uint8)).convert("RGBA")
d = ImageDraw.Draw(img, "RGBA")
for k in range(28):  # light rays from behind the objects
    a = k / 28 * math.tau
    d.polygon([(380, 520), (380 + math.cos(a) * 1200, 520 + math.sin(a) * 1200),
               (380 + math.cos(a + 0.09) * 1200, 520 + math.sin(a + 0.09) * 1200)], fill=(255, 120, 90, 16))


def sticker(im, r=8, col=CREAM):
    pad = r + 24
    big = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    a = Image.new("L", big.size, 0)
    a.paste(im.getchannel("A"), (pad, pad))
    border = a.point(lambda v: 255 if v > 30 else 0).filter(ImageFilter.MaxFilter(2 * r + 1))
    sh = border.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.55))
    shadow = Image.new("RGBA", big.size, (40, 0, 0, 255))
    shadow.putalpha(sh)
    out = Image.new("RGBA", big.size, (0, 0, 0, 0))
    out.alpha_composite(shadow, (8, 12))
    paper = Image.new("RGBA", big.size, col + (255,))
    paper.putalpha(border)
    out.alpha_composite(paper)
    out.alpha_composite(im, (pad, pad))
    return out


def place(im, cx, cy, rot=0, scale=1.0):
    if scale != 1:
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


# --- inventions
def match():
    im = Image.new("RGBA", (200, 420), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    g = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse((10, 0, 190, 200), fill=(255, 190, 60, 170))
    im.alpha_composite(g.filter(ImageFilter.GaussianBlur(22)))
    d.rounded_rectangle((86, 170, 114, 410), 10, fill=(222, 178, 118, 255))
    d.ellipse((72, 138, 128, 196), fill=(150, 36, 28, 255))
    d.polygon([(100, 10), (150, 100), (136, 150), (100, 166), (64, 150), (50, 100)], fill=(250, 120, 30, 255))
    d.polygon([(100, 70), (124, 118), (100, 152), (76, 118)], fill=(255, 226, 110, 255))
    return sticker(im)


def bowl():
    im = Image.new("RGBA", (360, 250), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for _ in range(46):
        x, y = rng.uniform(50, 310), rng.uniform(40, 120)
        r = rng.uniform(16, 26)
        pts = [(x + math.cos(a) * r * rng.uniform(0.7, 1), y + math.sin(a) * r * 0.6) for a in np.linspace(0, math.tau, 7)[:-1]]
        d.polygon(pts, fill=(196, 120, 40, 255))
        d.polygon([(x + (px - x) * 0.75, y + (py - y) * 0.75) for px, py in pts], fill=(240, 180, 70, 255))
    d.chord((10, -20, 350, 245), 0, 180, fill=(250, 250, 252, 255), outline=(190, 196, 210, 255), width=5)
    d.rectangle((10, 108, 350, 114), fill=(250, 250, 252, 255))
    d.arc((40, 120, 320, 220), 20, 160, fill=(60, 110, 200, 255), width=10)
    return sticker(im)


def windshield():
    im = Image.new("RGBA", (360, 230), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(40, 10), (320, 10), (356, 222), (4, 222)], fill=(40, 40, 48, 255))
    d.polygon([(54, 22), (306, 22), (338, 210), (22, 210)], fill=(150, 215, 245, 255))
    d.line((80, 40, 140, 190), fill=(220, 245, 255, 255), width=8)
    cx, cy = 210, 110
    for k in range(11):
        a = k / 11 * math.tau + rng.uniform(-0.2, 0.2)
        L = rng.uniform(60, 110)
        d.line((cx, cy, cx + math.cos(a) * L, cy + math.sin(a) * L * 0.75), fill=(255, 255, 255, 255), width=3)
    for rr in (18, 40, 66):
        pts = [(cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.75) for a in np.linspace(0, math.tau, 12)]
        d.line(pts, fill=(255, 255, 255, 255), width=3)
    return sticker(im)


def spoon():
    src = Image.open(SPOON_SRC).convert("RGB").crop((0, 118, 256, 228))
    a = np.asarray(src, np.float32)
    alpha = ((60 - (a.max(-1) - a.min(-1))) / 30).clip(0, 1) * 255
    g = a.mean(-1, keepdims=True)
    rgb = np.concatenate([g, g, g * 0.98], -1)
    im = Image.fromarray(np.concatenate([rgb, alpha[..., None]], -1).astype(np.uint8), "RGBA").resize((512, 220), Image.LANCZOS)
    return sticker(im)


place(windshield(), 600, 585, 6, 0.85)
place(bowl(), 345, 545, -4, 0.9)
place(match(), 120, 520, 12, 0.78)

# --- crow professor, beak open (surprised), big on the right
crow = crow_prof.build(CROW_SRC, 1.0)
cimg = crow_prof.frame(crow, 1.0)
s = 0.92
cimg = cimg.resize((int(cimg.width * s), int(cimg.height * s)), Image.LANCZOS)
img.alpha_composite(cimg, (W - cimg.width + 150, H - cimg.height + 60))

# --- headline
def stroke_text(xy, text, f, fill, stroke=12, rot=0, shadow=10):
    bb = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), text, font=f, stroke_width=stroke)
    t = Image.new("RGBA", (bb[2] - bb[0] + 60, bb[3] - bb[1] + 60), (0, 0, 0, 0))
    td = ImageDraw.Draw(t)
    td.text((30 - bb[0] + shadow, 30 - bb[1] + shadow), text, font=f, fill=INK + (255,), stroke_width=stroke, stroke_fill=INK + (255,))
    td.text((30 - bb[0], 30 - bb[1]), text, font=f, fill=fill + (255,), stroke_width=stroke, stroke_fill=INK + (255,))
    t = t.rotate(rot, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(t, (int(xy[0]), int(xy[1])))
    return t.size


stroke_text((10, -10), "FOI SEM", font("Anton-Regular.ttf", 170), CREAM, 12, 2)
stroke_text((10, 165), "QUERER?!", font("Anton-Regular.ttf", 190), YEL, 13, 2)

# small tag
tag = "INVENÇÕES ACIDENTAIS"
f = font("Anton-Regular.ttf", 40)
bb = ImageDraw.Draw(img).textbbox((0, 0), tag, font=f)
tw = bb[2] - bb[0]
t = Image.new("RGBA", (tw + 40, 70), INK + (255,))
ImageDraw.Draw(t).text((20 - bb[0], 35 - (bb[3] - bb[1]) / 2 - bb[1]), tag, font=f, fill=CREAM + (255,))
place(t, 300, 405, -3)

# hand-drawn yellow arrow from the headline to the objects

img = img.convert("RGB")
img.save(OUT, quality=95)
img.resize((320, 180), Image.LANCZOS).save(OUT.replace(".png", "_pequena.png"))
