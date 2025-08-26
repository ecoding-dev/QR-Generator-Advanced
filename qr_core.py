# -*- coding: utf-8 -*-
import segno
from penalties import compute_mask_penalty

def make_qr(text, ecc='M', version=None, mode='byte', encoding='utf-8',
            eci=True, mask='auto', boost_error=False, micro=False):
    """
    Crea el símbolo segun parámetros elegidos.
    - version: int 1..40 o None/'auto' para mínima
    - mask: 'auto' => None (auto-selección), si no int 0..7
    """
    mask_arg = None if mask == 'auto' else int(mask)
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

def evaluate_all_masks(text, ecc, version, mode, encoding, eci, boost_error, micro):
    """
    Calcula penalización para máscaras 0..7 con los mismos parámetros.
    Devuelve (best_mask, best_score, scores_dict)
    """
    scores = {}
    best_mask = None
    best_score = None

    for m in range(8):
        sym = make_qr(text, ecc=ecc, version=version, mode=mode,
                      encoding=encoding, eci=eci, mask=m,
                      boost_error=boost_error, micro=micro)
        mat = list(sym.matrix)
        sc = compute_mask_penalty(mat)
        scores[m] = sc
        if best_score is None or sc < best_score:
            best_score = sc
            best_mask = m

    return best_mask, best_score, scores
