#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QR Visual Analyzer (configurable, clone-friendly) + Mask Penalty Suggestion

- Flask app que genera un único QR con los parámetros exactos elegidos.
- Form: texto + ECC + versión (auto o fija) + mode + encoding + ECI + mask (auto o fija) +
        boost_error + micro + quiet zone.
- Render: PNG coloreado por zonas técnicas (finder / timing / alignment / format / version / data).
- Métricas: tamaño, ecc, mask, quiet zone, dark modules, functional modules, data-area (estimado).
- NUEVO: Evalúa penalización (ISO/IEC) de las 8 máscaras y sugiere la de menor score.

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

app = Flask(__name__)

# Colores (RGB)
PALETTE = {
    'background': (255, 255, 255),
    'finder': (128, 0, 128),       # purple
    'separator': (230, 230, 230),  # light gray (visual)
    'timing': (255, 165, 0),       # orange
    'alignment': (0, 128, 128),    # teal
    'format': (255, 0, 0),         # red
    'version': (180, 0, 0),        # dark red
    'data': (35, 35, 35),          # dark charcoal
}

TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>QR Visual Analyzer — Configurable</title>
  <style>
    body{font-family:Inter, Arial, sans-serif; padding:18px; background:#fff; color:#222}
    .row{display:flex; flex-wrap:wrap; gap:16px; align-items:flex-end}
    .field{display:flex; flex-direction:column; font-size:14px}
    input[type="text"], select, input[type="number"]{padding:6px 8px; font-family:monospace; border:1px solid #ccc; border-radius:6px}
    label{font-weight:600; margin-bottom:4px}
    button{padding:10px 16px; border-radius:8px; border:1px solid #333; background:#111; color:#fff; cursor:pointer}
    button:hover{opacity:.9}
    .card{margin-top:18px; border:1px solid #ddd; border-radius:10px; padding:14px}
    img{display:block; margin:8px 0; border:1px solid #ccc}
    .metrics{font-size:13px; color:#333; line-height:1.4}
    .legend{margin-top:18px}
    .legend div{margin:6px 0}
    .sw{display:inline-block; width:18px; height:12px; border:1px solid #aaa; margin-right:8px}
    .error{color:#b00; font-weight:700}
    .hint{font-size:12px; color:#666}
    code{background:#f6f6f6; padding:1px 4px; border-radius:4px}
  </style>
</head>
<body>
  <h1>QR Visual Analyzer — Configurable</h1>

  <form method="post">
    <div class="row">
      <div class="field" style="flex:1 1 100%">
        <label>Texto (raw)</label>
        <input type="text" name="text" value="{{text|e}}" placeholder="Ingresa el payload EMVCo / string">
      </div>
    </div>

    <div class="row">
      <div class="field">
        <label>ECC</label>
        <select name="ecc">
          {% for v in ['L','M','Q','H'] %}
            <option value="{{v}}" {% if ecc==v %}selected{% endif %}>{{v}}</option>
          {% endfor %}
        </select>
      </div>

      <div class="field">
        <label>Versión</label>
        <select name="version">
          <option value="auto" {% if version=='auto' %}selected{% endif %}>auto (mínima)</option>
          {% for v in range(1,41) %}
            <option value="{{v}}" {% if version|int==v %}selected{% endif %}>v{{v}}</option>
          {% endfor %}
        </select>
        <div class="hint">Si eliges "auto", segno elige la mínima quepa con los demás parámetros.</div>
      </div>

      <div class="field">
        <label>Modo</label>
        <select name="mode">
          {% for v in ['byte','alphanumeric','numeric','kanji'] %}
            <option value="{{v}}" {% if mode==v %}selected{% endif %}>{{v}}</option>
          {% endfor %}
        </select>
        <div class="hint">Para clonar Yape: <strong>byte</strong></div>
      </div>

      <div class="field" style="min-width:200px">
        <label>Encoding</label>
        <input type="text" name="encoding" value="{{encoding|e}}">
        <div class="hint">Ej: utf-8, iso-8859-1</div>
      </div>

      <div class="field">
        <label>ECI</label>
        <select name="eci">
          <option value="true" {% if eci %}selected{% endif %}>True</option>
          <option value="false" {% if not eci %}selected{% endif %}>False</option>
        </select>
        <div class="hint">Yape: True (ECI UTF-8)</div>
      </div>

      <div class="field">
        <label>Mask</label>
        <select name="mask">
          <option value="auto" {% if mask=='auto' %}selected{% endif %}>auto</option>
          {% for m in range(8) %}
            <option value="{{m}}" {% if mask|int==m %}selected{% endif %}>{{m}}</option>
          {% endfor %}
        </select>
        <div class="hint">Yape: 2</div>
      </div>

      <div class="field">
        <label>boost_error</label>
        <select name="boost_error">
          <option value="false" {% if not boost_error %}selected{% endif %}>False</option>
          <option value="true" {% if boost_error %}selected{% endif %}>True</option>
        </select>
        <div class="hint">Para clonar: False</div>
      </div>

      <div class="field">
        <label>micro</label>
        <select name="micro">
          <option value="false" {% if not micro %}selected{% endif %}>False</option>
          <option value="true" {% if micro %}selected{% endif %}>True</option>
        </select>
        <div class="hint">Para clonar: False</div>
      </div>

      <div class="field">
        <label>Quiet zone (módulos)</label>
        <input type="number" name="border" min="0" max="20" step="1" value="{{border}}">
        <div class="hint">Yape: 4</div>
      </div>
    </div>

    <div class="row">
      <button type="submit">Generar</button>
    </div>
  </form>

  {% if error %}
    <p class="error">{{error}}</p>
  {% endif %}

  {% if qr %}
    <div class="card">
      <strong>v{{qr.version}}</strong> — {{qr.size}}×{{qr.size}} px (mask={{qr.mask}})<br>
      <em>Params:</em>
      ECC=<strong>{{qr.ecc}}</strong>,
      mode=<strong>{{qr.mode}}</strong>,
      encoding=<strong>{{qr.encoding}}</strong>,
      ECI=<strong>{{'True' if qr.eci else 'False'}}</strong>,
      boost_error=<strong>{{'True' if qr.boost_error else 'False'}}</strong>,
      micro=<strong>{{'True' if qr.micro else 'False'}}</strong>,
      border=<strong>{{qr.border}}</strong>
      <a href="data:image/png;base64,{{qr.img_b64}}" target="_blank">
        <img src="data:image/png;base64,{{qr.img_b64}}" width="300" alt="QR v{{qr.version}}">
      </a>
      <div class="metrics">
        Dark modules: {{qr.dark_modules}} / {{qr.modules}}<br>
        Functional modules: {{qr.functional_modules}}<br>
        Data-area modules (estimado): {{qr.data_modules}}<br>
        <hr>
        <strong>Sugerencia de máscara (menor penalización):</strong>
        mask=<strong>{{qr.best_mask}}</strong> (score={{qr.best_score}})
        <div class="hint">Scores por máscara: {{qr.mask_scores_text}}</div>
      </div>
    </div>

    <div class="legend">
      <h3>Leyenda</h3>
      <div><span class="sw" style="background:rgb(128,0,128)"></span> Finder pattern (3 esquinas)</div>
      <div><span class="sw" style="background:rgb(230,230,230);border:1px solid #ccc"></span> Separator (visual)</div>
      <div><span class="sw" style="background:rgb(255,165,0)"></span> Timing pattern (fila 6 y columna 6)</div>
      <div><span class="sw" style="background:rgb(0,128,128)"></span> Alignment patterns</div>
      <div><span class="sw" style="background:rgb(255,0,0)"></span> Format bits</div>
      <div><span class="sw" style="background:rgb(180,0,0)"></span> Version bits (v ≥ 7)</div>
      <div><span class="sw" style="background:rgb(35,35,35)"></span> Data area (datos + ECC)</div>
    </div>

    <p class="hint">
      Nota: separar exactamente datos vs. ECC por módulo implicaría mapear codewords a módulos; aquí marcamos zonas funcionales y tratamos lo demás como "data area".
    </p>

    <div class="legend" style="margin-top:32px">
      <h3>Documentación de parámetros</h3>
      <ul style="font-size:13px; line-height:1.5; color:#333">
        <li><strong>ECC</strong> (Error Correction Code):
          <ul>
            <li>L = 7% de recuperación de datos</li>
            <li>M = 15% (Yape usa este)</li>
            <li>Q = 25%</li>
            <li>H = 30% (más robusto, pero menos capacidad)</li>
          </ul>
        </li>
        <li><strong>Versión</strong>:
          <ul>
            <li><code>auto</code> → segno elige la versión mínima en la que el texto cabe con los parámetros actuales.</li>
            <li>1…40 → fuerza una versión fija. Cada incremento agrega 4 módulos por lado (v1=21×21, v40=177×177).</li>
          </ul>
        </li>
        <li><strong>Modo</strong>:
          <ul>
            <li><code>byte</code> → codifica byte a byte (soporta cualquier texto/UTF-8). Recomendado y usado por Yape.</li>
            <li><code>alphanumeric</code> → solo A–Z 0–9 y unos símbolos, más compacto.</li>
            <li><code>numeric</code> → solo dígitos, aún más compacto.</li>
            <li><code>kanji</code> → caracteres Shift-JIS japoneses.</li>
          </ul>
        </li>
        <li><strong>Encoding</strong>:
          <ul>
            <li>Charset usado en <code>mode=byte</code>. Ejemplos: <code>utf-8</code>, <code>iso-8859-1</code>.</li>
          </ul>
        </li>
        <li><strong>ECI</strong> (Extended Channel Interpretation):
          <ul>
            <li><code>True</code> → añade un encabezado que indica la codificación usada (ej. UTF-8).</li>
            <li><code>False</code> → se asume implícitamente ISO-8859-1.</li>
            <li>Yape usa: <strong>True + UTF-8</strong>.</li>
          </ul>
        </li>
        <li><strong>Mask</strong>:
          <ul>
            <li><code>auto</code> → segno prueba 8 patrones y escoge el de menor penalización.</li>
            <li>0…7 → fuerza máscara fija (Yape usa 2).</li>
          </ul>
        </li>
        <li><strong>boost_error</strong>:
          <ul>
            <li><code>False</code> → usa el ECC elegido sin subirlo automáticamente.</li>
            <li><code>True</code> → si cabe, sube a un ECC mayor (menos capacidad, más robustez).</li>
          </ul>
        </li>
        <li><strong>micro</strong>:
          <ul>
            <li><code>False</code> → QR estándar (v1–40).</li>
            <li><code>True</code> → Micro QR (más chico, menos capacidades).</li>
            <li>Yape usa QR estándar → False.</li>
          </ul>
        </li>
        <li><strong>Quiet zone (módulos)</strong>:
          <ul>
            <li>Borde blanco alrededor del símbolo, en módulos.</li>
            <li>Valor típico: 4 (mínimo recomendado en ISO/IEC).</li>
          </ul>
        </li>
      </ul>
    </div>
  {% endif %}
</body>
</html>
"""

# ---- Helpers de zonas funcionales ----

def compute_alignment_centers(version: int):
    """Centros de alignment segun especificación clásica."""
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

def build_function_mask(size: int, version: int):
    """
    Devuelve (func_mask, sep_mask):
      - func_mask[r][c] = True si es módulo funcional (finder/timing/alignment/format/version)
      - sep_mask[r][c] = True si pertenece al "separator" (visualización)
    """
    func = [[False]*size for _ in range(size)]
    sep = [[False]*size for _ in range(size)]

    # Finder 7x7 en 3 esquinas
    finder_positions = [(0,0), (0,size-7), (size-7,0)]
    for (r0,c0) in finder_positions:
        for r in range(r0, r0+7):
            for c in range(c0, c0+7):
                if 0 <= r < size and 0 <= c < size:
                    func[r][c] = True
        # Separator (marco 1 módulo alrededor)
        for r in range(r0-1, r0+8):
            for c in range(c0-1, c0+8):
                if 0 <= r < size and 0 <= c < size:
                    if r < r0 or r > r0+6 or c < c0 or c > c0+6:
                        sep[r][c] = True

    # Timing patterns: fila 6 y col 6
    for i in range(size):
        func[6][i] = True
        func[i][6] = True

    # Alignment patterns 5x5
    centers = compute_alignment_centers(version)
    for cy in centers:
        for cx in centers:
            # saltar solapes con finders
            if (cy <= 6 and cx <= 6) or (cy <= 6 and cx >= size-7) or (cy >= size-7 and cx <= 6):
                continue
            for r in range(cy-2, cy+3):
                for c in range(cx-2, cx+3):
                    if 0 <= r < size and 0 <= c < size:
                        func[r][c] = True

    # Format information (zonas alrededor de finders)
    for i in range(0, 9):
        if i < size:
            func[8][i] = True
            func[i][8] = True
            func[8][size-1-i] = True

    # Version information (v >= 7): dos áreas 6x3
    if version >= 7:
        for r in range(0,6):
            for c in range(size-11, size-8):
                func[r][c] = True
        for r in range(size-11, size-8):
            for c in range(0,6):
                func[r][c] = True

    return func, sep

def render_colored_png_from_matrix(matrix, version, border=4, scale=6):
    """
    matrix: iterable de filas (True=oscuro, False=claro)
    """
    rows = list(matrix)
    size = len(rows)
    func_mask, sep_mask = build_function_mask(size, version)

    img_px = (size + 2*border) * scale
    img = Image.new('RGB', (img_px, img_px), PALETTE['background'])
    draw = ImageDraw.Draw(img)

    dark_modules = 0

    finder_positions = [(0,0), (0,size-7), (size-7,0)]
    alignment_centers = compute_alignment_centers(version)

    for r in range(size):
        for c in range(size):
            is_dark = bool(rows[r][c])
            x0 = (c + border) * scale
            y0 = (r + border) * scale
            x1 = x0 + scale - 1
            y1 = y0 + scale - 1

            if sep_mask[r][c] and not is_dark:
                draw.rectangle([x0, y0, x1, y1], fill=PALETTE['separator'])
                continue

            if not is_dark:
                continue

            dark_modules += 1

            if func_mask[r][c]:
                # Finder
                in_finder = False
                for (r0, c0) in finder_positions:
                    if r0 <= r < r0+7 and c0 <= c < c0+7:
                        draw.rectangle([x0, y0, x1, y1], fill=PALETTE['finder'])
                        in_finder = True
                        break
                if in_finder:
                    continue

                # Alignment
                aligned = False
                for cy in alignment_centers:
                    for cx in alignment_centers:
                        if (cy-2) <= r <= (cy+2) and (cx-2) <= c <= (cx+2):
                            draw.rectangle([x0, y0, x1, y1], fill=PALETTE['alignment'])
                            aligned = True
                            break
                    if aligned:
                        break
                if aligned:
                    continue

                # Timing
                if r == 6 or c == 6:
                    draw.rectangle([x0, y0, x1, y1], fill=PALETTE['timing'])
                    continue

                # Format
                if (r == 8 or c == 8) or (r < 9 and c < 9) or (c >= size-8 and r < 9):
                    draw.rectangle([x0, y0, x1, y1], fill=PALETTE['format'])
                    continue

                # Version
                if version >= 7 and ((r < 6 and c >= size-11) or (r >= size-11 and c < 6)):
                    draw.rectangle([x0, y0, x1, y1], fill=PALETTE['version'])
                    continue

            # Data area
            draw.rectangle([x0, y0, x1, y1], fill=PALETTE['data'])

    total_modules = size * size
    functional_count = sum(sum(1 for c in row if c) for row in func_mask)
    data_modules_est = total_modules - functional_count

    buf = BytesIO()
    img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode('ascii')

    return b64, {
        'size': size,
        'modules': total_modules,
        'dark_modules': dark_modules,
        'functional_modules': functional_count,
        'data_modules_est': data_modules_est,
        'border': border
    }

# ---- Penalización ISO/IEC (N1..N4) ----

def penalty_N1(rows):
    score = 0
    n = len(rows)
    for r in range(n):
        run = 1
        for c in range(1, n):
            if rows[r][c] == rows[r][c-1]:
                run += 1
            else:
                if run >= 5:
                    score += 3 + (run - 5)
                run = 1
        if run >= 5:
            score += 3 + (run - 5)

    # columnas
    for c in range(n):
        run = 1
        for r in range(1, n):
            if rows[r][c] == rows[r-1][c]:
                run += 1
            else:
                if run >= 5:
                    score += 3 + (run - 5)
                run = 1
        if run >= 5:
            score += 3 + (run - 5)
    return score

def penalty_N2(rows):
    score = 0
    n = len(rows)
    for r in range(n-1):
        for c in range(n-1):
            v = rows[r][c]
            if rows[r][c+1] == v and rows[r+1][c] == v and rows[r+1][c+1] == v:
                score += 3
    return score

def _pattern_1_1_3_1_1(seq):
    # Devuelve índices donde aparece 1011101 (1:1:3:1:1) con 4 claros a un lado
    idxs = []
    n = len(seq)
    pat = [1,0,1,1,1,0,1]
    for i in range(n - 7 + 1):
        if seq[i:i+7] == pat:
            # check 4 blancos a izq o der
            left_ok = (i >= 4 and all(v == 0 for v in seq[i-4:i]))
            right_ok = (i+7 <= n-4 and all(v == 0 for v in seq[i+7:i+11]))
            if left_ok or right_ok:
                idxs.append(i)
    return idxs

def penalty_N3(rows):
    score = 0
    n = len(rows)
    # filas
    for r in range(n):
        row = [1 if rows[r][c] else 0 for c in range(n)]
        score += 40 * len(_pattern_1_1_3_1_1(row))
    # columnas
    for c in range(n):
        col = [1 if rows[r][c] else 0 for r in range(n)]
        score += 40 * len(_pattern_1_1_3_1_1(col))
    return score

def penalty_N4(rows):
    n = len(rows)
    total = n * n
    dark = sum(1 for r in range(n) for c in range(n) if rows[r][c])
    ratio = dark * 100.0 / total
    k = int(abs(ratio - 50.0) // 5.0)  # por cada 5% de desviación
    return k * 10

def compute_mask_penalty(matrix_bool):
    """matrix_bool: lista de listas de bool (True=oscuro)."""
    rows = [[bool(v) for v in row] for row in matrix_bool]
    return penalty_N1(rows) + penalty_N2(rows) + penalty_N3(rows) + penalty_N4(rows)

# ---- Encapsulado de creación segno acorde a parámetros ----

def make_qr(text, ecc='M', version=None, mode='byte', encoding='utf-8',
            eci=True, mask='auto', boost_error=False, micro=False):
    """
    Crea el símbolo segun parámetros elegidos.
    - version: int 1..40 o None/'auto' para mínima
    - mask: 'auto' => None (auto-selección), si no int 0..7
    """
    mask_arg = None if mask == 'auto' else int(mask)
    ver_arg = None if (version in (None, 'auto')) else int(version)

    return segno.make(
        text,
        error=ecc,
        version=ver_arg,
        mode=mode,
        encoding=encoding,
        eci=bool(eci),
        mask=mask_arg,
        boost_error=bool(boost_error),
        micro=bool(micro)
    )

def evaluate_all_masks(text, ecc, version, mode, encoding, eci, boost_error, micro):
    """
    Calcula penalización para máscaras 0..7 con los mismos parámetros.
    Devuelve (best_mask, best_score, scores_dict, chosen_version)
    """
    scores = {}
    chosen_version = None
    # Si el usuario eligió 'auto' de versión, la versión mínima no depende de la máscara → cualquiera sirve.
    # Generamos con mask=0 para fijar chosen_version si está en auto.
    try:
        sym0 = make_qr(text, ecc=ecc, version=version, mode=mode, encoding=encoding,
                       eci=eci, mask=0, boost_error=boost_error, micro=micro)
    except Exception:
        # Si falla con mask=0 (no debería), probamos sin máscara (auto) solo para fijar versión
        sym0 = make_qr(text, ecc=ecc, version=version, mode=mode, encoding=encoding,
                       eci=eci, mask='auto', boost_error=boost_error, micro=micro)
    chosen_version = sym0.version

    best_mask = None
    best_score = None

    for m in range(8):
        sym = make_qr(text, ecc=ecc, version=chosen_version, mode=mode, encoding=encoding,
                      eci=eci, mask=m, boost_error=boost_error, micro=micro)
        mat = list(sym.matrix)
        sc = compute_mask_penalty(mat)
        scores[m] = sc
        if best_score is None or sc < best_score:
            best_score = sc
            best_mask = m

    return best_mask, best_score, scores, chosen_version

# ---- Flask route ----

@app.route('/', methods=['GET', 'POST'])
def index():
    # Defaults = receta Yape
    text = ""
    ecc = "M"
    version = "auto"
    mode = "byte"
    encoding = "utf-8"
    eci = True
    mask = "2"
    boost_error = False
    micro = False
    border = 4

    qr_view = None
    error = None

    if request.method == 'POST':
        text = (request.form.get('text') or "").strip()
        ecc = (request.form.get('ecc') or "M").strip().upper()
        version = request.form.get('version') or "auto"
        mode = (request.form.get('mode') or "byte").strip().lower()
        encoding = (request.form.get('encoding') or "utf-8").strip()
        eci = (request.form.get('eci') == 'true')
        mask = request.form.get('mask') or "2"
        boost_error = (request.form.get('boost_error') == 'true')
        micro = (request.form.get('micro') == 'true')
        try:
            border = int(request.form.get('border') or 4)
        except Exception:
            border = 4

        if not text:
            error = "Debes ingresar el texto raw que quieres codificar."
        else:
            try:
                # Generar el símbolo pedido por el usuario (tal cual sus parámetros)
                qr_symbol = make_qr(
                    text=text,
                    ecc=ecc,
                    version=version,
                    mode=mode,
                    encoding=encoding,
                    eci=eci,
                    mask=mask,
                    boost_error=boost_error,
                    micro=micro
                )
            except Exception as ex:
                error = f"No se pudo generar el QR con los parámetros elegidos: {ex}"
                qr_symbol = None

            if qr_symbol:
                # Render coloreado + métricas
                matrix = list(qr_symbol.matrix)
                b64, metrics = render_colored_png_from_matrix(
                    matrix, qr_symbol.version, border=border, scale=6
                )

                # Evaluar penalización para las 8 máscaras con los mismos parámetros base
                try:
                    best_mask, best_score, scores, fixed_version = evaluate_all_masks(
                        text=text, ecc=ecc,
                        version=qr_symbol.version,  # fijamos la versión concreta del símbolo generado
                        mode=mode, encoding=encoding, eci=eci,
                        boost_error=boost_error, micro=micro
                    )
                    scores_text = ", ".join(f"{k}:{v}" for k, v in sorted(scores.items()))
                except Exception as _:
                    best_mask, best_score, scores_text = "-", "-", "no disponible"

                qr_view = {
                    'version': qr_symbol.version,
                    'size': metrics['size'],
                    'img_b64': b64,
                    'ecc': ecc,
                    'mask': getattr(qr_symbol, 'mask', None if mask == 'auto' else int(mask)),
                    'modules': metrics['modules'],
                    'dark_modules': metrics['dark_modules'],
                    'functional_modules': metrics['functional_modules'],
                    'data_modules': metrics['data_modules_est'],
                    'border': metrics['border'],
                    'mode': mode,
                    'encoding': encoding,
                    'eci': eci,
                    'boost_error': boost_error,
                    'micro': micro,
                    'best_mask': best_mask,
                    'best_score': best_score,
                    'mask_scores_text': scores_text
                }

    return render_template_string(
        TEMPLATE,
        text=text, ecc=ecc, version=version, mode=mode, encoding=encoding,
        eci=eci, mask=mask, boost_error=boost_error, micro=micro, border=border,
        qr=qr_view, error=error
    )

if __name__ == "__main__":
    app.run(debug=True)
