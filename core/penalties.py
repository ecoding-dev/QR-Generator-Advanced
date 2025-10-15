# -*- coding: utf-8 -*-
"""
QR Code Mask Penalty Evaluation Module

This module implements the mask pattern evaluation algorithm according to
ISO/IEC 18004:2015 standard. The algorithm evaluates QR codes with different
mask patterns and assigns penalty scores based on four criteria (N1-N4).
The mask with the lowest total penalty is considered optimal.

Functions:
    penalty_N1: Evaluate adjacent modules in runs (Rule N1)
    penalty_N2: Evaluate 2x2 blocks of same color (Rule N2)  
    penalty_N3: Evaluate finder-like patterns (Rule N3)
    penalty_N4: Evaluate dark/light module ratio (Rule N4)
    compute_mask_penalty: Calculate total penalty score
"""

from typing import List


def penalty_N1(rows: List[List[bool]]) -> int:
    """
    Calculate penalty for adjacent modules in runs (Rule N1).
    
    This rule penalizes long runs of consecutive modules of the same color
    in both horizontal and vertical directions. Runs of 5 or more modules
    receive penalties: 3 + (run_length - 5).
    
    Args:
        rows (List[List[bool]]): QR matrix (True=dark, False=light)
        
    Returns:
        int: Penalty score for rule N1
        
    Example:
        >>> matrix = [[True, True, True, True, True, False]]  # 5 consecutive
        >>> score = penalty_N1(matrix)
        >>> print(score)  # 3 (3 + (5-5))
        
    Note:
        Based on ISO/IEC 18004:2015 section 8.8.2, Rule N1
    """
    score = 0
    n = len(rows)
    
    # Check horizontal runs
    for r in range(n):
        run = 1
        for c in range(1, n):
            if rows[r][c] == rows[r][c-1]:
                run += 1
            else:
                if run >= 5:
                    score += 3 + (run - 5)
                run = 1
        # Check final run in row
        if run >= 5:
            score += 3 + (run - 5)
    
    # Check vertical runs
    for c in range(n):
        run = 1
        for r in range(1, n):
            if rows[r][c] == rows[r-1][c]:
                run += 1
            else:
                if run >= 5:
                    score += 3 + (run - 5)
                run = 1
        # Check final run in column
        if run >= 5:
            score += 3 + (run - 5)
    
    return score


def penalty_N2(rows: List[List[bool]]) -> int:
    """
    Calculate penalty for 2x2 blocks of same color (Rule N2).
    
    This rule penalizes 2x2 blocks where all four modules have the same color.
    Each such block adds 3 points to the penalty score.
    
    Args:
        rows (List[List[bool]]): QR matrix (True=dark, False=light)
        
    Returns:
        int: Penalty score for rule N2
        
    Example:
        >>> matrix = [[True, True], [True, True]]  # 2x2 dark block
        >>> score = penalty_N2(matrix)
        >>> print(score)  # 3
        
    Note:
        Based on ISO/IEC 18004:2015 section 8.8.2, Rule N2
    """
    score = 0
    n = len(rows)
    
    # Check all 2x2 blocks
    for r in range(n - 1):
        for c in range(n - 1):
            value = rows[r][c]
            # Check if all 4 modules in 2x2 block are same color
            if (rows[r][c+1] == value and 
                rows[r+1][c] == value and 
                rows[r+1][c+1] == value):
                score += 3
    
    return score


def _pattern_1_1_3_1_1(seq: List[int]) -> List[int]:
    """
    Find occurrences of pattern 1:1:3:1:1 in a sequence.
    
    This pattern (dark:light:dark:dark:dark:light:dark) resembles finder patterns
    and is penalized to avoid confusion with actual finder patterns.
    
    Args:
        seq (List[int]): Binary sequence (1=dark, 0=light)
        
    Returns:
        List[int]: List of starting indices where pattern is found
        
    Note:
        Pattern must be surrounded by at least 4 light modules on either side
    """
    indices = []
    n = len(seq)
    pattern = [1, 0, 1, 1, 1, 0, 1]  # 1:1:3:1:1 pattern
    
    for i in range(n - 7 + 1):
        if seq[i:i+7] == pattern:
            # Check left side (at least 4 light modules)
            left_ok = (i >= 4 and all(v == 0 for v in seq[i-4:i]))
            # Check right side (at least 4 light modules)  
            right_ok = (i+7 <= n-4 and all(v == 0 for v in seq[i+7:i+11]))
            
            if left_ok or right_ok:
                indices.append(i)
    
    return indices


def penalty_N3(rows: List[List[bool]]) -> int:
    """
    Calculate penalty for finder-like patterns (Rule N3).
    
    This rule penalizes patterns that resemble finder patterns (1:1:3:1:1 ratio)
    to avoid confusion with actual finder patterns. Each occurrence adds 40 points.
    
    Args:
        rows (List[List[bool]]): QR matrix (True=dark, False=light)
        
    Returns:
        int: Penalty score for rule N3
        
    Example:
        >>> # Pattern: dark-light-dark-dark-dark-light-dark
        >>> matrix = [[True, False, True, True, True, False, True]]
        >>> score = penalty_N3(matrix)
        >>> print(score)  # 40
        
    Note:
        Based on ISO/IEC 18004:2015 section 8.8.2, Rule N3
    """
    score = 0
    n = len(rows)
    
    # Check horizontal patterns
    for r in range(n):
        row = [1 if rows[r][c] else 0 for c in range(n)]
        score += 40 * len(_pattern_1_1_3_1_1(row))
    
    # Check vertical patterns
    for c in range(n):
        col = [1 if rows[r][c] else 0 for r in range(n)]
        score += 40 * len(_pattern_1_1_3_1_1(col))
    
    return score


def penalty_N4(rows: List[List[bool]]) -> int:
    """
    Calculate penalty for dark/light module ratio (Rule N4).
    
    This rule penalizes QR codes where the ratio of dark modules deviates
    significantly from 50%. The penalty is calculated as:
    10 * floor(abs(ratio - 50) / 5)
    
    Args:
        rows (List[List[bool]]): QR matrix (True=dark, False=light)
        
    Returns:
        int: Penalty score for rule N4
        
    Example:
        >>> # Matrix with 75% dark modules
        >>> matrix = [[True, True, True, False]]  # 3/4 = 75%
        >>> score = penalty_N4(matrix)
        >>> print(score)  # 10 * floor(abs(75-50)/5) = 10 * 5 = 50
        
    Note:
        Based on ISO/IEC 18004:2015 section 8.8.2, Rule N4
    """
    n = len(rows)
    total = n * n
    dark = sum(1 for r in range(n) for c in range(n) if rows[r][c])
    
    # Calculate percentage of dark modules
    ratio = dark * 100.0 / total
    
    # Calculate penalty: 10 * floor(abs(ratio - 50) / 5)
    k = int(abs(ratio - 50.0) // 5.0)
    return k * 10


def compute_mask_penalty(matrix_bool: List[List[bool]]) -> int:
    """
    Calculate total mask penalty score for a QR code matrix.
    
    This function combines all four penalty rules (N1-N4) to determine
    the overall quality score of a QR code with a specific mask pattern.
    Lower scores indicate better visual quality and easier scanning.
    
    Args:
        matrix_bool (List[List[bool]]): QR matrix (True=dark, False=light)
        
    Returns:
        int: Total penalty score (lower is better)
        
    Example:
        >>> matrix = [[True, False, True], [False, True, False], [True, False, True]]
        >>> total_penalty = compute_mask_penalty(matrix)
        >>> print(f"Total penalty: {total_penalty}")
        
    Note:
        Based on ISO/IEC 18004:2015 section 8.8.2
        The mask with the lowest total penalty should be selected
    """
    # Convert to boolean matrix if needed
    rows = [[bool(v) for v in row] for row in matrix_bool]
    
    # Calculate all penalty components
    n1_score = penalty_N1(rows)
    n2_score = penalty_N2(rows)
    n3_score = penalty_N3(rows)
    n4_score = penalty_N4(rows)
    
    # Return total penalty
    return n1_score + n2_score + n3_score + n4_score


# Reference information for understanding penalty rules
"""
ISO/IEC 18004:2015 Mask Penalty Rules Summary:

N1 - Adjacent modules in runs:
    - Penalizes consecutive modules of same color
    - Formula: 3 + (run_length - 5) for runs ≥ 5
    - Applied to both horizontal and vertical directions

N2 - 2x2 blocks of same color:
    - Penalizes 2x2 blocks where all modules are same color
    - Each block adds 3 points to penalty

N3 - Finder-like patterns:
    - Penalizes 1:1:3:1:1 patterns (dark:light:dark:dark:dark:light:dark)
    - Each occurrence adds 40 points
    - Must be surrounded by ≥4 light modules on either side

N4 - Dark/light module ratio:
    - Penalizes deviation from 50% dark modules
    - Formula: 10 * floor(abs(ratio - 50) / 5)
    - Encourages balanced distribution

The mask pattern (0-7) with the lowest total penalty is selected as optimal.
"""
