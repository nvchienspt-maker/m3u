import sys
sys.stdout.reconfigure(encoding='utf-8')
from test_clean_aggregation import unique

for g in ["VTV", "VTVCab", "HTV", "SCTV"]:
    chs = [c for c in unique.values() if c['group'] == g]
    print(f"\nGroup {g} ({len(chs)} channels):")
    for c in chs:
        print(f"  {c['name']} (key: {c.get('key', '')}) [URLs: {len(c['urls'])}]")

