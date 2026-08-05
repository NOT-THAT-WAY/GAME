#!/usr/bin/env python3
"""blender-choreography — générateur de STORYBOARD Nano-Banana Pro (/edit).

Chaque panel = un BEAT de chorégraphie : une pose caméra explicite autour du device
canonique. Claude interprète ensuite chaque panel en pose caméra Blender exacte
(azimut / élévation / distance / focale) → keyframes. Cf. WORKFLOW.md étapes 1-2.

Doctrine anti-drift (audits_blender/pulsed-asset-prompts-v2.md) : l'identité est
portée par l'image de référence attachée, le prompt ne décrit QUE le cadrage demandé.

NO-OVERWRITE : refs/storyboards/<board>-<date>/ uniquement.
Usage:  python3 gen_storyboard.py sb-001          # génère le board complet
        python3 gen_storyboard.py sb-001 p2       # un seul panel
"""
import json, sys, time, base64, subprocess, tempfile, pathlib, urllib.request, urllib.error

HERE  = pathlib.Path(__file__).resolve().parent             # tools/
LANE  = HERE.parent                                         # blender-choreography/
ROOT  = LANE.parent                                         # unrecorded-marketing/
ENV   = ROOT / "_pipeline" / "llm_proxy" / ".env"
CANON = LANE / "refs" / "01_canonical_front.png"
PRICE, RES, ASPECT = 0.15, "2K", "9:16"

KEEP = (
  "Keep EXACTLY the same device as the attached reference — same shape, same translucent "
  "amethyst-purple satin-matte shell, same internal purple PCB visible through it, same "
  "frosted-white controls in the same positions, same embossed markings, dark screen kept OFF. "
  "Do not move, add or restyle any control. ")

STYLE = (
  "Cinematic product-film still, dark studio void, near-black background, soft volumetric haze, "
  "one cool rim light grazing the translucent edges, satin matte finish (no wet gloss). "
  "Photoreal. NOT a Game Boy, NOT a games console. ")

BOARDS = {
  # sb-001 "crane macro→hero" : réveil macro → hero 3/4 → plongée zénithale → repos frontal
  "sb-001": {
    "p1": dict(seed=6101, save="panel_01_macro-low.png",
      cam="CAMERA: extreme close-up from a very LOW angle near the device's bottom edge, "
          "looking UP across the faceplate — strong foreshortening, only the lower half of "
          "the device visible, the horizontal slider and D-pad huge in the foreground, the "
          "dark screen receding above."),
    "p2": dict(seed=6102, save="panel_02_hero-3q-low.png",
      cam="CAMERA: low three-quarter LEFT hero angle, the whole device standing and filling "
          "the frame, seen slightly from below so it feels monumental, its left edge toward "
          "the viewer catching the rim light."),
    "p3": dict(seed=6103, save="panel_03_overhead.png",
      cam="CAMERA: high overhead angle, plunging view from above the device tilted about 55 "
          "degrees down — the faceplate reads almost flat like a map, screen centered, "
          "controls laid out geometrically."),
    "p4": dict(seed=6104, save="panel_04_hero-rest.png",
      cam="CAMERA: frontal, level with the device center, the whole device small and centered "
          "with generous margins all around — calm rest pose, perfectly symmetrical framing."),
  },
}

def fal_key():
    for line in ENV.read_text().splitlines():
        if line.startswith("FAL_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("FAL_KEY not found in " + str(ENV))

def to_data_uri(path):
    src = pathlib.Path(path)
    tmp = pathlib.Path(tempfile.gettempdir()) / (src.stem + "_cap.jpg")
    subprocess.run(["sips", "-s", "format", "jpeg", "-Z", "2000", str(src), "--out", str(tmp)],
                   check=True, capture_output=True)
    return "data:image/jpeg;base64," + base64.b64encode(tmp.read_bytes()).decode()

def call_fal(slug, payload, key):
    req = urllib.request.Request("https://fal.run/" + slug, data=json.dumps(payload).encode(),
                                 headers={"Authorization": "Key " + key,
                                          "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode())

def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=180) as r:
        dest.write_bytes(r.read())

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in BOARDS:
        sys.exit("usage: gen_storyboard.py <" + "|".join(BOARDS) + "> [panel]")
    board = sys.argv[1]
    panels = BOARDS[board]
    order = [sys.argv[2]] if len(sys.argv) > 2 else list(panels)
    out = LANE / "refs" / "storyboards" / (board + "-" + time.strftime("%Y-%m-%d"))
    key = fal_key()
    out.mkdir(parents=True, exist_ok=True)
    uri, spent = to_data_uri(CANON), 0.0
    for i, k in enumerate(order, 1):
        s = panels[k]
        prompt = KEEP + STYLE + s["cam"]
        payload = {"prompt": prompt, "image_urls": [uri], "aspect_ratio": ASPECT,
                   "resolution": RES, "num_images": 1, "seed": s["seed"], "output_format": "png"}
        t0 = time.time()
        print("[%d/%d] %s seed=%d ..." % (i, len(order), k, s["seed"]), flush=True)
        try:
            res = call_fal("fal-ai/nano-banana-pro/edit", payload, key)
            url = res["images"][0]["url"]
            download(url, out / s["save"])
            spent += PRICE
            with (out / "_run.jsonl").open("a") as f:
                f.write(json.dumps(dict(k=k, seed=s["seed"], url=url, saved=s["save"],
                        prompt=prompt, secs=round(time.time() - t0, 1),
                        cum=round(spent, 2))) + "\n")
            print("      OK %.1fs -> %s  (run $%.2f)" % (time.time() - t0, s["save"], spent), flush=True)
        except urllib.error.HTTPError as e:
            print("      FAIL HTTP %d: %s" % (e.code, e.read().decode()[:500]), flush=True); break
        except Exception as e:
            print("      FAIL %s: %s" % (type(e).__name__, e), flush=True); break
    print("\nDONE. run $%.2f. board: %s" % (spent, out.relative_to(ROOT)))

if __name__ == "__main__":
    main()
