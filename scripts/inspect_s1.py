import sys
sys.stdout.reconfigure(encoding='utf-8')

from test_classifier import is_movie_or_junk, classify_group
from parse_all_sources import parse_m3u_file

s1 = parse_m3u_file("source_all.m3u", "IPTV-Auto")
s2 = parse_m3u_file("source_vmttv.m3u", "VMTTV")
s3 = parse_m3u_file(r"C:/Users/ADMIN/.gemini/antigravity/brain/00f23127-e01e-43b1-89dc-d1934fab81e7/.user_uploaded/media_1793336516800_1f042b9f.m3u", "VXM-Uploaded")

print("\n--- SAMPLE 50 FROM source_all.m3u ---")
for item in s1[100:150]:
    print(f"  [{item['group']}] {item['name']} -> {item['url'][:50]}")

