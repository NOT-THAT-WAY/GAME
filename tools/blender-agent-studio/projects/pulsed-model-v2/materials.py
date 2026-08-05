"""Materiaux Pulsed v2, cales sur refB (violet amethyste translucide).

La cle du look : la coque n'est pas un plastique diffus teinte, c'est une paroi
mince en transmission avec une absorption volumique violette. C'est elle qui
donne la profondeur et laisse lire le PCB derriere.
"""

import bpy


def _new(name):
    m = bpy.data.materials.get(name)
    if m:
        bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, m.node_tree.nodes["Principled BSDF"]


def shell_purple(name="M_shell_purple", roughness=0.12, transmission=0.95,
                 color=(0.30, 0.15, 0.55)):
    """Amethyste translucide.

    PAS d'absorption volumique : la coque est une paroi mince fermee par
    Solidify, et Cycles finit par traiter toute la cavite interne comme le
    volume — resultat, un brouillard violet qui noie le PCB. La teinte passe
    donc par la couleur de transmission, ce qui reste net et previsible.
    """
    m, b = _new(name)
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = roughness
    b.inputs["Transmission Weight"].default_value = transmission
    b.inputs["IOR"].default_value = 1.53
    b.inputs["Metallic"].default_value = 0.0
    return m


def shell_purple_glossy(name="M_shell_purple_glossy"):
    """Dômes de molette : même teinte, poli miroir."""
    return shell_purple(name, roughness=0.03, transmission=0.97)


def control_grey(name="M_control_grey", color=(0.50, 0.49, 0.53)):
    m, b = _new(name)
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = 0.38
    b.inputs["Specular IOR Level"].default_value = 0.45
    return m


def control_grey_dark(name="M_control_grey_dark"):
    """Pour les textes graves (SYNC) : doivent se detacher du bouton."""
    return control_grey(name, color=(0.30, 0.29, 0.32))


def control_white(name="M_control_white"):
    m, b = _new(name)
    b.inputs["Base Color"].default_value = (0.70, 0.70, 0.72, 1.0)
    b.inputs["Roughness"].default_value = 0.42
    return m


def pcb(name="M_pcb"):
    """Carte sombre + reseau de pistes procedural.

    Vu a travers la coque translucide, ce sont les pistes qui donnent la
    lecture « electronique » — un aplat sombre lit comme une plaque grise.
    """
    m, b = _new(name)
    b.inputs["Roughness"].default_value = 0.5
    nt = m.node_tree

    coord = nt.nodes.new("ShaderNodeTexCoord"); coord.location = (-1200, 0)
    mapping = nt.nodes.new("ShaderNodeMapping"); mapping.location = (-1020, 0)
    mapping.inputs["Scale"].default_value = (1.0, 1.0, 1.0)

    def wave(rot_z, scale, loc):
        w = nt.nodes.new("ShaderNodeTexWave")
        w.wave_type = "BANDS"
        w.bands_direction = "X"
        w.wave_profile = "SAW"
        # Les coordonnees Objet du PCB vont a +/-6.9 BU : une echelle de 26
        # donnerait ~360 bandes en travers, ca aliase en aplat gris.
        w.inputs["Scale"].default_value = scale
        # Distortion faible : on veut des PISTES, pas des flaques de cuivre.
        w.inputs["Distortion"].default_value = 0.7
        w.inputs["Detail"].default_value = 1.0
        w.inputs["Detail Scale"].default_value = 0.8
        w.location = loc
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Rotation"].default_value = (0, 0, rot_z)
        mp.location = (loc[0] - 180, loc[1])
        nt.links.new(mapping.outputs["Vector"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], w.inputs["Vector"])
        return w

    w1 = wave(0.0, 3.2, (-620, 220))
    w2 = wave(1.5708, 2.4, (-620, -160))

    def band(w, loc):
        """Bande FINE autour d'une valeur : une piste, pas un aplat.

        Un simple seuil laissait passer 56 % de cuivre — la carte virait au
        mauve clair au lieu de rester sombre.
        """
        r = nt.nodes.new("ShaderNodeValToRGB")
        r.location = loc
        cr = r.color_ramp
        cr.elements[0].position = 0.60
        cr.elements[0].color = (0, 0, 0, 1)
        cr.elements[1].position = 0.655
        cr.elements[1].color = (1, 1, 1, 1)
        tail = cr.elements.new(0.71)
        tail.color = (0, 0, 0, 1)
        nt.links.new(w.outputs["Fac"], r.inputs["Fac"])
        return r

    b1 = band(w1, (-420, 220))
    b2 = band(w2, (-420, -160))

    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MAXIMUM"
    mx.location = (-250, 40)
    nt.links.new(b1.outputs["Color"], mx.inputs[0])
    nt.links.new(b2.outputs["Color"], mx.inputs[1])

    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.location = (-60, 120)
    mix.inputs[6].default_value = (0.010, 0.014, 0.032, 1.0)   # masque de soudure
    mix.inputs[7].default_value = (0.38, 0.23, 0.10, 1.0)      # cuivre
    nt.links.new(mx.outputs["Value"], mix.inputs["Factor"])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])

    nt.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    return m


def pcb_component(name="M_pcb_component", color=(0.016, 0.016, 0.019)):
    """Boitiers noir mat : ils doivent se lire par leur silhouette et leur
    speculaire, pas par leur valeur — la carte est deja tres sombre."""
    m, b = _new(name)
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = 0.34
    return m


def copper(name="M_copper"):
    m, b = _new(name)
    b.inputs["Base Color"].default_value = (0.55, 0.36, 0.20, 1.0)
    b.inputs["Metallic"].default_value = 0.85
    b.inputs["Roughness"].default_value = 0.38
    return m


def dark_metal(name="M_dark_metal"):
    m, b = _new(name)
    b.inputs["Base Color"].default_value = (0.30, 0.31, 0.33, 1.0)
    b.inputs["Metallic"].default_value = 0.9
    b.inputs["Roughness"].default_value = 0.33
    return m


def screen_glass(name="M_screen_glass"):
    m, b = _new(name)
    b.inputs["Base Color"].default_value = (0.008, 0.010, 0.014, 1.0)
    b.inputs["Roughness"].default_value = 0.09
    b.inputs["Specular IOR Level"].default_value = 0.6
    return m


def screen_ui(name="M_screen_ui", image=None, strength=2.6):
    """Dalle emissive portant la texture d'UI."""
    m = bpy.data.materials.get(name)
    if m:
        bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = nt.nodes["Material Output"]

    emit = nt.nodes.new("ShaderNodeEmission")
    emit.location = (-200, 0)
    emit.inputs["Strength"].default_value = strength

    if image is not None:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.location = (-520, 0)
        tex.image = image
        tex.interpolation = "Closest"
        tex.extension = "CLIP"
        nt.links.new(tex.outputs["Color"], emit.inputs["Color"])
    else:
        emit.inputs["Color"].default_value = (0.05, 0.10, 0.12, 1.0)

    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return m


def shell_purple_thin(name="M_shell_purple_thin"):
    """Pieces minces (rail du slider, embossages) : teinte plus claire,
    sinon elles virent au noir alors que la ref les montre lumineuses."""
    return shell_purple(name, roughness=0.09, transmission=0.93,
                        color=(0.44, 0.27, 0.72))


def build_all():
    return {
        "shell": shell_purple(),
        "shell_thin": shell_purple_thin(),
        "shell_glossy": shell_purple_glossy(),
        "grey": control_grey(),
        "grey_dark": control_grey_dark(),
        "white": control_white(),
        "pcb": pcb(),
        "component": pcb_component(),
        "copper": copper(),
        "metal": dark_metal(),
        "glass": screen_glass(),
    }
