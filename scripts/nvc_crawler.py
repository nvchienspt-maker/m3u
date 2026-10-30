#!/usr/bin/env python3
"""
NVC Tivi - Master Channel Crawler & Deep Live Validator (v3.0)
Hệ thống crawl, tổng hợp đa nguồn, loại bỏ phim/VOD, lọc link sống chuyên sâu,
phân nhóm chuẩn 6 danh mục theo thứ tự: VTV, VTVCab, HTV, SCTV, Quốc Tế, Địa Phương.
"""

import os
import sys
import re
import json
import time
import ssl
import urllib.request
import urllib.error
import urllib.parse
import unicodedata
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding='utf-8')
CTX = ssl._create_unverified_context()
TIMEOUT = 3.5

LOGO_BASE = "https://raw.githubusercontent.com/nvchienspt-maker/m3u/refs/heads/main/logos"

BANNED_DOMAINS = [
    "1011154949.vnns.net",
    "watchtivo-8k.com",
    "stream.dongthaptv.vn"
]

GEO_VN_DOMAINS = [
    "fptplay", "vtvdigital.vn", "vtvgo", "tv360", "mytvnet.vn", "vieon",
    "seenow.vn", "vtvprime.vn", "vietmitv.id.vn", "short.gy", "dpdns.org"
]

ORDERED_GROUPS = [
    "VTV",
    "VTVCab",
    "HTV",
    "SCTV",
    "Quốc Tế",
    "Địa Phương"
]

VIETNAMESE_PROVINCES = [
    "an giang", "vung tau", "bac giang", "bac kan", "bac lieu", "bac ninh", "ben tre",
    "binh dinh", "binh duong", "binh phuoc", "binh thuan", "ca mau", "can tho", "cao bang",
    "da nang", "dak lak", "dak nong", "dien bien", "dong nai", "dong thap", "gia lai",
    "ha giang", "ha nam", "ha noi", "ha tinh", "hai duong", "hai phong", "hau giang",
    "hoa binh", "hung yen", "khanh hoa", "kien giang", "kon tum", "lai chau", "lam dong",
    "lang son", "lao cai", "long an", "nam dinh", "nghe an", "ninh binh", "ninh thuan",
    "phu tho", "phu yen", "quang binh", "quang nam", "quang ngai", "quang ninh", "quang tri",
    "soc trang", "son la", "tay ninh", "thai binh", "thai nguyen", "thanh hoa", "hue",
    "tien giang", "tra vinh", "tuyen quang", "vinh long", "vinh phuc", "yen bai",
    "thvl", "thp", "dnrtv", "drt", "btv", "ptth", "antv", "an ninh", "qpvn", "quoc phong",
    "nhan dan", "quoc hoi", "vov tv", "vtc"
]

INTL_KEYWORDS = [
    "hbo", "cinemax", "axn", "cinemaworld", "cartoon network", "cartoonito",
    "cbeebies", "dmax", "dreamworks", "davinci", "kix", "animal planet",
    "outdoor", "channel news asia", "cna", "tv5", "discovery", "tlc",
    "fashion tv", "food network", "afn", "hgtv", "kbs", "nhk", "france 24",
    "cnbc", "history", "deutsche welle", "dw", "cnn", "arirang", "bloomberg",
    "bbc", "tvb", "warner", "cctv", "sky sport", "canal+", "tnt sports",
    "box movie", "hollywood classics", "box hits", "music box", "woman",
    "cctv"
]

def strip_accents(text):
    text = text.replace('đ', 'd').replace('Đ', 'D')
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower()

def is_movie_or_junk(name, group, url):
    lower_n = name.lower().strip()
    lower_g = group.lower().strip()
    lower_u = url.lower().strip()
    
    if not url or not url.startswith("http"):
        return True
    if lower_n in ["unknown", "test", "#extinf:-1"] or len(lower_n) < 2:
        return True
    if "quý khán giả" in lower_n or "mật lệnh hoa sữa" in lower_n:
        return True
        
    movie_words = [
        "kkphim", "phim1280", "betting with ghost", "làm giàu với ma",
        "doraemon movie", "ngày xưa có một chuyện tình", "đèn âm hồn",
        "người con gái nam xương", "phim lẻ", "phim bộ", "tập 0", "tập 1",
        "tập 2", "tập 3", "tập 4", "tập 5", "tập 6", "tập 7", "tập 8", "tập 9",
        "tap-", "tap_", "episode", "season", "thuyết minh", "lồng tiếng",
        "bản đẹp", "camrip", "web-dl", "chiếu rạp", "hùng long phong bá"
    ]
    if any(w in lower_n for w in movie_words) or any(lower_u.endswith(ext) for ext in [".mp4", ".mkv", ".avi"]) or "kkphim" in lower_u or "phim1280" in lower_u:
        return True
    if lower_g in ["live events 🔴", "kho phim", "phim", "vod", "phim le", "phim bo"]:
        return True
    if "radio" in lower_g or lower_n.startswith("vov") or "heart fm" in lower_n or "capital radio" in lower_n:
        return True
    football_blv = [
        "socolive", "luongson", "cola tv", "gà vàng", "khán đài tv", "xôi chè tv",
        "blv ", "blv.", "blv_", "tiếng việt blv", "japan (w)", "india (w)", "adelaide", "machida"
    ]
    if any(b in lower_n for b in football_blv) or any(b in lower_g for b in football_blv):
        return True
    return False

def clean_channel_name(name):
    n = name.strip()
    if ' - Báo và PTTH' in n: n = n.split(' - Báo và PTTH')[0].strip()
    if ' - Vie Channel' in n: n = n.split(' - Vie Channel')[0].strip()
    if ' - TODAY TV' in n: n = n.split(' - TODAY TV')[0].strip()
    if ' | ' in n: n = n.split(' | ')[0].strip()
    return n

def classify_channel(name, group):
    s = strip_accents(f"{name} {group}").replace("+", "plus")
    lower_n = name.lower()
    
    # 1. VTV
    if "vtv" in s and "vtvcab" not in s and "vtvprime" not in s:
        if any(f"vtv{i}" in s.replace(" ", "") for i in range(1, 13)) or "vtv can tho" in s or "vietnam today" in s:
            return "VTV"
        if "vtv" in strip_accents(group) and "vtvcab" not in strip_accents(group):
            return "VTV"

    # 2. VTVCab
    if "vtvcab" in s or "vtvprime" in s:
        return "VTVCab"
    on_channels = [
        "on sports", "on cine", "on movies", "on football", "on golf",
        "on kids", "on bibi", "on o2tv", "on music", "on life", "on phim viet",
        "on vfamily", "on trending", "on infotv", "on vie", "on e channel",
        "the thao tv", "bong da tv"
    ]
    if any(c in s for c in on_channels):
        return "VTVCab"

    # 3. HTV
    if "htv" in s or "htvc" in s:
        return "HTV"

    # 4. SCTV
    if "sctv" in s:
        return "SCTV"

    # 5. Quốc Tế
    if any(k in lower_n for k in INTL_KEYWORDS) or any(k in strip_accents(group) for k in ["quoc te", "trung quoc", "in the box"]):
        return "Quốc Tế"

    # 6. Địa Phương
    if any(p in s for p in VIETNAMESE_PROVINCES):
        return "Địa Phương"

    return None

def get_canonical_key(name, group):
    s = strip_accents(clean_channel_name(name)).replace("+", "plus")
    
    # VTV
    if "vtv" in s and "vtvcab" not in s and "vtvprime" not in s:
        vtv_m = re.search(r'\bvtv\s*([0-9]+)\b', s)
        if vtv_m: return f"vtv{vtv_m.group(1)}"
        if "can tho" in s: return "vtvcantho"
        if "5" in s:
            if "tay nguyen" in s: return "vtv5tn"
            if "tay nam bo" in s: return "vtv5tnb"
            return "vtv5"
        if "vietnam today" in s: return "vietnamtoday"
            
    # VTVCab
    if "vtvprime" in s:
        p_m = re.search(r'vtvprime\s*([0-9]+)', s)
        if p_m: return f"vtvprime_{p_m.group(1)}"
            
    on_m = re.search(r'\bon\s+([a-z0-9\+]+)', s)
    if on_m:
        sub = on_m.group(1).replace('+', 'plus').replace(' ', '')
        for tag in ['hd', 'sd', '50fps', 'tv']:
            sub = re.sub(r'\b' + tag + r'\b', '', sub)
        return f"on_{sub}"

    # HTV & HTVC
    if "htvc" in s:
        if "thuan viet" in s: return "htvc_thuanviet"
        if "gia dinh" in s: return "htvc_giadinh"
        if "phu nu" in s: return "htvc_phunu"
        if "du lich" in s: return "htvc_dulich"
        if "phim" in s: return "htvc_phim"
        if "ca nhac" in s: return "htvc_canhac"
        if "plus" in s or "+" in s: return "htvc_plus"
        sub = s.replace("htvc", "").strip()
        sub = re.sub(r'\b(hd|sd|plus|\+)\b', '', sub).strip().replace(" ", "")
        return f"htvc_{sub}" if sub else "htvc"
        
    htv_m = re.search(r'\bhtv\s*([0-9]+)\b', s)
    if htv_m: return f"htv{htv_m.group(1)}"
    if "htv the thao" in s: return "htvthethao"
    if "htv key" in s: return "htvkey"

    # SCTV
    sctv_m = re.search(r'\bsctv\s*([0-9]+)\b', s)
    if sctv_m: return f"sctv{sctv_m.group(1)}"
    if "sctv 4k" in s or "sctv4k" in s: return "sctv4k"
    if "sctv" in s and ("phim tong hop" in s or "pth" in s or "dan toc" in s):
        return "sctvhdpth"

    # Quốc Tế
    if "hbo hits" in s: return "hbo_hits"
    if "hbo family" in s: return "hbo_family"
    if "hbo signature" in s: return "hbo_signature"
    if "hbo" in s: return "hbo"
    if "cinemax" in s: return "cinemax"
    if "cinemaworld" in s or "cinema world" in s: return "cinemaworld"
    if "warner" in s: return "warner_tv"
    if "axn" in s: return "axn"
    if "cartoon network" in s: return "cartoon_network"
    if "cartoonito" in s: return "cartoonito"
    if "cbeebies" in s: return "cbeebies"
    if "dreamworks" in s: return "dreamworks"
    if "davinci" in s or "da vinci" in s: return "davinci"
    if "kix" in s: return "kix"
    if "animal planet" in s: return "animal_planet"
    if "discovery asia" in s: return "discovery_asia"
    if "discovery" in s: return "discovery"
    if "tlc" in s or "travel living" in s: return "tlc"
    if "fashion" in s: return "fashion_tv"
    if "food network" in s or "afn" in s: return "asian_food_network"
    if "hgtv" in s: return "hgtv"
    if "kbs world" in s or "kbs" in s and "world" in s: return "kbs_world"
    if "nhk world" in s: return "nhk_world"
    if "nhk premium" in s: return "nhk_premium"
    if "france 24" in s: return "france24"
    if "cnbc" in s: return "cnbc"
    if "history" in s: return "history"
    if "dw" in s or "deutsche welle" in s: return "dw"
    if "cnn" in s: return "cnn"
    if "arirang" in s: return "arirang"
    if "bloomberg" in s: return "bloomberg"
    if "cna" in s or "channel news asia" in s: return "cna"
    if "tv5" in s or "tv5monde" in s: return "tv5monde"
    if "box movie" in s: return "box_movie_1"
    if "hollywood classics" in s: return "hollywood_classics"
    if "box hits" in s: return "box_hits"
    if "music box" in s and "russia" not in s: return "music_box"
    if "woman" in s: return "woman"
    if "outdoor" in s: return "outdoor_hd"
    if "dmax" in s: return "dmax"
    if "tvb viet nam" in s or "tvb việt nam" in s: return "tvb_vietnam"
    
    # CCTV
    cctv_m = re.search(r'cctv\s*([0-9\+]+)', s)
    if cctv_m: return f"cctv_{cctv_m.group(1).replace('+', 'plus')}"

    # Địa Phương
    thvl_m = re.search(r'(thvl|vinh long)\s*([0-9]+)', s)
    if thvl_m: return f"thvl{thvl_m.group(2)}"
    hn_m = re.search(r'(ha noi|hanoi)\s*([0-9]+)', s)
    if hn_m: return f"hanoi{hn_m.group(2)}"
    ct_m = re.search(r'(can tho|cantho)\s*([0-9]+)', s)
    if ct_m: return f"cantho{ct_m.group(2)}"
    dn_m = re.search(r'(da nang|danang)\s*([0-9]+)', s)
    if dn_m: return f"danang{dn_m.group(2)}"
    dnai_m = re.search(r'(dong nai|dnrtv)\s*([0-9]+)', s)
    if dnai_m: return f"dongnai{dnai_m.group(2)}"
    dt_m = re.search(r'(dong thap)\s*([0-9]+)', s)
    if dt_m: return f"dongthap{dt_m.group(2)}"
    if "dong thap" in s: return "dongthap1"
    ag_m = re.search(r'(an giang)\s*([0-9]+)', s)
    if ag_m: return f"angiang{ag_m.group(2)}"
    ld_m = re.search(r'(lam dong)\s*([0-9]+)', s)
    if ld_m: return f"lamdong{ld_m.group(2)}"
    hp_m = re.search(r'(hai phong|thp)\s*([0-9]+)', s)
    if hp_m: return f"haiphong{hp_m.group(2)}"
    if "hai phong" in s or "thp" in s: return "haiphong1"
    if "khanh hoa" in s: return "khanhhoa"
    if "dak lak" in s or "drt" in s: return "daklak"
    if "antv" in s or "an ninh tv" in s: return "antv"
    if "qpvn" in s or "quoc phong" in s: return "qpvn"

    clean = re.sub(r'[^a-z0-9]', '', s)
    for tag in ['hd', 'sd', 'fhd', '4k', '50fps', '1080p', '720p', 'tv', 'truyenhinh', 'kenh']:
        clean = re.sub(r'\b' + tag + r'\b', '', clean)
    return clean if clean else s

def get_tvg_id(key, orig_id):
    if orig_id and len(orig_id) > 2 and "http" not in orig_id:
        return orig_id
    if key.startswith("vtv") and key not in ["vtvcantho", "vtv5tn", "vtv5tnb"]:
        return f"{key}hd"
    return key

def parse_m3u(path, source_tag):
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()

    blocks = []
    curr = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('#EXTINF:'):
            if curr: blocks.append(curr)
            curr = [line]
        elif curr and line:
            curr.append(line)
    if curr: blocks.append(curr)

    channels = []
    for b in blocks:
        extinf = b[0]
        comma = extinf.rfind(',')
        name = extinf[comma+1:].strip() if comma >= 0 else extinf
        
        g_match = re.search(r'group-title="([^"]*)"', extinf)
        group = g_match.group(1).strip() if g_match else 'None'
        
        id_match = re.search(r'tvg-id="([^"]*)"', extinf)
        tvg_id = id_match.group(1).strip() if id_match else ''
        
        logo_match = re.search(r'tvg-logo="([^"]*)"', extinf)
        logo = logo_match.group(1).strip() if logo_match else ''
        
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        url = ""
        has_kodi = False
        license_key = None
        for l in b[1:]:
            if 'http-user-agent=' in l: ua = l.split('http-user-agent=')[-1].strip()
            elif 'manifest_type=hls' in l or 'manifest_type=mpd' in l: has_kodi = True
            elif 'license_key=' in l: license_key = l.split('license_key=')[-1].strip()
            elif l.startswith('http://') or l.startswith('https://'): url = l
                
        if url:
            channels.append({
                'name': name, 'group': group, 'tvg_id': tvg_id, 'logo': logo,
                'url': url, 'ua': ua, 'kodi': has_kodi, 'license': license_key, 'source': source_tag
            })
    return channels

def deep_test_stream(url, ua="Mozilla/5.0"):
    for bad in BANNED_DOMAINS:
        if bad in url:
            return False, f"Banned domain ({bad})", 0, url

    req_headers = {
        "User-Agent": ua if ua else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*"
    }
    
    start = time.time()
    try:
        req = urllib.request.Request(url, headers=req_headers)
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as resp:
            elapsed = int((time.time() - start) * 1000)
            status = resp.status
            if status != 200:
                return False, f"HTTP {status}", elapsed, url
                
            content = resp.read(4096)
            text = content.decode('utf-8', errors='ignore')
            lower_text = text.lower()
            
            if "signal_low" in lower_text or "nosignal" in lower_text or "offline" in lower_text:
                return False, "Placeholder/No Signal", elapsed, url
                
            if "<mpd" in lower_text or "manifest.mpd" in url.lower():
                return True, "LIVE (DASH/DRM)", elapsed, resp.geturl()
                
            if "#extm3u" in lower_text or "#ext-x-" in lower_text:
                if "#ext-x-stream-inf" in lower_text:
                    sub_url = None
                    for line in text.splitlines():
                        line = line.strip()
                        if line and not line.startswith('#'):
                            sub_url = urllib.parse.urljoin(resp.geturl(), line)
                            break
                    if sub_url and sub_url != url:
                        try:
                            sub_req = urllib.request.Request(sub_url, headers=req_headers)
                            with urllib.request.urlopen(sub_req, timeout=TIMEOUT, context=CTX) as sub_resp:
                                sub_data = sub_resp.read(2048).decode('utf-8', errors='ignore')
                                if any(m in sub_data.lower() for m in ['.ts', '.m4s', '#extinf', 'chunklist']):
                                    return True, "LIVE (Verified HLS)", elapsed, sub_resp.geturl()
                                else:
                                    return False, "Empty Sub-playlist", elapsed, sub_url
                        except Exception as sub_e:
                            return False, f"Sub-playlist error ({type(sub_e).__name__})", elapsed, sub_url
                
                if any(m in lower_text for m in ['.ts', '.m4s', '#extinf', '#ext-x-targetduration']):
                    return True, "LIVE (HLS Chunks)", elapsed, resp.geturl()
                    
                return True, "LIVE (HLS)", elapsed, resp.geturl()
                
            return False, "Not valid HLS/DASH", elapsed, url

    except urllib.error.HTTPError as e:
        elapsed = int((time.time() - start) * 1000)
        if e.code in (401, 403):
            if any(dom in url for dom in GEO_VN_DOMAINS):
                return True, f"LIVE (Geo-VN {e.code})", elapsed, url
        return False, f"HTTP {e.code}", elapsed, url
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        return False, f"Error: {type(e).__name__}", elapsed, url

def verify_channel_item(item):
    urls = item['urls']
    ua = item['ua']
    
    for idx, u in enumerate(urls):
        ok, reason, latency, final_url = deep_test_stream(u, ua)
        if ok:
            item['best_url'] = u
            item['resolved_url'] = final_url
            item['status'] = reason
            item['latency'] = latency
            item['is_live'] = True
            return item
            
    item['best_url'] = urls[0]
    item['resolved_url'] = ""
    item['status'] = "DEAD"
    item['latency'] = 0
    item['is_live'] = False
    return item

def main():
    print("=" * 75)
    print("⚡ NVC TIVI - HỆ THỐNG KIỂM TRA & TỔNG HỢP KÊNH TRUYỀN HÌNH CHUẨN LINK SỐNG")
    print("=" * 75)
    
    # 1. Tải và đọc nguồn
    s1 = parse_m3u("source_all.m3u", "IPTV-Auto")
    s2 = parse_m3u("source_vmttv.m3u", "VMTTV")
    
    # Uploaded file
    uploaded_candidates = [
        "C:/Users/ADMIN/.gemini/antigravity/brain/00f23127-e01e-43b1-89dc-d1934fab81e7/.user_uploaded/media_1793336516800_1f042b9f.m3u",
        "vxm_decrypted_(1).m3u"
    ]
    s3 = []
    for cand in uploaded_candidates:
        if os.path.exists(cand):
            s3 = parse_m3u(cand, "VXM-Uploaded")
            break
            
    # Link CDN trực tiếp chính chủ (không có vnns.net)
    trusted_direct_cdns = {
        "vtv1": ["https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/vtv1/playlist_360p.m3u8"],
        "vtv2": ["https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/vtv2/playlist_360p.m3u8"],
        "vtv3": ["https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/vtv3/playlist_360p.m3u8"],
        "vtv4": ["https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/vtv4/playlist_360p.m3u8"],
        "vtv5": ["https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/vtv5/playlist_360p.m3u8"]
    }
    
    combined_raw = s3 + s2 + s1
    print(f"Tổng số bản ghi đọc được từ các nguồn: {len(combined_raw)}")
    
    unique_candidates = {}
    movie_junk_count = 0
    
    for item in combined_raw:
        name = clean_channel_name(item['name'])
        group = item['group']
        url = item['url']
        
        # 1. Bỏ ngay link phim, VOD, radio, BLV phủi
        if is_movie_or_junk(name, group, url):
            movie_junk_count += 1
            continue
            
        # 2. Bỏ domain hỏng đã biết
        if any(bad in url for bad in BANNED_DOMAINS):
            continue
            
        target_group = classify_channel(name, group)
        if not target_group:
            continue
            
        key = get_canonical_key(name, group)
        tvg_id = get_tvg_id(key, item['tvg_id'])
        logo = f"{LOGO_BASE}/{tvg_id}.png"
        
        if key not in unique_candidates:
            candidate_urls = []
            if key in trusted_direct_cdns:
                candidate_urls.extend(trusted_direct_cdns[key])
            if url not in candidate_urls:
                candidate_urls.append(url)
                
            unique_candidates[key] = {
                'key': key,
                'name': name,
                'target_group': target_group,
                'tvg_id': tvg_id,
                'logo': logo,
                'ua': item['ua'],
                'kodi': item['kodi'],
                'license': item['license'],
                'urls': candidate_urls
            }
        else:
            if url not in unique_candidates[key]['urls']:
                unique_candidates[key]['urls'].append(url)
            if not unique_candidates[key]['kodi'] and item['kodi']:
                unique_candidates[key]['kodi'] = True
            if not unique_candidates[key]['license'] and item['license']:
                unique_candidates[key]['license'] = item['license']

    print(f"-> Đã loại bỏ link phim, VOD và nội dung rác: {movie_junk_count} mục")
    print(f"-> Tổng số kênh phân loại duy nhất cần kiểm tra luồng: {len(unique_candidates)} kênh")
    
    print("\nĐang tiến hành kiểm tra luồng sống thực tế cho từng kênh (16 luồng đồng thời)...")
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=16) as executor:
        tested_results = list(executor.map(verify_channel_item, unique_candidates.values()))
        
    elapsed_all = time.time() - start_time
    
    live_channels = [ch for ch in tested_results if ch['is_live']]
    dead_channels = [ch for ch in tested_results if not ch['is_live']]
    
    print(f"-> Hoàn tất kiểm tra trong {elapsed_all:.2f}s!")
    print(f"✅ SỐ KÊNH SỐNG (LIVE): {len(live_channels)} kênh")
    print(f"❌ SỐ KÊNH CHẾT ĐÃ LOẠI BỎ (DEAD): {len(dead_channels)} kênh")
    
    # Phân bổ vào 6 nhóm theo đúng thứ tự
    grouped = {g: [] for g in ORDERED_GROUPS}
    for ch in live_channels:
        g = ch['target_group']
        grouped[g].append(ch)
        
    print("\n" + "=" * 75)
    print("📊 KẾT QUẢ PHÂN NHÓM CHUẨN (ĐÃ XẮP XẾP VÀ LOẠI BỎ KÊNH CHẾT):")
    print("=" * 75)
    final_playlist = []
    for g in ORDERED_GROUPS:
        chs = grouped[g]
        print(f"  {ORDERED_GROUPS.index(g)+1}. {g}: {len(chs)} kênh")
        final_playlist.extend(chs)
        
    print(f"\n=> TỔNG SỐ KÊNH TRUYỀN HÌNH SỐNG ĐƯỢC ĐƯA VÀO PLAYLIST: {len(final_playlist)} KÊNH")
    
    # Tạo M3U
    m3u_lines = [
        '#EXTM3U url-tvg="https://epgvn.vercel.app/epg.xml,https://epg.io.vn/epgc.xml" tvg-shift=0 m3uautoload=1',
        '#PLAYLIST: NVC Tivi - Truyền Hình Việt Nam & Quốc Tế Chuẩn Link Sống',
        '#AUTHOR: NVC Tivi Development Team',
        ''
    ]
    proxy_lines = [
        '#EXTM3U url-tvg="https://epgvn.vercel.app/epg.xml,https://epg.io.vn/epgc.xml" tvg-shift=0 m3uautoload=1',
        '#PLAYLIST: NVC Tivi - Truyền Hình Việt Nam & Quốc Tế Chuẩn Link Sống',
        '#AUTHOR: NVC Tivi Development Team',
        ''
    ]
    
    for ch in final_playlist:
        extinf = f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}" tvg-name="{ch["name"]}" tvg-logo="{ch["logo"]}" group-title="{ch["target_group"]}",{ch["name"]}'
        
        m3u_lines.append(extinf)
        if ch.get("ua"): m3u_lines.append(f'#EXTVLCOPT:http-user-agent={ch["ua"]}')
        if ch.get("kodi"): m3u_lines.append('#KODIPROP:inputstream.adaptive.manifest_type=hls')
        if ch.get("license"): m3u_lines.append(f'#KODIPROP:inputstream.adaptive.license_key={ch["license"]}')
        m3u_lines.append(ch['best_url'])
        m3u_lines.append('')
        
        proxy_lines.append(extinf)
        if ch.get("ua"): proxy_lines.append(f'#EXTVLCOPT:http-user-agent={ch["ua"]}')
        if ch.get("kodi"): proxy_lines.append('#KODIPROP:inputstream.adaptive.manifest_type=hls')
        if ch.get("license"): proxy_lines.append(f'#KODIPROP:inputstream.adaptive.license_key={ch["license"]}')
        proxy_url = f"https://nvctivi-stream.workers.dev/channel?group={urllib.parse.quote(ch['target_group'])}&name={urllib.parse.quote(ch['name'])}"
        proxy_lines.append(proxy_url)
        proxy_lines.append('')

    with open("nvctivi.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))
    print("-> Xuất thành công nvctivi.m3u")
    
    with open("nvctivi_proxy.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(proxy_lines))
    print("-> Xuất thành công nvctivi_proxy.m3u")

    # Master catalog
    master_catalog = []
    for ch in final_playlist:
        master_catalog.append({
            "name": ch["name"],
            "group": ch["target_group"],
            "tvg_id": ch["tvg_id"],
            "logo": ch["logo"],
            "urls": ch["urls"],
            "headers": {"User-Agent": ch["ua"]},
            "kodi": ch.get("kodi", False),
            "license": ch.get("license")
        })
    with open("scripts/master_178_catalog.json", "w", encoding="utf-8") as f:
        json.dump(master_catalog, f, ensure_ascii=False, indent=2)
    print("-> Cập nhật scripts/master_178_catalog.json")

    # JSON API
    json_data = {
        "app": "NVC Tivi",
        "version": "2.0.0",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_channels": len(final_playlist),
        "epg_urls": [
            "https://epgvn.vercel.app/epg.xml",
            "https://epg.io.vn/epgc.xml"
        ],
        "groups": ORDERED_GROUPS,
        "channels": [
            {
                "name": ch["name"],
                "group": ch["target_group"],
                "tvg_id": ch["tvg_id"],
                "logo": ch["logo"],
                "url": ch["best_url"],
                "user_agent": ch["ua"],
                "kodi": ch.get("kodi", False),
                "status": ch["status"]
            }
            for ch in final_playlist
        ]
    }
    with open("nvctivi_channels.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    print("-> Cập nhật nvctivi_channels.json")

    # Báo cáo Markdown
    report_lines = [
        "# Báo Cáo Kiểm Tra Kênh Truyền Hình NVC Tivi",
        f"\n- **Thời gian quét:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Tổng số kênh hoạt động (LIVE):** **{len(final_playlist)} kênh**",
        f"- **Đã loại bỏ link chết / domain lỗi:** {len(dead_channels)} kênh",
        f"- **Đã loại bỏ link phim/VOD/rác:** {movie_junk_count} mục",
        f"- **EPG tích hợp:** `https://epgvn.vercel.app/epg.xml`, `https://epg.io.vn/epgc.xml`",
        f"- **Đường dẫn Logo chuẩn:** `{LOGO_BASE}/`",
        "\n## Danh sách phân bổ kênh theo thứ tự chuẩn:\n"
    ]
    for g in ORDERED_GROUPS:
        chs = grouped[g]
        report_lines.append(f"### {ORDERED_GROUPS.index(g)+1}. {g} ({len(chs)} kênh)")
        report_lines.append("| STT | Tên kênh | TVG-ID | Trạng thái | Link phát |")
        report_lines.append("| :---: | :--- | :--- | :---: | :--- |")
        for i, c in enumerate(chs, 1):
            report_lines.append(f"| {i} | {c['name']} | `{c['tvg_id']}` | ✅ {c['status']} | `{c['best_url'][:60]}...` |")
        report_lines.append("")
        
    with open("REPORT_LIVE_CHANNELS.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print("-> Cập nhật REPORT_LIVE_CHANNELS.md")

if __name__ == "__main__":
    main()
