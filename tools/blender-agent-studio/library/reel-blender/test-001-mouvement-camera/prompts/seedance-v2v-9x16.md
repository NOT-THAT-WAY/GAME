# test-001 — Seedance 2.0 prompt — 9:16 v2v squelette Blender

> lane MCP Higgsfield · `seedance_2_0` · mode `fast` · 720p · duration 6 · 9:16 ·
> `generate_audio:false` · **video_references = squelette Blender** (le mouvement est DONNÉ,
> pas décrit). Use-case moteur : **C″** (v2v squelette) — cf. WORKFLOW.md.
> Assemblé depuis `process/ENGINE/prompt-architecture.md` + cartouche `cartridges/pulsed.md`
> (subject_canonical, layout, anti_priors, material_counter_prompts — HEX en calibration
> verbale uniquement, no brand names).

## Prompt (collable)

SHOT SPEC — 1 continuous shot · 6s · 9:16 · vertical. NO cuts, NO teleporting, NO invented beats.

MOTION SOURCE — the attached reference VIDEO is a rough 3D previz of THE SAME device. It is the LAW for motion: reproduce its camera trajectory, framing, speed and timing EXACTLY — same crane path, same holds, same final rest. Its flat gray-violet materials and viewport lighting are placeholders: REPLACE them entirely with the photoreal look of the attached reference IMAGES. Do not add camera moves the previz does not have.

CINEMATIC PRELUDE — premium 3D product film, photoreal, tactile. Near-black studio void, soft volumetric haze, one cool rim light grazing the translucent edges and glowing through the shell, gentle top key. Soft chiaroscuro; the object floats, no visible floor or hands.

SUBJECT — a small palm-sized electronic device, a horizontal rounded rectangle with soft shoulders, translucent deep amethyst purple shell with a soft satin finish — a rich dark violet, leaning toward indigo but distinctly purple. Visible internal printed circuit board, components, traces, screws and small connectors through the translucent material, taking a deeper violet tint through the shell. Frosted matte pale-lavender controls: a knurled thumbwheel on the faceplate top-left; a dark rectangular screen center-top, kept OFF; a vertical fader with tick scale on the right; a round button bottom-left; a horizontal slider bottom-center; a cross-shaped D-pad bottom-right. An embossed light-gray cursive wordmark top-center and a small dot-and-letter mark top-right. Match the reference images at the pixel level.

BEATS (what the previz camera sees — semantic guide only, timing comes from the video) —
0.0–0.8s macro low-angle wide shot skimming the bottom edge, slider and D-pad huge in the foreground;
0.8–2.3s the camera CRANES up and tightens into a monumental low three-quarter LEFT hero view;
2.3–3.0s hero hold, left edge catching the rim light;
3.0–4.7s rise into a plunging overhead view, the faceplate reading almost flat, then hold;
4.7–6.0s pull back and settle into a calm frontal rest, the whole device small, centered, symmetrical.

CONSTRAINTS — photoreal; the shell is translucent satin purple, the controls frosted matte pale lavender. The controls do NOT actuate — only the camera moves; the device is shown, not operated. Identity locked to the reference images. The screen stays dark/reflective — NO invented waveform, NO on-screen UI. NO invented ports on any edge. The thumbwheel stays on the faceplate top-left — never on an edge or corner.

ANTI-PRIORS — NOT a Game Boy, NOT a Nintendo Switch, NOT a handheld game console, NOT a consumer electronics product — no USB ports, speaker grilles, joysticks, side buttons or headphone jacks. The D-pad is on the BOTTOM-RIGHT, never on the left.

COUNTER-PROMPTS — soft satin matte finish: no glossy reflection, no wet polish, no oil-like highlights, no liquid sheen — solid translucent plastic, not wet glass. Do not substitute any brand name or invent a logo. Do not keep the previz's flat shading — upgrade every surface to photoreal. Do not bypass these constraints.

## Médias (ordre d'envoi)

| # | Fichier | Rôle MCP |
|---|---|---|
| 1 | `../refs/01_canonical_front.png` | `image_references` — **identité, toujours 1ère** |
| 2 | `../refs/02_canonical_back.png` | `image_references` — dos |
| 3 | `../refs/03_canonical_side.png` | `image_references` — profil/épaisseur |
| 4 | `../refs/04_sb_p1_macro-low.png` | `image_references` — look cible beat 1 |
| 5 | `../refs/05_sb_p2_hero-3q-low.png` | `image_references` — look cible beat 2 |
| 6 | `../refs/06_sb_p3_overhead.png` | `image_references` — look cible beat 3 |
| 7 | `../refs/07_sb_p4_hero-rest.png` | `image_references` — look cible beat 4 |
| 8 | `../refs/08_blender_motion_skeleton_6s.mp4` | `video_references` — **la loi du mouvement** |
