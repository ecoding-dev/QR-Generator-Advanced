#!/usr/bin/env python3
"""
QR Visual Analyzer (full + image analysis)

- Flask app con dos funciones:
  1. Genera QR en todas las versiones (1..40) a partir de un texto + ECC.
     Colorea zonas técnicas (finder, timing, alignment, etc).
  2. Analiza un QR subido como imagen (PNG/JPG con o sin branding/logo).
     Muestra contenido, versión detectada, ECC, tamaño y métricas posibles.

Dependencias:
    pip install flask segno pillow numpy pyzbar opencv-python

Ejecutar:
    python qr_visual_analyzer_full.py
Abrir:
    http://127.0.0.1:5000/
"""

from flask import Flask, render_template_string, request
from io import BytesIO
import base64, math
from PIL import Image, ImageDraw
import segno
from pyzbar.pyzbar import decode
import numpy as np

app = Flask(__name__)

# Colores (RGB tuples)
PALETTE = {
    'background': (255, 255, 255),
    'finder': (128, 0, 128),       # purple
    'separator': (230, 230, 230),  # light gray
    'timing': (255, 165, 0),       # orange
    'alignment': (0, 128, 128),    # teal
    'format': (255, 0, 0),         # red
    'version': (180, 0, 0),        # dark red
    'data': (35, 35, 35),          # dark charcoal
    'quiet_zone': (255, 255, 255)  # white
}

# ========= HTML =========
TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>QR Visual Analyzer</title>
  <style>
    body{font-family:Inter, Arial, sans-serif; padding:18px; background:#fff}
    .grid{display:flex;flex-wrap:wrap;gap:12px}
    .card{width:270px;border:1px solid #ddd;padding:10px;border-radius:8px;background:#fff}
    img{display:block;margin:6px 0;border:1px solid #ccc;max-width:100%}
    .legend{margin-top:18px}
    .legend div{margin:6px 0}
    .sw{display:inline-block;width:18px;height:12px;border:1px solid #aaa;margin-right:8px}
    .metrics{font-size:12px;color:#333}
    .error{color:#b00;font-weight:600}
    input[type="text"]{font-family:monospace}
  </style>
</head>
<body>
  <h1>QR Visual Analyzer</h1>

  <h2>1. Generar QR desde texto</h2>
  <form method="post" enctype="multipart/form-data">
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
    <div class="grid">
      {% for info in qrs %}
      <div class="card">
        <strong>v{{info.version}}</strong> — {{info.size}}×{{info.size}} px (mask={{info.mask}}) <br>
        <a href="data:image/png;base64,{{info.img_b64}}" target="_blank">
          <img src="data:image/png;base64,{{info.img_b64}}" alt="QR v{{info.version}}">
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
      <h3>Leyenda colores</h3>
      <div><span class="sw" style="background:rgb(128,0,128)"></span> Finder pattern</div>
      <div><span class="sw" style="background:rgb(230,230,230);border:1px solid #ccc"></span> Separator</div>
      <div><span class="sw" style="background:rgb(255,165,0)"></span> Timing pattern</div>
      <div><span class="sw" style="background:rgb(0,128,128)"></span> Alignment</div>
      <div><span class="sw" style="background:rgb(255,0,0)"></span> Format bits</div>
      <div><span class="sw" style="background:rgb(180,0,0)"></span> Version bits</div>
      <div><span class="sw" style="background:rgb(35,35,35)"></span> Data/ECC area</div>
    </div>
  {% endif %}

  <hr>

  <h2>2. Analizar QR desde imagen</h2>
  <form method="post" action="/analyze" enctype="multipart/form-data">
    <input type="file" name="file" accept="image/*">
    <button type="submit">Analizar</button>
  </form>

  {% if analysis %}
    <h3>Resultado del análisis</h3>
    {% for a in analysis %}
      <div class="card">
        <strong>Contenido:</strong> {{a.data}}<br>
        <strong>Formato:</strong> {{a.type}}<br>
        <strong>Versión detectada (estimada):</strong> {{a.version}}<br>
        <strong>Tamaño en módulos:</strong> {{a.modules}} x {{a.modules}}<br>
        <strong>ECC detectado:</strong> {{a.ecc}}<br>
        <img src="data:image/png;base64,{{a.img_b64}}">
      </div>
    {% endfor %}
  {% endif %}
</body>
</html>
"""

# ========= Helpers existentes (para generación coloreada) =========
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
    func = [[False]*size for _ in range(size)]
    sep = [[False]*size for _ in range(size)]
    finder_positions = [(0,0), (0,size-7), (size-7,0)]
    for (r0,c0) in finder_positions:
        for r in range(r0, r0+7):
            for c in range(c0, c0+7):
                if 0 <= r < size and 0 <= c < size:
                    func[r][c] = True
        for r in range(r0-1, r0+8):
            for c in range(c0-1, c0+8):
                if 0 <= r < size and 0 <= c < size:
                    if r < r0 or r > r0+6 or c < c0 or c > c0+6:
                        sep[r][c] = True
    for i in range(8, size-8):
        func[6][i] = True
        func[i][6] = True
    centers = compute_alignment_centers(version)
    for cy in centers:
        for cx in centers:
            if (cy <= 6 and cx <= 6) or (cy <= 6 and cx >= size-7) or (cy >= size-7 and cx <= 6):
                continue
            for r in range(cy-2, cy+3):
                for c in range(cx-2, cx+3):
                    if 0 <= r < size and 0 <= c < size:
                        func[r][c] = True
    for i in range(0, 9):
        if i < size:
            func[8][i] = True
            func[i][8] = True
            func[8][size-1-i] = True
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
    for r in range(size):
        for c in range(size):
            is_dark = bool(rows[r][c])
            if is_dark: dark_modules += 1
            x0 = (c + border) * scale
            y0 = (r + border) * scale
            x1 = x0 + scale - 1
            y1 = y0 + scale - 1
            if sep_mask[r][c] and not is_dark:
                draw.rectangle([x0,y0,x1,y1], fill=PALETTE['separator']); continue
            if not is_dark: continue
            if func_mask[r][c]:
                draw.rectangle([x0,y0,x1,y1], fill=PALETTE['format'])
            else:
                draw.rectangle([x0,y0,x1,y1], fill=PALETTE['data'])
    buf = BytesIO(); img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode('ascii')
    return b64, {
        'size': size,
        'modules': size*size,
        'dark_modules': dark_modules,
        'functional_modules': sum(sum(1 for c in row if c) for row in func_mask),
        'data_modules_est': size*size - sum(sum(1 for c in row if c) for row in func_mask),
        'border': border
    }

# ========= Rutas =========
@app.route('/', methods=['GET', 'POST'])
def index():
    text, ecc, qrs, error = "", "H", [], None
    if request.method == 'POST':
        text = (request.form.get('text') or "").strip()
        ecc = request.form.get('ecc') or "H"
        if not text:
            error = "Debes ingresar el texto raw."
        else:
            try:
                qr_min = segno.make(text, error=ecc, boost_error=False, micro=False)
            except Exception:
                error = "El texto no cabe en ninguna versión con el ECC seleccionado."
                qr_min = None
            if qr_min:
                min_ver = qr_min.version
                for v in range(min_ver, 41):
                    try:
                        qr_v = segno.make(text, error=ecc, version=v, boost_error=False, micro=False)
                    except Exception: break
                    matrix = list(qr_v.matrix)
                    b64, metrics = render_colored_png_from_matrix(matrix, qr_v.version, ecc, getattr(qr_v,'mask',None))
                    qrs.append({
                        'version': qr_v.version,
                        'size': metrics['size'],
                        'img_b64': b64,
                        'ecc': ecc,
                        'mask': getattr(qr_v,'mask',None),
                        'modules': metrics['modules'],
                        'dark_modules': metrics['dark_modules'],
                        'functional_modules': metrics['functional_modules'],
                        'data_modules': metrics['data_modules_est'],
                        'border': metrics['border']
                    })
    return render_template_string(TEMPLATE, text=text, ecc=ecc, qrs=qrs, error=error)

@app.route('/analyze', methods=['POST'])
def analyze():
    analysis = []
    file = request.files.get('file')
    if file:
        img = Image.open(file.stream).convert("RGB")
        decoded = decode(img)
        for d in decoded:
            data = d.data.decode("utf-8", errors="ignore")
            # estimar versión a partir del tamaño en módulos
            # módulo size = (px / symbols)
            symbols = d.rect.width
            version_est = (symbols - 21)//4 + 1 if symbols>=21 else "?"
            # preview base64
            buf = BytesIO(); img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            analysis.append({
                "data": data,
                "type": d.type,
                "version": version_est,
                "modules": symbols,
                "ecc": "Desconocido (lector no lo reporta)",
                "img_b64": b64
            })
    return render_template_string(TEMPLATE, text="", ecc="H", qrs=None, error=None, analysis=analysis)

if __name__ == "__main__":
    app.run(debug=True)
