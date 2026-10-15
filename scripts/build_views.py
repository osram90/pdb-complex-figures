"""Genera una página 3Dmol.js por ligando con las dos vistas de la figura.

Panel A  superficie molecular completa; sitio de unión en violeta y residuos
         destacados en rojo tenue. Sitúa el complejo en la proteína.
Panel B  detalle del bolsillo: residuos de contacto en sticks verdes, residuos
         destacados en rojo, ligando en su color y puentes de hidrógeno
         punteados con su distancia.

Uso:  python build_views.py [contacts.json]
"""
import json, sys, numpy as np
from figlib import read_receptor

W, H = 1100, 900          # tamaño de cada lienzo; define la resolución final
VIOLET, CORAL, GREY = "#8b5cf6", "#e0827c", "#cdd4dc"

TPL = """<!DOCTYPE html><html><head><meta charset="utf-8">
<script src="https://3Dmol.csb.pitt.edu/build/3Dmol-min.js"></script>
<style>body{margin:0;background:#fff}.v{width:%(W)dpx;height:%(H)dpx;display:inline-block}</style>
</head><body>
<div id="A" class="v"></div><div id="B" class="v"></div>
<script>
const REC=`%(REC)s`, LIG=`%(LIG)s`, C="%(COLOR)s";
const SITE=%(SITE)s, HL=%(HL)s, HB=%(HB)s, AZ=%(AZ).4f, EL=%(EL).4f;
window.ready=false;
const orient=v=>{v.rotate(AZ,"y");v.rotate(EL,"x");};

/* ---- A: superficie molecular completa ---- */
const vA=$3Dmol.createViewer("A",{backgroundColor:"white",antialias:true});
vA.addModel(REC,"pdb"); vA.addModel(LIG,"pdb");
vA.setStyle({},{});
vA.setStyle({resn:"LIG"},{stick:{radius:0.30,color:C},sphere:{radius:0.42,color:C}});
const pA=[
  vA.addSurface($3Dmol.SurfaceType.MS,{opacity:0.90,color:"%(GREY)s"},{model:0}),
  vA.addSurface($3Dmol.SurfaceType.MS,{opacity:1.00,color:"%(VIOLET)s"},{model:0,resi:SITE})
];
if (HL.length) pA.push(
  vA.addSurface($3Dmol.SurfaceType.MS,{opacity:1.00,color:"%(CORAL)s"},{model:0,resi:HL}));

/* ---- B: detalle del bolsillo ---- */
const vB=$3Dmol.createViewer("B",{backgroundColor:"white",antialias:true});
vB.addModel(REC,"pdb"); vB.addModel(LIG,"pdb");
vB.setStyle({},{});
vB.setStyle({model:0,resi:SITE},{stick:{radius:0.14,colorscheme:"greenCarbon"}});
if (HL.length) vB.setStyle({model:0,resi:HL},{stick:{radius:0.20,color:"%(CORAL)s"}});
vB.setStyle({resn:"LIG"},{stick:{radius:0.22,color:C},sphere:{radius:0.30,color:C}});
const pB=[vB.addSurface($3Dmol.SurfaceType.MS,{opacity:0.30,color:"#b9c2cc"},
          {model:0,resi:SITE})];
HB.forEach(h=>{
  vB.addCylinder({start:{x:h.a[0],y:h.a[1],z:h.a[2]},
                  end:{x:h.b[0],y:h.b[1],z:h.b[2]},
                  radius:0.055,dashed:true,fromCap:1,toCap:1,color:"black"});
  vB.addLabel(h.d.toFixed(2)+" \\u00c5",
    {position:{x:(h.a[0]+h.b[0])/2,y:(h.a[1]+h.b[1])/2,z:(h.a[2]+h.b[2])/2},
     fontSize:15,fontColor:"black",backgroundColor:"white",backgroundOpacity:0.82,
     borderThickness:0.8,borderColor:"black",inFront:true});
  vB.addLabel(h.label,{position:{x:h.a[0],y:h.a[1],z:h.a[2]},
     fontSize:15,fontColor:"#14532d",backgroundColor:"white",backgroundOpacity:0.75,
     inFront:true,screenOffset:{x:h.off[0],y:h.off[1]}});
});

/* Las superficies se calculan de forma asíncrona: si se captura antes de que
   resuelvan, la imagen sale incompleta o sin superficie. */
Promise.all([...pA,...pB].map(p=>Promise.resolve(p))).then(async()=>{
  vA.zoomTo({model:0}); orient(vA); vA.zoom(0.88); vA.render();
  vB.zoomTo({resn:"LIG"}); orient(vB); vB.zoom(0.50); vB.render();
  await new Promise(r=>setTimeout(r,2500));
  window.pngA=vA.pngURI(); window.pngB=vB.pngURI(); window.ready=true;
});
</script></body></html>"""


def main(path="contacts.json"):
    data = json.load(open(path, encoding="utf-8"))
    rec_view = data.get("receptor_view", "receptor_view.pdb")
    rec_txt = open(rec_view, encoding="utf-8").read()
    rec_atoms = read_receptor(data["receptor"])
    centre = np.array([a["xyz"] for a in rec_atoms]).mean(0)
    highlight = data.get("highlight_residues", [])
    # abanico de desplazamientos para que las etiquetas no se encimen
    offsets = [(-70, 26), (-70, -26), (70, 26), (70, -26), (0, 48)]

    for lig in data["ligands"]:
        site = sorted({c["num"] for c in lig["contacts"]})
        site_nohl = [r for r in site if r not in highlight]
        hb = [dict(a=c["rxyz"], b=c["lxyz"], d=c["d"],
                   label=f"{c['res']}{c['num']}", off=offsets[i % len(offsets)])
              for i, c in enumerate([x for x in lig["contacts"] if x["kind"] == "H-bond"][:5])]

        lig_txt = open(lig["pose_pdb"], encoding="utf-8").read()
        lxyz = np.array([[float(l[30:38]), float(l[38:46]), float(l[46:54])]
                         for l in lig_txt.splitlines() if l.startswith(("ATOM", "HETATM"))])
        d = lxyz.mean(0) - centre
        norm = np.linalg.norm(d)
        d = d / norm if norm > 1e-6 else np.array([0.0, 0.0, 1.0])
        az = -np.degrees(np.arctan2(d[0], d[2]))
        el = np.degrees(np.arcsin(np.clip(d[1], -1, 1)))

        html = TPL % dict(W=W, H=H, REC=rec_txt, LIG=lig_txt, COLOR=lig["color"],
                          SITE=json.dumps(site_nohl), HL=json.dumps(highlight),
                          HB=json.dumps(hb), AZ=az, EL=el,
                          GREY=GREY, VIOLET=VIOLET, CORAL=CORAL)
        out = f"view_{lig['id']}.html"
        open(out, "w", encoding="utf-8").write(html)
        print(f"{out:34s} {len(site)} residuos en el sitio · {len(hb)} H-bonds acotados")

    print("\nAhora sirve los archivos y captura los lienzos:\n"
          "  python capture_server.py      (en segundo plano)\n"
          "  abrir http://localhost:<puerto>/view_<id>.html y volcar window.pngA / pngB")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "contacts.json"))
