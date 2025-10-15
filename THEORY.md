# QR Code Theory and Implementation

This document provides a comprehensive overview of QR code theory, structure, and the implementation details used in QR Generator Advanced.

## Table of Contents

1. [QR Code Overview](#qr-code-overview)
2. [QR Code Structure](#qr-code-structure)
3. [Error Correction](#error-correction)
4. [Encoding Modes](#encoding-modes)
5. [Mask Patterns](#mask-patterns)
6. [Penalty Evaluation](#penalty-evaluation)
7. [Implementation Details](#implementation-details)
8. [References](#references)

## QR Code Overview

QR (Quick Response) codes are two-dimensional barcodes that can store various types of data. They were invented by Denso Wave in 1994 and are standardized by ISO/IEC 18004.

### Key Characteristics

- **High Capacity**: Can store up to 4,296 alphanumeric characters
- **Error Correction**: Built-in Reed-Solomon error correction
- **Fast Reading**: Can be read from any angle
- **Robust**: Can be read even with up to 30% damage (depending on error correction level)

### QR Code Versions

QR codes come in 40 different versions, each with a different size:

- **Version 1**: 21×21 modules
- **Version 2**: 25×25 modules
- **Version 40**: 177×177 modules

Each version adds 4 modules per side, so version N has size = 21 + (N-1) × 4.

## QR Code Structure

A QR code consists of several functional areas:

### 1. Finder Patterns (3 corners)

```
████████
█      █
█ ████ █
█ ████ █
█ ████ █
█      █
████████
```

- Located at three corners (top-left, top-right, bottom-left)
- 7×7 modules each
- Used for orientation and position detection
- Surrounded by 1-module separator (light border)

### 2. Timing Patterns

- Horizontal timing pattern in row 6
- Vertical timing pattern in column 6
- Alternating dark/light modules
- Used to determine module size and correct for distortion

### 3. Alignment Patterns (Version 2+)

```
█████
█   █
█ █ █
█   █
█████
```

- 5×5 modules
- Positioned at calculated centers
- Used for perspective correction
- Not present in version 1

### 4. Format Information

- 15 bits containing:
  - Error correction level (2 bits)
  - Mask pattern (3 bits)
  - Error correction for format info (10 bits)
- Located around finder patterns and in timing areas

### 5. Version Information (Version 7+)

- 18 bits containing version number
- Two 3×6 blocks: top-right and bottom-left
- Only present in versions 7-40

### 6. Data and Error Correction

- Remaining modules contain:
  - Data codewords (your actual information)
  - Error correction codewords (Reed-Solomon codes)
- Placed in zigzag pattern from right to left, skipping column 6

## Error Correction

QR codes use Reed-Solomon error correction to recover from damage. Four levels are available:

### Error Correction Levels

| Level | Recovery Capability | Approximate Capacity Reduction |
|-------|-------------------|-------------------------------|
| L     | ~7%               | 7%                            |
| M     | ~15%              | 15%                           |
| Q     | ~25%              | 25%                           |
| H     | ~30%              | 30%                           |

### Reed-Solomon Implementation

- Data is divided into blocks
- Each block gets error correction codewords
- Higher versions may have multiple groups with different ECC counts
- Can recover from both random errors and burst errors

### Example: Version 6, Level M

- **Group 1**: 4 blocks, 16 ECC codewords each
- **Group 2**: 4 blocks, 16 ECC codewords each
- **Total ECC**: 4×16 + 4×16 = 128 codewords

## Encoding Modes

QR codes support four encoding modes:

### 1. Numeric Mode (0-9)

- **Efficiency**: 3.33 bits per digit
- **Capacity**: Up to 7,089 digits
- **Use case**: Phone numbers, IDs, numeric data

### 2. Alphanumeric Mode (0-9, A-Z, and 9 symbols)

- **Efficiency**: 5.5 bits per character
- **Capacity**: Up to 4,296 characters
- **Use case**: URLs, text with limited character set

### 3. Byte Mode (Any 8-bit data)

- **Efficiency**: 8 bits per byte
- **Capacity**: Up to 2,953 bytes
- **Use case**: UTF-8 text, binary data, EMVCo payloads

### 4. Kanji Mode (Shift-JIS)

- **Efficiency**: 13 bits per character
- **Capacity**: Up to 1,817 characters
- **Use case**: Japanese text

### Mode Selection

The encoder automatically selects the most efficient mode, but you can force a specific mode for compatibility reasons.

## Mask Patterns

Mask patterns are applied to the data area to avoid problematic patterns and improve readability. Eight mask patterns are available (0-7).

### Mask Pattern Formulas

| Pattern | Formula | Description |
|---------|---------|-------------|
| 0       | (i + j) mod 2 = 0 | Checkerboard |
| 1       | i mod 2 = 0 | Horizontal stripes |
| 2       | j mod 3 = 0 | Vertical stripes |
| 3       | (i + j) mod 3 = 0 | Diagonal stripes |
| 4       | ((i div 2) + (j div 3)) mod 2 = 0 | Large checkerboard |
| 5       | (i × j) mod 2 + (i × j) mod 3 = 0 | Small checkerboard |
| 6       | ((i × j) mod 2 + (i × j) mod 3) mod 2 = 0 | Alternating |
| 7       | ((i × j) mod 3 + (i + j) mod 2) mod 2 = 0 | Complex pattern |

Where i = row, j = column (0-based)

### Mask Selection

The optimal mask is selected using penalty evaluation (see below).

## Penalty Evaluation

The ISO/IEC 18004 standard defines four penalty rules to evaluate mask quality:

### Rule N1: Adjacent Modules in Runs

Penalizes long runs of consecutive modules of the same color.

- **Formula**: 3 + (run_length - 5) for runs ≥ 5
- **Applied to**: Both horizontal and vertical directions
- **Purpose**: Avoid patterns that are hard to scan

### Rule N2: 2×2 Blocks of Same Color

Penalizes 2×2 blocks where all modules have the same color.

- **Penalty**: 3 points per block
- **Purpose**: Avoid large solid areas

### Rule N3: Finder-like Patterns

Penalizes patterns that resemble finder patterns.

- **Pattern**: 1:1:3:1:1 (dark:light:dark:dark:dark:light:dark)
- **Penalty**: 40 points per occurrence
- **Requirement**: Must be surrounded by ≥4 light modules
- **Purpose**: Avoid confusion with actual finder patterns

### Rule N4: Dark/Light Module Ratio

Penalizes deviation from 50% dark modules.

- **Formula**: 10 × floor(abs(ratio - 50) / 5)
- **Purpose**: Encourage balanced distribution

### Total Penalty

The mask with the lowest total penalty (N1 + N2 + N3 + N4) is selected.

## Implementation Details

### Data Placement Order

Data is placed in a zigzag pattern:

1. Start from bottom-right corner
2. Move upward in pairs of columns
3. Skip column 6 (timing pattern)
4. Alternate direction for each row
5. Continue until all data is placed

### ECI (Extended Channel Interpretation)

ECI allows specifying character encoding explicitly:

- **ECI True**: Adds ECI header with encoding identifier
- **ECI False**: Assumes ISO-8859-1 encoding
- **Use case**: UTF-8 text, international characters

### Micro QR Codes

Smaller version of QR codes with reduced capacity:

- **M1**: 11×11 modules, numeric only
- **M2**: 13×13 modules, alphanumeric
- **M3**: 15×15 modules, byte mode
- **M4**: 17×17 modules, full features

## References

### Standards

- **ISO/IEC 18004:2015**: Information technology — Automatic identification and data capture techniques — QR Code bar code symbology specification
- **EMVCo QR Code Specification**: For payment QR codes

### Technical Resources

- **Segno Library**: Python QR code generation library
- **QR Code Generator**: Online QR code tools
- **Reed-Solomon Codes**: Error correction theory

### Implementation Notes

This implementation uses the Segno library for core QR generation and implements custom visualization and analysis features. The penalty evaluation follows ISO/IEC 18004:2015 specifications exactly.

### Yape Integration

The original use case was Yape QR regeneration, which uses:
- **Error Correction**: Level M (15%)
- **Mask Pattern**: 2 (vertical stripes)
- **Encoding Mode**: Byte
- **Character Set**: UTF-8
- **ECI**: True

This configuration ensures compatibility with Yape's payment system while maintaining optimal readability.
