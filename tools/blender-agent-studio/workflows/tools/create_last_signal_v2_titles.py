#!/usr/bin/env python3
"""Create deterministic transparent title cards for LAST SIGNAL V2."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders" / "last-signal-film-v2-final" / "titles"
OUT.mkdir(parents=True, exist_ok=True)
FONT = "/System/Library/Fonts/SFNS.ttf"
MONO = "/System/Library/Fonts/SFNSMono.ttf"


def canvas():
    return Image.new("RGBA", (960, 540), (0, 0, 0, 0))


def save_opening():
    im = canvas(); d = ImageDraw.Draw(im)
    d.text((58, 42), "LAST SIGNAL", font=ImageFont.truetype(FONT, 46), fill=(245, 246, 242, 242))
    d.text((61, 101), "ONE LAST MESSAGE", font=ImageFont.truetype(FONT, 18), fill=(84, 226, 196, 235))
    im.save(OUT / "opening.png")


def save_message():
    im = canvas(); d = ImageDraw.Draw(im)
    d.text((58, 428), "INCOMING SIGNAL", font=ImageFont.truetype(MONO, 17), fill=(255, 138, 76, 242))
    d.text((58, 451), "HELLO", font=ImageFont.truetype(FONT, 31), fill=(248, 248, 242, 246))
    im.save(OUT / "message.png")


def save_ending():
    im = canvas(); d = ImageDraw.Draw(im)
    d.text((58, 42), "CONNECTION RESTORED", font=ImageFont.truetype(FONT, 32), fill=(245, 246, 242, 242))
    im.save(OUT / "ending.png")


save_opening(); save_message(); save_ending()
print(OUT)
