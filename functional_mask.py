# -*- coding: utf-8 -*-

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

    # Finder 7x7 (3 esquinas)
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

    # Timing patterns
    for i in range(size):
        func[6][i] = True
        func[i][6] = True

    # Alignment 5x5
    centers = compute_alignment_centers(version)
    for cy in centers:
        for cx in centers:
            if (cy <= 6 and cx <= 6) or (cy <= 6 and cx >= size-7) or (cy >= size-7 and cx <= 6):
                continue
            for r in range(cy-2, cy+3):
                for c in range(cx-2, cx+3):
                    if 0 <= r < size and 0 <= c < size:
                        func[r][c] = True

    # Format info
    for i in range(0, 9):
        if i < size:
            func[8][i] = True
            func[i][8] = True
            func[8][size-1-i] = True

    # Version info (v >= 7)
    if version >= 7:
        for r in range(0,6):
            for c in range(size-11, size-8):
                func[r][c] = True
        for r in range(size-11, size-8):
            for c in range(0,6):
                func[r][c] = True

    return func, sep
