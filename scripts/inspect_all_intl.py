import sys
sys.stdout.reconfigure(encoding='utf-8')
from test_clean_aggregation import unique

chs = [c for c in unique.values() if c['group'] == "Quốc Tế"]
print(f"Total in Quốc Tế: {len(chs)}")
for c in chs:
    print(f"  {c['name']} (key: {c.get('key', '')})")

