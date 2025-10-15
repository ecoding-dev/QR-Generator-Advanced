# QR Generator Advanced

A comprehensive QR code generator with advanced configuration options and detailed analysis capabilities. Originally developed for Yape QR regeneration, this tool has evolved into a general-purpose QR code generation platform with professional-grade features.

![QR Generator Advanced](https://img.shields.io/badge/QR-Generator%20Advanced-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8+-green?style=flat-square)
![Flask](https://img.shields.io/badge/Flask-3.0+-red?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

## 🚀 Features

### Core Functionality
- **Advanced QR Generation**: Full control over all QR code parameters
- **Visual Analysis**: Zone-based coloring to understand QR structure
- **Multiple Export Formats**: PNG, JPG, SVG (both monochrome and colored)
- **Mask Optimization**: Automatic selection of optimal mask patterns
- **Real-time Preview**: Instant generation with parameter adjustment

### Technical Capabilities
- **Error Correction Levels**: L (7%), M (15%), Q (25%), H (30%)
- **Encoding Modes**: Byte, Alphanumeric, Numeric, Kanji
- **Version Control**: Auto-selection or manual version specification (1-40)
- **Character Encoding**: UTF-8, ISO-8859-1, and custom encodings
- **ECI Support**: Extended Channel Interpretation for proper encoding declaration

### Analysis Features
- **Zone Visualization**: Color-coded functional areas (finder, timing, alignment, format, version)
- **Data vs ECC Separation**: Distinguish between payload and error correction data
- **Mask Evaluation**: ISO/IEC 18004 compliant penalty scoring
- **Metrics Display**: Module counts, ratios, and optimization suggestions

## 📋 Requirements

- Python 3.8 or higher
- Flask 3.0+
- Segno 1.6+
- Pillow 10.0+

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ecoding-dev/QR-Generator-Advanced.git
   cd qr-generator-advanced
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Open your browser**
   Navigate to `http://localhost:5000`

## 🎯 Usage

### Web Interface

The web interface provides an intuitive way to generate QR codes:

1. **Enter your data** in the text field (URL, text, or EMVCo payload)
2. **Configure parameters**:
   - Error Correction Level (recommended: M for Yape)
   - Version (Auto for optimal size)
   - Encoding Mode (Byte for maximum compatibility)
3. **Advanced options**:
   - Character encoding
   - ECI settings
   - Mask pattern (Auto for optimization)
   - Quiet zone size
4. **Generate and analyze** your QR code
5. **Export** in your preferred format

### Example: Yape QR Generation

```python
from core.qr_generator import make_qr

# Generate Yape-style QR code
yape_payload = "00020101021243650016COM.MERCADOLIVRE02008..."
qr = make_qr(
    text=yape_payload,
    ecc='M',           # 15% error correction
    mask=2,            # Yape uses mask pattern 2
    mode='byte',       # Byte mode for EMVCo
    encoding='utf-8',
    eci=True
)

# Save as PNG
qr.save('yape_qr.png', scale=10, border=4)
```

### Programmatic Usage

```python
from core.qr_generator import make_qr, evaluate_all_masks
from core.renderer import render_colored_png_from_matrix

# Generate QR code
qr = make_qr("https://example.com", ecc='M', version='auto', mask='auto')

# Analyze mask patterns
best_mask, best_score, all_scores = evaluate_all_masks(
    "https://example.com", ecc='M', version=qr.version,
    mode='byte', encoding='utf-8', eci=True, boost_error=False, micro=False
)

# Create colored visualization
matrix = list(qr.matrix)
b64_image, metrics = render_colored_png_from_matrix(
    matrix, qr.version, border=4, scale=6, ecc='M'
)
```

## 📊 QR Code Structure

The application provides detailed visualization of QR code components:

- **🟣 Finder Patterns**: Three corner patterns for orientation
- **🟠 Timing Patterns**: Alternating pattern for module size detection
- **🔵 Alignment Patterns**: Correction patterns for perspective distortion
- **🔴 Format Information**: Error correction level and mask pattern
- **⚫ Data Modules**: Your actual payload
- **🔵 ECC Modules**: Error correction codes

## 🔧 Configuration

### Environment Variables

- `FLASK_ENV`: Set to `development` for debug mode
- `FLASK_DEBUG`: Enable/disable debug mode
- `PORT`: Server port (default: 5000)

### Customization

The application can be customized by modifying:

- `core/qr_generator.py`: QR generation logic
- `core/renderer.py`: Visualization and coloring
- `templates/index.html`: Web interface
- `app.py`: Flask routes and configuration

## 📚 Documentation

- **[THEORY.md](THEORY.md)**: Comprehensive QR code theory and specifications
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**: Code architecture and design patterns
- **[README.es.md](README.es.md)**: Spanish documentation

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Add tests if applicable
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Add docstrings for all functions
- Include examples in documentation

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Segno Library**: For robust QR code generation
- **Flask Framework**: For the web interface
- **ISO/IEC 18004**: For QR code specifications
- **Yape**: For inspiring the original use case

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/ecoding-dev/QR-Generator-Advanced/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ecoding-dev/QR-Generator-Advanced/discussions)

## 🗺️ Roadmap

- [ ] CLI interface for batch processing
- [ ] API endpoints for programmatic access
- [ ] Additional export formats (PDF, EPS)
- [ ] Batch QR code generation
- [ ] QR code scanning and analysis
- [ ] Custom color schemes
- [ ] Logo embedding support

---

**Made with ❤️ for the QR code community**
