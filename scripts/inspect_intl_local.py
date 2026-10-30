import sys
sys.stdout.reconfigure(encoding='utf-8')
from test_clean_aggregation import unique

for g in ["Quốc Tế", "Địa Phương"]:
    chs = [c for c in unique.values() if c['group'] == g]
    print(f"\nGroup {g} ({len(chs)} channels):")
    for c in chs[:30]:
        print(f"  {c['name']} [URLs: {len(c['urls'])}]")

