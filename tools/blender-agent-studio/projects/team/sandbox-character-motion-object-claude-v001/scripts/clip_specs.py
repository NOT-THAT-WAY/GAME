"""Dispatcher turning a clip name into {name, range, periodic, keyposes, declared}.

Runs inside the live MCP session. Each entry declares the contract values that
the measurement pass later verifies independently, so a clip cannot claim a
range, a loop flag or a nominal speed that its evidence does not support.
"""
import math

import clips
from pose_kernel import BODY, FOOT_L, FOOT_R, ARM_L, ARM_R

BUILDERS = {}


def builder(name):
    def wrap(fn):
        BUILDERS[name] = fn
        return fn
    return wrap


def build(name):
    if name not in BUILDERS:
        raise KeyError(f"clip inconnu: {name} (connus: {sorted(BUILDERS)})")
    return BUILDERS[name]()


def _locomotion(spec, carry_arms=None):
    keyposes = clips.locomotion_keyposes(spec, carry_arms=carry_arms)
    n = spec["f_end"] - spec["f_start"] + 1
    stance = round(n * spec["duty"])
    return {
        "name": spec["name"],
        "f_start": spec["f_start"],
        "f_end": spec["f_end"],
        "periodic": spec["periodic"],
        "keyposes": keyposes,
        "declared": {
            "loop": True,
            "samples": n,
            "duration_s": (n - 1) / 30.0,
            "nominal_speed_mps": spec["speed"],
            "gameplay_speed_mps": 4.2 if "Sprint" not in spec["name"] else 7.0,
            "playback_multiplier": (4.2 if "Sprint" not in spec["name"] else 7.0) / spec["speed"],
            "duty_factor": spec["duty"],
            "stance_frames": stance,
            "swing_frames": n - stance,
            "stance_excursion_m": spec["speed"] * stance / 30.0,
            "stride_per_cycle_m": spec["speed"] * n / 30.0,
            "contacts": {"L": spec["contact_l"], "R": spec["contact_r"]},
            "swing_apex": {"L": spec["apex_l"], "R": spec["apex_r"]},
            "foot_lift_m": spec["lift"],
        },
    }


@builder("SB_Walk")
def _walk():
    return _locomotion(clips.WALK)


@builder("SB_Sprint")
def _sprint():
    return _locomotion(clips.SPRINT)


def _pin_feet(keyposes, f0, f1):
    """Key both feet on EVERY frame of a planted range.

    With only sparse keys, the Catmull-Rom tangent at the last planted key is
    computed from the next airborne key, so the curve dips before it rises and
    drives the sole a couple of millimetres under the floor while the foot is
    still supposed to be planted. Keying every frame removes the tangent instead
    of fighting it.
    """
    for f in range(f0, f1 + 1):
        keyposes.setdefault(f, {})
        keyposes[f][FOOT_L] = clips.pose()
        keyposes[f][FOOT_R] = clips.pose()
    return keyposes


def _smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _oneshot(name, f0, f1, keyposes, declared=None):
    n = f1 - f0 + 1
    base = {"loop": False, "samples": n, "duration_s": (n - 1) / 30.0}
    base.update(declared or {})
    return {"name": name, "f_start": f0, "f_end": f1, "periodic": False,
            "keyposes": keyposes, "declared": base}


def _static_loop(name, f0, f1, keyposes, declared=None):
    n = f1 - f0 + 1
    base = {"loop": True, "samples": n, "duration_s": (n - 1) / 30.0}
    base.update(declared or {})
    return {"name": name, "f_start": f0, "f_end": f1, "periodic": True,
            "keyposes": keyposes, "declared": base}


def _merge(*dicts):
    out = {}
    for d in dicts:
        out.update(d)
    return out


# The single airborne pose. It is defined once because SB_JumpTakeoff's last
# frame and SB_Airborne's first frame must be the SAME pose, otherwise the
# engine pops when the jump hands over to the fall.
# Measured ceiling on any downward body motion. The body sphere's underside and
# the foot domes leave only 0.0534 m of room at their tightest slice (x = 0.204),
# so this character cannot crouch by dropping its body much further than that;
# a first pass at -0.16 m buried the feet 0.108 m inside the belly. Compression
# is therefore carried by pitch and arms, and the dip stays under this value.
# Forward pitch also lowers the sphere (about 10 mm at 12 deg), which is why the
# authored dips stay well below the raw ceiling.
BODY_DIP_MAX = 0.0534

AIR_OUT, AIR_LIFT = 0.22, 0.09


def _airborne_pose(phase):
    """`phase` in [0,1) around the 24-frame cycle."""
    wobble = math.sin(2.0 * math.pi * phase)
    wobble2 = math.sin(4.0 * math.pi * phase)
    body = clips.pose(dz=0.020 + 0.012 * wobble, rx=-4.0 + 1.6 * wobble2,
                      ry=1.2 * wobble)
    feet = {
        FOOT_L: clips.pose(dx=AIR_OUT, dy=0.05 + 0.02 * wobble,
                           dz=AIR_LIFT + 0.015 * wobble, rx=-9.0 + 4.0 * wobble),
        FOOT_R: clips.pose(dx=-AIR_OUT, dy=0.05 - 0.02 * wobble,
                           dz=AIR_LIFT - 0.015 * wobble, rx=-9.0 - 4.0 * wobble),
    }
    arms = clips.arm_pair("release", blend=0.55,
                          extra_upper=(-6.0 + 3.0 * wobble, -14.0, 0.0),
                          extra_fore=(0.0, 0.0, 0.0))
    return _merge({BODY: body}, feet, arms)


@builder("SB_Airborne")
def _airborne():
    keyposes = {f: _airborne_pose((f - 1) / 24.0) for f in range(1, 25)}
    return _static_loop("SB_Airborne", 1, 24, keyposes, {
        "intent": "pose aerienne stable, faible balancier, aucun pedalage",
        "foot_out_m": AIR_OUT, "foot_lift_m": AIR_LIFT,
    })


@builder("SB_CarryIdle")
def _carry_idle():
    keyposes = {}
    for f in range(1, 61):
        th = 2.0 * math.pi * (f - 1) / 60.0
        breath = math.sin(th)
        breath2 = math.sin(2.0 * th + 0.9)
        body = clips.pose(dx=0.006 * math.cos(th),
                          dz=0.009 * breath + 0.0025 * breath2,
                          rx=clips.SOLVED["carry"]["body_rx"] + 0.5 * breath, ry=1.1 * math.cos(th),
                          rz=0.6 * math.sin(th + math.pi / 3.0))
        # The hands hold the object volume, so they drift far less than the
        # body: the carry zone must stay stable under the code's attachment.
        arms = clips.arm_pair("carry",
                              extra_upper=(0.9 * breath, 0.6 * math.cos(th), 0.0),
                              extra_fore=(0.5 * breath, 0.0, 0.0))
        keyposes[f] = _merge({BODY: body}, clips.feet_planted(), arms)
    return _static_loop("SB_CarryIdle", 1, 60, keyposes, {
        "intent": "calme d'Idle, bras stabilisant la zone d'objet devant le torse",
        "carry_zone_blender_m": [0.0, -0.62, 0.86],
    })


@builder("SB_CarryWalk")
def _carry_walk():
    spec = clips.CARRY_WALK_BASE
    carry = clips.arm_pair("carry")
    result = _locomotion(spec, carry_arms=carry)
    result["declared"]["intent"] = (
        "phases et vitesse nominale identiques a SB_Walk, corps plus stable, "
        "zone portee coherente"
    )
    return result


@builder("SB_JumpTakeoff")
def _jump_takeoff():
    air = _airborne_pose(0.0)
    keyposes = {
        1: _merge({BODY: clips.pose(dz=-0.018, rx=6.0)}, clips.feet_planted(),
                  clips.arm_pair("release", blend=0.20,
                                 extra_upper=(12.0, -4.0, 0.0))),
        4: _merge({BODY: clips.pose(dz=-0.035, rx=12.0)}, clips.feet_planted(),
                  clips.arm_pair("release", blend=0.15,
                                 extra_upper=(35.0, -6.0, 0.0))),
        8: _merge({BODY: clips.pose(dz=0.110, rx=-1.0)},
                  clips.feet_tucked(0.12, 0.030, dy=0.10),
                  clips.arm_pair("release", blend=0.60,
                                 extra_upper=(-30.0, -15.0, 0.0))),
        9: _merge({BODY: clips.pose(dz=0.120, rx=-2.0)},
                  clips.feet_tucked(0.15, 0.045, dy=0.11),
                  clips.arm_pair("release", blend=0.62,
                                 extra_upper=(-28.0, -15.0, 0.0))),
        12: air,
    }
    air_feet = {k: v for k, v in air.items() if k in (FOOT_L, FOOT_R)}
    for f in range(1, 13):
        keyposes.setdefault(f, {})
        if f <= 4:
            keyposes[f][FOOT_L] = clips.pose()
            keyposes[f][FOOT_R] = clips.pose()
        else:
            # Smoothstep so the take-off starts with zero velocity and the sole
            # never dips below the floor on the way up.
            e = _smoothstep((f - 4) / 8.0)
            for bone in (FOOT_L, FOOT_R):
                keyposes[f][bone] = tuple(e * c for c in air_feet[bone])
    return _oneshot("SB_JumpTakeoff", 1, 12, keyposes, {
        "intent": "compression f4, extension f8-9, f12 identique a SB_Airborne f1",
        "handover_pose": "SB_Airborne frame 1",
    })


@builder("SB_Land")
def _land():
    keyposes = {
        # f1 is ALREADY grounded: gameplay fires this clip after contact, so a
        # rebound or an airborne first frame would replay a landing that the
        # simulation has already resolved.
        1: _merge({BODY: clips.pose(dz=0.050, rx=3.0)}, clips.feet_planted(),
                  clips.arm_pair("release", blend=0.36,
                                 extra_upper=(-3.0, -9.0, 0.0))),
        # An intermediate key here on purpose: with only f1 and f5 the arm had
        # to cover 41 deg in four frames and peaked at 17 deg in a single frame
        # while the median step over the clip was 1.1 deg, which reads as a snap
        # followed by a freeze rather than as a landing that settles.
        3: _merge({BODY: clips.pose(dz=-0.008, rx=9.0)}, clips.feet_planted(),
                  clips.arm_pair("release", blend=0.38,
                                 extra_upper=(-4.0, -8.0, 0.0))),
        # The arms stay low through the absorption instead of springing back to
        # neutral. Opening them from -21 to -7.5 deg across two frames was the
        # real source of the spike, not the entry pose that the first three
        # attempts kept softening: during a landing the body absorbs and the
        # arms follow, they do not lead.
        5: _merge({BODY: clips.pose(dz=-0.035, rx=14.0)}, clips.feet_planted(),
                  clips.arm_pair("release", blend=0.34,
                                 extra_upper=(0.0, -7.0, 0.0))),
        8: _merge({BODY: clips.pose(dz=-0.020, rx=8.0)}, clips.feet_planted(),
                  clips.arm_pair("release", blend=0.22, extra_upper=(2.0, -4.0, 0.0))),
        12: _merge({BODY: clips.pose(dz=0.0, rx=4.0)}, clips.feet_planted(),
                   clips.arm_pair("carry", blend=0.0)),
    }
    _pin_feet(keyposes, 1, 12)
    return _oneshot("SB_Land", 1, 12, keyposes, {
        "intent": "f1 deja au sol, compression max f5, f12 compatible Idle/Walk",
    })


@builder("SB_Pickup")
def _pickup():
    carry = clips.arm_pair("carry")
    keyposes = {
        1: _merge({BODY: clips.pose(rx=2.0)}, clips.feet_planted(),
                  clips.arm_pair("carry", blend=0.0)),
        8: _merge({BODY: clips.pose(dz=-0.012, rx=clips.SOLVED["grab"]["body_rx"])},
                  clips.feet_planted(),
                  clips.arm_pair("grab")),
        12: _merge({BODY: clips.pose(dz=-0.010, rx=clips.SOLVED["grab"]["body_rx"] - 2.0)},
                   clips.feet_planted(),
                   clips.arm_pair("grab", extra_upper=(0.0, 6.0, 0.0))),
        20: _merge({BODY: clips.pose(dz=-0.018, rx=9.0)}, clips.feet_planted(),
                   clips.arm_pair("carry", blend=0.80)),
        24: _merge({BODY: clips.pose(rx=clips.SOLVED["carry"]["body_rx"])}, clips.feet_planted(), carry),
    }
    _pin_feet(keyposes, 1, 24)
    return _oneshot("SB_Pickup", 1, 24, keyposes, {
        "intent": "lecture du sol, portee basse f8, prise visuelle f12, "
                  "f24 compatible SB_CarryIdle f1",
    })


@builder("SB_Throw")
def _throw():
    keyposes = {
        1: _merge({BODY: clips.pose(rx=clips.SOLVED["carry"]["body_rx"])}, clips.feet_planted(),
                  clips.arm_pair("carry")),
        6: _merge({BODY: clips.pose(dz=0.020, rx=-11.0)},
                  clips.feet_planted(),
                  clips.arm_pair("carry", extra_upper=(26.0, -20.0, 0.0),
                                 extra_fore=(14.0, 0.0, 0.0))),
        9: _merge({BODY: clips.pose(dz=0.014, rx=clips.SOLVED["reach"]["body_rx"] * 0.45)},
                  clips.feet_planted(),
                  clips.arm_pair("reach", blend=0.42,
                                 extra_upper=(0.0, -18.0, 0.0))),
        11: _merge({BODY: clips.pose(dz=0.010, rx=clips.SOLVED["reach"]["body_rx"] * 0.8)}, clips.feet_planted(),
                   clips.arm_pair("reach", blend=0.78,
                                  extra_upper=(0.0, -16.0, 0.0))),
        12: _merge({BODY: clips.pose(rx=clips.SOLVED["reach"]["body_rx"])}, clips.feet_planted(),
                   clips.arm_pair("reach")),
        14: _merge({BODY: clips.pose(dz=-0.010, rx=clips.SOLVED["reach"]["body_rx"] * 0.95)},
                   clips.feet_planted(),
                   clips.arm_pair("reach", blend=0.82,
                                  extra_upper=(8.0, -18.0, 0.0))),
        17: _merge({BODY: clips.pose(dz=-0.030, rx=clips.SOLVED["reach"]["body_rx"] * 0.85)},
                   clips.feet_planted(),
                   clips.arm_pair("reach", blend=0.55,
                                  extra_upper=(18.0, -20.0, 0.0))),
        24: _merge({BODY: clips.pose(rx=3.0)}, clips.feet_planted(),
                   clips.arm_pair("carry", blend=0.0)),
    }
    _pin_feet(keyposes, 1, 24)
    return _oneshot("SB_Throw", 1, 24, keyposes, {
        "intent": "arme f4-7, acceleration f8-11, release VISUEL f12, "
                  "suivi f13-17, f24 sans objet compatible Idle",
        "release_frame": 12,
        "note": "aucun projectile ni evenement gameplay n'est exporte",
    })


@builder("SB_Drop")
def _drop():
    keyposes = {
        1: _merge({BODY: clips.pose(rx=clips.SOLVED["carry"]["body_rx"])}, clips.feet_planted(),
                  clips.arm_pair("carry")),
        6: _merge({BODY: clips.pose(dz=-0.010, rx=4.0)}, clips.feet_planted(),
                  clips.arm_pair("carry", extra_upper=(4.0, -22.0, 0.0),
                                 extra_fore=(0.0, -6.0, 0.0))),
        9: _merge({BODY: clips.pose(dz=-0.015, rx=5.0)}, clips.feet_planted(),
                  clips.arm_pair("release", blend=0.85,
                                 extra_upper=(6.0, -18.0, 0.0))),
        18: _merge({BODY: clips.pose(rx=2.0)}, clips.feet_planted(),
                   clips.arm_pair("carry", blend=0.0)),
    }
    _pin_feet(keyposes, 1, 18)
    return _oneshot("SB_Drop", 1, 18, keyposes, {
        "intent": "ouverture des mains f6, release VISUEL f8-9, f18 compatible Idle",
        "release_frame": 9,
    })


@builder("SB_Deposit")
def _deposit():
    keyposes = {
        1: _merge({BODY: clips.pose(rx=clips.SOLVED["carry"]["body_rx"])}, clips.feet_planted(),
                  clips.arm_pair("carry")),
        10: _merge({BODY: clips.pose(dz=0.030, rx=-6.0)}, clips.feet_planted(),
                   clips.arm_pair("carry", extra_upper=(-14.0, -18.0, 0.0),
                                  extra_fore=(-6.0, 0.0, 0.0))),
        15: _merge({BODY: clips.pose(dz=0.010, rx=clips.SOLVED["reach"]["body_rx"] * 0.9)},
                   clips.feet_planted(),
                   clips.arm_pair("reach", blend=0.92,
                                  extra_upper=(0.0, -12.0, 0.0))),
        22: _merge({BODY: clips.pose(dz=-0.020, rx=8.0)}, clips.feet_planted(),
                   clips.arm_pair("release", blend=0.50,
                                  extra_upper=(10.0, -22.0, 0.0))),
        30: _merge({BODY: clips.pose(rx=2.0)}, clips.feet_planted(),
                   clips.arm_pair("carry", blend=0.0)),
    }
    _pin_feet(keyposes, 1, 30)
    return _oneshot("SB_Deposit", 1, 30, keyposes, {
        "intent": "presentation f1-10, extension vers la zone, release VISUEL f15, "
                  "retrait f22, f30 sans objet compatible Idle",
        "release_frame": 15,
    })
