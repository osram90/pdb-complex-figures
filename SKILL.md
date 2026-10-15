---
name: pdb-complex-figures
description: Genera figuras y tablas de complejos proteína-ligando con calidad de publicación a partir de archivos PDB/PDBQT — superficie molecular completa más un detalle del sitio de unión con los puentes de hidrógeno acotados, y las tablas de resultados y de contactos en Markdown, CSV y HTML. Úsala siempre que el usuario mencione figuras de acoplamiento molecular o docking, poses de AutoDock Vina, complejos proteína-ligando, visualizar un sitio de unión o un bolsillo, interacciones ligando-receptor, mapas de contactos, archivos .pdbqt o _out.pdbqt, o pida "una figura como la del paper" de una estructura, o la tabla de contactos o de afinidades de un acoplamiento; también cuando pida figuras tipo PyMOL o ChimeraX de un complejo, aunque no nombre ninguna de esas herramientas.
---

# Figuras de complejos proteína-ligando

Produce una figura de dos paneles por ligando, el formato habitual en artículos de
acoplamiento molecular:

- **Panel A** — superficie molecular de toda la proteína, con el sitio de unión en
  violeta y los residuos destacados (catalíticos, por ejemplo) en rojo tenue. Sitúa el
  complejo: el lector ve *dónde* se une el ligando.
- **Panel B** — detalle del bolsillo: residuos de contacto en sticks verdes, ligando en
  su color y los puentes de hidrógeno punteados con su distancia rotulada. Muestra *cómo*
  se une.

Ambos paneles van unidos por un círculo y dos líneas guía, con la afinidad destacada y,
si hay varias poses, una barra por pose. Se entregan las dos versiones: **la figura
conjunta** con todos los ligandos y **una figura individual por compuesto**.

Además genera las **tablas de resultados** a partir de los mismos datos que la figura —
de modo que no puedan contradecirla— en Markdown, CSV y HTML.

El renderizado usa **3Dmol.js en el navegador**, no PyMOL. Esta decisión es deliberada:
`pymol-open-source` falla al importarse en muchos equipos Windows (error de carga de DLL)
y arrastra dependencias pesadas. 3Dmol.js calcula la misma superficie molecular de
Connolly, se ejecuta en cualquier parte y exporta el lienzo a PNG.

## Requisitos

```bash
pip install scipy numpy pillow
```

Hace falta además un navegador que puedas controlar (el panel del navegador de Claude
sirve) para el paso de captura, y una proteína y una o más poses en PDB o PDBQT.

## Antes de empezar: ¿son poses acopladas?

Esto es lo primero, y conviene no saltárselo. Un archivo de ligando **no dice** si
contiene una pose acoplada (el resultado del acoplamiento) o solo la molécula preparada
(la entrada). Si dibujas lo segundo creyendo que es lo primero, obtienes una figura
convincente y falsa: el ligando aparece atravesando el interior de la proteína y las
"interacciones" medidas son contactos entre átomos superpuestos.

La diferencia se detecta por geometría, y `validate_poses.py` lo hace automáticamente:

| | Ligando de entrada | Pose acoplada |
|---|---|---|
| Centro | suele ser (0, 0, 0) | dentro de la caja de búsqueda |
| Distancia mínima al receptor | < 1 Å (imposible) | 2.5–3.5 Å |
| Átomos en choque (< 2.2 Å) | muchos | ninguno |

Si la validación falla, **detente y dilo**. No hay figura que dibujar: hay que ejecutar
el acoplamiento y usar los archivos de salida (`*_out.pdbqt` en AutoDock Vina).

## Configuración

Crea `complex.json` en el directorio de trabajo. Lo mínimo es el receptor y los ligandos;
el resto tiene valores por omisión razonables.

```json
{
  "receptor": "proteina.pdb",
  "title": "Mi proteína – complejos proteína–ligando",
  "highlight_residues": [69, 300],
  "highlight_label": "diada catalítica",
  "outfile": "FIGURA_complejos.png",
  "port": 8766,
  "ligands": [
    {"name": "Compuesto_A", "pose": "Compuesto_A_out.pdbqt", "color": "#ff2d55"},
    {"name": "Compuesto_B", "pose": "Compuesto_B_out.pdbqt", "color": "#ff9500",
     "label": "Compuesto β"}
  ]
}
```

| Clave | Para qué |
|---|---|
| `receptor` | PDB de la proteína, **con su numeración original** (ver abajo) |
| `ligands[].pose` | Salida de Vina (`_out.pdbqt`, multi-MODEL) o un PDB con la pose |
| `ligands[].color` | Color del ligando; si se omite, se asigna uno de una paleta |
| `ligands[].label` | Nombre a mostrar; útil para acentos y griegas |
| `ligands[].score` | Afinidad; si la pose viene de Vina se lee sola del archivo |
| `site_residues` | Residuos que delimitan la cavidad (de CB-Dock2 u otro análisis). Si se indican, la figura y las tablas informan cuántos contactos caen dentro |
| `site_label` | Cómo nombrar esa región: «la cavidad 1», «el sitio activo»… |
| `highlight_residues` | Números de residuo a pintar en rojo (sitio catalítico, mutaciones…) |
| `model` | Qué pose usar del multi-MODEL. Por omisión 1, la de mejor afinidad |
| `hbond_max`, `hydrophobic_max` | Umbrales en Å (3.5 y 4.5 por omisión) |

**Usa siempre el PDB original como receptor, no el PDBQT.** Las herramientas de
preparación (OpenBabel entre ellas) renumeran los residuos al escribir el PDBQT, así que
los contactos medidos sobre él salen con las etiquetas equivocadas: lo que parece
«Thr36» puede ser en realidad Cys36. Si tienes una lista externa de los residuos del
sitio (de CB-Dock2, por ejemplo) comprueba que la identidad de los aminoácidos coincida
con la numeración antes de seguir.

## Procedimiento

Ejecuta los scripts desde el directorio que contiene los archivos de entrada.

### 1. Validar las poses

```bash
python validate_poses.py
```

Imprime centro, distancia mínima y choques de cada pose. Devuelve código 1 si alguna no
es creíble. No continúes si falla.

### 2. Medir los contactos

```bash
python analyze_contacts.py
```

Extrae cada pose a PDB y mide las distancias contra el receptor. Clasifica cada contacto:
puente de hidrógeno si ambos átomos son polares (N, O, S) y están a ≤ 3.5 Å; hidrofóbico
si interviene un carbono a ≤ 4.5 Å. Conserva un contacto por residuo, el más corto, con
prioridad al puente de hidrógeno.

Produce `contacts.json`, que alimenta los pasos siguientes, y un `*_pose.pdb` por ligando.

Es un criterio **solo de distancia**: no comprueba el ángulo donador–H–aceptor. Si el
usuario va a publicar el recuento, conviene decírselo — es una estimación razonable del
patrón de interacción, no una medida definitiva.

### 3. Generar las tablas

```bash
python make_tables.py
```

Solo necesita `contacts.json`, así que puede ejecutarse en cuanto termine el paso
anterior, sin esperar a las figuras. Produce la tabla de resumen (una fila por ligando:
afinidad, contactos, contactos dentro de la cavidad, puentes de hidrógeno e interacción
con los residuos destacados) y una tabla de contactos por ligando.

Cada tabla se escribe en tres formatos porque el destino cambia: `.md` para el
manuscrito, `.csv` para Excel y `.html` para pegar en Word conservando el formato.

### 4. Construir las escenas

```bash
python build_views.py
```

Genera `view_<id>.html` por ligando. La cámara se orienta automáticamente hacia el
bolsillo: calcula el vector del centro de la proteína al centro del ligando y rota la
escena para mirarlo de frente.

### 5. Capturar los lienzos

Levanta el servidor en segundo plano (sirve las páginas y recibe los PNG por POST, para
no mover megabytes de base64 por la conversación):

```bash
python capture_server.py &
```

Después, **por cada ligando**: abre `http://localhost:<puerto>/view_<id>.html` en el
navegador, espera a que `window.ready` sea `true` y envía los dos lienzos. Con las
herramientas del navegador de Claude, en un solo paso por ligando:

```javascript
for (let i = 0; i < 80 && !window.ready; i++) await new Promise(r => setTimeout(r, 500));
if (!window.ready) throw new Error('timeout');
const s = async (n, d) => (await fetch('http://localhost:8766/save?name=' + n,
                                       {method:'POST', body:d})).status;
({A: await s('cap_<id>_A', window.pngA), B: await s('cap_<id>_B', window.pngB)})
```

`<id>` es el nombre del ligando con los caracteres no alfanuméricos sustituidos por `_`;
es el mismo que aparece en el nombre del HTML. La espera no es un capricho: las
superficies se calculan de forma asíncrona y capturar antes produce imágenes sin
superficie o a medio dibujar.

### 6. Componer las figuras

```bash
python compose_figure.py
```

Escribe la figura conjunta (300 ppp) y una figura individual por ligando. Las dos se
entregan siempre: la conjunta sirve para el artículo y las individuales para la
presentación o el anexo.

### 7. Revisar

Mira la figura antes de darla por terminada y señala tú mismo los defectos. Los que
aparecen con más frecuencia: etiquetas de residuo encimadas cuando hay muchos puentes de
hidrógeno próximos, el ligando poco visible en el panel A si la cavidad es profunda, y
superficies incompletas si alguna captura se adelantó.

## Ajustes frecuentes

**El ligando no se ve en el panel A.** Es normal en cavidades profundas: la superficie
opaca lo tapa. El parche violeta marca dónde está el sitio, que suele bastar. Si la unión
es superficial y quieres verlo directamente, sube la opacidad de la superficie general a
1.0 en `build_views.py`.

**Las etiquetas se enciman.** `build_views.py` las abre en abanico con `screenOffset`
(lista `offsets`). Amplía las separaciones o reduce a 3 el número de puentes rotulados.

**Demasiados residuos en el panel B.** Baja `hydrophobic_max` a 4.0 Å: entran menos
residuos y el detalle respira.

**Estructuras experimentales en lugar de acoplamiento.** Funciona igual: separa el
ligando del PDB del complejo a un archivo aparte y pásalo como `pose`. No habrá
afinidades y la figura omitirá el recuadro y las barras, que es lo correcto.

**Más de 4 o 5 ligandos.** La figura crece hacia abajo y se vuelve incómoda. Conviene
partirla en dos figuras o entregar las individuales.

## Problemas conocidos

| Síntoma | Causa | Solución |
|---|---|---|
| El ligando no aparece en el render | En 3Dmol.js el selector `{model: <objeto>}` no funciona | Selecciona por índice (`{model:1}`) o por residuo (`{resn:"LIG"}`); los scripts ya lo hacen |
| Imagen sin superficie o incompleta | Se capturó antes de que resolvieran las promesas de `addSurface` | Espera a `window.ready`; no acortes la espera |
| La molécula se ve sin enlaces | Columnas desalineadas en el PDB del ligando | `figlib.write_ligand_pdb` respeta las columnas fijas; no escribas el PDB a mano |
| Etiquetas con residuos equivocados | Se midieron los contactos sobre el PDBQT renumerado | Usa el PDB original como `receptor` |
| `OSError: [Errno 22]` al guardar el PNG | El archivo está abierto en un visor (Windows) | Ciérralo o cambia `outfile` |
| El panel B sale casi vacío | El ligando apenas toca la proteína | Revisa la validación: puede que la pose no sea buena |

## Archivos que produce

| Archivo | Contenido |
|---|---|
| `contacts.json` | Todos los contactos con distancia, tipo y coordenadas de ambos átomos |
| `<ligando>_pose.pdb` | La pose aislada, lista para abrir en cualquier visualizador |
| `view_<id>.html` | Escena 3D interactiva; se abre en el navegador y se puede rotar |
| `cap_<id>_A.png`, `cap_<id>_B.png` | Los lienzos capturados |
| `FIGURA_*.png` | La figura conjunta y las individuales, a 300 ppp |
| `tabla_resumen.md/.csv/.html` | Una fila por ligando: afinidad, contactos y residuos destacados |
| `tabla_contactos_<id>.md/.csv/.html` | Todos los contactos de ese ligando |
| `tabla_contactos_todos.csv` | Los contactos de todos los ligandos juntos |

Los HTML son útiles por sí mismos: permiten al usuario explorar el complejo y elegir otra
orientación si la automática no le convence.
