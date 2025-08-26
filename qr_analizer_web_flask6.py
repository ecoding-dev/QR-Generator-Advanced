#!/usr/bin/env python3
"""
QR Visual Analyzer (full) — Solo versión 7 (45x45) y TODAS las máscaras 0..7

- Flask app que genera únicamente la versión 7 (45×45 módulos) para un texto y ECC dados.
- Para esa versión, renderiza las 8 máscaras posibles (0..7).
- Colorea zonas técnicas (finder, separator, timing, alignment, format, version, data-area).
- Muestra métricas por máscara: size, ecc, mask, quiet zone, dark modules, functional modules, data-area modules.

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

# --- Configuración de la versión objetivo ---
TARGET_VERSION = 7           # 7 → 45x45
TARGET_SIZE = 21 + 4*(TARGET_VERSION - 1)  # 45

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

TEMPLATE = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>QR Visual Analyzer — v{TARGET_VERSION} ({TARGET_SIZE}×{TARGET_SIZE}) + Masks 0..7</title>
  <style>
    body{{font-family:Inter, Arial, sans-serif; padding:18px; background:#fff}}
    .grid{{display:flex;flex-wrap:wrap;gap:12px}}
    .card{{width:270px;border:1px solid #ddd;padding:10px;border-radius:8px;background:#fff}}
    img{{display:block;margin:6px 0;border:1px solid #ccc}}
    .legend{{margin-top:18px}}
    .legend div{{margin:6px 0}}
    .sw{{display:inline-block;width:18px;height:12px;border:1px solid #aaa;margin-right:8px}}
    .metrics{{font-size:12px;color:#333}}
    .error{{color:#b00;font-weight:600}}
    input[type="text"]{{font-family:monospace}}
  </style>
</head>
<body>
  <h1>QR Visual Analyzer — Solo versión {TARGET_VERSION} ({TARGET_SIZE}×{TARGET_SIZE}), todas las máscaras</h1>

  <form method="post">
    Texto (raw): <input type="text" name="text" size="90" value="{{{{text|e}}}}">
    ECC:
    <select name="ecc">
      <option value="L" {{% if ecc=='L' %}}selected{{% endif %}}>L (7%)</option>
      <option value="M" {{% if ecc=='M' %}}selected{{% endif %}}>M (15%)</option>
      <option value="Q" {{% if ecc=='Q' %}}selected{{% endif %}}>Q (25%)</option>
      <option value="H" {{% if ecc=='H' %}}selected{{% endif %}}>H (30%)</option>
    </select>
    <button type="submit">Generar</button>
  </form>

  {{% if error %}}
    <p class="error">{{{{error}}}}</p>
  {{% endif %}}

  {{% if qrs %}}
    <p>Se generan <strong>únicamente</strong> símbolos de <strong>versión {TARGET_VERSION} ({TARGET_SIZE}×{TARGET_SIZE} módulos)</strong>, probando <strong>todas las máscaras (0..7)</strong> con el ECC seleccionado.</p>
    <div class="grid">
      {{% for info in qrs %}}
      <div class="card">
        <strong>v{{{{info.version}}}} </strong> — {{{{info.size}}}}×{{{{info.size}}}} px (mask={{{{info.mask}}}}) <br>
        <a href="data:image/png;base64,{{{{info.img_b64}}}}" target="_blank">
          <img src="data:image/png;base64,{{{{info.img_b64}}}}" width="240" alt="QR v{{{{info.version}}}} mask {{{{info.mask}}}}">
        </a>
        <div class="metrics">
          ECC: <strong>{{{{info.ecc}}}}</strong><br>
          Quiet zone (border): {{{{info.border}}}} modules<br>
          Dark modules: {{{{info.dark_modules}}}} / {{{{info.modules}}}}<br>
          Functional modules: {{{{info.functional_modules}}}}<br>
          Data-area modules (estimado): {{{{info.data_modules}}}}<br>
        </div>
      </div>
      {{% endfor %}}
    </div>

    <div class="legend">
      <h3>Leyenda</h3>
      <div><span class="sw" style="background:rgb(128,0,128)"></span> Finder pattern (3 esquinas)</div>
      <div><span class="sw" style="background:rgb(230,230,230);border:1px solid #ccc"></span> Separator (borde blanco alrededor del finder, visual)</div>
      <div><span class="sw" style="background:rgb(255,165,0)"></span> Timing pattern (row 6 & col 6)</div>
      <div><span class="sw" style="background:rgb(0,128,128)"></span> Alignment patterns (centros para versiones &ge; 2)</div>
      <div><span class="sw" style="background:rgb(255,0,0)"></span> Format bits (cerca de finders)</div>
      <div><span class="sw" style="background:rgb(180,0,0)"></span> Version bits (v&ge;7; <strong>en v7 aplica</strong>)</div>
      <div><span class="sw" style="background:rgb(35,35,35)"></span> Data area (incluye datos + ECC — estimado)</div>
    </div>

    <p style="font-size:12px;color:#444">
      Nota: separar exactamente qué módulos pertenecen a bloques ECC vs datos requiere mapear codewords → módulos. Aquí marcamos las zonas funcionales según la especificación y tratamos lo no-funcional como "data area".
    </p>
  {{% endif %}}
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
                    if r < r0 or r > r0+6 or c < c0 or c > c0+6:
                        sep[r][c] = True

    # Timing patterns: row 6 and column 6 (except inside finders)
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

    # Format information areas (approx): around the finder top-left & top-right + col/row 8
    for i in range(0, 9):
        if i < size:
            func[8][i] = True   # horizontal near top-left
            func[i][8] = True   # vertical near top-left
            func[8][size-1-i] = True  # near top-right

    # Version information for v>=7 (en v7 sí aplica)
    if version >= 7:
        for r in range(0,6):
            for c in range(size-11, size-8):
                func[r][c] = True
        for r in range(size-11, size-8):
            for c in range(0,6):
                func[r][c] = True

    return func, sep

def render_colored_png_from_matrix(matrix, version, ecc, mask, scale=6, border=4):
    rows = list(matrix)
    size = len(rows)
    func_mask, sep_mask = build_function_mask(size, version)

    img_px = (size + 2*border) * scale
    img = Image.new('RGB', (img_px, img_px), PALETTE['background'])
    draw = ImageDraw.Draw(img)

    dark_modules = 0

    # Precompute alignment centers once
    centers = compute_alignment_centers(version)
    finder_positions = [(0,0), (0,size-7), (size-7,0)]

    for r in range(size):
        for c in range(size):
            is_dark = bool(rows[r][c])
            if is_dark:
                dark_modules += 1

            x0 = (c + border) * scale
            y0 = (r + border) * scale
            x1 = x0 + scale - 1
            y1 = y0 + scale - 1

            if sep_mask[r][c] and not is_dark:
                draw.rectangle([x0, y0, x1, y1], fill=PALETTE['separator'])
                continue

            if not is_dark:
                continue

            if func_mask[r][c]:
                # Finder?
                in_finder = False
                for (r0,c0) in finder_positions:
                    if r0 <= r < r0+7 and c0 <= c < c0+7:
                        draw.rectangle([x0, y0, x1, y1], fill=PALETTE['finder'])
                        in_finder = True
                        break
                if in_finder:
                    continue
                # Alignment?
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
                # Timing?
                if (r == 6 or c == 6) and not ((r < 9 and c < 9) or (r < 9 and c >= size-8) or (r >= size-8 and c < 9)):
                    draw.rectangle([x0, y0, x1, y1], fill=PALETTE['timing'])
                    continue
                # Format (aprox)
                if (r == 8 or c == 8) or (r < 9 and c < 9) or (c >= size-8 and r < 9):
                    draw.rectangle([x0, y0, x1, y1], fill=PALETTE['format'])
                    continue
                # Version bits (en v7 aplica)
                if version >= 7 and ((r < 6 and c >= size-11) or (r >= size-11 and c < 6)):
                    draw.rectangle([x0, y0, x1, y1], fill=PALETTE['version'])
                    continue

            # Data area
            draw.rectangle([x0, y0, x1, y1], fill=PALETTE['data'])

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
        'border': 4
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    text = ""
    ecc = "H"
    qrs = []
    error = None

    variants = [
        # (etiqueta, kwargs de segno.make)
        ("BYTE no-ECI", dict(mode='byte', encoding='iso-8859-1', eci=False)),
        ("BYTE ECI-UTF8", dict(mode='byte', encoding='utf-8', eci=True)),
        # ("AUTO (optimizado)", dict())
    ]

    if request.method == 'POST':
        text = (request.form.get('text') or "").strip()
        ecc = request.form.get('ecc') or "H"
        if not text:
            error = "Debes ingresar el texto raw que quieres codificar."
        else:
            # Validar que el texto cabe en VERSIÓN 7 con el ECC seleccionado.
            try:
                _ = segno.make(
                    text, error=ecc, version=TARGET_VERSION, boost_error=False,
                    micro=False, mask=0, mode='byte', encoding='iso-8859-1', eci=False
                )
            except Exception:
                error = f"El texto no cabe en versión {TARGET_VERSION} ({TARGET_SIZE}×{TARGET_SIZE}) con el ECC seleccionado."
            else:
                for label, extra in variants:
                    for m in range(8):
                        try:
                            qr_v = segno.make(
                                text, error=ecc, version=TARGET_VERSION, boost_error=False,
                                micro=False, mask=m, **extra
                            )
                        except Exception:
                            continue
                        matrix = list(qr_v.matrix)
                        b64, metrics = render_colored_png_from_matrix(
                            matrix, qr_v.version, ecc, getattr(qr_v, 'mask', None)
                        )
                        qrs.append({
                            'version': qr_v.version,   # 7
                            'size': metrics['size'],   # 45
                            'img_b64': b64,
                            'ecc': f"{ecc} · {label}",
                            'mask': getattr(qr_v, 'mask', None),
                            'modules': metrics['modules'],
                            'dark_modules': metrics['dark_modules'],
                            'functional_modules': metrics['functional_modules'],
                            'data_modules': metrics['data_modules_est'],
                            'border': metrics['border']
                        })

                if not qrs:
                    error = f"No se pudo generar ninguna máscara para v{TARGET_VERSION} (caso inesperado)."

    return render_template_string(TEMPLATE, text=text, ecc=ecc, qrs=qrs, error=error)

if __name__ == "__main__":
    app.run(debug=True)
