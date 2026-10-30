#!/usr/bin/env python3
"""
NVC Tivi - Master Channel Crawler & Live Validator
Chuyên gia crawl và chuẩn hoá dữ liệu các kênh truyền hình Việt Nam cho app NVC Tivi.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
import ssl
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding='utf-8')

# SSL context ignoring verification for regional CDNs
CTX = ssl._create_unverified_context()
TIMEOUT = 4.5

LOGO_BASE = "https://raw.githubusercontent.com/nvctivi/m3u/main/logos"

# Master Channel Database for NVC Tivi
CHANNEL_CATALOG = [
    # ==========================================
    # ⭐️ 1. VTV - KÊNH THIẾT YẾU QUỐC GIA
    # ==========================================
    {
        "name": "VTV1 HD",
        "group": "⭐️ VTV - Kênh Thiết Yếu",
        "tvg_id": "vtv1hd",
        "logo": f"{LOGO_BASE}/vtv1hd.png",
        "urls": [
            "https://1011154949.vnns.net/CDN-FPT02/VTV1-HD-1080p/playlist.m3u8",
            "https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/vtv1/playlist_360p.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "VTV2 HD",
        "group": "⭐️ VTV - Kênh Thiết Yếu",
        "tvg_id": "vtv2hd",
        "logo": f"{LOGO_BASE}/vtv2hd.png",
        "urls": [
            "https://1011154949.vnns.net/CDN-FPT02/VTV2-HD-1080p/playlist.m3u8",
            "https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/vtv2/playlist_360p.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "VTV3 HD",
        "group": "⭐️ VTV - Kênh Thiết Yếu",
        "tvg_id": "vtv3hd",
        "logo": f"{LOGO_BASE}/vtv3hd.png",
        "urls": [
            "https://1011154949.vnns.net/CDN-FPT02/VTV3-HD-1080p/playlist.m3u8",
            "https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/vtv3/playlist_360p.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "VTV4 HD",
        "group": "⭐️ VTV - Kênh Thiết Yếu",
        "tvg_id": "vtv4hd",
        "logo": f"{LOGO_BASE}/vtv4hd.png",
        "urls": [
            "https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/vtv4/playlist_360p.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "VTV5 HD",
        "group": "⭐️ VTV - Kênh Thiết Yếu",
        "tvg_id": "vtv5hd",
        "logo": f"{LOGO_BASE}/vtv5hd.png",
        "urls": [
            "https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/vtv5/playlist_360p.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "VTV5 Tây Nam Bộ",
        "group": "⭐️ VTV - Kênh Thiết Yếu",
        "tvg_id": "vtv5hdtnb",
        "logo": f"{LOGO_BASE}/vtv5hdtnb.png",
        "urls": [
            "https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/vtv5tnb/playlist_360p.m3u8",
            "https://dethich.pw/vtv5tnb/index.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "VTV5 Tây Nguyên",
        "group": "⭐️ VTV - Kênh Thiết Yếu",
        "tvg_id": "vtv5hdtn",
        "logo": f"{LOGO_BASE}/vtv5hdtn.png",
        "urls": [
            "https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/vtv5tn/playlist_360p.m3u8",
            "http://dethich.pw/vtv5tn/index.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "VTV Cần Thơ",
        "group": "⭐️ VTV - Kênh Thiết Yếu",
        "tvg_id": "vtvcanthohd",
        "logo": f"{LOGO_BASE}/vtv6hd.png",
        "urls": [
            "https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/vtv6/playlist_360p.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "VTV7 HD",
        "group": "⭐️ VTV - Kênh Thiết Yếu",
        "tvg_id": "vtv7hd",
        "logo": f"{LOGO_BASE}/vtv7hd.png",
        "urls": [
            "https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/vtv7/playlist_360p.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "VTV8 HD",
        "group": "⭐️ VTV - Kênh Thiết Yếu",
        "tvg_id": "vtv8hd",
        "logo": f"{LOGO_BASE}/vtv8hd.png",
        "urls": [
            "https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/vtv8/playlist_360p.m3u8",
            "https://dethich.pw/vtv8/index.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "VTV9 HD",
        "group": "⭐️ VTV - Kênh Thiết Yếu",
        "tvg_id": "vtv9hd",
        "logo": f"{LOGO_BASE}/vtv9hd.png",
        "urls": [
            "https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/vtv9/playlist_360p.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "VTV10",
        "group": "⭐️ VTV - Kênh Thiết Yếu",
        "tvg_id": "vtv10",
        "logo": f"{LOGO_BASE}/vtv10.png",
        "urls": [
            "https://vtvgolivepre-vtv02.vtvdigital.vn/hls/vtv/live/vtv10/free/master.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "Vietnam Today",
        "group": "⭐️ VTV - Kênh Thiết Yếu",
        "tvg_id": "vietnamtoday",
        "logo": f"{LOGO_BASE}/vietnamtoday.png",
        "urls": [
            "https://amagi-live.ondemandkorea.com/amgplt0456.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },

    # ==========================================
    # 📺 2. HTV - HTVC TP. HỒ CHÍ MINH
    # ==========================================
    {
        "name": "HTV1 HD",
        "group": "📺 HTV - HTVC TP.HCM",
        "tvg_id": "htv1hd",
        "logo": f"{LOGO_BASE}/htv1.png",
        "urls": [
            "https://1011154949.vnns.net/CDN-FPT02/HTV1-HD-1080p/playlist.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "HTV2 HD",
        "group": "📺 HTV - HTVC TP.HCM",
        "tvg_id": "htv2hd",
        "logo": f"{LOGO_BASE}/htv2.png",
        "urls": [
            "https://1011154949.vnns.net/CDN-FPT02/HTV2-HD-1080p/playlist.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "HTV3",
        "group": "📺 HTV - HTVC TP.HCM",
        "tvg_id": "htv3",
        "logo": f"{LOGO_BASE}/htv3.png",
        "urls": [
            "https://1011154949.vnns.net/CDN-FPT02/HTV3-SD-720p/playlist.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "HTV7 HD",
        "group": "📺 HTV - HTVC TP.HCM",
        "tvg_id": "htv7hd",
        "logo": f"{LOGO_BASE}/htv7.png",
        "urls": [
            "https://1011154949.vnns.net/CDN-FPT02/HTV7-HD-1080p/playlist.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "HTV9 HD",
        "group": "📺 HTV - HTVC TP.HCM",
        "tvg_id": "htv9hd",
        "logo": f"{LOGO_BASE}/htv9.png",
        "urls": [
            "https://1011154949.vnns.net/CDN-FPT02/HTV9-HD-1080p/playlist.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "HTV Thể Thao",
        "group": "⚽ Thể Thao Đặc Sắc",
        "tvg_id": "htvthethaohd",
        "logo": f"{LOGO_BASE}/htvthethao.png",
        "urls": [
            "https://1011154949.vnns.net/CDN-FPT02/HTV-THETHAO-HD-1080p/playlist.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "HTVC Thuần Việt",
        "group": "📺 HTV - HTVC TP.HCM",
        "tvg_id": "htvcthuanviethd",
        "logo": f"{LOGO_BASE}/htvcthuanviet.png",
        "urls": [
            "https://1011154949.vnns.net/CDN-FPT02/HTVC-THUANVIET-HD-1080p/playlist.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "HTVC Gia Đình",
        "group": "📺 HTV - HTVC TP.HCM",
        "tvg_id": "htvcgiadinhhd",
        "logo": f"{LOGO_BASE}/htvcgiadinh.png",
        "urls": [
            "https://1011154949.vnns.net/CDN-FPT02/HTVC-GIADINH-HD-1080p/playlist.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "HTVC Phim HD",
        "group": "📺 HTV - HTVC TP.HCM",
        "tvg_id": "htvcphimhd",
        "logo": f"{LOGO_BASE}/htvcphim.png",
        "urls": [
            "https://1011154949.vnns.net/CDN-FPT02/HTVC-PHIM-HD-1080p/playlist.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "HTVC Phụ Nữ",
        "group": "📺 HTV - HTVC TP.HCM",
        "tvg_id": "htvcphunuhd",
        "logo": f"{LOGO_BASE}/htvcphunu.png",
        "urls": [
            "https://1011154949.vnns.net/CDN-FPT02/HTVC-PHUNU-HD-1080p/playlist.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "HTVC Du Lịch",
        "group": "📺 HTV - HTVC TP.HCM",
        "tvg_id": "htvcdulichhd",
        "logo": f"{LOGO_BASE}/htvcdulich.png",
        "urls": [
            "https://1011154949.vnns.net/CDN-FPT02/HTVC-DULICH-HD-1080p/playlist.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "HTVC Ca Nhạc",
        "group": "📺 HTV - HTVC TP.HCM",
        "tvg_id": "htvccanhachd",
        "logo": f"{LOGO_BASE}/htvccanhac.png",
        "urls": [
            "https://1011154949.vnns.net/CDN-FPT02/HTVC-CANHAC-HD-1080p/playlist.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "HTVC Plus",
        "group": "📺 HTV - HTVC TP.HCM",
        "tvg_id": "htvcplus",
        "logo": f"{LOGO_BASE}/htvcplus.png",
        "urls": [
            "https://1011154949.vnns.net/CDN-FPT02/HTVC-PLUS-HD-1080p/playlist.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },

    # ==========================================
    # 🎬 3. TRUYỀN HÌNH VĨNH LONG (THVL)
    # ==========================================
    {
        "name": "THVL1 HD",
        "group": "🎬 Truyền Hình Vĩnh Long",
        "tvg_id": "thvl1hd",
        "logo": f"{LOGO_BASE}/thvl1hd.png",
        "urls": [
            "https://1011154949.vnns.net/CDN-FPT02/THVL1-HD-1080p/playlist.m3u8",
            "https://vietmitv.id.vn/c.php?k=ddf8023"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "THVL2 HD",
        "group": "🎬 Truyền Hình Vĩnh Long",
        "tvg_id": "thvl2hd",
        "logo": f"{LOGO_BASE}/thvl2hd.png",
        "urls": [
            "https://1011154949.vnns.net/CDN-FPT02/THVL2-HD-1080p/playlist.m3u8",
            "https://vietmitv.id.vn/c.php?k=05d10eb"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "THVL3 HD",
        "group": "🎬 Truyền Hình Vĩnh Long",
        "tvg_id": "thvl3hd",
        "logo": f"{LOGO_BASE}/thvl3hd.png",
        "urls": [
            "https://vietmitv.id.vn/c.php?k=a7b34c2"
        ],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"}
    },
    {
        "name": "THVL4 HD",
        "group": "🎬 Truyền Hình Vĩnh Long",
        "tvg_id": "thvl4hd",
        "logo": f"{LOGO_BASE}/thvl4hd.png",
        "urls": [
            "https://vietmitv.id.vn/c.php?k=b128250"
        ],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"}
    },

    # ==========================================
    # 📡 4. KÊNH QUỐC GIA, AN NINH & QUỐC PHÒNG
    # ==========================================
    {
        "name": "ANTV HD",
        "group": "📡 Kênh Quốc Gia & An Ninh",
        "tvg_id": "antvhd",
        "logo": f"{LOGO_BASE}/antv-hd.png",
        "urls": [
            "https://1011154949.vnns.net/CDN-FPT02/ANTV-HD-1080p/playlist.m3u8",
            "https://liveh12.vtvprime.vn/hls/ANNINHTV/index.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "QPVN HD",
        "group": "📡 Kênh Quốc Gia & An Ninh",
        "tvg_id": "qpvnhd",
        "logo": f"{LOGO_BASE}/qpvn-hd.png",
        "urls": [
            "https://liveh12.vtvprime.vn/hls/QPTV/index.m3u8"
        ],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },

    # ==========================================
    # 🎥 5. TRUYỀN HÌNH CÁP SCTV
    # ==========================================
    {
        "name": "SCTV2",
        "group": "🎥 Truyền Hình Cáp SCTV",
        "tvg_id": "sctv2hd",
        "logo": f"{LOGO_BASE}/sctv2hd.png",
        "urls": ["https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/sctv2/master.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "SCTV3",
        "group": "🎥 Truyền Hình Cáp SCTV",
        "tvg_id": "sctv3hd",
        "logo": f"{LOGO_BASE}/sctv3hd.png",
        "urls": ["https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/sctv3/master.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "SCTV4",
        "group": "🎥 Truyền Hình Cáp SCTV",
        "tvg_id": "sctv4hd",
        "logo": f"{LOGO_BASE}/sctv4hd.png",
        "urls": ["https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/sctv4/master.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "SCTV6",
        "group": "🎥 Truyền Hình Cáp SCTV",
        "tvg_id": "sctv6hd",
        "logo": f"{LOGO_BASE}/sctv6hd.png",
        "urls": ["https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/sctv6/master.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "SCTV7",
        "group": "🎥 Truyền Hình Cáp SCTV",
        "tvg_id": "sctv7hd",
        "logo": f"{LOGO_BASE}/sctv7hd.png",
        "urls": ["https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/sctv7/master.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "SCTV9",
        "group": "🎥 Truyền Hình Cáp SCTV",
        "tvg_id": "sctv9hd",
        "logo": f"{LOGO_BASE}/sctv9hd.png",
        "urls": ["https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/sctv9/master.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "SCTV11",
        "group": "🎥 Truyền Hình Cáp SCTV",
        "tvg_id": "sctv11hd",
        "logo": f"{LOGO_BASE}/sctv11hd.png",
        "urls": ["https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/sctv11/master.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "SCTV12",
        "group": "🎥 Truyền Hình Cáp SCTV",
        "tvg_id": "sctv12hd",
        "logo": f"{LOGO_BASE}/sctv12hd.png",
        "urls": ["https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/sctv12/master.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "SCTV13",
        "group": "🎥 Truyền Hình Cáp SCTV",
        "tvg_id": "sctv13hd",
        "logo": f"{LOGO_BASE}/sctv13hd.png",
        "urls": ["https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/sctv13/master.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "SCTV14",
        "group": "🎥 Truyền Hình Cáp SCTV",
        "tvg_id": "sctv14hd",
        "logo": f"{LOGO_BASE}/sctv14hd.png",
        "urls": ["https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/sctv14/master.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "SCTV15 (Thể Thao)",
        "group": "⚽ Thể Thao Đặc Sắc",
        "tvg_id": "sctv15hd",
        "logo": f"{LOGO_BASE}/sctv15hd.png",
        "urls": ["https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/sctv15/master.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "SCTV16",
        "group": "🎥 Truyền Hình Cáp SCTV",
        "tvg_id": "sctv16hd",
        "logo": f"{LOGO_BASE}/sctv16hd.png",
        "urls": ["https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/sctv16/master.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "SCTV17 (Thể Thao)",
        "group": "⚽ Thể Thao Đặc Sắc",
        "tvg_id": "sctv17hd",
        "logo": f"{LOGO_BASE}/sctv17hd.png",
        "urls": ["https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/sctv17/master.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "SCTV18",
        "group": "🎥 Truyền Hình Cáp SCTV",
        "tvg_id": "sctv18hd",
        "logo": f"{LOGO_BASE}/sctv18hd.png",
        "urls": ["https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/sctv18/master.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "SCTV19",
        "group": "🎥 Truyền Hình Cáp SCTV",
        "tvg_id": "sctv19hd",
        "logo": f"{LOGO_BASE}/sctv19hd.png",
        "urls": ["https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/sctv19/master.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "SCTV20",
        "group": "🎥 Truyền Hình Cáp SCTV",
        "tvg_id": "sctv20hd",
        "logo": f"{LOGO_BASE}/sctv20hd.png",
        "urls": ["https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/sctv20/master.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "SCTV22",
        "group": "🎥 Truyền Hình Cáp SCTV",
        "tvg_id": "sctv22hd",
        "logo": f"{LOGO_BASE}/sctv22hd.png",
        "urls": ["https://vtvgolive-sctvdrm.vtvdigital.vn/manifest/sctv22/master.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },

    # ==========================================
    # ⚽ 6. THỂ THAO & GIẢI TRÍ ĐẶC SẮC
    # ==========================================
    {
        "name": "ON GOLF",
        "group": "⚽ Thể Thao Đặc Sắc",
        "tvg_id": "ongolf",
        "logo": f"{LOGO_BASE}/ongolf.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=7c1dc3a"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },

    # ==========================================
    # 🎬 7. VTVCAB - PHIM TRUYỆN & GIẢI TRÍ
    # ==========================================
    {
        "name": "ON Cine",
        "group": "🎬 Phim Truyện & Giải Trí",
        "tvg_id": "oncine",
        "logo": f"{LOGO_BASE}/oncine.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=13fa5d2"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },
    {
        "name": "On Movies",
        "group": "🎬 Phim Truyện & Giải Trí",
        "tvg_id": "onmovies",
        "logo": f"{LOGO_BASE}/onmovies.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=6d5e19c"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },
    {
        "name": "ON Vie Giải Trí",
        "group": "🎬 Phim Truyện & Giải Trí",
        "tvg_id": "onviegiaitri",
        "logo": f"{LOGO_BASE}/onviegiaitri.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=5c975ba"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },
    {
        "name": "ON Vie Dramas",
        "group": "🎬 Phim Truyện & Giải Trí",
        "tvg_id": "onviedramas",
        "logo": f"{LOGO_BASE}/onviedramas.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=2a92be7"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },
    {
        "name": "ON E-Channel",
        "group": "🎬 Phim Truyện & Giải Trí",
        "tvg_id": "onechannel",
        "logo": f"{LOGO_BASE}/onechannel.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=2094832"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },
    {
        "name": "ON TRENDING TV",
        "group": "🎬 Phim Truyện & Giải Trí",
        "tvg_id": "ontrending",
        "logo": f"{LOGO_BASE}/ontrending.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=93f5539"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },
    {
        "name": "ON V Family",
        "group": "🎬 Phim Truyện & Giải Trí",
        "tvg_id": "onvfamily",
        "logo": f"{LOGO_BASE}/onvfamily.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=a666bb8"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },
    {
        "name": "ON Style TV",
        "group": "🎬 Phim Truyện & Giải Trí",
        "tvg_id": "onstyle",
        "logo": f"{LOGO_BASE}/onstyle.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=db10182"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },
    {
        "name": "On Music",
        "group": "🎬 Phim Truyện & Giải Trí",
        "tvg_id": "onmusic",
        "logo": f"{LOGO_BASE}/onmusic.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=2406e6c"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },
    {
        "name": "On Life",
        "group": "🎬 Phim Truyện & Giải Trí",
        "tvg_id": "onlife",
        "logo": f"{LOGO_BASE}/onlife.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=428d0be"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },
    {
        "name": "On O2TV",
        "group": "🎬 Phim Truyện & Giải Trí",
        "tvg_id": "ono2tv",
        "logo": f"{LOGO_BASE}/ono2tv.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=212c7c8"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },
    {
        "name": "ON Info TV",
        "group": "🎬 Phim Truyện & Giải Trí",
        "tvg_id": "oninfotv",
        "logo": f"{LOGO_BASE}/oninfotv.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=bcb8ad9"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },

    # ==========================================
    # 👧 8. THIẾU NHI & GIA ĐÌNH
    # ==========================================
    {
        "name": "On BiBi",
        "group": "👧 Thiếu Nhi & Gia Đình",
        "tvg_id": "onbibi",
        "logo": f"{LOGO_BASE}/onbibi.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=0009010"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },
    {
        "name": "On Kids",
        "group": "👧 Thiếu Nhi & Gia Đình",
        "tvg_id": "onkids",
        "logo": f"{LOGO_BASE}/onkids.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=facd9a9"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },

    # ==========================================
    # 🏛️ 9. TRUYỀN HÌNH ĐỊA PHƯƠNG
    # ==========================================
    {
        "name": "Hà Nội 1",
        "group": "🏛️ Truyền Hình Địa Phương",
        "tvg_id": "hanoi1",
        "logo": f"{LOGO_BASE}/hanoi1.png",
        "urls": ["https://liveh34.vtvprime.vn/hls/HANOI1TV/index.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "Hải Phòng",
        "group": "🏛️ Truyền Hình Địa Phương",
        "tvg_id": "haiphong",
        "logo": f"{LOGO_BASE}/haiphong.png",
        "urls": ["https://live.mediatech.vn/live/285a4c99665fdf84e94956c66bc7dc7eb5d/playlist.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "Cà Mau",
        "group": "🏛️ Truyền Hình Địa Phương",
        "tvg_id": "camau",
        "logo": f"{LOGO_BASE}/camau.png",
        "urls": ["https://1011154949.vnns.net/CDN-FPT02/CAMAU-HD-1080p/playlist.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "Bình Thuận",
        "group": "🏛️ Truyền Hình Địa Phương",
        "tvg_id": "binhthuan",
        "logo": f"{LOGO_BASE}/binhthuan.png",
        "urls": ["https://1011154949.vnns.net/CDN-FPT02/BINHTHUAN-SD-720p/playlist.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "Tuyên Quang",
        "group": "🏛️ Truyền Hình Địa Phương",
        "tvg_id": "tuyenquang",
        "logo": f"{LOGO_BASE}/tuyenquang.png",
        "urls": ["https://streaming.tuyenquangtv.vn/channel/tuyenquang/playlist.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "Thái Nguyên",
        "group": "🏛️ Truyền Hình Địa Phương",
        "tvg_id": "thainguyen",
        "logo": f"{LOGO_BASE}/thainguyen.png",
        "urls": ["https://streaming.thainguyentv.vn/hls/livestream.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "Quảng Ninh 1",
        "group": "🏛️ Truyền Hình Địa Phương",
        "tvg_id": "quangninh1",
        "logo": f"{LOGO_BASE}/quangninh1.png",
        "urls": ["https://cdn.baoquangninh.vn/live/285f5e4256ea38d48eebdc6175909c847fe/chunklist.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "Quảng Ninh 3",
        "group": "🏛️ Truyền Hình Địa Phương",
        "tvg_id": "quangninh3",
        "logo": f"{LOGO_BASE}/quangninh3.png",
        "urls": ["https://live.baoquangninh.vn/qtvlive/tv3live.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "Bắc Ninh",
        "group": "🏛️ Truyền Hình Địa Phương",
        "tvg_id": "bacninh",
        "logo": f"{LOGO_BASE}/bacninh.png",
        "urls": ["https://live-hq.evgcdn.net/live/285f5f227e988ab4445a2138091d3d62e8d/chunklist.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "Phú Thọ",
        "group": "🏛️ Truyền Hình Địa Phương",
        "tvg_id": "phutho",
        "logo": f"{LOGO_BASE}/phutho.png",
        "urls": ["https://live.mediatech.vn/live/2856e81d201c99b4649b5c62f3cddad3881/chunklist.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "Sơn La",
        "group": "🏛️ Truyền Hình Địa Phương",
        "tvg_id": "sonla",
        "logo": f"{LOGO_BASE}/sonla.png",
        "urls": ["https://live.mediatech.vn/live/28595222e707a364251b8724717894baa46/playlist.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "Điện Biên",
        "group": "🏛️ Truyền Hình Địa Phương",
        "tvg_id": "dienbien",
        "logo": f"{LOGO_BASE}/dienbien.png",
        "urls": ["https://live-hq.evgcdn.net/live/2855dfeccb7f49a41a2b0441b3bfeda413c/chunklist.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "Hưng Yên",
        "group": "🏛️ Truyền Hình Địa Phương",
        "tvg_id": "hungyen",
        "logo": f"{LOGO_BASE}/hungyen.png",
        "urls": ["https://live.mediatech.vn/live/285f5449d7d7d2946e0bd2d54b7e60f25a4/playlist.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "Ninh Bình",
        "group": "🏛️ Truyền Hình Địa Phương",
        "tvg_id": "ninhbinh",
        "logo": f"{LOGO_BASE}/ninhbinh.png",
        "urls": ["https://live.mediatech.vn/live/28597f8fd7ea5064d0f84ab00b3699dfd86/playlist.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "Nghệ An",
        "group": "🏛️ Truyền Hình Địa Phương",
        "tvg_id": "nghean",
        "logo": f"{LOGO_BASE}/nghean.png",
        "urls": ["https://live.mediatech.vn/live/2859591eef2e92249b682db021f4247c364/playlist.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "Lâm Đồng",
        "group": "🏛️ Truyền Hình Địa Phương",
        "tvg_id": "lamdong",
        "logo": f"{LOGO_BASE}/lamdong.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=be083d9"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },
    {
        "name": "Tây Ninh",
        "group": "🏛️ Truyền Hình Địa Phương",
        "tvg_id": "tayninh",
        "logo": f"{LOGO_BASE}/tayninhtv.png",
        "urls": ["https://live-hq.evgcdn.net/live/2851dc2c9af68834814a89e61db0faee561/chunklist.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },

    # ==========================================
    # 🌐 10. KÊNH QUỐC TẾ CHỌN LỌC
    # ==========================================
    {
        "name": "TVB Việt Nam",
        "group": "🌐 Kênh Quốc Tế",
        "tvg_id": "tvbvietnam",
        "logo": f"{LOGO_BASE}/tvb-vietnam.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=24a932f1ddbed2be"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },
    {
        "name": "KBS World",
        "group": "🌐 Kênh Quốc Tế",
        "tvg_id": "kbsworld",
        "logo": f"{LOGO_BASE}/kbsworld.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=de55dd1c30425798"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },
    {
        "name": "NHK World Japan",
        "group": "🌐 Kênh Quốc Tế",
        "tvg_id": "nhkworld",
        "logo": f"{LOGO_BASE}/nhk.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=821cc0a76b9ae654"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },
    {
        "name": "NHK Premium",
        "group": "🌐 Kênh Quốc Tế",
        "tvg_id": "nhk_premium",
        "logo": f"{LOGO_BASE}/nhk.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=3714b1cfca8cac1f"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },
    {
        "name": "France 24",
        "group": "🌐 Kênh Quốc Tế",
        "tvg_id": "france24",
        "logo": f"{LOGO_BASE}/france24.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=61ba002639c4e0c8"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },
    {
        "name": "DW - Deutsche Welle",
        "group": "🌐 Kênh Quốc Tế",
        "tvg_id": "dw",
        "logo": f"{LOGO_BASE}/dw.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=0c33f1bb2e61a86e"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },
    {
        "name": "Channel News Asia",
        "group": "🌐 Kênh Quốc Tế",
        "tvg_id": "channelnewsasia",
        "logo": f"{LOGO_BASE}/channelnewsasia.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=e47519e6c738f235"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },
    {
        "name": "TV5 Monde",
        "group": "🌐 Kênh Quốc Tế",
        "tvg_id": "tv5monde",
        "logo": f"{LOGO_BASE}/tv5monde.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=fd70eaf55b8ad286"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },
    {
        "name": "Kix",
        "group": "🌐 Kênh Quốc Tế",
        "tvg_id": "kix",
        "logo": f"{LOGO_BASE}/kix.png",
        "urls": ["https://vietmitv.id.vn/c.php?k=efa3a413e6c10a76"],
        "headers": {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"}
    },
    {
        "name": "Arirang TV HD",
        "group": "🌐 Kênh Quốc Tế",
        "tvg_id": "arirang",
        "logo": f"{LOGO_BASE}/arirang.png",
        "urls": ["http://amdlive.ctnd.com.edgesuite.net/arirang_1ch/smil:arirang_1ch.smil/playlist.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    },
    {
        "name": "VBS TV HD",
        "group": "🌐 Kênh Quốc Tế",
        "tvg_id": "vbstv",
        "logo": f"{LOGO_BASE}/vbstv.png",
        "urls": ["https://tgn.bozztv.com/vbstvcdn/vbstv/ngrp:vbstv_all/playlist.m3u8"],
        "headers": {"User-Agent": "Mozilla/5.0"}
    }
]

def check_single_url(url, headers):
    """Kiểm tra chuyên sâu một URL luồng HLS m3u8 có đang sống và phát nội dung thật sự hay không."""
    req_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    if headers:
        req_headers.update(headers)
    
    start_time = time.time()
    try:
        req = urllib.request.Request(url, headers=req_headers)
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as resp:
            elapsed = int((time.time() - start_time) * 1000)
            if resp.status != 200:
                return False, f"HTTP {resp.status}", elapsed, url
            
            data = resp.read(3072)
            content_type = resp.headers.get("Content-Type", "")
            
            # Kiểm tra định dạng m3u8 playlist
            if b"#EXTM3U" not in data and "mpegurl" not in content_type and b"#EXT-X" not in data:
                return False, "Not an M3U8 stream", elapsed, url
            
            # Kiểm tra bẫy offline / placeholder (như signal_low0.png, nosignal, offline)
            text_preview = data.decode("utf-8", errors="ignore").lower()
            if "signal_low" in text_preview or "nosignal" in text_preview or "maintenance" in text_preview:
                return False, "Placeholder/No Signal", elapsed, url
            
            # Phải có ít nhất 1 segment hoặc 1 stream bitrate
            if not any(marker in text_preview for marker in [".ts", ".m3u8", ".m4s", ".aac", "#ext-x-stream-inf"]):
                return False, "Empty or invalid playlist chunks", elapsed, url
            
            final_url = resp.geturl()
            return True, "ALIVE", elapsed, final_url
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}", int((time.time() - start_time) * 1000), url
    except urllib.error.URLError as e:
        return False, f"URLError: {e.reason}", int((time.time() - start_time) * 1000), url
    except Exception as e:
        return False, f"Error: {type(e).__name__}", int((time.time() - start_time) * 1000), url

def verify_channel(channel):
    """Kiểm tra từng channel, tự động fallback URL nếu url chính bị chết."""
    for idx, url in enumerate(channel["urls"]):
        ok, reason, latency, resolved = check_single_url(url, channel.get("headers", {}))
        if ok:
            return {
                "channel": channel,
                "status": "LIVE",
                "active_url": url,
                "resolved_url": resolved,
                "latency_ms": latency,
                "is_fallback": idx > 0,
                "message": f"OK ({latency}ms)"
            }
    
    return {
        "channel": channel,
        "status": "DEAD",
        "active_url": channel["urls"][0],
        "resolved_url": "",
        "latency_ms": 0,
        "is_fallback": False,
        "message": reason
    }

def generate_m3u(verified_list, out_path, proxy_origin=None):
    """Tạo file playlist .M3U chuẩn định dạng Extended M3U cho NVC Tivi."""
    lines = [
        '#EXTM3U url-tvg="https://epg.io.vn/epgc.xml,https://raw.githubusercontent.com/AqFad2811/epg/main/epg.xml" tvg-shift=0 m3uautoload=1',
        '#PLAYLIST: NVC Tivi - Truyền Hình Việt Nam Chuẩn Link Sống',
        '#AUTHOR: NVC Tivi Development Team',
        ''
    ]
    
    for item in verified_list:
        ch = item["channel"]
        url = item["active_url"]
        
        # Nếu ở chế độ proxy qua Cloudflare Worker
        if proxy_origin:
            import urllib.parse
            url = f"{proxy_origin}/channel?group={urllib.parse.quote(ch['group'])}&name={urllib.parse.quote(ch['name'])}"
        
        extinf = f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}" tvg-name="{ch["name"]}" tvg-logo="{ch["logo"]}" group-title="{ch["group"]}",{ch["name"]}'
        lines.append(extinf)
        lines.append('#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        lines.append('#KODIPROP:inputstream.adaptive.manifest_type=hls')
        lines.append(url)
        lines.append('')
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"-> Generated {out_path} ({len(verified_list)} live channels)")

def main():
    print("=" * 65)
    print("⚡ NVC TIVI - HỆ THỐNG CRAWL VÀ XÁC THỰC KÊNH TRUYỀN HÌNH VIỆT NAM")
    print("=" * 65)
    print(f"Tổng số kênh trong cơ sở dữ liệu: {len(CHANNEL_CATALOG)}")
    print("Đang tiến hành kiểm tra kết nối & luồng streaming thực tế...")
    
    start_all = time.time()
    
    # Dùng 10 worker threads để tối ưu tốc độ và không gây nghẽn CDN
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(verify_channel, CHANNEL_CATALOG))
    
    total_time = time.time() - start_all
    
    live_channels = [r for r in results if r["status"] == "LIVE"]
    dead_channels = [r for r in results if r["status"] == "DEAD"]
    
    print("\n" + "=" * 65)
    print("📊 KẾT QUẢ KIỂM TRA LINK SỐNG (LIVE STREAM CHECK)")
    print("=" * 65)
    print(f"✅ SỐ KÊNH HOẠT ĐỘNG TỐT (LIVE): {len(live_channels)} / {len(CHANNEL_CATALOG)} ({len(live_channels)/len(CHANNEL_CATALOG)*100:.1f}%)")
    print(f"❌ SỐ KÊNH LỖI / ĐÃ LOẠI BỎ (DEAD): {len(dead_channels)}")
    print(f"⏱️ Tổng thời gian kiểm tra: {total_time:.2f} giây")
    
    # In danh sách kênh Live theo Group
    groups = {}
    for r in live_channels:
        g = r["channel"]["group"]
        groups.setdefault(g, []).append(r)
        
    print("\n📋 PHÂN BỔ KÊNH THEO NHÓM:")
    for g, items in groups.items():
        print(f"  • {g}: {len(items)} kênh")
    
    if dead_channels:
        print("\n⚠️ CÁC KÊNH BỊ LOẠI BỎ (LINK LỖI / CHẾT):")
        for r in dead_channels:
            print(f"  ❌ [{r['channel']['group']}] {r['channel']['name']}: {r['message']}")
            
    # Xuất file M3U chuẩn
    generate_m3u(live_channels, "nvctivi.m3u")
    generate_m3u(live_channels, "nvctivi_proxy.m3u", proxy_origin="https://nvctivi-stream.workers.dev")
    
    # Xuất file JSON cho App NVC Tivi
    json_data = {
        "app": "NVC Tivi",
        "version": "2.0.0",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_live_channels": len(live_channels),
        "epg_urls": [
            "https://epg.io.vn/epgc.xml",
            "https://raw.githubusercontent.com/AqFad2811/epg/main/epg.xml"
        ],
        "groups": list(groups.keys()),
        "channels": [
            {
                "name": r["channel"]["name"],
                "group": r["channel"]["group"],
                "tvg_id": r["channel"]["tvg_id"],
                "logo": r["channel"]["logo"],
                "url": r["active_url"],
                "latency_ms": r["latency_ms"],
                "status": "online"
            }
            for r in live_channels
        ]
    }
    
    with open("nvctivi_channels.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    print("-> Generated nvctivi_channels.json")
    
    # Tạo báo cáo Markdown
    report_lines = [
        "# BÁO CÁO KIỂM ĐỊNH VÀ CHUẨN HOÁ DANH SÁCH KÊNH NVC TIVI",
        f"- Thời gian thực hiện: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Tổng số kênh kiểm tra: {len(CHANNEL_CATALOG)}",
        f"- Kênh hoạt động (LIVE): **{len(live_channels)}** ({len(live_channels)/len(CHANNEL_CATALOG)*100:.1f}%)",
        f"- Kênh không hoạt động (DEAD - đã loại bỏ): **{len(dead_channels)}**",
        "",
        "## Thống kê theo nhóm kênh",
        "| Nhóm kênh | Số lượng kênh sống | Tình trạng |",
        "| :--- | :---: | :---: |"
    ]
    for g, items in groups.items():
        report_lines.append(f"| {g} | {len(items)} | ✅ 100% Link sống |")
    
    report_lines.extend([
        "",
        "## Danh sách kênh hoạt động chi tiết",
        "| Kênh | Nhóm | Độ trễ (ms) | URL luồng phát sóng trực tiếp |",
        "| :--- | :--- | :---: | :--- |"
    ])
    for r in live_channels:
        ch = r["channel"]
        report_lines.append(f"| **{ch['name']}** | {ch['group']} | {r['latency_ms']}ms | `{r['active_url']}` |")
        
    with open("REPORT_LIVE_CHANNELS.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print("-> Generated REPORT_LIVE_CHANNELS.md")

if __name__ == "__main__":
    main()
