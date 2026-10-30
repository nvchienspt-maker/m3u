import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

def analyze_m3u(path):
    print(f"\n=================== ANALYZING: {path} ===================")
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
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

    print(f"Total channel blocks: {len(blocks)}")
    
    groups = {}
    vod_phim = []
    for b in blocks:
        extinf = b[0]
        name = extinf.split(',')[-1].strip()
        g_match = re.search(r'group-title="([^"]*)"', extinf)
        group = g_match.group(1).strip() if g_match else 'None'
        groups[group] = groups.get(group, 0) + 1
        
        # Check if it looks like movie / vod
        url = ""
        for l in b[1:]:
            if l.startswith("http"):
                url = l
                break
        
        lower_name = name.lower()
        lower_group = group.lower()
        lower_url = url.lower()
        
        # Detect movie indicators
        if any(w in lower_group for w in ['phim', 'vod', 'movie', 'cinema', 'series', 'kho phim', 'phim lẻ', 'phim bộ']) or \
           any(lower_url.endswith(ext) for ext in ['.mp4', '.mkv', '.avi']) or \
           'tap-' in lower_url or 'tap_' in lower_url or 'episode' in lower_url:
            vod_phim.append((name, group, url))

    print(f"Detected {len(groups)} distinct groups:")
    for g, count in sorted(groups.items(), key=lambda x: -x[1]):
        print(f"  • [{g}]: {count} items")
        
    print(f"\nPotential Movie/VOD items count: {len(vod_phim)}")
    if vod_phim:
        print("Sample 5 potential movie/VOD items:")
        for n, g, u in vod_phim[:5]:
            print(f"   Name: {n} | Group: {g} | URL: {u[:70]}")

analyze_m3u("source_all.m3u")
analyze_m3u("source_vmttv.m3u")
analyze_m3u(r"C:/Users/ADMIN/.gemini/antigravity/brain/00f23127-e01e-43b1-89dc-d1934fab81e7/.user_uploaded/media_1793336516800_1f042b9f.m3u")

