"""Comprueba que las poses son complejos físicamente posibles antes de dibujarlos.

Un archivo de ligando no dice si contiene una pose acoplada o solo la molécula
preparada. La diferencia se ve en la geometría: una pose real toca al receptor a
2.5-3.5 A; un ligando de entrada suele estar centrado en el origen y, si el
receptor también lo está, aparece empotrado en su núcleo por coincidencia.

Uso:  python validate_poses.py [complex.json]
Sale con código 1 si alguna pose no es creíble.
"""
import sys, numpy as np
from scipy.spatial import cKDTree
from figlib import load_config, read_receptor, read_ligand

CLASH = 2.2      # por debajo de esto dos átomos pesados se estorban
MIN_OK = 2.2     # distancia mínima creíble para un contacto real
MAX_OK = 4.0     # si el átomo más cercano está más lejos, el ligando no toca nada


def main(cfg_path="complex.json"):
    cfg = load_config(cfg_path)
    rec = read_receptor(cfg["receptor"])
    tree = cKDTree(np.array([a["xyz"] for a in rec]))
    print(f"Receptor: {cfg['receptor']}  ({len(rec)} átomos pesados)\n")
    print(f"{'ligando':18s} {'centro de la pose':28s} {'d_min':>7s} {'choques':>9s}  veredicto")
    print("-" * 86)

    problems = []
    for lig in cfg["ligands"]:
        atoms = read_ligand(lig["pose"], cfg["model"])
        xyz = np.array([a["xyz"] for a in atoms])
        d, _ = tree.query(xyz)
        clashes = int((d < CLASH).sum())
        dmin = float(d.min())
        if dmin < MIN_OK or clashes:
            verdict, ok = "NO es una pose acoplada", False
        elif dmin > MAX_OK:
            verdict, ok = "el ligando no toca el receptor", False
        else:
            verdict, ok = "correcta", True
        if not ok:
            problems.append((lig["name"], verdict))
        print(f"{lig['name']:18s} {str(np.round(xyz.mean(0), 2)):28s} "
              f"{dmin:7.2f} {clashes:4d}/{len(atoms):<4d}  {verdict}")

    if problems:
        print("\nSe detuvo la validación. Poses no utilizables:")
        for name, why in problems:
            print(f"  - {name}: {why}")
        print("\nSi los archivos están centrados en (0,0,0) y chocan con el receptor, "
              "son ligandos de ENTRADA, no resultados.\nHay que ejecutar el "
              "acoplamiento y usar los archivos de salida.")
        return 1

    print("\nTodas las poses pasan la validación geométrica.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "complex.json"))
