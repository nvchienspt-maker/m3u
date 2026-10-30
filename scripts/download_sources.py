import urllib.request
import ssl
import sys

sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl._create_unverified_context()

def download(url, out_name):
    print(f"Downloading {url} ...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        content = r.read().decode('utf-8', errors='ignore')
    with open(out_name, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"-> Saved {out_name}: {len(content.splitlines())} lines, {len(content)} bytes")

download("https://raw.githubusercontent.com/minhtan001/IPTV-Auto/refs/heads/playlists/all.m3u", "source_all.m3u")
download("https://raw.githubusercontent.com/vuminhthanh12/vuminhthanh12/main/vmttv", "source_vmttv.m3u")

