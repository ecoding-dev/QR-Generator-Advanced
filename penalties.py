# -*- coding: utf-8 -*-

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
    idxs = []
    n = len(seq)
    pat = [1,0,1,1,1,0,1]
    for i in range(n - 7 + 1):
        if seq[i:i+7] == pat:
            left_ok = (i >= 4 and all(v == 0 for v in seq[i-4:i]))
            right_ok = (i+7 <= n-4 and all(v == 0 for v in seq[i+7:i+11]))
            if left_ok or right_ok:
                idxs.append(i)
    return idxs

def penalty_N3(rows):
    score = 0
    n = len(rows)
    for r in range(n):
        row = [1 if rows[r][c] else 0 for c in range(n)]
        score += 40 * len(_pattern_1_1_3_1_1(row))
    for c in range(n):
        col = [1 if rows[r][c] else 0 for r in range(n)]
        score += 40 * len(_pattern_1_1_3_1_1(col))
    return score

def penalty_N4(rows):
    n = len(rows)
    total = n * n
    dark = sum(1 for r in range(n) for c in range(n) if rows[r][c])
    ratio = dark * 100.0 / total
    k = int(abs(ratio - 50.0) // 5.0)
    return k * 10

def compute_mask_penalty(matrix_bool):
    """matrix_bool: lista de listas de bool (True=oscuro)."""
    rows = [[bool(v) for v in row] for row in matrix_bool]
    return penalty_N1(rows) + penalty_N2(rows) + penalty_N3(rows) + penalty_N4(rows)
