# -*- coding: utf-8 -*-
"""Genere la banniere du profil GitHub, en variantes claire et sombre."""
import os

W, H = 1280, 320
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, 'Helvetica Neue', Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

THEMES = {
    "dark": dict(
        bg="#0A0C10", card_stroke="#FFFFFF", card_stroke_o=0.07,
        text="#F4F6FA", sub="#C3CBD8", muted="#79839A",
        dot="#FFFFFF", dot_o=0.17,
        a1="#22D3EE", a2="#818CF8", glow_o=0.16, edge_o=0.38, node_glow=True,
    ),
    "light": dict(
        bg="#FCFCFD", card_stroke="#0A0C10", card_stroke_o=0.10,
        text="#0B0E14", sub="#3D4757", muted="#6B7686",
        dot="#0A0C10", dot_o=0.15,
        a1="#0891B2", a2="#4F46E5", glow_o=0.07, edge_o=0.42, node_glow=False,
    ),
}

# --- Grille de points (fond, cote droit) ---
COLS, ROWS, GX0, GY0, GS = 16, 8, 806, 66, 27

# --- Graphe : une racine qui se ramifie vers la droite (enumeration de surface d'attaque) ---
NODES = {
    "root": (2, 4, 5.2),
    "b1":   (5, 2, 4.0), "b2": (5, 6, 4.0),
    "c1":   (9, 1, 3.3), "c2": (9, 3, 3.3), "c3": (9, 5, 3.3), "c4": (9, 7, 3.3),
    "d1":   (13, 0, 3.0), "d2": (13, 3, 3.0), "d3": (13, 6, 3.0),
}
EDGES = [("root","b1"),("root","b2"),("b1","c1"),("b1","c2"),
         ("b2","c3"),("b2","c4"),("c1","d1"),("c2","d2"),("c3","d2"),("c4","d3")]
# Trajets parcourus par un signal lumineux
SIGNALS = [(["root","b1","c2","d2"], 7.0, 0.0), (["root","b2","c4","d3"], 7.0, 3.5)]

def pos(name):
    c, r, _ = NODES[name]
    return GX0 + c * GS, GY0 + r * GS

def build(theme_name):
    t = THEMES[theme_name]
    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Pierre Pocheron, developpeur full-stack, Lyon, cybersecurite">')

    # --- defs ---
    o.append('<defs>')
    o.append(f'<linearGradient id="acc" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t["a1"]}"/><stop offset="1" stop-color="{t["a2"]}"/></linearGradient>')
    o.append(f'<linearGradient id="accV" gradientUnits="userSpaceOnUse" x1="{GX0}" y1="{GY0}" x2="{GX0+(COLS-1)*GS}" y2="{GY0+(ROWS-1)*GS}"><stop offset="0" stop-color="{t["a1"]}"/><stop offset="1" stop-color="{t["a2"]}"/></linearGradient>')
    o.append(f'<radialGradient id="halo" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="{t["a1"]}" stop-opacity="{t["glow_o"]}"/><stop offset="1" stop-color="{t["a1"]}" stop-opacity="0"/></radialGradient>')
    if t["node_glow"]:
        o.append('<filter id="soft" x="-120%" y="-120%" width="340%" height="340%"><feGaussianBlur stdDeviation="4"/></filter>')
    o.append(f'<clipPath id="card"><rect x="0" y="0" width="{W}" height="{H}" rx="20"/></clipPath>')
    # Trajets nommes, reutilises par les signaux animes
    for i, (path_nodes, _, _) in enumerate(SIGNALS):
        pts = " ".join(("M" if k == 0 else "L") + f"{pos(n)[0]} {pos(n)[1]}" for k, n in enumerate(path_nodes))
        o.append(f'<path id="sig{i}" d="{pts}" fill="none"/>')
    o.append('</defs>')

    o.append('<g clip-path="url(#card)">')
    o.append(f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>')
    o.append(f'<ellipse cx="1010" cy="160" rx="420" ry="230" fill="url(#halo)"/>')

    # --- Grille de points, en fondu vers la gauche ---
    node_cells = {(c, r) for c, r, _ in NODES.values()}
    o.append(f'<g fill="{t["dot"]}">')
    for r in range(ROWS):
        for c in range(COLS):
            if (c, r) in node_cells:
                continue
            fade = 0.22 + 0.78 * (c / (COLS - 1))
            op = round(t["dot_o"] * fade, 4)
            o.append(f'<circle cx="{GX0 + c*GS}" cy="{GY0 + r*GS}" r="2.1" opacity="{op}"/>')
    o.append('</g>')

    # --- Aretes du graphe ---
    o.append(f'<g stroke="url(#accV)" stroke-width="1.15" stroke-linecap="round" opacity="{t["edge_o"]}">')
    for a, b in EDGES:
        (x1, y1), (x2, y2) = pos(a), pos(b)
        o.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
    o.append('</g>')

    # --- Noeuds ---
    if t["node_glow"]:
        o.append('<g fill="url(#accV)" filter="url(#soft)" opacity="0.55">')
        for n, (c, r, rad) in NODES.items():
            x, y = pos(n)
            o.append(f'<circle cx="{x}" cy="{y}" r="{rad + 1.2}"/>')
        o.append('</g>')
    o.append('<g fill="url(#accV)">')
    for n, (c, r, rad) in NODES.items():
        x, y = pos(n)
        o.append(f'<circle cx="{x}" cy="{y}" r="{rad}"/>')
    o.append('</g>')
    # Anneau qui respire autour de la racine
    rx, ry = pos("root")
    o.append(f'<circle cx="{rx}" cy="{ry}" r="5" fill="none" stroke="{t["a1"]}" stroke-width="1.2">'
             f'<animate attributeName="r" values="6;17;6" dur="6s" repeatCount="indefinite" calcMode="spline" keySplines="0.4 0 0.2 1;0.4 0 0.2 1" keyTimes="0;0.5;1"/>'
             f'<animate attributeName="opacity" values="0.5;0;0.5" dur="6s" repeatCount="indefinite"/></circle>')
    # Signaux qui parcourent le graphe
    for i, (_, dur, delay) in enumerate(SIGNALS):
        o.append(f'<circle r="2.6" fill="{t["a1"]}" opacity="0">'
                 f'<animate attributeName="opacity" values="0;0.95;0.95;0" keyTimes="0;0.12;0.88;1" dur="{dur}s" begin="{delay}s" repeatCount="indefinite"/>'
                 f'<animateMotion dur="{dur}s" begin="{delay}s" repeatCount="indefinite" calcMode="spline" keyPoints="0;1" keyTimes="0;1" keySplines="0.45 0 0.55 1"><mpath href="#sig{i}"/></animateMotion></circle>')

    # --- Bloc de texte ---
    o.append(f'<circle cx="79" cy="82" r="3.6" fill="url(#acc)"/>')
    o.append(f'<text x="95" y="87" font-family="{MONO}" font-size="13" letter-spacing="2.4" fill="{t["muted"]}">LYON &#183; FRANCE</text>')
    o.append(f'<text x="76" y="158" font-family="{SANS}" font-size="62" font-weight="600" letter-spacing="-1.4" fill="{t["text"]}">Pierre Pocheron</text>')
    o.append(f'<rect x="78" y="182" width="46" height="3" rx="1.5" fill="url(#acc)"/>')
    o.append(f'<text x="76" y="222" font-family="{SANS}" font-size="21" font-weight="500" letter-spacing="-0.1" fill="{t["sub"]}">D&#233;veloppeur full-stack &#183; Cybers&#233;curit&#233;</text>')
    o.append(f'<text x="76" y="251" font-family="{SANS}" font-size="17" fill="{t["muted"]}">Je construis mes propres produits web.</text>')

    o.append(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="20" fill="none" stroke="{t["card_stroke"]}" stroke-opacity="{t["card_stroke_o"]}"/>')
    o.append('</g></svg>')
    return "\n".join(o)

out = os.path.dirname(os.path.abspath(__file__))
os.makedirs(out, exist_ok=True)
for name in THEMES:
    p = os.path.join(out, f"banner-{name}.svg")
    with open(p, "w", encoding="utf-8") as f:
        f.write(build(name))
    print(f"{p}  ({os.path.getsize(p)} octets)")
