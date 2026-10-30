import re
import sys
import json
from pathlib import Path
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding='utf-8')

# 1. Định nghĩa bộ lọc các link phim, VOD, bóng đá phủi tạm thời và rác
def is_movie_or_junk(name, group, url):
    lower_name = name.lower().strip()
    lower_group = group.lower().strip()
    lower_url = url.lower().strip()
    
    # Rác hoặc không có URL
    if not url or not url.startswith("http"):
        return True
    if lower_name in ["unknown", "test", "#extinf:-1"] or len(lower_name) < 2:
        return True
    if "quý khán giả theo dõi" in lower_name or "mật lệnh hoa sữa" in lower_name:
        return True
        
    # Phim lẻ, phim bộ, VOD, series
    movie_words = [
        "kkphim", "phim1280", "betting with ghost", "làm giàu với ma", 
        "doraemon movie", "ngày xưa có một chuyện tình", "đèn âm hồn", 
        "người con gái nam xương", "phim lẻ", "phim bộ", "tập 0", "tập 1", 
        "tập 2", "tập 3", "tập 4", "tập 5", "tập 6", "tập 7", "tập 8", "tập 9",
        "tap-", "tap_", "episode", "season", "thuyết minh", "lồng tiếng", 
        "bản đẹp", "camrip", "web-dl", "phim hoạt hình", "phim việt nam chiếu rạp"
    ]
    if any(w in lower_name for w in movie_words):
        return True
    if any(w in lower_url for w in [".mp4", ".mkv", ".avi", "kkphim", "phim1280"]):
        return True
    if lower_group in ["live events 🔴", "kho phim", "phim", "vod", "phim le", "phim bo"]:
        return True

    # Kênh bóng đá phủi / BLV cá nhân (chỉ giữ các kênh đài truyền hình thực thụ)
    football_blv = [
        "socolive", "luongson", "cola tv", "gà vàng", "khán đài tv", "xôi chè tv",
        "blv ", "blv.", "blv_", "tiếng việt blv"
    ]
    if any(b in lower_name for b in football_blv) or any(b in lower_group for b in football_blv):
        return True
        
    # Radio (người dùng yêu cầu IPTV truyền hình)
    if "radio" in lower_group or lower_name.startswith("vov") or "heart fm" in lower_name or "capital radio" in lower_name:
        return True
        
    return False

# 2. Định nghĩa quy tắc phân nhóm thành đúng 6 nhóm theo thứ tự:
# VTV, VTVCab, HTV, SCTV, Quốc tế, Địa phương
def classify_group(name, orig_group):
    lower_n = name.lower()
    lower_g = orig_group.lower()
    
    # 1. VTV
    if "vtv" in lower_n or "vtv" in lower_g:
        # Ngoại trừ VTVCab
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
        "vtvprime"
    ]
    if any(c in lower_n for c in on_channels):
        return "VTVCab"

    # 3. HTV & HTVC
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

    # 6. Địa Phương (mặc định các kênh tỉnh thành, ANTV, QPVN, Vĩnh Long...)
    return "Địa Phương"

print("Classify tests:")
for item in [("VTV1 HD", "VTV"), ("ON Sports+", "VTVcab"), ("HTV7 HD", "HTV"), ("SCTV14", "SCTV"), ("HBO HD", "Quốc Tế"), ("Vĩnh Long 1", "Địa Phương"), ("ANTV HD", "Địa Phương")]:
    print(f"  {item[0]} -> {classify_group(item[0], item[1])}")

