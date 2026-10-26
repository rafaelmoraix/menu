import math, random, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

random.seed(7)
SRC = sys.argv[1]
OUT = sys.argv[2]
FONT = sys.argv[3]
W, H = 2560, 1440
SAFE = (507, 508, 2053, 931)  # YouTube safe area (all devices)
S = 2  # supersample

BG = (38, 92, 74)
GREENS = [(46, 120, 70), (58, 140, 78), (35, 104, 62), (72, 160, 88), (30, 86, 60)]
PINK = (248, 150, 196)
PINK_D = (232, 70, 150)
YEL = (240, 228, 50)
BLACK = (20, 10, 24)

img = Image.new("RGB", (W * S, H * S), BG)
d = ImageDraw.Draw(img)


def stroke(pts, color, width):
    pts = [(x * S, y * S) for x, y in pts]
    d.line(pts, fill=color, width=int(width * S), joint="curve")
    r = width * S / 2
    for x, y in (pts[0], pts[-1]):
        d.ellipse((x - r, y - r, x + r, y + r), fill=color)


def grass(cx, cy, size, color):
    # V / Y shaped tuft like the painted grass in the art
    ang = random.uniform(-0.5, 0.5)
    w = size * random.uniform(0.16, 0.22)
    for spread in (-0.55, 0.0, 0.55) if random.random() < 0.5 else (-0.45, 0.45):
        a = ang + spread + random.uniform(-0.12, 0.12)
        L = size * random.uniform(0.75, 1.1)
        mid = (cx + math.sin(a) * L * 0.5 + random.uniform(-6, 6), cy - math.cos(a) * L * 0.5)
        tip = (cx + math.sin(a) * L, cy - math.cos(a) * L)
        stroke([(cx, cy), mid, tip], color, w)


def flower(cx, cy, r):
    rot = random.uniform(0, math.tau)
    for i in range(5):
        a = rot + i * math.tau / 5
        px, py = cx + math.cos(a) * r * 0.62, cy + math.sin(a) * r * 0.62
        pr = r * 0.48
        d.ellipse(((px - pr) * S, (py - pr) * S, (px + pr) * S, (py + pr) * S), fill=PINK)
    for i in range(5):
        a = rot + i * math.tau / 5 + 0.3
        px, py = cx + math.cos(a) * r * 0.42, cy + math.sin(a) * r * 0.42
        q = r * 0.13
        d.rectangle(((px - q) * S, (py - q) * S, (px + q) * S, (py + q) * S), fill=PINK_D)
    cr = r * 0.3
    d.ellipse(((cx - cr) * S, (cy - cr) * S, (cx + cr) * S, (cy + cr) * S), fill=YEL)


# background grass, several layers
for layer in range(2):
    for _ in range(150):
        grass(random.uniform(-60, W + 60), random.uniform(-40, H + 120),
              random.uniform(90, 170), random.choice(GREENS))

# flowers, kept out of the text area so they don't fight the name
text_zone = (1000, 560, 2060, 880)
placed = []
tries = 0
while len(placed) < 26 and tries < 4000:
    tries += 1
    x, y = random.uniform(40, W - 40), random.uniform(40, H - 40)
    r = random.uniform(38, 62)
    if text_zone[0] - 40 < x < text_zone[2] + 40 and text_zone[1] - 40 < y < text_zone[3] + 40:
        continue
    if 520 < x < 1000 and 480 < y < 960:
        continue
    if any(math.hypot(x - px, y - py) < 230 for px, py in placed):
        continue
    placed.append((x, y))
    flower(x, y, r)

# a few foreground tufts on top of flowers for depth
for _ in range(60):
    x, y = random.uniform(0, W), random.uniform(0, H)
    if SAFE[0] - 20 < x < SAFE[2] + 20 and SAFE[1] - 40 < y < SAFE[3] + 80:
        continue
    grass(x, y, random.uniform(110, 180), random.choice(GREENS[:4]))

img = img.resize((W, H), Image.LANCZOS)

# darken the band behind the safe area slightly so the content pops
shade = Image.new("L", (W, H), 0)
sd = ImageDraw.Draw(shade)
sd.rounded_rectangle((SAFE[0] - 120, SAFE[1] - 30, SAFE[2] + 120, SAFE[3] + 30), 120, fill=90)
shade = shade.filter(ImageFilter.GaussianBlur(70))
img = Image.composite(Image.new("RGB", (W, H), (14, 40, 34)), img, shade)

# --- character "sticker" -------------------------------------------------
art = Image.open(SRC).convert("RGB")
crop = art.crop((40, 40, 1000, 1000))  # framed on the face
SZ = 360
crop = crop.resize((SZ, SZ), Image.LANCZOS)
B = 14
card = Image.new("RGBA", (SZ + 2 * B, SZ + 2 * B), (0, 0, 0, 0))
cd = ImageDraw.Draw(card)
cd.rounded_rectangle((0, 0, SZ + 2 * B - 1, SZ + 2 * B - 1), 48, fill=BLACK + (255,))
mask = Image.new("L", (SZ, SZ), 0)
ImageDraw.Draw(mask).rounded_rectangle((0, 0, SZ - 1, SZ - 1), 36, fill=255)
card.paste(crop, (B, B), mask)
card = card.rotate(-5, resample=Image.BICUBIC, expand=True)

cx, cy = 790, (SAFE[1] + SAFE[3]) // 2
shadow = Image.new("RGBA", card.size, (0, 0, 0, 0))
shadow.putalpha(card.getchannel("A").point(lambda a: int(a * 0.85)))
sh_col = Image.new("RGBA", card.size, (91, 42, 134, 255))
sh_col.putalpha(shadow.getchannel("A"))
img = img.convert("RGBA")
img.alpha_composite(sh_col, (cx - card.width // 2 + 16, cy - card.height // 2 + 18))
img.alpha_composite(card, (cx - card.width // 2, cy - card.height // 2))

# little flower pinned on the sticker corner
d = ImageDraw.Draw(img)
def flower_direct(cx, cy, r):
    rot = 0.4
    for i in range(5):
        a = rot + i * math.tau / 5
        px, py = cx + math.cos(a) * r * 0.62, cy + math.sin(a) * r * 0.62
        pr = r * 0.5
        d.ellipse((px - pr - 6, py - pr - 6, px + pr + 6, py + pr + 6), fill=BLACK)
    for i in range(5):
        a = rot + i * math.tau / 5
        px, py = cx + math.cos(a) * r * 0.62, cy + math.sin(a) * r * 0.62
        pr = r * 0.5
        d.ellipse((px - pr, py - pr, px + pr, py + pr), fill=PINK)
    cr = r * 0.32
    d.ellipse((cx - cr, cy - cr, cx + cr, cy + cr), fill=YEL, outline=BLACK, width=5)
flower_direct(cx + 175, cy - 170, 54)

# --- name ----------------------------------------------------------------
name = "lessterr"
font = ImageFont.truetype(FONT, 290)
tl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
td = ImageDraw.Draw(tl)
bbox = td.textbbox((0, 0), name, font=font, stroke_width=18)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
tx = 1525 - tw // 2 - bbox[0]
ty = cy - th // 2 - bbox[1] - 10

# purple drop shadow, black outline, pink fill, magenta lower shading
td.text((tx + 14, ty + 16), name, font=font, fill=(91, 42, 134), stroke_width=18, stroke_fill=(91, 42, 134))
td.text((tx, ty), name, font=font, fill=PINK, stroke_width=18, stroke_fill=BLACK)
fill_mask = Image.new("L", (W, H), 0)
ImageDraw.Draw(fill_mask).text((tx, ty), name, font=font, fill=255)
lower = Image.new("L", (W, H), 0)
ld = ImageDraw.Draw(lower)
ld.rectangle((0, ty + bbox[1] + int(th * 0.62), W, H), fill=255)
from PIL import ImageChops
band = ImageChops.multiply(fill_mask, lower)
mag = Image.new("RGBA", (W, H), (226, 74, 160, 255))
mag.putalpha(band)
tl.alpha_composite(mag)
# glossy highlight streak
hl = Image.new("L", (W, H), 0)
ImageDraw.Draw(hl).rectangle((0, ty + bbox[1] + int(th * 0.18), W, ty + bbox[1] + int(th * 0.26)), fill=150)
hl = ImageChops.multiply(fill_mask.filter(ImageFilter.MinFilter(9)), hl)
white = Image.new("RGBA", (W, H), (255, 220, 238, 255))
white.putalpha(hl)
tl.alpha_composite(white)
img.alpha_composite(tl)

img = img.convert("RGB")
img.save(OUT, quality=95)

# preview with safe-area guides
g = img.copy()
gd = ImageDraw.Draw(g)
gd.rectangle(SAFE, outline=(255, 255, 255), width=4)
gd.rectangle((0, SAFE[1], W - 1, SAFE[3]), outline=(255, 255, 0), width=3)
g.save(OUT.replace(".png", "_guias.png"))
