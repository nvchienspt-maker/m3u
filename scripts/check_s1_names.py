import sys
sys.stdout.reconfigure(encoding='utf-8')
from parse_all_sources import parse_m3u_file

s1 = parse_m3u_file("source_all.m3u", "IPTV-Auto")

names = [x['name'] for x in s1]
print("Unique names in s1:", len(set(names)))
for name in list(set(names))[:30]:
    print("  ", name)

