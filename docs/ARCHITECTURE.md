# QR Generator Advanced - Architecture Documentation

This document describes the architecture, design patterns, and code organization of the QR Generator Advanced project.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture Overview](#architecture-overview)
3. [Module Structure](#module-structure)
4. [Data Flow](#data-flow)
5. [Design Patterns](#design-patterns)
6. [Extension Points](#extension-points)
7. [Performance Considerations](#performance-considerations)

## Project Overview

QR Generator Advanced is a Flask-based web application that provides advanced QR code generation capabilities. The project follows a modular architecture with clear separation of concerns.

### Key Design Principles

- **Modularity**: Core functionality is separated into independent modules
- **Extensibility**: Easy to add new features and export formats
- **Maintainability**: Clean code with comprehensive documentation
- **Performance**: Efficient algorithms for mask evaluation and rendering
- **Standards Compliance**: Full adherence to ISO/IEC 18004 specifications

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Interface Layer                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   Flask Routes  │  │   Templates     │  │   Static    │ │
│  │   (app.py)      │  │   (HTML/CSS)    │  │   Assets    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Core Business Logic                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ QR Generator    │  │   Renderer      │  │ Functional  │ │
│  │ (qr_generator)  │  │   (renderer)    │  │   Areas     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│  ┌─────────────────┐                                       │
│  │   Penalties     │                                       │
│  │  (penalties)    │                                       │
│  └─────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    External Dependencies                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │     Segno       │  │     Pillow      │  │    Flask    │ │
│  │  (QR Library)   │  │  (Image Proc)   │  │   (Web)     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Module Structure

### Core Module (`core/`)

The core module contains all business logic and is designed to be framework-agnostic.

#### `core/__init__.py`
- Module initialization and public API definition
- Exports all public functions and classes
- Version information and metadata

#### `core/qr_generator.py`
**Purpose**: QR code generation and parameter management

**Key Functions**:
- `make_qr()`: Main QR generation function with full parameter control
- `evaluate_all_masks()`: Mask pattern optimization

**Design Patterns**:
- **Factory Pattern**: `make_qr()` creates QR objects with different configurations
- **Strategy Pattern**: Different encoding modes and error correction levels
- **Parameter Object**: All parameters passed as individual arguments for clarity

**Dependencies**: `segno`, `penalties`

#### `core/renderer.py`
**Purpose**: Visual rendering and analysis of QR codes

**Key Functions**:
- `render_colored_png_from_matrix()`: PNG generation with zone coloring
- `render_colored_svg_from_matrix()`: SVG generation with zone coloring

**Design Patterns**:
- **Template Method**: Common rendering logic with format-specific implementations
- **Strategy Pattern**: Different color schemes and visualization modes
- **Data Transfer Object**: Metrics dictionary for analysis results

**Dependencies**: `PIL`, `functional_areas`

#### `core/functional_areas.py`
**Purpose**: QR code structure analysis and functional area detection

**Key Functions**:
- `build_function_mask()`: Create masks for functional areas
- `compute_alignment_centers()`: Calculate alignment pattern positions

**Design Patterns**:
- **Algorithm Pattern**: Mathematical calculations for QR structure
- **Immutable Data**: Return new data structures rather than modifying inputs

**Dependencies**: None (pure mathematical functions)

#### `core/penalties.py`
**Purpose**: Mask pattern evaluation according to ISO/IEC standards

**Key Functions**:
- `compute_mask_penalty()`: Calculate total penalty score
- `penalty_N1()` through `penalty_N4()`: Individual penalty rules

**Design Patterns**:
- **Strategy Pattern**: Different penalty calculation strategies
- **Chain of Responsibility**: Each penalty rule is independent
- **Pure Functions**: No side effects, deterministic results

**Dependencies**: None (pure mathematical functions)

### Web Layer (`app.py`)

**Purpose**: Flask web application and HTTP interface

**Key Components**:
- Route handlers for web interface
- Parameter validation and error handling
- File export functionality
- Logging and monitoring

**Design Patterns**:
- **MVC Pattern**: Routes (Controller), Templates (View), Core (Model)
- **Decorator Pattern**: Flask route decorators
- **Error Handling**: Comprehensive exception handling with user-friendly messages

## Data Flow

### QR Generation Flow

```
1. User Input (Web Form)
   ↓
2. Parameter Validation (_read_params)
   ↓
3. QR Generation (make_qr)
   ↓
4. Matrix Extraction (qr.matrix)
   ↓
5. Visualization (render_colored_png_from_matrix)
   ↓
6. Mask Evaluation (evaluate_all_masks)
   ↓
7. Response Assembly (qr_view dictionary)
   ↓
8. Template Rendering (index.html)
```

### Export Flow

```
1. Export Request (GET /export/*)
   ↓
2. Parameter Extraction (_read_params)
   ↓
3. QR Generation (make_qr)
   ↓
4. Format-Specific Rendering
   ├── PNG: segno.save() or custom renderer
   ├── JPG: PIL conversion from PNG
   └── SVG: custom SVG generation
   ↓
5. File Response (send_file)
```

### Mask Evaluation Flow

```
1. QR Generation with Fixed Parameters
   ↓
2. Iterate Through All Masks (0-7)
   ↓
3. Generate QR with Each Mask
   ↓
4. Extract Matrix
   ↓
5. Calculate Penalty (compute_mask_penalty)
   ├── N1: Adjacent modules in runs
   ├── N2: 2x2 blocks of same color
   ├── N3: Finder-like patterns
   └── N4: Dark/light ratio
   ↓
6. Select Best Mask (lowest penalty)
   ↓
7. Return Results
```

## Design Patterns

### 1. Factory Pattern
Used in `make_qr()` to create QR objects with different configurations:

```python
def make_qr(text, ecc='M', version=None, mode='byte', ...):
    # Factory method that creates QR objects based on parameters
    return segno.make(text, error=ecc, version=ver_arg, ...)
```

### 2. Strategy Pattern
Different algorithms for encoding modes, error correction, and mask evaluation:

```python
# Different encoding strategies
modes = ['byte', 'alphanumeric', 'numeric', 'kanji']

# Different error correction strategies  
ecc_levels = ['L', 'M', 'Q', 'H']

# Different penalty calculation strategies
penalty_functions = [penalty_N1, penalty_N2, penalty_N3, penalty_N4]
```

### 3. Template Method Pattern
Common rendering logic with format-specific implementations:

```python
def render_colored_png_from_matrix(matrix, version, border, scale, ecc):
    # Common setup logic
    func_mask, sep_mask = build_function_mask(size, version)
    # ... common processing ...
    
    # Format-specific rendering
    img = Image.new('RGB', (img_px, img_px), PALETTE['background'])
    # ... PNG-specific code ...
```

### 4. Data Transfer Object (DTO)
Structured data transfer between layers:

```python
qr_view = {
    'version': qr_symbol.version,
    'size': metrics['size'],
    'img_b64': b64,
    'ecc': ecc,
    'mask': getattr(qr_symbol, 'mask', None),
    # ... more structured data ...
}
```

## Extension Points

### 1. Adding New Export Formats

To add a new export format (e.g., PDF):

1. Add route handler in `app.py`:
```python
@app.route('/export/pdf', methods=['GET'])
def export_pdf():
    # Implementation
```

2. Add export logic using appropriate library
3. Update template with new export button

### 2. Adding New Visualization Modes

To add new visualization modes:

1. Extend `PALETTE` in `renderer.py`
2. Add new coloring logic in rendering functions
3. Update template to include new visualization options

### 3. Adding New Penalty Rules

To add new penalty evaluation rules:

1. Add new penalty function in `penalties.py`
2. Update `compute_mask_penalty()` to include new rule
3. Update documentation

### 4. Adding New Encoding Modes

To add support for new encoding modes:

1. Check if `segno` library supports the mode
2. Update parameter validation in `_read_params()`
3. Update template with new mode option
4. Add documentation

## Performance Considerations

### 1. Mask Evaluation Optimization

- **Current**: Evaluates all 8 masks for each request
- **Optimization**: Cache results for identical parameters
- **Future**: Background evaluation with WebSocket updates

### 2. Image Rendering

- **Current**: Generates images on-demand
- **Optimization**: Cache rendered images for common parameters
- **Future**: Pre-rendered image library

### 3. Memory Usage

- **Current**: Loads full matrices into memory
- **Optimization**: Stream processing for large QR codes
- **Future**: Lazy loading of matrix data

### 4. Database Integration

- **Current**: Stateless operation
- **Future**: Optional database for:
  - User preferences
  - Generation history
  - Performance metrics

## Code Quality

### 1. Type Hints
All functions include comprehensive type hints for better IDE support and documentation.

### 2. Documentation
- Comprehensive docstrings for all public functions
- Inline comments for complex algorithms
- Architecture documentation (this file)

### 3. Error Handling
- Graceful degradation for unsupported parameters
- User-friendly error messages
- Comprehensive logging

### 4. Testing Strategy
- Unit tests for core mathematical functions
- Integration tests for web interface
- Performance tests for mask evaluation

## Future Enhancements

### 1. API Layer
Add REST API endpoints for programmatic access:

```python
@app.route('/api/v1/generate', methods=['POST'])
def api_generate():
    # JSON API for QR generation
```

### 2. CLI Interface
Add command-line interface for batch processing:

```python
# qr-generator-cli --input file.txt --output dir/ --format png
```

### 3. Plugin System
Allow third-party extensions for:
- Custom export formats
- Advanced visualization modes
- Integration with external services

### 4. Real-time Features
- WebSocket support for real-time updates
- Progress indicators for long operations
- Collaborative editing features

This architecture provides a solid foundation for current functionality while maintaining flexibility for future enhancements.
