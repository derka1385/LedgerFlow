"""Build the Mac app with an automatic local runtime, or configure a remote HTTPS origin."""
import argparse
from pathlib import Path
import plistlib
import platform
import subprocess
from urllib.parse import urlsplit

parser = argparse.ArgumentParser()
parser.add_argument("--url", help="Optional remote HTTPS origin. Omit to start the local runtime automatically.")
parser.add_argument("--allow-localhost", action="store_true", help="Permit HTTP loopback for local development only")
args = parser.parse_args()
url = urlsplit(args.url or "")
local = url.scheme == "http" and url.hostname in {"127.0.0.1", "localhost", "::1"}
if args.url and ((url.scheme != "https" and not (args.allow_localhost and local)) or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}):
    parser.error("Use an HTTPS origin without credentials, path, query or fragment. HTTP loopback requires --allow-localhost.")
here = Path(__file__).resolve().parent
app = here / "build" / "LedgerFlow.app"
macos = app / "Contents" / "MacOS"
resources = app / "Contents" / "Resources"
macos.mkdir(parents=True, exist_ok=True)
resources.mkdir(parents=True, exist_ok=True)
info = {
    "CFBundleName": "LedgerFlow", "CFBundleDisplayName": "LedgerFlow", "CFBundleIdentifier": "app.ledgerflow.workspace",
    "CFBundleExecutable": "LedgerFlow", "CFBundlePackageType": "APPL", "CFBundleShortVersionString": "0.2.0", "CFBundleVersion": "2",
    "LSMinimumSystemVersion": "13.0", "NSHighResolutionCapable": True, "LedgerFlowRepository":str(here.parents[1]),
    "NSLocalNetworkUsageDescription":"Associer votre iPhone à LedgerFlow et synchroniser les pièces avec ce Mac.",
}
if args.url:
    info["LedgerFlowOrigin"] = args.url.rstrip("/") + "/"
icon_source = here.parents[1] / "frontend" / "public" / "icons" / "mac-icon-1024.png"
if not icon_source.exists():
    icon_source = here.parents[1] / "frontend" / "public" / "icons" / "icon-512.png"
if icon_source.exists():
    subprocess.run([str(here.parents[1]/".venv/bin/python"), "-c", "from PIL import Image; import sys; Image.open(sys.argv[1]).save(sys.argv[2], format='ICNS')", str(icon_source), str(resources/"LedgerFlow.icns")],check=True)
    info["CFBundleIconFile"] = "LedgerFlow.icns"
if local:
    info["NSAppTransportSecurity"] = {"NSAllowsLocalNetworking": True}
with (app / "Contents" / "Info.plist").open("wb") as f:
    plistlib.dump(info, f)
subprocess.run(["swiftc", "-swift-version", "6", "-target", f"{platform.machine()}-apple-macos13.0", "-parse-as-library", "-module-cache-path", "/tmp/ledgerflow-swift-module-cache", "-framework", "AppKit", "-framework", "WebKit", str(here / "LedgerFlow.swift"), str(here.parent / "shared/WorkspaceTrust.swift"), "-o", str(macos / "LedgerFlow")], check=True)
subprocess.run(["codesign", "--force", "--sign", "-", "--timestamp=none", str(app)], check=True)
print(f"Built {app}\nLocal ad-hoc signature only; not notarized or App Store signed.")
