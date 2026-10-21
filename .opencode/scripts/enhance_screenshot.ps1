# enhance_screenshot.ps1 — pre-processing opzionale per modelli vision
#
# MISURATO (Qwen3-VL 8B su screenshot scuri, testo 10-11 px):
#   - l'upscale NON aiuta: il modello normalizza internamente l'immagine (stessi prompt token) e il refuso
#     OCR resta identico;
#   - il contrasto non cambia la precisione in modo misurabile.
# Per questo lo script NON e' nel flusso critico: si usa solo, in via eccezionale, per tentare di rendere
# leggibile un'etichetta che il modello ha dichiarato illeggibile.
#
# Uso:  powershell -NoProfile -File enhance_screenshot.ps1 -In <png> -Out <png> [-Scale 1.0] [-Contrast 1.6]
param(
  [Parameter(Mandatory = $true)][string]$In,
  [Parameter(Mandatory = $true)][string]$Out,
  [double]$Scale = 2.0,
  [double]$Contrast = 1.5
)

Add-Type -AssemblyName System.Drawing

$src = [System.Drawing.Image]::FromFile((Resolve-Path $In).Path)
try {
  $w = [int]($src.Width * $Scale)
  $h = [int]($src.Height * $Scale)
  $dst = New-Object System.Drawing.Bitmap $w, $h, ([System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
  try {
    $g = [System.Drawing.Graphics]::FromImage($dst)
    try {
      $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
      $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
      $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
      $g.Clear([System.Drawing.Color]::Black)

      $attrs = New-Object System.Drawing.Imaging.ImageAttributes
      try {
        # Contrasto lineare: out = k*in + offset (offset = 128*(1-k) -> pivot a grigio medio)
        $off = 128.0 * (1.0 - $Contrast)
        $cm = New-Object System.Drawing.Imaging.ColorMatrix
        $cm.Matrix00 = $Contrast; $cm.Matrix01 = 0; $cm.Matrix02 = 0; $cm.Matrix03 = 0; $cm.Matrix04 = $off
        $cm.Matrix10 = 0; $cm.Matrix11 = $Contrast; $cm.Matrix12 = 0; $cm.Matrix13 = 0; $cm.Matrix14 = $off
        $cm.Matrix20 = 0; $cm.Matrix21 = 0; $cm.Matrix22 = $Contrast; $cm.Matrix23 = 0; $cm.Matrix24 = $off
        $cm.Matrix33 = 1.0
        $cm.Matrix44 = 1.0
        $attrs.SetColorMatrix($cm)

        $rect = New-Object System.Drawing.Rectangle 0, 0, $w, $h
        $g.DrawImage($src, $rect, 0, 0, $src.Width, $src.Height, [System.Drawing.GraphicsUnit]::Pixel, $attrs)
      } finally { $attrs.Dispose() }
    } finally { $g.Dispose() }

    $dir = Split-Path -Parent $Out
    if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    $dst.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
    Write-Output ("{0} -> {1} ({2}x{3}, contrast {4})" -f $In, $Out, $w, $h, $Contrast)
  } finally { $dst.Dispose() }
} finally { $src.Dispose() }
