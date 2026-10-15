"""Extrae cada pose a PDB y mide los contactos proteína-ligando.

Produce contacts.json, que alimenta a build_views.py y compose_figure.py.

Criterios (ajustables desde complex.json):
  puente de hidrógeno  ambos átomos polares (N, O, S)   <= 3.5 A
  contacto hidrofóbico al menos un carbono              <= 4.5 A
Se conserva un contacto por residuo, el más corto, con prioridad al puente de
hidrógeno. Son criterios de distancia: no comprueban el ángulo donador-H-aceptor,
así que el recuento es una estimación razonable, no una medida definitiva.

Uso:  python analyze_contacts.py [complex.json]
"""
import json, sys, numpy as np
from scipy.spatial import cKDTree
from figlib import (load_config, read_receptor, read_ligand, vina_scores,
                    write_ligand_pdb, write_receptor_view, POLAR, safe)


def main(cfg_path="complex.json"):
    cfg = load_config(cfg_path)
    hb_max, hyd_max = cfg["hbond_max"], cfg["hydrophobic_max"]
    cut = max(hb_max, hyd_max)
    highlight = set(cfg["highlight_residues"])
    site = set(cfg["site_residues"])

    rec = read_receptor(cfg["receptor"])
    tree = cKDTree(np.array([a["xyz"] for a in rec]))
    view = write_receptor_view(cfg["receptor"])

    out = {"receptor": cfg["receptor"], "receptor_view": view,
           "site_residues": sorted(site), "site_label": cfg["site_label"],
           "highlight_residues": sorted(highlight),
           "highlight_label": cfg["highlight_label"],
           "title": cfg["title"], "subtitle": cfg["subtitle"],
           "outfile": cfg["outfile"],
           "criteria": {"hbond_max": hb_max, "hydrophobic_max": hyd_max},
           "ligands": []}

    for lig in cfg["ligands"]:
        atoms = read_ligand(lig["pose"], cfg["model"])
        pose_pdb = lig["pose_pdb"]
        write_ligand_pdb(atoms, pose_pdb)

        best = {}
        for la in atoms:
            for ri in tree.query_ball_point(la["xyz"], cut):
                ra = rec[ri]
                d = float(np.linalg.norm(np.array(la["xyz"]) - np.array(ra["xyz"])))
                polar = ra["elem"] in POLAR and la["elem"] in POLAR
                if polar and d <= hb_max:
                    kind, rank = "H-bond", 0
                elif not polar and d <= hyd_max:
                    kind, rank = "hidrofobico", 1
                else:
                    continue
                prev = best.get(ra["num"])
                if prev is None or (rank, d) < (prev["rank"], prev["d"]):
                    best[ra["num"]] = dict(
                        res=ra["res"], num=ra["num"], d=round(d, 2), kind=kind, rank=rank,
                        ratom=ra["name"], latom=la["name"],
                        rxyz=[round(v, 3) for v in ra["xyz"]],
                        lxyz=[round(v, 3) for v in la["xyz"]])
        contacts = sorted(best.values(), key=lambda c: (c["rank"], c["d"]))

        scores = vina_scores(lig["pose"])
        entry = dict(name=lig["name"], label=lig["label"], color=lig["color"],
                     pose_pdb=pose_pdb, id=safe(lig["name"]),
                     score=lig.get("score", scores[0] if scores else None),
                     poses=scores, heavy_atoms=len(atoms),
                     n_total=len(contacts),
                     n_hbond=sum(1 for c in contacts if c["kind"] == "H-bond"),
                     n_highlight=sum(1 for c in contacts if c["num"] in highlight),
                     n_site=(sum(1 for c in contacts if c["num"] in site) if site else None),
                     contacts=contacts)
        out["ligands"].append(entry)

        print(f"\n{'='*70}\n{lig['label']}"
              + (f"   {entry['score']:.2f} kcal/mol" if entry["score"] is not None else ""))
        print(f"{len(atoms)} átomos · {len(contacts)} residuos en contacto · "
              f"{entry['n_hbond']} puentes de hidrógeno")
        print(f"  {'residuo':10s} {'dist':>6s}  {'tipo':13s} {'átomos'}")
        for c in contacts[:12]:
            mark = "  <<< " + cfg["highlight_label"] if c["num"] in highlight else ""
            print(f"  {c['res']}{c['num']:<7d} {c['d']:6.2f}  {c['kind']:13s} "
                  f"{c['ratom']}···{c['latom']}{mark}")

    json.dump(out, open("contacts.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"\n{'='*70}\n-> contacts.json  ({len(out['ligands'])} ligandos)")
    print("-> " + ", ".join(l["pose_pdb"] for l in out["ligands"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "complex.json"))
