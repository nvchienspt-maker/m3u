#!/usr/bin/env python3
"""
NVC Tivi - Multi-Source IPTV Processor & Live Validator
Tự động tải, giải mã và xử lý 3 nguồn IPTV riêng biệt:
- Nguồn 1: vxm.enc (giải mã AESGCM)
- Nguồn 2: all.m3u (IPTV-Auto)
- Nguồn 3: vmttv (VMTTV)

Yêu cầu thực hiện cho từng file:
1. Phân nhóm rõ ràng theo 6 nhóm đúng thứ tự:
   1. VTV
   2. VTVCab
   3. HTV
   4. SCTV
   5. Quốc Tế
   6. Địa Phương
2. Xoá toàn bộ link phim, VOD, radio, BLV bóng đá phủi
3. Kiểm tra lọc link sống (loại bỏ vnns.net, link chết, bẫy offline placeholder)
4. Giữ lại các kênh bản quyền Geo-blocking VN và DRM giải mã (Kodi/MPD)
5. Chuẩn hoá Logo và Dual EPG (epgvn.vercel.app + epg.io.vn)
"""

import os
import sys
import re
import json
import time
import ssl
import struct
import hashlib
import urllib.request
import urllib.error
import urllib.parse
import unicodedata
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

sys.stdout.reconfigure(encoding='utf-8')
CTX = ssl._create_unverified_context()
TIMEOUT = 5.0

LOGO_BASE = "https://raw.githubusercontent.com/nvchienspt-maker/m3u/refs/heads/main/logos"
EPG_HEADER = '#EXTM3U url-tvg="https://epgvn.vercel.app/epg.xml,https://epg.io.vn/epgc.xml" tvg-shift=0 m3uautoload=1'

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

# ==============================================================================
# 1. GIẢI MÃ NGUỒN 1 (VXM.ENC)
# ==============================================================================
MAGIC = b"VXMENC3\x00"
AAD_PREFIX = b"VietMiTV/VXMENC3"
KEY_ID = 1

K = [
    bytes([0x85, 0x05, 0x75, 0x40, 0xE5, 0x2E, 0xD3, 0xF2]),
    bytes([0x57, 0xD8, 0xC3, 0x3E, 0x7F, 0x13, 0x1C, 0xE3]),
    bytes([0x4A, 0xBE, 0xB2, 0x89, 0x9C, 0x8E, 0x21, 0x63]),
    bytes([0x77, 0x06, 0xC3, 0x70, 0xD7, 0xCD, 0x71, 0x44]),
]
M = [0x5A, 0xA7, 0x3C, 0xD1]

def derive_key(salt):
    seed = bytes(v ^ M[i] for i, part in enumerate(K) for v in part)
    key = hashlib.sha256(seed + salt).digest()
    for _ in range(60000):
        key = hashlib.sha256(key + salt).digest()
    return key

def decrypt_vxm(data):
    if data[:8] != MAGIC:
        raise ValueError("Sai định dạng VXMENC3")
    pos = 8
    signed_len = struct.unpack(">I", data[pos:pos+4])[0]
    pos += 4
    signed = data[pos:pos+signed_len]
    pos += signed_len
    if len(signed) != signed_len or pos + 4 > len(data):
        raise ValueError("Dữ liệu bị thiếu")
    sig_len = struct.unpack(">I", data[pos:pos+4])[0]
    pos += 4
    signature = data[pos:pos+sig_len]
    if len(signature) != sig_len or pos + sig_len != len(data):
        raise ValueError("Signature length không hợp lệ")

    counter, key_id, created_at = struct.unpack(">QIQ", signed[:20])
    salt = signed[20:36]
    iv = signed[36:48]
    cipher_len = struct.unpack(">I", signed[48:52])[0]
    ciphertext = signed[52:52+cipher_len]

    if counter <= 0 or key_id != KEY_ID or created_at <= 0:
        raise ValueError("Metadata không hợp lệ")
    if len(ciphertext) != cipher_len or 52 + cipher_len != len(signed):
        raise ValueError("Ciphertext length không hợp lệ")

    aad = AAD_PREFIX + struct.pack(">QIQ", counter, key_id, created_at) + salt + iv
    plaintext = AESGCM(derive_key(salt)).decrypt(iv, ciphertext, aad)
    text = plaintext.decode("utf-8-sig").strip()
    return text, counter

# ==============================================================================
# 2. BỘ LỌC PHIM, VOD, RADIO & BLV PHỦI
# ==============================================================================
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
    "box movie", "hollywood classics", "box hits", "music box", "woman"
]

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
    if any(p in s for p in VIETNAMESE_PROVINCES) or "dia phuong" in strip_accents(group):
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

# ==============================================================================
# 3. KIỂM TRA LUỒNG SỐNG CHUYÊN SÂU
# ==============================================================================
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
        attempts = 2 if "vietmitv.id.vn" in u else 1
        for attempt in range(attempts):
            ok, reason, latency, final_url = deep_test_stream(u, ua)
            if ok:
                item['best_url'] = u
                item['resolved_url'] = final_url
                item['status'] = reason
                item['latency'] = latency
                item['is_live'] = True
                return item
            if attempt < attempts - 1:
                time.sleep(0.3)
            
    item['best_url'] = urls[0]
    item['resolved_url'] = ""
    item['status'] = "DEAD"
    item['latency'] = 0
    item['is_live'] = False
    return item

# ==============================================================================
# 4. PARSER M3U CHO TỪNG NGUỒN
# ==============================================================================
def parse_m3u_text(text, source_tag):
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

# ==============================================================================
# 5. XỬ LÝ VÀ XUẤT FILE M3U RIÊNG CHO TỪNG NGUỒN
# ==============================================================================
def process_single_source(raw_channels, source_title, out_m3u_path):
    print(f"\n--- BẮT ĐẦU XỬ LÝ: {source_title} ({len(raw_channels)} kênh gốc) ---")
    
    unique_candidates = {}
    movie_junk_count = 0
    
    for item in raw_channels:
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
            unique_candidates[key] = {
                'key': key,
                'name': name,
                'target_group': target_group,
                'tvg_id': tvg_id,
                'logo': logo,
                'ua': item['ua'],
                'kodi': item['kodi'],
                'license': item['license'],
                'urls': [url]
            }
        else:
            if url not in unique_candidates[key]['urls']:
                unique_candidates[key]['urls'].append(url)
            if not unique_candidates[key]['kodi'] and item['kodi']:
                unique_candidates[key]['kodi'] = True
            if not unique_candidates[key]['license'] and item['license']:
                unique_candidates[key]['license'] = item['license']

    print(f"  • Đã loại bỏ link phim, VOD và rác: {movie_junk_count} mục")
    print(f"  • Kênh duy nhất sau khi xoá trùng lặp: {len(unique_candidates)} kênh")
    
    # Kiểm tra luồng sống
    print(f"  • Đang kiểm tra link sống...")
    with ThreadPoolExecutor(max_workers=8) as executor:
        tested_results = list(executor.map(verify_channel_item, unique_candidates.values()))
        
    live_channels = [ch for ch in tested_results if ch['is_live']]
    dead_channels = [ch for ch in tested_results if not ch['is_live']]
    
    print(f"  • Kênh sống (LIVE): {len(live_channels)} | Kênh chết (DEAD): {len(dead_channels)}")
    
    # Phân bổ vào 6 nhóm theo đúng thứ tự
    grouped = {g: [] for g in ORDERED_GROUPS}
    for ch in live_channels:
        g = ch['target_group']
        grouped[g].append(ch)
        
    final_playlist = []
    print("  • Phân nhóm theo thứ tự chuẩn:")
    for g in ORDERED_GROUPS:
        chs = grouped[g]
        print(f"    {ORDERED_GROUPS.index(g)+1}. {g}: {len(chs)} kênh")
        final_playlist.extend(chs)
        
    # Tạo nội dung M3U
    m3u_lines = [
        EPG_HEADER,
        f'#PLAYLIST: NVC Tivi - {source_title}',
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
        
    with open(out_m3u_path, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))
    print(f"  => Xuất thành công: {out_m3u_path} ({len(final_playlist)} kênh sống)")
    return final_playlist, grouped

# ==============================================================================
# 6. TẢI VÀ CHẠY TOÀN BỘ 3 NGUỒN
# ==============================================================================
def download_url(url, is_binary=False):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15, context=CTX) as r:
        data = r.read()
    return data if is_binary else data.decode('utf-8', errors='ignore')

def main():
    print("=" * 80)
    print("⚡ NVC TIVI - TỰ ĐỘNG TỔNG HỢP VÀ TẠO 3 FILE M3U RIÊNG CHO 3 NGUỒN")
    print("=" * 80)

    # 1. NGUỒN 1: vxm.enc (giải mã AES-GCM)
    print("\n[NGUỒN 1] Đang tải và giải mã vxm.enc từ vietng228...")
    SRC1_URL = "https://github.com/vietng228/m3u/raw/refs/heads/main/vxm.enc"
    try:
        vxm_bytes = download_url(SRC1_URL, is_binary=True)
        vxm_text, counter = decrypt_vxm(vxm_bytes)
        print(f"  -> Giải mã thành công vxm.enc (Counter: {counter})")
        src1_channels = parse_m3u_text(vxm_text, "Nguồn 1 - VXM")
    except Exception as e:
        print(f"  -> Lỗi giải mã Nguồn 1 ({e}), thử đọc file cục bộ nếu có...")
        if os.path.exists("vxm_decrypted_(1).m3u"):
            text = Path("vxm_decrypted_(1).m3u").read_text(encoding="utf-8")
            src1_channels = parse_m3u_text(text, "Nguồn 1 - VXM Cục Bộ")
        else:
            src1_channels = []

    # 2. NGUỒN 2: all.m3u (IPTV-Auto)
    print("\n[NGUỒN 2] Đang tải all.m3u từ minhtan001/IPTV-Auto...")
    SRC2_URL = "https://raw.githubusercontent.com/minhtan001/IPTV-Auto/refs/heads/playlists/all.m3u"
    try:
        all_text = download_url(SRC2_URL)
        src2_channels = parse_m3u_text(all_text, "Nguồn 2 - IPTV-Auto")
    except Exception as e:
        print(f"  -> Lỗi tải Nguồn 2: {e}")
        src2_channels = []

    # 3. NGUỒN 3: vmttv (VMTTV)
    print("\n[NGUỒN 3] Đang tải vmttv từ vuminhthanh12...")
    SRC3_URL = "https://raw.githubusercontent.com/vuminhthanh12/vuminhthanh12/main/vmttv"
    try:
        vmttv_text = download_url(SRC3_URL)
        src3_channels = parse_m3u_text(vmttv_text, "Nguồn 3 - VMTTV")
    except Exception as e:
        print(f"  -> Lỗi tải Nguồn 3: {e}")
        src3_channels = []

    # XỬ LÝ VÀ XUẤT 3 FILE M3U RIÊNG BIỆT
    list1, grp1 = process_single_source(src1_channels, "Nguồn 1 (VXM)", "nvctivi_source1.m3u")
    list2, grp2 = process_single_source(src2_channels, "Nguồn 2 (IPTV-Auto)", "nvctivi_source2.m3u")
    list3, grp3 = process_single_source(src3_channels, "Nguồn 3 (VMTTV)", "nvctivi_source3.m3u")

    # TẠO FILE TỔNG HỢP MASTER (NVCTIVI.M3U) TỪ CẢ 3 NGUỒN
    print("\n" + "=" * 80)
    print("🌟 ĐỒNG BỘ PLAYLIST TỔNG HỢP TOÀN DIỆN (nvctivi.m3u)")
    print("=" * 80)
    # Gộp 3 nguồn theo thứ tự ưu tiên: Nguồn 1 > Nguồn 3 > Nguồn 2
    combined_raw = src1_channels + src3_channels + src2_channels
    master_live, grp_master = process_single_source(combined_raw, "Tổng Hợp Toàn Bộ 3 Nguồn", "nvctivi.m3u")

    # Cập nhật proxy M3U
    proxy_lines = [
        EPG_HEADER,
        '#PLAYLIST: NVC Tivi - Truyền Hình Việt Nam & Quốc Tế Chuẩn Link Sống',
        '#AUTHOR: NVC Tivi Development Team',
        ''
    ]
    for ch in master_live:
        extinf = f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}" tvg-name="{ch["name"]}" tvg-logo="{ch["logo"]}" group-title="{ch["target_group"]}",{ch["name"]}'
        proxy_lines.append(extinf)
        if ch.get("ua"): proxy_lines.append(f'#EXTVLCOPT:http-user-agent={ch["ua"]}')
        if ch.get("kodi"): proxy_lines.append('#KODIPROP:inputstream.adaptive.manifest_type=hls')
        if ch.get("license"): proxy_lines.append(f'#KODIPROP:inputstream.adaptive.license_key={ch["license"]}')
        proxy_url = f"https://nvctivi-stream.workers.dev/channel?group={urllib.parse.quote(ch['target_group'])}&name={urllib.parse.quote(ch['name'])}"
        proxy_lines.append(proxy_url)
        proxy_lines.append('')
    with open("nvctivi_proxy.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(proxy_lines))

    # Cập nhật JSON API
    json_data = {
        "app": "NVC Tivi",
        "version": "2.0.0",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_channels": len(master_live),
        "source1_channels": len(list1),
        "source2_channels": len(list2),
        "source3_channels": len(list3),
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
            for ch in master_live
        ]
    }
    with open("nvctivi_channels.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    # Cập nhật REPORT_LIVE_CHANNELS.md
    report_lines = [
        "# Báo Cáo Tổng Hợp 3 Nguồn Kênh Truyền Hình NVC Tivi",
        f"\n- **Thời gian xử lý:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Nguồn 1 (VXM decrypted):** **{len(list1)} kênh sống** (`nvctivi_source1.m3u`)",
        f"- **Nguồn 2 (IPTV-Auto):** **{len(list2)} kênh sống** (`nvctivi_source2.m3u`)",
        f"- **Nguồn 3 (VMTTV):** **{len(list3)} kênh sống** (`nvctivi_source3.m3u`)",
        f"- **Playlist Master Tổng Hợp:** **{len(master_live)} kênh sống** (`nvctivi.m3u`)",
        f"- **EPG tích hợp:** `https://epgvn.vercel.app/epg.xml`, `https://epg.io.vn/epgc.xml`",
        f"- **Đường dẫn Logo chuẩn:** `{LOGO_BASE}/`",
        "\n## Bảng thống kê phân nhóm theo thứ tự chuẩn 6 nhóm:\n",
        "| STT | Nhóm Kênh | Nguồn 1 (VXM) | Nguồn 2 (IPTV-Auto) | Nguồn 3 (VMTTV) | Master Tổng Hợp |",
        "|:---:|:---|:---:|:---:|:---:|:---:|"
    ]
    for idx, g in enumerate(ORDERED_GROUPS, 1):
        c1 = len(grp1.get(g, []))
        c2 = len(grp2.get(g, []))
        c3 = len(grp3.get(g, []))
        cm = len(grp_master.get(g, []))
        report_lines.append(f"| {idx} | **{g}** | {c1} | {c2} | {c3} | {cm} |")
    report_lines.append(f"| **Tổng** | **Tất cả các nhóm** | **{len(list1)}** | **{len(list2)}** | **{len(list3)}** | **{len(master_live)}** |")
    report_lines.append("\n---\n")

    with open("REPORT_LIVE_CHANNELS.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    # Tự động mã hoá & đồng bộ nvc.enc
    try:
        sys.path.insert(0, os.path.abspath("scripts"))
        from update import sync as sync_update
        print("\n[ĐỒNG BỘ NVC.ENC] Đang mã hoá nvc.enc từ nvctivi.m3u...")
        sync_update()
    except Exception as e:
        print(f"Cảnh báo: Không thể tự động đồng bộ nvc.enc ({e})")

    print("\n-> Đã cập nhật xong tất cả 3 file nguồn + file master + nvc.enc + báo cáo.")

if __name__ == "__main__":
    main()
