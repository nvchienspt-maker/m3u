import re
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

# Helper to normalize channel names for deduplication
def clean_name(name):
    # remove quality tags like HD, SD, 1080p, 720p, 50fps, FHD, 4K
    n = name.strip()
    # remove trailing annotations like "- Báo và PTTH..." or "- Vie Channel"
    if ' - ' in n:
        n = n.split(' - ')[0].strip()
    if ' | ' in n:
        n = n.split(' | ')[0].strip()
    return n

def get_channel_key(name):
    n = clean_name(name).lower()
    for tag in ['hd', 'sd', 'fhd', '4k', '50fps', '1080p', '720p', 'tv', 'truyền hình', 'báo và ptth']:
        n = re.sub(r'\b' + tag + r'\b', '', n)
    n = re.sub(r'[^a-z0-9]', '', n)
    return n

print("Clean name sample:")
for test in ["VTV1 HD", "VTV1", "HTV1 - Báo và PTTH Thành Phố Hồ Chí Minh", "HTV2 - Vie Channel", "SCTV2 - TODAY TV"]:
    print(f"  '{test}' -> clean: '{clean_name(test)}' -> key: '{get_channel_key(test)}'")

