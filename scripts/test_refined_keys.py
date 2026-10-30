import re
import sys
import unicodedata

sys.stdout.reconfigure(encoding='utf-8')

def strip_accents(text):
    text = text.replace('đ', 'd').replace('Đ', 'D')
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower()

def clean_channel_name(name):
    n = name.strip()
    if ' - Báo và PTTH' in n:
        n = n.split(' - Báo và PTTH')[0].strip()
    if ' - Vie Channel' in n:
        n = n.split(' - Vie Channel')[0].strip()
    if ' - TODAY TV' in n:
        n = n.split(' - TODAY TV')[0].strip()
    if ' | ' in n:
        n = n.split(' | ')[0].strip()
    return n

def get_refined_key(name, group):
    s = strip_accents(clean_channel_name(name)).replace("+", "plus")
    g = strip_accents(group).replace("+", "plus")
    
    # 1. VTV
    if "vtv" in s and "vtvcab" not in s and "vtvprime" not in s:
        vtv_m = re.search(r'\bvtv\s*([0-9]+)\b', s)
        if vtv_m:
            return f"vtv{vtv_m.group(1)}"
        if "can tho" in s:
            return "vtvcantho"
        if "5" in s:
            if "tay nguyen" in s:
                return "vtv5tn"
            if "tay nam bo" in s:
                return "vtv5tnb"
            return "vtv5"
        if "vietnam today" in s:
            return "vietnamtoday"
            
    # 2. VTVCab
    if "vtvcab" in s or "vtvcab" in g or "vtvprime" in s:
        p_m = re.search(r'vtvprime\s*([0-9]+)', s)
        if p_m:
            return f"vtvprime_{p_m.group(1)}"
            
    on_m = re.search(r'\bon\s+([a-z0-9\+]+)', s)
    if on_m:
        sub = on_m.group(1).replace('+', 'plus').replace(' ', '')
        for tag in ['hd', 'sd', '50fps', 'tv']:
            sub = re.sub(r'\b' + tag + r'\b', '', sub)
        return f"on_{sub}"

    # 3. HTV & HTVC
    if "htvc" in s:
        sub = s.replace("htvc", "").strip()
        sub = re.sub(r'\b(hd|sd|plus|\+)\b', '', sub).strip().replace(" ", "")
        if "thuan viet" in s: return "htvc_thuanviet"
        if "gia dinh" in s: return "htvc_giadinh"
        if "phu nu" in s: return "htvc_phunu"
        if "du lich" in s: return "htvc_dulich"
        if "phim" in s: return "htvc_phim"
        if "ca nhac" in s: return "htvc_canhac"
        if "plus" in s or "+" in s: return "htvc_plus"
        return f"htvc_{sub}" if sub else "htvc"
        
    htv_m = re.search(r'\bhtv\s*([0-9]+)\b', s)
    if htv_m:
        return f"htv{htv_m.group(1)}"
    if "htv the thao" in s: return "htvthethao"
    if "htv key" in s: return "htvkey"

    # 4. SCTV
    sctv_m = re.search(r'\bsctv\s*([0-9]+)\b', s)
    if sctv_m:
        return f"sctv{sctv_m.group(1)}"
    if "sctv 4k" in s or "sctv4k" in s: return "sctv4k"
    if "sctv" in s and ("phim tong hop" in s or "pth" in s or "dan toc" in s):
        return "sctvhdpth"

    # 5. Quốc Tế nổi tiếng
    if "hbo hits" in s: return "hbo_hits"
    if "hbo family" in s: return "hbo_family"
    if "hbo signature" in s: return "hbo_signature"
    if "hbo" in s: return "hbo"
    if "cinemax" in s or "max" in s and "pkg20" in s: return "cinemax"
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
    if cctv_m:
        return f"cctv_{cctv_m.group(1).replace('+', 'plus')}"

    # 6. Địa Phương (Tỉnh thành VN)
    # THVL
    thvl_m = re.search(r'(thvl|vinh long)\s*([0-9]+)', s)
    if thvl_m:
        return f"thvl{thvl_m.group(2)}"
    # Hà Nội
    hn_m = re.search(r'(ha noi|hanoi)\s*([0-9]+)', s)
    if hn_m:
        return f"hanoi{hn_m.group(2)}"
    # Cần Thơ
    ct_m = re.search(r'(can tho|cantho)\s*([0-9]+)', s)
    if ct_m:
        return f"cantho{ct_m.group(2)}"
    # Đà Nẵng
    dn_m = re.search(r'(da nang|danang)\s*([0-9]+)', s)
    if dn_m:
        return f"danang{dn_m.group(2)}"
    # Đồng Nai
    dnai_m = re.search(r'(dong nai|dnrtv)\s*([0-9]+)', s)
    if dnai_m:
        return f"dongnai{dnai_m.group(2)}"
    # Đồng Tháp
    dt_m = re.search(r'(dong thap)\s*([0-9]+)', s)
    if dt_m:
        return f"dongthap{dt_m.group(2)}"
    if "dong thap" in s:
        return "dongthap1"
    # An Giang
    ag_m = re.search(r'(an giang)\s*([0-9]+)', s)
    if ag_m:
        return f"angiang{ag_m.group(2)}"
    # Lâm Đồng
    ld_m = re.search(r'(lam dong)\s*([0-9]+)', s)
    if ld_m:
        return f"lamdong{ld_m.group(2)}"
    # Hải Phòng
    hp_m = re.search(r'(hai phong|thp)\s*([0-9]+)', s)
    if hp_m:
        return f"haiphong{hp_m.group(2)}"
    if "hai phong" in s or "thp" in s:
        return "haiphong1"
    # Khánh Hòa
    if "khanh hoa" in s:
        return "khanhhoa"
    # Đắk Lắk
    if "dak lak" in s or "drt" in s:
        return "daklak"
    # ANTV & QPVN
    if "antv" in s or "an ninh tv" in s:
        return "antv"
    if "qpvn" in s or "quoc phong" in s:
        return "qpvn"

    # General normalized token
    clean = re.sub(r'[^a-z0-9]', '', s)
    for tag in ['hd', 'sd', 'fhd', '4k', '50fps', '1080p', '720p', 'tv', 'truyenhinh', 'kenh']:
        clean = re.sub(r'\b' + tag + r'\b', '', clean)
    return clean if clean else s

tests = [
    ("HBO", "HBO HD"),
    ("BOX MOVIE 1 HD", "Box Movie 1"),
    ("WARNER TV HD", "Warner TV"),
    ("ASIAN FOOD NETWORK HD", "Asian Food Network"),
    ("HTVC Gia Đình", "HTVC GIA ĐÌNH"),
    ("SCTV14 - Kênh Phim Việt", "SCTV14"),
    ("Khánh Hòa", "Khánh Hòa 1"),
    ("Đồng Tháp", "Đồng Tháp 1"),
    ("Hải Phòng", "THP HD - Báo và PTTH Hải Phòng"),
    ("ON Sports +", "ON SPORTS+")
]
print("Refined key deduplication tests:")
for a, b in tests:
    ka = get_refined_key(a, "")
    kb = get_refined_key(b, "")
    print(f"  '{a}' ({ka}) == '{b}' ({kb}) -> {ka == kb}")
