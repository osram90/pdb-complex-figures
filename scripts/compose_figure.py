"""Compone la figura final a partir de los lienzos capturados.

Una fila por ligando: vista general a la izquierda, detalle a la derecha, unidos
por un círculo y dos líneas guía. Añade la letra del panel, el nombre, el
recuadro de afinidad, el pie con el recuento de contactos y, si hay varias
poses, una barra por pose.

Uso:  python compose_figure.py [contacts.json]
Espera encontrar cap_<id>_A.png y cap_<id>_B.png en el directorio actual.
"""
import json, math, os, sys
from PIL import Image, ImageChops, ImageDraw, ImageFont

INK, MUT, LINE, PAPER = (18, 26, 38), (95, 107, 120), (206, 213, 221), (255, 255, 255)
LW, LH, RW, RH = 760, 620, 980, 620          # tamaño de cada panel
GAP, MARGIN, ROWGAP, HEAD = 90, 60, 40, 126


def font(size, bold=False):
    for path in ((r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf"),
                 ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
                 ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                  "/System/Library/Fonts/Supplemental/Arial.ttf")):
        try:
            return ImageFont.truetype(path[0] if bold else path[1], size)
        except OSError:
            continue
    return ImageFont.load_default()


def trim(im, pad=12):
    """Recorta el blanco sobrante del render antes de escalar."""
    bbox = ImageChops.difference(im, Image.new(im.mode, im.size, PAPER)).getbbox()
    if not bbox:
        return im
    x0, y0, x1, y1 = bbox
    return im.crop((max(0, x0 - pad), max(0, y0 - pad),
                    min(im.width, x1 + pad), min(im.height, y1 + pad)))


def fit(path, box):
    im = trim(Image.open(path).convert("RGB"))
    r = min(box[0] / im.width, box[1] / im.height)
    im = im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)
    canvas = Image.new("RGB", box, PAPER)
    canvas.paste(im, ((box[0] - im.width) // 2, (box[1] - im.height) // 2))
    return canvas


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def main(path="contacts.json"):
    data = json.load(open(path, encoding="utf-8"))
    ligs = data["ligands"]
    missing = [f"cap_{l['id']}_{p}.png" for l in ligs for p in "AB"
               if not os.path.exists(f"cap_{l['id']}_{p}.png")]
    if missing:
        sys.exit("Faltan capturas: " + ", ".join(missing) +
                 "\nEjecuta la captura de los lienzos antes de componer la figura.")

    allscores = [s for l in ligs for s in (l.get("poses") or [])]
    smin, smax = (min(allscores), max(allscores)) if allscores else (0, 1)
    letters = "ABCDEFGHIJKL"

    W = MARGIN * 2 + LW + GAP + RW
    H = HEAD + MARGIN // 2 + len(ligs) * (LH + ROWGAP) + 20
    fig = Image.new("RGB", (W, H), PAPER)
    dr = ImageDraw.Draw(fig)

    f_title, f_sub = font(40, True), font(21)
    f_letter, f_name = font(40, True), font(28, True)
    f_badge, f_unit = font(40, True), font(20)
    f_cap, f_small, f_tiny = font(19), font(17, True), font(15)

    dr.text((MARGIN, 30), data.get("title", ""), fill=INK, font=f_title)
    sub = data.get("subtitle") or (
        "Izquierda: superficie molecular — sitio de unión en violeta"
        + (f", {data.get('highlight_label','')} en rojo" if data.get("highlight_residues") else "")
        + ".   Derecha: detalle del bolsillo, con los puentes de hidrógeno acotados.")
    dr.text((MARGIN, 80), sub, fill=MUT, font=f_sub)

    for i, lig in enumerate(ligs):
        top = HEAD + MARGIN // 2 + i * (LH + ROWGAP)
        lx, rx = MARGIN, MARGIN + LW + GAP
        accent = hex_rgb(lig["color"])

        fig.paste(fit(f"cap_{lig['id']}_A.png", (LW, LH)), (lx, top))
        fig.paste(fit(f"cap_{lig['id']}_B.png", (RW, RH)), (rx, top))
        dr.rectangle([lx, top, lx + LW, top + LH], outline=INK, width=3)
        dr.rectangle([rx, top, rx + RW, top + RH], outline=INK, width=3)

        cx, cy, rad = lx + int(LW * 0.56), top + int(LH * 0.54), 92
        dr.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=INK, width=3)
        for ty in (top + 6, top + LH - 6):
            ang = math.atan2(ty - cy, rx - cx)
            dr.line([cx + rad * math.cos(ang), cy + rad * math.sin(ang), rx, ty],
                    fill=INK, width=2)

        dr.text((lx + 14, top + 10), letters[i], fill=INK, font=f_letter)
        dr.text((lx + 66, top + 18), lig["label"], fill=INK, font=f_name)

        if lig.get("score") is not None:
            bw, bh = 190, 96
            bx, by = lx + LW - bw - 16, top + 14
            dr.rounded_rectangle([bx, by, bx + bw, by + bh], radius=12, fill=accent)
            dr.text((bx + bw // 2, by + 10), f"{lig['score']:.2f}", fill=PAPER,
                    font=f_badge, anchor="ma")
            dr.text((bx + bw // 2, by + 62), "kcal/mol", fill=PAPER, font=f_unit, anchor="ma")

        poses = lig.get("poses") or []
        if len(poses) > 1:
            gx, gy, gw = rx + 16, top + RH - 122, RW - 32
            dr.rectangle([rx + 3, gy - 34, rx + RW - 3, top + RH - 3], fill=PAPER)
            dr.line([rx + 3, gy - 34, rx + RW - 3, gy - 34], fill=LINE, width=2)
            dr.text((gx, gy - 30), f"Afinidad de las {len(poses)} poses (kcal/mol)",
                    fill=(55, 65, 78), font=f_small)
            slot = gw / len(poses)
            for j, s in enumerate(poses):
                frac = (smax - s) / (smax - smin) if smax != smin else 0.5
                bh2 = 8 + frac * 46
                x0, x1 = gx + j * slot + 4, gx + (j + 1) * slot - 4
                dr.rectangle([x0, gy + 56 - bh2, x1, gy + 56],
                             fill=accent if j == 0 else (188, 196, 206))
                dr.text(((x0 + x1) / 2, gy + 60), f"{s:.2f}",
                        fill=(30, 38, 48) if j == 0 else (120, 130, 142),
                        font=f_tiny, anchor="ma")

        en_sitio = (f" ({lig['n_site']} en {data.get('site_label', 'el sitio')})"
                    if lig.get("n_site") is not None else "")
        txt = (f"{lig['n_total']} residuos en contacto{en_sitio}   ·   "
               f"{lig['n_hbond']} puentes de hidrógeno")
        hl = sorted(c["num"] for c in lig["contacts"]
                    if c["num"] in set(data.get("highlight_residues", [])))
        if hl:
            names = {c["num"]: c["res"].capitalize() for c in lig["contacts"]}
            txt += (f"   ·   {data.get('highlight_label','destacados')}: "
                    + ", ".join(f"{names[n]}{n}" for n in hl))
        dr.text((rx + 16, top + 14), txt, fill=(55, 65, 78), font=f_cap)

    out = data.get("outfile", "FIGURA_complejos.png")
    fig.save(out, quality=97, dpi=(300, 300))
    print(f"{out}   {fig.width}x{fig.height} px")

    for i, lig in enumerate(ligs):
        one = Image.new("RGB", (MARGIN * 2 + LW + GAP + RW, LH + 150), PAPER)
        d = ImageDraw.Draw(one)
        one.paste(fit(f"cap_{lig['id']}_A.png", (LW, LH)), (MARGIN, 110))
        one.paste(fit(f"cap_{lig['id']}_B.png", (RW, RH)), (MARGIN + LW + GAP, 110))
        d.rectangle([MARGIN, 110, MARGIN + LW, 110 + LH], outline=INK, width=3)
        d.rectangle([MARGIN + LW + GAP, 110, MARGIN + LW + GAP + RW, 110 + RH],
                    outline=INK, width=3)
        d.text((MARGIN, 26), lig["label"], fill=INK, font=f_title)
        line = (f"{lig['score']:.2f} kcal/mol   ·   " if lig.get("score") is not None else "")
        d.text((MARGIN, 76), line + f"{lig['n_total']} contactos · "
               f"{lig['n_hbond']} puentes de hidrógeno",
               fill=hex_rgb(lig["color"]), font=f_sub)
        name = f"FIGURA_{lig['id']}.png"
        one.save(name, quality=97, dpi=(300, 300))
        print(name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "contacts.json"))
