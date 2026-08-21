"""Dispatcher for the 7 force / combat / life-state clips.

Runs inside the live MCP session on Kimi's master (port 9880).
"""
import math

import clips_kimi as K
from clips_kimi import arms, feet, merge, pose
from pose_kernel import BODY, FOOT_L, FOOT_R

BUILDERS = {}
LOOPS = {"SB_Push", "SB_WallPushed", "SB_KnockedOutLoop"}


def builder(name):
    def wrap(fn):
        BUILDERS[name] = fn
        return fn
    return wrap


def build(name):
    if name not in BUILDERS:
        raise KeyError(f"clip inconnu: {name} (connus: {sorted(BUILDERS)})")
    return BUILDERS[name]()


def _clip(name, f0, f1, keyposes, periodic, declared=None):
    n = f1 - f0 + 1
    base = {"loop": periodic, "samples": n, "duration_s": (n - 1) / 30.0}
    base.update(declared or {})
    return {"name": name, "f_start": f0, "f_end": f1, "periodic": periodic,
            "keyposes": keyposes, "declared": base}


def _pin_feet(keyposes, f0, f1, foot_pose=None):
    """Key both feet on EVERY frame of a planted range.

    Sparse keys let the Catmull-Rom tangent from the next airborne key dip the
    sole under the floor while the foot is still meant to be planted.
    """
    foot_pose = foot_pose if foot_pose is not None else feet()
    for f in range(f0, f1 + 1):
        keyposes.setdefault(f, {})
        keyposes[f][FOOT_L] = foot_pose[FOOT_L]
        keyposes[f][FOOT_R] = foot_pose[FOOT_R]
    return keyposes


# ------------------------------------------------------------------ SB_Punch
@builder("SB_Punch")
def _punch():
    """Right fist punches, left fist guards. Asymmetric throughout.

    Re-authored at 30 fps from readable poses rather than retimed from the
    existing 24 fps placeholder: changing a scene's fps does not respace an
    action, it only relabels it.
    """
    keyposes = {
        1: merge({BODY: pose(rx=2.0, rz=-4.0)},
                 arms("guard", left_blend=0.92, right_blend=0.92)),
        # Anticipation: the punching shoulder loads back, the body coils away.
        4: merge({BODY: pose(dz=-0.012, rx=-2.0, rz=-11.0)},
                 arms("guard", left_blend=0.95, right_blend=0.70,
                      right_extra=(26.0, -6.0, 0.0))),
        6: merge({BODY: pose(dz=-0.008, rx=1.0, rz=-9.0)},
                 arms("guard", left_blend=0.96, right_blend=0.62,
                      right_extra=(30.0, -7.0, 0.0))),
        # Visual impact. No AnimationEvent: this frame is a reading mark only.
        10: merge({BODY: pose(dz=0.006, rx=K.SOLVED["punch"]["body_rx"] * 0.85, rz=9.0)},
                  arms("guard", right_key="punch", left_blend=0.88, right_blend=1.0,
                       left_extra=(6.0, 0.0, 0.0))),
        13: merge({BODY: pose(dz=0.002, rx=K.SOLVED["punch"]["body_rx"] * 0.62, rz=6.0)},
                  arms("guard", right_key="punch", left_blend=0.85, right_blend=0.78,
                       right_extra=(10.0, -4.0, 0.0))),
        16: merge({BODY: pose(rx=6.0, rz=2.0)},
                  arms("guard", left_blend=0.55, right_blend=0.45)),
        20: merge({BODY: pose(rx=2.0)}, arms("guard", left_blend=0.0, right_blend=0.0)),
    }
    _pin_feet(keyposes, 1, 20, feet(dx=0.05))
    return _clip("SB_Punch", 1, 20, keyposes, False, {
        "intent": "garde f1, anticipation f3-5, impact VISUEL f10, suivi f11-13, "
                  "recuperation compatible Idle f20",
        "impact_frame": 10,
        "reauthored_at_30fps": True,
        "asymmetry": "poing droit frappe, poing gauche garde",
    })


# --------------------------------------------------------------- SB_HitReact
@builder("SB_HitReact")
def _hit_react():
    keyposes = {
        1: merge({BODY: pose(rx=2.0)}, arms("guard", left_blend=0.0, right_blend=0.0)),
        # Impact: the upper volume is driven back and slightly across.
        2: merge({BODY: pose(dz=0.004, dy=0.011, rx=-4.5, rz=3.0)},
                 arms("guard", left_blend=0.14, right_blend=0.12,
                      left_extra=(5.0, 0.0, 0.0), right_extra=(4.0, 0.0, 0.0))),
        3: merge({BODY: pose(dz=0.008, dy=0.020, rx=-9.0, rz=6.0)},
                 arms("guard", left_blend=0.28, right_blend=0.24,
                      left_extra=(9.0, 0.0, 0.0), right_extra=(7.0, 0.0, 0.0))),
        5: merge({BODY: pose(dz=0.004, dy=0.022, rx=-7.0, rz=5.0)},
                 arms("guard", left_blend=0.58, right_blend=0.55,
                      left_extra=(0.0, -14.0, 0.0), right_extra=(0.0, -14.0, 0.0))),
        # Face protected, still recoiled.
        8: merge({BODY: pose(dz=-0.006, dy=0.010, rx=-1.0, rz=2.0)},
                 arms("guard", left_blend=0.70, right_blend=0.68,
                      left_extra=(0.0, -16.0, 0.0), right_extra=(0.0, -16.0, 0.0))),
        12: merge({BODY: pose(rx=1.0)},
                  arms("guard", left_blend=0.42, right_blend=0.40,
                       left_extra=(0.0, -10.0, 0.0), right_extra=(0.0, -10.0, 0.0))),
        18: merge({BODY: pose(rx=2.0)}, arms("guard", left_blend=0.0, right_blend=0.0)),
    }
    _pin_feet(keyposes, 1, 18, feet(dx=0.04))
    return _clip("SB_HitReact", 1, 18, keyposes, False, {
        "intent": "depart Idle, impact f2-3, recul et protection jusqu'a f8, "
                  "recuperation compatible Idle f18",
        "impact_frame": 3,
        "no_fall": True,
    })


# ------------------------------------------------------------------- SB_Push
@builder("SB_Push")
def _push():
    """The player ACTS: wide planted stance, body tipped into the wall.

    The stance is wide by a constant offset, which is a stance and not a drift:
    the feet never move across the cycle. The effort breathes through the body
    only, and by a deliberately small amount, because the brief forbids the
    hands pumping on the wall.
    """
    keyposes = {}
    for f in range(1, 31):
        th = 2.0 * math.pi * (f - 1) / 30.0
        effort = math.sin(th)
        # Effort amplitude is set by the wall, not by taste. Counter-rotating
        # the arms cannot cancel the body's swing exactly: the body pivots at
        # z = 0.30 and the shoulder at z = 0.92, so the two levers differ and a
        # residual always survives. The cycle is therefore scaled until that
        # residual fits the 10 mm no-pump budget: at 1.1 deg the hands travelled
        # 24.9 mm, so 0.35 deg leaves about 8 mm.
        body = pose(dz=-0.010 + 0.0012 * effort,
                    rx=K.SOLVED["push"]["body_rx"] + 0.35 * effort,
                    ry=0.20 * math.sin(2.0 * th))
        # The arms COUNTER-rotate the body's effort so the hands stay put on the
        # wall. The sign matters and was wrong first time: +rx leans the body
        # forward but swings an arm backward, so holding a hand still against a
        # forward lean needs +rx on the arm too. Signing it negative added the
        # two motions instead of cancelling them and the hands pumped 23.7 mm.
        keyposes[f] = merge(
            {BODY: body},
            feet(dx=0.12, dy=0.06),
            arms("push",
                 left_extra=(0.35 * effort, 0.0, 0.0),
                 right_extra=(0.35 * effort, 0.0, 0.0)),
        )
    return _clip("SB_Push", 1, 30, keyposes, True, {
        "intent": "pieds ecartes et stables, corps bascule vers l'avant, mains en "
                  "appui contre un plan proxy, effort cyclique sans pompage",
        "stance_offset_m": 0.12,
        "proxy_plane": "derive de la geometrie evaluee des poings, preuve seulement, jamais exporte",
    })


# ------------------------------------------------------------- SB_WallPushed
@builder("SB_WallPushed")
def _wall_pushed():
    """The player SUFFERS: the body lags the external translation.

    The wall's push is applied by the simulation, never by the clip, so the root
    stays still and only the body's lag, the counterweight arms and small
    alternating catch-up steps are animated. Each foot returns to exactly the
    place it left, so the clip carries no implied travel and stays readable at
    any WallPushSpeed between 1 and 3.5 m/s.

    There is no fresh impact at the seam: the lag is a steady oscillation, not a
    hit replayed every 24 frames.
    """
    keyposes = {}
    lift, reach = 0.075, 0.10
    for f in range(1, 25):
        th = 2.0 * math.pi * (f - 1) / 24.0
        lag = math.sin(th)
        body = pose(dy=0.030 + 0.012 * lag, dz=-0.006,
                    rx=-9.0 + 2.2 * lag, ry=2.4 * math.cos(th), rz=1.6 * lag)

        def step(offset):
            # One foot at a time, each hopping and landing back on its own spot.
            phase = (th + offset) % (2.0 * math.pi)
            if phase >= math.pi:
                return 0.0, 0.0
            s = phase / math.pi
            return lift * math.sin(math.pi * s) ** 1.5, -reach * math.sin(math.pi * s)

        zl, yl = step(0.0)
        zr, yr = step(math.pi)
        keyposes[f] = merge(
            {BODY: body},
            feet(dx=0.10, dz_l=zl, dz_r=zr, dy_l=yl, dy_r=yr,
                 rx_l=-6.0 * (zl / lift if lift else 0.0),
                 rx_r=-6.0 * (zr / lift if lift else 0.0)),
            arms("guard", left_blend=0.30, right_blend=0.30,
                 left_extra=(6.0 * lag, -18.0, 0.0),
                 right_extra=(-6.0 * lag, -18.0, 0.0)),
        )
    return _clip("SB_WallPushed", 1, 24, keyposes, True, {
        "intent": "volume en retard sur la translation externe, bascule amortie, "
                  "bras en contrepoids, petits pas alternes",
        "credible_speed_range_mps": [1.0, 3.5],
        "no_impact_at_seam": True,
        "direction_neutral": True,
    })


# --------------------------------------------------------- SB_KnockedOutLoop
@builder("SB_KnockedOutLoop")
def _ko_loop():
    keyposes = {f: K.ko_pose_breathing((f - 1) / 60.0) for f in range(1, 61)}
    return _clip("SB_KnockedOutLoop", 1, 60, keyposes, True, {
        "intent": "corps au sol, contacts stables, respiration a peine visible, "
                  "lecture KO et non Idle couche",
        "anchor_frame_1": "reference exacte des deux transitions",
    })


# ----------------------------------------------------------------- SB_Knockout
@builder("SB_Knockout")
def _knockout():
    """Idle to the KO anchor. Frame 30 IS the anchor, not an approximation."""
    keyposes = {
        1: merge({BODY: pose(rx=2.0)}, feet(), arms("guard", left_blend=0.0, right_blend=0.0)),
        # Balance breaks: the volume tips back, arms fly up as counterweight.
        2: merge({BODY: pose(dz=0.001, dy=0.002, rx=-1.6, rz=0.6)}, feet(),
                 arms("splay", left_blend=0.05, right_blend=0.04,
                      left_extra=(-2.5, 0.0, 0.0), right_extra=(-2.0, 0.0, 0.0))),
        3: merge({BODY: pose(dz=0.003, dy=0.006, rx=-4.0, rz=1.6)}, feet(),
                 arms("splay", left_blend=0.10, right_blend=0.09,
                      left_extra=(-3.5, 0.0, 0.0), right_extra=(-3.0, 0.0, 0.0))),
        # The counterweight arms are ramped over four keys instead of two: with
        # a single jump from blend 0.12 to 0.35 the shoulder moved 9.6 deg in
        # one frame against a 1.4 deg median, which reads as a snap rather than
        # as a body losing its balance.
        4: merge({BODY: pose(dz=0.004, dy=0.010, rx=-6.6, rz=2.3)}, feet(),
                 arms("splay", left_blend=0.17, right_blend=0.15,
                      left_extra=(-7.0, 0.0, 0.0), right_extra=(-6.0, 0.0, 0.0))),
        5: merge({BODY: pose(dz=0.006, dy=0.016, rx=-10.0, rz=3.4)}, feet(),
                 arms("splay", left_blend=0.25, right_blend=0.22,
                      left_extra=(-11.0, 0.0, 0.0), right_extra=(-9.5, 0.0, 0.0))),
        6: merge({BODY: pose(dz=0.005, dy=0.026, rx=-15.0, rz=4.4)}, feet(),
                 arms("splay", left_blend=0.34, right_blend=0.30,
                      left_extra=(-14.5, 0.0, 0.0), right_extra=(-12.5, 0.0, 0.0))),
        8: merge({BODY: pose(dz=0.004, dy=0.045, rx=-22.0, rz=6.0)},
                 feet(dx=0.06, dy=-0.06, dz=0.03),
                 arms("splay", left_blend=0.55, right_blend=0.50,
                      left_extra=(-20.0, 0.0, 0.0), right_extra=(-18.0, 0.0, 0.0))),
        # Controlled descent.
        14: merge({BODY: pose(dz=-0.012, dy=0.040, rx=-34.0, rz=5.0)},
                  feet(dx=0.09, dy=-0.18, dz=0.11),
                  arms("splay", left_blend=0.75, right_blend=0.72,
                       left_extra=(-10.0, 0.0, 0.0), right_extra=(-9.0, 0.0, 0.0))),
        # First ground contact must land before frame 22. Measured at frame 24 on
        # the first attempt, so the descent is brought forward rather than the
        # requirement reinterpreted.
        18: merge({BODY: pose(dz=-0.060, dy=0.020, rx=-45.0, rz=2.5)},
                  feet(dx=0.10, dy=-0.28, dz=0.16, rx=-22.0),
                  arms("splay", left_blend=0.88, right_blend=0.86,
                       left_extra=(-3.0, 0.0, 0.0))),
        20: merge({BODY: pose(dz=-0.0685, dy=0.016, rx=-49.0, rz=1.2)},
                  feet(dx=0.10, dy=-0.31, dz=0.175, rx=-25.0),
                  arms("splay", left_blend=0.94, right_blend=0.92,
                       left_extra=(-1.0, 0.0, 0.0))),
        23: merge({BODY: pose(dz=-0.0640, dy=0.014, rx=-50.8)},
                  feet(dx=0.10, dy=-0.330, dz=0.183, rx=-26.5),
                  arms("splay", left_extra=(5.5, 0.0, 0.0), right_extra=(-3.4, 0.0, 0.0))),
        25: merge({BODY: pose(dz=-0.0635, dy=0.013, rx=-51.0)},
                  feet(dx=0.10, dy=-0.335, dz=0.185, rx=-27.0),
                  arms("splay", left_extra=(5.0, 0.0, 0.0), right_extra=(-3.0, 0.0, 0.0))),
        27: merge({BODY: pose(dz=-0.0650, dy=0.012, rx=-50.6)},
                  feet(dx=0.10, dy=-0.337, dz=0.187, rx=-27.4),
                  arms("splay", left_extra=(4.6, 0.0, 0.0), right_extra=(-2.6, 0.0, 0.0))),
        30: dict(K.KO_POSE),
    }
    # Hold the feet exactly at rest across the declared stance window: with only
    # sparse keys they crept 11.7 mm toward the next key while still supposed to
    # be planted, and clipped 2.4 mm through the floor on the way.
    for f in range(1, 6):
        keyposes.setdefault(f, {}).update(feet())
    return _clip("SB_Knockout", 1, 30, keyposes, False, {
        "intent": "rupture d'equilibre f1-8, descente controlee, premier contact "
                  "sol avant f22, f30 identique a SB_KnockedOutLoop f1",
        "first_ground_contact_before": 22,
        "interface_pose": "frame 30 == SB_KnockedOutLoop frame 1",
    })


# ------------------------------------------------------------------ SB_Recover
@builder("SB_Recover")
def _recover():
    """The KO anchor back to Idle, using only joints this rig actually has."""
    keyposes = {
        1: dict(K.KO_POSE),
        # Hands press the floor.
        6: merge({BODY: pose(dz=-0.0655, dy=0.012, rx=-47.0)},
                 feet(dx=0.10, dy=-0.31, dz=0.16, rx=-24.0),
                 arms("splay", left_extra=(-6.0, 6.0, 0.0), right_extra=(-6.0, 6.0, 0.0))),
        14: merge({BODY: pose(dz=-0.050, dy=0.028, rx=-33.0)},
                  feet(dx=0.09, dy=-0.20, dz=0.12, rx=-18.0),
                  arms("splay", left_blend=0.80, right_blend=0.80,
                       left_extra=(-16.0, 8.0, 0.0), right_extra=(-16.0, 8.0, 0.0))),
        # The feet come back under the body. No knee is simulated: they are free
        # volumes parented to the root, so they simply travel.
        22: merge({BODY: pose(dz=-0.026, dy=0.016, rx=-16.0)},
                  feet(dx=0.06, dy=-0.08, dz=0.05, rx=-8.0),
                  arms("splay", left_blend=0.50, right_blend=0.50,
                       left_extra=(-12.0, 4.0, 0.0), right_extra=(-12.0, 4.0, 0.0))),
        28: merge({BODY: pose(dz=-0.006, rx=-4.0)}, feet(),
                  arms("guard", left_blend=0.28, right_blend=0.28)),
        36: merge({BODY: pose(rx=2.0)}, feet(),
                  arms("guard", left_blend=0.0, right_blend=0.0)),
    }
    for f in range(28, 37):
        keyposes.setdefault(f, {}).update(feet())
    return _clip("SB_Recover", 1, 36, keyposes, False, {
        "intent": "f1 identique a SB_KnockedOutLoop f1, appui des mains, "
                  "redressement, f36 compatible SB_Idle",
        "interface_pose": "frame 1 == SB_KnockedOutLoop frame 1",
        "no_invented_joint": True,
    })
