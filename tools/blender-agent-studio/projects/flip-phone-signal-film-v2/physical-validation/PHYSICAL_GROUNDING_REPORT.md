# Physical grounding report — DRUMBOII Flip Phone

## Failure history

1. `-92°` folded the screen away from the user.
2. `+92°` selected the right side but stopped at a horizontal half-close.
3. `+180°` applied the theoretical clamshell travel but crossed the keypad geometry.
4. A static sweep at `0, 60, 90, 120, 140, 155, 170, 180°` established the mesh-specific limit.
5. `+140°` is the last clean closed configuration: exterior shell forward, keypad covered, no re-emergence behind the base.

## Final articulation

- joint: revolute;
- moving link: `LS2_Hinge` and descendants;
- fixed base: `LS2_Phone`;
- local axis: X;
- open reference: 93.3848° absolute Euler X;
- legal delta: 0–140°;
- closed: +140°;
- open: +0°;
- main action: monotonically decreasing from frame 310 to 350.

## Validation

The Blender contract validator reports 22/22 checks passing. It covers semantic fields, five joint states,
joint limits, monotonic opening, phone/carrier contact, carrier/rail clearance, crossing above the dais and
landed contact on the dais.

Visual evidence:

- `angle-sweep-static/contact-sheet-front.jpg`: all candidate limits;
- `gates-clamshell-final/contact-sheet.jpg`: final state sequence;
- `final-hinge-sequence-140deg.jpg`: encoded film sequence.

## General lesson

Physics alone cannot infer the correct sign or stopping angle. The accepted state must satisfy all of:

```text
one valid revolute joint
+ positive collision clearance
+ exterior shell visible when closed
+ keypad covered when closed
+ screen and keypad usable when open
```

