"""Utilidades compartidas por los scripts de pdb-complex-figures."""
import json, os, re, sys

AUTODOCK_TO_ELEMENT = {
    "A": "C", "C": "C", "N": "N", "NA": "N", "NS": "N", "OA": "O", "O": "O",
    "SA": "S", "S": "S", "F": "F", "CL": "CL", "BR": "BR", "I": "I", "P": "P",
    "MG": "MG", "ZN": "ZN", "FE": "FE", "CA": "CA", "MN": "MN",
}
POLAR = {"N", "O", "S"}
DEFAULT_COLORS = ["#ff2d55", "#ff9500", "#ffd60a", "#30d158",
                  "#0a84ff", "#bf5af2", "#64d2ff", "#ff6482"]


def load_config(path="complex.json"):
    """Lee el archivo de configuración y rellena los valores por omisión."""
    if not os.path.exists(path):
        sys.exit(f"No encuentro {path}. Crea el archivo de configuración primero "
                 f"(ver la sección «Configuración» de SKILL.md).")
    cfg = json.load(open(path, encoding="utf-8"))
    for key in ("receptor", "ligands"):
        if key not in cfg:
            sys.exit(f"Falta la clave obligatoria '{key}' en {path}.")
    cfg.setdefault("highlight_residues", [])
    cfg.setdefault("highlight_label", "residuos destacados")
    cfg.setdefault("title", "Complejos proteina-ligando")
    cfg.setdefault("subtitle", "")
    cfg.setdefault("hbond_max", 3.5)
    cfg.setdefault("hydrophobic_max", 4.5)
    cfg.setdefault("model", 1)
    cfg.setdefault("port", 8766)
    cfg.setdefault("outfile", "FIGURA_complejos.png")
    for i, lig in enumerate(cfg["ligands"]):
        lig.setdefault("label", lig["name"])
        lig.setdefault("color", DEFAULT_COLORS[i % len(DEFAULT_COLORS)])
        lig.setdefault("pose_pdb", safe(lig["name"]) + "_pose.pdb")
    return cfg


def safe(name):
    """Nombre utilizable como archivo y como identificador de HTML/JS."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", name)


def read_receptor(path, skip_hydrogens=True):
    """Átomos del receptor desde un PDB, conservando su numeración original.

    Importante: mide siempre los contactos sobre el PDB original. Las
    herramientas de preparación (OpenBabel, por ejemplo) suelen renumerar los
    residuos al escribir el PDBQT, y las etiquetas saldrían equivocadas.
    """
    atoms = []
    for line in open(path, encoding="utf-8", errors="ignore"):
        if not line.startswith("ATOM"):
            continue
        elem = (line[76:78].strip() or line[12:16].strip()[0]).upper()
        if skip_hydrogens and elem == "H":
            continue
        try:
            atoms.append(dict(
                name=line[12:16].strip(), res=line[17:20].strip(),
                num=int(line[22:26]), chain=line[21].strip() or "A", elem=elem,
                xyz=[float(line[30:38]), float(line[38:46]), float(line[46:54])]))
        except ValueError:
            continue
    if not atoms:
        sys.exit(f"{path} no contiene registros ATOM legibles.")
    return atoms


def read_ligand(path, model=1, skip_hydrogens=True):
    """Átomos de una pose. Acepta PDBQT multi-MODEL (salida de Vina) o PDB."""
    atoms, inside = [], None
    for line in open(path, encoding="utf-8", errors="ignore"):
        if line.startswith("MODEL"):
            try:
                inside = int(line.split()[1]) == model
            except (IndexError, ValueError):
                inside = True
            continue
        if line.startswith("ENDMDL"):
            if inside:
                break
            continue
        if inside is False:
            continue
        if not line.startswith(("ATOM", "HETATM")):
            continue
        raw = line[76:79].strip().upper()
        elem = AUTODOCK_TO_ELEMENT.get(raw, raw[:1] if raw else "C")
        if raw in ("HD", "H") or (skip_hydrogens and elem == "H"):
            continue
        try:
            atoms.append(dict(name=line[12:16].strip(), elem=elem,
                              xyz=[float(line[30:38]), float(line[38:46]), float(line[46:54])]))
        except ValueError:
            continue
    if not atoms:
        sys.exit(f"{path} no contiene átomos legibles (¿existe el MODEL {model}?).")
    return atoms


def vina_scores(path):
    """Afinidades de todas las poses de una salida de Vina, si las hay."""
    try:
        txt = open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return []
    return [float(m) for m in re.findall(r"VINA RESULT:\s+(-?\d+\.\d+)", txt)]


def write_ligand_pdb(atoms, path, resname="LIG", resseq=900, chain="A"):
    """Escribe la pose como PDB respetando las columnas fijas del formato.

    Un solo carácter de desplazamiento y el visualizador no reconoce la
    molécula: no dibuja enlaces o directamente no la muestra.
    """
    with open(path, "w", encoding="utf-8") as fh:
        for i, a in enumerate(atoms, 1):
            e = a["elem"]
            nm = f" {e}{i:<2d}"[:4] if len(e) == 1 else f"{e}{i:<2d}"[:4]
            fh.write(f"HETATM{i:5d} {nm} {resname:>3s} {chain}{resseq:4d}    "
                     f"{a['xyz'][0]:8.3f}{a['xyz'][1]:8.3f}{a['xyz'][2]:8.3f}"
                     f"  1.00  0.00          {e:>2s}\n")
        fh.write("END\n")
    return len(atoms)


def write_receptor_view(src, dst="receptor_view.pdb"):
    """Copia del receptor sin MODEL/ENDMDL, que confunden al parser de 3Dmol.js."""
    with open(src, encoding="utf-8", errors="ignore") as f, open(dst, "w", encoding="utf-8") as o:
        for line in f:
            if line.startswith(("ATOM", "TER")):
                o.write(line)
        o.write("END\n")
    return dst
