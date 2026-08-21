# SB_HitReact — anchor 2. MCP session only.
# 1-18 one-shot: start Idle f1, impact f2-3, upper-body recoil + face cover
# until f8, recovery to exactly SB_Idle f1 at f18. No fall, no root motion,
# centre of mass essentially in place (recoil read through rotation).
exec(open("projects/team/sandbox-character-force-combat-kimi-v001/scripts/mcp/kimi_anim_lib.py").read())

guard()
arm = get_arm()
sc = bpy.context.scene
sc.render.fps = 30
sc.render.fps_base = 1.0
sc.frame_start, sc.frame_end = 1, 18

P_IDLE = idle_f1_pose(arm)
UA_L, FA_L, HA_L = CHAINS[0]
UA_R, FA_R, HA_R = CHAINS[1]

# hit f3: sharp backward pitch (top of body toward +Y), fists fly up to cover
HIT = {
    BODY: ([(X, -10.0), (Z, 2.0)], Vector((0.0, 0.012, 0.004))),
    UA_L: ([(X, -46.0), (Z, -13.0)], Vector((0.003, 0, 0))),
    FA_L: ([(X, -18.0)], Vector((0, 0, 0))),
    UA_R: ([(X, -46.0), (Z, 13.0)], Vector((-0.003, 0, 0))),
    FA_R: ([(X, -14.0)], Vector((0, 0, 0))),
}
# protect f8: recoil decays, cover held
PROTECT = {
    BODY: ([(X, -6.5), (Z, 1.0)], Vector((0.0, 0.008, 0.002))),
    UA_L: ([(X, -39.0), (Z, -11.0)], Vector((0.003, 0, 0))),
    FA_L: ([(X, -14.0)], Vector((0, 0, 0))),
    UA_R: ([(X, -39.0), (Z, 11.0)], Vector((-0.003, 0, 0))),
    FA_R: ([(X, -14.0)], Vector((0, 0, 0))),
}

KEYS = [(1, "IDLE"), (3, "HIT"), (8, "PROTECT"), (18, "IDLE")]
SPECS = {"HIT": HIT, "PROTECT": PROTECT}
POSES = {k: compute_pose(arm, SPECS[k]) for k in SPECS}
POSES["IDLE"] = P_IDLE

# ride-out: during the cover, forearms slide ~3 mm along the arm axis so the
# elbow socket keeps its rest baseline (socket is a source construction
# overlap; the animation must not deepen it).
def ride_out(pose, mm):
    for ua, fa, ha in CHAINS:
        d = (pose[fa].translation - pose[ua].translation).normalized()
        off = d * (mm / 1000.0)
        for b in (fa, ha):
            pose[b] = Matrix.Translation(off) @ pose[b]

ride_out(POSES["HIT"], 3.0)
ride_out(POSES["PROTECT"], 2.0)

act = new_action(arm, "SB_HitReact")

def pose_at(f):
    for i in range(len(KEYS) - 1):
        f0, k0 = KEYS[i]
        f1_, k1 = KEYS[i + 1]
        if f0 <= f <= f1_:
            if f == f0:
                return POSES[k0]
            t = smoothstep((f - f0) / (f1_ - f0))
            return blend_poses(POSES[k0], POSES[k1], t)
    return POSES[KEYS[-1][1]]

for f in range(1, 19):
    sc.frame_set(f)
    apply_pose(arm, pose_at(f))
    key_all(arm, f)

force_linear(act)
sc.frame_set(1)

res = {}
for f in (1, 3, 8, 18):
    sc.frame_set(f)
    bpy.context.view_layer.update()
    res["fists_f%d" % f] = fist_positions(arm)
d = pose_delta(capture_pose(arm), P_IDLE)
res["f18_vs_idle_f1"] = {"dt_m": round(d[0], 6), "dr_deg": round(d[1], 4)}
d0 = pose_delta(POSES["HIT"], P_IDLE)
res["hit_vs_idle"] = {"dt_m": round(d0[0], 5), "dr_deg": round(d0[1], 3)}
res["action"] = act.name
res["frame_range"] = list(act.frame_range)
print(json.dumps(res))
