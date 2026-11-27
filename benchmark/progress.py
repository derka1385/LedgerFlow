"""Live progress of the Vultr benchmark run. python3 benchmark/progress.py  (Ctrl+C to quit)"""
import glob, json, os, re, time

LOG = "/tmp/lf_live_full.log"
PARTS = os.path.join(os.path.dirname(__file__), "results", "live_parts")
TOTAL_CONFIGS, RECEIPTS, PLANS = 18, 22, 11

while True:
    log = open(LOG).read() if os.path.exists(LOG) else ""
    done = sorted(glob.glob(f"{PARTS}/*.json"))
    rows = {}
    for ln in log.splitlines():
        m = re.match(r"\s+(\S+) (codegen )?(R\d\d):", ln)
        if m:
            r = rows.setdefault(m.group(1), [0, 0])
            r[1 if m.group(2) else 0] += 1
    os.system("clear")
    print(f"LedgerFlow live benchmark  {time.strftime('%H:%M:%S')}   configs finished {len(done)}/{TOTAL_CONFIGS}\n")
    for spec, (rc, cg) in sorted(rows.items()):
        finished = any(os.path.basename(p) == spec.replace("@", "__") + ".json" for p in done)
        bar = "#" * int(20 * (rc + cg) / (RECEIPTS + PLANS))
        print(f"{spec:<48} [{bar:<20}] receipts {rc:>2}/{RECEIPTS}  code {cg:>2}/{PLANS}  {'DONE' if finished else ''}")
    if log.rstrip().splitlines()[-1:] and log.rstrip().splitlines()[-1].startswith("wrote "):
        print("\nRun complete:", log.rstrip().splitlines()[-1])
        break
    time.sleep(3)
