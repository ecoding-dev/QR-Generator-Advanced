# pip install opencv-python numpy pillow
import cv2, numpy as np
from PIL import Image

FORMAT_MASK = 0x5412  # XOR para desenmascarar los 15 bits
# Tabla de los 32 codewords de formato válidos (BCH(15,5))
# índice = (ecc_bits<<3) | mask_id   donde ecc_bits: 01=L, 00=M, 11=Q, 10=H
FORMAT_CODEWORDS = [
    0x77C4,0x72F3,0x7DAA,0x789D,0x662F,0x6318,0x6C41,0x6976,
    0x5D8A,0x58BD,0x57E4,0x52D3,0x4C61,0x4956,0x461F,0x4328,
    0x355F,0x3068,0x3F31,0x3A06,0x24B4,0x2183,0x2EDA,0x2BED,
    0x1F11,0x1A26,0x156F,0x1058,0x0EEA,0x0BDD,0x0484,0x01B3
]

ECC_MAP = {0b01:'L', 0b00:'M', 0b11:'Q', 0b10:'H'}

def hamming(a,b): return bin(a^b).count('1')

def best_format_match(fmt15):
    # Corrige errores buscando el codeword válido más cercano
    best_i, best_d = None, 1e9
    for i,cw in enumerate(FORMAT_CODEWORDS):
        d = hamming(fmt15, cw)
        if d < best_d:
            best_i, best_d = i, d
    ecc_bits = (best_i >> 3) & 0b11
    mask_id  = best_i & 0b111
    return ECC_MAP[ecc_bits], mask_id, best_d

def sample_module(img_bin, r, c, scale):
    # promedia un pequeño área alrededor del centro del módulo
    h, w = img_bin.shape
    y0 = int(r*scale + scale*0.25)
    x0 = int(c*scale + scale*0.25)
    y1 = int((r+1)*scale - scale*0.25)
    x1 = int((c+1)*scale - scale*0.25)
    patch = img_bin[max(0,y0):min(h,y1), max(0,x0):min(w,x1)]
    return 1 if patch.mean() < 128 else 0  # 1 = negro

def analyze_qr_image(path):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    detector = cv2.QRCodeDetector()
    data, points, straight = detector.detectAndDecode(img)
    if straight is None or straight.size == 0:
        raise RuntimeError("No se pudo rectificar el QR (logo demasiado intrusivo o imagen borrosa).")

    # Binarizar fuerte
    s = cv2.threshold(straight, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]

    # Estimar N (nº de módulos) contando el patrón finder TL ~ 7 módulos
    # y el quiet zone que suele ser >=4 módulos. Más robusto: buscar timing.
    H, W = s.shape
    # Estimar tamaño de módulo midiendo el ancho del finder TL (7 módulos)
    # Busca el primer bloque negro horizontal desde ~10% de la altura
    row = s[int(H*0.15), :]
    # posiciones de transición blanco->negro->blanco del finder superior
    transitions = np.where(np.diff((row<128).astype(np.uint8))!=0)[0]
    # fallback si no encontramos bien: usar relaciones conocidas
    if len(transitions) < 6:
        # estimar N asumiendo que straight viene escalado con N múltiplo
        # prueba valores plausibles
        candidates = [21+4*i for i in range(1,41)]
        N = min(candidates, key=lambda n: abs(W/n - round(W/n)))
    else:
        # ancho aproximado del finder (7 módulos)
        first, last = transitions[0], transitions[5]
        finder_px = last - first
        module = finder_px / 7.0
        N = int(round(W / module))

    version = int((N - 21)//4 + 1)
    # escala (px por módulo)
    scale = W / float(N)

    # Leer bits de FORMAT (posición según ISO):
    #  - 15 bits alrededor de (fila 8, col 0..8 excepto (8,6)) y (col 8, fila N-1..N-7, etc.)
    # Construimos secuencia como en la especificación (primera ubicación)
    coords1 = []
    # (row 8, col 0..5)
    for c in range(0,6): coords1.append((8,c))
    # (row 8, col 7..8)
    coords1 += [(8,7),(8,8)]
    # (row 8, col N-8..N-1)  (los últimos 7 bits)
    for c in range(N-8,N): coords1.append((8,c))
    # (col 8, row 0..5)  y (row 7) y (row 8)
    coords2 = []
    for r in range(0,6): coords2.append((r,8))
    coords2 += [(7,8),(8,8)]
    for r in range(N-7,N): coords2.append((r,8))

    def read15(coords):
        bits = 0
        for (r,c) in coords:
            v = sample_module(s, r, c, scale)
            bits = (bits<<1) | (v&1)
        return bits

    fmt_a = read15(coords1)
    fmt_b = read15(coords2)

    # Desenmascarar (XOR con 0x5412)
    fmt_a ^= FORMAT_MASK
    fmt_b ^= FORMAT_MASK

    # Intenta decodificar ambos; elige el que tenga menor distancia
    ecc_a, mask_a, d_a = best_format_match(fmt_a)
    ecc_b, mask_b, d_b = best_format_match(fmt_b)
    if d_b < d_a:
        ecc, mask_id, dist = ecc_b, mask_b, d_b
    else:
        ecc, mask_id, dist = ecc_a, mask_a, d_a

    return {
        "data": data,
        "version": version,
        "modules": N,
        "ecc": ecc,
        "mask": mask_id,
        "format_distance": dist  # 0 = coincidencia exacta
    }

# --- ejemplo de uso ---
info = analyze_qr_image("C:/Users/ADM/Downloads/qr.png")
print(info)
