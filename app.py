from flask import Flask, request, Response
from PIL import Image, ImageDraw, ImageFont
import requests as req
import re, io, os

app = Flask(__name__)

# ── Brand colours ───────────────────────────────────────────────
GREEN      = (57, 255, 20)    # #39FF14
DARK_GREEN = (10, 30, 10)     # #0a1e0a  (big faded bg number)
WHITE      = (255, 255, 255)
GRAY       = (136, 136, 136)  # body text
DIM        = (85,  85,  85)   # slide counter
SIZE       = 1080

# ── Font setup ──────────────────────────────────────────────────
FONT_DIR = '/tmp/fonts'
os.makedirs(FONT_DIR, exist_ok=True)

# Old browser UA tricks Google Fonts into serving legacy TTF format
LEGACY_UA = 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)'

FONT_SPECS = {
    'playfair_bold': 'Playfair+Display:700',
    'inter_regular': 'Inter:400',
    'inter_bold':    'Inter:700',
}

def download_fonts():
    for name, spec in FONT_SPECS.items():
        path = f'{FONT_DIR}/{name}.ttf'
        if os.path.exists(path):
            continue
        print(f'Downloading font: {name}...')
        try:
            # Google Fonts CSS v1 returns TTF URLs for old user agents
            css = req.get(
                f'https://fonts.googleapis.com/css?family={spec}',
                headers={'User-Agent': LEGACY_UA},
                timeout=15
            ).text
            ttf_urls = re.findall(r"url\(([^)]+\.ttf)\)", css)
            if ttf_urls:
                data = req.get(ttf_urls[0], timeout=15).content
                with open(path, 'wb') as f:
                    f.write(data)
                print(f'Done: {name}')
            else:
                print(f'WARNING: No TTF URL found for {name}')
        except Exception as e:
            print(f'WARNING: Could not download {name}: {e}')

download_fonts()

def fnt(name, size):
    """Load font with fallback to system DejaVu if download failed."""
    path = f'{FONT_DIR}/{name}.ttf'
    if os.path.exists(path):
        return ImageFont.truetype(path, size)
    # Fallback: DejaVu fonts (pre-installed on Render's Linux)
    for fb in [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/dejavu/DejaVuSans.ttf',
    ]:
        if os.path.exists(fb):
            return ImageFont.truetype(fb, size)
    return ImageFont.load_default()

# ── Drawing helpers ─────────────────────────────────────────────
def tw(d, text, font):
    return d.textbbox((0, 0), text, font=font)[2]

def wrap(d, text, font, max_w):
    words, lines, cur = text.split(), [], ''
    for w in words:
        test = (cur + ' ' + w).strip()
        if tw(d, test, font) <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines or ['']

def draw_colored(d, x, y, text, green_phrase, font):
    if not green_phrase or green_phrase.lower() not in text.lower():
        d.text((x, y), text, fill=WHITE, font=font)
        return
    i  = text.lower().find(green_phrase.lower())
    b  = text[:i]
    ph = text[i:i+len(green_phrase)]
    a  = text[i+len(green_phrase):]
    cx = x
    if b:  d.text((cx, y), b,  fill=WHITE,  font=font); cx += tw(d, b,  font)
    d.text((cx, y), ph, fill=GREEN, font=font);          cx += tw(d, ph, font)
    if a:  d.text((cx, y), a,  fill=WHITE,  font=font)

def brackets(d):
    M, A, T, S = 22, 45, 3, SIZE
    for pts in [
        [(M,M),(M+A,M)], [(M,M),(M,M+A)],
        [(S-M,M),(S-M-A,M)], [(S-M,M),(S-M,M+A)],
        [(M,S-M),(M+A,S-M)], [(M,S-M),(M,S-M-A)],
    ]:
        d.line(pts, fill=GREEN, width=T)

def bottom_bar(d, n, total, fi_br, fi_cnt):
    cnt = f'{str(n).zfill(2)} / {str(total).zfill(2)}'
    d.text((32, 1050), cnt, fill=DIM, font=fi_cnt)
    d.text((810, 1047), 'GP ', fill=WHITE, font=fi_br)
    d.text((810 + tw(d, 'GP ', fi_br), 1047), 'Systems', fill=GREEN, font=fi_br)

# ── Slide generator ─────────────────────────────────────────────
@app.route('/slide')
def slide():
    n     = int(request.args.get('n', 1))
    h     = request.args.get('h', '')
    g     = request.args.get('g', '')
    b     = request.args.get('b', '')
    s     = request.args.get('s', '')
    l     = request.args.get('l', '')
    total = int(request.args.get('total', 6))

    img = Image.new('RGB', (SIZE, SIZE), (0, 0, 0))
    d   = ImageDraw.Draw(img)

    fp_huge = fnt('playfair_bold', 250)
    fp_h1   = fnt('playfair_bold', 70)
    fp_h2   = fnt('playfair_bold', 60)
    fi_sm   = fnt('inter_bold',    14)
    fi_body = fnt('inter_regular', 23)
    fi_bold = fnt('inter_bold',    23)
    fi_br   = fnt('inter_bold',    20)
    fi_cnt  = fnt('inter_regular', 14)

    brackets(d)

    if n == 1:  # ── Hook ──
        lbl = 'G P   S Y S T E M S'
        d.text(((SIZE - tw(d, lbl, fi_sm)) // 2, 155), lbl, fill=GREEN, font=fi_sm)
        y = 290
        for line in wrap(d, h, fp_h1, 960):
            draw_colored(d, (SIZE - tw(d, line, fp_h1)) // 2, y, line, g, fp_h1)
            y += 92
        if s:
            y += 20
            for line in wrap(d, s, fi_body, 860):
                d.text(((SIZE - tw(d, line, fi_body)) // 2, y), line, fill=GRAY, font=fi_body)
                y += 38

    elif n < total:  # ── Content ──
        sn = str(n - 1).zfill(2)
        d.text((740, -10), sn, fill=DARK_GREEN, font=fp_huge)
        slide_label = l.upper() if l else f'S T E P   {sn}'
        d.text((60, 265), slide_label, fill=GREEN, font=fi_sm)
        y = 315
        for line in wrap(d, h, fp_h1, 860):
            draw_colored(d, 60, y, line, g, fp_h1)
            y += 90
        y += 10
        d.rectangle([(60, y), (105, y + 3)], fill=GREEN)
        y += 28
        if b:
            lines = wrap(d, b, fi_body, 960)
            for i, line in enumerate(lines):
                d.text((60, y), line, fill=WHITE if i == 0 else GRAY,
                       font=fi_bold if i == 0 else fi_body)
                y += 38

    else:  # ── CTA ──
        y = 380
        for line in wrap(d, h, fp_h2, 900):
            draw_colored(d, (SIZE - tw(d, line, fp_h2)) // 2, y, line, g, fp_h2)
            y += 80
        if s:
            y += 24
            for line in wrap(d, s, fi_body, 860):
                d.text(((SIZE - tw(d, line, fi_body)) // 2, y), line, fill=GRAY, font=fi_body)
                y += 36

    bottom_bar(d, n, total, fi_br, fi_cnt)

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return Response(buf.getvalue(), mimetype='image/png')

@app.route('/health')
def health():
    return 'OK', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
