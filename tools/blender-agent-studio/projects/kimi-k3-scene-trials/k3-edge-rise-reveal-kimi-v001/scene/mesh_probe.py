"""Mesure la position réelle du mesh déformé (pieds, bassin) à la frame 30."""
import bpy, collections
from mathutils import Vector

sc = bpy.context.scene
sc.frame_set(int(__import__('sys').argv[-1]) if __import__('sys').argv[-1].isdigit() else 30)
body = bpy.data.objects['K3_MECHA_BODY']
dg = bpy.context.evaluated_depsgraph_get()
ev = body.evaluated_get(dg)
mesh = ev.to_mesh()
fr_inv = bpy.data.objects['USTUDIO_BOX_FLOAT_ROOT'].matrix_world.inverted()
names = {g.index: g.name for g in body.vertex_groups}

def stat(ids, tag):
    pts = [fr_inv @ (ev.matrix_world @ mesh.vertices[i].co) for i in ids]
    if not pts:
        print(tag, 'EMPTY')
        return
    cx = sum(p.x for p in pts)/len(pts)
    cy = sum(p.y for p in pts)/len(pts)
    cz = sum(p.z for p in pts)/len(pts)
    print(tag, 'centroid float-local', round(cx,3), round(cy,3), round(cz,3),
          'zmin', round(min(p.z for p in pts),3), 'n', len(pts))
    agg = collections.Counter()
    for i in ids:
        for g in body.data.vertices[i].groups:
            agg[names[g.group]] += g.weight
    print('   weights:', {k: round(v/len(ids),2) for k, v in agg.most_common(4)})

rest = body.data.vertices
footL = [i for i, v in enumerate(rest) if v.co.z < 0.10 and v.co.x < -0.1]
footR = [i for i, v in enumerate(rest) if v.co.z < 0.10 and v.co.x > 0.1]
butt  = [i for i, v in enumerate(rest) if 0.60 < v.co.z < 0.75 and abs(v.co.x) < 0.22]
kneeL = [i for i, v in enumerate(rest) if 0.35 < v.co.z < 0.55 and v.co.x < -0.1]
stat(footL, 'FOOT_L')
stat(footR, 'FOOT_R')
stat(butt, 'BUTT')
stat(kneeL, 'KNEE_L')
ev.to_mesh_clear()
print('MESHPROBE_OK')
