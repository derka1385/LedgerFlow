"""Render the iOS receipt icon from the same geometry as ReceiptGlyph. Requires Pillow."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1] / "LedgerFlow" / "Assets.xcassets"

def contents(folder, **values):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "Contents.json").write_text(json.dumps({**values, "info": {"author": "xcode", "version": 1}}, indent=2) + "\n")

contents(root)
image = Image.new("RGB", (1024, 1024), "#103D30")
draw = ImageDraw.Draw(image)
def point(x, y):
    return (int(190 + x * 6.44), int(160 + y * 6.44))

sheet = [(13, 5), (69, 5), (87, 23), (87, 101), (75, 93), (63, 101),
         (51, 93), (39, 101), (27, 93), (13, 101)]
draw.polygon([point(x + 1, y + 2) for x, y in sheet], fill="#0A2A22")
draw.polygon([point(x, y) for x, y in sheet], fill="#F0F3DF")
draw.polygon([point(69, 5), point(69, 23), point(87, 23)], fill="#90B591")
def stroke(points, width, fill):
    draw.line([point(x, y) for x, y in points], width=int(width * 6.44), fill=fill, joint="curve")

stroke([(25, 25), (51, 25)], 4, "#103D30")
stroke([(25, 37), (58, 37)], 2, "#81998B")
for y in (51, 62, 73):
    stroke([(25, y), (74, y)], 1, "#A5BAA8")
stroke([(49, 48), (49, 75)], 1, "#A5BAA8")
stroke([(55, 83), (61, 88), (73, 77)], 3, "#103D30")

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
