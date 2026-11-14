"""Transforme une photo en portrait ASCII (card/art.txt) pour la carte de profil.

Usage, depuis la racine du repo :
    python3 card/ascii_portrait.py photo.png
    python3 card/ascii_portrait.py photo.png --cols 50 --gamma 0.7
puis :
    python3 card/update_profile.py --preview   (aperçu de la carte complète)

Le mieux : une photo détourée (fond transparent, ex. remove.bg), visage + épaules, recadrée
serré autour de la tête pour que le visage prenne de la place.
Si la photo a encore son fond et que rembg est installé (pip install "rembg[cpu]"),
le script la détoure tout seul. Seule dépendance obligatoire : Pillow
(macOS : pip3 install pillow ; Debian : sudo apt install python3-pil).
"""
import argparse
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

RAMP = " .:-=+*#%@"  # du vide au dense ; en thème sombre, dense = clair
FLOOR = 2  # caractère minimal sur le sujet (":"), pour que les zones sombres (cheveux, ombres) restent visibles
LIGHT_FIX = 0.4  # 0 = brut, 1 = éclairage entièrement égalisé (utile quand un côté du visage est dans l'ombre)
CHAR_ASPECT = 0.53  # largeur d'un caractère / hauteur de ligne (police mono 10px, lignes de 11px)
MAX_COLS, MAX_ROWS = 58, 44  # place libre à gauche de la colonne d'infos


def load(path):
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
    if img.getchannel("A").getextrema()[0] == 255:  # aucun pixel transparent : la photo a un fond
        try:
            from rembg import remove

            img = remove(img).convert("RGBA")
        except ImportError:
            print('Astuce : détoure la photo (remove.bg, ou pip install "rembg[cpu]") '
                  "pour une silhouette propre.\n")
    bbox = img.getchannel("A").point(lambda a: 255 if a > 64 else 0).getbbox()
    return img.crop(bbox) if bbox else img  # recadre au plus près du sujet


def to_ascii(img, cols, gamma):
    w, h = img.size
    cols = max(1, min(cols, MAX_COLS))
    rows = max(1, round(cols * h / w * CHAR_ASPECT))
    if rows > MAX_ROWS:  # trop haut : on réduit la largeur pour garder les proportions
        cols, rows = max(1, round(cols * MAX_ROWS / rows)), MAX_ROWS

    # contraste local (fait ressortir yeux, sourire, mèches), puis réduction à 1 pixel par caractère
    gray = img.convert("L").filter(ImageFilter.UnsharpMask(radius=max(w, h) / 12, percent=160, threshold=0))
    lum = gray.resize((cols, rows), Image.Resampling.LANCZOS).tobytes()
    fg = bytes(255 if a >= 128 else 0 for a in img.getchannel("A").resize((cols, rows), Image.Resampling.LANCZOS).tobytes())
    n_fg = max(1, sum(1 for m in fg if m))

    # éclairage : moyenne floue de la luminosité du sujet seul, puis on la compense en partie
    blur = ImageFilter.GaussianBlur(max(cols, rows) / 8)
    num = Image.frombytes("L", (cols, rows), bytes(l if m else 0 for l, m in zip(lum, fg))).filter(blur).tobytes()
    den = Image.frombytes("L", (cols, rows), fg).filter(blur).tobytes()
    mean = sum(l for l, m in zip(lum, fg) if m) / n_fg
    vals = []
    for l, a, b in zip(lum, num, den):
        light = a * 255 / b if b else mean
        vals.append((1 - LIGHT_FIX) * l + LIGHT_FIX * l / max(light, 1) * mean)

    ref = sorted(v for v, m in zip(vals, fg) if m) or [0, 255]
    lo, hi = ref[len(ref) // 50], ref[-1 - len(ref) // 50]  # contraste auto, 2 % écrêtés de chaque côté
    levels = len(RAMP) - 1 - FLOOR
    lines = []
    for y in range(rows):
        line = ""
        for x in range(cols):
            i = y * cols + x
            if not fg[i]:
                line += " "  # fond
                continue
            t = min(max((vals[i] - lo) / max(hi - lo, 1), 0.0), 1.0) ** gamma
            line += RAMP[FLOOR + round(t * levels)]
        lines.append(line.rstrip())
    return "\n".join(lines).strip("\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("photo")
    p.add_argument("--cols", type=int, default=MAX_COLS, help=f"largeur en caractères (max et défaut {MAX_COLS})")
    p.add_argument("--gamma", type=float, default=0.8, help="<1 plus dense et lumineux, >1 plus sombre (défaut 0.8)")
    a = p.parse_args()

    art = to_ascii(load(a.photo), a.cols, a.gamma)
    out = Path(__file__).resolve().parent / "art.txt"
    out.write_text(art + "\n", encoding="utf-8")
    print(art)
    print("\n-> card/art.txt mis à jour. Aperçu : python3 card/update_profile.py --preview")
