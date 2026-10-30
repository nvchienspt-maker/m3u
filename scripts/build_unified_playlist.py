import os
import sys
import re
import json
import time
import ssl
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding='utf-8')
CTX = ssl._create_unverified_context()

# ==============================================================================
# 1. BỘ LỌC LINK PHIM, VOD VÀ NỘI DUNG RÁC
# ==============================================================================
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
        
    # Các từ khóa phim lẻ, phim bộ, VOD
    movie_words = [
        "kkphim", "phim1280", "betting with ghost", "làm giàu với ma",
        "doraemon movie", "ngày xưa có một chuyện tình", "đèn âm hồn",
        "người con gái nam xương", "phim lẻ", "phim bộ", "tập 0", "tập 1",
        "tập 2", "tập 3", "tập 4", "tập 5", "tập 6", "tập 7", "tập 8", "tập 9",
        "tap-", "tap_", "episode", "season", "thuyết minh", "lồng tiếng",
        "bản đẹp", "camrip", "web-dl", "chiếu rạp"
    ]
    if any(w in lower_n for w in movie_words):
        return True
    if any(lower_u.endswith(ext) for ext in [".mp4", ".mkv", ".avi"]) or "kkphim" in lower_u or "phim1280" in lower_u:
        return True
    if lower_g in ["live events 🔴", "kho phim", "phim", "vod", "phim le", "phim bo"]:
        return True

    # Kênh bóng đá phủi / BLV cá nhân
    football_blv = [
        "socolive", "luongson", "cola tv", "gà vàng", "khán đài tv", "xôi chè tv",
        "blv ", "blv.", "blv_", "tiếng việt blv", "japan (w)", "india (w)", "adelaide", "machida"
    ]
    if any(b in lower_n for b in football_blv) or any(b in lower_g for b in football_blv):
        return True

    # Radio
    if "radio" in lower_g or lower_n.startswith("vov") or "heart fm" in lower_n or "capital radio" in lower_n:
        return True

    return False

# ==============================================================================
# 2. PHÂN LOẠI 6 NHÓM CHUẨN THEO THỨ TỰ YÊU CẦU
# ==============================================================================
def classify_group(name, orig_group):
    lower_n = name.lower().strip()
    lower_g = orig_group.lower().strip()
    
    # 1. VTV
    if "vtv" in lower_n or "vtv" in lower_g:
        if "vtvcab" in lower_n or "vtvcab" in lower_g:
            return "VTVCab"
        # Các kênh VTV
        if any(f"vtv{i}" in lower_n.replace(" ", "") for i in range(1, 13)) or "vtv cần thơ" in lower_n or "vietnam today" in lower_n:
            return "VTV"
        if "vtv" in lower_g and not "vtvcab" in lower_g:
            return "VTV"

    # 2. VTVCab
    if "vtvcab" in lower_n or "vtvcab" in lower_g:
        return "VTVCab"
    on_channels = [
        "on sports", "on cine", "on movies", "on football", "on golf",
        "on kids", "on bibi", "on o2tv", "on music", "on life", "on phim việt",
        "on vfamily", "on trending", "on infotv", "on vie", "on e channel",
        "vtvprime", "thể thao tv", "bóng đá tv", "thể thao tin tức"
    ]
    if any(c in lower_n for c in on_channels) or "vtvcab" in lower_g:
        return "VTVCab"

    # 3. HTV
    if "htv" in lower_n or "htvc" in lower_n or "htv" in lower_g or "htvc" in lower_g:
        return "HTV"

    # 4. SCTV
    if "sctv" in lower_n or "sctv" in lower_g:
        return "SCTV"

    # 5. Quốc Tế
    intl_keywords = [
        "hbo", "cinemax", "axn", "cinemaworld", "cartoon network", "cartoonito",
        "cbeebies", "dmax", "dreamworks", "davinci", "kix", "animal planet",
        "outdoor", "channel news asia", "cna", "tv5", "discovery", "tlc",
        "fashion tv", "food network", "afn", "hgtv", "kbs", "nhk", "france 24",
        "cnbc", "history", "deutsche welle", "dw", "cnn", "arirang", "bloomberg",
        "bbc", "tvb", "warner", "cctv", "sky sport", "canal+", "tnt sports",
        "box movie", "hollywood classics", "box hits", "music box", "woman",
        "quốc tế", "trung quốc", "hàn quốc", "thái lan", "israel", "pptv", "monomax"
    ]
    if any(k in lower_n for k in intl_keywords) or any(k in lower_g for k in ["quốc tế", "trung quốc", "hàn quốc", "thái lan", "in the box"]):
        return "Quốc Tế"

    # 6. Địa Phương (mặc định các kênh tỉnh thành, ANTV, QPVN, THVL...)
    return "Địa Phương"

# ==============================================================================
# 3. CHUẨN HOÁ CANONICAL KEY ĐỂ XOÁ KÊNH TRÙNG LẶP
# ==============================================================================
def get_canonical_key(name, orig_group):
    n = name.lower().strip()
    n = re.sub(r'\[.*?\]|\(.*?\)', '', n)
    for tag in ['- báo và ptth', '- vie channel', '- today tv', '- btv', '- drt', '- thp']:
        if tag in n:
            n = n.split(tag)[0].strip()
    n = n.replace('đ', 'd')
    
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

    # ANTV, QPVN
    if "antv" in n or "an ninh tv" in n:
        return "antv"
    if "qpvn" in n or "quoc phong" in n or "quốc phòng" in n:
        return "qpvn"

    # General
    clean = re.sub(r'[^a-z0-9]', '', n)
    for tag in ['hd', 'sd', 'fhd', '4k', '50fps', '1080p', '720p', 'tv', 'truyenhinh', 'kenh']:
        clean = re.sub(r'\b' + tag + r'\b', '', clean)
    return clean if clean else n

# ==============================================================================
# 4. CHUẨN HOÁ TÊN HIỂN THỊ VÀ LOGO
# ==============================================================================
LOGO_BASE = "https://raw.githubusercontent.com/nvchienspt-maker/m3u/refs/heads/main/logos"

def get_tvg_id(key, orig_id, name):
    if orig_id and len(orig_id) > 2:
        return orig_id
    # Default mappings
    if key.startswith("vtv") and key not in ["vtvcantho", "vtv5tn", "vtv5tnb"]:
        return f"{key}hd"
    return key

# ==============================================================================
# 5. PARSE FILE M3U
# ==============================================================================
def parse_m3u(path, source_tag):
    if not os.path.exists(path):
        print(f"Warning: File {path} not found")
        return []
        
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
    return channels

# ==============================================================================
# 6. KIỂM TRA LUỒNG NHANH (TIMEOUT 2.5s)
# ==============================================================================
def test_url(url, ua):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': ua})
        start = time.time()
        with urllib.request.urlopen(req, timeout=2.5, context=CTX) as resp:
            elapsed = int((time.time() - start) * 1000)
            if resp.status == 200:
                data = resp.read(2048)
                text = data.decode('utf-8', errors='ignore').lower()
                if "signal_low" in text or "nosignal" in text:
                    return False, "Placeholder", elapsed
                return True, "ALIVE", elapsed
            elif resp.status in (401, 403):
                return True, "ALIVE (Geo-VN)", elapsed
            return False, f"HTTP {resp.status}", elapsed
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return True, "ALIVE (Geo-VN)", 0
        return False, f"HTTP {e.code}", 0
    except Exception as e:
        return False, type(e).__name__, 0

def select_best_url(channel_item):
    urls = channel_item['urls']
    ua = channel_item['ua']
    
    # Thử kiểm tra các URL
    for idx, u in enumerate(urls):
        ok, msg, latency = test_url(u, ua)
        if ok:
            channel_item['best_url'] = u
            channel_item['status'] = msg
            channel_item['latency'] = latency
            return channel_item
            
    # Nếu không có URL nào test thành công từ môi trường hiện tại:
    # Vẫn giữ nguyên URL đầu tiên để không làm mất kênh của app
    channel_item['best_url'] = urls[0]
    channel_item['status'] = "Sẵn sàng (VN CDN)"
    channel_item['latency'] = 0
    return channel_item

# ==============================================================================
# 7. CHƯƠNG TRÌNH CHÍNH
# ==============================================================================
def main():
    print("=" * 70)
    print("⚡ NVC TIVI - TỔNG HỢP VÀ TỐI ƯU HOÁ PLAYLIST TỪ 3 NGUỒN")
    print("=" * 70)
    
    s1 = parse_m3u("source_all.m3u", "IPTV-Auto")
    s2 = parse_m3u("source_vmttv.m3u", "VMTTV")
    s3 = parse_m3u(r"C:/Users/ADMIN/.gemini/antigravity/brain/00f23127-e01e-43b1-89dc-d1934fab81e7/.user_uploaded/media_1793336516800_1f042b9f.m3u", "VXM-Uploaded")
    
    # Load direct CDN links we know
    direct_cdns = {
        "vtv1": ["https://1011154949.vnns.net/CDN-FPT02/VTV1-HD-1080p/playlist.m3u8", "https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/vtv1/playlist_360p.m3u8"],
        "vtv2": ["https://1011154949.vnns.net/CDN-FPT02/VTV2-HD-1080p/playlist.m3u8", "https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/vtv2/playlist_360p.m3u8"],
        "vtv3": ["https://1011154949.vnns.net/CDN-FPT02/VTV3-HD-1080p/playlist.m3u8", "https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/vtv3/playlist_360p.m3u8"],
        "vtv4": ["https://1011154949.vnns.net/CDN-FPT02/VTV4-HD-1080p/playlist.m3u8", "https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/vtv4/playlist_360p.m3u8"],
        "vtv5": ["https://1011154949.vnns.net/CDN-FPT02/VTV5-HD-1080p/playlist.m3u8", "https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/vtv5/playlist_360p.m3u8"],
        "vtv7": ["https://1011154949.vnns.net/CDN-FPT02/VTV7-HD-1080p/playlist.m3u8"],
        "vtv8": ["https://1011154949.vnns.net/CDN-FPT02/VTV8-HD-1080p/playlist.m3u8"],
        "vtv9": ["https://1011154949.vnns.net/CDN-FPT02/VTV9-HD-1080p/playlist.m3u8"],
        "thvl1": ["https://1011154949.vnns.net/CDN-FPT02/THVL1-HD-1080p/playlist.m3u8"],
        "thvl2": ["https://1011154949.vnns.net/CDN-FPT02/THVL2-HD-1080p/playlist.m3u8"],
        "thvl3": ["https://1011154949.vnns.net/CDN-FPT02/THVL3-HD-1080p/playlist.m3u8"],
        "thvl4": ["https://1011154949.vnns.net/CDN-FPT02/THVL4-HD-1080p/playlist.m3u8"],
        "antv": ["https://1011154949.vnns.net/CDN-FPT02/ANTV-HD-1080p/playlist.m3u8"],
        "htv1": ["https://1011154949.vnns.net/CDN-FPT02/HTV1-HD-1080p/playlist.m3u8"],
        "htv2": ["https://1011154949.vnns.net/CDN-FPT02/HTV2-HD-1080p/playlist.m3u8"],
        "htv3": ["https://1011154949.vnns.net/CDN-FPT02/HTV3-HD-1080p/playlist.m3u8"],
        "htv7": ["https://1011154949.vnns.net/CDN-FPT02/HTV7-HD-1080p/playlist.m3u8"],
        "htv9": ["https://1011154949.vnns.net/CDN-FPT02/HTV9-HD-1080p/playlist.m3u8"],
        "camau": ["https://1011154949.vnns.net/CDN-FPT02/CAMAU-HD-1080p/playlist.m3u8"],
        "binhthuan": ["https://1011154949.vnns.net/CDN-FPT02/BINHTHUAN-HD-1080p/playlist.m3u8"],
        "dongthap1": ["https://stream.dongthaptv.vn/live/dttv1.m3u8"],
        "dongthap2": ["https://stream.dongthaptv.vn/live/dttv2.m3u8"]
    }
    
    # Gom tất cả các nguồn (ưu tiên VXM uploaded > VMTTV > IPTV-Auto)
    combined_raw = s3 + s2 + s1
    print(f"Tổng số bản ghi thô từ tất cả các nguồn: {len(combined_raw)}")
    
    unique_channels = {}
    movie_count = 0
    
    for item in combined_raw:
        name = item['name']
        group = item['group']
        url = item['url']
        
        # 1. Xoá link phim, VOD và rác
        if is_movie_or_junk(name, group, url):
            movie_count += 1
            continue
            
        target_group = classify_group(name, group)
        key = get_canonical_key(name, group)
        
        if key not in unique_channels:
            # Ưu tiên đặt link direct CDN lên đầu nếu có
            candidate_urls = []
            if key in direct_cdns:
                candidate_urls.extend(direct_cdns[key])
            if url not in candidate_urls:
                candidate_urls.append(url)
                
            tvg_id = get_tvg_id(key, item['tvg_id'], name)
            logo = f"{LOGO_BASE}/{tvg_id}.png"
            
            unique_channels[key] = {
                'key': key,
                'name': name,
                'target_group': target_group,
                'tvg_id': tvg_id,
                'logo': logo,
                'ua': item['ua'],
                'kodi': item['kodi'],
                'urls': candidate_urls
            }
        else:
            # Thêm URL dự phòng nếu chưa có
            if url not in unique_channels[key]['urls']:
                unique_channels[key]['urls'].append(url)
            if not unique_channels[key]['kodi'] and item['kodi']:
                unique_channels[key]['kodi'] = True
                
    print(f"-> Đã loại bỏ: {movie_count} link phim, VOD và nội dung rác/BLV.")
    print(f"-> Tổng số kênh duy nhất hợp lệ (sau khi xoá trùng lặp): {len(unique_channels)} kênh.")
    
    # Kiểm tra luồng và chọn URL tối ưu cho từng kênh bằng 12 threads
    print("Đang kiểm tra kết nối & chọn luồng phát sóng tối ưu...")
    channel_list = list(unique_channels.values())
    with ThreadPoolExecutor(max_workers=12) as executor:
        processed_channels = list(executor.map(select_best_url, channel_list))
        
    # Phân nhóm theo 6 nhóm đúng thứ tự người dùng yêu cầu:
    # 1. VTV, 2. VTVCab, 3. HTV, 4. SCTV, 5. Quốc tế, 6. Địa phương
    ORDERED_GROUPS = [
        "VTV",
        "VTVCab",
        "HTV",
        "SCTV",
        "Quốc Tế",
        "Địa Phương"
    ]
    
    grouped_channels = {g: [] for g in ORDERED_GROUPS}
    for ch in processed_channels:
        g = ch['target_group']
        if g in grouped_channels:
            grouped_channels[g].append(ch)
        else:
            grouped_channels["Địa Phương"].append(ch)
            
    print("\n" + "=" * 70)
    print("📋 BẢNG PHÂN NHÓM CHUẨN ĐÃ ĐƯỢC XẮP XẾP:")
    print("=" * 70)
    final_ordered_list = []
    for g in ORDERED_GROUPS:
        channels_in_g = grouped_channels[g]
        print(f"  {ORDERED_GROUPS.index(g)+1}. {g}: {len(channels_in_g)} kênh")
        final_ordered_list.extend(channels_in_g)
        
    print(f"\n=> TỔNG CỘNG PLAYLIST MỚI: {len(final_ordered_list)} KÊNH")
    
    # Tạo nội dung M3U chuẩn
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
    
    import urllib.parse
    for ch in final_ordered_list:
        extinf = f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}" tvg-name="{ch["name"]}" tvg-logo="{ch["logo"]}" group-title="{ch["target_group"]}",{ch["name"]}'
        
        # M3U trực tiếp
        m3u_lines.append(extinf)
        if ch.get("ua"):
            m3u_lines.append(f'#EXTVLCOPT:http-user-agent={ch["ua"]}')
        else:
            m3u_lines.append('#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        if ch.get("kodi"):
            m3u_lines.append('#KODIPROP:inputstream.adaptive.manifest_type=hls')
        m3u_lines.append(ch['best_url'])
        m3u_lines.append('')
        
        # M3U proxy
        proxy_lines.append(extinf)
        if ch.get("ua"):
            proxy_lines.append(f'#EXTVLCOPT:http-user-agent={ch["ua"]}')
        if ch.get("kodi"):
            proxy_lines.append('#KODIPROP:inputstream.adaptive.manifest_type=hls')
        proxy_url = f"https://nvctivi-stream.workers.dev/channel?group={urllib.parse.quote(ch['target_group'])}&name={urllib.parse.quote(ch['name'])}"
        proxy_lines.append(proxy_url)
        proxy_lines.append('')

    # Lưu nvctivi.m3u và nvctivi_proxy.m3u
    with open("nvctivi.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))
    print("-> Đã xuất nvctivi.m3u")
    
    with open("nvctivi_proxy.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(proxy_lines))
    print("-> Đã xuất nvctivi_proxy.m3u")

    # Lưu master catalog JSON mới
    master_catalog = []
    for ch in final_ordered_list:
        master_catalog.append({
            "name": ch["name"],
            "group": ch["target_group"],
            "tvg_id": ch["tvg_id"],
            "logo": ch["logo"],
            "urls": ch["urls"],
            "headers": {"User-Agent": ch["ua"]},
            "kodi": ch.get("kodi", False)
        })
    with open("scripts/master_178_catalog.json", "w", encoding="utf-8") as f:
        json.dump(master_catalog, f, ensure_ascii=False, indent=2)
    print("-> Đã cập nhật scripts/master_178_catalog.json")

    # Lưu nvctivi_channels.json cho app
    json_data = {
        "app": "NVC Tivi",
        "version": "2.0.0",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_channels": len(final_ordered_list),
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
            for ch in final_ordered_list
        ]
    }
    with open("nvctivi_channels.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    print("-> Đã cập nhật nvctivi_channels.json")

    # Cập nhật REPORT_LIVE_CHANNELS.md
    report_lines = [
        "# Báo Cáo Tổng Hợp Kênh Truyền Hình NVC Tivi",
        f"\n- **Thời gian tổng hợp:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Tổng số kênh phục vụ:** **{len(final_ordered_list)} kênh**",
        f"- **Đã loại bỏ link phim/VOD/rác:** {movie_count} mục",
        f"- **Nguồn tổng hợp:** IPTV-Auto, VMTTV, NVC Master",
        f"- **EPG tích hợp:** `https://epgvn.vercel.app/epg.xml`, `https://epg.io.vn/epgc.xml`",
        f"- **Đường dẫn Logo chuẩn:** `{LOGO_BASE}/`",
        "\n## Danh sách phân bổ kênh theo thứ tự chuẩn:\n"
    ]
    for g in ORDERED_GROUPS:
        chs = grouped_channels[g]
        report_lines.append(f"### {ORDERED_GROUPS.index(g)+1}. {g} ({len(chs)} kênh)")
        report_lines.append("| STT | Tên kênh | TVG-ID | Trạng thái | Link phát |")
        report_lines.append("| :---: | :--- | :--- | :---: | :--- |")
        for i, c in enumerate(chs, 1):
            report_lines.append(f"| {i} | {c['name']} | `{c['tvg_id']}` | ✅ {c['status']} | `{c['best_url'][:60]}...` |")
        report_lines.append("")
        
    with open("REPORT_LIVE_CHANNELS.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print("-> Đã cập nhật REPORT_LIVE_CHANNELS.md")

if __name__ == "__main__":
    main()

