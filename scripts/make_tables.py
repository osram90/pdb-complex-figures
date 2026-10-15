"""Construye las tablas de resultados a partir de contacts.json.

Las tablas salen de los mismos datos que la figura, de modo que no puedan
contradecirla. Cada una se escribe en tres formatos:

  .md    para pegar en Markdown o en el manuscrito
  .csv   para abrir en Excel
  .html  para pegar en Word conservando el formato de tabla

Produce:
  tabla_resumen.*              una fila por ligando
  tabla_contactos_<id>.*       todos los contactos de ese ligando
  tabla_contactos_todos.csv    los contactos de todos los ligandos juntos

Uso:  python make_tables.py [contacts.json]
"""
import csv, html, json, sys

TRES_A_NOMBRE = {
    "ALA": "Ala", "ARG": "Arg", "ASN": "Asn", "ASP": "Asp", "CYS": "Cys",
    "GLN": "Gln", "GLU": "Glu", "GLY": "Gly", "HIS": "His", "ILE": "Ile",
    "LEU": "Leu", "LYS": "Lys", "MET": "Met", "PHE": "Phe", "PRO": "Pro",
    "SER": "Ser", "THR": "Thr", "TRP": "Trp", "TYR": "Tyr", "VAL": "Val",
}


def residuo(c):
    return f"{TRES_A_NOMBRE.get(c['res'], c['res'].capitalize())}{c['num']}"


def write_md(path, header, rows, align=None):
    sep = ["---" if not align or align[i] != "c" else ":-:" for i in range(len(header))]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("| " + " | ".join(header) + " |\n")
        fh.write("| " + " | ".join(sep) + " |\n")
        for r in rows:
            fh.write("| " + " | ".join(str(x) for x in r) + " |\n")


def write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")     # ';' para que Excel en español separe bien
        w.writerow(header)
        w.writerows(rows)


def write_html(path, header, rows, caption=None):
    css = ("border-collapse:collapse;font-family:Calibri,Arial,sans-serif;font-size:11pt")
    th = "border:1px solid #c9d3de;background:#12263a;color:#fff;padding:5px 9px;text-align:left"
    td = "border:1px solid #c9d3de;padding:5px 9px"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f'<table style="{css}">\n')
        if caption:
            fh.write(f'<caption style="caption-side:bottom;text-align:left;'
                     f'font-size:9.5pt;color:#5b6b7c;padding-top:6px">{html.escape(caption)}</caption>\n')
        fh.write("<tr>" + "".join(f'<th style="{th}">{html.escape(str(h))}</th>'
                                  for h in header) + "</tr>\n")
        for r in rows:
            fh.write("<tr>" + "".join(f'<td style="{td}">{html.escape(str(x))}</td>'
                                      for x in r) + "</tr>\n")
        fh.write("</table>\n")


def emit(stem, header, rows, caption=None):
    write_md(stem + ".md", header, rows)
    write_csv(stem + ".csv", header, rows)
    write_html(stem + ".html", header, rows, caption)
    print(f"  {stem}.md / .csv / .html")


def main(path="contacts.json"):
    data = json.load(open(path, encoding="utf-8"))
    ligs = data["ligands"]
    site_label = data.get("site_label", "el sitio")
    hl_label = data.get("highlight_label", "residuos destacados")
    hl = set(data.get("highlight_residues", []))
    tiene_sitio = any(l.get("n_site") is not None for l in ligs)
    tiene_score = any(l.get("score") is not None for l in ligs)

    # ---------------- tabla de resumen ----------------
    header = ["Compuesto"]
    if tiene_score:
        header.append("Afinidad (kcal/mol)")
    header.append("Residuos en contacto")
    if tiene_sitio:
        header.append(f"En {site_label}")
    header.append("Puentes de hidrógeno")
    if hl:
        header.append(hl_label.capitalize())

    rows = []
    for lig in ligs:
        row = [lig["label"]]
        if tiene_score:
            row.append(f"{lig['score']:.2f}" if lig.get("score") is not None else "—")
        row.append(lig["n_total"])
        if tiene_sitio:
            row.append(f"{lig['n_site']} de {lig['n_total']}"
                       if lig.get("n_site") is not None else "—")
        row.append(lig["n_hbond"])
        if hl:
            hits = sorted((c for c in lig["contacts"] if c["num"] in hl),
                          key=lambda c: (c["rank"], c["d"]))
            if hits:
                row.append(" + ".join(
                    f"{residuo(c)} {c['d']:.2f} Å"
                    + ("" if c["kind"] == "H-bond" else " (hidrofóbico)") for c in hits))
            else:
                row.append("sin contacto")
        rows.append(row)

    print("Tablas generadas:")
    emit("tabla_resumen", header, rows,
         "Resumen de los complejos: afinidad, contactos e interacción con "
         + hl_label if hl else "Resumen de los complejos.")

    # ---------------- una tabla de contactos por ligando ----------------
    cab = ["Residuo", "Distancia (Å)", "Tipo", "Átomos (receptor···ligando)"]
    todos = []
    for lig in ligs:
        filas = []
        for c in lig["contacts"]:
            marca = "  ←" if c["num"] in hl else ""
            filas.append([residuo(c) + marca, f"{c['d']:.2f}",
                          "puente de hidrógeno" if c["kind"] == "H-bond" else "hidrofóbico",
                          f"{c['ratom']}···{c['latom']}"])
            todos.append([lig["label"]] + filas[-1])
        emit(f"tabla_contactos_{lig['id']}", cab, filas,
             f"Contactos de {lig['label']} con el receptor, ordenados por tipo y distancia.")

    write_csv("tabla_contactos_todos.csv", ["Compuesto"] + cab, todos)
    print("  tabla_contactos_todos.csv")

    # ---------------- vista rápida en consola ----------------
    anchos = [max(len(str(r[i])) for r in [header] + rows) for i in range(len(header))]
    print()
    print("  " + "  ".join(str(h).ljust(anchos[i]) for i, h in enumerate(header)))
    print("  " + "  ".join("-" * a for a in anchos))
    for r in rows:
        print("  " + "  ".join(str(x).ljust(anchos[i]) for i, x in enumerate(r)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "contacts.json"))
