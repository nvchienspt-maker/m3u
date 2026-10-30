import re
import sys
import json
import unicodedata

sys.stdout.reconfigure(encoding='utf-8')

from parse_all_sources import parse_m3u_file

def strip_accents(text):
    text = text.replace('đ', 'd').replace('Đ', 'D')
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower()

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

def is_vietnamese_local(name, group):
    s = strip_accents(f"{name} {group}")
    return any(p in s for p in VIETNAMESE_PROVINCES)

INTL_KEYWORDS = [
    "hbo", "cinemax", "axn", "cinemaworld", "cartoon network", "cartoonito",
    "cbeebies", "dmax", "dreamworks", "davinci", "kix", "animal planet",
    "outdoor", "channel news asia", "cna", "tv5", "discovery", "tlc",
    "fashion tv", "food network", "afn", "hgtv", "kbs", "nhk", "france 24",
    "cnbc", "history", "deutsche welle", "dw", "cnn", "arirang", "bloomberg",
    "bbc", "tvb", "warner", "cctv", "sky sport", "canal+", "tnt sports",
    "box movie", "hollywood classics", "box hits", "music box", "woman"
]

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
        "bản đẹp", "camrip", "web-dl", "chiếu rạp"
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

def classify(name, group):
    s = strip_accents(f"{name} {group}")
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
    if is_vietnamese_local(name, group):
        return "Địa Phương"

    # If it doesn't match any known TV channel, return None (ignore foreign junk / webcams)
    return None

s1 = parse_m3u_file("source_all.m3u", "IPTV-Auto")
s2 = parse_m3u_file("source_vmttv.m3u", "VMTTV")
s3 = parse_m3u_file(r"C:/Users/ADMIN/.gemini/antigravity/brain/00f23127-e01e-43b1-89dc-d1934fab81e7/.user_uploaded/media_1793336516800_1f042b9f.m3u", "VXM-Uploaded")

all_items = s3 + s2 + s1

from aggregate_test import get_canonical_key

unique = {}
ignored = 0
for item in all_items:
    name = item['name']
    group = item['group']
    url = item['url']
    
    if is_movie_or_junk(name, group, url):
        continue
        
    g = classify(name, group)
    if not g:
        ignored += 1
        continue
        
    k = get_canonical_key(name, group)
    if k not in unique:
        unique[k] = {
            'name': name,
            'group': g,
            'tvg_id': item['tvg_id'],
            'logo': item['logo'],
            'ua': item['ua'],
            'kodi': item['kodi'],
            'urls': [url]
        }
    else:
        if url not in unique[k]['urls']:
            unique[k]['urls'].append(url)

print(f"\n================ SUMMARY CLEAN CHANNELS ================")
print(f"Total valid TV channels: {len(unique)}")
print(f"Ignored non-TV / foreign junk: {ignored}")

groups = {"VTV": 0, "VTVCab": 0, "HTV": 0, "SCTV": 0, "Quốc Tế": 0, "Địa Phương": 0}
for ch in unique.values():
    groups[ch['group']] = groups.get(ch['group'], 0) + 1

for g in ["VTV", "VTVCab", "HTV", "SCTV", "Quốc Tế", "Địa Phương"]:
    print(f"  {g}: {groups[g]} kênh")

