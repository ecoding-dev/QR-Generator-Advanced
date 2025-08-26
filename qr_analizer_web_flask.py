#!/usr/bin/env python3
"""
QR Visual Analyzer (full)

- Flask app that generates QR versions (min_version..40) for a given text and ECC.
- Renders colored PNGs marking finder, separator, timing, alignment, format bits,
  version bits and data-area (data + ECC).
- Shows metrics per version: size, ecc, mask, quiet zone, dark modules, functional modules, data-area modules.

Dependencias:
    pip install flask segno pillow numpy

Ejecutar:
    python qr_visual_analyzer_full.py
Abrir:
    http://127.0.0.1:5000/
"""

from flask import Flask, render_template_string, request
from io import BytesIO
import base64
from PIL import Image, ImageDraw
import segno
import math

app = Flask(__name__)

# Colores (RGB tuples)
PALETTE = {
    'background': (255, 255, 255),
    'finder': (128, 0, 128),       # purple
    'separator': (230, 230, 230),  # light gray (visual)
    'timing': (255, 165, 0),       # orange
    'alignment': (0, 128, 128),    # teal
    'format': (255, 0, 0),         # red
    'version': (180, 0, 0),        # dark red
    'data': (35, 35, 35),          # dark charcoal
    'quiet_zone': (255, 255, 255)  # white
}

TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>QR Visual Analyzer — Full</title>
  <style>
    body{font-family:Inter, Arial, sans-serif; padding:18px; background:#fff}
    .grid{display:flex;flex-wrap:wrap;gap:12px}
    .card{width:270px;border:1px solid #ddd;padding:10px;border-radius:8px;background:#fff}
    img{display:block;margin:6px 0;border:1px solid #ccc}
    .legend{margin-top:18px}
    .legend div{margin:6px 0}
    .sw{display:inline-block;width:18px;height:12px;border:1px solid #aaa;margin-right:8px}
    .metrics{font-size:12px;color:#333}
    .error{color:#b00;font-weight:600}
    input[type="text"]{font-family:monospace}
  </style>
</head>
<body>
  <h1>QR Visual Analyzer — Full (zonas técnicas)</h1>

  <form method="post">
    Texto (raw): <input type="text" name="text" size="90" value="{{text|e}}">
    ECC:
    <select name="ecc">
      <option value="L" {% if ecc=='L' %}selected{% endif %}>L (7%)</option>
      <option value="M" {% if ecc=='M' %}selected{% endif %}>M (15%)</option>
      <option value="Q" {% if ecc=='Q' %}selected{% endif %}>Q (25%)</option>
      <option value="H" {% if ecc=='H' %}selected{% endif %}>H (30%)</option>
    </select>
    <button type="submit">Generar</button>
  </form>

  {% if error %}
    <p class="error">{{error}}</p>
  {% endif %}

  {% if qrs %}
    <p>Se generan versiones desde la versión mínima ({% raw %}min_version{% endraw %}) encontrada hasta la 40. Click en la imagen para abrir en nueva pestaña.</p>
    <div class="grid">
      {% for info in qrs %}
      <div class="card">
        <strong>v{{info.version}}</strong> — {{info.size}}×{{info.size}} px (mask={{info.mask}}) <br>
        <a href="data:image/png;base64,{{info.img_b64}}" target="_blank">
          <img src="data:image/png;base64,{{info.img_b64}}" width="240" alt="QR v{{info.version}}">
        </a>
        <div class="metrics">
          ECC: <strong>{{info.ecc}}</strong><br>
          Quiet zone (border): {{info.border}} modules<br>
          Dark modules: {{info.dark_modules}} / {{info.modules}}<br>
          Functional modules: {{info.functional_modules}}<br>
          Data-area modules (estimado): {{info.data_modules}}<br>
        </div>
      </div>
      {% endfor %}
    </div>

    <div class="legend">
      <h3>Leyenda</h3>
      <div><span class="sw" style="background:rgb(128,0,128)"></span> Finder pattern (3 esquinas)</div>
      <div><span class="sw" style="background:rgb(230,230,230);border:1px solid #ccc"></span> Separator (borde blanco alrededor del finder, aquí visualizado)</div>
      <div><span class="sw" style="background:rgb(255,165,0)"></span> Timing pattern (row 6 & col 6)</div>
      <div><span class="sw" style="background:rgb(0,128,128)"></span> Alignment patterns (centros para versiones >= 2)</div>
      <div><span class="sw" style="background:rgb(255,0,0)"></span> Format bits (cerca de finders)</div>
      <div><span class="sw" style="background:rgb(180,0,0)"></span> Version bits (si v>=7)</div>
      <div><span class="sw" style="background:rgb(35,35,35)"></span> Data area (incluye datos + ECC — estimado)</div>
    </div>

    <p style="font-size:12px;color:#444">
      Nota: separar exactamente qué módulos pertenecen a los bloques ECC vs datos requiere mapear codewords -> módulos. Aquí marcamos las zonas funcionales según la especificación y tratamos lo no-funcional como "data area".
    </p>
  {% endif %}
</body>
</html>
"""

# Helpers to compute alignment centers (standard algorithm)
def compute_alignment_centers(version):
    if version == 1:
        return []
    size = 21 + (version - 1) * 4
    num = version // 7 + 2
    first = 6
    last = size - 7
    if num == 2:
        return [first, last]
    step = (last - first) / (num - 1)
    centers = [int(round(first + i * step)) for i in range(num)]
    return centers

def build_function_mask(size, version):
    """
    Build a boolean mask (size x size) marking functional modules:
    finder, separators (not marked as dark but considered functional),
    timing, alignment, format, version areas.
    Return two masks: func_mask (True if functional), sep_mask (True if separator white area).
    """
    func = [[False]*size for _ in range(size)]
    sep = [[False]*size for _ in range(size)]

    # Finder positions (7x7) top-left, top-right, bottom-left
    finder_positions = [(0,0), (0,size-7), (size-7,0)]
    for (r0,c0) in finder_positions:
        for r in range(r0, r0+7):
            for c in range(c0, c0+7):
                if 0 <= r < size and 0 <= c < size:
                    func[r][c] = True
        # Separator: 1-module frame around finder -> mark as sep (visual aid)
        for r in range(r0-1, r0+8):
            for c in range(c0-1, c0+8):
                if 0 <= r < size and 0 <= c < size:
                    # If it's outside the 7x7 finder core
                    if r < r0 or r > r0+6 or c < c0 or c > c0+6:
                        sep[r][c] = True

    # Timing patterns: row 6 and column 6 (except inside finders)
    for i in range(size):
        if not ((i < 9 and 6 < 9) or (i >= size-9 and 6 < 9)):
            pass
    for i in range(8, size-8):
        func[6][i] = True
        func[i][6] = True

    # Alignment patterns (5x5 centered)
    centers = compute_alignment_centers(version)
    for cy in centers:
        for cx in centers:
            # skip overlap with finders
            if (cy <= 6 and cx <= 6) or (cy <= 6 and cx >= size-7) or (cy >= size-7 and cx <= 6):
                continue
            for r in range(cy-2, cy+3):
                for c in range(cx-2, cx+3):
                    if 0 <= r < size and 0 <= c < size:
                        func[r][c] = True

    # Format information areas (approx): around the finder top-left and top-right
    for i in range(0, 9):
        if i < size:
            func[8][i] = True  # horizontal near top-left
            func[i][8] = True  # vertical near top-left
            func[8][size-1-i] = True  # near top-right

    # Version information for v>=7: 6x3 areas (two places)
    if version >= 7:
        for r in range(0,6):
            for c in range(size-11, size-8):
                if 0 <= r < size and 0 <= c < size:
                    func[r][c] = True
        for r in range(size-11, size-8):
            for c in range(0,6):
                if 0 <= r < size and 0 <= c < size:
                    func[r][c] = True

    return func, sep

def render_colored_png_from_matrix(matrix, version, ecc, mask, scale=6, border=4):
    """
    matrix: iterable of rows (True=dark, False=light) from segno.symbol.matrix
    version: integer
    ecc: string 'L','M','Q','H'
    mask: integer or None
    """
    rows = list(matrix)
    size = len(rows)
    func_mask, sep_mask = build_function_mask(size, version)

    # image size with border (quiet zone)
    img_px = (size + 2*border) * scale
    img = Image.new('RGB', (img_px, img_px), PALETTE['background'])
    draw = ImageDraw.Draw(img)

    dark_modules = 0
    functional_modules = 0

    for r in range(size):
        for c in range(size):
            is_dark = bool(rows[r][c])
            if is_dark:
                dark_modules += 1

            # compute pixel coords
            x0 = (c + border) * scale
            y0 = (r + border) * scale
            x1 = x0 + scale - 1
            y1 = y0 + scale - 1

            # if separator (visual): draw light gray square to indicate separator area (only if light)
            if sep_mask[r][c] and not is_dark:
                draw.rectangle([x0, y0, x1, y1], fill=PALETTE['separator'])
                continue

            if not is_dark:
                # leave background (quiet zone or light module)
                continue

            # if functional
            if func_mask[r][c]:
                functional_modules += 1
                # determine which functional area to color (priority)
                # Finder area
                in_finder = False
                finder_positions = [(0,0), (0,size-7), (size-7,0)]
                for (r0,c0) in finder_positions:
                    if r0 <= r < r0+7 and c0 <= c < c0+7:
                        draw.rectangle([x0, y0, x1, y1], fill=PALETTE['finder'])
                        in_finder = True
                        break
                if in_finder:
                    continue
                # alignment
                centers = compute_alignment_centers(version)
                aligned = False
                for cy in centers:
                    for cx in centers:
                        if cy-2 <= r <= cy+2 and cx-2 <= c <= cx+2:
                            draw.rectangle([x0, y0, x1, y1], fill=PALETTE['alignment'])
                            aligned = True
                            break
                    if aligned: break
                if aligned:
                    continue
                # timing
                if (r == 6 or c == 6) and not ((r < 9 and c < 9) or (r < 9 and c >= size-8) or (r >= size-8 and c < 9)):
                    draw.rectangle([x0, y0, x1, y1], fill=PALETTE['timing'])
                    continue
                # format bits approx
                if (r == 8 or c == 8) or (r < 9 and c < 9) or (c >= size-8 and r < 9):
                    draw.rectangle([x0, y0, x1, y1], fill=PALETTE['format'])
                    continue
                # version bits
                if version >= 7 and ((r < 6 and c >= size-11) or (r >= size-11 and c < 6)):
                    draw.rectangle([x0, y0, x1, y1], fill=PALETTE['version'])
                    continue

            # default: data area (dark)
            draw.rectangle([x0, y0, x1, y1], fill=PALETTE['data'])

    # border quiet zone visualization: (we don't color quiet zone modules, border param is in modules)
    # return PNG bytes
    buf = BytesIO()
    img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode('ascii')

    total_modules = size * size
    functional_count = sum(sum(1 for c in row if c) for row in func_mask)
    data_modules_est = total_modules - functional_count

    return b64, {
        'size': size,
        'modules': total_modules,
        'dark_modules': dark_modules,
        'functional_modules': functional_count,
        'data_modules_est': data_modules_est,
        'border': border
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    text = ""
    ecc = "H"
    qrs = []
    error = None

    if request.method == 'POST':
        text = (request.form.get('text') or "").strip()
        ecc = request.form.get('ecc') or "H"
        if not text:
            error = "Debes ingresar el texto raw que quieres codificar."
        else:
            # try create minimal segno QR to discover min_version (segno chooses min version by default)
            try:
                qr_min = segno.make(text, error=ecc, boost_error=False, micro=False, mask=3)
            except Exception as ex:
                error = "El texto no cabe en ninguna versión con el ECC seleccionado."
                qr_min = None

            if qr_min:
                min_ver = qr_min.version
                # generate each version from min_ver..40 (stop when segno refuses)
                for v in range(min_ver, 41):
                    try:
                        qr_v = segno.make(text, error=ecc, version=v, boost_error=False, micro=False, mask=3)
                    except Exception:
                        # can't encode at this version (segno raises), break loop
                        break
                    # segno's matrix: iter(rows) with booleans; top-left is row 0 col 0
                    matrix = list(qr_v.matrix)  # rows
                    b64, metrics = render_colored_png_from_matrix(matrix, qr_v.version, ecc, getattr(qr_v, 'mask', None))
                    qrs.append({
                        'version': qr_v.version,
                        'size': metrics['size'],
                        'img_b64': b64,
                        'ecc': ecc,
                        'mask': getattr(qr_v, 'mask', None),
                        'modules': metrics['modules'],
                        'dark_modules': metrics['dark_modules'],
                        'functional_modules': metrics['functional_modules'],
                        'data_modules': metrics['data_modules_est'],
                        'border': metrics['border']
                    })
                if not qrs:
                    error = "El texto no cabe en ninguna versión con el ECC seleccionado."
    return render_template_string(TEMPLATE, text=text, ecc=ecc, qrs=qrs, error=error)


if __name__ == "__main__":
    app.run(debug=True)
