#!/usr/bin/env python3
"""Générateur du labyrinthe 16x16 de GAME, style cartoon.

Une seule source produit la topologie typée (`MazeGrid16x16.json`) et la
géométrie (`Maze16x16.fbx`). C'est le point important : tant que les deux
sortaient d'outils séparés, un mur déclaré par le JSON pouvait manquer dans le
FBX, ou l'inverse. Ici la grille est tirée d'abord, la géométrie en découle.

Direction artistique : cartoon lisible. Aplats saturés, volumes trapus et
chanfreinés, aucune sculpture bruitée. Ce que le joueur voit correspond à ce qui
l'arrête, ce qui n'était pas le cas de la map précédente :

- **aucun objet au sol dans un couloir**. Il n'y a pas de groupe `Props`.
- **la végétation ne descend jamais dans un couloir**. Elle vit sur le dessus des
  murs, au-dessus de 3,00 m, ou hors du labyrinthe. Elle n'a pas de collider et
  ne peut donc pas mentir sur un passage.
- **les murs ne sont pas sculptés**. Le corps est un prisme chanfreiné aux cotes
  exactes du design, donc la boîte de collision posée par Unity coïncide avec ce
  qu'on voit.

Repère et échelle : Blender Z-up en mètres. L'export `axis_forward=-Z`,
`axis_up=Y` envoie `(x, y, z)` sur `(-x, z, -y)` côté Unity. Un nœud de grille
`(nx, ny)` est donc placé ici en `((nx - W/2) * PITCH, (ny - H/2) * PITCH)`, ce
qui retombe exactement sur `MovableWallDirector.NodePosition`.

Contrat de grille — non négociable, le code réseau en dépend :

- `vwalls[x][y]` est l'arête verticale du nœud `(x, y)` au nœud `(x, y+1)`,
  `x` de 0 à W, `y` de 0 à H-1 ; elle sépare les cellules `(x-1, y)` et `(x, y)` ;
- `hwalls[x][y]` est l'arête horizontale du nœud `(x, y)` au nœud `(x+1, y)`,
  `x` de 0 à W-1, `y` de 0 à H ; elle sépare `(x, y-1)` et `(x, y)` ;
- état 0 vide, 1 mur statique, 2 bras de pivot ;
- le pourtour reste fermé sauf aux quatre entrées de la rangée `y = 0`.

Usage :

    blender --factory-startup --background --python build_maze_cartoon.py -- \
        --seed 20260805 --out-fbx <chemin.fbx> --out-json <chemin.json> \
        --render-dir <dossier>

Sans Blender, `python3 build_maze_cartoon.py --topology-only --out-json …`
produit la seule grille : la topologie est du Python pur, testable sans scène.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import deque
from pathlib import Path

# --------------------------------------------------------------------------
# Cotes du design. Les changer, c'est changer le jeu : le pas de grille est la
# conséquence du couloir et de l'épaisseur, pas un réglage indépendant.
# --------------------------------------------------------------------------

WIDTH = 16
HEIGHT = 16
CORRIDOR = 2.50
WALL_THICKNESS = 0.25
PITCH = CORRIDOR + WALL_THICKNESS  # 2,75 m
WALL_HEIGHT = 3.00

# Le chaperon coiffe le mur : il déborde en épaisseur pour donner une ligne
# franche vue d'en haut, et c'est lui qui porte la couleur de contraste.
CAP_HEIGHT = 0.42
CAP_OVERHANG = 0.09
BODY_HEIGHT = WALL_HEIGHT - CAP_HEIGHT

# Chanfreins : c'est tout ce qui sépare une boîte d'un volume cartoon.
CHAMFER_XY = 0.05
CHAMFER_Z = 0.06

# Appareillage de pierre. Les blocs affleurent l'épaisseur nominale du mur et ce
# sont les joints qui sont creusés : le nu extérieur reste donc à ±0,125 m de
# l'axe de l'arête, exactement là où Unity pose sa boîte de collision. Du relief
# en saillie mentirait sur l'endroit où le joueur s'arrête ; du relief en creux
# ne ment sur rien.
COURSES = 5
JOINT_WIDTH = 0.055
JOINT_DEPTH = 0.05
NICHE_DEPTH = 0.15

# Un merlon de rempart sur le pourtour : c'est ce qui donne une silhouette
# depuis l'intérieur des couloirs. Au-dessus de 3 m, donc hors d'atteinte.
MERLON_HEIGHT = 0.55
MERLON_WIDTH = 0.42

PIVOT_TOTEM_RADIUS = 0.34
PIVOT_TOTEM_HEIGHT = 3.55

# Repères hors labyrinthe : visibles par-dessus les murs de 3 m depuis un
# couloir, donc utilisables pour se situer, mais inatteignables.
TORCHES: list[tuple[float, float]] = []

TOWER_HEIGHT = 11.0
TOWER_RADIUS = 2.1

ENTRANCE_CELLS = (2, 6, 10, 14)
TREASURE_CELL = (8, 15)
PIVOT_COUNT = 17

EMPTY, STATIC, PIVOT_ARM = 0, 1, 2

# Directions en coordonnées de grille. Les lettres suivent la convention de
# `scripts/migrate-maze-topology-v1.py`, qui les lit pour dériver les états des
# bras : N = +y, S = -y, E = +x, W = -x dans le repère de la grille, sans égard
# à l'orientation du monde Unity. Elles ne sont pas documentaires — un bras
# nommé « N » doit couvrir l'arête verticale `vwalls[x][y]` de son nœud.
DIRECTIONS = {
    "N": (0, 1),
    "S": (0, -1),
    "E": (1, 0),
    "W": (-1, 0),
}


# ==========================================================================
# 1. Topologie — Python pur, aucune dépendance Blender
# ==========================================================================


class Grid:
    """Grille d'arêtes du labyrinthe, seule source de vérité de la topologie."""

    def __init__(self) -> None:
        # Tout est plein au départ : on creuse ensuite.
        self.vwalls = [[STATIC] * HEIGHT for _ in range(WIDTH + 1)]
        self.hwalls = [[STATIC] * (HEIGHT + 1) for _ in range(WIDTH)]

    # -- accès arêtes -------------------------------------------------------

    def state(self, family: int, x: int, y: int) -> int:
        return self.vwalls[x][y] if family == 0 else self.hwalls[x][y]

    def set_state(self, family: int, x: int, y: int, value: int) -> None:
        if family == 0:
            self.vwalls[x][y] = value
        else:
            self.hwalls[x][y] = value

    @staticmethod
    def is_perimeter(family: int, x: int, y: int) -> bool:
        """Même règle que `MazePlaytestBuild.IsPerimeterSlot`."""
        return (x in (0, WIDTH)) if family == 0 else (y in (0, HEIGHT))

    @staticmethod
    def edge_between(a: tuple[int, int], b: tuple[int, int]) -> tuple[int, int, int]:
        """Arête séparant deux cellules voisines."""
        (ax, ay), (bx, by) = a, b
        if ax == bx:
            return 1, ax, max(ay, by)  # horizontale
        return 0, max(ax, bx), ay  # verticale

    @staticmethod
    def edges_at_node(nx: int, ny: int) -> dict[str, tuple[int, int, int]]:
        """Les quatre arêtes qui touchent un nœud, par direction de grille.

        L'ordre d'insertion est celui du tirage aléatoire des bras : le changer
        changerait la map produite par une seed donnée.
        """
        edges: dict[str, tuple[int, int, int]] = {}
        if ny > 0:
            edges["S"] = (0, nx, ny - 1)
        if ny < HEIGHT:
            edges["N"] = (0, nx, ny)
        if nx < WIDTH:
            edges["E"] = (1, nx, ny)
        if nx > 0:
            edges["W"] = (1, nx - 1, ny)
        return edges

    # -- construction -------------------------------------------------------

    def carve(self, rng: random.Random) -> None:
        """Arbre couvrant par parcours en profondeur : le labyrinthe est connexe."""
        start = (rng.randrange(WIDTH), rng.randrange(HEIGHT))
        seen = {start}
        stack = [start]

        while stack:
            cx, cy = stack[-1]
            neighbours = []
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < WIDTH and 0 <= ny < HEIGHT and (nx, ny) not in seen:
                    neighbours.append((nx, ny))

            if not neighbours:
                stack.pop()
                continue

            nxt = rng.choice(neighbours)
            family, x, y = self.edge_between((cx, cy), nxt)
            self.set_state(family, x, y, EMPTY)
            seen.add(nxt)
            stack.append(nxt)

    def braid(self, rng: random.Random, ratio: float) -> None:
        """Ouvre des boucles.

        Un arbre parfait n'a qu'un chemin entre deux points : à six ou huit
        joueurs on se croise sans arrêt dans des culs-de-sac. Les boucles rendent
        la map jouable et donnent de l'intérêt aux murs mobiles.
        """
        candidates = [
            (family, x, y)
            for family in (0, 1)
            for x, y in self._interior_indices(family)
            if self.state(family, x, y) == STATIC
        ]
        rng.shuffle(candidates)
        for family, x, y in candidates[: int(len(candidates) * ratio)]:
            self.set_state(family, x, y, EMPTY)

    def open_entrances(self) -> list[tuple[int, int]]:
        """Quatre entrées sur la rangée y = 0, côté +Z une fois dans Unity."""
        cells = []
        for cx in ENTRANCE_CELLS:
            self.hwalls[cx][0] = EMPTY
            cells.append((cx, 0))
        return cells

    def place_pivots(self, rng: random.Random) -> list[dict]:
        """Pose les pivots sur des nœuds intérieurs bien répartis.

        Un pivot mange ses arêtes : elles passent en état 2 et sortent du jeu des
        murs mobiles. On ne prend donc que des nœuds où au moins deux arêtes
        intérieures sont pleines, sinon le pivot tournerait dans le vide.
        """
        nodes = [(nx, ny) for nx in range(1, WIDTH) for ny in range(1, HEIGHT)]
        rng.shuffle(nodes)

        pivots: list[dict] = []
        taken: list[tuple[int, int]] = []

        # Deux passes. La première ne retient que les nœuds à trois bras pleins,
        # parce qu'un pivot en T change vraiment la carte quand il tourne : il
        # ferme un couloir et en ouvre un autre. La seconde complète en L ou en I
        # avec ce qui reste, plutôt que de rendre la map pauvre en pivots.
        for minimum in (3, 2):
            for nx, ny in nodes:
                if len(pivots) >= PIVOT_COUNT:
                    break

                # Deux pivots collés partageraient une arête et se bloqueraient.
                if any(max(abs(nx - px), abs(ny - py)) < 3 for px, py in taken):
                    continue

                usable = {
                    name: edge
                    for name, edge in self.edges_at_node(nx, ny).items()
                    if not self.is_perimeter(*edge) and self.state(*edge) == STATIC
                }
                if len(usable) < minimum:
                    continue

                names = sorted(usable, key=lambda n: rng.random())[:3 if len(usable) >= 3 else 2]
                shape = self._shape_of(names)
                for name in names:
                    self.set_state(*usable[name], PIVOT_ARM)

                pivots.append({
                    "node": [nx, ny],
                    "shape": shape,
                    "arms": sorted(names),
                    "orientation": 0,
                })
                taken.append((nx, ny))

        return pivots

    # -- vérifications ------------------------------------------------------

    def reachable_cells(self) -> set[tuple[int, int]]:
        """Cellules atteignables depuis les entrées, pivots à l'orientation 0."""
        start = [(cx, 0) for cx in ENTRANCE_CELLS]
        seen = set(start)
        queue = deque(start)

        while queue:
            cx, cy = queue.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < WIDTH and 0 <= ny < HEIGHT) or (nx, ny) in seen:
                    continue
                if self.state(*self.edge_between((cx, cy), (nx, ny))) != EMPTY:
                    continue
                seen.add((nx, ny))
                queue.append((nx, ny))

        return seen

    def distance_from_entrances(self) -> dict[tuple[int, int], int]:
        start = [(cx, 0) for cx in ENTRANCE_CELLS]
        distances = {cell: 0 for cell in start}
        queue = deque(start)

        while queue:
            cx, cy = queue.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < WIDTH and 0 <= ny < HEIGHT) or (nx, ny) in distances:
                    continue
                if self.state(*self.edge_between((cx, cy), (nx, ny))) != EMPTY:
                    continue
                distances[(nx, ny)] = distances[(cx, cy)] + 1
                queue.append((nx, ny))

        return distances

    def movable_edges(self) -> list[tuple[int, int, int]]:
        """Arêtes statiques intérieures : exactement les murs mobiles d'Unity."""
        return [
            (family, x, y)
            for family in (0, 1)
            for x, y in self._interior_indices(family)
            if self.state(family, x, y) == STATIC
        ]

    def _interior_indices(self, family: int):
        if family == 0:
            for x in range(1, WIDTH):
                for y in range(HEIGHT):
                    yield x, y
        else:
            for x in range(WIDTH):
                for y in range(1, HEIGHT):
                    yield x, y

    @staticmethod
    def _shape_of(names: list[str]) -> str:
        if len(names) >= 3:
            return "T"
        opposites = {"N": "S", "S": "N", "E": "W", "W": "E"}
        return "I" if opposites[names[0]] == names[1] else "L"


def build_topology(seed: int) -> tuple[Grid, dict]:
    """Tire une grille jouable et son document JSON."""
    for attempt in range(200):
        rng = random.Random(seed + attempt * 7919)
        grid = Grid()
        grid.carve(rng)
        grid.braid(rng, ratio=0.11)
        entrances = grid.open_entrances()
        pivots = grid.place_pivots(rng)

        reachable = grid.reachable_cells()
        if len(pivots) < PIVOT_COUNT:
            continue
        if len(reachable) < WIDTH * HEIGHT:
            continue
        if TREASURE_CELL not in reachable:
            continue

        distances = grid.distance_from_entrances()
        movable = grid.movable_edges()
        arm_edges = sum(
            1
            for family in (0, 1)
            for x, y in grid._interior_indices(family)
            if grid.state(family, x, y) == PIVOT_ARM
        )

        payload = {
            "meta": {
                "width": WIDTH,
                "height": HEIGHT,
                "seed": seed,
                "attempt": attempt,
                "players": "6-8 joueurs",
                "style": "cartoon",
                "cell_pitch_m": PITCH,
                "wall_thickness_m": WALL_THICKNESS,
                "wall_height_m": WALL_HEIGHT,
                "edge_states": {"0": "Empty", "1": "Static", "2": "PivotArm"},
                "generator": "tools/maze-3d/build_maze_cartoon.py",
            },
            "vwalls": grid.vwalls,
            "hwalls": grid.hwalls,
            "pivots": pivots,
            "entrances": [list(cell) for cell in entrances],
            "exit": "une des 4 entrees (retour)",
            "treasure": list(TREASURE_CELL),
            "stats": {
                "grid": f"{WIDTH}x{HEIGHT}",
                "seed": seed,
                "connected": True,
                "cells_reachable": len(reachable),
                "pivot_count": len(pivots),
                "shapes": {
                    shape: sum(1 for p in pivots if p["shape"] == shape)
                    for shape in ("T", "L", "I")
                },
                "arm_edges": arm_edges,
                "movable_walls": len(movable),
                "treasure_distance": distances.get(TREASURE_CELL, -1),
            },
        }
        return grid, payload

    raise RuntimeError("aucune grille jouable trouvée : élargir la recherche de seed")


# ==========================================================================
# 2. Géométrie Blender
# ==========================================================================
#
# Tout le décor est peint par **couleurs de sommet**, pas par un matériau plat
# par teinte. C'est le point qui décide de l'aspect : une couleur unique par
# matériau donne une surface en plastique, quelle que soit la finesse du
# maillage. En jittant la teinte de chaque pierre, de chaque feuille et de
# chaque face, on obtient le grain d'un décor peint à la main — et un seul
# matériau par famille de surface, donc moins d'appels de rendu, pas plus.


def node_xy(nx: float, ny: float) -> tuple[float, float]:
    """Nœud de grille vers le plan Blender. Miroir exact de NodePosition côté Unity."""
    return (nx - WIDTH / 2.0) * PITCH, (ny - HEIGHT / 2.0) * PITCH


# -- palette : valeurs linéaires, saturées, à écarts de valeur nets ---------

STONE_TONES = (
    (0.80, 0.66, 0.45),
    (0.74, 0.60, 0.40),
    (0.86, 0.72, 0.50),
    (0.70, 0.57, 0.38),
    (0.83, 0.69, 0.47),
    (0.77, 0.63, 0.42),
)
STONE_MOSSY = (0.52, 0.55, 0.32)
STONE_CORE = (0.22, 0.17, 0.11)
STONE_QUOIN = (0.66, 0.51, 0.32)

CAP_TONES = {
    "ne": (0.14, 0.46, 0.29),   # cuivre patiné
    "nw": (0.18, 0.38, 0.48),   # ardoise
    "se": (0.66, 0.28, 0.12),   # terre cuite
    "sw": (0.40, 0.48, 0.16),   # olive
}

BANNER_TONES = ((0.62, 0.12, 0.12), (0.14, 0.22, 0.55), (0.72, 0.46, 0.06))
GOLD = (0.86, 0.62, 0.14)
PIVOT_STONE = ((0.68, 0.28, 0.10), (0.60, 0.23, 0.08), (0.74, 0.33, 0.13))
PIVOT_TOTEM_TONE = (0.20, 0.19, 0.44)

GRASS_TONES = ((0.20, 0.44, 0.14), (0.24, 0.50, 0.16), (0.17, 0.38, 0.12))
PAVING_TONES = ((0.48, 0.44, 0.36), (0.43, 0.39, 0.32), (0.52, 0.48, 0.39))
FIELD_TONE = (0.26, 0.50, 0.18)
LEAF_TONES = ((0.13, 0.36, 0.14), (0.17, 0.44, 0.17), (0.10, 0.29, 0.12), (0.22, 0.48, 0.18))
TRUNK_TONE = (0.30, 0.19, 0.10)
ROCK_TONES = ((0.42, 0.41, 0.38), (0.36, 0.35, 0.33))
TOWER_ROOF = (0.60, 0.16, 0.14)


def jitter(colour, rng, amount=0.05, value=0.0):
    """Teinte voisine : c'est ce qui empêche une surface de sonner plastique."""
    scale = 1.0 + value
    return tuple(
        max(0.0, min(1.0, channel * scale + rng.uniform(-amount, amount)))
        for channel in colour
    )


def pick(tones, rng):
    return tones[rng.randrange(len(tones))]


# -- primitives -------------------------------------------------------------


def chamfered_prism(cx, cy, z0, z1, sx, sy, chamfer_xy=CHAMFER_XY, chamfer_z=CHAMFER_Z):
    """Prisme à arêtes cassées : la brique de base du style.

    Section en octogone — les quatre coins verticaux sont coupés — et une
    couronne de chanfrein sous le dessus. C'est ce qui accroche la lumière et
    donne le volume trapu du cartoon, sans un seul modificateur.
    """
    hx, hy = sx / 2.0, sy / 2.0
    c = min(chamfer_xy, hx * 0.6, hy * 0.6)

    def ring(inset: float, z: float):
        ax, ay = hx - inset, hy - inset
        cc = max(0.0, c - inset * 0.5)
        return [
            (cx - ax + cc, cy - ay, z),
            (cx + ax - cc, cy - ay, z),
            (cx + ax, cy - ay + cc, z),
            (cx + ax, cy + ay - cc, z),
            (cx + ax - cc, cy + ay, z),
            (cx - ax + cc, cy + ay, z),
            (cx - ax, cy + ay - cc, z),
            (cx - ax, cy - ay + cc, z),
        ]

    top_inset = min(chamfer_z, hx * 0.5, hy * 0.5)
    z_shoulder = max(z0, z1 - chamfer_z)

    lower = ring(0.0, z0)
    middle = ring(0.0, z_shoulder)
    upper = ring(top_inset, z1)

    verts = lower + middle + upper
    faces = []
    n = 8
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
        faces.append((n + i, n + j, 2 * n + j, 2 * n + i))
    faces.append(tuple(range(2 * n, 3 * n)))
    faces.append(tuple(reversed(range(n))))
    return verts, faces


def polygon_prism(cx, cy, z0, z1, radius, sides, top_scale=0.86):
    """Prisme régulier, légèrement conique. Volontairement peu de côtés."""
    lower, upper = [], []
    for i in range(sides):
        angle = 2 * math.pi * i / sides + math.pi / sides
        lower.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle), z0))
        upper.append((
            cx + radius * top_scale * math.cos(angle),
            cy + radius * top_scale * math.sin(angle),
            z1,
        ))

    verts = lower + upper
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((i, j, sides + j, sides + i))
    faces.append(tuple(range(sides, 2 * sides)))
    faces.append(tuple(reversed(range(sides))))
    return verts, faces


def blob(cx, cy, cz, radius, rng, squash=1.0, segments=7, rings=4, rough=0.16):
    """Masse organique bosselée : feuillage, buisson, rocher.

    Un cône empilé se reconnaît immédiatement comme un asset générique. Une
    sphère basse-résolution dont chaque sommet est déplacé au hasard se lit,
    elle, comme un volume dessiné.
    """
    verts = []
    for ring in range(1, rings):
        phi = math.pi * ring / rings
        radial = radius * math.sin(phi)
        height = cz + radius * squash * math.cos(phi)
        for seg in range(segments):
            theta = 2 * math.pi * seg / segments
            wobble = rng.uniform(1.0 - rough, 1.0 + rough)
            verts.append((
                cx + radial * wobble * math.cos(theta),
                cy + radial * wobble * math.sin(theta),
                height + radius * rough * 0.4 * rng.uniform(-1.0, 1.0),
            ))

    top = len(verts)
    verts.append((cx, cy, cz + radius * squash * rng.uniform(0.92, 1.08)))
    bottom = len(verts)
    verts.append((cx, cy, cz - radius * squash * rng.uniform(0.92, 1.08)))

    faces = []
    for ring in range(rings - 2):
        for seg in range(segments):
            nxt = (seg + 1) % segments
            faces.append((
                ring * segments + seg,
                ring * segments + nxt,
                (ring + 1) * segments + nxt,
                (ring + 1) * segments + seg,
            ))
    for seg in range(segments):
        faces.append((top, (seg + 1) % segments, seg))
    last = (rings - 2) * segments
    for seg in range(segments):
        faces.append((bottom, last + seg, last + (seg + 1) % segments))

    return verts, faces


# -- assemblage -------------------------------------------------------------


class MeshBuilder:
    """Accumule de la géométrie et une couleur par face.

    L'ombrage est **cuit dans la couleur** : orientation de la face et hauteur au
    sol. C'est le levier qui manquait — sans lui, un aplat reste un aplat quelle
    que soit la finesse du maillage, parce qu'une seule lumière directionnelle ne
    creuse ni les arêtes ni les pieds de mur. Un dessus reçoit le ciel, un
    dessous ne reçoit rien, et le bas d'un mur est occlus par le sol : peindre
    ces trois faits suffit à donner du volume.
    """

    def __init__(self, ao_height: float = 1.3, ao_strength: float = 0.30) -> None:
        self.verts: list[tuple[float, float, float]] = []
        self.faces: list[tuple[int, ...]] = []
        self.colours: list[tuple[float, float, float]] = []
        self.ao_height = ao_height
        self.ao_strength = ao_strength

    def add(self, verts, faces, colour, rng=None, face_jitter=0.0) -> None:
        offset = len(self.verts)
        self.verts.extend(verts)

        for face in faces:
            self.faces.append(tuple(index + offset for index in face))

            tone = jitter(colour, rng, face_jitter) if (rng and face_jitter > 0.0) else colour
            shade = self._shade(verts, face)
            self.colours.append(tuple(min(1.0, channel * shade) for channel in tone))

    def _shade(self, verts, face) -> float:
        a, b, c = (verts[face[0]], verts[face[1]], verts[face[2]])
        ux, uy, uz = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        vx, vy, vz = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        nz = ux * vy - uy * vx
        length = math.sqrt((uy * vz - uz * vy) ** 2 + (uz * vx - ux * vz) ** 2 + nz ** 2)
        nz = nz / length if length > 1e-9 else 0.0

        # Dessus lavé par le ciel, flanc neutre, dessous éteint.
        shade = 1.0 + 0.16 * nz if nz > 0 else 1.0 + 0.30 * nz

        if self.ao_height > 0.0:
            height = sum(verts[index][2] for index in face) / len(face)
            ratio = max(0.0, min(1.0, height / self.ao_height))
            shade *= (1.0 - self.ao_strength) + self.ao_strength * ratio

        return max(0.05, shade)

    def is_empty(self) -> bool:
        return not self.faces


def edge_frame(family: int, x: int, y: int):
    """Centre d'une arête et direction unitaire dans laquelle elle court."""
    if family == 0:
        (x0, y0), (x1, y1) = node_xy(x, y), node_xy(x, y + 1)
        return ((x0 + x1) / 2.0, (y0 + y1) / 2.0), (0.0, 1.0)

    (x0, y0), (x1, y1) = node_xy(x, y), node_xy(x + 1, y)
    return ((x0 + x1) / 2.0, (y0 + y1) / 2.0), (1.0, 0.0)


def slab(cx, cy, along, offset, z0, z1, length, thickness, chamfer=0.05, top=0.045):
    """Bloc posé sur l'axe d'un mur, décalé de `offset` le long de celui-ci."""
    ax, ay = along
    px, py = cx + ax * offset, cy + ay * offset
    sx = length if ax else thickness
    sy = length if ay else thickness
    return chamfered_prism(px, py, z0, z1, sx, sy, chamfer_xy=chamfer, chamfer_z=top)


def masonry(builder, cx, cy, along, z0, z1, length, thickness, rng,
            tones, quoin_tone, core_tone, niche_course=-1, banner_tone=None):
    """Assises de pierre irrégulières, à joints creusés.

    Trois choses font la différence avec un mur de boîtes : les blocs n'ont ni
    la même largeur ni la même hauteur d'une assise à l'autre, quelques-uns
    rentrent de un ou deux centimètres, et **chacun a sa propre teinte**. Rien
    ne dépasse jamais du nu du mur : le relief est toujours en creux, donc la
    boîte de collision d'Unity reste exacte.
    """
    course_height = (z1 - z0) / COURSES
    core_thickness = thickness - 2 * JOINT_DEPTH
    base = z0

    for course in range(COURSES):
        wobble = rng.uniform(0.88, 1.12) if course < COURSES - 1 else 1.0
        height = course_height * wobble
        if course == COURSES - 1:
            height = z1 - base
        top = base + height - JOINT_WIDTH * rng.uniform(0.8, 1.3)

        thin = course == niche_course
        builder.add(
            *slab(cx, cy, along, 0.0, base, base + height, length,
                  core_thickness * (0.45 if thin else 1.0), 0.01, 0.01),
            core_tone, rng, 0.02)

        count = rng.randint(2, 4)
        span = length / count
        cuts = [-length / 2.0]
        for index in range(1, count):
            cuts.append(-length / 2.0 + span * index + rng.uniform(-span * 0.16, span * 0.16))
        cuts.append(length / 2.0)

        for index in range(len(cuts) - 1):
            start, end = cuts[index], cuts[index + 1]
            if index > 0:
                start += JOINT_WIDTH / 2.0
            if index < len(cuts) - 2:
                end -= JOINT_WIDTH / 2.0

            is_edge_block = index in (0, len(cuts) - 2)
            if thin and not is_edge_block:
                continue
            # Une pierre manquante de temps en temps : c'est ce qui fait qu'un
            # mur a été bâti puis vécu, au lieu d'être imprimé.
            if not is_edge_block and rng.random() < 0.045:
                continue

            recess = 0.0 if rng.random() > 0.22 else rng.uniform(0.012, 0.030)
            tone = quoin_tone if is_edge_block else pick(tones, rng)
            # Le bas des murs prend l'humidité : verdi en pied, lessivé en tête.
            blend = 1.0 - (base / max(z1 - z0, 0.001))
            tone = tuple(
                channel * (1.0 - 0.13 * blend) + STONE_MOSSY[axis] * 0.13 * blend
                for axis, channel in enumerate(tone)
            )

            builder.add(
                *slab(cx, cy, along, (start + end) / 2.0, base, top - rng.uniform(0.0, 0.02),
                      end - start, thickness - 2 * recess),
                jitter(tone, rng, 0.028), rng, 0.022)

        if thin and banner_tone is not None:
            builder.add(
                *slab(cx, cy, along, 0.0, base + 0.12, top - 0.12, length / 3.0,
                      core_thickness * 0.45 + 0.035, 0.01, 0.01),
                banner_tone, rng, 0.03)
            builder.add(
                *slab(cx, cy, along, 0.0, top - 0.12, top - 0.05, length / 2.6,
                      core_thickness * 0.45 + 0.05, 0.01, 0.01),
                GOLD, rng, 0.04)

        base += height


def cap_tone(cx: float, cy: float):
    """Chaperon coloré par quadrant : quatre zones lisibles vues d'en haut."""
    key = ("n" if cy >= 0 else "s") + ("e" if cx >= 0 else "w")
    return CAP_TONES[key]


def build_wall(builder, family, x, y, perimeter, rng):
    """Un mur complet : appareil, chaperon mouluré, crénelage au pourtour."""
    (cx, cy), along = edge_frame(family, x, y)

    niche_course = 2 if (not perimeter and rng.random() < 0.17) else -1
    banner = pick(BANNER_TONES, rng)

    masonry(builder, cx, cy, along, 0.0, BODY_HEIGHT, PITCH, WALL_THICKNESS, rng,
            STONE_TONES, STONE_QUOIN, STONE_CORE, niche_course, banner)

    tone = cap_tone(cx, cy)
    moulding = WALL_THICKNESS + 2 * CAP_OVERHANG * 0.55
    overhang = WALL_THICKNESS + 2 * CAP_OVERHANG

    # Chaperon en deux tables : une doucine étroite puis la table débordante.
    # Une seule dalle lit comme une planche posée ; deux lisent comme une
    # corniche, et c'est ce qui donne l'ombre portée sur le haut du mur.
    broken = rng.random() < 0.13
    segments = ((-PITCH / 2.0, PITCH / 2.0),) if not broken else (
        (-PITCH / 2.0, -PITCH / 6.0), (PITCH / 8.0, PITCH / 2.0))

    for start, end in segments:
        centre = (start + end) / 2.0
        length = end - start
        builder.add(*slab(cx, cy, along, centre, BODY_HEIGHT, BODY_HEIGHT + CAP_HEIGHT * 0.38,
                          length, moulding, 0.04, 0.05),
                    jitter(tone, rng, 0.03, 0.10), rng, 0.025)
        builder.add(*slab(cx, cy, along, centre, BODY_HEIGHT + CAP_HEIGHT * 0.38, WALL_HEIGHT,
                          length, overhang, 0.06, 0.08),
                    jitter(tone, rng, 0.03), rng, 0.025)

    # Accessoires à hauteur de regard. Tous au-dessus de 1,40 m, la taille du
    # joueur : ils peuvent donc dépasser du nu du mur sans qu'on puisse s'y
    # cogner, et ce sont eux qui donnent quelque chose à regarder dans un
    # couloir. En dessous de cette ligne, rien ne dépasse jamais.
    if not perimeter and rng.random() < 0.34:
        offset = rng.uniform(-0.7, 0.7)
        side = rng.choice((-1.0, 1.0))
        across = (along[1], along[0])
        face = WALL_THICKNESS / 2.0
        bx = cx + along[0] * offset + across[0] * side * face
        by = cy + along[1] * offset + across[1] * side * face
        height = rng.uniform(1.85, 2.10)

        bracket = polygon_prism(bx + across[0] * side * 0.05, by + across[1] * side * 0.05,
                                height - 0.30, height, 0.055, 6, 1.35)
        builder.add(*bracket, jitter(TRUNK_TONE, rng, 0.03, 0.1), rng, 0.04)
        builder.add(*blob(bx + across[0] * side * 0.09, by + across[1] * side * 0.09,
                          height + 0.14, 0.135, rng, squash=1.5, rough=0.22),
                    jitter(GOLD, rng, 0.04, 0.35), rng, 0.05)
        TORCHES.append((bx + across[0] * side * 1.4, by + across[1] * side * 1.4))

    if not perimeter and rng.random() < 0.30:
        # Chaînage de bois : une ligne horizontale franche et une matière
        # différente, à 2,25 m, donc hors d'atteinte.
        builder.add(*slab(cx, cy, along, 0.0, 2.18, 2.36, PITCH, WALL_THICKNESS + 0.045, 0.02, 0.02),
                    jitter(TRUNK_TONE, rng, 0.03), rng, 0.035)

    if perimeter:
        count = 4
        step = PITCH / count
        for index in range(count):
            if rng.random() < 0.12:
                continue
            offset = -PITCH / 2.0 + step * (index + 0.5)
            height = MERLON_HEIGHT * rng.uniform(0.82, 1.12)
            builder.add(
                *slab(cx, cy, along, offset, WALL_HEIGHT, WALL_HEIGHT + height,
                      MERLON_WIDTH * rng.uniform(0.9, 1.1), WALL_THICKNESS, 0.04, 0.05),
                jitter(pick(STONE_TONES, rng), rng, 0.04), rng, 0.03)

    return (cx, cy), along


def build_tree(builder, ox, oy, rng, scale=1.0):
    """Arbre à houppier en masses, et non en cônes empilés."""
    trunk_height = rng.uniform(2.6, 4.6) * scale
    radius = rng.uniform(0.20, 0.32) * scale
    builder.add(*polygon_prism(ox, oy, -0.1, trunk_height, radius * 1.5, 6, 0.62),
                jitter(TRUNK_TONE, rng, 0.03), rng, 0.03)

    crown = rng.uniform(1.5, 2.4) * scale
    for index in range(rng.randint(3, 5)):
        angle = rng.uniform(0, 2 * math.pi)
        spread = crown * rng.uniform(0.0, 0.55)
        builder.add(
            *blob(ox + spread * math.cos(angle), oy + spread * math.sin(angle),
                  trunk_height + crown * rng.uniform(0.25, 0.85),
                  crown * rng.uniform(0.55, 0.85), rng, squash=rng.uniform(0.75, 1.0)),
            jitter(pick(LEAF_TONES, rng), rng, 0.035), rng, 0.05)


def build_scene(grid: Grid, payload: dict, seed: int):
    """Monte toute la map dans Blender. Un objet par groupe attendu par Unity."""
    import bpy

    rng = random.Random(seed ^ 0x5EED)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0

    def surface(name: str, roughness: float, specular: float = 0.15):
        """Matériau piloté par la couleur de sommet.

        Un seul matériau porte des centaines de teintes : c'est ce qui permet la
        variation sans multiplier les sous-maillages, donc sans multiplier les
        appels de rendu côté moteur.
        """
        material = bpy.data.materials.new(f"MAT_{name}")
        material.use_nodes = True
        tree = material.node_tree
        bsdf = tree.nodes["Principled BSDF"]
        bsdf.inputs["Roughness"].default_value = roughness
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = specular

        attribute = tree.nodes.new("ShaderNodeVertexColor")
        attribute.layer_name = "Col"
        attribute.location = (-320, 240)
        tree.links.new(attribute.outputs["Color"], bsdf.inputs["Base Color"])
        return material

    materials = {
        "stone": surface("stone", 0.78, 0.10),
        "foliage": surface("foliage", 0.82, 0.06),
        "ground": surface("ground", 0.88, 0.05),
        "trim": surface("trim", 0.55, 0.32),
    }

    def commit(name: str, builder: MeshBuilder, surface_name: str, location=(0.0, 0.0, 0.0)):
        if builder.is_empty():
            return None

        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(builder.verts, [], builder.faces)
        mesh.validate()
        mesh.materials.append(materials[surface_name])

        layer = mesh.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="CORNER")
        for polygon, colour in zip(mesh.polygons, builder.colours):
            polygon.use_smooth = False
            for loop in polygon.loop_indices:
                layer.data[loop].color = (colour[0], colour[1], colour[2], 1.0)
        mesh.update()

        obj = bpy.data.objects.new(name, mesh)
        obj.location = location
        scene.collection.objects.link(obj)
        return obj

    # -- murs statiques : un seul maillage fusionné, comme l'exige Unity ------
    TORCHES.clear()
    walls = MeshBuilder()
    wall_tops: list[tuple[float, float, tuple[float, float]]] = []
    for family in (0, 1):
        limits = (WIDTH + 1, HEIGHT) if family == 0 else (WIDTH, HEIGHT + 1)
        for x in range(limits[0]):
            for y in range(limits[1]):
                if grid.state(family, x, y) != STATIC:
                    continue
                perimeter = grid.is_perimeter(family, x, y)
                wall_rng = random.Random((seed, family, x, y).__hash__() & 0xFFFFFFFF)
                centre, along = build_wall(walls, family, x, y, perimeter, wall_rng)
                if not perimeter:
                    wall_tops.append((centre[0], centre[1], along))
    commit("Murs_Statiques", walls, "stone")

    # -- pivots : un objet par pivot, origine sur son nœud -------------------
    for index, pivot in enumerate(payload["pivots"]):
        nx, ny = pivot["node"]
        ox, oy = node_xy(nx, ny)
        pivot_rng = random.Random(seed * 31 + index)
        builder = MeshBuilder()

        builder.add(*polygon_prism(0.0, 0.0, 0.0, 0.46, PIVOT_TOTEM_RADIUS * 1.5, 8, 0.90),
                    jitter(PIVOT_TOTEM_TONE, pivot_rng, 0.03, -0.15), pivot_rng, 0.03)
        builder.add(*polygon_prism(0.0, 0.0, 0.46, PIVOT_TOTEM_HEIGHT - 0.55, PIVOT_TOTEM_RADIUS, 8, 0.92),
                    jitter(PIVOT_TOTEM_TONE, pivot_rng, 0.03), pivot_rng, 0.04)
        builder.add(*polygon_prism(0.0, 0.0, PIVOT_TOTEM_HEIGHT - 0.55, PIVOT_TOTEM_HEIGHT - 0.18,
                                   PIVOT_TOTEM_RADIUS * 1.55, 8, 0.98),
                    jitter(GOLD, pivot_rng, 0.03), pivot_rng, 0.04)
        builder.add(*blob(0.0, 0.0, PIVOT_TOTEM_HEIGHT + 0.05, 0.30, pivot_rng, squash=1.25),
                    jitter(GOLD, pivot_rng, 0.04, 0.12), pivot_rng, 0.05)

        for arm in pivot["arms"]:
            dx, dy = DIRECTIONS[arm]
            mid_x, mid_y = dx * PITCH / 2.0, dy * PITCH / 2.0
            along = (1.0, 0.0) if dx else (0.0, 1.0)

            masonry(builder, mid_x, mid_y, along, 0.0, BODY_HEIGHT, PITCH, WALL_THICKNESS,
                    pivot_rng, PIVOT_STONE, jitter(PIVOT_STONE[1], pivot_rng, 0.02, -0.2),
                    STONE_CORE)
            builder.add(*slab(mid_x, mid_y, along, 0.0, BODY_HEIGHT,
                              BODY_HEIGHT + CAP_HEIGHT * 0.38, PITCH,
                              WALL_THICKNESS + CAP_OVERHANG, 0.04, 0.05),
                        jitter(GOLD, pivot_rng, 0.03, -0.25), pivot_rng, 0.03)
            builder.add(*slab(mid_x, mid_y, along, 0.0, BODY_HEIGHT + CAP_HEIGHT * 0.38,
                              WALL_HEIGHT, PITCH, WALL_THICKNESS + 2 * CAP_OVERHANG, 0.06, 0.08),
                        jitter(PIVOT_STONE[2], pivot_rng, 0.03, 0.10), pivot_rng, 0.03)

        commit(f"Pivot_{nx:02d}_{ny:02d}_{pivot['shape']}", builder, "stone",
               location=(ox, oy, 0.0))

    # -- sol du labyrinthe : dalles à joints creusés -------------------------
    # Le dessus des dalles est strictement plan à z = 0 ; seuls les joints sont
    # en contrebas de 3 cm. Le joueur marche donc toujours sur le même plan.
    floor = MeshBuilder(ao_height=0.0)
    inset = 0.09
    for cx in range(WIDTH):
        for cy in range(HEIGHT):
            cell_rng = random.Random(seed * 17 + cx * 97 + cy)
            x0, y0 = node_xy(cx, cy)
            x1, y1 = node_xy(cx + 1, cy + 1)
            floor.add(
                [(x0, y0, -0.03), (x1, y0, -0.03), (x1, y1, -0.03), (x0, y1, -0.03)],
                [(0, 1, 2, 3)], jitter(STONE_CORE, cell_rng, 0.03, 0.6))

            grassy = cell_rng.random() < 0.17
            tone = pick(GRASS_TONES if grassy else PAVING_TONES, cell_rng)
            floor.add(
                [(x0 + inset, y0 + inset, 0.0), (x1 - inset, y0 + inset, 0.0),
                 (x1 - inset, y1 - inset, 0.0), (x0 + inset, y1 - inset, 0.0)],
                [(0, 1, 2, 3)], jitter(tone, cell_rng, 0.04))
    commit("Sol_Dalles", floor, "ground")

    # -- plateau extérieur ---------------------------------------------------
    field = MeshBuilder(ao_height=0.0)
    span = 120.0
    field.add(
        [(-span, -span, -0.02), (span, -span, -0.02), (span, span, -0.02), (-span, span, -0.02)],
        [(0, 1, 2, 3)], FIELD_TONE)
    commit("Sol_Sable", field, "ground")

    # -- repères d'entrée et de trésor ---------------------------------------
    markers = MeshBuilder()
    for cx in ENTRANCE_CELLS:
        gate_rng = random.Random(seed * 7 + cx)
        x0, _ = node_xy(cx, 0)
        x1, _ = node_xy(cx + 1, 0)
        _, y0 = node_xy(cx, 0)

        for post_x in (x0, x1):
            markers.add(*polygon_prism(post_x, y0, 0.0, WALL_HEIGHT + 1.15, 0.19, 6, 0.80),
                        jitter(TRUNK_TONE, gate_rng, 0.03, 0.15), gate_rng, 0.04)
            markers.add(*polygon_prism(post_x, y0, WALL_HEIGHT + 1.15, WALL_HEIGHT + 1.45,
                                       0.32, 6, 0.35),
                        jitter(GOLD, gate_rng, 0.03), gate_rng, 0.04)

        markers.add(*chamfered_prism((x0 + x1) / 2.0, y0, WALL_HEIGHT + 0.40,
                                     WALL_HEIGHT + 1.02, PITCH, WALL_THICKNESS + 0.24,
                                     chamfer_xy=0.08, chamfer_z=0.10),
                    jitter(TRUNK_TONE, gate_rng, 0.03, 0.25), gate_rng, 0.03)
        banner = pick(BANNER_TONES, gate_rng)
        markers.add(*chamfered_prism((x0 + x1) / 2.0, y0, WALL_HEIGHT - 0.75,
                                     WALL_HEIGHT + 0.40, PITCH * 0.44, 0.06,
                                     chamfer_xy=0.03, chamfer_z=0.03),
                    jitter(banner, gate_rng, 0.04), gate_rng, 0.04)

    treasure_rng = random.Random(seed * 13)
    tx0, ty0 = node_xy(TREASURE_CELL[0], TREASURE_CELL[1])
    tx1, ty1 = node_xy(TREASURE_CELL[0] + 1, TREASURE_CELL[1] + 1)
    tcx, tcy = (tx0 + tx1) / 2.0, (ty0 + ty1) / 2.0
    markers.add(*chamfered_prism(tcx, tcy, 0.0, 0.14, 2.10, 2.10, 0.14, 0.05),
                jitter(pick(PAVING_TONES, treasure_rng), treasure_rng, 0.03), treasure_rng, 0.03)
    markers.add(*chamfered_prism(tcx, tcy, 0.14, 0.26, 1.55, 1.55, 0.12, 0.05),
                jitter(GOLD, treasure_rng, 0.03, -0.2), treasure_rng, 0.03)
    markers.add(*polygon_prism(tcx, tcy, 0.26, 2.55, 0.18, 6, 0.68),
                jitter(TRUNK_TONE, treasure_rng, 0.03, 0.2), treasure_rng, 0.04)
    markers.add(*blob(tcx, tcy, 2.95, 0.46, treasure_rng, squash=1.2),
                jitter(GOLD, treasure_rng, 0.04, 0.15), treasure_rng, 0.06)
    commit("Reperes_Gameplay", markers, "trim")

    # -- végétation : jamais dans un couloir ---------------------------------
    # Le lierre est plaqué au nu du mur ; touffes et couronnes restent au-dessus
    # de 3 m. Rien ne descend dans un passage, rien ne peut donc tromper.
    plants = MeshBuilder(ao_height=0.0)
    for cx, cy, along in wall_tops:
        plant_rng = random.Random(int((cx * 131.0 + cy * 977.0) * 100) ^ seed)
        across = (along[1], along[0])
        top = WALL_HEIGHT - 0.05

        if plant_rng.random() < 0.38:
            for _ in range(plant_rng.randint(2, 4)):
                offset = plant_rng.uniform(-1.15, 1.15)
                size = plant_rng.uniform(0.16, 0.30)
                plants.add(
                    *blob(cx + along[0] * offset + across[0] * plant_rng.uniform(-0.07, 0.07),
                          cy + along[1] * offset + across[1] * plant_rng.uniform(-0.07, 0.07),
                          top + size * 0.7, size, plant_rng, squash=0.85),
                    jitter(pick(LEAF_TONES, plant_rng), plant_rng, 0.04), plant_rng, 0.05)

        if plant_rng.random() < 0.34:
            # Lierre en cascade de petites masses, pas en bandes plates : une
            # bande verte collée au mur se lit comme une rayure peinte, jamais
            # comme une plante. Chaque touffe est aplatie contre le nu du mur,
            # donc rien ne déborde dans le couloir.
            side = plant_rng.choice((-1.0, 1.0))
            face = WALL_THICKNESS / 2.0
            start = plant_rng.uniform(-1.05, 1.05)
            drop = plant_rng.uniform(0.7, 1.9)
            count = plant_rng.randint(3, 6)

            for step in range(count):
                size = plant_rng.uniform(0.14, 0.26) * (1.0 - 0.45 * step / count)
                offset = start + plant_rng.uniform(-0.22, 0.22)
                height = top - drop * step / count
                verts, faces = blob(0.0, 0.0, 0.0, size, plant_rng, squash=0.9, rough=0.26)
                flat_x = 0.30 if across[0] else 1.0
                flat_y = 0.30 if across[1] else 1.0
                placed = [
                    (cx + along[0] * offset + across[0] * side * face + vx * flat_x,
                     cy + along[1] * offset + across[1] * side * face + vy * flat_y,
                     height + vz)
                    for vx, vy, vz in verts
                ]
                plants.add(placed, faces,
                           jitter(pick(LEAF_TONES, plant_rng), plant_rng, 0.04),
                           plant_rng, 0.05)
    commit("Vegetation", plants, "foliage")

    # -- décor lointain : les repères qui manquaient -------------------------
    far = MeshBuilder()
    half = WIDTH / 2.0 * PITCH
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            tower_rng = random.Random(int(seed + sx * 3 + sy * 11))
            ox, oy = sx * (half + 8.0), sy * (half + 8.0)
            far.add(*polygon_prism(ox, oy, 0.0, 1.3, TOWER_RADIUS * 1.28, 8, 0.94),
                    jitter(STONE_QUOIN, tower_rng, 0.03, -0.1), tower_rng, 0.04)
            for level in range(5):
                z0 = 1.3 + level * (TOWER_HEIGHT - 3.0) / 5.0
                z1 = z0 + (TOWER_HEIGHT - 3.0) / 5.0 - 0.06
                far.add(*polygon_prism(ox, oy, z0, z1, TOWER_RADIUS * (1.0 - level * 0.02), 8, 0.97),
                        jitter(pick(STONE_TONES, tower_rng), tower_rng, 0.04), tower_rng, 0.05)
            far.add(*polygon_prism(ox, oy, TOWER_HEIGHT - 1.7, TOWER_HEIGHT - 1.0,
                                   TOWER_RADIUS * 1.38, 8, 0.99),
                    jitter(STONE_QUOIN, tower_rng, 0.03), tower_rng, 0.04)
            for index in range(8):
                angle = 2 * math.pi * index / 8 + math.pi / 8
                far.add(*chamfered_prism(ox + TOWER_RADIUS * 1.18 * math.cos(angle),
                                         oy + TOWER_RADIUS * 1.18 * math.sin(angle),
                                         TOWER_HEIGHT - 1.0, TOWER_HEIGHT - 0.35, 0.5, 0.5,
                                         0.05, 0.06),
                        jitter(pick(STONE_TONES, tower_rng), tower_rng, 0.04), tower_rng, 0.04)
            far.add(*polygon_prism(ox, oy, TOWER_HEIGHT - 0.35, TOWER_HEIGHT + 2.8,
                                   TOWER_RADIUS * 0.98, 8, 0.04),
                    jitter(TOWER_ROOF, tower_rng, 0.04), tower_rng, 0.05)

    for index in range(150):
        far_rng = random.Random(seed * 101 + index)
        angle = far_rng.uniform(0, 2 * math.pi)
        radius = far_rng.uniform(half + 5.5, 110.0)
        ox, oy = radius * math.cos(angle), radius * math.sin(angle)
        roll = far_rng.random()
        if roll < 0.18:
            size = far_rng.uniform(0.7, 2.4)
            far.add(*blob(ox, oy, size * 0.35, size, far_rng, squash=0.62, rough=0.30),
                    jitter(pick(ROCK_TONES, far_rng), far_rng, 0.04), far_rng, 0.05)
        elif roll < 0.30:
            for _ in range(far_rng.randint(2, 3)):
                size = far_rng.uniform(0.5, 0.9)
                far.add(*blob(ox + far_rng.uniform(-0.8, 0.8), oy + far_rng.uniform(-0.8, 0.8),
                              size * 0.8, size, far_rng, squash=0.8),
                        jitter(pick(LEAF_TONES, far_rng), far_rng, 0.04), far_rng, 0.05)
        else:
            build_tree(far, ox, oy, far_rng, scale=far_rng.uniform(0.85, 1.5))

    commit("Decor_Lointain", far, "foliage")

    # -- ciel et soleil ------------------------------------------------------
    world = bpy.data.worlds.new("Ciel")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.26, 0.48, 0.84, 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.55
    scene.world = world

    sun_data = bpy.data.lights.new("Soleil", type="SUN")
    sun_data.energy = 3.1
    sun_data.angle = math.radians(3.0)
    sun_data.color = (1.0, 0.93, 0.79)
    sun = bpy.data.objects.new("Soleil", sun_data)
    sun.rotation_euler = (math.radians(46.0), 0.0, math.radians(38.0))
    scene.collection.objects.link(sun)

    # Appoint froid côté ombre : sans lui, un couloir orienté au nord devient un
    # aplat gris et tout le travail de teinte des pierres disparaît.
    fill_data = bpy.data.lights.new("Appoint", type="SUN")
    fill_data.energy = 0.32
    fill_data.angle = math.radians(45.0)
    fill_data.color = (0.62, 0.74, 1.0)
    fill = bpy.data.objects.new("Appoint", fill_data)
    fill.rotation_euler = (math.radians(58.0), 0.0, math.radians(215.0))
    scene.collection.objects.link(fill)

    return scene


# ==========================================================================
# 3. Rendus de contrôle et export
# ==========================================================================


def render_previews(directory: Path, grid: Grid) -> list[Path]:
    """Trois vues : l'ensemble, un couloir à hauteur d'yeux, un pivot."""
    import bpy
    from mathutils import Vector

    directory.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene

    # Le nom du moteur temps réel a changé plusieurs fois entre les versions de
    # Blender : on prend le premier disponible au lieu d'en coder un en dur.
    available = scene.render.bl_rna.properties["engine"].enum_items.keys()
    for candidate in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        if candidate in available:
            scene.render.engine = candidate
            break

    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"

    camera_data = bpy.data.cameras.new("Camera")
    camera = bpy.data.objects.new("Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    def aim(position, target, lens):
        camera.location = position
        camera_data.lens = lens
        direction = Vector(target) - Vector(position)
        camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    entrance_x, entrance_y = node_xy(ENTRANCE_CELLS[1] + 0.5, 0.5)

    shots = [
        ("apercu-aerien.png", (0.0, -52.0, 46.0), (0.0, 2.0, 0.0), 38.0),
        # Hauteur d'yeux du joueur, reculée d'une cellule pour montrer l'arche
        # d'entrée en même temps que le couloir.
        ("apercu-entree.png", (entrance_x, entrance_y - 6.0, 1.05), (entrance_x, entrance_y + 14.0, 2.0), 24.0),
    ]

    if TORCHES:
        tx, ty = TORCHES[len(TORCHES) // 2]
        shots.append(("apercu-couloir.png", (tx, ty - 2.4, 1.05), (tx, ty + 3.0, 1.9), 26.0))

    pivots = [obj for obj in scene.objects if obj.name.startswith("Pivot_")]
    if pivots:
        pivot = min(pivots, key=lambda o: o.location.length)
        px, py = pivot.location.x, pivot.location.y
        shots.append(
            ("apercu-pivot.png", (px - 7.5, py - 9.0, 4.2), (px, py, 1.4), 30.0)
        )

    written = []
    for name, position, target, lens in shots:
        aim(position, target, lens)
        scene.render.filepath = str(directory / name)
        bpy.ops.render.render(write_still=True)
        written.append(directory / name)

    return written


def export_fbx(path: Path) -> None:
    """Export dans la convention Unity, transformations cuites dans le maillage.

    `bake_space_transform` est ce qui fait arriver les nœuds à l'identité côté
    Unity au lieu de porter la conversion d'axes de Blender. L'ancien export ne
    le faisait pas : chaque nœud arrivait à -90° en x et à l'échelle 100, ce qui
    a fini par coucher les pivots au démarrage.
    """
    import bpy

    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.fbx(
        filepath=str(path),
        use_selection=False,
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_NONE",
        global_scale=1.0,
        bake_space_transform=True,
        object_types={"MESH"},
        use_mesh_modifiers=True,
        mesh_smooth_type="FACE",
        use_tspace=False,
        add_leaf_bones=False,
        bake_anim=False,
        axis_forward="-Z",
        axis_up="Y",
        path_mode="COPY",
        embed_textures=False,
    )


def scene_statistics() -> dict:
    import bpy

    triangles = 0
    objects = {}
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        count = sum(len(polygon.vertices) - 2 for polygon in obj.data.polygons)
        triangles += count
        objects[obj.name] = count

    return {
        "triangles": triangles,
        "objects": objects,
        "materials": len(bpy.data.materials),
    }


# ==========================================================================


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260805)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-fbx", type=Path)
    parser.add_argument("--out-blend", type=Path)
    parser.add_argument("--render-dir", type=Path)
    parser.add_argument("--topology-only", action="store_true")
    args = parser.parse_args(argv)

    grid, payload = build_topology(args.seed)

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    report = {
        "seed": args.seed,
        "json": str(args.out_json),
        "movable_walls": payload["stats"]["movable_walls"],
        "arm_edges": payload["stats"]["arm_edges"],
        "pivots": payload["stats"]["pivot_count"],
        "shapes": payload["stats"]["shapes"],
        "cells_reachable": payload["stats"]["cells_reachable"],
        "treasure_distance": payload["stats"]["treasure_distance"],
    }

    if not args.topology_only:
        build_scene(grid, payload, args.seed)
        report["scene"] = scene_statistics()

        if args.render_dir:
            report["renders"] = [str(p) for p in render_previews(args.render_dir, grid)]
        if args.out_fbx:
            export_fbx(args.out_fbx)
            report["fbx"] = str(args.out_fbx)
            report["fbx_bytes"] = args.out_fbx.stat().st_size
        if args.out_blend:
            import bpy

            args.out_blend.parent.mkdir(parents=True, exist_ok=True)
            bpy.ops.wm.save_as_mainfile(filepath=str(args.out_blend))
            report["blend"] = str(args.out_blend)

    print("[MAZE-CARTOON] " + json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    raise SystemExit(main(argv))
