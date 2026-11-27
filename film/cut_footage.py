"""Cut the real recordings on motion: frozen stretches (ffmpeg freezedetect) shrink to a short beat, the rest plays near real time."""
import subprocess, sys
SRC = {"mac": "/Users/petrinolann/Desktop/Screen Recording 2026-11-27 at 19.27.54.mov",
       "p1": "/Users/petrinolann/Downloads/ScreenRecording_11-27-2026 19-29-15_1.MP4",
       "p2": "/Users/petrinolann/Downloads/ScreenRecording_11-27-2026 19-32-51_1.MP4"}
FREEZE = {"mac": "0-1.76 1.76-3.4 5.3-7.9 8.8-11.88 11.88-14.86 15.48-17.56 21.05-25.06 25.43-27.9 27.9-30.37 30.58-31.8 31.8-33.71 34.06-35.75 37.47-39.76 40.26-41.76 43.66-45.9 45.9-48.14 49.6-50.93 54.3-56.29 56.29-84.43 84.63-86.78 86.84-91.09 91.09-94.12 94.6-99.96 102.75-104.63 107.17-109.28 112.84-114.77 114.8-116.15 116.15-117.58 118.05-123.71 123.71-152.22 152.24-156.2 163.26-165.57 185.93-187.22 187.35-188.59 189.37-190.57 191.5-193.34 193.99-195.25 196.64-198.84 199.87-201.17",
          "p1": "0-1.43 4.67-6.8 9.83-48.37 61.77-64.99 67.67-69.19 70.14-71.36 74.21-84.59 85.87-92.17 92.27-102.28 103.14-109.51",
          "p2": "0.4-1.98 11.27-12.89 13.25-17.1"}
M = dict(w=1240, h=805, x=80, y=110); P = dict(w=416, h=900, x=330, y=90)
SCENES = {  # name: source, window, speed, layout, extra pre-filter
  "ma": ("mac", 0, 48, 1.8, M, "split[s][c];[c]crop=940:150:1450:690,boxblur=22:4[b];[s][b]overlay=1450:690:enable='between(t,4,19.5)'"),
  "mb": ("mac", 48, 100, 1.25, M, None),
  "pa": ("p1", 0, 75, 1.6, P, None),
  "md": ("mac", 150, 171, 1.25, M, None),   # stops before the error at the end of the recording
  "pb": ("p2", 0, 27.3, 1.9, P, None)}
BEAT = 0.4
for name, (src, a, b, speed, L, pre) in SCENES.items():
    if len(sys.argv) > 1 and name not in sys.argv[1:]: continue
    fr = [tuple(map(float, x.split("-"))) for x in FREEZE[src].split()]
    keep, t = [], a
    for s, e in sorted(fr):
        s, e = max(s, a), min(e, b)
        if e <= t or s >= b: continue
        if s > t: keep.append((t, s))
        keep.append((s, min(s + BEAT, e))); t = e
    if t < b: keep.append((t, b))
    keep = [(s, e) for s, e in keep if e - s > 0.05]
    out_len = sum(e - s for s, e in keep) / speed
    chain = (f"[1:v]{pre}[pre];[pre]" if pre else "[1:v]") + "split=" + str(len(keep)) + "".join(f"[k{i}]" for i in range(len(keep))) + ";"
    chain += ";".join(f"[k{i}]trim={s}:{e},setpts=PTS-STARTPTS[t{i}]" for i, (s, e) in enumerate(keep)) + ";"
    chain += "".join(f"[t{i}]" for i in range(len(keep))) + f"concat=n={len(keep)}:v=1:a=0,setpts=PTS/{speed},fps=30,scale={L['w']}:{L['h']}:flags=lanczos[v];"
    chain += f"[0:v][v]overlay={L['x']}:{L['y']}:shortest=1[c];[c][2:v]overlay=0:0,fade=t=in:d=0.4,fade=t=out:st={out_len-0.4:.2f}:d=0.4,format=yuv420p[o]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", "comp/bg.png", "-i", SRC[src],
                    "-loop", "1", "-framerate", "30", "-i", f"comp/{name}.png", "-filter_complex", chain, "-map", "[o]",
                    "-t", f"{out_len:.2f}", "-an", "-c:v", "libx264", "-crf", "17", "-r", "30", f"scenes/{name}.mp4"], check=True)
    print(name, f"{b - a:.0f}s source -> {out_len:.1f}s, {len(keep)} cuts")
