"""Editable SVG wave fields. Geometry morphs smoothly; no bitmap or video."""
from pathlib import Path
import math

out=Path(__file__).resolve().parents[2]/"frontend/public/design-lab"
def curve(line,phase):
    points=[]
    for step in range(81):
        x=-160+step*20
        t=x/1280
        y=410+line*13-160*math.sin(t*math.pi*2+phase)+34*math.sin(t*math.pi*3-phase*.7+line*.035)
        points.append(f'{x:.1f},{y:.1f}')
    return 'M'+'L'.join(points)
groups=[]
for line in range(19):
    frames=[curve(line,p) for p in [0,.42,0,-.42,0]]
    motion=f'<animate attributeName="d" dur="18s" repeatCount="indefinite" values="{";".join(frames)}" keyTimes="0;.25;.5;.75;1" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1;.45 0 .55 1;.45 0 .55 1"/>'
    groups.append(f'<path d="{frames[0]}" vector-effect="non-scaling-stroke">{motion}</path>')
static=''.join(f'<path d="{curve(i,0)}" vector-effect="non-scaling-stroke"/>' for i in range(19))
start='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" fill="none" preserveAspectRatio="xMidYMid slice"><title>LedgerFlow — nappes de vagues</title>'
style='<style>.still{display:none}@media(prefers-reduced-motion:reduce){.moving{display:none}.still{display:inline}}</style>'
paint='stroke="#bfd3a6" stroke-width="1" stroke-opacity=".5"'
(out/'flow-field.svg').write_text(start+style+f'<g class="moving" {paint}>'+''.join(groups)+f'</g><g class="still" {paint}>'+static+'</g></svg>')
(out/'flow-field-still.svg').write_text(start+f'<g {paint}>'+static+'</g></svg>')
print('Wave assets generated: 19 continuous lines, 18-second cycle, reduced-motion alternative.')
