"""Construit le personnage "Golem de grès" depuis le turnaround 360°.

Référence : définir GOLEM_REFERENCE si l’image externe est disponible.
Unités     : 1 BU = 1 m. Hauteur totale 1.00 m, semelles à z = 0 (contact sol réel).

Exécution (Blender 5.1, via MCP ou console) :

    blender --background --factory-startup --python workflows/scripts/build_golem_de_gres.py

Méthode : blockout clay facetté (icosphère -> profil de révolution mesuré sur la
référence -> bruit basse fréquence -> Decimate DISSOLVE -> flat shading), puis
gravures booléennes projetées par raycast sur la surface finale, donc à profondeur
constante quelle que soit la courbure.

Le script est idempotent : il supprime sa propre production avant de reconstruire.
Il ne touche à aucun objet non préfixé, sauf le Cube de la scène de démarrage.
"""

import json
import math
import os
from pathlib import Path

import bpy
import bmesh
from mathutils import Matrix, Vector
from mathutils import noise as mnoise

# --------------------------------------------------------------------------- #
# Contrat d'identité — valeurs mesurées sur le turnaround
# --------------------------------------------------------------------------- #

PREFIX = "K3_GOLEMGRES_"
COLLECTION_NAME = PREFIX + "ASSET"
ROOT = Path(__file__).resolve().parents[2]
REFERENCE = os.environ.get("GOLEM_REFERENCE", "external:golem-de-gres-turnaround.png")

HEIGHT = 1.00

# Toutes les formes viennent du calque produit par
# workflows/tools/trace_golem_reference.py : aucune silhouette n'est saisie à la
# main ici. Relancer le calque si la planche de référence change.
TRACE = str(ROOT / "projects" / "golem-de-gres" / "golem-trace.json")

# 16 côtés plutôt que 22 : la référence montre de grandes facettes lisibles, pas
# une surface lisse. Le bruit et le dissolve finissent de casser la régularité.
BODY_SEGMENTS = 20

# Fermeture du dessous : le calque s'arrête là où le ventre disparaît derrière les
# jambes. On referme sous cette dernière tranche, hors silhouette.
BODY_CLOSE_DROP = 0.0

# Yeux : le calque donne rayon, écart et hauteur. Ce sont de vrais trous percés
# dans la pierre, pas des billes posées — la référence montre des cavités noires.
EYE_BORE_DEPTH = 2.1        # en rayons d'œil
EYE_SEGMENTS = 14

# Bras : la ligne moyenne et la section sont reconstruites depuis le calque. Au-
# dessus de arm_start le bras se confond avec le corps de face, on y remonte par
# le contour extérieur mesuré, en soustrayant la demi-section.
ARM_SHOULDER_T = 0.735      # au-dessus, le bras est entièrement noyé dans le corps
ARM_SEGMENTS = 14
THUMB_T = 0.88
THUMB_HALF = Vector((0.036, 0.046, 0.072))

# Jambes : hauteur non mesurable de face (le ventre les couvre) ; on les enfonce
# assez pour qu'elles se soudent au corps.
LEG_Z_TOP = 0.155

# Nombre de plans de taille par pièce : c'est lui qui fixe la lisibilité des
# facettes. La planche montre une quarantaine de pans sur le corps.
BODY_FACETS = 44
ARM_FACETS = 26
LEG_FACETS = 16
THUMB_FACETS = 10

FACET_ANGLE_DEG = 11.0
BEVEL_WIDTH = 0.005
# Les traits d'une même rune se croisent : chaque intersection laisse une arête à
# plus de deux faces. C'est cumulatif et sans conséquence sur le solveur ; seul le
# bord ouvert est bloquant. Le seuil ne sert qu'à détecter une vraie dérive.
MAX_NONMANIFOLD_EDGES = 64
# Quelques bordures residuelles ne bloquent pas le solveur ; c'est le maillage
# largement ouvert (des dizaines de bords) qui provoquait le calcul sans fin.
MAX_BORDER_EDGES = 8

GROOVE_WIDTH = 0.016
GROOVE_DEPTH = 0.010

# Runes angulaires, en unités locales [-0.5, 0.5], polylignes 2D (u, v).
RUNE_A = [
    [(-0.40, 0.34), (0.40, 0.34)],
    [(-0.24, 0.34), (-0.24, -0.18), (0.06, -0.36)],
    [(0.20, 0.34), (0.20, -0.10)],
    [(0.02, -0.10), (0.40, -0.10)],
]
RUNE_B = [
    [(-0.36, 0.36), (0.36, 0.36)],
    [(0.00, 0.36), (0.00, -0.14)],
    [(-0.30, -0.14), (0.30, -0.14), (0.30, -0.40)],
    [(-0.30, 0.06), (-0.04, 0.06)],
]
RUNE_C = [
    [(-0.30, -0.34), (0.00, 0.30), (0.30, -0.34), (-0.30, -0.34)],
    [(0.00, 0.30), (0.00, 0.46)],
]


# --------------------------------------------------------------------------- #
# Utilitaires
# --------------------------------------------------------------------------- #

def srgb(r, g, b):
    """Couleur sRGB lisible -> linéaire, comme attendu par les sockets Blender."""

    def to_linear(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return (to_linear(r), to_linear(g), to_linear(b), 1.0)


def lerp_table(x, table, smooth=True):
    """Interpolation sur une table (clé, valeur) triée, bornée aux extrémités."""
    if x <= table[0][0]:
        return table[0][1]
    if x >= table[-1][0]:
        return table[-1][1]
    for i in range(len(table) - 1):
        x0, v0 = table[i]
        x1, v1 = table[i + 1]
        if x0 <= x <= x1:
            t = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
            if smooth:
                t = t * t * (3.0 - 2.0 * t)
            return v0 + (v1 - v0) * t
    return table[-1][1]


def superellipsoid(direction, exponent):
    """Direction unitaire -> point sur une superellipsoïde unité (boîte arrondie)."""
    ax, ay, az = abs(direction.x), abs(direction.y), abs(direction.z)
    s = (ax ** exponent + ay ** exponent + az ** exponent) ** (1.0 / exponent)
    return direction / s if s > 1e-9 else direction.copy()


def new_ico_bmesh(subdivisions):
    bm = bmesh.new()
    try:
        bmesh.ops.create_icosphere(bm, subdivisions=subdivisions, radius=1.0)
    except TypeError:  # API antérieure à 3.0
        bmesh.ops.create_icosphere(bm, subdivisions=subdivisions, diameter=1.0)
    return bm


def displace_noise(bm, amplitude, frequency, offset, fade_fn=None):
    """Déplace le long des normales avec un bruit lisse : irrégularité sans casser
    la planéité locale, sinon le Decimate DISSOLVE ne fusionne plus rien."""
    bm.normal_update()
    off = Vector(offset)
    for v in bm.verts:
        n = mnoise.noise(v.co * frequency + off)
        amp = amplitude
        if fade_fn is not None:
            amp *= fade_fn(v.co)
        v.co += v.normal * (n * amp)


def ensure_outward(bm):
    """Oriente la coque vers l'extérieur en s'appuyant sur le volume signé.

    recalc_face_normals seul ne suffit pas sur un tube courbe : son heuristique
    peut retenir l'orientation inverse, et un outil booléen retourné transforme
    une différence en intersection — le corps disparaît au profit de la gravure.
    """
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    volume = sum(f.calc_area() * f.normal.dot(f.calc_center_median()) for f in bm.faces)
    if volume < 0.0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    return volume / 3.0


def bmesh_to_object(bm, name, collection):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def activate(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply_modifier(obj, modifier):
    activate(obj)
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def facet(obj, angle_deg=FACET_ANGLE_DEG):
    """Decimate planaire appliqué + flat shading : grandes facettes de pierre."""
    mod = obj.modifiers.new(name="Facet", type="DECIMATE")
    mod.decimate_type = "DISSOLVE"
    mod.angle_limit = math.radians(angle_deg)
    apply_modifier(obj, mod)
    heal(obj)
    activate(obj)
    bpy.ops.object.shade_flat()


def add_bevel(obj, width=BEVEL_WIDTH):
    """Arêtes usées, gardé vivant (non destructif)."""
    mod = obj.modifiers.new(name="WornEdges", type="BEVEL")
    mod.width = width
    mod.segments = 1
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(35.0)
    mod.harden_normals = False
    return mod


def set_origin(obj, world_point):
    """Origine = pivot utile pour le rig, sans passer par parent_set/ops de scale."""
    delta = Vector(world_point)
    obj.data.transform(Matrix.Translation(-delta))
    obj.location = delta


def bounds(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(depsgraph)
    pts = [ev.matrix_world @ Vector(c) for c in ev.bound_box]
    return (
        Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
        Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))),
    )


# --------------------------------------------------------------------------- #
# Pièces
# --------------------------------------------------------------------------- #

def sphere_dirs(count, seed):
    """Directions réparties en spirale de Fibonacci, brouillées de façon
    déterministe : sans ce brouillage les facettes s'alignent en bandes
    régulières et la pierre a l'air tournée au tour, pas taillée."""
    golden = math.pi * (3.0 - math.sqrt(5.0))
    out = []
    for i in range(count):
        z = 1.0 - 2.0 * (i + 0.5) / count
        r = math.sqrt(max(0.0, 1.0 - z * z))
        a = golden * i
        d = Vector((math.cos(a) * r, math.sin(a) * r, z))
        jitter = Vector((
            mnoise.noise(d * 2.4 + Vector((seed, 0.0, 0.0))),
            mnoise.noise(d * 2.4 + Vector((0.0, seed, 0.0))),
            mnoise.noise(d * 2.4 + Vector((0.0, 0.0, seed))),
        ))
        out.append((d + jitter * 0.20).normalized())
    return out


def faceted_solid(points, count, seed, margin=1.0):
    """Enveloppe convexe d'un échantillon épars du nuage calqué.

    Deux façons d'obtenir des pans plats, et une seule est fidèle :
      - couper un bloc par des plans tangents **circonscrit** la forme, les
        facettes bombent entre les points de contact (mesuré : +12 à +18 % de
        largeur, +93 % au sommet du crâne) ;
      - l'enveloppe convexe d'un échantillon **passe par les points**, donc elle
        est inscrite ; l'erreur est celle de la corde, bien plus faible, et se
        rattrape par `margin`.

    Le nombre de points retenus fixe la taille des facettes : peu de points, de
    grands pans, comme un caillou dégrossi au ciseau.
    """
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    centre = (lo + hi) * 0.5

    step = max(1, len(points) // max(count, 8))
    sample = [points[i] for i in range(0, len(points), step)]

    bm = bmesh.new()
    for p in sample:
        jitter = Vector((
            mnoise.noise(p * 6.0 + Vector((seed, 0.0, 0.0))),
            mnoise.noise(p * 6.0 + Vector((0.0, seed, 0.0))),
            mnoise.noise(p * 6.0 + Vector((0.0, 0.0, seed))),
        ))
        bm.verts.new(centre + (p - centre) * margin + jitter * 0.006)

    # Extrêmes non brouillés : ils fixent l'encombrement exact de la pièce.
    for axis in range(3):
        for pick in (min, max):
            bm.verts.new(pick(points, key=lambda p: p[axis]))

    res = bmesh.ops.convex_hull(bm, input=bm.verts, use_existing_faces=False)
    # convex_hull renvoie les mêmes éléments dans plusieurs listes ; bmesh.delete
    # refuse un doublon, d'où la déduplication par identité.
    junk = list({id(g): g for g in
                 res.get("geom_interior", []) + res.get("geom_unused", [])}.values())
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    ensure_outward(bm)
    return bm


def lathe_points(rings_spec, segments):
    """Nuage de points sur la surface calquée, sans construire de faces."""
    pts = []
    for z, half, front, back in rings_spec:
        if half < 1e-5:
            pts.append(Vector((0.0, 0.0, z)))
            continue
        for i in range(segments):
            a = 2.0 * math.pi * i / segments
            s = math.sin(a)
            depth = front if s > 0.0 else back
            pts.append(Vector((half * math.cos(a), -depth * s, z)))
    return pts


def load_trace():
    with open(TRACE) as fh:
        return json.load(fh)


def bridge_rings(bm, rings, segments):
    """Relie les anneaux et FERME les extrémités qui ne sont pas des pôles.

    Une extrémité laissée ouverte rend le maillage non-manifold, et le solveur
    booléen EXACT part alors dans des temps de calcul inexploitables — c'est ce
    qui a bloqué Blender pendant 17 minutes avant cette correction."""
    for lo, hi in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            if len(lo) == 1:
                bm.faces.new((lo[0], hi[i], hi[j]))
            elif len(hi) == 1:
                bm.faces.new((lo[i], lo[j], hi[0]))
            else:
                bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    if len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if len(rings[-1]) > 1:
        bm.faces.new(list(rings[-1]))


def lathe(bm, rings_spec, segments):
    """rings_spec : liste de (z, demi_largeur, avant, arriere). Section elliptique
    dissymétrique : la tête avance plus qu'elle ne recule."""
    rings = []
    for z, half, front, back in rings_spec:
        if half < 1e-5:
            rings.append([bm.verts.new((0.0, 0.0, z))])
            continue
        ring = []
        for i in range(segments):
            a = 2.0 * math.pi * i / segments
            s = math.sin(a)
            depth = front if s > 0.0 else back
            ring.append(bm.verts.new((half * math.cos(a), -depth * s, z)))
        rings.append(ring)
    bridge_rings(bm, rings, segments)
    return rings


def build_body(collection, spec):
    """Tour sur le calque : la silhouette de face et les profondeurs de profil sont
    posées telles quelles, sans réinterprétation."""
    slices = [(b["t"] * HEIGHT, b["half"] * HEIGHT,
               b["front"] * HEIGHT, b["back"] * HEIGHT) for b in spec["body"]]
    slices.sort(key=lambda s: s[0])

    # Fermeture du dessous, sous la dernière tranche mesurée : le calque s'arrête
    # là où les jambes prennent le relais dans la vue de face.
    # Pas de pointe sous le ventre : l'enveloppe convexe la ferait bomber jusqu'au
    # sol et avalerait les jambes. On laisse le dessous plat, caché entre elles.
    if BODY_CLOSE_DROP > 0.0:
        z0, half0, front0, back0 = slices[0]
        drop = BODY_CLOSE_DROP
        slices = [
            (z0 - drop, 0.0, 0.0, 0.0),
            (z0 - drop * 0.72, half0 * 0.55, front0 * 0.55, back0 * 0.55),
            (z0 - drop * 0.34, half0 * 0.87, front0 * 0.87, back0 * 0.87),
        ] + slices

    points = lathe_points(slices, BODY_SEGMENTS)
    bm = faceted_solid(points, BODY_FACETS, seed=3.7, margin=1.012)
    obj = bmesh_to_object(bm, PREFIX + "BODY", collection)
    # Le facettage est différé : les runes et les orbites se percent sur le tour
    # propre, en quads réguliers. Graver après le dissolve revenait à faire opérer
    # le booléen sur des n-gons non plans, ce qui déchirait le maillage.
    return obj


def arm_slices(spec):
    """Empilement de sections du bras, reconstruit depuis le calque.

    Sous arm_start le bras est séparé du corps : centre et demi-largeur sont
    mesurés directement. Au-dessus il se confond avec le corps ; seul le contour
    extérieur reste mesuré, on en déduit le centre en retranchant la demi-section.
    """
    measured = sorted(spec["arm"], key=lambda a: a["t"])
    outline = sorted(spec["outline"], key=lambda o: o["t"])
    top_measured = measured[-1]
    ratio = spec["arm_depth_ratio"]

    # Épaisseur au-dessus de la zone mesurée : constante puis rentrée à l'épaule,
    # où le bras se fond dans la masse.
    thickness = [
        (top_measured["t"], top_measured["half"]),
        (0.60, top_measured["half"]),
        (ARM_SHOULDER_T, top_measured["half"] * 0.82),
    ]

    out = []
    for a in measured:
        out.append((a["t"], a["centre"], a["half"]))
    for o in outline:
        if not (top_measured["t"] < o["t"] <= ARM_SHOULDER_T):
            continue
        half = lerp_table(o["t"], thickness)
        out.append((o["t"], o["half"] - half, half))
    out.sort()

    slices = []
    for t, centre, half in out:
        slices.append((t * HEIGHT, centre * HEIGHT, half * HEIGHT, half * ratio * HEIGHT))
    # Pointe de la main sous la dernière mesure, et fermeture à l'épaule.
    t0, c0, h0, d0 = slices[0]
    slices.insert(0, (t0 - 0.022, c0, 0.0, 0.0))
    tn, cn, hn, dn = slices[-1]
    slices.append((tn + 0.016, cn, hn * 0.45, dn * 0.45))
    return slices


def build_arm(collection, side, spec):
    """Bras construit à x positif d'après le calque, puis mis en miroir."""
    slices = arm_slices(spec)
    points = []
    for z, centre, half, depth in slices:
        if half < 1e-5:
            points.append(Vector((centre, 0.0, z)))
            continue
        for i in range(ARM_SEGMENTS):
            a = 2.0 * math.pi * i / ARM_SEGMENTS
            points.append(Vector((centre + half * math.cos(a), -depth * math.sin(a), z)))
    bm = faceted_solid(points, ARM_FACETS, seed=8.1 if side > 0 else 15.4, margin=1.015)

    # Pouce : coin bas avant-interne de la main.
    hand_z, hand_c, hand_h, _ = slices[2]
    tilt = Matrix.Rotation(math.radians(18.0), 3, "X")
    origin = Vector((hand_c - hand_h * 0.55, -0.062, hand_z + 0.030))
    thumb_pts = []
    probe = new_ico_bmesh(2)
    for v in probe.verts:
        d = superellipsoid(v.co.normalized(), 3.0)
        local = Vector((d.x * THUMB_HALF.x, d.y * THUMB_HALF.y, d.z * THUMB_HALF.z))
        thumb_pts.append(origin + tilt @ local)
    probe.free()
    thumb = faceted_solid(thumb_pts, THUMB_FACETS, seed=21.3, margin=1.02)

    if side < 0:
        for shell in (bm, thumb):
            bmesh.ops.transform(shell, matrix=Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0)),
                                verts=shell.verts)
            bmesh.ops.reverse_faces(shell, faces=shell.faces)

    # Bruit décorrélé entre les deux bras : deux blocs taillés à la main ne sont
    # jamais des miroirs exacts, et cette dissymétrie fait beaucoup du caractère.
    displace_noise(bm, amplitude=0.010, frequency=3.6,
                   offset=(3.1, 8.4, 1.7) if side > 0 else (17.9, 2.3, 12.6))

    name = PREFIX + ("ARM_R" if side > 0 else "ARM_L")
    obj = bmesh_to_object(bm, name, collection)
    # Pouce fusionné par booléen plutôt que simplement juxtaposé : deux coques qui
    # s'interpénètrent dans un même maillage relancent le problème d'auto-intersection
    # au moment de graver les runes.
    boolean(obj, thumb, name + "_THUMB", operation="UNION", use_self=False)
    shoulder = Vector((slices[-1][1] * side, 0.0, slices[-1][0]))
    return obj, shoulder


def build_leg(collection, side, spec):
    legs = sorted(spec["legs"], key=lambda l: l["t"])
    centre = sum(l["centre"] for l in legs) / len(legs) * HEIGHT
    half = max(l["half"] for l in legs) * HEIGHT
    depth_series = sorted(spec["depth"], key=lambda d: d["t"])
    near = min(depth_series, key=lambda d: abs(d["t"] - legs[-1]["t"]))
    half_depth = (near["front"] + near["back"]) * 0.5 * HEIGHT

    probe = new_ico_bmesh(3)
    pts = []
    for v in probe.verts:
        # Exposant élevé sur Z : semelle et hanche franches, flancs arrondis.
        p = superellipsoid(v.co.normalized(), 4.5)
        flare = 1.0 + 0.10 * max(0.0, -p.z)
        pts.append(Vector((p.x * half * flare, p.y * half_depth * flare,
                           p.z * LEG_Z_TOP * 0.5)))
    probe.free()
    bm = faceted_solid(pts, LEG_FACETS, seed=5.5 * side + 30.0, margin=1.01)

    min_z = min(v.co.z for v in bm.verts)
    bmesh.ops.transform(
        bm,
        matrix=Matrix.Translation(Vector((centre * side, -0.012, -min_z))),
        verts=bm.verts,
    )

    name = PREFIX + ("LEG_R" if side > 0 else "LEG_L")
    obj = bmesh_to_object(bm, name, collection)
    facet(obj, angle_deg=12.0)
    return obj, Vector((centre * side, -0.012, LEG_Z_TOP))


def seat_on_ground(obj):
    """Le DISSOLVE peut supprimer le sommet le plus bas et le Bevel rogne la semelle :
    on rassoit sur les bounds évalués, sinon le contact sol est faux."""
    bpy.context.view_layer.update()
    lo, _ = bounds(obj)
    obj.location.z -= lo.z


# --------------------------------------------------------------------------- #
# Gravures et yeux : projection par raycast sur la surface définitive
# --------------------------------------------------------------------------- #

def surface_hit(target, origin, direction, distance=1.5):
    ok, location, normal, _ = target.ray_cast(origin, direction.normalized(), distance=distance)
    return (location, normal) if ok else (None, None)


def stroke_prism(samples, width, depth, standout=0.02):
    """Prisme fermé suivant un trait posé sur la surface.

    Une gravure était auparavant approchée par un chapelet de cubes qui se
    recouvraient : le solveur booléen devait alors résoudre des centaines
    d'auto-intersections et rendait un maillage déchiré (307 bords ouverts
    mesurés). Un seul tube fermé par trait supprime le problème à la source.
    """
    if len(samples) < 2:
        return None
    bm = bmesh.new()
    rings = []
    for i, (p, n) in enumerate(samples):
        nxt = samples[min(i + 1, len(samples) - 1)][0]
        prv = samples[max(i - 1, 0)][0]
        tangent = (nxt - prv)
        if tangent.length < 1e-9:
            continue
        side = tangent.normalized().cross(n).normalized() * (width * 0.5)
        out = n * standout
        deep = n * (-depth)
        rings.append([
            bm.verts.new(p + side + out),
            bm.verts.new(p + side + deep),
            bm.verts.new(p - side + deep),
            bm.verts.new(p - side + out),
        ])
    if len(rings) < 2:
        bm.free()
        return None

    for lo, hi in zip(rings, rings[1:]):
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(list(rings[-1]))
    ensure_outward(bm)
    return bm


def project_stroke(target, plane_center, u_axis, v_axis, ray_dir, line,
                   size_u, size_v, step=0.006):
    """Projette une polyligne 2D sur la surface réelle, par raycast."""
    u_axis = Vector(u_axis).normalized()
    v_axis = Vector(v_axis).normalized()
    ray_dir = Vector(ray_dir).normalized()

    out = []
    for i in range(len(line) - 1):
        a, b = Vector(line[i]), Vector(line[i + 1])
        real = math.hypot((b.x - a.x) * size_u, (b.y - a.y) * size_v)
        steps = max(2, int(math.ceil(real / step)))
        for k in range(steps + (1 if i == len(line) - 2 else 0)):
            p = a.lerp(b, k / steps)
            origin = plane_center + u_axis * (p.x * size_u) + v_axis * (p.y * size_v)
            location, normal = surface_hit(target, origin, ray_dir, distance=2.0)
            if location is not None:
                out.append((location, normal.normalized()))
    return out


def carve_glyph(target, name, plane_center, u_axis, v_axis, ray_dir, polylines,
                size_u, size_v):
    """Un booléen par trait : chaque outil est un solide fermé et isolé."""
    for idx, line in enumerate(polylines):
        samples = project_stroke(target, plane_center, u_axis, v_axis, ray_dir,
                                 line, size_u, size_v)
        prism = stroke_prism(samples, GROOVE_WIDTH, GROOVE_DEPTH)
        if prism is None:
            continue
        boolean(target, prism, "%s_%d" % (name, idx),
                operation="DIFFERENCE", use_self=True)


def assign_material(obj, mat):
    """Le Boolean laisse un slot vide en index 0 : on repart d'un slot unique,
    sinon les faces pointent sur None et rendent en blanc par défaut."""
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.material_index = 0


def heal(obj):
    """Recoud le maillage : doublons, faces dégénérées, trous résiduels.

    Un booléen EXACT laisse régulièrement une arête isolée sur une intersection
    rasante. Une seule suffit à rendre le booléen suivant inexploitable, donc on
    répare systématiquement au lieu d'attendre le blocage."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    # Plusieurs passes : boucher un trou peut en révéler un autre en dessous.
    for _ in range(3):
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges)
        # Arêtes filaires : holes_fill ne les traite pas, il faut les supprimer.
        wire = [e for e in bm.edges if not e.link_faces]
        if wire:
            bmesh.ops.delete(bm, geom=wire, context="EDGES")
        holes = [e for e in bm.edges if len(e.link_faces) == 1]
        if not holes:
            break
        bmesh.ops.holes_fill(bm, edges=holes, sides=0)
        still = [e for e in bm.edges if len(e.link_faces) == 1]
        if still:
            bmesh.ops.triangle_fill(bm, use_beauty=True, edges=still)
    loose = [v for v in bm.verts if not v.link_edges]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")

    ensure_outward(bm)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def assert_closed(obj, label):
    """Refuse d'entrer dans un booléen avec un maillage ouvert : EXACT n'échoue
    pas dessus, il part en calcul quasi infini, ce qui est bien pire à diagnostiquer."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    wire = sum(1 for e in bm.edges if not e.link_faces)
    border = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    excess = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    bm.free()
    # Seuls les bords ouverts déclenchent le calcul sans fin observé. Quelques
    # arêtes à plus de deux faces, résidus normaux d'un dissolve planaire, passent
    # sans dommage — on les signale sans bloquer.
    if wire or border > MAX_BORDER_EDGES:
        raise RuntimeError("%s : %d filaires, %d bordures — booleen refuse"
                           % (label, wire, border))
    if border:
        print("  note: %s garde %d bordure(s) apres reparation" % (label, border))
    if excess > MAX_NONMANIFOLD_EDGES:
        raise RuntimeError("%s : %d aretes a >2 faces, au-dela du tolere"
                           % (label, excess))
    if excess:
        print("  note: %s porte %d arete(s) a >2 faces" % (label, excess))


def boolean(target, cutter_bm, name, operation="DIFFERENCE", use_self=True):
    if cutter_bm is None:
        return
    cutter = bmesh_to_object(cutter_bm, name, bpy.context.scene.collection)
    assert_closed(target, "cible " + target.name)
    assert_closed(cutter, "outil " + name)
    mod = target.modifiers.new(name=name, type="BOOLEAN")
    mod.object = cutter
    mod.operation = operation
    mod.solver = "EXACT"
    mod.use_self = use_self
    apply_modifier(target, mod)
    bpy.data.objects.remove(cutter, do_unlink=True)
    heal(target)


def carve(target, cutter_bm, name):
    boolean(target, cutter_bm, name, operation="DIFFERENCE", use_self=True)


def carve_glyphs(body, arm_r, arm_l):
    # Poitrine : grappe de deux runes, côté gauche du personnage (x positif).
    carve_glyph(body, PREFIX + "CUT_CHEST_A",
                plane_center=Vector((0.115, -0.75, 0.640)),
                u_axis=(1, 0, 0), v_axis=(0, 0, 1), ray_dir=(0, 1, 0),
                polylines=RUNE_A, size_u=0.170, size_v=0.160)

    carve_glyph(body, PREFIX + "CUT_CHEST_B",
                plane_center=Vector((0.095, -0.75, 0.455)),
                u_axis=(1, 0, 0), v_axis=(0, 0, 1), ray_dir=(0, 1, 0),
                polylines=RUNE_B, size_u=0.145, size_v=0.135)

    # Bras : colonne de runes sur la face externe.
    for arm, side, runes in ((arm_r, 1, (RUNE_C, RUNE_A)), (arm_l, -1, (RUNE_B, RUNE_C))):
        for idx, rune in enumerate(runes):
            z = 0.560 - idx * 0.155
            carve_glyph(arm, "%sCUT_ARM_%s_%d" % (PREFIX, "R" if side > 0 else "L", idx),
                        plane_center=Vector((0.95 * side, -0.015, z)),
                        u_axis=(0, 1, 0), v_axis=(0, 0, 1), ray_dir=(-side, 0, 0),
                        polylines=rune, size_u=0.115, size_v=0.135)


def bore_eyes(body, spec):
    """Perce deux vrais trous dans la pierre. La référence montre des cavités
    noires, pas des billes posées : une bille prend la lumière et fait un œil
    brillant, un trou reste sombre sous tous les angles."""
    radius = spec["eyes"]["r"] * HEIGHT
    depth = radius * EYE_BORE_DEPTH
    bores = []

    for side in (1, -1):
        # Un outil par orbite : deux coques dans un même maillage se font piéger
        # par l'orientation au volume signé, qui raisonne sur leur somme et peut
        # en laisser une retournée.
        cutter = bmesh.new()
        origin = Vector((spec["eyes"]["x"] * HEIGHT * side, -0.90, spec["eyes"]["z"] * HEIGHT))
        location, normal = surface_hit(body, origin, Vector((0, 1, 0)), distance=2.0)
        if location is None:
            cutter.free()
            continue
        # Axe droit vers l'arrière plutôt que la normale de facette : une normale
        # de facette donne une coupe rasante que le solveur EXACT résout mal, et
        # le trou ressort alors ouvert.
        axis = Vector((0.0, 1.0, 0.0))
        standoff = 0.055
        mouth = location - axis * standoff   # démarre franchement devant la surface
        # La profondeur utile se compte depuis la pierre, pas depuis la bouche de
        # l'outil, sinon le fût s'arrête avant d'avoir mordu.
        total = standoff + depth
        # On mémorise le point de surface, pas la bouche de l'outil : le noircissage
        # doit se limiter au fût réellement creusé dans la pierre.
        bores.append((location.copy(), axis.copy(), radius, depth))

        rot = axis.to_track_quat("Z", "Y").to_matrix().to_4x4()
        # Fût cylindrique terminé par une calotte : le fond du trou n'est pas un
        # disque plat, il reste lisible comme une cavité.
        rings = []
        profile = [(0.0, radius), (total * 0.86, radius),
                   (total * 0.95, radius * 0.72), (total, 0.0)]
        for d, r in profile:
            if r < 1e-5:
                rings.append([cutter.verts.new((mouth + axis * d))])
                continue
            ring = []
            for i in range(EYE_SEGMENTS):
                a = 2.0 * math.pi * i / EYE_SEGMENTS
                local = Vector((r * math.cos(a), r * math.sin(a), 0.0))
                ring.append(cutter.verts.new(mouth + axis * d + (rot.to_3x3() @ local)))
            rings.append(ring)
        cap = []
        for i in range(EYE_SEGMENTS):
            a = 2.0 * math.pi * i / EYE_SEGMENTS
            local = Vector((radius * math.cos(a), radius * math.sin(a), 0.0))
            cap.append(cutter.verts.new(mouth - axis * 0.03 + (rot.to_3x3() @ local)))
        rings.insert(0, cap)
        for lo, hi in zip(rings, rings[1:]):
            for i in range(EYE_SEGMENTS):
                j = (i + 1) % EYE_SEGMENTS
                if len(hi) == 1:
                    cutter.faces.new((lo[i], lo[j], hi[0]))
                else:
                    cutter.faces.new((lo[i], lo[j], hi[j], hi[i]))
        cutter.faces.new(list(reversed(rings[0])))
        ensure_outward(cutter)
        carve(body, cutter, "%sCUT_EYE_%s" % (PREFIX, "R" if side > 0 else "L"))

    return bores


def shade_bores(body, bores, dark_index):
    """Assigne la matière sombre aux seules faces qui tapissent les trous.

    Le test porte sur TOUS les sommets d'une face, pas sur son centre : les
    facettes du crâne font une dizaine de centimètres, et un test au centre
    barbouillait de noir des pans entiers voisins de l'orbite.
    """
    if not bores:
        return 0
    verts = body.data.vertices
    count = 0
    for poly in body.data.polygons:
        for surface, axis, radius, depth in bores:
            inside = True
            for vi in poly.vertices:
                rel = verts[vi].co - surface
                along = rel.dot(axis)
                if not (-0.006 <= along <= depth + 0.004):
                    inside = False
                    break
                if (rel - axis * along).length > radius * 1.08:
                    inside = False
                    break
            if inside:
                poly.material_index = dark_index
                count += 1
                break
    return count


# --------------------------------------------------------------------------- #
# Matières
# --------------------------------------------------------------------------- #

def sandstone_material():
    name = PREFIX + "MAT_SANDSTONE"
    mat = bpy.data.materials.get(name)
    if mat:
        bpy.data.materials.remove(mat)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (900, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (620, 0)

    # Dégradé vertical : sommet clair chauffé par le ciel, base plus ocre.
    tex_coord = nt.nodes.new("ShaderNodeTexCoord")
    tex_coord.location = (-900, 0)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-720, -60)
    nt.links.new(tex_coord.outputs["Object"], sep.inputs["Vector"])

    grad_map = nt.nodes.new("ShaderNodeMapRange")
    grad_map.location = (-560, -60)
    grad_map.inputs["From Min"].default_value = 0.0
    grad_map.inputs["From Max"].default_value = 1.0
    nt.links.new(sep.outputs["Z"], grad_map.inputs["Value"])

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-380, -60)
    ramp.color_ramp.elements[0].position = 0.05
    ramp.color_ramp.elements[0].color = srgb(0.58, 0.44, 0.31)
    ramp.color_ramp.elements[1].position = 0.95
    ramp.color_ramp.elements[1].color = srgb(0.85, 0.72, 0.55)
    mid = ramp.color_ramp.elements.new(0.5)
    mid.color = srgb(0.76, 0.62, 0.45)
    nt.links.new(grad_map.outputs["Result"], ramp.inputs["Fac"])

    # Marbrure du grès.
    mottle = nt.nodes.new("ShaderNodeTexNoise")
    mottle.location = (-560, 240)
    mottle.inputs["Scale"].default_value = 5.5
    mottle.inputs["Detail"].default_value = 6.0
    mottle.inputs["Roughness"].default_value = 0.55

    mix_mottle = nt.nodes.new("ShaderNodeMix")
    mix_mottle.location = (-180, 60)
    mix_mottle.data_type = "RGBA"
    mix_mottle.blend_type = "MULTIPLY"
    mix_mottle.inputs["Factor"].default_value = 0.22
    nt.links.new(ramp.outputs["Color"], mix_mottle.inputs["A"])
    nt.links.new(mottle.outputs["Fac"], mix_mottle.inputs["B"])

    # Occlusion locale : creux assombris -> les gravures se lisent sans texture
    # peinte. Pointiness serait plus net mais n'existe que sous Cycles ; le nœud AO
    # fonctionne aussi en EEVEE, donc le gate viewport dit la vérité.
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.location = (-900, 460)
    ao.samples = 8
    ao.only_local = True
    ao.inputs["Distance"].default_value = 0.028
    point_ramp = nt.nodes.new("ShaderNodeValToRGB")
    point_ramp.location = (-700, 460)
    point_ramp.color_ramp.elements[0].position = 0.25
    point_ramp.color_ramp.elements[0].color = (0.14, 0.10, 0.07, 1.0)
    point_ramp.color_ramp.elements[1].position = 0.85
    point_ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    nt.links.new(ao.outputs["AO"], point_ramp.inputs["Fac"])

    mix_cavity = nt.nodes.new("ShaderNodeMix")
    mix_cavity.location = (180, 60)
    mix_cavity.data_type = "RGBA"
    mix_cavity.blend_type = "MULTIPLY"
    mix_cavity.inputs["Factor"].default_value = 1.0
    nt.links.new(mix_mottle.outputs["Result"], mix_cavity.inputs["A"])
    nt.links.new(point_ramp.outputs["Color"], mix_cavity.inputs["B"])
    nt.links.new(mix_cavity.outputs["Result"], bsdf.inputs["Base Color"])

    # Grain fin en bump.
    grain = nt.nodes.new("ShaderNodeTexNoise")
    grain.location = (180, -420)
    grain.inputs["Scale"].default_value = 42.0
    grain.inputs["Detail"].default_value = 8.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.location = (400, -420)
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.004
    nt.links.new(grain.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    rough = nt.nodes.new("ShaderNodeMapRange")
    rough.location = (400, -220)
    rough.inputs["To Min"].default_value = 0.62
    rough.inputs["To Max"].default_value = 0.86
    nt.links.new(mottle.outputs["Fac"], rough.inputs["Value"])
    nt.links.new(rough.outputs["Result"], bsdf.inputs["Roughness"])

    bsdf.inputs["Metallic"].default_value = 0.0
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def eye_material():
    name = PREFIX + "MAT_EYE"
    mat = bpy.data.materials.get(name)
    if mat:
        bpy.data.materials.remove(mat)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = srgb(0.06, 0.05, 0.05)
    bsdf.inputs["Roughness"].default_value = 0.32
    bsdf.inputs["Metallic"].default_value = 0.0
    return mat


# --------------------------------------------------------------------------- #
# Scène de contrôle
# --------------------------------------------------------------------------- #

def build_check_rig(collection):
    ground_mesh = bpy.data.meshes.new(PREFIX + "GROUND")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=6.0)
    bm.to_mesh(ground_mesh)
    bm.free()
    ground = bpy.data.objects.new(PREFIX + "GROUND", ground_mesh)
    collection.objects.link(ground)

    ground_mat = bpy.data.materials.get(PREFIX + "MAT_GROUND")
    if ground_mat:
        bpy.data.materials.remove(ground_mat)
    ground_mat = bpy.data.materials.new(PREFIX + "MAT_GROUND")
    ground_mat.use_nodes = True
    gb = ground_mat.node_tree.nodes["Principled BSDF"]
    gb.inputs["Base Color"].default_value = srgb(0.30, 0.28, 0.26)
    gb.inputs["Roughness"].default_value = 0.95
    ground.data.materials.append(ground_mat)

    key = bpy.data.lights.new(PREFIX + "KEY", type="AREA")
    key.energy = 220.0
    key.size = 2.0
    key_obj = bpy.data.objects.new(PREFIX + "KEY", key)
    key_obj.location = (1.7, -2.0, 2.4)
    key_obj.rotation_euler = (math.radians(52), 0, math.radians(40))
    collection.objects.link(key_obj)

    rim = bpy.data.lights.new(PREFIX + "RIM", type="AREA")
    rim.energy = 160.0
    rim.size = 1.4
    rim_obj = bpy.data.objects.new(PREFIX + "RIM", rim)
    rim_obj.location = (-1.6, 1.9, 1.8)
    rim_obj.rotation_euler = (math.radians(64), 0, math.radians(-140))
    collection.objects.link(rim_obj)

    cam_data = bpy.data.cameras.new(PREFIX + "CAM")
    cam_data.lens = 85.0
    cam_obj = bpy.data.objects.new(PREFIX + "CAM", cam_data)
    cam_obj.location = (0.0, -4.2, 0.55)
    cam_obj.rotation_euler = (math.radians(90), 0, 0)
    collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = srgb(0.42, 0.45, 0.50)
        bg.inputs["Strength"].default_value = 0.65

    return ground, cam_obj


# --------------------------------------------------------------------------- #
# Assemblage
# --------------------------------------------------------------------------- #

def purge_previous():
    for obj in list(bpy.data.objects):
        if obj.name.startswith(PREFIX) or obj.name == "Cube":
            bpy.data.objects.remove(obj, do_unlink=True)
    coll = bpy.data.collections.get(COLLECTION_NAME)
    if coll:
        bpy.data.collections.remove(coll)
    for block in list(bpy.data.meshes):
        if block.users == 0:
            bpy.data.meshes.remove(block)


def build():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    purge_previous()

    collection = bpy.data.collections.new(COLLECTION_NAME)
    bpy.context.scene.collection.children.link(collection)

    spec = load_trace()
    body = build_body(collection, spec)
    arm_r, shoulder_r = build_arm(collection, 1, spec)
    arm_l, shoulder_l = build_arm(collection, -1, spec)
    leg_r, hip_r = build_leg(collection, 1, spec)
    leg_l, hip_l = build_leg(collection, -1, spec)

    bpy.context.view_layer.update()
    carve_glyphs(body, arm_r, arm_l)
    bores = bore_eyes(body, spec)

    # Facettage après les booléens : les parois de gravure et d'orbite sont à ~90°
    # de la surface, très au-delà de la limite du dissolve, donc elles survivent.
    facet(body, angle_deg=8.5)
    facet(arm_r)
    facet(arm_l)

    stone = sandstone_material()
    dark = eye_material()
    for obj in (body, arm_r, arm_l, leg_r, leg_l):
        assign_material(obj, stone)
        add_bevel(obj)
    # Le corps porte deux matières : la pierre, et le noir qui tapisse les orbites.
    body.data.materials.append(dark)
    bored = shade_bores(body, bores, len(body.data.materials) - 1)

    # Pivots utiles au rig.
    set_origin(body, Vector((0.0, 0.0, spec["body"][0]["t"] * HEIGHT)))
    set_origin(arm_r, shoulder_r)
    set_origin(arm_l, shoulder_l)
    set_origin(leg_r, hip_r)
    set_origin(leg_l, hip_l)

    root = bpy.data.objects.new(PREFIX + "ROOT", None)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.25
    collection.objects.link(root)
    root["reference_image"] = REFERENCE
    root["trace_spec"] = TRACE
    root["unit_scale"] = "1 BU = 1 m"
    root["target_height_m"] = HEIGHT

    parts = [body, arm_r, arm_l, leg_r, leg_l]
    for obj in parts:
        # Affectation directe : parent_set réinitialise l'échelle (cf. leçons rig mecha).
        obj.parent = root
        obj.matrix_parent_inverse = root.matrix_world.inverted()

    for leg in (leg_r, leg_l):
        seat_on_ground(leg)

    ground, cam = build_check_rig(collection)
    bpy.context.view_layer.update()

    lo_all = Vector((1e9, 1e9, 1e9))
    hi_all = Vector((-1e9, -1e9, -1e9))
    report = {"parts": {}}
    for obj in parts:
        lo, hi = bounds(obj)
        for i in range(3):
            lo_all[i] = min(lo_all[i], lo[i])
            hi_all[i] = max(hi_all[i], hi[i])
        report["parts"][obj.name] = {
            "polygons": len(obj.data.polygons),
            "min": [round(v, 4) for v in lo],
            "max": [round(v, 4) for v in hi],
        }

    report["overall"] = {
        "height_m": round(hi_all.z - lo_all.z, 4),
        "width_m": round(hi_all.x - lo_all.x, 4),
        "depth_m": round(hi_all.y - lo_all.y, 4),
        "ground_gap_m": round(lo_all.z, 5),
    }
    report["collection"] = COLLECTION_NAME
    report["total_polygons"] = sum(p["polygons"] for p in report["parts"].values())
    report["eye_bores"] = len(bores)
    report["eye_faces_darkened"] = bored
    print("GOLEM_REPORT " + json.dumps(report))
    return report


REPORT = build()
