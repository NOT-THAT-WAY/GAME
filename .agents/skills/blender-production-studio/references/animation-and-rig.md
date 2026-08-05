# Rig and animation

Audit mesh topology, hierarchy, bind pose, rest axes, pivots and scale before rigging. Declare joint
limits, mechanical exclusions, deformation expectations, influence limits and export skeleton.
Test extreme and intermediate poses on evaluated meshes.

For every clip, declare fps, inclusive frame range, action/strip ownership, loop policy, root motion,
events, bake and sampling. Measure contacts across all relevant frames; never infer foot or hand
contact from a control bone alone. Validate the loop seam in pose, velocity and root trajectory.

Deliver skeleton and weights audits, clip manifest, full playblast/probe, baked export and clip
reimport. Test in the target engine when the animation is for gameplay.
