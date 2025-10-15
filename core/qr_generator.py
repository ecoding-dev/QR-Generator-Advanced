# -*- coding: utf-8 -*-
"""
QR Code Generator Module

This module provides the core functionality for generating QR codes with advanced
configuration options. Originally developed for Yape QR regeneration, it has
evolved into a comprehensive QR code generation tool.

Functions:
    make_qr: Generate QR code with specified parameters
    evaluate_all_masks: Evaluate all mask patterns to find optimal one
"""

import segno
from typing import Optional, Union, Tuple, Dict, Any
from .penalties import compute_mask_penalty


def make_qr(
    text: str,
    ecc: str = 'M',
    version: Optional[Union[int, str]] = None,
    mode: str = 'byte',
    encoding: str = 'utf-8',
    eci: bool = True,
    mask: Union[str, int] = 'auto',
    boost_error: bool = False,
    micro: bool = False
) -> segno.QRCode:
    """
    Generate a QR code symbol with specified parameters.
    
    This function creates a QR code using the segno library with advanced
    configuration options. Originally designed for Yape QR regeneration,
    it supports all standard QR code parameters.
    
    Args:
        text (str): The data to encode in the QR code
        ecc (str): Error correction level ('L', 'M', 'Q', 'H')
            - L: ~7% recovery capability
            - M: ~15% recovery capability (Yape default)
            - Q: ~25% recovery capability  
            - H: ~30% recovery capability
        version (Optional[Union[int, str]]): QR code version (1-40) or 'auto'
            - 'auto': Select minimum version that fits the data
            - int: Force specific version (1=21x21, 40=177x177)
        mode (str): Encoding mode
            - 'byte': Any binary data/UTF-8 (recommended, Yape uses this)
            - 'alphanumeric': A-Z, 0-9, and few symbols (more compact)
            - 'numeric': Digits only (maximum compression)
            - 'kanji': Shift-JIS characters
        encoding (str): Character encoding for byte mode (e.g., 'utf-8', 'iso-8859-1')
        eci (bool): Extended Channel Interpretation
            - True: Add ECI header with encoding info (e.g., UTF-8)
            - False: Assume ISO-8859-1 implicitly
        mask (Union[str, int]): Mask pattern
            - 'auto': Calculate optimal mask using ISO/IEC penalty rules
            - int: Use specific mask pattern (0-7, Yape uses 2)
        boost_error (bool): Automatically increase ECC level if space allows
        micro (bool): Use Micro QR format (M1-M4) instead of standard QR
        
    Returns:
        segno.QRCode: Generated QR code object
        
    Raises:
        ValueError: If parameters are invalid
        segno.DataOverflowError: If data doesn't fit in specified version
        
    Example:
        >>> # Generate Yape-style QR code
        >>> qr = make_qr("00020101021243650016COM.MERCADOLIVRE02008...", 
        ...              ecc='M', mask=2, mode='byte')
        >>> 
        >>> # Generate with auto-optimization
        >>> qr = make_qr("https://example.com", ecc='M', version='auto', mask='auto')
    """
    # Convert mask parameter: 'auto' -> None, otherwise int
    mask_arg = None if mask == 'auto' else int(mask)
    
    # Convert version parameter: 'auto' or None -> None, otherwise int
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


def evaluate_all_masks(
    text: str,
    ecc: str,
    version: int,
    mode: str,
    encoding: str,
    eci: bool,
    boost_error: bool,
    micro: bool
) -> Tuple[int, int, Dict[int, int]]:
    """
    Evaluate all mask patterns (0-7) to find the optimal one.
    
    This function generates QR codes with all possible mask patterns and
    calculates their penalty scores according to ISO/IEC 18004 standard.
    The mask with the lowest penalty score is considered optimal.
    
    Args:
        text (str): The data to encode
        ecc (str): Error correction level ('L', 'M', 'Q', 'H')
        version (int): QR code version (1-40)
        mode (str): Encoding mode ('byte', 'alphanumeric', 'numeric', 'kanji')
        encoding (str): Character encoding for byte mode
        eci (bool): Extended Channel Interpretation flag
        boost_error (bool): Boost error correction flag
        micro (bool): Micro QR format flag
        
    Returns:
        Tuple[int, int, Dict[int, int]]: (best_mask, best_score, all_scores)
            - best_mask: Mask pattern with lowest penalty (0-7)
            - best_score: Penalty score of the best mask
            - all_scores: Dictionary mapping mask -> penalty score
            
    Example:
        >>> best_mask, best_score, scores = evaluate_all_masks(
        ...     "Hello World", ecc='M', version=2, mode='byte',
        ...     encoding='utf-8', eci=True, boost_error=False, micro=False
        ... )
        >>> print(f"Best mask: {best_mask} (score: {best_score})")
        >>> print(f"All scores: {scores}")
    """
    scores = {}
    best_mask = None
    best_score = None
    
    # Evaluate each mask pattern (0-7)
    for mask_pattern in range(8):
        try:
            # Generate QR code with specific mask
            symbol = make_qr(
                text, ecc=ecc, version=version, mode=mode,
                encoding=encoding, eci=eci, mask=mask_pattern,
                boost_error=boost_error, micro=micro
            )
            
            # Convert matrix to list format for penalty calculation
            matrix = list(symbol.matrix)
            penalty_score = compute_mask_penalty(matrix)
            
            scores[mask_pattern] = penalty_score
            
            # Track the best (lowest penalty) mask
            if best_score is None or penalty_score < best_score:
                best_score = penalty_score
                best_mask = mask_pattern
                
        except Exception:
            # If a mask fails, assign high penalty
            scores[mask_pattern] = 999999
    
    return best_mask, best_score, scores
