"""Measurement contracts for the 7 force / combat / life-state clips.

Windows are derived from the same phase model that drove authoring, never
eyeballed from the result: a window that disagreed with the motion would make
the drift and clearance numbers meaningless.
"""
from __future__ import annotations

import json
import pathlib
import sys


def static(name, f0, f1, loop, stance=None, swing=None, note=None):
    return {"clip": name, "f_start": f0, "f_end": f1, "loop": loop,
            "nominal_speed_mps": 0.0,
            "stance_windows": stance or {}, "swing_windows": swing or {},
            "note": note or ""}


def both(f0, f1):
    return {"L": [{"start": f0, "end": f1}], "R": [{"start": f0, "end": f1}]}


CONTRACTS = {
    # Feet planted for the whole clip; v_nom = 0 so the reconstructed world is
    # the local frame and any foot movement is reported directly as drift.
    "SB_Punch": lambda: static("SB_Punch", 1, 20, False, stance=both(1, 20)),
    "SB_HitReact": lambda: static("SB_HitReact", 1, 18, False, stance=both(1, 18)),
    "SB_Push": lambda: static("SB_Push", 1, 30, True, stance=both(1, 30),
                              note="appuis plantes larges, offset constant de 0.12 m"),

    # Alternating catch-up steps: the left foot hops over frames 2-12 and the
    # right over 14-24, each landing back on the spot it left.
    "SB_WallPushed": lambda: static(
        "SB_WallPushed", 1, 24, True,
        stance={"L": [{"start": 13, "end": 24}], "R": [{"start": 1, "end": 13}]},
        swing={"L": [{"start": 2, "end": 12}], "R": [{"start": 14, "end": 24}]}),

    # The feet never touch the ground in the KO states: the BODY is the support,
    # and the ground gate covers it because penetration is measured across every
    # mesh, not just the feet.
    "SB_KnockedOutLoop": lambda: static(
        "SB_KnockedOutLoop", 1, 60, True, swing=both(1, 60),
        note="support reel = volume du corps au sol, pas les pieds"),
    "SB_Knockout": lambda: static(
        "SB_Knockout", 1, 30, False,
        stance=both(1, 4), swing={"L": [{"start": 14, "end": 30}],
                                  "R": [{"start": 14, "end": 30}]}),
    "SB_Recover": lambda: static(
        "SB_Recover", 1, 36, False,
        stance=both(30, 36), swing={"L": [{"start": 1, "end": 20}],
                                    "R": [{"start": 1, "end": 20}]}),
}


if __name__ == "__main__":
    name, out = sys.argv[1], sys.argv[2]
    pathlib.Path(out).write_text(json.dumps(CONTRACTS[name](), indent=1))
    print(json.dumps(CONTRACTS[name](), indent=1))
