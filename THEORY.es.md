# Teoría e Implementación de Códigos QR

Este documento proporciona una visión integral de la teoría de códigos QR, estructura y detalles de implementación utilizados en QR Generator Advanced.

## Tabla de Contenidos

1. [Resumen de Códigos QR](#resumen-de-códigos-qr)
2. [Estructura del Código QR](#estructura-del-código-qr)
3. [Corrección de Errores](#corrección-de-errores)
4. [Modos de Codificación](#modos-de-codificación)
5. [Patrones de Máscara](#patrones-de-máscara)
6. [Evaluación de Penalización](#evaluación-de-penalización)
7. [Detalles de Implementación](#detalles-de-implementación)
8. [Referencias](#referencias)

## Resumen de Códigos QR

Los códigos QR (Quick Response) son códigos de barras bidimensionales que pueden almacenar varios tipos de datos. Fueron inventados por Denso Wave en 1994 y están estandarizados por ISO/IEC 18004.

### Características Clave

- **Alta Capacidad**: Puede almacenar hasta 4,296 caracteres alfanuméricos
- **Corrección de Errores**: Corrección de errores Reed-Solomon incorporada
- **Lectura Rápida**: Puede ser leído desde cualquier ángulo
- **Robusto**: Puede ser leído incluso con hasta 30% de daño (dependiendo del nivel de corrección)

### Versiones de Códigos QR

Los códigos QR vienen en 40 versiones diferentes, cada una con un tamaño diferente:

- **Versión 1**: 21×21 módulos
- **Versión 2**: 25×25 módulos
- **Versión 40**: 177×177 módulos

Cada versión agrega 4 módulos por lado, por lo que la versión N tiene tamaño = 21 + (N-1) × 4.

## Estructura del Código QR

Un código QR consiste en varias áreas funcionales:

### 1. Patrones Finder (3 esquinas)

```
████████
█      █
█ ████ █
█ ████ █
█ ████ █
█      █
████████
```

- Ubicados en tres esquinas (superior-izquierda, superior-derecha, inferior-izquierda)
- 7×7 módulos cada uno
- Usados para orientación y detección de posición
- Rodeados por separador de 1 módulo (borde claro)

### 2. Patrones de Timing

- Patrón de timing horizontal en la fila 6
- Patrón de timing vertical en la columna 6
- Módulos alternados oscuros/claros
- Usados para determinar el tamaño del módulo y corregir distorsión

### 3. Patrones de Alineación (Versión 2+)

```
█████
█   █
█ █ █
█   █
█████
```

- 5×5 módulos
- Posicionados en centros calculados
- Usados para corrección de perspectiva
- No presentes en la versión 1

### 4. Información de Formato

- 15 bits conteniendo:
  - Nivel de corrección de errores (2 bits)
  - Patrón de máscara (3 bits)
  - Corrección de errores para información de formato (10 bits)
- Ubicados alrededor de patrones finder y en áreas de timing

### 5. Información de Versión (Versión 7+)

- 18 bits conteniendo número de versión
- Dos bloques 3×6: superior-derecha e inferior-izquierda
- Solo presente en versiones 7-40

### 6. Datos y Corrección de Errores

- Los módulos restantes contienen:
  - Codewords de datos (tu información real)
  - Codewords de corrección de errores (códigos Reed-Solomon)
- Colocados en patrón zigzag de derecha a izquierda, saltando columna 6

## Corrección de Errores

Los códigos QR usan corrección de errores Reed-Solomon para recuperarse del daño. Cuatro niveles están disponibles:

### Niveles de Corrección de Errores

| Nivel | Capacidad de Recuperación | Reducción Aproximada de Capacidad |
|-------|---------------------------|-----------------------------------|
| L     | ~7%                       | 7%                                |
| M     | ~15%                      | 15%                               |
| Q     | ~25%                      | 25%                               |
| H     | ~30%                      | 30%                               |

### Implementación Reed-Solomon

- Los datos se dividen en bloques
- Cada bloque obtiene codewords de corrección de errores
- Versiones más altas pueden tener múltiples grupos con diferentes conteos de ECC
- Puede recuperarse de errores aleatorios y errores en ráfaga

### Ejemplo: Versión 6, Nivel M

- **Grupo 1**: 4 bloques, 16 codewords ECC cada uno
- **Grupo 2**: 4 bloques, 16 codewords ECC cada uno
- **ECC Total**: 4×16 + 4×16 = 128 codewords

## Modos de Codificación

Los códigos QR soportan cuatro modos de codificación:

### 1. Modo Numérico (0-9)

- **Eficiencia**: 3.33 bits por dígito
- **Capacidad**: Hasta 7,089 dígitos
- **Caso de uso**: Números de teléfono, IDs, datos numéricos

### 2. Modo Alfanumérico (0-9, A-Z, y 9 símbolos)

- **Eficiencia**: 5.5 bits por carácter
- **Capacidad**: Hasta 4,296 caracteres
- **Caso de uso**: URLs, texto con conjunto limitado de caracteres

### 3. Modo Byte (Cualquier dato de 8 bits)

- **Eficiencia**: 8 bits por byte
- **Capacidad**: Hasta 2,953 bytes
- **Caso de uso**: Texto UTF-8, datos binarios, payloads EMVCo

### 4. Modo Kanji (Shift-JIS)

- **Eficiencia**: 13 bits por carácter
- **Capacidad**: Hasta 1,817 caracteres
- **Caso de uso**: Texto japonés

### Selección de Modo

El codificador selecciona automáticamente el modo más eficiente, pero puedes forzar un modo específico por razones de compatibilidad.

## Patrones de Máscara

Los patrones de máscara se aplican al área de datos para evitar patrones problemáticos y mejorar la legibilidad. Ocho patrones de máscara están disponibles (0-7).

### Fórmulas de Patrones de Máscara

| Patrón | Fórmula | Descripción |
|--------|---------|-------------|
| 0      | (i + j) mod 2 = 0 | Tablero de ajedrez |
| 1      | i mod 2 = 0 | Rayas horizontales |
| 2      | j mod 3 = 0 | Rayas verticales |
| 3      | (i + j) mod 3 = 0 | Rayas diagonales |
| 4      | ((i div 2) + (j div 3)) mod 2 = 0 | Tablero grande |
| 5      | (i × j) mod 2 + (i × j) mod 3 = 0 | Tablero pequeño |
| 6      | ((i × j) mod 2 + (i × j) mod 3) mod 2 = 0 | Alternante |
| 7      | ((i × j) mod 3 + (i + j) mod 2) mod 2 = 0 | Patrón complejo |

Donde i = fila, j = columna (base 0)

### Selección de Máscara

La máscara óptima se selecciona usando evaluación de penalización (ver abajo).

## Evaluación de Penalización

El estándar ISO/IEC 18004 define cuatro reglas de penalización para evaluar la calidad de la máscara:

### Regla N1: Módulos Adyacentes en Secuencias

Penaliza secuencias largas de módulos consecutivos del mismo color.

- **Fórmula**: 3 + (longitud_secuencia - 5) para secuencias ≥ 5
- **Aplicado a**: Ambas direcciones horizontal y vertical
- **Propósito**: Evitar patrones difíciles de escanear

### Regla N2: Bloques 2×2 del Mismo Color

Penaliza bloques 2×2 donde todos los módulos tienen el mismo color.

- **Penalización**: 3 puntos por bloque
- **Propósito**: Evitar áreas sólidas grandes

### Regla N3: Patrones Tipo Finder

Penaliza patrones que se asemejan a patrones finder.

- **Patrón**: 1:1:3:1:1 (oscuro:claro:oscuro:oscuro:oscuro:claro:oscuro)
- **Penalización**: 40 puntos por ocurrencia
- **Requisito**: Debe estar rodeado por ≥4 módulos claros
- **Propósito**: Evitar confusión con patrones finder reales

### Regla N4: Ratio de Módulos Oscuros/Claros

Penaliza desviación del 50% de módulos oscuros.

- **Fórmula**: 10 × floor(abs(ratio - 50) / 5)
- **Propósito**: Fomentar distribución equilibrada

### Penalización Total

La máscara con la penalización total más baja (N1 + N2 + N3 + N4) se selecciona.

## Detalles de Implementación

### Orden de Colocación de Datos

Los datos se colocan en un patrón zigzag:

1. Comenzar desde la esquina inferior-derecha
2. Moverse hacia arriba en pares de columnas
3. Saltar columna 6 (patrón de timing)
4. Alternar dirección para cada fila
5. Continuar hasta que todos los datos estén colocados

### ECI (Interpretación Extendida de Canal)

ECI permite especificar codificación de caracteres explícitamente:

- **ECI Verdadero**: Agrega encabezado ECI con identificador de codificación
- **ECI Falso**: Asume codificación ISO-8859-1
- **Caso de uso**: Texto UTF-8, caracteres internacionales

### Códigos QR Micro

Versión más pequeña de códigos QR con capacidad reducida:

- **M1**: 11×11 módulos, solo numérico
- **M2**: 13×13 módulos, alfanumérico
- **M3**: 15×15 módulos, modo byte
- **M4**: 17×17 módulos, características completas

## Referencias

### Estándares

- **ISO/IEC 18004:2015**: Tecnología de la información — Técnicas de identificación automática y captura de datos — Especificación de símbolos de código de barras QR Code
- **Especificación EMVCo QR Code**: Para códigos QR de pago

### Recursos Técnicos

- **Librería Segno**: Librería de generación de códigos QR en Python
- **Generador de Códigos QR**: Herramientas de códigos QR en línea
- **Códigos Reed-Solomon**: Teoría de corrección de errores

### Notas de Implementación

Esta implementación usa la librería Segno para la generación principal de QR e implementa características personalizadas de visualización y análisis. La evaluación de penalización sigue exactamente las especificaciones ISO/IEC 18004:2015.

### Integración con Yape

El caso de uso original fue la regeneración de QRs de Yape, que usa:
- **Corrección de Errores**: Nivel M (15%)
- **Patrón de Máscara**: 2 (rayas verticales)
- **Modo de Codificación**: Byte
- **Conjunto de Caracteres**: UTF-8
- **ECI**: Verdadero

Esta configuración asegura compatibilidad con el sistema de pagos de Yape mientras mantiene legibilidad óptima.
