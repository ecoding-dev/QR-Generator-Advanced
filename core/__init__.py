# -*- coding: utf-8 -*-
"""
QR Generator Advanced - Core Module

This module contains the core functionality for generating and analyzing QR codes
with advanced configuration options.

Modules:
    qr_generator: Main QR code generation functions
    renderer: Visual rendering and coloring of QR codes
    functional_areas: QR code functional pattern detection
    penalties: Mask pattern evaluation algorithms
"""

__version__ = "1.0.0"
__author__ = "QR Generator Advanced Team"

from .qr_generator import make_qr, evaluate_all_masks
from .renderer import render_colored_png_from_matrix, render_colored_svg_from_matrix
from .functional_areas import build_function_mask, compute_alignment_centers
from .penalties import compute_mask_penalty

__all__ = [
    'make_qr',
    'evaluate_all_masks', 
    'render_colored_png_from_matrix',
    'render_colored_svg_from_matrix',
    'build_function_mask',
    'compute_alignment_centers',
    'compute_mask_penalty'
]
