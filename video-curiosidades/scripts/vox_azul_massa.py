"""Vox-style collage on blue paper: paper-doll Kellogg brothers find stale dough, roll it, and get flakes.
Crow professor talks in the corner; synthesized paper/whoosh/stamp/typewriter SFX are muxed in."""
import math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crow_prof

CROW_SRC, OUT = sys.argv[1], sys.argv[2]
FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
W, H, FPS = 1920, 1080, 30
DUR = 15.0
N = int(DUR * FPS)
rng = np.random.default_rng(5)

INK = (24, 20, 20)
CREAM = (246, 238, 220)
NEWS = (232, 224, 204)
YEL = (238, 196, 60)
RED = (196, 30, 34)

F = {
    "anton": f"{FD}/Anton-Regular.ttf",
    "abril": f"{FD}/AbrilFatface-Regular.ttf",
    "type": f"{FD}/SpecialElite-Regular.ttf",
    "mark": f"{FD}/PermanentMarker-Regular.ttf",
}
font = lambda k, s: ImageFont.truetype(F[k], s)


def ease_out(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def ease_back(t):
    t = min(max(t, 0.0), 1.0)
    c = 1.9
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


# ------------------------------------------------------------------ background
PW, PH = int(W * 1.08), int(H * 1.08)


def blotch(scale, amp, w, h):
    small = rng.normal(0, 1, (h // scale + 2, w // scale + 2)).astype(np.float32)
    im = Image.fromarray(((small * 40) + 128).clip(0, 255).astype(np.uint8))
    im = im.resize((w + 2 * scale, h + 2 * scale), Image.BICUBIC).crop((scale, scale, w + scale, h + scale))
    return (np.asarray(im, dtype=np.float32) - 128) / 40 * amp


tex = blotch(110, 8, PW, PH) + blotch(24, 5, PW, PH) + rng.normal(0, 6, (PH, PW)).astype(np.float32)
yy, xx = np.mgrid[0:PH, 0:PW].astype(np.float32)
tex -= (((xx - PW / 2) / (PW / 2)) ** 2 + ((yy - PH / 2) / (PH / 2)) ** 2) * 22
BG = (np.array([30, 72, 146], np.float32)[None, None] + tex[..., None] * np.array([0.35, 0.55, 1.0])).clip(0, 255)
BG = Image.fromarray(BG.astype(np.uint8))
bd = ImageDraw.Draw(BG, "RGBA")
for _ in range(1500):
    x, y = rng.uniform(0, PW), rng.uniform(0, PH)
    a = rng.uniform(0, math.pi)
    L = rng.uniform(5, 20)
    bd.line((x, y, x + math.cos(a) * L, y + math.sin(a) * L), fill=(150, 190, 245, int(rng.uniform(20, 55))), width=1)
BG = BG.convert("RGBA")
OX, OY = (PW - W) // 2, (PH - H) // 2

GRAIN = []
for _ in range(6):
    g = rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
    g = Image.fromarray((g * 14 + 128).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    GRAIN.append(np.asarray(g, dtype=np.int16) - 128)


# ------------------------------------------------------------------ collage helpers
def torn_poly(w, h, step=9, jit=3.5):
    pts = []
    for x in np.arange(0, w, step):
        pts.append((x, rng.uniform(-jit, jit)))
    for y in np.arange(0, h, step):
        pts.append((w + rng.uniform(-jit, jit), y))
    for x in np.arange(w, 0, -step):
        pts.append((x, h + rng.uniform(-jit, jit)))
    for y in np.arange(h, 0, -step):
        pts.append((rng.uniform(-jit, jit), y))
    return pts


def scrap(w, h, color, edge=(255, 252, 245)):
    """Torn paper piece with a lighter fibrous edge, paper grain and a drop shadow."""
    pad = 30
    img = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    poly = [(x + pad, y + pad) for x, y in torn_poly(w, h)]
    under = [(x + rng.uniform(-3, 3), y + rng.uniform(-3, 3)) for x, y in torn_poly(w, h, 7, 6)]
    under = [(x + pad, y + pad) for x, y in under]
    sh = Image.new("L", img.size, 0)
    ImageDraw.Draw(sh).polygon([(x + 7, y + 10) for x, y in under], fill=120)
    sh = sh.filter(ImageFilter.GaussianBlur(9))
    shadow = Image.new("RGBA", img.size, (0, 10, 40, 255))
    shadow.putalpha(sh)
    img.alpha_composite(shadow)
    d = ImageDraw.Draw(img)
    d.polygon(under, fill=edge + (255,))
    d.polygon(poly, fill=color + (255,))
    n = rng.normal(0, 7, (img.height, img.width))
    arr = np.asarray(img, dtype=np.float32)
    m = arr[..., 3] > 0
    arr[..., :3][m] = (arr[..., :3][m] + n[m][:, None]).clip(0, 255)
    return Image.fromarray(arr.astype(np.uint8)), pad


def halftone(dark, spacing=8, color=INK):
    """dark: L image (255 = full ink). Returns RGBA dot layer."""
    out = Image.new("RGBA", dark.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    a = np.asarray(dark, dtype=np.float32) / 255
    for y in range(spacing // 2, dark.height, spacing):
        off = spacing // 2 if (y // spacing) % 2 else 0
        for x in range(spacing // 2 + off, dark.width, spacing):
            v = a[y, x]
            if v > 0.04:
                r = spacing * 0.62 * math.sqrt(v)
                d.ellipse((x - r, y - r, x + r, y + r), fill=color + (255,))
    return out


def bust(d, cx, base_y, s, shade, hat=None):
    """Simple head-and-shoulders silhouette."""
    d.ellipse((cx - 95 * s, base_y - 120 * s, cx + 95 * s, base_y + 80 * s), fill=shade)  # shoulders
    d.rectangle((cx - 22 * s, base_y - 150 * s, cx + 22 * s, base_y - 95 * s), fill=shade)  # neck
    d.ellipse((cx - 40 * s, base_y - 235 * s, cx + 40 * s, base_y - 135 * s), fill=shade)  # head
    if hat == "bowler":
        d.ellipse((cx - 58 * s, base_y - 222 * s, cx + 58 * s, base_y - 204 * s), fill=shade)
        d.ellipse((cx - 38 * s, base_y - 268 * s, cx + 38 * s, base_y - 200 * s), fill=shade)
    elif hat == "chef":
        d.rectangle((cx - 34 * s, base_y - 290 * s, cx + 34 * s, base_y - 215 * s), fill=shade)
        for k in (-30, 0, 30):
            d.ellipse((cx + (k - 30) * s, base_y - 330 * s, cx + (k + 30) * s, base_y - 270 * s), fill=shade)
    elif hat == "tophat":
        d.rounded_rectangle((cx - 62 * s, base_y - 228 * s, cx + 62 * s, base_y - 212 * s), 6, fill=shade)
        d.rectangle((cx - 40 * s, base_y - 330 * s, cx + 40 * s, base_y - 215 * s), fill=shade)
        d.rectangle((cx - 30 * s, base_y - 150 * s, cx + 30 * s, base_y - 115 * s), fill=shade)  # high collar
    elif hat == "hair":
        d.ellipse((cx - 46 * s, base_y - 245 * s, cx + 46 * s, base_y - 170 * s), fill=shade)


def crowd_card(w, h, color):
    img, pad = scrap(w, h, color)
    dark = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(dark)
    rows = [(0.55, 120, 0.42), (0.75, 165, 0.62), (1.0, 230, 0.9)]
    for row, (s, step, shade) in enumerate(rows):
        x = rng.uniform(-30, 30)
        while x < w + 60:
            hat = rng.choice(["bowler", "hair", None, "bowler", None])
            bust(d, x, h - 10 - (2 - row) * 70, s * rng.uniform(0.9, 1.08), int(255 * shade), hat)
            x += step * rng.uniform(0.85, 1.15)
    dots = halftone(dark, 8)
    img.alpha_composite(dots, (pad, pad))
    return img


def person_card(w, h, color, hat):
    img, pad = scrap(w, h, color)
    dark = Image.new("L", (w, h), 0)
    bust(ImageDraw.Draw(dark), w / 2, h + 20, w / 210, 230, hat)
    img.alpha_composite(halftone(dark, 7), (pad, pad))
    return img


def petri_card():
    w, h = 470, 430
    img, pad = scrap(w, h, (250, 248, 242))
    d = ImageDraw.Draw(img)
    cx, cy, r = pad + w / 2, pad + h / 2 - 25, 170
    d.ellipse((cx - r - 8, cy - r - 8, cx + r + 8, cy + r + 8), fill=(205, 210, 205, 255), outline=(150, 155, 150, 255), width=3)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(236, 214, 150, 255))
    mx, my = cx - 30, cy + 10
    for _ in range(220):  # bacteria colonies, killed in a ring around the mould
        a, rr = rng.uniform(0, math.tau), rng.uniform(0, r - 10)
        x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr
        if math.hypot(x - mx, y - my) < 105:
            continue
        q = rng.uniform(3, 6)
        d.ellipse((x - q, y - q, x + q, y + q), fill=(250, 244, 222, 255), outline=(200, 180, 120, 255))
    mould = Image.new("L", img.size, 0)
    md = ImageDraw.Draw(mould)
    for _ in range(40):
        a, rr = rng.uniform(0, math.tau), rng.uniform(0, 34)
        q = rng.uniform(16, 30)
        x, y = mx + math.cos(a) * rr, my + math.sin(a) * rr
        md.ellipse((x - q, y - q, x + q, y + q), fill=255)
    mould = mould.filter(ImageFilter.GaussianBlur(3))
    green = Image.new("RGBA", img.size, (96, 128, 84, 255))
    green.putalpha(mould)
    img.alpha_composite(green)
    rim = mould.filter(ImageFilter.MaxFilter(9)).point(lambda v: 150 if v > 60 else 0).filter(ImageFilter.GaussianBlur(2))
    rimc = Image.new("RGBA", img.size, (240, 246, 232, 255))
    rimc.putalpha(Image.fromarray((np.asarray(rim, np.int16) - np.asarray(mould, np.int16)).clip(0, 255).astype(np.uint8)))
    img.alpha_composite(rimc)
    d.arc((cx - r + 18, cy - r + 18, cx + r - 18, cy + r - 18), 200, 250, fill=(255, 255, 255, 200), width=6)
    d.text((pad + w / 2 - 55, pad + h - 70), "1928", font=font("mark", 54), fill=INK + (255,))
    return img


def label(text, fk, size, fg, bg, padx=26, pady=14):
    f = font(fk, size)
    bb = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), text, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    img, pad = scrap(tw + 2 * padx, th + 2 * pady, bg)
    ImageDraw.Draw(img).text((pad + padx - bb[0], pad + pady - bb[1]), text, font=f, fill=fg + (255,))
    return img


def clipping():
    w, h = 640, 470
    img, pad = scrap(w, h, NEWS)
    d = ImageDraw.Draw(img)
    d.text((pad + 30, pad + 18), "A LENDA DA", font=font("abril", 58), fill=INK + (255,))
    d.text((pad + 30, pad + 88), "BATATA CHIPS", font=font("abril", 58), fill=INK + (255,))
    d.line((pad + 30, pad + 168, pad + w - 30, pad + 168), fill=INK + (255,), width=3)
    pic = Image.new("L", (250, 230), 0)
    bust(ImageDraw.Draw(pic), 125, 250, 1.0, 230, "chef")
    d.rectangle((pad + 30, pad + 190, pad + 280, pad + 420), fill=(214, 204, 180, 255))
    img.alpha_composite(halftone(pic, 6), (pad + 30, pad + 190))
    for row in range(10):
        y = pad + 196 + row * 23
        d.rectangle((pad + 305, y, pad + w - 30 - rng.uniform(0, 60), y + 9), fill=(120, 112, 100, 255))
    d.text((pad + 30, pad + 428), "Saratoga Springs, 1853", font=font("type", 26), fill=INK + (255,))
    return img


def stamp(text, size, w, h):
    st = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(st)
    sd.rounded_rectangle((14, 14, w - 14, h - 14), 22, fill=(250, 240, 225, 255), outline=RED + (255,), width=16)
    f = font("anton", size)
    bb = sd.textbbox((0, 0), text, font=f)
    sd.text((w / 2 - (bb[2] - bb[0]) / 2 - bb[0], h / 2 - (bb[3] - bb[1]) / 2 - bb[1]), text, font=f, fill=RED + (255,))
    holes = Image.fromarray(((rng.random((h, w)) > 0.14) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.1))
    a = np.asarray(st.getchannel("A"), np.float32) * np.asarray(holes, np.float32) / 255 * 0.95
    st.putalpha(Image.fromarray(a.astype(np.uint8)))
    return st.rotate(-9, resample=Image.BICUBIC, expand=True)


# ------------------------------------------------------------------ timeline of collage elements
SFX = []  # (time, kind)


class El:
    def __init__(self, img, x, y, t_in, rot=0.0, kind="slap", t_out=None, dur=0.16, sfx="slap"):
        self.img, self.x, self.y, self.t_in, self.rot, self.kind, self.t_out, self.dur = img, x, y, t_in, rot, kind, t_out, dur
        self.cache = None
        if sfx:
            SFX.append((t_in, sfx))

    def draw(self, canvas, t):
        if t < self.t_in:
            return
        p = (t - self.t_in) / self.dur
        x, y, rot, s, alpha = self.x, self.y, self.rot, 1.0, 1.0
        if self.kind == "slap":
            s = 1.0 + 0.32 * (1 - ease_out(p))
            alpha = min(1.0, p * 2.5)
        elif self.kind == "pop":
            s = max(0.01, ease_back(p))
        moving = p < 1
        if self.t_out is not None and t > self.t_out:
            q = (t - self.t_out) / 0.3
            x -= (q ** 2) * 2200
            rot += q * 30
            moving = True
        if not moving and self.cache is not None:
            img = self.cache
        else:
            img = self.img.rotate(rot, resample=Image.BICUBIC, expand=True)
            if abs(s - 1) > 0.005:
                img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BILINEAR)
            if alpha < 1:
                img = img.copy()
                img.putalpha(img.getchannel("A").point(lambda v: int(v * alpha)))
            if not moving:
                self.cache = img
        canvas.alpha_composite(img, (int(OX + x - img.width / 2), int(OY + y - img.height / 2)))


els = []

STYLES = [(CREAM, INK, "abril"), (INK, CREAM, "anton"), ((255, 255, 255), RED, "anton"), (YEL, INK, "type"),
          (NEWS, INK, "anton"), (CREAM, RED, "abril"), (INK, YEL, "abril")]
# "Quando voltaram, a massa tinha ficado velha. Em vez de jogar tudo fora, eles resolveram passar a massa no
#  rolo. E aí veio a surpresa: em vez de virar uma folha lisa, ela se partiu em vários flocos."
import paper_dolls as PD

DOLL_NOISE = rng.normal(0, 6, (PD.CH, PD.CW, 1))


def doll(kind, **pose):
    im = PD.draw(kind, **pose)
    a = np.asarray(im, np.float32)
    m = a[..., 3:] > 0
    a[..., :3] = np.where(m, (a[..., :3] + DOLL_NOISE).clip(0, 255), a[..., :3])
    return PD.with_border(Image.fromarray(a.astype(np.uint8)))


TABLE_X0, TABLE_X1, TABLE_Y = 360, 900, 812
TCX = (TABLE_X0 + TABLE_X1) / 2
FEET_Y = 1040


def table_img():
    w = TABLE_X1 - TABLE_X0
    im = Image.new("RGBA", (w + 40, 340), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for lx in (40, w - 10):
        d.rectangle((lx, 30, lx + 26, 330), fill=(104, 68, 40, 255))
    d.rectangle((20, 0, w + 20, 34), fill=(150, 98, 56, 255))
    for k in range(5):
        y = 6 + k * 6
        d.line((30, y, w + 10, y + rng.uniform(-2, 2)), fill=(128, 82, 46, 255), width=1)
    d.rectangle((20, 30, w + 20, 40), fill=(104, 68, 40, 255))
    return sticker(im, 6)



def sticker(img, r=9, col=(250, 246, 236)):
    pad = r + 24
    big = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    a = Image.new("L", big.size, 0)
    a.paste(img.getchannel("A"), (pad, pad))
    border = a.point(lambda v: 255 if v > 30 else 0).filter(ImageFilter.MaxFilter(2 * r + 1)).filter(ImageFilter.GaussianBlur(1))
    sh = border.filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * 0.45))
    shadow = Image.new("RGBA", big.size, (0, 10, 40, 255))
    shadow.putalpha(sh)
    out = Image.new("RGBA", big.size, (0, 0, 0, 0))
    out.alpha_composite(shadow, (6, 9))
    paper = Image.new("RGBA", big.size, col + (255,))
    paper.putalpha(border)
    out.alpha_composite(paper)
    out.alpha_composite(img, (pad, pad))
    return out


def pot_img():
    im = Image.new("RGBA", (260, 170), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((20, 40, 240, 168), 30, fill=(74, 76, 86, 255))
    d.ellipse((6, 22, 254, 66), fill=(104, 106, 118, 255))
    d.ellipse((22, 30, 238, 60), fill=(176, 170, 118, 255))
    for k in range(9):
        x, y = rng.uniform(40, 220), rng.uniform(34, 52)
        d.ellipse((x - 14, y - 8, x + 14, y + 8), fill=(160, 158, 104, 255))
        d.ellipse((x - 4, y - 3, x + 2, y + 1), fill=(120, 140, 80, 255))
    d.rectangle((0, 70, 24, 84), fill=(54, 56, 64, 255))
    d.rectangle((236, 70, 260, 84), fill=(54, 56, 64, 255))
    return sticker(im, 6)


def trash_img():
    im = Image.new("RGBA", (190, 230), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(26, 40), (164, 40), (150, 226), (40, 226)], fill=(150, 156, 160, 255))
    for x in (60, 95, 130):
        d.line((x, 56, x - 4 + (x - 95) * 0.1, 212), fill=(110, 116, 122, 255), width=8)
    d.rounded_rectangle((10, 18, 180, 44), 8, fill=(120, 126, 132, 255))
    d.rounded_rectangle((76, 0, 114, 22), 8, fill=(120, 126, 132, 255))
    return sticker(im, 6)


def pin_img():
    im = Image.new("RGBA", (380, 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((70, 4, 310, 56), 24, fill=(206, 160, 104, 255))
    d.line((90, 18, 290, 18), fill=(232, 196, 140, 255), width=6)
    for x0 in (0, 300):
        d.rounded_rectangle((x0 + 4, 20, x0 + 76, 40), 10, fill=(170, 122, 72, 255))
    return sticker(im, 5)


def flake_img(seed):
    r_ = np.random.default_rng(seed)
    im = Image.new("RGBA", (70, 70), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    n = r_.integers(6, 9)
    pts = []
    for k in range(n):
        a = k / n * math.tau
        rr = r_.uniform(18, 32)
        pts.append((35 + math.cos(a) * rr, 35 + math.sin(a) * rr * r_.uniform(0.6, 1.0)))
    d.polygon(pts, fill=(176, 104, 36, 255))
    d.polygon([(35 + (x - 35) * 0.8, 35 + (y - 35) * 0.8) for x, y in pts], fill=(232, 172, 70, 255))
    d.line([(35 + (x - 35) * 0.5, 33 + (y - 35) * 0.4) for x, y in pts[:3]], fill=(250, 214, 130, 255), width=3)
    return sticker(im, 4)


TABLE = table_img()
POT, TRASH, PIN = pot_img(), trash_img(), pin_img()
FLAKES = [flake_img(k) for k in range(6)]
KERNEL = FLAKES[0]

# ---- timeline (s)
T_STALE, T_TRASH, T_X1, T_DUMP, T_ROLL0, T_ROLL1 = 2.0, 3.6, 4.05, 5.0, 5.3, 7.2
T_SURP, T_SURP_END, T_LISA, T_X2, T_CRACK, T_BURST = 7.55, 9.05, 9.3, 10.3, 10.95, 11.3

top_els = []
top_els.append(El(stamp("VELHA!", 120, 420, 180), TCX, 560, T_STALE, 0, dur=0.14, sfx="stamp", t_out=T_DUMP - 0.1))
top_els.append(El(label("JOHN", "anton", 60, INK, CREAM, 18, 6), 250, 330, 1.55, -4, t_out=T_DUMP - 0.1, sfx="tap"))
top_els.append(El(label("WILL", "anton", 60, CREAM, INK, 18, 6), 1020, 290, 1.7, 4, t_out=T_DUMP - 0.1, sfx="tap"))
TRASH_EL = El(TRASH, 640, 300, T_TRASH, -6, "pop", T_DUMP - 0.1, 0.22, "slap")
top_els.append(TRASH_EL)
SFX.append((T_X1, "scribble"))
for k, ch in enumerate("?!"):
    top_els.append(El(label(ch, "anton", 220, (INK if k else YEL), (YEL if k else INK), 26, 0), TCX - 70 + k * 150,
                      470, T_SURP + 0.05 + k * 0.1, (-8 if k else 7), "pop", T_SURP_END, 0.2, "tap"))
SFX.append((T_SURP, "hit"))
top_els.append(El(label("folha lisa?", "type", 58, INK, CREAM), TCX, 560, T_LISA, -3, t_out=T_CRACK - 0.1))
SFX.append((T_X2, "scribble"))
letters = []
for ch in "FLOCOS!":
    bg, fg, fk = STYLES[rng.integers(len(STYLES))]
    letters.append(label(ch, fk, int(rng.uniform(120, 150)), fg, bg, 14, 10))
x = TCX - sum(l.width - 40 for l in letters) / 2
for k, l in enumerate(letters):
    top_els.append(El(l, x + (l.width - 40) / 2, 400 + rng.uniform(-12, 12), T_BURST + 0.35 + k * 0.07,
                      rng.uniform(-9, 9), "pop", None, 0.2, "tap"))
    x += l.width - 40

# footsteps, flies, rolling, crack, burst
for k in range(6):
    SFX.append((0.15 + k * 0.27, "step"))
SFX.append((0.9, "buzz"))
SFX.append((T_DUMP, "slap"))
SFX.append((T_ROLL0, "roll"))
for k in range(4):
    SFX.append((T_CRACK + k * 0.08, "snap"))
SFX.append((T_BURST, "crackle"))
SFX.append((T_BURST, "whoosh"))

# flakes: launched from the sheet, land on the table (or fall off it)
flakes = []
for k in range(70):
    x0 = rng.uniform(TCX - 210, TCX + 210)
    vx, vy = rng.uniform(-330, 330), rng.uniform(-1050, -520)
    rest = TABLE_Y - rng.uniform(4, 40)
    g = 2000
    disc = vy * vy + 2 * g * (rest - (TABLE_Y - 14))
    t_land = (-vy + math.sqrt(max(disc, 0))) / g
    xl = x0 + vx * t_land
    on_table = TABLE_X0 + 10 < xl < TABLE_X1 - 10
    flakes.append(dict(x0=x0, vx=vx, vy=vy, rest=rest, tl=t_land if on_table else 9, img=FLAKES[k % 6],
                       spin=rng.uniform(-500, 500), s=rng.uniform(0.7, 1.15)))
for f_ in sorted(flakes, key=lambda f: f["tl"])[:14:2]:
    SFX.append((T_BURST + f_["tl"], "tap"))

EAT_TIMES = (14.0,)
for te in EAT_TIMES:
    SFX.append((te - 0.45, "whoosh"))
    SFX.append((te, "crunch"))
els = []
CRACKS = []
for k in range(7):
    x0 = rng.uniform(TCX - 180, TCX + 180)
    pts = [(x0, TABLE_Y - 14)]
    for j in range(4):
        pts.append((pts[-1][0] + rng.uniform(-40, 40), TABLE_Y - 14 + rng.uniform(-10, 10)))
    CRACKS.append(pts)


def lerp(a, b, u):
    u = min(max(u, 0), 1)
    return a + (b - a) * u


def pose_at(who, t):
    """Position + pose for each brother over the timeline."""
    p = dict(arm_l=8, arm_r=8, len_l=175, len_r=175, leg_l=0, leg_r=0, eyes="dot", mouth="line")
    if who == "john":
        x_end, delay = 250, 0.0
    else:
        x_end, delay = 1020, 0.25
    walk = (t - delay) / 1.5
    x = lerp(-260, x_end, ease_out(walk) if walk < 1 else 1)
    bob = 0
    if 0 <= walk < 1:
        ph = (t - delay) * 9
        p.update(leg_l=18 * math.sin(ph), leg_r=-18 * math.sin(ph), arm_l=8 - 14 * math.sin(ph), arm_r=8 + 14 * math.sin(ph))
        bob = -abs(math.sin(ph)) * 14
    if T_STALE - 0.1 <= t < T_DUMP:
        if who == "john":
            p.update(arm_r=232, len_r=150, mouth="yuck")  # hand on the nose
        else:
            p.update(arm_l=165, len_l=150, mouth="o")      # scratching the head
    if T_DUMP <= t < T_SURP:
        roll = (t - T_ROLL0) / (T_ROLL1 - T_ROLL0)
        if who == "john":
            x = lerp(250, 300, (t - T_DUMP) / 0.3)
    if T_SURP <= t < T_SURP_END:
        p.update(eyes="wide", mouth="o", arm_l=65, arm_r=65)
        bob = -18 * max(0, 1 - (t - T_SURP) / 0.2)
    if t >= T_BURST:
        u = t - T_BURST
        p.update(eyes="happy" if u > 1.2 else "wide", mouth="smile", arm_l=150 + 10 * math.sin(u * 8), arm_r=150 - 10 * math.sin(u * 8))
        bob = -abs(math.sin(u * 6)) * 26 * max(0, 1 - u / 2.5)
    return x, bob, p


def pin_x(t):
    if t < T_ROLL0:
        return TCX - 150
    if t < T_ROLL1:
        u = (t - T_ROLL0) / (T_ROLL1 - T_ROLL0)
        return TCX + math.sin(u * math.tau * 2.5 - math.pi / 2) * 170
    return TCX + 170


doll_cache = {}


def doll_img(who, p):
    key = (who,) + tuple(round(v) if isinstance(v, float) else v for v in p.values())
    if key not in doll_cache:
        doll_cache[key] = doll(who, **p)
    return doll_cache[key]


def reach(sx, sy, tx, ty, side):
    """Arm angle/length (PD convention) from shoulder to a target point."""
    dx, dy = (tx - sx) * side, ty - sy
    ang = math.degrees(math.atan2(dx, dy))
    return ang, min(math.hypot(dx, dy), 320)


def PUNCH(t):
    if T_SURP <= t < T_SURP_END:
        return 0.09 * ease_out((t - T_SURP) / 0.15)
    if T_SURP_END <= t < T_SURP_END + 0.3:
        return 0.09 * (1 - ease_out((t - T_SURP_END) / 0.3))
    return 0


def SHAKE(t):
    s = 0
    for t0, amp in ((T_STALE, 10), (T_SURP, 12), (T_BURST, 14)):
        if t0 <= t < t0 + 0.35:
            s = max(s, amp * (1 - (t - t0) / 0.35))
    return s

# ------------------------------------------------------------------ crow professor
CROW = crow_prof.build(CROW_SRC, 1.0)
CROW_SCALE = 1.08
crow_cache = {}


def crow_img(level):
    if level not in crow_cache:
        im = crow_prof.frame(CROW, level / 6)
        crow_cache[level] = im.resize((int(im.width * CROW_SCALE), int(im.height * CROW_SCALE)), Image.LANCZOS)
    return crow_cache[level]


# talking envelope: syllables with pauses where the scenes change
talk = np.zeros(N)
pauses = [(0, 0.2), (2.9, 3.3), (7.25, 7.5), (8.8, 9.2), (13.2, DUR)]
tt = 0.25
while tt < DUR:
    d_ = rng.uniform(0.11, 0.2)
    amp = rng.uniform(0.35, 1.0)
    i0, i1 = int(tt * FPS), int((tt + d_) * FPS)
    for i in range(i0, min(i1 + 1, N)):
        ph = (i / FPS - tt) / d_
        talk[i] = max(talk[i], amp * math.sin(math.pi * min(max(ph, 0), 1)))
    tt += d_ + rng.uniform(0.02, 0.08)
for a, b in pauses:
    talk[int(a * FPS):int(b * FPS)] = 0
SFX.append((0.0, "whoosh"))
# eating: a kernel flies into the beak, the beak snaps shut and chews
for te in EAT_TIMES:
    for i in range(N):
        u = i / FPS - te
        if -0.35 <= u < 0:
            talk[i] = 1.0 * ease_out((u + 0.35) / 0.2)
        elif 0 <= u < 0.6:
            talk[i] = [0.0, 0.0, 0.45, 0.45, 0.0, 0.0, 0.4, 0.4, 0.0, 0.0, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0][int(u * FPS)]
crumbs = [dict(te=te, vx=rng.uniform(-80, 60), vy=rng.uniform(-60, 40), r=rng.uniform(2.5, 5)) for te in EAT_TIMES for _ in range(10)]


def beak_mouth(t):
    k = ease_back(t / 0.4)
    img_w = int(CROW["size"][0] * CROW_SCALE)
    img_h = int(CROW["size"][1] * CROW_SCALE)
    x = OX + W - img_w + 30 + (1 - k) * 900
    y = OY + H - img_h + 60 + math.sin(t * 2.1) * 6
    return x + 70 * CROW_SCALE, y + 238 * CROW_SCALE


def draw_eating(canvas, t):
    d = ImageDraw.Draw(canvas)
    for te in EAT_TIMES:
        u = t - te
        if -0.45 <= u < 0:
            mx, my = beak_mouth(t)
            p = ease_out((u + 0.45) / 0.45)
            sx, sy = mx - 900, my - 260
            x_ = sx + (mx - sx) * p
            y_ = sy + (my - sy) * p - math.sin(p * math.pi) * 120
            im = KERNEL.rotate(u * 600, resample=Image.BILINEAR, expand=True)
            canvas.alpha_composite(im, (int(x_ - im.width / 2), int(y_ - im.height / 2)))
    for c in crumbs:
        u = t - c["te"]
        if 0 < u < 0.9:
            mx, my = beak_mouth(c["te"])
            x_ = mx + c["vx"] * u
            y_ = my + 10 + c["vy"] * u + 900 * u * u
            d.ellipse((x_ - c["r"], y_ - c["r"], x_ + c["r"], y_ + c["r"]), fill=(250, 210, 70, 255))


def draw_crow(canvas, i, t):
    k = ease_back(t / 0.4)
    img = crow_img(int(round(talk[i] * 6)))
    bob = math.sin(t * 7.0) * 1.2 * (talk[i] > 0.05)
    img = img.rotate(bob, resample=Image.BICUBIC, center=(img.width * 0.6, img.height))
    x = OX + W - img.width + 30 + (1 - k) * 900
    y = OY + H - img.height + 60 + math.sin(t * 2.1) * 6
    canvas.alpha_composite(img, (int(x), int(y)))


# ------------------------------------------------------------------ render
def fmt(n):
    return f"{n:,}".replace(",", ".")


frames = []
for i in range(N):
    t = i / FPS
    canvas = BG.copy()
    for e in els:
        e.draw(canvas, t)
    # ---- stage: table, pot / dough, rolling pin, brothers, flakes
    canvas.alpha_composite(TABLE, (int(OX + TABLE_X0 - 20 - 30), int(OY + TABLE_Y - 30)))
    if t < T_DUMP:
        pk = ease_back((t - 0.6) / 0.3) if t > 0.6 else 0
        if pk > 0:
            pim = POT if pk >= 0.999 else POT.resize((max(1, int(POT.width * pk)), max(1, int(POT.height * pk))))
            canvas.alpha_composite(pim, (int(OX + TCX - pim.width / 2), int(OY + TABLE_Y - pim.height + 30)))
        if t > T_STALE - 0.4:  # stink lines + flies
            d = ImageDraw.Draw(canvas)
            for k in range(3):
                bx = OX + TCX - 60 + k * 60
                pts = [(bx + math.sin(j * 0.5 + t * 6 + k) * 12, OY + TABLE_Y - 150 - j * 9) for j in range(14)]
                d.line(pts, fill=(140, 200, 100, 255), width=6, joint="curve")
            for k in range(3):
                a = t * (5 + k) + k * 2
                fx = OX + TCX + math.cos(a) * (90 + 20 * k)
                fy = OY + TABLE_Y - 230 + math.sin(a * 1.7) * 40
                wing = 7 + 4 * math.sin(t * 60 + k)
                d.ellipse((fx - 9, fy - wing - 6, fx + 1, fy - 2), fill=(230, 240, 250, 220))
                d.ellipse((fx - 1, fy - wing - 6, fx + 9, fy - 2), fill=(230, 240, 250, 220))
                d.ellipse((fx - 6, fy - 5, fx + 6, fy + 5), fill=(20, 20, 24, 255))
    else:
        d = ImageDraw.Draw(canvas)
        roll = min(max((t - T_ROLL0) / (T_ROLL1 - T_ROLL0), 0), 1)
        w_ = lerp(260, 460, roll)
        h_ = lerp(70, 22, roll)
        drop = ease_back((t - T_DUMP) / 0.25)
        cy_ = OY + TABLE_Y - h_ / 2 - (1 - drop) * 200
        if t < T_BURST:
            d.rounded_rectangle((OX + TCX - w_ / 2 - 5, cy_ - h_ / 2 + 4, OX + TCX + w_ / 2 + 5, cy_ + h_ / 2 + 4),
                                int(h_ / 2), fill=(250, 246, 236, 255))
            d.rounded_rectangle((OX + TCX - w_ / 2, cy_ - h_ / 2, OX + TCX + w_ / 2, cy_ + h_ / 2), int(h_ / 2),
                                fill=(214, 186, 128, 255))
            for k in range(6 if roll < 0.6 else 0):
                bx = OX + TCX - w_ / 2 + 30 + k * (w_ - 60) / 5
                d.ellipse((bx - 18, cy_ - h_ / 2 - 6, bx + 18, cy_ - h_ / 2 + 14), fill=(214, 186, 128, 255))
            if t >= T_CRACK:  # cracks spreading through the sheet
                u = min(1, (t - T_CRACK) / 0.3)
                for c in CRACKS:
                    n = max(2, int(len(c) * u))
                    d.line([(OX + x_, OY + y_) for x_, y_ in c[:n]], fill=(120, 80, 40, 255), width=4)
        if T_ROLL0 - 0.3 <= t < T_SURP_END:  # rolling pin
            px = pin_x(t)
            lift = 0 if t >= T_ROLL0 else (1 - (t - T_ROLL0 + 0.3) / 0.3) * 120
            canvas.alpha_composite(PIN, (int(OX + px - PIN.width / 2), int(OY + TABLE_Y - h_ - 46 - lift)))
    for who in ("john", "will"):
        x, bob, p = pose_at(who, t)
        if T_ROLL0 - 0.3 <= t < T_SURP and T_DUMP <= t:  # both hold the rolling pin
            px = pin_x(t)
            hy_ = TABLE_Y - 40
            if who == "john":
                p["arm_r"], p["len_r"] = reach(x + 78, FEET_Y - (PD.CH - PD.HIP[1] - 0) - (PD.HIP[1] - PD.SHOULDER_Y) + 70, px - 150, hy_, 1)
            else:
                p["arm_l"], p["len_l"] = reach(x - 78, FEET_Y - (PD.CH - PD.HIP[1] - 0) - (PD.HIP[1] - PD.SHOULDER_Y) + 70, px + 150, hy_, -1)
        im = doll_img(who, p)
        canvas.alpha_composite(im, (int(OX + x - im.width / 2), int(OY + FEET_Y - im.height + 70 + bob)))
    if t >= T_BURST:
        for f_ in flakes:
            u = t - T_BURST
            if u < f_["tl"]:
                fx = f_["x0"] + f_["vx"] * u
                fy = TABLE_Y - 14 + f_["vy"] * u + 1000 * u * u
                rot = f_["spin"] * u
            else:
                fx = f_["x0"] + f_["vx"] * f_["tl"]
                fy = f_["rest"]
                rot = f_["spin"] * f_["tl"]
            if fy > H + 100:
                continue
            im = f_["img"].rotate(rot, resample=Image.BILINEAR, expand=True)
            if f_["s"] != 1:
                im = im.resize((int(im.width * f_["s"]), int(im.height * f_["s"])), Image.BILINEAR)
            canvas.alpha_composite(im, (int(OX + fx - im.width / 2), int(OY + fy - im.height / 2)))
    # ---- labels / stamps on top + red X scribbles
    for e in top_els:
        e.draw(canvas, t)
    for (t0, cx0, cy0, w0, h0, t_end) in ((T_X1, 640, 300, 110, 125, T_DUMP - 0.1), (T_X2, TCX, 560, 230, 60, T_CRACK - 0.1)):
        if t0 <= t < t_end + 0.3:
            dx = -((t - t_end) / 0.3) ** 2 * 2200 if t > t_end else 0
            d = ImageDraw.Draw(canvas)
            prog = (t - t0) / 0.45 * 2
            for k_, (a_, b_) in enumerate((((-1, -1), (1, 1)), ((1, -1), (-1, 1)))):
                f_ = min(max(prog - k_, 0), 1)
                if f_ > 0:
                    x0_, y0_ = OX + cx0 + a_[0] * w0 + dx, OY + cy0 + a_[1] * h0
                    x1_, y1_ = OX + cx0 + b_[0] * w0 + dx, OY + cy0 + b_[1] * h0
                    d.line((x0_, y0_, x0_ + (x1_ - x0_) * f_, y0_ + (y1_ - y0_) * f_), fill=(220, 30, 40, 255), width=24)
    draw_crow(canvas, i, t)
    draw_eating(canvas, t)
    # camera: slow push, kick on the stamp
    z = 1.0 + 0.045 * t / DUR + PUNCH(t)
    shake = SHAKE(t)
    cw, ch = PW / 1.08 / z * 1.0, PH / 1.08 / z
    cx = PW / 2 + math.sin(i * 2.7) * shake
    cy = PH / 2 + math.cos(i * 3.3) * shake
    fr = canvas.crop((int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2))).resize((W, H), Image.BILINEAR)
    a = (np.asarray(fr.convert("RGB"), np.int16) + GRAIN[i % 6][..., None]).clip(0, 255).astype(np.uint8)
    frames.append(a)

# ------------------------------------------------------------------ audio
SR = 44100
mix = np.zeros(int(DUR * SR) + SR)


def band(n, lo, hi):
    x = rng.normal(size=n)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    y = np.fft.irfft(X, n)
    return y / (np.abs(y).max() + 1e-9)


def env_exp(n, tau):
    return np.exp(-np.arange(n) / SR / tau)


def thump(n, f0, f1, tau):
    tt_ = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-tt_ / 0.04)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt_ / tau)


def snd(kind):
    if kind == "slap":
        n = int(0.16 * SR)
        return 0.55 * band(n, 700, 6500) * env_exp(n, 0.02) + 0.5 * thump(n, 140, 60, 0.035)
    if kind == "tap":
        n = int(0.06 * SR)
        return 0.38 * band(n, 1500, 8000) * env_exp(n, 0.008) + 0.12 * thump(n, 300, 180, 0.012)
    if kind == "whoosh":
        n = int(0.42 * SR)
        e = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
        lo, hi = band(n, 250, 1400), band(n, 1400, 6000)
        x = np.linspace(0, 1, n)
        return 0.45 * e * (lo * (1 - x) + hi * x)
    if kind == "rustle":
        n = int(0.5 * SR)
        c = np.abs(band(n, 5, 40)) ** 3
        return 0.4 * band(n, 2000, 9000) * c / (c.max() + 1e-9) * np.sin(np.pi * np.linspace(0, 1, n))
    if kind == "tape":
        n = int(0.22 * SR)
        c = (rng.random(n) > 0.6).astype(float)
        e = np.linspace(0.3, 1, n) ** 2
        e[-int(0.02 * SR):] *= np.linspace(1, 0, int(0.02 * SR))
        return 0.45 * band(n, 1200, 7000) * c * e
    if kind == "stamp":
        n = int(0.45 * SR)
        return 0.95 * thump(n, 110, 45, 0.09) + 0.5 * band(n, 200, 3000) * env_exp(n, 0.012)
    if kind == "key":
        n = int(0.05 * SR)
        return 0.3 * band(n, 2000, 9000) * env_exp(n, 0.006) + 0.15 * thump(n, 260, 160, 0.01)
    if kind == "scribble":
        n = int(0.55 * SR)
        tt_ = np.arange(n) / SR
        m = (0.5 + 0.5 * np.sin(2 * np.pi * 9 * tt_)) ** 2
        return 0.35 * band(n, 1500, 5500) * m * np.sin(np.pi * np.linspace(0, 1, n)) ** 0.5
    if kind == "tick":
        n = int(0.015 * SR)
        return 0.16 * np.sin(2 * np.pi * 2300 * np.arange(n) / SR) * env_exp(n, 0.003)
    if kind == "ding":
        n = int(0.8 * SR)
        tt_ = np.arange(n) / SR
        return 0.3 * (np.sin(2 * np.pi * 1320 * tt_) + 0.5 * np.sin(2 * np.pi * 1980 * tt_)) * env_exp(n, 0.18)
    if kind == "step":
        n = int(0.08 * SR)
        return 0.25 * thump(n, 120, 70, 0.02) + 0.1 * band(n, 300, 2000) * env_exp(n, 0.01)
    if kind == "buzz":
        n = int(2.2 * SR)
        tt_ = np.arange(n) / SR
        f = 210 + 25 * np.sin(2 * np.pi * 3.1 * tt_) + 15 * np.sin(2 * np.pi * 7.3 * tt_)
        saw = 2 * ((np.cumsum(f) / SR) % 1) - 1
        e = np.minimum(1, tt_ / 0.2) * np.minimum(1, (tt_[-1] - tt_) / 0.3)
        return 0.08 * saw * (0.6 + 0.4 * np.sin(2 * np.pi * 1.7 * tt_)) * e
    if kind == "roll":
        n = int(1.9 * SR)
        tt_ = np.arange(n) / SR
        speed = np.abs(np.cos(tt_ / 1.9 * 2 * np.pi * 2.5 - np.pi / 2))
        return 0.35 * band(n, 60, 500) * speed * np.minimum(1, tt_ / 0.1)
    if kind == "hit":
        n = int(0.9 * SR)
        return 0.9 * thump(n, 160, 50, 0.22) + 0.25 * band(n, 100, 1200) * env_exp(n, 0.05)
    if kind == "snap":
        n = int(0.05 * SR)
        return 0.45 * band(n, 1500, 9000) * env_exp(n, 0.004)
    if kind == "crackle":
        n = int(0.9 * SR)
        out = np.zeros(n)
        for _ in range(40):
            i0 = int(rng.uniform(0, 0.7) * SR)
            m = int(0.03 * SR)
            out[i0:i0 + m] += band(m, 1200, 8000) * env_exp(m, 0.005) * rng.uniform(0.3, 1)
        return 0.4 * out / (np.abs(out).max() + 1e-9)
    if kind == "crunch":
        n = int(0.55 * SR)
        out = np.zeros(n)
        for k, dt in enumerate((0.0, 0.05, 0.11, 0.2, 0.26, 0.37)):
            m = int(0.07 * SR)
            b = band(m, 900, 7000) * env_exp(m, 0.012) * (0.9 if k == 0 else 0.55)
            i0 = int(dt * SR)
            out[i0:i0 + m] += b[: n - i0]
        return 0.55 * out
    if kind == "strike":
        n = int(0.6 * SR)
        tt_ = np.arange(n) / SR
        scratch = band(n, 1500, 9000) * np.exp(-tt_ / 0.05) * (rng.random(n) > 0.35)
        ignite = band(n, 150, 1800) * np.clip(tt_ / 0.06, 0, 1) * np.exp(-tt_ / 0.25)
        return 0.45 * scratch + 0.55 * ignite
    raise ValueError(kind)


for t0, kind in SFX:
    s = snd(kind)
    i0 = int(t0 * SR)
    mix[i0:i0 + len(s)] += s[: len(mix) - i0]
mix = mix[: int(DUR * SR)]
mix = mix / (np.abs(mix).max() + 1e-9) * 0.7
pcm = (np.stack([mix, mix], 1) * 32767).astype(np.int16)
wav_path = OUT.rsplit(".", 1)[0] + "_sfx.wav"
with wave.open(wav_path, "wb") as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes(pcm.tobytes())

proc = subprocess.Popen(
    ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
     "-i", wav_path, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
     "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
for fr in frames:
    proc.stdin.write(fr.tobytes())
proc.stdin.close()
proc.wait()
print("ok", len(frames), "frames,", len(SFX), "sfx")
