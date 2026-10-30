import re
import sys
import json
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

def parse_m3u_file(path, source_tag):
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

    channels = []
    for b in blocks:
        extinf = b[0]
        # parse name
        comma = extinf.rfind(',')
        name = extinf[comma+1:].strip() if comma >= 0 else extinf
        
        # clean annotations
        if ' - Báo và PTTH' in name:
            name = name.split(' - Báo và PTTH')[0].strip()
        elif ' - Vie Channel' in name:
            name = name.split(' - Vie Channel')[0].strip()
        elif ' - TODAY TV' in name:
            name = name.split(' - TODAY TV')[0].strip()
            
        g_match = re.search(r'group-title="([^"]*)"', extinf)
        group = g_match.group(1).strip() if g_match else 'None'
        
        id_match = re.search(r'tvg-id="([^"]*)"', extinf)
        tvg_id = id_match.group(1).strip() if id_match else ''
        
        logo_match = re.search(r'tvg-logo="([^"]*)"', extinf)
        logo = logo_match.group(1).strip() if logo_match else ''
        
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        url = ""
        has_kodi = False
        for l in b[1:]:
            if 'http-user-agent=' in l:
                ua = l.split('http-user-agent=')[-1].strip()
            elif 'manifest_type=hls' in l:
                has_kodi = True
            elif l.startswith('http://') or l.startswith('https://'):
                url = l
                
        if url:
            channels.append({
                'name': name,
                'group': group,
                'tvg_id': tvg_id,
                'logo': logo,
                'url': url,
                'ua': ua,
                'kodi': has_kodi,
                'source': source_tag
            })
            
    print(f"Parsed {len(channels)} channels from {source_tag} ({path})")
    return channels

src1 = parse_m3u_file("source_all.m3u", "IPTV-Auto")
src2 = parse_m3u_file("source_vmttv.m3u", "VMTTV")
src3 = parse_m3u_file(r"C:/Users/ADMIN/.gemini/antigravity/brain/00f23127-e01e-43b1-89dc-d1934fab81e7/.user_uploaded/media_1793336516800_1f042b9f.m3u", "VXM-Uploaded")

