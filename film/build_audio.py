"""Builds the film soundtrack: original synthesized music bed (3 acts) + voiceover placed per scene + SRT captions."""
import json, subprocess
DUR = [12,13,13,14,10,13,14,11,15,24,14,11,12,15,14,13]
VO_OFFSET = {"s01": 2.0, "s10": 0.6}
starts, t = [], 0.0
for d in DUR: starts.append(t); t += d
TOTAL = t
vo = json.load(open("vo_script.json"))
def dur(f): return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f],capture_output=True,text=True).stdout)
# 1) music: Act I (0-68) A minor 9 pad, Act II (68-149) same pad + soft pulse, containment dip, Act III (149-end) A major add9 pad
def pad(freqs, amp=0.05):
    return "+".join(f"{amp}*sin(2*PI*{f}*t+0.3*sin(2*PI*0.11*t))*(0.7+0.3*sin(2*PI*0.07*t+{i}))" for i, f in enumerate(freqs))
minor = [110, 164.81, 220, 261.63, 329.63, 493.88]
major = [110, 164.81, 220, 277.18, 329.63, 493.88]
act1 = pad(minor)
act2 = pad(minor) + "+0.035*sin(2*PI*55*t)*(0.5+0.5*sin(2*PI*1.6*t))^4"
act3 = pad(major) + "+0.025*sin(2*PI*55*t)*(0.5+0.5*sin(2*PI*1.6*t))^4"
s10 = starts[9]; s11 = starts[10]
expr = (f"if(lt(t,{starts[5]}),{act1},if(lt(t,{s10}),{act2},if(lt(t,{s11}),0.18*({act1}),{act3})))")
subprocess.run(["ffmpeg","-y","-loglevel","error","-f","lavfi","-i",f"aevalsrc='{expr}':s=48000:d={TOTAL}",
  "-af",f"lowpass=f=2400,aecho=0.8:0.7:400|900:0.3|0.2,afade=t=in:d=3,afade=t=out:st={TOTAL-4}:d=4,volume=1.6",
  "-ac","2","audio/music.wav"],check=True)
# 2) voiceover track
inputs, filters, srt = [], [], []
for i, (sid, text) in enumerate(vo):
    at = starts[i] + VO_OFFSET.get(sid, 1.2); d = dur(f"audio/{sid}.aiff")
    inputs += ["-i", f"audio/{sid}.aiff"]; ms = int(at * 1000)
    filters.append(f"[{i}:a]aresample=48000,adelay={ms}|{ms},apad=whole_dur={TOTAL}[v{i}]")
    # captions: split long lines into ~2 chunks by sentence
    parts = [p.strip() for p in text.replace("? ", "?|").replace(". ", ".|").split("|") if p.strip()]
    tot_chars = sum(len(p) for p in parts); cur = at
    for p in parts:
        seg = d * len(p) / tot_chars; srt.append((cur, cur + seg, p)); cur += seg
mix = "".join(f"[v{i}]" for i in range(len(vo))) + f"amix=inputs={len(vo)}:normalize=0,volume=1.0[vo]"
subprocess.run(["ffmpeg","-y","-loglevel","error",*inputs,"-filter_complex",";".join(filters)+";"+mix,"-map","[vo]","-ac","2","-t",str(TOTAL),"audio/vo.wav"],check=True)
# 3) duck music under voice, mix
subprocess.run(["ffmpeg","-y","-loglevel","error","-i","audio/music.wav","-i","audio/vo.wav","-filter_complex",
  "[0:a][1:a]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[m];[m][1:a]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]",
  "-map","[a]","-c:a","pcm_s16le","audio/final_mix.wav"],check=True)
def ts(x): h=int(x//3600); m=int(x%3600//60); s=x%60; return f"{h:02}:{m:02}:{int(s):02},{int(round((s-int(s))*1000)):03}"
with open("LedgerFlow_Official_Demo.en.srt","w") as f:
    for n,(a,b,txt) in enumerate(srt,1): f.write(f"{n}\n{ts(a)} --> {ts(b)}\n{txt}\n\n")
print("total", TOTAL, "s; captions", len(srt))
