# -*- coding: utf-8 -*-
from io import BytesIO
from PIL import Image, ImageDraw
import base64
from functional_mask import build_function_mask, compute_alignment_centers

# Paleta para render
PALETTE = {
    'background': (255, 255, 255),
    'finder': (128, 0, 128),
    'separator': (230, 230, 230),
    'timing': (255, 165, 0),
    'alignment': (0, 128, 128),
    'format': (255, 0, 0),
    'version': (180, 0, 0),
    'data': (35, 35, 35),          # datos (oscuro carbón)
    'ecc': (20, 90, 160),          # ECC (azulado)
}

# --------------------------------------------------------------------
#  ECC codewords por bloque (tabla compacta) SOLO para ECC=M v1..v10.
#  Tu caso (Yape) usa M, típicamente v6/v7; esto lo cubre perfecto.
#  Formato: version -> (g1_blocks, ecc_per_block_g1, g2_blocks, ecc_per_block_g2)
#  Nota: en M el #ECC por bloque es fijo dentro de cada versión.
# --------------------------------------------------------------------
_ECC_TABLE_M = {
    1:  (1, 10, 0, 0),
    2:  (1, 16, 1, 16),
    3:  (1, 26, 1, 26),
    4:  (2, 18, 2, 18),
    5:  (2, 24, 2, 24),
    6:  (4, 16, 4, 16),
    7:  (2, 18, 4, 18),
    8:  (4, 22, 2, 22),
    9:  (4, 20, 4, 20),
    10: (2, 24, 6, 24),
}

def _total_ecc_codewords(version: int, ecc_level: str) -> int:
    """
    Devuelve el total de codewords ECC para la versión/ecc dada.
    Por ahora implementado para ECC='M' y v1..v10.
    Si no se reconoce, devuelve 0 (pintará todo como 'datos' para evitar confusión).
    """
    ecc = (ecc_level or 'M').upper()
    if ecc == 'M' and version in _ECC_TABLE_M:
        g1, ecc1, g2, ecc2 = _ECC_TABLE_M[version]
        return g1 * ecc1 + g2 * ecc2
    # TODO: extender para L/Q/H y v11..v40 si lo necesitas
    return 0

def _data_modules_coords(size: int, func_mask):
    """
    Devuelve las coordenadas (r,c) de módulos NO funcionales en el
    orden de colocación estándar QR (zig-zag de 2 columnas), saltando col=6.
    """
    coords = []
    upward = True
    col = size - 1
    while col > 0:
        if col == 6:  # columna de timing
            col -= 1
        for i in range(size):
            r = (size - 1 - i) if upward else i
            # par de columnas [col, col-1]
            for c in (col, col - 1):
                if 0 <= r < size and 0 <= c < size and not func_mask[r][c]:
                    coords.append((r, c))
        upward = not upward
        col -= 2
    return coords

def render_colored_png_from_matrix(matrix, version, border=4, scale=6, ecc='M'):
    """
    Renderiza PNG coloreado por zonas técnicas y distingue 'datos' vs 'ECC'.
    matrix: iterable de filas (True=oscuro, False=claro)
    version: int (1..40)
    border: quiet zone en módulos
    scale: tamaño de cada módulo en px
    ecc: nivel de corrección ('L','M','Q','H') para colorear ECC (tabla actual: M v1..v10)
    """
    rows = list(matrix)
    size = len(rows)

    # Máscaras funcionales
    func_mask, sep_mask = build_function_mask(size, version)

    # Métricas base
    total_modules = size * size
    functional_count = sum(sum(1 for c in row if c) for row in func_mask)
    data_modules_est = total_modules - functional_count

    # ------------------------------------------------------------
    # Determinar qué módulos no-funcionales corresponden a 'datos'
    # y cuáles a 'ECC' según el orden estándar y el #ECC total.
    # ------------------------------------------------------------
    coords = _data_modules_coords(size, func_mask)  # orden de colocación
    total_cw_est = data_modules_est // 8
    ecc_cw_total = _total_ecc_codewords(version, ecc)
    data_cw = max(0, total_cw_est - ecc_cw_total)
    data_bits = data_cw * 8

    # Conjunto de posiciones consideradas 'datos' (primeros bits colocados)
    data_positions = set(coords[:data_bits])

    # Imagen de salida
    img_px = (size + 2 * border) * scale
    img = Image.new('RGB', (img_px, img_px), PALETTE['background'])
    draw = ImageDraw.Draw(img)

    dark_modules = 0

    # atajos
    finder_positions = [(0, 0), (0, size - 7), (size - 7, 0)]
    alignment_centers = compute_alignment_centers(version)

    for r in range(size):
        for c in range(size):
            is_dark = bool(rows[r][c])
            x0 = (c + border) * scale
            y0 = (r + border) * scale
            x1 = x0 + scale - 1
            y1 = y0 + scale - 1

            # Visualizar 'separator' en gris si el módulo real es claro
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
                    if r0 <= r < r0 + 7 and c0 <= c < c0 + 7:
                        draw.rectangle([x0, y0, x1, y1], fill=PALETTE['finder'])
                        in_finder = True
                        break
                if in_finder:
                    continue

                # Alignment
                aligned = False
                for cy in alignment_centers:
                    for cx in alignment_centers:
                        if (cy - 2) <= r <= (cy + 2) and (cx - 2) <= c <= (cx + 2):
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
                if (r == 8 or c == 8) or (r < 9 and c < 9) or (c >= size - 8 and r < 9):
                    draw.rectangle([x0, y0, x1, y1], fill=PALETTE['format'])
                    continue

                # Version
                if version >= 7 and ((r < 6 and c >= size - 11) or (r >= size - 11 and c < 6)):
                    draw.rectangle([x0, y0, x1, y1], fill=PALETTE['version'])
                    continue

            # -----------------------------
            # Área no-funcional: datos/ECC
            # -----------------------------
            if (r, c) in data_positions:
                fill = PALETTE['data']
            else:
                # Si no tenemos tabla para esta versión/ECC, ecc_cw_total=0
                # y todo se pintará como 'datos' (comportamiento seguro).
                fill = PALETTE['ecc'] if ecc_cw_total > 0 else PALETTE['data']
            draw.rectangle([x0, y0, x1, y1], fill=fill)

    # Codificar PNG a base64 + métricas
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

def render_colored_svg_from_matrix(matrix, version, border=4, scale=10, ecc='M'):
    """
    Devuelve un SVG (bytes) coloreado por zonas técnicas y distinguiendo DATOS vs ECC
    (para ECC='M' v1..v10; si no se reconoce, todo lo no-funcional se pinta como datos).

    - matrix: iterable de filas (True=oscuro, False=claro)
    - version: int 1..40
    - border: quiet zone en módulos
    - scale: tamaño de cada módulo en px
    - ecc: 'L'/'M'/'Q'/'H' (tabla actual implementada para 'M' v1..v10)
    """
    rows = list(matrix)
    size = len(rows)

    func_mask, sep_mask = build_function_mask(size, version)

    total_modules = size * size
    functional_count = sum(sum(1 for c in row if c) for row in func_mask)
    data_modules_est = total_modules - functional_count

    # Orden de colocación y separación Datos/ECC
    coords = _data_modules_coords(size, func_mask)
    total_cw_est = data_modules_est // 8
    ecc_cw_total = _total_ecc_codewords(version, ecc)
    data_cw = max(0, total_cw_est - ecc_cw_total)
    data_bits = data_cw * 8
    data_positions = set(coords[:data_bits])

    # SVG header
    size_mod = size + 2 * border
    px = size_mod * scale
    out = []
    out.append('<?xml version="1.0" encoding="UTF-8"?>')
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{px}" height="{px}" viewBox="0 0 {px} {px}">')
    out.append(f'<rect width="{px}" height="{px}" fill="rgb{PALETTE["background"]}"/>')

    # Para detección de áreas funcionales
    finder_positions = [(0, 0), (0, size - 7), (size - 7, 0)]
    alignment_centers = compute_alignment_centers(version)

    # Dibuja separadores (solo donde el módulo real es claro)
    for r in range(size):
        for c in range(size):
            if sep_mask[r][c] and not rows[r][c]:
                x = (c + border) * scale
                y = (r + border) * scale
                out.append(f'<rect x="{x}" y="{y}" width="{scale}" height="{scale}" fill="rgb{PALETTE["separator"]}"/>')

    # Dibuja módulos oscuros coloreando por zona / datos / ecc
    for r in range(size):
        for c in range(size):
            if not rows[r][c]:
                continue

            # ¿funcional?
            fill = None
            if func_mask[r][c]:
                # Finder
                for (r0, c0) in finder_positions:
                    if r0 <= r < r0 + 7 and c0 <= c < c0 + 7:
                        fill = PALETTE['finder']; break
                if fill is None:
                    # Alignment
                    aligned = False
                    for cy in alignment_centers:
                        for cx in alignment_centers:
                            if (cy - 2) <= r <= (cy + 2) and (cx - 2) <= c <= (cx + 2):
                                fill = PALETTE['alignment']; aligned = True; break
                        if aligned: break
                if fill is None:
                    # Timing
                    if r == 6 or c == 6:
                        fill = PALETTE['timing']
                if fill is None:
                    # Format
                    if (r == 8 or c == 8) or (r < 9 and c < 9) or (c >= size - 8 and r < 9):
                        fill = PALETTE['format']
                if fill is None and version >= 7:
                    # Version
                    if (r < 6 and c >= size - 11) or (r >= size - 11 and c < 6):
                        fill = PALETTE['version']
                if fill is None:
                    # Por si algún caso no cayó arriba, tratar como data
                    fill = PALETTE['data']
            else:
                # No-funcional: datos vs ecc
                fill = PALETTE['data'] if (r, c) in data_positions else (PALETTE['ecc'] if ecc_cw_total > 0 else PALETTE['data'])

            # pintar
            x = (c + border) * scale
            y = (r + border) * scale
            out.append(f'<rect x="{x}" y="{y}" width="{scale}" height="{scale}" fill="rgb{fill}"/>')

    out.append('</svg>')
    return "\n".join(out).encode("utf-8")
