#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, send_file
from io import BytesIO
from qr_core import make_qr, evaluate_all_masks
from render import render_colored_png_from_matrix, render_colored_svg_from_matrix

def _read_params(req):
    text = (req.values.get('text') or "").strip()
    ecc = (req.values.get('ecc') or "M").strip().upper()
    version = req.values.get('version') or "auto"
    mode = (req.values.get('mode') or "byte").strip().lower()
    encoding = (req.values.get('encoding') or "utf-8").strip()
    eci = (req.values.get('eci') == 'true') if req.values.get('eci') is not None else True
    mask = req.values.get('mask') or "2"
    boost_error = (req.values.get('boost_error') == 'true') if req.values.get('boost_error') is not None else False
    micro = (req.values.get('micro') == 'true') if req.values.get('micro') is not None else False
    border = int(req.values.get('border') or 4)
    return text, ecc, version, mode, encoding, eci, mask, boost_error, micro, border

def _svg_from_matrix_rects(matrix, border=4, scale=10, light="#ffffff", dark="#000000"):
    """
    Genera un SVG donde cada módulo oscuro es un <rect> independiente.
    Incluye quiet zone = border (en módulos).
    """
    rows = list(matrix)
    n = len(rows)
    size_mod = n + 2 * border
    px = size_mod * scale

    # header
    out = []
    out.append('<?xml version="1.0" encoding="UTF-8"?>')
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{px}" height="{px}" viewBox="0 0 {px} {px}">')
    # fondo (quiet zone + blancos)
    out.append(f'<rect width="{px}" height="{px}" fill="{light}"/>')

    # dibuja cada módulo oscuro como rect
    for r in range(n):
        for c in range(n):
            if rows[r][c]:
                x = (c + border) * scale
                y = (r + border) * scale
                out.append(f'<rect x="{x}" y="{y}" width="{scale}" height="{scale}" fill="{dark}"/>')

    out.append('</svg>')
    return "\n".join(out).encode("utf-8")

app = Flask(__name__, template_folder='templates')

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
                qr_symbol = make_qr(
                    text=text, ecc=ecc, version=version, mode=mode,
                    encoding=encoding, eci=eci, mask=mask,
                    boost_error=boost_error, micro=micro
                )
            except Exception as ex:
                error = f"No se pudo generar el QR con los parámetros elegidos: {ex}"
                qr_symbol = None

            if qr_symbol:
                matrix = list(qr_symbol.matrix)
                b64, metrics = render_colored_png_from_matrix(
                    matrix, qr_symbol.version, border=border, scale=6, ecc=ecc
                )

                # Sugerencia de máscara (ISO/IEC)
                try:
                    best_mask, best_score, scores = evaluate_all_masks(
                        text=text, ecc=ecc,
                        version=qr_symbol.version,  # fijamos la versión concreta
                        mode=mode, encoding=encoding, eci=eci,
                        boost_error=boost_error, micro=micro
                    )
                    scores_text = ", ".join(f"{k}:{v}" for k, v in sorted(scores.items()))
                except Exception:
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

    return render_template(
        'index.html',
        text=text, ecc=ecc, version=version, mode=mode, encoding=encoding,
        eci=eci, mask=mask, boost_error=boost_error, micro=micro, border=border,
        qr=qr_view, error=error
    )

@app.route('/export/png', methods=['GET'])
def export_png_bw():
    text, ecc, version, mode, encoding, eci, mask, boost_error, micro, border = _read_params(request)
    if not text:
        return "Falta texto", 400
    qr = make_qr(text, ecc=ecc, version=version, mode=mode, encoding=encoding,
                 eci=eci, mask=mask, boost_error=boost_error, micro=micro)
    buf = BytesIO()
    # PNG monocromo; usa quiet zone = border
    qr.save(buf, kind='png', scale=10, border=border, light='white', dark='black')
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name='qr_bw.png', mimetype='image/png')

@app.route('/export/jpg', methods=['GET'])
def export_jpg_bw():
    text, ecc, version, mode, encoding, eci, mask, boost_error, micro, border = _read_params(request)
    if not text:
        return "Falta texto", 400
    qr = make_qr(text, ecc=ecc, version=version, mode=mode, encoding=encoding,
                 eci=eci, mask=mask, boost_error=boost_error, micro=micro)
    # Primero generamos PNG en memoria para conservar nitidez, luego convertimos a JPG
    png_buf = BytesIO()
    qr.save(png_buf, kind='png', scale=12, border=border, light='white', dark='black')
    png_buf.seek(0)

    from PIL import Image
    im = Image.open(png_buf).convert('RGB')
    jpg_buf = BytesIO()
    im.save(jpg_buf, format='JPEG', quality=95, optimize=True, progressive=True)
    jpg_buf.seek(0)
    return send_file(jpg_buf, as_attachment=True, download_name='qr_bw.jpg', mimetype='image/jpeg')

@app.route('/export/svg', methods=['GET'])
def export_svg_separate():
    text, ecc, version, mode, encoding, eci, mask, boost_error, micro, border = _read_params(request)
    if not text:
        return "Falta texto", 400
    qr = make_qr(text, ecc=ecc, version=version, mode=mode, encoding=encoding,
                 eci=eci, mask=mask, boost_error=boost_error, micro=micro)

    svg_bytes = _svg_from_matrix_rects(qr.matrix, border=border, scale=10,
                                       light="#ffffff", dark="#000000")
    buf = BytesIO(svg_bytes)
    return send_file(buf, as_attachment=True,
                     download_name='qr_bw_separate.svg',
                     mimetype='image/svg+xml')

@app.route('/export/svg-colored', methods=['GET'])
def export_svg_colored():
    text, ecc, version, mode, encoding, eci, mask, boost_error, micro, border = _read_params(request)
    if not text:
        return "Falta texto", 400
    qr = make_qr(text, ecc=ecc, version=version, mode=mode, encoding=encoding,
                 eci=eci, mask=mask, boost_error=boost_error, micro=micro)
    svg_bytes = render_colored_svg_from_matrix(
        qr.matrix, qr.version, border=border, scale=10, ecc=ecc
    )
    return send_file(BytesIO(svg_bytes), as_attachment=True,
                     download_name='qr_colored_zones.svg',
                     mimetype='image/svg+xml')

if __name__ == "__main__":
    app.run(debug=True)
