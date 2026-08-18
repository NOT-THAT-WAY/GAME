# SB_Punch — anchor 1. Authored in the open MCP session only.
# 1-20 one-shot: guard f1, anticipation f3-5, impact f10, follow f11-13,
# recovery to exactly SB_Idle f1 at f20. Right jab toward -Y.
exec(open("projects/team/sandbox-character-force-combat-kimi-v001/scripts/mcp/kimi_anim_lib.py").read())

guard()
arm = get_arm()
sc = bpy.context.scene
sc.render.fps = 30
sc.render.fps_base = 1.0
sc.frame_start, sc.frame_end = 1, 20

P_IDLE = idle_f1_pose(arm)

UA_L, FA_L, HA_L = CHAINS[0]
UA_R, FA_R, HA_R = CHAINS[1]

# ---- pose specs -------------------------------------------------------
# guard: near Idle, fists slightly raised in front, body settled
GUARD = {
    BODY: ([(X, 3.0)], Vector((0.0, -0.008, -0.015))),
    UA_L: ([(X, -26.0), (Z, -9.0)], Vector((0.002, 0, 0))),
    FA_L: ([(X, -15.0)], Vector((0, 0, 0))),
    UA_R: ([(X, -26.0), (Z, 9.0)], Vector((-0.002, 0, 0))),
    FA_R: ([(X, -15.0)], Vector((0, 0, 0))),
}
# anticipation f5: right arm draws back/up, torso winds right
ANTIC = {
    BODY: ([(X, 2.0), (Z, -9.0)], Vector((0.01, 0.005, -0.02))),
    UA_L: ([(X, -32.0), (Z, -12.0)], Vector((0.004, 0, 0))),
    FA_L: ([(X, -18.0)], Vector((0, 0, 0))),
    UA_R: ([(X, -14.0), (Z, 15.0)], Vector((-0.008, 0, 0))),
    FA_R: ([(X, -29.0)], Vector((0, 0, 0))),
}
# impact f10: right fist extended toward -Y, torso twists into the punch
IMPACT = {
    BODY: ([(X, 8.0), (Z, 7.0)], Vector((-0.008, -0.042, -0.026))),
    UA_L: ([(X, -36.0), (Z, -14.0)], Vector((0.004, 0, 0))),
    FA_L: ([(X, -21.0)], Vector((0, 0, 0))),
    UA_R: ([(X, -52.0), (Z, 3.0)], Vector((-0.010, 0, 0))),
    FA_R: ([(X, -3.0)], Vector((0, 0, 0))),
    HA_R: ([(X, -6.0)], Vector((0, 0, 0))),
}
# follow f13: slight overshoot settling
FOLLOW = {
    BODY: ([(X, 6.5), (Z, 5.5)], Vector((-0.006, -0.034, -0.022))),
    UA_L: ([(X, -33.0), (Z, -13.0)], Vector((0.004, 0, 0))),
    FA_L: ([(X, -19.0)], Vector((0, 0, 0))),
    UA_R: ([(X, -47.0), (Z, 4.0)], Vector((-0.009, 0, 0))),
    FA_R: ([(X, -10.0)], Vector((0, 0, 0))),
    HA_R: ([(X, -5.0)], Vector((0, 0, 0))),
}

KEYS = [(1, "GUARD"), (5, "ANTIC"), (10, "IMPACT"), (13, "FOLLOW"), (20, "IDLE")]
SPECS = {"GUARD": GUARD, "ANTIC": ANTIC, "IMPACT": IMPACT, "FOLLOW": FOLLOW}

POSES = {k: compute_pose(arm, SPECS[k]) for k in SPECS}
POSES["IDLE"] = P_IDLE

# nudge GUARD toward IDLE compatibility: report deltas
dt_g, dr_g = pose_delta(POSES["GUARD"], P_IDLE)

act = new_action(arm, "SB_Punch")

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

for f in range(1, 21):
    sc.frame_set(f)
    apply_pose(arm, pose_at(f))
    key_all(arm, f)

force_linear(act)
sc.frame_set(1)

# quick numeric sanity: fist world positions at beats, f20 vs Idle f1
res = {"guard_vs_idle": {"dt_m": round(dt_g, 5), "dr_deg": round(dr_g, 3)}}
for f in (1, 5, 10, 13, 20):
    sc.frame_set(f)
    bpy.context.view_layer.update()
    res["fists_f%d" % f] = fist_positions(arm)
sc.frame_set(20)
d20 = pose_delta(capture_pose(arm), P_IDLE)
res["f20_vs_idle_f1"] = {"dt_m": round(d20[0], 6), "dr_deg": round(d20[1], 4)}
res["action"] = act.name
res["frame_range"] = list(act.frame_range)
print(json.dumps(res))
