"""Render the existing code-native receipt mark; requires Pillow. No generated artwork."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1] / "LedgerFlow" / "Assets.xcassets"

def contents(folder, **values):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "Contents.json").write_text(json.dumps({**values, "info": {"author": "xcode", "version": 1}}, indent=2) + "\n")

contents(root)
green, paper = "#0F5C4A", "#F6F4EE"
image = Image.open(Path(__file__).resolve().parents[3] / "frontend/public/icons/app-icon-1024.png").convert("RGB")

icons = []
for idiom, size, scales in [("iphone",20,[2,3]),("iphone",29,[2,3]),("iphone",40,[2,3]),("iphone",60,[2,3]),("ipad",20,[1,2]),("ipad",29,[1,2]),("ipad",40,[1,2]),("ipad",76,[1,2]),("ipad",83.5,[2]),("ios-marketing",1024,[1])]:
    for scale in scales:
        pixels = int(size * scale)
        filename = f"icon-{pixels}.png"
        folder = root / "AppIcon.appiconset"
        folder.mkdir(parents=True, exist_ok=True)
        image.resize((pixels,pixels), Image.Resampling.LANCZOS).save(folder / filename)
        icons.append({"idiom":idiom,"size":f"{size}x{size}","scale":f"{scale}x","filename":filename})
contents(root / "AppIcon.appiconset", images=icons)
marks = []
for scale in (1,2,3):
    folder = root / "ReceiptMark.imageset"
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"receipt-{scale}x.png"
    image.resize((48*scale,48*scale), Image.Resampling.LANCZOS).save(folder / filename)
    marks.append({"idiom":"universal","scale":f"{scale}x","filename":filename})
contents(root / "ReceiptMark.imageset", images=marks)

def color(hex_value):
    return {"color-space":"srgb","components":{**{name:f"0x{hex_value[index:index+2]}" for name,index in [("red",0),("green",2),("blue",4)]},"alpha":"1.000"}}
for name, light, dark in [("BrandAccent","0F5C4A","8DD1BA"),("LaunchBackground","F6F4EE","151919")]:
    contents(root / f"{name}.colorset", colors=[{"idiom":"universal","color":color(light)},{"idiom":"universal","appearances":[{"appearance":"luminosity","value":"dark"}],"color":color(dark)}])
print(root)
