#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QR Generator Advanced - Flask Web Application
"""

import logging
from flask import Flask, render_template, request, send_file
from io import BytesIO
from typing import Tuple
from core.qr_generator import make_qr, evaluate_all_masks
from core.renderer import render_colored_png_from_matrix, render_colored_svg_from_matrix
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _read_params(req) -> Tuple[str, str, str, str, str, bool, str, bool, bool, int]:
    """Extract and validate QR generation parameters from Flask request."""
    text = (req.values.get('text') or "").strip()
    ecc = (req.values.get('ecc') or "M").strip().upper()
    version = req.values.get('version') or "auto"
    mode = (req.values.get('mode') or "byte").strip().lower()
    encoding = (req.values.get('encoding') or "utf-8").strip()
    eci = (req.values.get('eci') == 'true') if req.values.get('eci') is not None else True
    mask = req.values.get('mask') or "2"
    boost_error = (req.values.get('boost_error') == 'true') if req.values.get('boost_error') is not None else False
    micro = (req.values.get('micro') == 'true') if req.values.get('micro') is not None else False
    
    try:
        border = int(req.values.get('border') or 4)
        if border < 0 or border > 20:
            border = 4
    except (ValueError, TypeError):
        border = 4
        
    return text, ecc, version, mode, encoding, eci, mask, boost_error, micro, border

# Variable global para guardar el logo actual
_current_logo_image = None

def _svg_from_matrix_rects(matrix, logo_image=None, border=4, scale=10, light="#ffffff", dark="#000000"):
    """Genera un SVG del QR donde los módulos que colisionen con el logo se omiten."""
    from PIL import Image, ImageDraw
    import numpy as np
    import base64
    from io import BytesIO
    
    # Si no hay logo, usar triángulo
    if logo_image is None:
        logo_size_px = 400
        img_logo = Image.new("RGBA", (logo_size_px, logo_size_px), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img_logo)
        pts = [(logo_size_px//2, 20), (logo_size_px-20, logo_size_px-20), (20, logo_size_px-20)]
        draw.polygon(pts, fill=(0, 0, 0, 255))
    else:
        img_logo = logo_image.convert("RGBA")
        logo_size_px = max(img_logo.size)
    
    logo_array = np.array(img_logo)
    alpha = logo_array[:, :, 3]
    mask_array = alpha > 128  # Cambié de 200 a 128 para detectar mejor la transparencia

    rows = list(matrix)
    n = len(rows)
    size_mod = n + 2 * border
    px = size_mod * scale
    cx = (n / 2 + border) * scale
    cy = (n / 2 + border) * scale

    logo_size = n * scale * 0.3
    mask_scale = logo_size / logo_size_px
    mask_width = int(logo_size_px * mask_scale)
    mask_height = int(logo_size_px * mask_scale)
    mask_array = np.array(
        Image.fromarray(mask_array.astype(np.uint8) * 255)
        .resize((mask_width, mask_height), Image.LANCZOS)
    ) > 128

    mask_offset_x = int(cx - mask_width / 2)
    mask_offset_y = int(cy - mask_height / 2)

    out = []
    out.append('<?xml version="1.0" encoding="UTF-8"?>')
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{px}" height="{px}" viewBox="0 0 {px} {px}">')
    out.append(f'<rect width="{px}" height="{px}" fill="{light}"/>')

    for r in range(n):
        for c in range(n):
            if not rows[r][c]:
                continue

            x = (c + border) * scale
            y = (r + border) * scale

            collision = False
            for px_iter in range(int(x), int(x + scale)):
                for py_iter in range(int(y), int(y + scale)):
                    mx = px_iter - mask_offset_x
                    my = py_iter - mask_offset_y
                    if (0 <= mx < mask_width and 0 <= my < mask_height and mask_array[my, mx]):
                        collision = True
                        break
                if collision:
                    break
            
            if collision:
                continue

            out.append(f'<rect x="{int(x)}" y="{int(y)}" width="{scale}" height="{scale}" fill="{dark}"/>')

    # Dibujar solo la imagen original sin procesarla
    img_resized = logo_image.convert("RGBA").resize((mask_width, mask_height), Image.LANCZOS)
    buffer = BytesIO()
    img_resized.save(buffer, format='PNG')
    buffer.seek(0)
    base64_str = base64.b64encode(buffer.getvalue()).decode()
    
    out.append(f'<image x="{mask_offset_x}" y="{mask_offset_y}" width="{mask_width}" height="{mask_height}" href="data:image/png;base64,{base64_str}"/>')
    out.append('</svg>')
    return "\n".join(out).encode("utf-8")

app = Flask(__name__, template_folder='templates')

@app.route('/', methods=['GET', 'POST'])
def index():
    global _current_logo_image
    from PIL import Image
    
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
    logo_image = None

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

        # Leer archivo logo si se subió
        if 'logo' in request.files and request.files['logo'].filename:
            try:
                file = request.files['logo']
                logo_image = Image.open(file.stream)
                _current_logo_image = logo_image
                logger.info(f"Logo uploaded: {file.filename} ({logo_image.size})")
            except Exception as ex:
                logger.warning(f"No se pudo cargar el logo: {ex}")
                logo_image = None
                _current_logo_image = None

        if not text:
            error = "Debes ingresar el texto raw que quieres codificar."
        else:
            try:
                logger.info(f"Generating QR code with parameters: ecc={ecc}, version={version}, mode={mode}, mask={mask}")
                qr_symbol = make_qr(
                    text=text, ecc=ecc, version=version, mode=mode,
                    encoding=encoding, eci=eci, mask=mask,
                    boost_error=boost_error, micro=micro
                )
                logger.info(f"Successfully generated QR code version {qr_symbol.version}")
            except Exception as ex:
                error = f"No se pudo generar el QR con los parámetros elegidos: {ex}"
                logger.error(f"QR generation failed: {ex}")
                qr_symbol = None

            if qr_symbol:
                matrix = list(qr_symbol.matrix)
                
                # Si hay logo, generar SVG para preview; si no, generar PNG
                qr_view_is_svg = False
                if logo_image:
                    svg_bytes = _svg_from_matrix_rects(matrix, logo_image=logo_image, border=border, scale=10,
                                                       light="#ffffff", dark="#000000")
                    b64 = base64.b64encode(svg_bytes).decode()
                    qr_view_is_svg = True
                    metrics = {
                        'size': len(matrix),
                        'modules': len(matrix) ** 2,
                        'dark_modules': sum(sum(row) for row in matrix),
                        'functional_modules': 0,
                        'data_modules_est': 0,
                        'border': border
                    }
                else:
                    b64, metrics = render_colored_png_from_matrix(
                        matrix, qr_symbol.version, border=border, scale=6, ecc=ecc
                    )

                try:
                    logger.info("Evaluating all mask patterns for optimization")
                    best_mask, best_score, scores = evaluate_all_masks(
                        text=text, ecc=ecc,
                        version=qr_symbol.version,
                        mode=mode, encoding=encoding, eci=eci,
                        boost_error=boost_error, micro=micro
                    )
                    scores_text = ", ".join(f"{k}:{v}" for k, v in sorted(scores.items()))
                    logger.info(f"Best mask: {best_mask} (score: {best_score})")
                except Exception as ex:
                    logger.warning(f"Mask evaluation failed: {ex}")
                    best_mask, best_score, scores_text = "-", "-", "no disponible"

                qr_view = {
                    'version': qr_symbol.version,
                    'size': metrics['size'],
                    'img_b64': b64,
                    'img_is_svg': qr_view_is_svg,
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
                    'mask_scores_text': scores_text,
                    'logo_image': logo_image
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
    global _current_logo_image
    
    text, ecc, version, mode, encoding, eci, mask, boost_error, micro, border = _read_params(request)
    if not text:
        return "Falta texto", 400
    qr = make_qr(text, ecc=ecc, version=version, mode=mode, encoding=encoding,
                 eci=eci, mask=mask, boost_error=boost_error, micro=micro)

    svg_bytes = _svg_from_matrix_rects(qr.matrix, logo_image=_current_logo_image, border=border, scale=10,
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