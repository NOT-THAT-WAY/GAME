# Passe de direction artistique "écho de l'arène" sur la composition validée.
#
# Intention observable, en une phrase :
#   « La mascotte se tient dans son terrain de jeu : un sol d'arène chaud éclairé
#     par-dessus, un fond froid qui recule, et l'orange de la zone de dépôt qui
#     revient en accent au dos du personnage. »
#
# Toute la palette est DÉRIVÉE du jeu, pas inventée. Sources exactes :
#   zone de dépôt (1.00, 0.28, 0.04)  Assets/_Project/Editor/M1PlaytestBuild.cs:1102
#   key light     (1.00, 0.92, 0.82)  M1PlaytestBuild.cs:838
#   fill light    (0.62, 0.72, 0.95)  M1PlaytestBuild.cs:849
#   horizon       (0.16, 0.19, 0.26)  M1PlaytestBuild.cs:91
#   sol décor     (0.10, 0.11, 0.14)  M1PlaytestBuild.cs:1144
#   pilier chaud  (0.24, 0.21, 0.20)  M1PlaytestBuild.cs:1147
#   caillou       (0.34, 0.31, 0.29)  M1PlaytestBuild.cs:110
#
# Verrous respectés : le personnage, son rig, ses Actions et ses matériaux ne
# sont jamais touchés. Budgets déclarés respectés : 1 seul mesh de présentation
# (celui qui existe est MODIFIÉ, aucun n'est ajouté) et 3 lumières (retunées,
# aucune ajoutée). Contrat de cadrage inchangé : compo centrée, DOF interdit.
#
# Une catégorie à la fois via --upto : 1 = décor/palette, 2 = + éclairage,
# 3 = + caméra hero.
#
# Usage :
#   blender -b <base.blend> --python art_direction_claude.py -- <upto> <out.blend>

import bpy, sys, math, json
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
UPTO = int(argv[0])
OUT = argv[1]

PREFIX = "BAS_SANDBOX_CHARACTER_COMPOSITION_V001_"
STAGE = PREFIX + "STAGE_CYCLORAMA"
KEY = PREFIX + "LIGHT_KEY"
FILL = PREFIX + "LIGHT_FILL"
RIM = PREFIX + "LIGHT_RIM"
HERO = PREFIX + "CAM_HERO_3Q"
TARGET = PREFIX + "TARGET_CHARACTER"

# ---- palette du jeu (linéaire) ----
GAME_DEPOSIT = (1.00, 0.28, 0.04)
GAME_KEY = (1.00, 0.92, 0.82)
GAME_FILL = (0.62, 0.72, 0.95)
GAME_HORIZON = (0.16, 0.19, 0.26)
GAME_GROUND = (0.10, 0.11, 0.14)
GAME_WARM = (0.24, 0.21, 0.20)

scene = bpy.context.scene
log = {"upto": UPTO, "categories": []}


def look_at(obj, target: Vector):
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def mix_node(nt):
    """Mix RGB robuste : ShaderNodeMixRGB (legacy) sinon ShaderNodeMix RGBA."""
    try:
        n = nt.nodes.new("ShaderNodeMixRGB")
        return n, n.inputs["Fac"], n.inputs["Color1"], n.inputs["Color2"], n.outputs["Color"]
    except RuntimeError:
        pass
    n = nt.nodes.new("ShaderNodeMix")
    n.data_type = "RGBA"
    fac = next(s for s in n.inputs if s.name == "Factor" and s.type == "VALUE")
    a = next(s for s in n.inputs if s.name == "A" and s.type == "RGBA")
    b = next(s for s in n.inputs if s.name == "B" and s.type == "RGBA")
    out = next(s for s in n.outputs if s.type == "RGBA")
    return n, fac, a, b, out


# =====================================================================
# CATÉGORIE 1 — décor et palette
# =====================================================================
def category_stage():
    stage = bpy.data.objects[STAGE]
    assert stage["support_plane_z"] == 0.0, "le plan de support doit rester à Z=0"

    mat = stage.data.materials[0]
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (900, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (620, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    # Coordonnées objet du décor : le personnage est à l'origine.
    tex = nt.nodes.new("ShaderNodeTexCoord"); tex.location = (-1000, 0)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); sep.location = (-820, 0)
    nt.links.new(tex.outputs["Object"], sep.inputs["Vector"])

    # -- facteur de hauteur : 0 sur le sol, 1 sur le fond --
    h = nt.nodes.new("ShaderNodeMapRange"); h.location = (-640, 180)
    h.inputs["From Min"].default_value = 0.02
    h.inputs["From Max"].default_value = 1.30
    h.clamp = True
    nt.links.new(sep.outputs["Z"], h.inputs["Value"])

    # -- distance radiale au personnage, dans le plan du sol --
    dot = nt.nodes.new("ShaderNodeVectorMath"); dot.location = (-820, -260)
    dot.operation = "MULTIPLY"
    nt.links.new(tex.outputs["Object"], dot.inputs[0])
    dot.inputs[1].default_value = (1.0, 1.0, 0.0)     # on annule Z
    length = nt.nodes.new("ShaderNodeVectorMath"); length.location = (-640, -260)
    length.operation = "LENGTH"
    nt.links.new(dot.outputs["Vector"], length.inputs[0])

    # pool chaud autour des pieds : 1 au centre, 0 au-delà de ~2.6 m
    pool = nt.nodes.new("ShaderNodeMapRange"); pool.location = (-460, -260)
    pool.inputs["From Min"].default_value = 0.55
    pool.inputs["From Max"].default_value = 2.60
    pool.inputs["To Min"].default_value = 1.0
    pool.inputs["To Max"].default_value = 0.0
    pool.clamp = True
    nt.links.new(length.outputs["Value"], pool.inputs["Value"])

    # adoucissement du pool
    smooth = nt.nodes.new("ShaderNodeMath"); smooth.location = (-280, -260)
    smooth.operation = "POWER"
    smooth.inputs[1].default_value = 1.7
    nt.links.new(pool.outputs["Result"], smooth.inputs[0])

    # -- sol : gris froid du décor -> argile chaude sous le personnage --
    # Essai 2 : pool resserré (0.5 -> 2.2 m) et exposant plus dur, pour que la
    # chaleur reste sous le personnage au lieu d'envahir tout le sol.
    pool.inputs["From Min"].default_value = 0.50
    pool.inputs["From Max"].default_value = 2.20
    smooth.inputs[1].default_value = 2.0

    floor_mix, f_fac, f_a, f_b, f_out = mix_node(nt)
    floor_mix.location = (-80, -200)
    f_a.default_value = (0.085, 0.092, 0.115, 1.0)   # sol froid, loin
    f_b.default_value = (0.150, 0.120, 0.100, 1.0)   # argile d'arène, sous les pieds
    nt.links.new(smooth.outputs["Value"], f_fac)

    # -- fond : il doit RECULER. Essai 1 l'avait éclairci (HorizonColor brut),
    # le personnage s'y noyait. On garde la teinte horizon mais on descend la
    # valeur bien sous celle du personnage.
    back_mix, b_fac, b_a, b_b, b_out = mix_node(nt)
    back_mix.location = (-80, 200)
    b_a.default_value = (0.070, 0.082, 0.115, 1.0)
    b_b.default_value = (0.026, 0.032, 0.052, 1.0)
    back_h = nt.nodes.new("ShaderNodeMapRange"); back_h.location = (-280, 200)
    back_h.inputs["From Min"].default_value = 0.10
    back_h.inputs["From Max"].default_value = 2.60
    back_h.clamp = True
    nt.links.new(sep.outputs["Z"], back_h.inputs["Value"])
    nt.links.new(back_h.outputs["Result"], b_fac)

    # -- sol/fond --
    ground_mix, g_fac, g_a, g_b, g_out = mix_node(nt)
    ground_mix.location = (140, 0)
    nt.links.new(h.outputs["Result"], g_fac)
    nt.links.new(f_out, g_a)
    nt.links.new(b_out, g_b)

    # Pas d'orange PEINT sur le décor. L'essai 1 en mettait un anneau, mais la
    # rampe ne redescendait jamais à zéro au-delà de 2.30 m : tout le sol et le
    # fond viraient rose et la séparation devenait pire que la baseline.
    # L'accent de la zone de dépôt est porté par la lumière rim (catégorie 2),
    # ce qui est de toute façon la bonne façon de poser un accent.
    nt.links.new(g_out, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.78
    bsdf.inputs["Metallic"].default_value = 0.0

    # -- World : ambiance froide profonde, l'arène est une salle, pas un vide --
    world = scene.world
    wnt = world.node_tree
    bg = wnt.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.016, 0.022, 0.038, 1.0)
    bg.inputs["Strength"].default_value = 0.26

    log["categories"].append({
        "category": "stage_and_palette",
        "attempt": 2,
        "attempt_1_rejected": ("anneau orange peint : la rampe restait à 0.135 au-delà de 2.30 m, "
                               "donc le sol ET le fond viraient rose et le personnage se noyait"),
        "changed": [STAGE + " (matériau procédural, mesh conservé)", "World"],
        "meshes_added": 0,
        "palette_sources": {
            "floor_far": {"value": [0.085, 0.092, 0.115],
                          "from": "dérivé de M1DecorGround :1144, légèrement relevé"},
            "floor_near_clay": {"value": [0.150, 0.120, 0.100],
                                "from": "dérivé de M1DecorPillarWarm :1147 vers une argile d'arène"},
            "backdrop": {"value": [[0.070, 0.082, 0.115], [0.026, 0.032, 0.052]],
                         "from": "teinte de HorizonColor :91, valeur abaissée pour que le fond recule"},
            "accent": {"value": GAME_DEPOSIT, "from": "M1PlaytestBuild.cs:1102 SandboxDeposit",
                       "carried_by": "lumière rim, pas par le matériau du décor"},
        },
    })


# =====================================================================
# CATÉGORIE 2 — éclairage
# =====================================================================
def category_lighting():
    key = bpy.data.objects[KEY]
    fill = bpy.data.objects[FILL]
    rim = bpy.data.objects[RIM]
    aim = Vector((0.0, 0.0, 0.72))

    # Géométrie du décor, mesurée sur le mesh : le sol va de y=-6 à y=1.8 à z=0,
    # l'arc raccorde jusqu'à (2.8, 1.0), puis le mur est VERTICAL à y=2.80.
    # Toute lumière placée à y>2.80 au-dessus de z=1.0 est donc derrière le mur.
    WALL_Y = 2.80

    # KEY : couleur exacte du jeu, resserrée pour redonner du modelé au volume.
    key.data.color = GAME_KEY
    key.data.energy = 600.0
    key.data.size = 2.8
    key.location = Vector((-2.60, -3.60, 3.60))
    look_at(key, aim)

    # FILL : bleu exact du jeu, côté caméra, doux et large, volontairement bas
    # pour que le côté ombre reste lisible sans effacer le modelé de la key.
    fill.data.color = GAME_FILL
    fill.data.energy = 130.0
    fill.data.size = 6.0
    fill.location = Vector((3.55, -3.05, 1.95))
    look_at(fill, aim)

    # RIM : porte l'accent. Essai 1 le plaçait à y=3.15, donc DERRIÈRE le mur :
    # il inondait le fond d'orange sans jamais raser le personnage. Ramené
    # devant le mur, plus près et plus petit, il grave maintenant une arête sur
    # la silhouette et décolle le bras écran-gauche du corps.
    # Essai 3 : à 300 W et z=2.20 il déversait une flaque orange sur tout le sol
    # et le fond écran-droit. Monté, rapproché, resserré et divisé par deux : la
    # chute en 1/d² pénalise alors le sol lointain bien plus que la silhouette,
    # donc l'accent redevient une arête fine au lieu d'un bain de couleur.
    rim.data.color = GAME_DEPOSIT
    rim.data.energy = 145.0
    rim.data.size = 0.9
    rim.location = Vector((-1.45, 1.30, 2.90))
    assert rim.location.y < WALL_Y, "le rim doit rester devant le mur du cyclorama"
    look_at(rim, Vector((0.0, 0.0, 0.95)))

    log["categories"].append({
        "category": "lighting",
        "attempt": 3,
        "attempt_1_rejected": ("rim à y=3.15, soit derrière le mur vertical du cyclorama (y=2.80) : "
                               "il éclairait le fond au lieu de raser la silhouette. Même défaut "
                               "que le rim de la baseline, placé à y=3.70."),
        "attempt_2_rejected": ("rim ramené devant le mur mais à 300 W et z=2.20 : il rasait bien la "
                               "silhouette mais noyait le sol et le fond écran-droit sous une flaque "
                               "orange, ce qui détruisait la séparation de ce côté."),
        "lights_added": 0,
        "cyclorama_wall_y": WALL_Y,
        "roles": {
            "key": {"color": GAME_KEY, "energy": 600.0, "size": 2.8,
                    "role": "exposition et volume", "source": "M1PlaytestBuild.cs:838"},
            "fill": {"color": GAME_FILL, "energy": 130.0, "size": 6.0,
                     "role": "lisibilité du côté ombre", "source": "M1PlaytestBuild.cs:849"},
            "rim": {"color": GAME_DEPOSIT, "energy": 145.0, "size": 0.9,
                    "role": "séparation du fond + accent narratif zone de dépôt",
                    "source": "M1PlaytestBuild.cs:1102"},
        },
    })


# =====================================================================
# CATÉGORIE 3 — caméra hero
# =====================================================================
def category_camera():
    hero = bpy.data.objects[HERO]
    target = bpy.data.objects[TARGET].location.copy()

    # Contrat de cadrage INCHANGÉ : compo centrée, DOF interdit.
    #
    # Le vrai défaut restant est géométrique : à 2.55 en X, l'angle trois-quarts
    # est assez fort pour que le bras écran-gauche passe DEVANT le corps et s'y
    # noie. On réduit l'angle sans passer plein face, pour garder le volume que
    # demande hero_intent tout en dégageant les deux bras.
    #
    # Cadrage visé, calculé et non deviné : lentille 58 mm sur capteur 36 mm
    # donne un demi-angle horizontal atan(18/58) = 17.24°. À 5.41 m de la cible
    # la fenêtre fait 3.36 x 1.89 m, donc un personnage de 1.36 m couvre ~0.72
    # en hauteur (cible 0.64-0.82) et ~0.52 en largeur (max 0.70).
    hero.data.lens = 58.0
    hero.location = Vector((1.75, -5.04, 1.58))
    look_at(hero, Vector((target.x, target.y, 0.70)))
    assert not hero.data.dof.use_dof, "le contrat interdit la profondeur de champ"

    log["categories"].append({
        "category": "hero_camera",
        "lens_mm": 58.0,
        "location": list(hero.location),
        "aim": [target.x, target.y, 0.70],
        "dof": False,
        "framing_contract": "inchangé (centré ±0.08, DOF interdit)",
        "predicted_height_coverage": 0.72,
        "predicted_width_coverage": 0.52,
        "reason": "réduire l'angle trois-quarts pour dégager le bras écran-gauche du corps",
    })


if UPTO >= 1:
    category_stage()
if UPTO >= 2:
    category_lighting()
if UPTO >= 3:
    category_camera()

scene["bas_status"] = "creative art direction pass by Claude: arena echo"
scene["bas_art_direction"] = "arena-echo"
scene["runtime_export"] = False

bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("ART_SAVED " + OUT)
print("ART_LOG " + json.dumps(log))
