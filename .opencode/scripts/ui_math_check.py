#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UI_MATH — verifica geometrica deterministica del probe UI A.C.T.D.

Due controlli, entrambi matematici (nessuna euristica, nessun LLM):

1. **Report**: `flagged=0` e zero righe `TIGHT` -> il troncamento e' escluso.
2. **PNG**: i due ritagli devono esistere, avere dimensioni plausibili e
   contenere pixels (deviazione standard sopra la soglia): uno screenshot
   nero, corrotto o vuoto viene scartato prima di spendere token su vision.

Il PNG viene letto con un decoder puro (zlib + unfilter PNG): il Python di
Blender NON ha PIL, e introdurre una dipendenza per un controllo non vale
la pena.

Uso:
    ui_math_check.py <dir_output> [--min-width 400] [--min-height 200] [--min-std 8.0]

Exit code: 0 = UI_PROBE_MATH_OK, 1 = UI_PROBE_FAIL, 2 = errore di uso.
"""

import argparse
import os
import struct
import sys
import zlib

# Soglia sotto la quale l'immagine e' considerata "piatta" (nera o vuota).
DEFAULT_MIN_STD = 8.0
DEFAULT_MIN_WIDTH = 400
DEFAULT_MIN_HEIGHT = 200
# Soglia di saturazione: pixel quasi tutti uguali.
DEFAULT_MAX_STD = 250.0


def _paeth(a, b, c):
    """Predittore Paeth del filtro PNG (RFC 2083)."""
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _unfilter(raw, width, height, bpp):
    """Ricostruisce i pixel da scanline filtrate. Ritorna (bytearray, w, h)."""
    stride = width * bpp
    out = bytearray(height * stride)
    pos = 0
    prev = bytearray(stride)
    for y in range(height):
        if pos >= len(raw):
            break
        ftype = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        pos += stride
        if len(line) < stride:
            line.extend(bytearray(stride - len(line)))
        if ftype == 0:
            pass
        elif ftype == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif ftype == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                upleft = prev[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + _paeth(left, prev[i], upleft)) & 0xFF
        else:
            raise ValueError("filtro PNG sconosciuto: {0}".format(ftype))
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return out, stride


def read_png_stats(path):
    """(larghezza, altezza, deviazione standard dei pixel) di un PNG.

    Supporta 8 bit, color type 0/2/4/6, non interlacciato: il formato che
    Blender produce per gli screenshot.
    """
    with open(path, "rb") as handle:
        data = handle.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("firma PNG non valida")

    width = height = 0
    bitdepth = colortype = interlace = 0
    idat = bytearray()
    pos = 8
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype == b"IHDR":
            width, height, bitdepth, colortype, _comp, _filt, interlace = \
                struct.unpack(">IIBBBBB", chunk[:13])
        elif ctype == b"IDAT":
            idat.extend(chunk)
        elif ctype == b"IEND":
            break

    if width == 0 or height == 0:
        raise ValueError("intestazione PNG incompleta")
    if bitdepth != 8:
        raise ValueError("bit depth non supportato: {0}".format(bitdepth))
    if interlace != 0:
        raise ValueError("PNG interlacciato non supportato")
    channels = {0: 1, 2: 3, 4: 2, 6: 4}.get(colortype)
    if channels is None:
        raise ValueError("color type non supportato: {0}".format(colortype))

    raw = zlib.decompress(bytes(idat))
    pixels, stride = _unfilter(raw, width, height, channels)

    # Somma e somma dei quadrati su un campione di righe: media e varianza
    # senza costruire un array numpy (il controllo resta in pura stdlib).
    step = max(1, height // 120)
    total = 0.0
    total_sq = 0.0
    count = 0
    for y in range(0, height, step):
        row = pixels[y * stride:(y + 1) * stride]
        for i in range(0, len(row)):
            value = float(row[i])
            total += value
            total_sq += value * value
            count += 1
    if count == 0:
        raise ValueError("immagine senza pixel")
    mean = total / count
    variance = max(0.0, (total_sq / count) - (mean * mean))
    return width, height, variance ** 0.5


def main():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("outdir", help="cartella con ui_report.txt e i PNG")
    parser.add_argument("--min-width", type=int, default=DEFAULT_MIN_WIDTH)
    parser.add_argument("--min-height", type=int, default=DEFAULT_MIN_HEIGHT)
    parser.add_argument("--min-std", type=float, default=DEFAULT_MIN_STD)
    parser.add_argument("--max-std", type=float, default=DEFAULT_MAX_STD)
    args = parser.parse_args()

    report_path = os.path.join(args.outdir, "ui_report.txt")
    if not os.path.isfile(report_path):
        print("UI_PROBE_FAIL | reason=report_missing | path={0}".format(report_path))
        return 1
    with open(report_path, "r", encoding="utf-8", errors="replace") as handle:
        report = handle.read()

    # 1. report: nessun TIGHT, flagged=0
    tight = 0
    flagged_ok = False
    for line in report.splitlines():
        if line.startswith("UI_TEXT ") and " TIGHT " in line:
            tight += 1
        if line.startswith("UI_SUMMARY ") and " flagged=0" in line:
            flagged_ok = True
    if tight > 0:
        print("UI_PROBE_FAIL | reason=TIGHT | tight={0}".format(tight))
        return 1
    if not flagged_ok:
        print("UI_PROBE_FAIL | reason=NO_SUMMARY | flagged=0 non trovato nel report")
        return 1

    # 2. PNG: esistono, dimensioni plausibili, non piatti
    for name in ("actd-ui-it.png", "actd-ui-en.png"):
        path = os.path.join(args.outdir, name)
        if not os.path.isfile(path):
            print("UI_PROBE_FAIL | reason=missing_png | file={0}".format(name))
            return 1
        try:
            width, height, std = read_png_stats(path)
        except Exception as exc:
            print("UI_PROBE_FAIL | reason=unreadable_png | file={0} | {1}: {2}".format(
                name, type(exc).__name__, exc))
            return 1
        if width < args.min_width or height < args.min_height:
            print("UI_PROBE_FAIL | reason=too_small | file={0} | {1}x{2}".format(
                name, width, height))
            return 1
        if std < args.min_std:
            print("UI_PROBE_FAIL | reason=blank_png | file={0} | std={1:.2f} (min {2})".format(
                name, std, args.min_std))
            return 1
        if std > args.max_std:
            print("UI_PROBE_FAIL | reason=noisy_png | file={0} | std={1:.2f} (max {2})".format(
                name, std, args.max_std))
            return 1

    print("UI_PROBE_MATH_OK | tight=0 | flagged=0 | pngs_valid=2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
