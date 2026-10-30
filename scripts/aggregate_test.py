import re
import sys
import json
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# Helper to normalize channel names for deduplication
def get_canonical_key(name, orig_group):
    n = name.lower().strip()
    
    # Pre-clean
    n = re.sub(r'\[.*?\]|\(.*?\)', '', n)
    for tag in ['- báo và ptth', '- vie channel', '- today tv', '- btv', '- drt', '- thp']:
        if tag in n:
            n = n.split(tag)[0].strip()
            
    # Normalize common Vietnamese accents
    n = n.replace('đ', 'd')
    
    # Specific standard keys
    # VTV
    vtv_match = re.search(r'\bvtv\s*([0-9]+)\b', n)
    if vtv_match:
        return f"vtv{vtv_match.group(1)}"
    if "vtv can tho" in n or "vtv cần thơ" in n:
        return "vtvcantho"
    if "vtv5" in n:
        if "tay nguyen" in n or "tây nguyên" in n:
            return "vtv5tn"
        if "tay nam bo" in n or "tây nam bộ" in n:
            return "vtv5tnb"
        return "vtv5"
    if "vietnam today" in n or "vietnamtoday" in n:
        return "vietnamtoday"
        
    # HTV & HTVC
    htvc_match = re.search(r'htvc\s*([a-z0-9\s]+)', n)
    if htvc_match:
        sub = htvc_match.group(1).strip().replace(" ", "")
        for tag in ['hd', 'sd']:
            sub = sub.replace(tag, '')
        return f"htvc_{sub}"
    htv_match = re.search(r'\bhtv\s*([0-9]+)\b', n)
    if htv_match:
        return f"htv{htv_match.group(1)}"
    if "htv the thao" in n or "htv thể thao" in n:
        return "htvthethao"
    if "htv key" in n or "htvkey" in n:
        return "htvkey"

    # SCTV
    sctv_match = re.search(r'\bsctv\s*([0-9]+)\b', n)
    if sctv_match:
        return f"sctv{sctv_match.group(1)}"
    if "sctv 4k" in n or "sctv4k" in n:
        return "sctv4k"
    if "sctv" in n and ("tieng dan toc" in n or "tiếng dân tộc" in n or "hd pth" in n):
        return "sctvhdpth"

    # VTVCab / ON
    on_match = re.search(r'\b(on\s+[a-z0-9\+]+)', n)
    if on_match:
        sub = on_match.group(1).replace(" ", "").replace("+", "plus")
        for tag in ['hd', 'sd', '50fps']:
            sub = sub.replace(tag, '')
        return f"on_{sub}"
    if "vtvprime" in n:
        p_num = re.search(r'vtvprime\s*([0-9]+)', n)
        return f"vtvprime_{p_num.group(1)}" if p_num else "vtvprime"

    # THVL / Vĩnh Long
    thvl_match = re.search(r'(thvl|vinh long|vĩnh long)\s*([0-9]+)', n)
    if thvl_match:
        return f"thvl{thvl_match.group(2)}"

    # Hà Nội
    hn_match = re.search(r'(ha noi|hà nội)\s*([0-9]+)', n)
    if hn_match:
        return f"hanoi{hn_match.group(2)}"

    # Hải Phòng
    hp_match = re.search(r'(hai phong|hải phòng|thp)\s*([0-9]*)', n)
    if hp_match and ("hai phong" in n or "hải phòng" in n or "thp" in n):
        num = hp_match.group(2) if hp_match.group(2) else "1"
        return f"haiphong{num}"

    # Cần Thơ
    ct_match = re.search(r'(can tho|cần thơ)\s*([0-9]*)', n)
    if ct_match:
        num = ct_match.group(2) if ct_match.group(2) else "1"
        return f"cantho{num}"

    # Đà Nẵng
    dn_match = re.search(r'(da nang|đà nẵng|danang)\s*([0-9]*)', n)
    if dn_match:
        num = dn_match.group(2) if dn_match.group(2) else "1"
        return f"danang{num}"

    # Đồng Nai
    dnai_match = re.search(r'(dong nai|đồng nai|dnrtv)\s*([0-9]*)', n)
    if dnai_match:
        num = dnai_match.group(2) if dnai_match.group(2) else "1"
        return f"dongnai{num}"

    # Đồng Tháp
    dt_match = re.search(r'(dong thap|đồng tháp)\s*([0-9]*)', n)
    if dt_match:
        num = dt_match.group(2) if dt_match.group(2) else "1"
        return f"dongthap{num}"

    # An Giang
    ag_match = re.search(r'(an giang)\s*([0-9]*)', n)
    if ag_match:
        num = ag_match.group(2) if ag_match.group(2) else "1"
        return f"angiang{num}"

    # Lâm Đồng
    ld_match = re.search(r'(lam dong|lâm đồng)\s*([0-9]*)', n)
    if ld_match:
        num = ld_match.group(2) if ld_match.group(2) else "1"
        return f"lamdong{num}"

    # CCTV
    cctv_match = re.search(r'cctv\s*([0-9\+]+)', n)
    if cctv_match:
        return f"cctv_{cctv_match.group(1).replace('+', 'plus')}"

    # General key
    clean = re.sub(r'[^a-z0-9]', '', n)
    for tag in ['hd', 'sd', 'fhd', '4k', '50fps', '1080p', '720p', 'tv', 'truyenhinh', 'kenh']:
        clean = re.sub(r'\b' + tag + r'\b', '', clean)
    return clean if clean else n

from test_classifier import is_movie_or_junk, classify_group
from parse_all_sources import parse_m3u_file

# Collect from all 3 files
s1 = parse_m3u_file("source_all.m3u", "IPTV-Auto")
s2 = parse_m3u_file("source_vmttv.m3u", "VMTTV")
s3 = parse_m3u_file(r"C:/Users/ADMIN/.gemini/antigravity/brain/00f23127-e01e-43b1-89dc-d1934fab81e7/.user_uploaded/media_1793336516800_1f042b9f.m3u", "VXM-Uploaded")

all_raw = s3 + s2 + s1 # Priority order: Uploaded master > VMTTV > IPTV-Auto

aggregated = {}
for item in all_raw:
    name = item['name']
    group = item['group']
    url = item['url']
    
    if is_movie_or_junk(name, group, url):
        continue
        
    canonical_group = classify_group(name, group)
    key = get_canonical_key(name, group)
    
    if key not in aggregated:
        aggregated[key] = {
            'key': key,
            'name': name,
            'target_group': canonical_group,
            'tvg_id': item['tvg_id'],
            'logo': item['logo'],
            'ua': item['ua'],
            'kodi': item['kodi'],
            'urls': [url]
        }
    else:
        # Add alternative URL if not already present
        if url not in aggregated[key]['urls']:
            aggregated[key]['urls'].append(url)
        # Update tvg_id or logo if better
        if not aggregated[key]['tvg_id'] and item['tvg_id']:
            aggregated[key]['tvg_id'] = item['tvg_id']
        if not aggregated[key]['logo'] and item['logo']:
            aggregated[key]['logo'] = item['logo']

print(f"\n================ SUMMARY AFTER DEDUPLICATION ================")
print(f"Total unique channels identified: {len(aggregated)}")

grouped_counts = {"VTV": 0, "VTVCab": 0, "HTV": 0, "SCTV": 0, "Quốc Tế": 0, "Địa Phương": 0}
for k, ch in aggregated.items():
    g = ch['target_group']
    grouped_counts[g] = grouped_counts.get(g, 0) + 1

for g in ["VTV", "VTVCab", "HTV", "SCTV", "Quốc Tế", "Địa Phương"]:
    print(f"  • {g}: {grouped_counts.get(g, 0)} channels")
