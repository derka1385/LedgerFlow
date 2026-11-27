"""Edit v3: silences cut, real-footage cuts, notification, beta card, five original music cues, ElevenLabs VO."""
import json, subprocess
EDIT = ["s01","s02","ma","mb","pa","md","s06","s07","s08","s09","s10","s11","pb","nt","s12","s13","s14","s15","s16","beta"]
FOOT = {"ma","mb","pa","md","pb","nt","beta"}
MIN = {"s01":10,"s02":12,"s10":20,"s14":13.5,"s16":12}
OFF = {"s01":1.5,"s10":0.6}
TEMPO = 1.15
def dur(f): return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f],capture_output=True,text=True).stdout)
vo = dict(json.load(open("vo_script.json")))
L = []
for s in EDIT:
    full = dur(f"scenes/{s}.mp4"); need = OFF.get(s,0.5) + dur(f"audio/{s}.mp3")/TEMPO + 0.7
    n = max(need, full) if s in FOOT else min(full, max(need, MIN.get(s,6)))
    pad = max(0, n - full)
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",f"scenes/{s}.mp4","-vf",f"tpad=stop_mode=clone:stop_duration={pad:.2f},fps=30,format=yuv420p","-t",f"{n:.2f}","-an","-c:v","libx264","-crf","17","-r","30",f"scenes/cut_{s}.mp4"],check=True)
    L.append(n)
starts=[sum(L[:i]) for i in range(len(L))]; TOTAL=sum(L)
open("edit3.txt","w").write("".join(f"file 'scenes/cut_{s}.mp4'\n" for s in EDIT))
subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i","edit3.txt","-c","copy","scenes/edit3.mp4"],check=True)
# --- music: five cues, each original and synthesized here ---
def seq(fs, rate):
    idx=f"mod(floor(t*{rate}),{len(fs)})"; e=str(fs[-1])
    for i in range(len(fs)-2,-1,-1): e=f"if(eq({idx},{i}),{fs[i]},{e})"
    return e
def pluck(fs, rate, a): return f"{a}*sin(2*PI*({seq(fs,rate)})*t)*exp(-6*mod(t,{1/rate}))"
def pad(roots, rate, a): r=seq(roots,rate); return f"{a}*(sin(2*PI*({r})*t)+0.6*sin(2*PI*1.5*({r})*t)+0.4*sin(2*PI*2*({r})*t))*(0.75+0.25*sin(2*PI*0.2*t))"
kick=lambda a,p=0.5: f"{a}*sin(2*PI*(45+90*exp(-25*mod(t,{p})))*mod(t,{p}))*exp(-7*mod(t,{p}))"
hat=lambda a: f"{a}*(2*random(0)-1)*exp(-70*mod(t+0.25,0.5))"
am=[220,261.63,329.63,440, 174.61,220,261.63,349.23, 196,261.63,329.63,392, 196,246.94,293.66,392]
maj=[220,277.18,329.63,440, 164.81,246.94,329.63,415.3, 185,220,277.18,369.99, 146.83,220,293.66,369.99]
CUES = [  # (first scene of the cue, expression)
 ("s01", pluck(am,4,0.07)+"+"+pad([110,87.31,130.81,98],1,0.035)),
 ("s06", pluck(am,4,0.05)+"+"+kick(0.28)+"+"+hat(0.035)+"+"+f"0.07*sin(2*PI*({seq([55,55,65.41,49],2)})*t)"),
 ("s10", "0.05*sin(2*PI*55*t)+0.035*sin(2*PI*82.41*t)*(0.6+0.4*sin(2*PI*0.2*t))+"+kick(0.22,1.2)),
 ("s11", pluck(maj,4,0.06)+"+"+kick(0.18)+"+"+hat(0.025)+"+"+pad([110,82.41,92.5,73.42],1,0.03)),
 ("s14", pluck(maj,3,0.07)+"+"+pad([110,82.41,92.5,73.42],0.75,0.045)+"+"+kick(0.12,1)),
]
parts=[]
for i,(first,expr) in enumerate(CUES):
    a=starts[EDIT.index(first)]; b=starts[EDIT.index(CUES[i+1][0])] if i+1<len(CUES) else TOTAL
    ln=b-a+(1.0 if i+1<len(CUES) else 0)
    f=f"audio/cue{i}.wav"; parts.append(f)
    subprocess.run(["ffmpeg","-y","-loglevel","error","-f","lavfi","-i",f"aevalsrc='{expr}':s=48000:d={ln:.2f}","-af","lowpass=f=5000,aecho=0.8:0.6:300|700:0.25|0.15","-ac","2",f],check=True)
fc="".join(f"[{i}:a]" for i in range(len(parts)))
chain=f"[0:a][1:a]acrossfade=d=1[x1]"
for i in range(2,len(parts)): chain+=f";[x{i-1}][{i}:a]acrossfade=d=1[x{i}]"
subprocess.run(["ffmpeg","-y","-loglevel","error",*sum([["-i",p] for p in parts],[]),"-filter_complex",chain+f";[x{len(parts)-1}]afade=t=in:d=2,afade=t=out:st={TOTAL-3:.2f}:d=3,volume=1.4[m]","-map","[m]","audio/music3.wav"],check=True)
# --- voice ---
inputs,filt,srt=[],[],[]
for i,s in enumerate(EDIT):
    src=f"audio/{s}.mp3"; d=dur(src)/TEMPO; at=starts[i]+OFF.get(s,0.5); ms=int(at*1000)
    inputs+=["-i",src]; filt.append(f"[{i}:a]aresample=48000,atempo={TEMPO},adelay={ms}|{ms},apad=whole_dur={TOTAL:.2f}[v{i}]")
    parts_=[p.strip() for p in vo[s].replace("? ","?|").replace(". ",".|").replace(": ",":|").split("|") if p.strip()]; tot=sum(map(len,parts_)); cur=at
    for p in parts_: seg=d*len(p)/tot; srt.append((cur,cur+seg,p)); cur+=seg
mix="".join(f"[v{i}]" for i in range(len(EDIT)))+f"amix=inputs={len(EDIT)}:normalize=0[vo]"
subprocess.run(["ffmpeg","-y","-loglevel","error",*inputs,"-filter_complex",";".join(filt)+";"+mix,"-map","[vo]","-ac","2","-t",f"{TOTAL:.2f}","audio/vo3.wav"],check=True)
subprocess.run(["ffmpeg","-y","-loglevel","error","-i","audio/music3.wav","-i","audio/vo3.wav","-filter_complex","[0:a][1:a]sidechaincompress=threshold=0.03:ratio=5:attack=20:release=350[m];[m][1:a]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]","-map","[a]","audio/final3.wav"],check=True)
ts=lambda x:f"{int(x//3600):02}:{int(x%3600//60):02}:{int(x%60):02},{int(round((x%1)*1000)):03}"
open("LedgerFlow_Official_Demo.en.srt","w").write("".join(f"{n}\n{ts(a)} --> {ts(b)}\n{t}\n\n" for n,(a,b,t) in enumerate(srt,1)))
subprocess.run(["ffmpeg","-y","-loglevel","error","-i","scenes/edit3.mp4","-i","audio/final3.wav","-i","LedgerFlow_Official_Demo.en.srt","-map","0:v","-map","1:a","-map","2:s","-c:v","copy","-c:a","aac","-b:a","256k","-c:s","mov_text","-metadata:s:s:0","language=eng","-movflags","+faststart","-t",f"{TOTAL:.2f}","LedgerFlow_Official_Demo.mp4"],check=True)
print(f"total {TOTAL:.1f}s"); print(" ".join(f"{s}:{l:.1f}" for s,l in zip(EDIT,L)))
