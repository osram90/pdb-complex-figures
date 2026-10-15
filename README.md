# pdb-complex-figures

Figuras **y tablas** de complejos proteína–ligando con calidad de publicación, a partir
de archivos PDB o PDBQT. Empaquetado como **Skill de Claude**, pero los scripts
funcionan por sí solos desde la línea de comandos.

> *Publication-quality protein–ligand complex figures from PDB/PDBQT files: molecular
> surface overview plus a binding-site close-up with annotated hydrogen bonds. Packaged
> as a Claude Skill; the Python scripts also run standalone. Documentation in Spanish.*

## Qué produce

Una figura de dos paneles por ligando, el formato habitual en artículos de acoplamiento
molecular:

- **Panel A** — superficie molecular de toda la proteína, con el sitio de unión en
  violeta y los residuos destacados (catalíticos, por ejemplo) en rojo tenue. Muestra
  *dónde* se une el ligando.
- **Panel B** — detalle del bolsillo: residuos de contacto en sticks verdes, ligando en
  su color y los puentes de hidrógeno punteados con su distancia rotulada. Muestra *cómo*
  se une.

Los dos paneles van unidos por un círculo y líneas guía, con la afinidad destacada y, si
hay varias poses, una barra por pose. Se entregan las dos versiones —la **figura
conjunta** y una **figura individual por compuesto**—, a 300 ppp, más la escena 3D
interactiva en HTML.

También genera las **tablas de resultados** desde los mismos datos que la figura, de modo
que no puedan contradecirla:

| Compuesto | Afinidad (kcal/mol) | Residuos en contacto | En la cavidad 1 | Puentes de hidrógeno | Diada catalítica |
| --- | --- | --- | --- | --- | --- |
| Dolutegravir | −9.08 | 17 | 15 de 17 | 6 | Asp300 3.65 Å (hidrofóbico) |
| Hiperósido | −8.72 | 21 | 21 de 21 | 10 | Asp300 2.99 Å + Asp69 3.02 Å |

Cada tabla se escribe en Markdown (para el manuscrito), CSV (para Excel) y HTML (para
pegar en Word conservando el formato), más una tabla de contactos por ligando.

## Por qué 3Dmol.js y no PyMOL

`pymol-open-source` falla al importarse en muchos equipos Windows (error de carga de DLL)
y arrastra dependencias pesadas. 3Dmol.js calcula la misma superficie molecular de
Connolly, se ejecuta en cualquier navegador y exporta el lienzo a PNG.

## Validación antes de dibujar

El paso que más suele omitirse y el que más importa. Un archivo de ligando **no dice** si
contiene una pose acoplada (resultado) o la molécula preparada (entrada). Dibujar lo
segundo creyendo que es lo primero produce una figura convincente y falsa: el ligando
aparece atravesando el interior de la proteína y las «interacciones» medidas son
contactos entre átomos superpuestos.

`validate_poses.py` lo detecta por geometría y detiene el proceso:

| | Ligando de entrada | Pose acoplada |
|---|---|---|
| Centro | suele ser (0, 0, 0) | dentro de la caja de búsqueda |
| Distancia mínima al receptor | < 1 Å (imposible) | 2.5–3.5 Å |
| Átomos en choque (< 2.2 Å) | muchos | ninguno |

## Instalación

```bash
pip install scipy numpy pillow
```

Hace falta además un navegador para el paso de captura.

**Como Skill de Claude:** descargue `pdb-complex-figures.skill` y ábralo en Claude; el
botón «Save skill» lo instala. A partir de ahí se activa solo cuando pida figuras de un
complejo o de poses de acoplamiento.

**Como scripts sueltos:** copie el contenido de `scripts/` al directorio donde estén sus
archivos y siga el procedimiento de abajo.

## Uso

Cree un `complex.json` en el directorio de trabajo (hay un ejemplo en `assets/`):

```json
{
  "receptor": "proteina.pdb",
  "title": "Mi proteína – complejos proteína–ligando",
  "site_residues": [48, 49, 67, 69, 71, 72],
  "site_label": "la cavidad 1",
  "highlight_residues": [69, 300],
  "highlight_label": "diada catalítica",
  "outfile": "FIGURA_complejos.png",
  "ligands": [
    {"name": "Compuesto_A", "pose": "Compuesto_A_out.pdbqt", "color": "#ff2d55"},
    {"name": "Compuesto_B", "pose": "Compuesto_B_out.pdbqt", "color": "#ff9500"}
  ]
}
```

Y ejecute, en orden:

```bash
python validate_poses.py      # 1. ¿son poses acopladas? se detiene si no
python analyze_contacts.py    # 2. mide y clasifica los contactos -> contacts.json
python make_tables.py         # 3. tablas en .md, .csv y .html
python build_views.py         # 4. genera las escenas 3D (view_*.html)
python capture_server.py &    # 5. sirve las páginas y recibe los PNG
#    abrir view_<id>.html, esperar a window.ready y volcar window.pngA / pngB
python compose_figure.py      # 6. figura conjunta + una por compuesto
```

El paso 5 requiere abrir cada página en el navegador y enviar los dos lienzos al
servidor. `SKILL.md` incluye el fragmento de JavaScript para hacerlo; si usa la Skill
dentro de Claude, ese paso se automatiza.

**Importante:** use siempre el **PDB original** como receptor, no el PDBQT. Las
herramientas de preparación (OpenBabel entre ellas) renumeran los residuos al escribir el
PDBQT, y los contactos medidos sobre él salen con las etiquetas equivocadas.

## Contenido

| Archivo | Función |
|---|---|
| `SKILL.md` | Procedimiento completo, ajustes y problemas conocidos |
| `scripts/validate_poses.py` | Comprueba que las poses son físicamente posibles |
| `scripts/analyze_contacts.py` | Extrae las poses y mide los contactos |
| `scripts/make_tables.py` | Tablas de resumen y de contactos en tres formatos |
| `scripts/build_views.py` | Genera las escenas 3Dmol.js |
| `scripts/capture_server.py` | Sirve las páginas y recibe los PNG |
| `scripts/compose_figure.py` | Compone la figura conjunta y las individuales |
| `scripts/figlib.py` | Lectores de PDB/PDBQT compartidos |
| `assets/complex.example.json` | Configuración de ejemplo |

## Criterios de contacto

Puente de hidrógeno si ambos átomos son polares (N, O, S) y están a ≤ 3.5 Å; contacto
hidrofóbico si interviene un carbono a ≤ 4.5 Å. Se conserva un contacto por residuo, el
más corto, con prioridad al puente de hidrógeno. Ambos umbrales son configurables.

Es un criterio **solo de distancia**: no comprueba el ángulo donador–H–aceptor. El
recuento es una estimación razonable del patrón de interacción, no una medida definitiva.

## Problemas conocidos

| Síntoma | Causa | Solución |
|---|---|---|
| El ligando no aparece en el render | En 3Dmol.js el selector `{model: <objeto>}` no funciona | Seleccionar por índice o por residuo; los scripts ya lo hacen |
| Imagen sin superficie o incompleta | Se capturó antes de que resolvieran las promesas de `addSurface` | Esperar a `window.ready` |
| La molécula se ve sin enlaces | Columnas desalineadas en el PDB del ligando | Usar `figlib.write_ligand_pdb`, que respeta el formato |
| Etiquetas con residuos equivocados | Contactos medidos sobre el PDBQT renumerado | Usar el PDB original como receptor |

## Licencia

MIT. Ver [LICENSE](LICENSE).
