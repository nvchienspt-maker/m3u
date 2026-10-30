import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('source_all.m3u', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
for idx in range(min(50, len(lines))):
    print(lines[idx].strip())

