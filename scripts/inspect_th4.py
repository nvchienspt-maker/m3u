import sys
sys.stdout.reconfigure(encoding='utf-8')
from parse_all_sources import parse_m3u_file

s1 = parse_m3u_file("source_all.m3u", "IPTV-Auto")

th3 = [x for x in s1 if x['group'] == 'TruyenHinh_3']
th4 = [x for x in s1 if x['group'] == 'TruyenHinh_4']

print(f"Total in TruyenHinh_3: {len(th3)}")
print(f"Total in TruyenHinh_4: {len(th4)}")

print("\nSample 20 from TruyenHinh_4:")
for x in th4[:20]:
    print(f"  {x['name']} -> {x['url'][:60]}")

