# -*- coding: utf-8 -*-
"""
QR Code Functional Areas Module

This module provides functionality to identify and analyze the functional areas
of QR codes according to ISO/IEC 18004 standard. Functional areas include
finder patterns, timing patterns, alignment patterns, format information,
and version information.

Functions:
    compute_alignment_centers: Calculate alignment pattern center positions
    build_function_mask: Build masks for functional and separator areas
"""

from typing import List, Tuple


def compute_alignment_centers(version: int) -> List[int]:
    """
    Calculate the center positions of alignment patterns for a given QR version.
    
    Alignment patterns are 5x5 modules used to correct for perspective distortion
    in QR codes. They are placed at specific positions based on the QR version.
    Version 1 has no alignment patterns.
    
    Args:
        version (int): QR code version (1-40)
        
    Returns:
        List[int]: List of center coordinates for alignment patterns
        
    Example:
        >>> centers = compute_alignment_centers(7)
        >>> print(centers)  # [6, 22, 38]
        
    Note:
        Algorithm based on ISO/IEC 18004:2015 section 7.3.5
    """
    if version == 1:
        return []
    
    # Calculate QR code size
    size = 21 + (version - 1) * 4
    
    # Number of alignment patterns per row/column
    num = version // 7 + 2
    
    # First and last positions (fixed)
    first = 6
    last = size - 7
    
    if num == 2:
        return [first, last]
    
    # Calculate intermediate positions
    step = (last - first) / (num - 1)
    centers = [int(round(first + i * step)) for i in range(num)]
    
    return centers


def build_function_mask(size: int, version: int) -> Tuple[List[List[bool]], List[List[bool]]]:
    """
    Build masks identifying functional and separator areas in QR codes.
    
    This function creates two boolean matrices:
    1. func_mask: Identifies all functional modules (finder, timing, alignment, format, version)
    2. sep_mask: Identifies separator areas (visual boundaries around finder patterns)
    
    Args:
        size (int): QR code size in modules (21 for v1, 25 for v2, etc.)
        version (int): QR code version (1-40)
        
    Returns:
        Tuple[List[List[bool]], List[List[bool]]]: (func_mask, sep_mask)
            - func_mask[r][c] = True if module (r,c) is functional
            - sep_mask[r][c] = True if module (r,c) is in separator area
            
    Example:
        >>> func_mask, sep_mask = build_function_mask(21, 1)
        >>> print(f"Functional modules: {sum(sum(row) for row in func_mask)}")
        
    Note:
        Based on ISO/IEC 18004:2015 functional pattern specifications
    """
    # Initialize masks
    func_mask = [[False] * size for _ in range(size)]
    sep_mask = [[False] * size for _ in range(size)]
    
    # 1. FINDER PATTERNS (7x7 modules at 3 corners)
    # Pattern: 1111111
    #          1000001  
    #          1011101
    #          1011101
    #          1011101
    #          1000001
    #          1111111
    finder_positions = [(0, 0), (0, size - 7), (size - 7, 0)]
    
    for (r0, c0) in finder_positions:
        # Mark 7x7 finder pattern as functional
        for r in range(r0, r0 + 7):
            for c in range(c0, c0 + 7):
                if 0 <= r < size and 0 <= c < size:
                    func_mask[r][c] = True
        
        # Mark separator area (1-module border around finder)
        for r in range(r0 - 1, r0 + 8):
            for c in range(c0 - 1, c0 + 8):
                if 0 <= r < size and 0 <= c < size:
                    # Only mark as separator if outside the 7x7 finder area
                    if r < r0 or r > r0 + 6 or c < c0 or c > c0 + 6:
                        sep_mask[r][c] = True
    
    # 2. TIMING PATTERNS (alternating pattern in row 6 and column 6)
    # These help scanners determine module size and correct for distortion
    for i in range(size):
        func_mask[6][i] = True  # Row 6
        func_mask[i][6] = True  # Column 6
    
    # 3. ALIGNMENT PATTERNS (5x5 modules, v2+)
    # Pattern: 11111
    #          10001
    #          10101  
    #          10001
    #          11111
    centers = compute_alignment_centers(version)
    
    for cy in centers:
        for cx in centers:
            # Skip if alignment would overlap with finder patterns
            if (cy <= 6 and cx <= 6) or (cy <= 6 and cx >= size - 7) or (cy >= size - 7 and cx <= 6):
                continue
                
            # Mark 5x5 alignment pattern as functional
            for r in range(cy - 2, cy + 3):
                for c in range(cx - 2, cx + 3):
                    if 0 <= r < size and 0 <= c < size:
                        func_mask[r][c] = True
    
    # 4. FORMAT INFORMATION (15 bits in specific positions)
    # Contains error correction level and mask pattern info
    # Positions: around top-left finder, and in timing pattern areas
    
    # Top-left area (around finder pattern)
    for i in range(0, 9):
        if i < size:
            func_mask[8][i] = True      # Row 8, columns 0-8
            func_mask[i][8] = True      # Column 8, rows 0-8
            func_mask[8][size - 1 - i] = True  # Row 8, right side
    
    # 5. VERSION INFORMATION (18 bits, v7+)
    # Contains version number for versions 7-40
    if version >= 7:
        # Two 3x6 blocks: top-right and bottom-left
        for r in range(0, 6):
            for c in range(size - 11, size - 8):
                func_mask[r][c] = True
        for r in range(size - 11, size - 8):
            for c in range(0, 6):
                func_mask[r][c] = True
    
    return func_mask, sep_mask


# ASCII diagram showing QR code structure (for documentation)
"""
QR Code Structure (Version 2 example, 25x25 modules):

   0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4
 0 F F F F F F F S S S S S S S S S S S S S S S S S S
 1 F F F F F F F S S S S S S S S S S S S S S S S S S  
 2 F F F F F F F S S S S S S S S S S S S S S S S S S
 3 F F F F F F F S S S S S S S S S S S S S S S S S S
 4 F F F F F F F S S S S S S S S S S S S S S S S S S
 5 F F F F F F F S S S S S S S S S S S S S S S S S S
 6 F F F F F F F T T T T T T T T T T T T T T T T T T
 7 S S S S S S S T D D D D D D D D D D D D D D D D D
 8 S S S S S S S T D D D D D D D D D D D D D D D D D
 9 S S S S S S S T D D D D D D D D D D D D D D D D D
10 S S S S S S S T D D D D D D D D D D D D D D D D D
11 S S S S S S S T D D D D D D D D D D D D D D D D D
12 S S S S S S S T D D D D D D D D D D D D D D D D D
13 S S S S S S S T D D D D D D D D D D D D D D D D D
14 S S S S S S S T D D D D D D D D D D D D D D D D D
15 S S S S S S S T D D D D D D D D D D D D D D D D D
16 S S S S S S S T D D D D D D D D D D D D D D D D D
17 S S S S S S S T D D D D D D D D D D D D D D D D D
18 S S S S S S S T D D D D D D D D D D D D D D D D D
19 S S S S S S S T D D D D D D D D D D D D D D D D D
20 S S S S S S S T D D D D D D D D D D D D D D D D D
21 S S S S S S S T D D D D D D D D D D D D D D D D D
22 S S S S S S S T D D D D D D D D D D D D D D D D D
23 S S S S S S S T T T T T T T T T T T T T T T T T T
24 S S S S S S S S S S S S S S S S S S S S S S S S S

Legend:
F = Finder pattern (7x7)
S = Separator (1-module border around finders)  
T = Timing pattern (row/column 6)
A = Alignment pattern (5x5, v2+)
D = Data/ECC area
V = Version information (v7+)
"""
