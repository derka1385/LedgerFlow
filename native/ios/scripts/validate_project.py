"""Check project integrity and the portable URL policy without claiming an iOS build."""
import json
from pathlib import Path
import plistlib
import re
import struct
import subprocess
import tempfile
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
project = root / "LedgerFlow.xcodeproj"
def run(*args):
    return subprocess.run(args, check=True, text=True, capture_output=True).stdout

data = json.loads(run("plutil", "-convert", "json", "-o", "-", str(project / "project.pbxproj")))
objects = data["objects"]
assert data["rootObject"] in objects
def references(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if re.fullmatch(r"[A-F0-9]{24}", key): assert key in objects, key
            references(item)
    elif isinstance(value, list):
        for item in value: references(item)
    elif isinstance(value, str) and re.fullmatch(r"[A-F0-9]{24}", value):
        assert value in objects, value
references(objects)
files = []
def visit(identifier, parent):
    node = objects[identifier]
    if node["isa"] == "PBXGroup":
        base = parent / node.get("path", "")
        for child in node["children"]: visit(child, base)
    elif node["isa"] == "PBXFileReference" and node.get("sourceTree") != "BUILT_PRODUCTS_DIR":
        path = parent / node["path"]
        assert path.exists(), path
        files.append(path)
visit(objects[data["rootObject"]]["mainGroup"], root)
targets = [item for item in objects.values() if item["isa"] == "PBXNativeTarget"]
assert {item["name"] for item in targets} == {"LedgerFlow", "LedgerFlowTests"}
scheme = ET.parse(project / "xcshareddata/xcschemes/LedgerFlow.xcscheme")
for node in scheme.iter("BuildableReference"):
    assert node.attrib["BlueprintIdentifier"] in objects
assert scheme.find("TestAction/Testables/TestableReference") is not None
for configuration in ("Debug", "Release"):
    with (root / f"LedgerFlow/Info.{configuration}.plist").open("rb") as stream:
        info = plistlib.load(stream)
    assert info["NSCameraUsageDescription"]
    assert info["LedgerFlowOrigin"] == "$(LEDGERFLOW_ORIGIN)"
    if configuration == "Release": assert "NSAppTransportSecurity" not in info
    else: assert info["NSAppTransportSecurity"] == {"NSAllowsLocalNetworking": True}

catalog = root / "LedgerFlow/Assets.xcassets"
images = 0
for manifest in catalog.rglob("Contents.json"):
    contents = json.loads(manifest.read_text())
    for image in contents.get("images", []):
        filename = manifest.parent / image["filename"]
        if filename.suffix == ".svg":
            assert ET.parse(filename).getroot().tag.endswith("}svg")
            continue
        header = filename.read_bytes()[:24]
        assert header[:8] == b"\x89PNG\r\n\x1a\n"
        dimensions = struct.unpack(">II", header[16:24])
        size = float(image.get("size", "48x48").split("x")[0])
        scale = int(image["scale"].removesuffix("x"))
        assert dimensions == (int(size * scale),) * 2
        images += 1
assert images == 21

sources = sorted((root / "LedgerFlow").glob("*.swift"))
tests = root / "LedgerFlowTests/WorkspaceEndpointTests.swift"
run("swiftc", "-frontend", "-parse", *map(str, [*sources, root.parent / "shared/WorkspaceTrust.swift", tests]))
with tempfile.TemporaryDirectory(prefix="ledgerflow-ios-check-") as directory:
    output = str(Path(directory) / "endpoint-check")
    run("swiftc", "-swift-version", "6", "-parse-as-library", "-module-cache-path", "/tmp/ledgerflow-swift-module-cache", str(root / "LedgerFlow/WorkspaceEndpoint.swift"), str(root / "LedgerFlow/WorkspaceAssociation.swift"), str(root / "scripts/check_endpoint.swift"), "-o", output)
    print(run(output).strip())
print(f"Project references valid: {len(objects)} objects, {len(files)} source/resource references, {images} icon slots.")
print("Swift syntax and plist/asset structure passed. UIKit/WebKit typechecking, signing and simulator execution were NOT performed.")
