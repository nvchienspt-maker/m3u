import sys
import re
sys.stdout.reconfigure(encoding='utf-8')

with open('source_vmttv.m3u', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

blocks = []
curr = []
for line in text.splitlines():
    line = line.strip()
    if line.startswith('#EXTINF:'):
        if curr:
            blocks.append(curr)
        curr = [line]
    elif curr and line:
        curr.append(line)
if curr:
    blocks.append(curr)

groups = {}
for b in blocks:
    g_match = re.search(r'group-title="([^"]*)"', b[0])
    group = g_match.group(1).strip() if g_match else 'None'
    groups.setdefault(group, []).append(b)

for g, blist in groups.items():
    print(f"\nGroup [{g}]: {len(blist)} channels")
    for b in blist[:4]:
        name = b[0].split(',')[-1].strip()
        url = [l for l in b[1:] if l.startswith('http')][0] if any(l.startswith('http') for l in b[1:]) else ''
        print(f"  {name} -> {url[:60]}")

