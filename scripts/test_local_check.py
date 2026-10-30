import re
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

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
    combined = f"{name} {group}".lower()
    combined = combined.replace('đ', 'd')
    return any(p in combined for p in VIETNAMESE_PROVINCES)

print("Check local tests:")
for t in ["THP HD - Báo và PTTH Hải Phòng", "Vĩnh Long 1 HD", "ANTV HD", "Belarus 5", "MBC Busan", "西藏卫视", "Hà Nội 1"]:
    print(f"  '{t}' -> is_local: {is_vietnamese_local(t, 'Địa phương')}")

