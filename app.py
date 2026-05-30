from flask import Flask, request, Response
from PIL import Image, ImageDraw, ImageFont
import requests as req
import io, os

app = Flask(__name__)

# ── Brand colours ───────────────────────────────────────────────
GREEN      = (57, 255, 20)    # #39FF14
DARK_GREEN = (10, 30, 10)     # #0a1e0a  (big faded bg number)
WHITE      = (255, 255, 255)
GRAY       = (136, 136, 136)  # body text
DIM        = (85,  85,  85)   # slide counter
SIZE       = 1080

# ── Font setup (downloaded once on cold start) ──────────────────
FONT_DIR = '/tmp/fonts'
os.makedirs(FONT_DIR, exist_ok=True)

FONT_URLS = {
    'playfair_bold': 'https://github.com/google/fonts/raw/main/ofl/playfairdisplay/static/PlayfairDisplay-Bold.ttf',
    'inter_regular': 'https://github.com/google/fonts/raw/main/ofl/inter/static/Inter-Regular.ttf',
    'inter_bold':    'https://github.com/google/fonts/raw/main/ofl/inter/static/Inter-Bold.ttf',
}

def download_fonts():
    for name, url in FONT_URLS.items():
        path = f'{FONT_DIR}/{name}.ttf'
        if not os.path.exists(path):
            print(f'Downloading font: {name}...')
            r = req.get(url, timeout=20)
            r.raise_for_status()
            with open(path, 'wb') as f:
                f.write(r.content)
            print(f'Done: {name}')

download_fonts()

def fnt(name, size):
    return ImageFont.truetype(f'{FONT_DIR}/{name}.ttf', size)

# ── Drawing helpers ─────────────────────────────────────────────
def tw(d, text, font):
    """Text width in pixels."""
    return d.textbbox((0, 0), text, font=font)[2]

def wrap(d, text, font, max_w):
    """Word-wrap text to fit max_w pixels."""
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
    """Draw text with a keyword highlighted in green."""
    if not green_phrase or green_phrase.lower() not in text.lower():
        d.text((x, y), text, fill=WHITE, font=font)
        return
    i  = text.lower().find(green_phrase.lower())
    b  = text[:i]
    ph = text[i:i+len(green_phrase)]
    a  = text[i+len(green_phrase):]
    cx = x
    if b:  d.text((cx, y), b,  fill=WHITE,  font=font); cx += tw(d, b,  font)
    d.text((cx, y), ph, fill=GREEN, font=font); cx += tw(d, ph, font)
    if a:  d.text((cx, y), a,  fill=WHITE,  font=font)

def brackets(d):
    """Draw GP Systems corner brackets."""
    M, A, T = 22, 45, 3
    S = SIZE
    lines = [
        [(M, M), (M+A, M)], [(M, M), (M, M+A)],           # top-left
        [(S-M, M), (S-M-A, M)], [(S-M, M), (S-M, M+A)],   # top-right
        [(M, S-M), (M+A, S-M)], [(M, S-M), (M, S-M-A)],   # bottom-left
    ]
    for pts in lines:
        d.line(pts, fill=GREEN, width=T)

def bottom_bar(d, n, total, fi_br, fi_cnt):
    """Draw slide counter and GP Systems brand name."""
    cnt = f'{str(n).zfill(2)} / {str(total).zfill(2)}'
    d.text((32, 1050), cnt, fill=DIM, font=fi_cnt)
    d.text((810, 1047), 'GP ', fill=WHITE, font=fi_br)
    d.text((810 + tw(d, 'GP ', fi_br), 1047), 'Systems', fill=GREEN, font=fi_br)

# ── Slide generator ─────────────────────────────────────────────
@app.route('/slide')
def slide():
    n     = int(request.args.get('n', 1))
    h     = request.args.get('h', '')          # headline
    g     = request.args.get('g', '')          # green keyword
    b     = request.args.get('b', '')          # body text
    s     = request.args.get('s', '')          # subtext (hook / CTA)
    l     = request.args.get('l', '')          # custom slide label (e.g. "THE PROBLEM")
    total = int(request.args.get('total', 6))

    img = Image.new('RGB', (SIZE, SIZE), (0, 0, 0))
    d   = ImageDraw.Draw(img)

    # Load fonts
    fp_huge = fnt('playfair_bold', 250)
    fp_h1   = fnt('playfair_bold', 70)
    fp_h2   = fnt('playfair_bold', 60)
    fi_sm   = fnt('inter_bold',    14)
    fi_body = fnt('inter_regular', 23)
    fi_bold = fnt('inter_bold',    23)
    fi_br   = fnt('inter_bold',    20)
    fi_cnt  = fnt('inter_regular', 14)

    brackets(d)

    # ── Slide 1: Hook ──────────────────────────────────────────
    if n == 1:
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

    # ── Slides 2 to (total-1): Content ────────────────────────
    elif n < total:
        sn = str(n - 1).zfill(2)
        d.text((740, -10), sn, fill=DARK_GREEN, font=fp_huge)
        # Use custom label if provided, otherwise default to STEP format
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
                color = WHITE if i == 0 else GRAY
                font  = fi_bold if i == 0 else fi_body
                d.text((60, y), line, fill=color, font=font)
                y += 38

    # ── Slide 6: CTA ──────────────────────────────────────────
    else:
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

# ── Health check (used by n8n to wake the service) ──────────────
@app.route('/health')
def health():
    return 'OK', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
