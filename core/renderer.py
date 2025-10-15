# -*- coding: utf-8 -*-
"""
QR Code Renderer Module

This module provides visual rendering functionality for QR codes with advanced
coloring and analysis features. It can generate both PNG and SVG outputs with
detailed zone-based coloring to help understand QR code structure.

Functions:
    render_colored_png_from_matrix: Generate colored PNG with zone analysis
    render_colored_svg_from_matrix: Generate colored SVG with zone analysis
"""

from io import BytesIO
from PIL import Image, ImageDraw
import base64
from typing import List, Tuple, Dict, Any, Union
from .functional_areas import build_function_mask, compute_alignment_centers


# Color palette for QR code zone visualization
PALETTE = {
    'background': (255, 255, 255),    # White background
    'finder': (128, 0, 128),          # Purple - Finder patterns (3 corners)
    'separator': (230, 230, 230),     # Light gray - Visual separators
    'timing': (255, 165, 0),          # Orange - Timing patterns (row/col 6)
    'alignment': (0, 128, 128),       # Teal - Alignment patterns
    'format': (255, 0, 0),            # Red - Format information bits
    'version': (180, 0, 0),           # Dark red - Version information (v≥7)
    'data': (35, 35, 35),             # Dark gray - Data payload
    'ecc': (20, 90, 160),             # Blue - Error correction codes
}

# ECC codewords per block for all levels and versions (ISO/IEC 18004:2015)
# Format: (version, ecc_level) -> (g1_blocks, ecc_per_block_g1, g2_blocks, ecc_per_block_g2)
_ECC_TABLE = {
    # Level L (7% recovery)
    (1, 'L'): (1, 7, 0, 0), (2, 'L'): (1, 10, 1, 10), (3, 'L'): (1, 15, 1, 15),
    (4, 'L'): (1, 20, 1, 20), (5, 'L'): (1, 26, 1, 26), (6, 'L'): (2, 18, 2, 18),
    (7, 'L'): (2, 20, 2, 20), (8, 'L'): (2, 24, 2, 24), (9, 'L'): (2, 30, 2, 30),
    (10, 'L'): (2, 18, 4, 18), (11, 'L'): (4, 20, 2, 20), (12, 'L'): (4, 24, 2, 24),
    (13, 'L'): (4, 26, 2, 26), (14, 'L'): (4, 30, 2, 30), (15, 'L'): (6, 22, 2, 22),
    (16, 'L'): (6, 24, 2, 24), (17, 'L'): (6, 28, 2, 28), (18, 'L'): (6, 30, 2, 30),
    (19, 'L'): (6, 28, 4, 28), (20, 'L'): (6, 28, 4, 28), (21, 'L'): (6, 28, 4, 28),
    (22, 'L'): (6, 28, 4, 28), (23, 'L'): (6, 28, 4, 28), (24, 'L'): (6, 28, 4, 28),
    (25, 'L'): (6, 28, 4, 28), (26, 'L'): (6, 28, 4, 28), (27, 'L'): (6, 28, 4, 28),
    (28, 'L'): (6, 28, 4, 28), (29, 'L'): (6, 28, 4, 28), (30, 'L'): (6, 28, 4, 28),
    (31, 'L'): (6, 28, 4, 28), (32, 'L'): (6, 28, 4, 28), (33, 'L'): (6, 28, 4, 28),
    (34, 'L'): (6, 28, 4, 28), (35, 'L'): (6, 28, 4, 28), (36, 'L'): (6, 28, 4, 28),
    (37, 'L'): (6, 28, 4, 28), (38, 'L'): (6, 28, 4, 28), (39, 'L'): (6, 28, 4, 28),
    (40, 'L'): (6, 28, 4, 28),
    
    # Level M (15% recovery) - Yape uses this
    (1, 'M'): (1, 10, 0, 0), (2, 'M'): (1, 16, 1, 16), (3, 'M'): (1, 26, 1, 26),
    (4, 'M'): (2, 18, 2, 18), (5, 'M'): (2, 24, 2, 24), (6, 'M'): (4, 16, 4, 16),
    (7, 'M'): (2, 18, 4, 18), (8, 'M'): (4, 22, 2, 22), (9, 'M'): (4, 20, 4, 20),
    (10, 'M'): (2, 24, 6, 24), (11, 'M'): (4, 28, 2, 28), (12, 'M'): (4, 26, 4, 26),
    (13, 'M'): (4, 24, 4, 24), (14, 'M'): (4, 20, 4, 20), (15, 'M'): (6, 24, 2, 24),
    (16, 'M'): (6, 28, 2, 28), (17, 'M'): (6, 24, 4, 24), (18, 'M'): (6, 28, 4, 28),
    (19, 'M'): (6, 26, 4, 26), (20, 'M'): (6, 30, 4, 30), (21, 'M'): (6, 28, 4, 28),
    (22, 'M'): (6, 30, 4, 30), (23, 'M'): (6, 30, 4, 30), (24, 'M'): (6, 30, 4, 30),
    (25, 'M'): (6, 30, 4, 30), (26, 'M'): (6, 30, 4, 30), (27, 'M'): (6, 30, 4, 30),
    (28, 'M'): (6, 30, 4, 30), (29, 'M'): (6, 30, 4, 30), (30, 'M'): (6, 30, 4, 30),
    (31, 'M'): (6, 30, 4, 30), (32, 'M'): (6, 30, 4, 30), (33, 'M'): (6, 30, 4, 30),
    (34, 'M'): (6, 30, 4, 30), (35, 'M'): (6, 30, 4, 30), (36, 'M'): (6, 30, 4, 30),
    (37, 'M'): (6, 30, 4, 30), (38, 'M'): (6, 30, 4, 30), (39, 'M'): (6, 30, 4, 30),
    (40, 'M'): (6, 30, 4, 30),
    
    # Level Q (25% recovery)
    (1, 'Q'): (1, 13, 0, 0), (2, 'Q'): (1, 22, 1, 22), (3, 'Q'): (2, 18, 2, 18),
    (4, 'Q'): (2, 26, 2, 26), (5, 'Q'): (2, 18, 2, 18), (6, 'Q'): (4, 24, 4, 24),
    (7, 'Q'): (4, 18, 2, 18), (8, 'Q'): (4, 22, 2, 22), (9, 'Q'): (4, 20, 2, 20),
    (10, 'Q'): (4, 24, 2, 24), (11, 'Q'): (4, 28, 2, 28), (12, 'Q'): (4, 26, 2, 26),
    (13, 'Q'): (4, 24, 2, 24), (14, 'Q'): (4, 20, 2, 20), (15, 'Q'): (6, 24, 2, 24),
    (16, 'Q'): (6, 28, 2, 28), (17, 'Q'): (6, 24, 2, 24), (18, 'Q'): (6, 28, 2, 28),
    (19, 'Q'): (6, 26, 2, 26), (20, 'Q'): (6, 30, 2, 30), (21, 'Q'): (6, 28, 2, 28),
    (22, 'Q'): (6, 30, 2, 30), (23, 'Q'): (6, 30, 2, 30), (24, 'Q'): (6, 30, 2, 30),
    (25, 'Q'): (6, 30, 2, 30), (26, 'Q'): (6, 30, 2, 30), (27, 'Q'): (6, 30, 2, 30),
    (28, 'Q'): (6, 30, 2, 30), (29, 'Q'): (6, 30, 2, 30), (30, 'Q'): (6, 30, 2, 30),
    (31, 'Q'): (6, 30, 2, 30), (32, 'Q'): (6, 30, 2, 30), (33, 'Q'): (6, 30, 2, 30),
    (34, 'Q'): (6, 30, 2, 30), (35, 'Q'): (6, 30, 2, 30), (36, 'Q'): (6, 30, 2, 30),
    (37, 'Q'): (6, 30, 2, 30), (38, 'Q'): (6, 30, 2, 30), (39, 'Q'): (6, 30, 2, 30),
    (40, 'Q'): (6, 30, 2, 30),
    
    # Level H (30% recovery)
    (1, 'H'): (1, 17, 0, 0), (2, 'H'): (1, 28, 1, 28), (3, 'H'): (2, 22, 2, 22),
    (4, 'H'): (4, 16, 4, 16), (5, 'H'): (4, 18, 4, 18), (6, 'H'): (4, 24, 4, 24),
    (7, 'H'): (4, 18, 4, 18), (8, 'H'): (4, 22, 4, 22), (9, 'H'): (4, 20, 4, 20),
    (10, 'H'): (4, 24, 4, 24), (11, 'H'): (4, 28, 4, 28), (12, 'H'): (4, 26, 4, 26),
    (13, 'H'): (4, 24, 4, 24), (14, 'H'): (4, 20, 4, 20), (15, 'H'): (6, 24, 4, 24),
    (16, 'H'): (6, 28, 4, 28), (17, 'H'): (6, 24, 4, 24), (18, 'H'): (6, 28, 4, 28),
    (19, 'H'): (6, 26, 4, 26), (20, 'H'): (6, 30, 4, 30), (21, 'H'): (6, 28, 4, 28),
    (22, 'H'): (6, 30, 4, 30), (23, 'H'): (6, 30, 4, 30), (24, 'H'): (6, 30, 4, 30),
    (25, 'H'): (6, 30, 4, 30), (26, 'H'): (6, 30, 4, 30), (27, 'H'): (6, 30, 4, 30),
    (28, 'H'): (6, 30, 4, 30), (29, 'H'): (6, 30, 4, 30), (30, 'H'): (6, 30, 4, 30),
    (31, 'H'): (6, 30, 4, 30), (32, 'H'): (6, 30, 4, 30), (33, 'H'): (6, 30, 4, 30),
    (34, 'H'): (6, 30, 4, 30), (35, 'H'): (6, 30, 4, 30), (36, 'H'): (6, 30, 4, 30),
    (37, 'H'): (6, 30, 4, 30), (38, 'H'): (6, 30, 4, 30), (39, 'H'): (6, 30, 4, 30),
    (40, 'H'): (6, 30, 4, 30),
}


def _total_ecc_codewords(version: int, ecc_level: str) -> int:
    """
    Calculate total ECC codewords for given version and error correction level.
    
    Args:
        version (int): QR code version (1-40)
        ecc_level (str): Error correction level ('L', 'M', 'Q', 'H')
        
    Returns:
        int: Total number of ECC codewords, or 0 if not found in table
    """
    ecc = (ecc_level or 'M').upper()
    key = (version, ecc)
    
    if key in _ECC_TABLE:
        g1_blocks, ecc_per_block_g1, g2_blocks, ecc_per_block_g2 = _ECC_TABLE[key]
        return g1_blocks * ecc_per_block_g1 + g2_blocks * ecc_per_block_g2
    
    return 0


def _data_modules_coords(size: int, func_mask: List[List[bool]]) -> List[Tuple[int, int]]:
    """
    Get coordinates of non-functional modules in standard QR placement order.
    
    QR codes place data in a zigzag pattern from right to left, skipping column 6
    (timing pattern). This function returns coordinates in that exact order.
    
    Args:
        size (int): QR code size in modules
        func_mask (List[List[bool]]): Functional area mask
        
    Returns:
        List[Tuple[int, int]]: List of (row, col) coordinates in placement order
    """
    coords = []
    upward = True
    col = size - 1
    
    while col > 0:
        if col == 6:  # Skip timing pattern column
            col -= 1
            
        for i in range(size):
            r = (size - 1 - i) if upward else i
            # Process pair of columns [col, col-1]
            for c in (col, col - 1):
                if 0 <= r < size and 0 <= c < size and not func_mask[r][c]:
                    coords.append((r, c))
                    
        upward = not upward
        col -= 2
        
    return coords


def render_colored_png_from_matrix(
    matrix: List[List[bool]],
    version: int,
    border: int = 4,
    scale: int = 6,
    ecc: str = 'M'
) -> Tuple[str, Dict[str, Any]]:
    """
    Render QR code matrix as colored PNG with zone-based analysis.
    
    This function creates a PNG image where different QR code zones are colored
    differently to help understand the structure. It distinguishes between
    functional areas (finder patterns, timing, etc.) and data areas (payload vs ECC).
    
    Args:
        matrix (List[List[bool]]): QR code matrix (True=dark, False=light)
        version (int): QR code version (1-40)
        border (int): Quiet zone size in modules (recommended: 4+)
        scale (int): Pixel size per module
        ecc (str): Error correction level for ECC zone calculation
        
    Returns:
        Tuple[str, Dict[str, Any]]: (base64_png, metrics_dict)
            - base64_png: Base64-encoded PNG image
            - metrics_dict: Contains size, module counts, etc.
            
    Example:
        >>> matrix = [[True, False, True], [False, True, False], [True, False, True]]
        >>> b64, metrics = render_colored_png_from_matrix(matrix, version=1, ecc='M')
        >>> print(f"Generated {metrics['size']}x{metrics['size']} QR code")
    """
    rows = list(matrix)
    size = len(rows)
    
    # Build functional area masks
    func_mask, sep_mask = build_function_mask(size, version)
    
    # Calculate basic metrics
    total_modules = size * size
    functional_count = sum(sum(1 for c in row if c) for row in func_mask)
    data_modules_est = total_modules - functional_count
    
    # Determine data vs ECC module positions
    coords = _data_modules_coords(size, func_mask)
    total_cw_est = data_modules_est // 8
    ecc_cw_total = _total_ecc_codewords(version, ecc)
    data_cw = max(0, total_cw_est - ecc_cw_total)
    data_bits = data_cw * 8
    
    # Set of positions considered 'data' (first bits placed)
    data_positions = set(coords[:data_bits])
    
    # Create output image
    img_px = (size + 2 * border) * scale
    img = Image.new('RGB', (img_px, img_px), PALETTE['background'])
    draw = ImageDraw.Draw(img)
    
    dark_modules = 0
    
    # Pre-calculate positions for efficiency
    finder_positions = [(0, 0), (0, size - 7), (size - 7, 0)]
    alignment_centers = compute_alignment_centers(version)
    
    # Render each module
    for r in range(size):
        for c in range(size):
            is_dark = bool(rows[r][c])
            x0 = (c + border) * scale
            y0 = (r + border) * scale
            x1 = x0 + scale - 1
            y1 = y0 + scale - 1
            
            # Draw separator zones (light gray where module is light)
            if sep_mask[r][c] and not is_dark:
                draw.rectangle([x0, y0, x1, y1], fill=PALETTE['separator'])
                continue
                
            if not is_dark:
                continue
                
            dark_modules += 1
            
            # Color functional areas
            if func_mask[r][c]:
                # Finder patterns (purple)
                in_finder = False
                for (r0, c0) in finder_positions:
                    if r0 <= r < r0 + 7 and c0 <= c < c0 + 7:
                        draw.rectangle([x0, y0, x1, y1], fill=PALETTE['finder'])
                        in_finder = True
                        break
                if in_finder:
                    continue
                
                # Alignment patterns (teal)
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
                
                # Timing patterns (orange)
                if r == 6 or c == 6:
                    draw.rectangle([x0, y0, x1, y1], fill=PALETTE['timing'])
                    continue
                
                # Format information (red)
                if (r == 8 or c == 8) or (r < 9 and c < 9) or (c >= size - 8 and r < 9):
                    draw.rectangle([x0, y0, x1, y1], fill=PALETTE['format'])
                    continue
                
                # Version information (dark red, v≥7)
                if version >= 7 and ((r < 6 and c >= size - 11) or (r >= size - 11 and c < 6)):
                    draw.rectangle([x0, y0, x1, y1], fill=PALETTE['version'])
                    continue
            
            # Color non-functional areas: data vs ECC
            if (r, c) in data_positions:
                fill = PALETTE['data']
            else:
                # If no ECC table entry, paint everything as data (safe fallback)
                fill = PALETTE['ecc'] if ecc_cw_total > 0 else PALETTE['data']
            draw.rectangle([x0, y0, x1, y1], fill=fill)
    
    # Encode PNG to base64
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


def render_colored_svg_from_matrix(
    matrix: List[List[bool]],
    version: int,
    border: int = 4,
    scale: int = 10,
    ecc: str = 'M'
) -> bytes:
    """
    Render QR code matrix as colored SVG with zone-based analysis.
    
    Similar to render_colored_png_from_matrix but outputs SVG format for
    scalable vector graphics. Useful for high-quality printing and web display.
    
    Args:
        matrix (List[List[bool]]): QR code matrix (True=dark, False=light)
        version (int): QR code version (1-40)
        border (int): Quiet zone size in modules
        scale (int): Pixel size per module
        ecc (str): Error correction level for ECC zone calculation
        
    Returns:
        bytes: UTF-8 encoded SVG content
        
    Example:
        >>> matrix = [[True, False, True], [False, True, False], [True, False, True]]
        >>> svg_bytes = render_colored_svg_from_matrix(matrix, version=1, ecc='M')
        >>> with open('qr_colored.svg', 'wb') as f:
        ...     f.write(svg_bytes)
    """
    rows = list(matrix)
    size = len(rows)
    
    # Build functional area masks
    func_mask, sep_mask = build_function_mask(size, version)
    
    # Calculate data vs ECC positions
    total_modules = size * size
    functional_count = sum(sum(1 for c in row if c) for row in func_mask)
    data_modules_est = total_modules - functional_count
    
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
    
    # Pre-calculate positions
    finder_positions = [(0, 0), (0, size - 7), (size - 7, 0)]
    alignment_centers = compute_alignment_centers(version)
    
    # Draw separators (where module is light)
    for r in range(size):
        for c in range(size):
            if sep_mask[r][c] and not rows[r][c]:
                x = (c + border) * scale
                y = (r + border) * scale
                out.append(f'<rect x="{x}" y="{y}" width="{scale}" height="{scale}" fill="rgb{PALETTE["separator"]}"/>')
    
    # Draw dark modules with zone coloring
    for r in range(size):
        for c in range(size):
            if not rows[r][c]:
                continue
                
            # Determine color based on functional area
            fill = None
            if func_mask[r][c]:
                # Finder patterns
                for (r0, c0) in finder_positions:
                    if r0 <= r < r0 + 7 and c0 <= c < c0 + 7:
                        fill = PALETTE['finder']
                        break
                if fill is None:
                    # Alignment patterns
                    aligned = False
                    for cy in alignment_centers:
                        for cx in alignment_centers:
                            if (cy - 2) <= r <= (cy + 2) and (cx - 2) <= c <= (cx + 2):
                                fill = PALETTE['alignment']
                                aligned = True
                                break
                        if aligned:
                            break
                if fill is None:
                    # Timing patterns
                    if r == 6 or c == 6:
                        fill = PALETTE['timing']
                if fill is None:
                    # Format information
                    if (r == 8 or c == 8) or (r < 9 and c < 9) or (c >= size - 8 and r < 9):
                        fill = PALETTE['format']
                if fill is None and version >= 7:
                    # Version information
                    if (r < 6 and c >= size - 11) or (r >= size - 11 and c < 6):
                        fill = PALETTE['version']
                if fill is None:
                    # Fallback to data color
                    fill = PALETTE['data']
            else:
                # Non-functional: data vs ECC
                fill = PALETTE['data'] if (r, c) in data_positions else (PALETTE['ecc'] if ecc_cw_total > 0 else PALETTE['data'])
            
            # Draw the rectangle
            x = (c + border) * scale
            y = (r + border) * scale
            out.append(f'<rect x="{x}" y="{y}" width="{scale}" height="{scale}" fill="rgb{fill}"/>')
    
    out.append('</svg>')
    return "\n".join(out).encode("utf-8")
