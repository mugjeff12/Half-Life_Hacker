"""Dev tool: build the app's logo, icons and (downsized) MNR photos from the originals.

    python tools/make_assets.py path/to/folder_with_originals
"""
import sys, pathlib
from PIL import Image

src = pathlib.Path(sys.argv[1])
dst = pathlib.Path(__file__).resolve().parent.parent / "assets"
(dst / "img").mkdir(parents=True, exist_ok=True)

logo = Image.open(src / "NAYGN_logo.png").convert("RGBA")
logo.resize((512, 512), Image.LANCZOS).save(dst / "naygn_logo.png", optimize=True)
logo.resize((1024, 1024), Image.LANCZOS).save(dst / "naygn.icns")
logo.resize((256, 256), Image.LANCZOS).save(
    dst / "naygn.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

photos = {"MNR_people.jpg": "people", "MNR_sign.jpg": "sign", "MNR.jpeg": "building",
          "MNR_core.jpg": "core", "MNR_core_2.jpeg": "core2"}
for name, key in photos.items():
    im = Image.open(src / name).convert("RGB")
    if im.width > 1400:
        im = im.resize((1400, round(im.height * 1400 / im.width)), Image.LANCZOS)
    im.save(dst / "img" / f"{key}.jpg", quality=82, optimize=True)
print("assets written to", dst)
