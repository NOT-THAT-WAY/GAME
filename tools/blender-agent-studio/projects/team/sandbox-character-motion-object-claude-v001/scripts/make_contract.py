"""Emit the per-clip measurement contract consumed by `measure_clip.py`.

Stance and swing windows are DERIVED from the same declared numbers that drove
authoring (contact frame, duty factor, cycle length), not eyeballed from the
result. A window that disagreed with the authored motion would make the drift
measurement meaningless, so both come from one source.

A stance that crosses the loop boundary is emitted as two windows rather than
one. Inside a single clip pass the reconstructed world advances by v_nom * T
across the seam, so a window spanning it would report that legitimate cycle
advance as drift.
"""
from __future__ import annotations

import json
import pathlib
import sys

SCRIPTS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import clips  # noqa: E402


def locomotion_contract(spec) -> dict:
    f0, f1 = spec["f_start"], spec["f_end"]
    n = f1 - f0 + 1
    stance = round(n * spec["duty"])

    def windows(contact):
        start = contact
        end = contact + stance
        out = []
        if end <= f1:
            out.append({"start": start, "end": end})
        else:
            out.append({"start": start, "end": f1})
            out.append({"start": f0, "end": end - n})
        return out

    def swing(contact):
        """Swing window, wrapped like the stance one.

        Emitting only the in-range head of the window was wrong: with the sprint
        duty of 0.35 the right foot swings from frame 21 through frame 13 of the
        next cycle, and its apex at frame 7 sat entirely outside the emitted
        window, so the clearance gate would have measured a phase that contains
        no apex and passed on nothing.
        """
        start = contact + stance
        # The window stops one frame BEFORE the next contact: on the contact
        # frame itself the foot is planted, and including it produced a
        # degenerate one-frame window whose "peak clearance" was 0 by
        # definition, failing the gate on a frame that is not a swing at all.
        end = contact + n - 1
        if start > f1:
            start -= n
            end -= n
        if end <= f1:
            return [{"start": start, "end": end}]
        return [{"start": start, "end": f1}, {"start": f0, "end": end - n}]

    return {
        "clip": spec["name"],
        "f_start": f0,
        "f_end": f1,
        "loop": spec["periodic"],
        "nominal_speed_mps": spec["speed"],
        "stance_windows": {"L": windows(spec["contact_l"]),
                           "R": windows(spec["contact_r"])},
        "swing_windows": {"L": swing(spec["contact_l"]),
                          "R": swing(spec["contact_r"])},
    }


def static_contract(name, f0, f1, loop, stance=None, swing=None) -> dict:
    """Contract for a clip with no ground travel (v_nom = 0)."""
    return {
        "clip": name,
        "f_start": f0,
        "f_end": f1,
        "loop": loop,
        "nominal_speed_mps": 0.0,
        "stance_windows": stance or {},
        "swing_windows": swing or {},
    }


def _both(f0, f1):
    return {"L": [{"start": f0, "end": f1}], "R": [{"start": f0, "end": f1}]}


CONTRACTS = {
    "SB_Walk": lambda: locomotion_contract(clips.WALK),
    "SB_Sprint": lambda: locomotion_contract(clips.SPRINT),
    "SB_CarryWalk": lambda: locomotion_contract(clips.CARRY_WALK_BASE),

    # Feet never touch the ground: no stance window to check, but the whole
    # range is a swing window so a foot dropping through the floor is caught.
    "SB_Airborne": lambda: static_contract(
        "SB_Airborne", 1, 24, True, swing=_both(1, 24)),

    # Feet planted for the entire clip. v_nom = 0, so the reconstructed world IS
    # the local frame and any foot movement is reported directly as drift.
    "SB_CarryIdle": lambda: static_contract(
        "SB_CarryIdle", 1, 60, True, stance=_both(1, 60)),
    "SB_Land": lambda: static_contract(
        "SB_Land", 1, 12, False, stance=_both(1, 12)),
    "SB_Pickup": lambda: static_contract(
        "SB_Pickup", 1, 24, False, stance=_both(1, 24)),
    "SB_Throw": lambda: static_contract(
        "SB_Throw", 1, 24, False, stance=_both(1, 24)),
    "SB_Drop": lambda: static_contract(
        "SB_Drop", 1, 18, False, stance=_both(1, 18)),
    "SB_Deposit": lambda: static_contract(
        "SB_Deposit", 1, 30, False, stance=_both(1, 30)),

    # Planted through the compression, airborne from frame 9 on.
    "SB_JumpTakeoff": lambda: static_contract(
        "SB_JumpTakeoff", 1, 12, False,
        stance=_both(1, 4), swing=_both(9, 12)),
}


if __name__ == "__main__":
    name, out = sys.argv[1], sys.argv[2]
    contract = CONTRACTS[name]()
    pathlib.Path(out).write_text(json.dumps(contract, indent=1))
    print(json.dumps(contract, indent=1))
