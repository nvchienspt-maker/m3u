import sys
import re
sys.stdout.reconfigure(encoding='utf-8')

with open('source_all.m3u', 'r', encoding='utf-8', errors='ignore') as f:
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

for target_group in ['TruyenHinh_2', 'TruyenHinh_3', 'TruyenHinh_4']:
    group_blocks = [b for b in blocks if f'group-title="{target_group}"' in b[0]]
    print(f"\nGroup {target_group}: {len(group_blocks)} channels")
    for b in group_blocks[:10]:
        name = b[0].split(',')[-1].strip()
        url = [l for l in b[1:] if l.startswith('http')][0] if any(l.startswith('http') for l in b[1:]) else ''
        print(f"  {name} -> {url[:60]}")

