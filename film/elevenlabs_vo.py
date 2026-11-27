"""ElevenLabs voiceover for the LedgerFlow film.

Key: ELEVENLABS_API_KEY in the environment or in the git-ignored ~/Coding/vultr/.env. It is never printed.
Optional: ELEVENLABS_VOICE_ID (default George), ELEVENLABS_MODEL (default eleven_multilingual_v2).

  python3 film/elevenlabs_vo.py --list-voices     # names and ids of the voices on your account
  python3 film/elevenlabs_vo.py                   # writes film/audio/s01.mp3 ... s16.mp3 from vo_script.json
  python3 film/elevenlabs_vo.py --only s10        # regenerate one scene
"""
import json, os, pathlib, subprocess, sys, urllib.error, urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ENV = HERE.parent / ".env"
DEFAULT_VOICE = "JBFqnCBsd6RMkjVDRZzb"  # "George", ElevenLabs premade voice: calm British narrator


def setting(name, default=None):
    if os.environ.get(name):
        return os.environ[name].strip()
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            k, _, v = line.partition("=")
            if k.strip() == name and v.strip():
                return v.strip().strip('"').strip("'")
    return default


def call(path, body=None):
    key = setting("ELEVENLABS_API_KEY")
    if not key:
        sys.exit("ELEVENLABS_API_KEY is missing: add it to ~/Coding/vultr/.env (never paste it in a chat).")
    req = urllib.request.Request("https://api.elevenlabs.io" + path, method="POST" if body else "GET",
                                 data=json.dumps(body).encode() if body else None,
                                 headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()
    except urllib.error.HTTPError as e:  # show the API's reason, never the key
        sys.exit(f"ElevenLabs {e.code}: {e.read()[:300].decode('utf-8', 'replace')}")


def main():
    if "--list-voices" in sys.argv:
        for v in json.loads(call("/v1/voices"))["voices"]:
            print(f"{v['voice_id']}  {v['name']:<24} {v.get('labels', {}).get('accent', '')} {v.get('labels', {}).get('description', '')}")
        return
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    voice = setting("ELEVENLABS_VOICE_ID", DEFAULT_VOICE)
    model = setting("ELEVENLABS_MODEL", "eleven_multilingual_v2")
    script = json.loads((HERE / "vo_script.json").read_text())
    (HERE / "audio").mkdir(exist_ok=True)
    for i, (sid, text) in enumerate(script):
        if only and sid != only:
            continue
        body = {"text": text, "model_id": model,
                "voice_settings": {"stability": 0.55, "similarity_boost": 0.8, "style": 0.15, "use_speaker_boost": True},
                # neighbouring lines keep the delivery continuous from scene to scene
                "previous_text": script[i - 1][1] if i else None,
                "next_text": script[i + 1][1] if i + 1 < len(script) else None}
        out = HERE / "audio" / f"{sid}.mp3"
        out.write_bytes(call(f"/v1/text-to-speech/{voice}?output_format=mp3_44100_128", body))
        d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                           capture_output=True, text=True).stdout.strip()
        print(f"{sid}  {float(d):5.1f} s  -> {out.name}")


if __name__ == "__main__":
    main()
