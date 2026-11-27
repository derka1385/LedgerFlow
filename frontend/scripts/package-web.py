"""Package only the built public client; never includes .env, server data or keys."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parents[2]
dist = root / "frontend" / "dist"
if not (dist / "index.html").exists():
    raise SystemExit("Run npm --prefix frontend run build first.")
out = root / "artifacts" / "apple-platform" / "LedgerFlow-web-client.zip"
out.parent.mkdir(parents=True, exist_ok=True)
with ZipFile(out, "w", ZIP_DEFLATED) as archive:
    for file in sorted(dist.rglob("*")):
        if file.is_file():
            archive.write(file, file.relative_to(dist))
print(out)
