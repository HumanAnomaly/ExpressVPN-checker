"""Crypto helpers: HMAC signing, gzip, RSA envelope, AES decrypt."""
import base64
import gzip
import hashlib
import hmac
import os
import random
import shutil
import string
import subprocess
import tempfile

from .config import EXPRESSVPN_CERT, HMAC_KEY


def hmac_b64(data: bytes) -> str:
    return base64.b64encode(hmac.new(HMAC_KEY, data, hashlib.sha1).digest()).decode()


def rand_digits(n: int = 64) -> str:
    return "".join(random.choice(string.digits) for _ in range(n))


def rand16() -> bytes:
    return os.urandom(16)


def gzip_compress(data: bytes) -> bytes:
    return gzip.compress(data)


def envelope_encrypt(data: bytes) -> bytes:
    """RSA envelope via `openssl smime` — only the server key opens it."""
    cert_der = base64.b64decode(EXPRESSVPN_CERT)
    openssl = shutil.which("openssl") or "openssl"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".cer") as cf:
        cf.write(cert_der)
        cert_path = cf.name
    with tempfile.NamedTemporaryFile(delete=False) as inf:
        inf.write(data)
        in_path = inf.name
    try:
        p = subprocess.run(
            [openssl, "smime", "-encrypt", "-binary", "-aes-128-cbc",
             "-outform", "DER", "-in", in_path, cert_path],
            capture_output=True, timeout=30)
        if p.returncode != 0:
            raise RuntimeError(f"openssl failed: {p.stderr.decode()[:300]}")
        return p.stdout
    finally:
        for f in (cert_path, in_path):
            try:
                os.unlink(f)
            except OSError:
                pass


def aes_cbc_decrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    dec = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    pt = dec.update(data) + dec.finalize()
    return pt[:-pt[-1]]
