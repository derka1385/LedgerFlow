"""Final edit v2: real recordings + motion scenes, ElevenLabs VO (+15 % tempo, pitch kept), original music, captions."""
import json, os, subprocess
EDIT = ["s01","s02","ma","mb","pa","md","s06","s07","s08","s09","s10","s11","pb","s12","s13","s14","s15","s16"]
SPEED = float(os.environ.get("VO_SPEED", "1.15"))
def dur(f): return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f],capture_output=True,text=True).stdout)
vo = dict(json.load(open("vo_script.json")))
D = [dur(f"scenes/{s}.mp4") for s in EDIT]; starts=[sum(D[:i]) for i in range(len(D))]; TOTAL=sum(D)
open("edit.txt","w").write("".join(f"file 'scenes/{s}.mp4'\n" for s in EDIT))
subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i","edit.txt","-c:v","libx264","-crf","17","-preset","medium","-pix_fmt","yuv420p","-r","30","scenes/edit2.mp4"],check=True)
# music: 3 moods following the edit (discovery → precision with pulse → containment dip → resolution)
def pad(fr, a=0.05): return "+".join(f"{a}*sin(2*PI*{f}*t+0.3*sin(2*PI*0.11*t))*(0.7+0.3*sin(2*PI*0.07*t+{i}))" for i,f in enumerate(fr))
mi=[110,164.81,220,261.63,329.63,493.88]; ma=[110,164.81,220,277.18,329.63,493.88]; pulse="+0.035*sin(2*PI*55*t)*(0.5+0.5*sin(2*PI*1.6*t))^4"
i6, i10, i11 = EDIT.index("s06"), EDIT.index("s10"), EDIT.index("s11")
expr=f"if(lt(t,{starts[i6]}),{pad(mi)},if(lt(t,{starts[i10]}),{pad(mi)}{pulse},if(lt(t,{starts[i11]}),0.18*({pad(mi)}),{pad(ma)}{pulse})))"
subprocess.run(["ffmpeg","-y","-loglevel","error","-f","lavfi","-i",f"aevalsrc='{expr}':s=48000:d={TOTAL}","-af",f"lowpass=f=2400,aecho=0.8:0.7:400|900:0.3|0.2,afade=t=in:d=3,afade=t=out:st={TOTAL-4}:d=4,volume=1.6","-ac","2","audio/music2.wav"],check=True)
inputs, filt, srt = [], [], []
for i,s in enumerate(EDIT):
    src=f"audio/{s}.mp3"; off = 2.0 if s=="s01" else 0.6 if s=="s10" else 1.0
    d=dur(src); slot=D[i]-off-0.4; tempo=min(max(d/slot,SPEED),1.3); at=starts[i]+off; ms=int(at*1000)
    inputs+=["-i",src]; filt.append(f"[{len(filt)}:a]aresample=48000,atempo={tempo:.3f},adelay={ms}|{ms},apad=whole_dur={TOTAL}[v{len(filt)}]")
    text=vo[s]; parts=[p.strip() for p in text.replace("? ","?|").replace(". ",".|").split("|") if p.strip()]; tot=sum(map(len,parts)); cur=at
    for p in parts: seg=(d/tempo)*len(p)/tot; srt.append((cur,cur+seg,p)); cur+=seg
mix="".join(f"[v{i}]" for i in range(len(filt)))+f"amix=inputs={len(filt)}:normalize=0[vo]"
subprocess.run(["ffmpeg","-y","-loglevel","error",*inputs,"-filter_complex",";".join(filt)+";"+mix,"-map","[vo]","-ac","2","-t",str(TOTAL),"audio/vo2.wav"],check=True)
subprocess.run(["ffmpeg","-y","-loglevel","error","-i","audio/music2.wav","-i","audio/vo2.wav","-filter_complex","[0:a][1:a]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[m];[m][1:a]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]","-map","[a]","audio/final2.wav"],check=True)
ts=lambda x:f"{int(x//3600):02}:{int(x%3600//60):02}:{int(x%60):02},{int(round((x%1)*1000)):03}"
open("LedgerFlow_Official_Demo.en.srt","w").write("".join(f"{n}\n{ts(a)} --> {ts(b)}\n{t}\n\n" for n,(a,b,t) in enumerate(srt,1)))
subprocess.run(["ffmpeg","-y","-loglevel","error","-i","scenes/edit2.mp4","-i","audio/final2.wav","-i","LedgerFlow_Official_Demo.en.srt","-map","0:v","-map","1:a","-map","2:s","-c:v","copy","-c:a","aac","-b:a","256k","-c:s","mov_text","-metadata:s:s:0","language=eng","-movflags","+faststart","-t",str(TOTAL),"LedgerFlow_Official_Demo.mp4"],check=True)
print(f"total {TOTAL:.1f}s, {len(srt)} captions")
