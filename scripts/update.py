#!/usr/bin/env python3
"""
NVC Tivi - Playlist Synchronizer & Encrypter
Cập nhật, đồng bộ hoá và mã hoá playlist cho NVC Tivi.
"""

import base64
import hashlib
import os
import struct
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

import requests

ENC_FILE = "nvc.enc"
MASTER_M3U = "nvctivi.m3u"
_SOURCE_KEY = 0x6D
_SOURCE_DATA = bytes([5,25,25,29,30,87,66,66,27,4,8,25,0,4,25,27,67,4,9,67,27,3,66,27,4,8,25,0,4,25,27,67,0,94,24])

NVC_MAGIC = b"VXMENC3\x00"
NVC_MAGIC_ALT = b"NVCENC3\x00"
NVC_AAD_PREFIX = b"VietMiTV/VXMENC3"
NVC_AAD_PREFIX_ALT = b"NVCTivi/NVCENC3"
NVC_KEY_ID = 1
NVC_K = [
    bytes([0x85, 0x05, 0x75, 0x40, 0xE5, 0x2E, 0xD3, 0xF2]),
    bytes([0x57, 0xD8, 0xC3, 0x3E, 0x7F, 0x13, 0x1C, 0xE3]),
    bytes([0x4A, 0xBE, 0xB2, 0x89, 0x9C, 0x8E, 0x21, 0x63]),
    bytes([0x77, 0x06, 0xC3, 0x70, 0xD7, 0xCD, 0x71, 0x44]),
]
NVC_M = [0x5A, 0xA7, 0x3C, 0xD1]


def source_url() -> str:
    env_url = os.environ.get("UPSTREAM_PLAYLIST_URL", "").strip()
    if env_url:
        return env_url
    value = bytes(b ^ _SOURCE_KEY for b in _SOURCE_DATA).decode("utf-8")
    if not value.startswith(("https://", "http://")):
        raise RuntimeError("Nguồn playlist không hợp lệ")
    return value


def load_private_key():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    raw = (
        os.environ.get("NVC_PRIVATE_KEY_B64", "")
        or os.environ.get("NVCENC3_PRIVATE_KEY_B64", "")
        or os.environ.get("VXMENC3_PRIVATE_KEY_B64", "")
    ).strip()
    if not raw:
        return None

    try:
        der = base64.b64decode(raw, validate=True)
        key = serialization.load_der_private_key(der, password=None)
    except Exception as exc:
        raise RuntimeError("NVC private key không hợp lệ") from exc

    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise RuntimeError("NVC private key không phải EC")
    if key.curve.name != "secp256r1":
        raise RuntimeError("NVC private key phải dùng P-256")

    return key


def derive_key(salt: bytes) -> bytes:
    seed = bytes(v ^ NVC_M[i] for i, part in enumerate(NVC_K) for v in part)
    key = hashlib.sha256(seed + salt).digest()

    for _ in range(60000):
        key = hashlib.sha256(key + salt).digest()

    return key


def build_aad(counter: int, key_id: int, created_at: int, salt: bytes, iv: bytes, prefix: bytes = NVC_AAD_PREFIX) -> bytes:
    return (
        prefix
        + struct.pack(">QIQ", counter, key_id, created_at)
        + salt
        + iv
    )


def normalize_playlist(text: str) -> str:
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n").strip()

    if not text.startswith("#EXTM3U"):
        raise RuntimeError("Nguồn không phải playlist M3U hợp lệ")
    if "#EXTINF:" not in text:
        raise RuntimeError("Playlist nguồn không có kênh")

    return text + "\n"


def count_channels(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.startswith("#EXTINF:"))


def fetch_source() -> str:
    # Ưu tiên sử dụng file nvctivi.m3u vừa được crawl & verify nếu có
    if Path(MASTER_M3U).exists():
        local_text = Path(MASTER_M3U).read_text(encoding="utf-8")
        if count_channels(local_text) > 0:
            print(f"Sử dụng playlist cục bộ đã xác thực link sống: {MASTER_M3U}")
            return normalize_playlist(local_text)

    for attempt in range(1, 5):
        try:
            response = requests.get(
                source_url(),
                timeout=(10, 45),
                allow_redirects=True,
                headers={
                    "User-Agent": "NVC-Tivi-Worker/2.0",
                    "Accept": "text/plain,text/*,*/*;q=0.8",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                },
            )
            try:
                response.raise_for_status()
                response.encoding = "utf-8"
                return normalize_playlist(response.text)
            finally:
                response.close()
        except requests.exceptions.SSLError:
            raise
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as error:
            status = error.response.status_code if error.response is not None else None
            if status is not None and status not in (408, 429, 500, 502, 503, 504):
                raise
            if attempt == 4:
                raise
            delay = 5 * attempt
            print(f"Tải nguồn thất bại ({type(error).__name__}); thử lại {attempt}/3 sau {delay}s", flush=True)
            time.sleep(delay)


def encrypt_playlist(text: str, counter: int) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if counter <= 0:
        raise RuntimeError("Counter NVCENC3 không hợp lệ")

    keypair = load_private_key()
    if not keypair:
        raise RuntimeError("Thiếu NVC_PRIVATE_KEY_B64 để mã hóa nvc.enc")

    salt = os.urandom(16)
    iv = os.urandom(12)
    created_at = int(time.time())

    aad = build_aad(counter, NVC_KEY_ID, created_at, salt, iv)
    ciphertext = AESGCM(derive_key(salt)).encrypt(
        iv,
        text.encode("utf-8"),
        aad,
    )

    signed = (
        struct.pack(">QIQ", counter, NVC_KEY_ID, created_at)
        + salt
        + iv
        + struct.pack(">I", len(ciphertext))
        + ciphertext
    )

    signature = keypair.sign(
        NVC_MAGIC + signed,
        ec.ECDSA(hashes.SHA256()),
    )

    return (
        NVC_MAGIC
        + struct.pack(">I", len(signed))
        + signed
        + struct.pack(">I", len(signature))
        + signature
    )


def decrypt_playlist(payload: bytes) -> tuple[str, int]:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    magic = payload[:8]
    if len(payload) < 96 or (magic != NVC_MAGIC and magic != NVC_MAGIC_ALT):
        raise RuntimeError("nvc.enc không đúng định dạng NVCENC3")

    pos = 8
    signed_len = struct.unpack(">I", payload[pos:pos + 4])[0]
    pos += 4

    signed = payload[pos:pos + signed_len]
    pos += signed_len

    if len(signed) != signed_len or pos + 4 > len(payload):
        raise RuntimeError("NVCENC3 bị thiếu dữ liệu")

    sig_len = struct.unpack(">I", payload[pos:pos + 4])[0]
    pos += 4
    signature = payload[pos:pos + sig_len]

    if len(signature) != sig_len or pos + sig_len != len(payload):
        raise RuntimeError("NVCENC3 signature length không hợp lệ")

    keypair = load_private_key()
    if keypair:
        try:
            keypair.public_key().verify(
                signature,
                magic + signed,
                ec.ECDSA(hashes.SHA256()),
            )
        except Exception as exc:
            raise RuntimeError("Chữ ký NVCENC3 không hợp lệ") from exc

    if len(signed) < 52:
        raise RuntimeError("NVCENC3 signed body quá ngắn")

    counter, key_id, created_at = struct.unpack(">QIQ", signed[:20])
    salt = signed[20:36]
    iv = signed[36:48]
    cipher_len = struct.unpack(">I", signed[48:52])[0]
    ciphertext = signed[52:52 + cipher_len]

    if counter <= 0 or key_id != NVC_KEY_ID or created_at <= 0:
        raise RuntimeError("Metadata NVCENC3 không hợp lệ")
    if len(ciphertext) != cipher_len or 52 + cipher_len != len(signed):
        raise RuntimeError("Ciphertext NVCENC3 không hợp lệ")

    # Thử giải mã với prefix mặc định hoặc prefix thay thế
    decrypted_bytes = None
    for prefix in [NVC_AAD_PREFIX, NVC_AAD_PREFIX_ALT]:
        aad = build_aad(counter, key_id, created_at, salt, iv, prefix=prefix)
        try:
            decrypted_bytes = AESGCM(derive_key(salt)).decrypt(
                iv,
                ciphertext,
                aad,
            )
            break
        except Exception:
            continue

    if decrypted_bytes is None:
        raise RuntimeError("Không giải mã/xác thực được NVCENC3")

    return normalize_playlist(decrypted_bytes.decode("utf-8")), counter


def load_current() -> tuple[str, int]:
    path = Path(ENC_FILE)
    if not path.exists():
        if Path(MASTER_M3U).exists():
            return Path(MASTER_M3U).read_text(encoding="utf-8"), 1
        raise RuntimeError(f"Không tìm thấy {ENC_FILE} hoặc {MASTER_M3U}")

    keypair = load_private_key()
    if not keypair:
        if Path(MASTER_M3U).exists():
            return Path(MASTER_M3U).read_text(encoding="utf-8"), 1
        return "#EXTM3U\n", 0

    return decrypt_playlist(path.read_bytes())


def validate() -> None:
    text, counter = load_current()
    print(f"Playlist nvc: {count_channels(text)} kênh hợp lệ; counter={counter}")


def sync() -> None:
    source = fetch_source()
    current, counter = load_current()

    print(f"Nguồn mới    : {count_channels(source)} kênh")
    print(f"Danh sách cũ : {count_channels(current)} kênh")

    Path(MASTER_M3U).write_text(source, encoding="utf-8")

    keypair = load_private_key()
    if keypair:
        next_counter = counter + 1
        Path(ENC_FILE).write_bytes(encrypt_playlist(source, next_counter))
        validate()
        print(f"Mã hóa & đồng bộ hoàn tất: {count_channels(source)} kênh; counter={next_counter}")
    else:
        print(f"Cập nhật {MASTER_M3U} hoàn tất ({count_channels(source)} kênh sống). [nvc.enc bỏ qua vì không có private key]")


def main() -> None:
    if sys.argv[1:] == ["--validate-only"]:
        validate()
        return

    if sys.argv[1:] == ["--crawl"]:
        import subprocess
        subprocess.run([sys.executable, "scripts/nvc_crawler.py"], check=True)
        return

    if sys.argv[1:] and sys.argv[1] not in ["--sync"]:
        raise SystemExit("Cách dùng: update.py [--validate-only | --crawl | --sync]")

    sync()


if __name__ == "__main__":
    main()
