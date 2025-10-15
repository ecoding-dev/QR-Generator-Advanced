# QR Generator Advanced

Un generador de códigos QR integral con opciones de configuración avanzadas y capacidades de análisis detallado. Originalmente desarrollado para la regeneración de QRs de Yape, esta herramienta ha evolucionado hasta convertirse en una plataforma de generación de códigos QR de propósito general con características de nivel profesional.

![QR Generator Advanced](https://img.shields.io/badge/QR-Generator%20Advanced-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8+-green?style=flat-square)
![Flask](https://img.shields.io/badge/Flask-3.0+-red?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

## 🚀 Características

### Funcionalidad Principal
- **Generación Avanzada de QR**: Control completo sobre todos los parámetros del código QR
- **Análisis Visual**: Coloreado por zonas para entender la estructura del QR
- **Múltiples Formatos de Exportación**: PNG, JPG, SVG (tanto monocromo como coloreado)
- **Optimización de Máscaras**: Selección automática de patrones de máscara óptimos
- **Vista Previa en Tiempo Real**: Generación instantánea con ajuste de parámetros

### Capacidades Técnicas
- **Niveles de Corrección de Errores**: L (7%), M (15%), Q (25%), H (30%)
- **Modos de Codificación**: Byte, Alfanumérico, Numérico, Kanji
- **Control de Versión**: Auto-selección o especificación manual de versión (1-40)
- **Codificación de Caracteres**: UTF-8, ISO-8859-1, y codificaciones personalizadas
- **Soporte ECI**: Interpretación Extendida de Canal para declaración adecuada de codificación

### Características de Análisis
- **Visualización por Zonas**: Áreas funcionales codificadas por colores (finder, timing, alignment, format, version)
- **Separación Datos vs ECC**: Distinguir entre datos de carga útil y corrección de errores
- **Evaluación de Máscaras**: Puntuación de penalización conforme a ISO/IEC 18004
- **Visualización de Métricas**: Conteos de módulos, ratios y sugerencias de optimización

## 📋 Requisitos

- Python 3.8 o superior
- Flask 3.0+
- Segno 1.6+
- Pillow 10.0+

## 🛠️ Instalación

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/ecoding-dev/QR-Generator-Advanced.git
   cd qr-generator-advanced
   ```

2. **Crear entorno virtual**
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar la aplicación**
   ```bash
   python app.py
   ```

5. **Abrir tu navegador**
   Navega a `http://localhost:5000`

## 🎯 Uso

### Interfaz Web

La interfaz web proporciona una forma intuitiva de generar códigos QR:

1. **Ingresa tus datos** en el campo de texto (URL, texto, o payload EMVCo)
2. **Configura los parámetros**:
   - Nivel de Corrección de Errores (recomendado: M para Yape)
   - Versión (Auto para tamaño óptimo)
   - Modo de Codificación (Byte para máxima compatibilidad)
3. **Opciones avanzadas**:
   - Codificación de caracteres
   - Configuraciones ECI
   - Patrón de máscara (Auto para optimización)
   - Tamaño de zona silenciosa
4. **Genera y analiza** tu código QR
5. **Exporta** en tu formato preferido

### Ejemplo: Generación de QR de Yape

```python
from core.qr_generator import make_qr

# Generar código QR estilo Yape
yape_payload = "00020101021243650016COM.MERCADOLIVRE02008..."
qr = make_qr(
    text=yape_payload,
    ecc='M',           # 15% de corrección de errores
    mask=2,            # Yape usa patrón de máscara 2
    mode='byte',       # Modo byte para EMVCo
    encoding='utf-8',
    eci=True
)

# Guardar como PNG
qr.save('yape_qr.png', scale=10, border=4)
```

### Uso Programático

```python
from core.qr_generator import make_qr, evaluate_all_masks
from core.renderer import render_colored_png_from_matrix

# Generar código QR
qr = make_qr("https://example.com", ecc='M', version='auto', mask='auto')

# Analizar patrones de máscara
best_mask, best_score, all_scores = evaluate_all_masks(
    "https://example.com", ecc='M', version=qr.version,
    mode='byte', encoding='utf-8', eci=True, boost_error=False, micro=False
)

# Crear visualización coloreada
matrix = list(qr.matrix)
b64_image, metrics = render_colored_png_from_matrix(
    matrix, qr.version, border=4, scale=6, ecc='M'
)
```

## 📊 Estructura del Código QR

La aplicación proporciona visualización detallada de los componentes del código QR:

- **🟣 Patrones Finder**: Tres patrones de esquina para orientación
- **🟠 Patrones de Timing**: Patrón alternante para detección de tamaño de módulo
- **🔵 Patrones de Alineación**: Patrones de corrección para distorsión de perspectiva
- **🔴 Información de Formato**: Nivel de corrección de errores y patrón de máscara
- **⚫ Módulos de Datos**: Tu carga útil real
- **🔵 Módulos ECC**: Códigos de corrección de errores

## 🔧 Configuración

### Variables de Entorno

- `FLASK_ENV`: Establecer a `development` para modo debug
- `FLASK_DEBUG`: Habilitar/deshabilitar modo debug
- `PORT`: Puerto del servidor (por defecto: 5000)

### Personalización

La aplicación puede ser personalizada modificando:

- `core/qr_generator.py`: Lógica de generación de QR
- `core/renderer.py`: Visualización y coloreado
- `templates/index.html`: Interfaz web
- `app.py`: Rutas de Flask y configuración

## 📚 Documentación

- **[THEORY.es.md](THEORY.es.md)**: Teoría integral de códigos QR y especificaciones
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**: Arquitectura del código y patrones de diseño
- **[README.md](README.md)**: Documentación en inglés

## 🤝 Contribuir

¡Aceptamos contribuciones! Por favor consulta nuestras [Guías de Contribución](CONTRIBUTING.md) para más detalles.

### Configuración de Desarrollo

1. Hacer fork del repositorio
2. Crear una rama de característica: `git checkout -b feature/amazing-feature`
3. Hacer tus cambios
4. Agregar pruebas si es aplicable
5. Confirmar tus cambios: `git commit -m 'Add amazing feature'`
6. Hacer push a la rama: `git push origin feature/amazing-feature`
7. Abrir un Pull Request

### Estilo de Código

- Seguir PEP 8 para código Python
- Usar type hints donde sea apropiado
- Agregar docstrings para todas las funciones
- Incluir ejemplos en la documentación

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

## 🙏 Agradecimientos

- **Librería Segno**: Por la generación robusta de códigos QR
- **Framework Flask**: Por la interfaz web
- **ISO/IEC 18004**: Por las especificaciones de códigos QR
- **Yape**: Por inspirar el caso de uso original

## 📞 Soporte

- **Issues**: [GitHub Issues](https://github.com/ecoding-dev/QR-Generator-Advanced/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ecoding-dev/QR-Generator-Advanced/discussions)
- **Email**: support@qr-generator-advanced.com

## 🗺️ Hoja de Ruta

- [ ] Interfaz CLI para procesamiento por lotes
- [ ] Endpoints API para acceso programático
- [ ] Formatos de exportación adicionales (PDF, EPS)
- [ ] Generación de códigos QR por lotes
- [ ] Escaneo y análisis de códigos QR
- [ ] Esquemas de colores personalizados
- [ ] Soporte para incrustación de logos

---

**Hecho con ❤️ para la comunidad de códigos QR**
